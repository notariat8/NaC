from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Callable
from urllib.parse import quote, urlencode

from .oidc_jwt import build_oci_identity_domain_json_fetcher


RoleMembershipResolver = Callable[..., dict[str, Any]]


def build_oci_identity_domain_role_membership_resolver(
    *,
    identity_domain_url: str,
    fetcher: Callable[[str], Mapping[str, Any]] | None = None,
) -> RoleMembershipResolver | None:
    base_url = _normalized_identity_domain_url(identity_domain_url)
    if not base_url:
        return None
    json_fetcher = fetcher or build_oci_identity_domain_json_fetcher()

    def resolve(*, claims: dict[str, Any], required_role: str) -> dict[str, Any]:
        role = required_role.strip() if isinstance(required_role, str) else ""
        if not role:
            return _evidence("unavailable", required_role=required_role)
        try:
            user = _find_user(base_url=base_url, claims=claims, fetcher=json_fetcher)
            if not user:
                return _evidence("missing", required_role=role)
            if _resource_contains_role(user, role):
                return _evidence("confirmed", required_role=role)
            if _group_contains_user(base_url=base_url, user=user, required_role=role, fetcher=json_fetcher):
                return _evidence("confirmed", required_role=role)
            return _evidence("missing", required_role=role)
        except Exception:
            return _evidence("unavailable", required_role=role)

    return resolve


def _find_user(
    *,
    base_url: str,
    claims: Mapping[str, Any],
    fetcher: Callable[[str], Mapping[str, Any]],
) -> Mapping[str, Any] | None:
    for attribute, value in _user_lookup_candidates(claims):
        payload = fetcher(
            _scim_filter_url(
                base_url,
                "Users",
                attribute,
                value,
                attributes=("id", "userName", "emails", "groups"),
            )
        )
        resource = _first_resource(payload)
        if resource is not None:
            return resource
    return None


def _user_lookup_candidates(claims: Mapping[str, Any]) -> Iterable[tuple[str, str]]:
    seen: set[tuple[str, str]] = set()
    for claim_key, scim_attribute in (
        ("sub", "id"),
        ("user_id", "id"),
        ("preferred_username", "userName"),
        ("upn", "userName"),
        ("email", "userName"),
    ):
        value = _safe_text(claims.get(claim_key), max_length=320)
        if not value:
            continue
        candidate = (scim_attribute, value)
        if candidate not in seen:
            seen.add(candidate)
            yield candidate
        if scim_attribute == "id" and value.startswith("ocid1.user."):
            ocid_candidate = ("ocid", value)
            if ocid_candidate not in seen:
                seen.add(ocid_candidate)
                yield ocid_candidate


def _group_contains_user(
    *,
    base_url: str,
    user: Mapping[str, Any],
    required_role: str,
    fetcher: Callable[[str], Mapping[str, Any]],
) -> bool:
    user_id = _safe_text(user.get("id"), max_length=160)
    if not user_id:
        return False
    payload = fetcher(
        _scim_filter_url(
            base_url,
            "Groups",
            "displayName",
            required_role,
            attributes=("id", "displayName", "members"),
        )
    )
    for group in _resources(payload):
        for member in _members(group):
            if member == user_id:
                return True
        group_id = _safe_text(group.get("id"), max_length=160)
        if not group_id:
            continue
        detail = fetcher(_scim_resource_url(base_url, "Groups", group_id, attributes=("id", "displayName", "members")))
        if not isinstance(detail, Mapping):
            continue
        for member in _members(detail):
            if member == user_id:
                return True
    return False


def _resource_contains_role(resource: Mapping[str, Any], required_role: str) -> bool:
    return required_role in set(_role_like_strings(resource))


def _role_like_strings(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized_key = str(key).replace("-", "_").lower()
            if normalized_key in {"groups", "roles", "group", "role", "app_roles", "approles"}:
                yield from _string_items(item)
            if isinstance(item, (Mapping, list, tuple, set)):
                yield from _role_like_strings(item)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _role_like_strings(item)


def _members(group: Mapping[str, Any]) -> Iterable[str]:
    for item in group.get("members", []) if isinstance(group.get("members"), list) else []:
        if isinstance(item, Mapping):
            member_id = _safe_text(item.get("value"), max_length=160)
            if member_id:
                yield member_id


def _string_items(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        if value:
            yield value
        return
    if isinstance(value, Mapping):
        for key in ("value", "name", "display", "displayName"):
            item = value.get(key)
            if isinstance(item, str) and item:
                yield item
        return
    if isinstance(value, Iterable):
        for item in value:
            yield from _string_items(item)


def _first_resource(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    for resource in _resources(payload):
        return resource
    return None


def _resources(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    resources = payload.get("Resources")
    if resources is None:
        resources = payload.get("resources")
    if not isinstance(resources, list):
        return
    for resource in resources:
        if isinstance(resource, Mapping):
            yield resource


def _scim_filter_url(
    base_url: str,
    resource: str,
    attribute: str,
    value: str,
    *,
    attributes: tuple[str, ...] = (),
) -> str:
    escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
    query_items: dict[str, str] = {"filter": f'{attribute} eq "{escaped_value}"'}
    if attributes:
        query_items["attributes"] = ",".join(attributes)
    query = urlencode(query_items)
    return f"{base_url}/admin/v1/{quote(resource, safe='')}?{query}"


def _scim_resource_url(
    base_url: str,
    resource: str,
    resource_id: str,
    *,
    attributes: tuple[str, ...] = (),
) -> str:
    query = urlencode({"attributes": ",".join(attributes)}) if attributes else ""
    url = f"{base_url}/admin/v1/{quote(resource, safe='')}/{quote(resource_id, safe='')}"
    return f"{url}?{query}" if query else url


def _normalized_identity_domain_url(value: str) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.strip().rstrip("/")
    if not normalized.startswith("https://") or ".identity.oraclecloud.com" not in normalized:
        return ""
    return normalized


def _safe_text(value: Any, *, max_length: int) -> str:
    if not isinstance(value, str):
        return ""
    stripped = value.strip()
    if not stripped or len(stripped) > max_length:
        return ""
    return stripped


def _evidence(status: str, *, required_role: str) -> dict[str, Any]:
    return {
        "status": status,
        "role": required_role,
        "source": "oci_identity_domain_server_lookup",
        "contains_credentials": False,
        "tokens_returned": False,
        "claims_exposed": False,
        "provider_details_exposed": False,
    }
