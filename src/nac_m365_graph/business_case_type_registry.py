from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from notary_kg.business_case_type_transport import (
    BusinessCaseTypeRegistryRow,
    RegistryFetchResult,
)

from .graph_client import GraphHttpError


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
MAX_PAGES = 100
MAX_ITEMS = 1000
MAX_RESPONSE_BYTES = 1_048_576

_ITEM_SELECT = "id,eTag"
_FIELDS_SELECT = "BusinessCaseTypeId,LifecycleStatus,Selectable,CatalogVersion"
_FIELDS_EXPAND = f"fields($select={_FIELDS_SELECT})"
_OPERATION_ROLES = {
    "case_create_validation": frozenset(
        {
            "notary",
            "notary_clerk",
            "substitution_notary",
            "substitution_clerk",
            "runtime_service",
        }
    ),
    "matter_type_correction_validation": frozenset({"MatterCorrector", "runtime_service"}),
    "backfill_validation": frozenset({"BackfillOperator", "runtime_service"}),
    "optional_process_read": frozenset(
        {
            "notary",
            "notary_clerk",
            "substitution_notary",
            "substitution_clerk",
            "runtime_service",
        }
    ),
}


class GraphBusinessCaseTypeTokenProvider(Protocol):
    def fetch_access_token(self) -> str: ...


class GraphBusinessCaseTypeHttpError(RuntimeError):
    def __init__(self, status: int):
        super().__init__(f"Microsoft Graph request failed with HTTP {status}")
        self.status = status


class GraphBusinessCaseTypeResponseError(RuntimeError):
    def __init__(self):
        super().__init__("Microsoft Graph returned an invalid JSON response")


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GraphBusinessCaseTypeRestClient:
    redirects_allowed = False
    retains_error_body = False

    def __init__(
        self,
        token_provider: GraphBusinessCaseTypeTokenProvider,
        *,
        base_url: str = GRAPH_BASE_URL,
    ) -> None:
        self.token_provider = token_provider
        self.base_url = base_url

    def get(self, path: str) -> dict[str, object]:
        if self.base_url != GRAPH_BASE_URL:
            raise ValueError("Only Microsoft Graph v1.0 is allowed")
        parsed_path = urllib.parse.urlsplit(path)
        if not path.startswith("/") or parsed_path.scheme or parsed_path.netloc:
            raise ValueError("A relative Microsoft Graph path is required")

        request = urllib.request.Request(
            self.base_url + path,
            headers={
                "Authorization": f"Bearer {self.token_provider.fetch_access_token()}",
                "Accept": "application/json",
            },
            method="GET",
        )
        status: int | None = None
        try:
            with self._open(request) as response:
                raw_response = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw_response) > MAX_RESPONSE_BYTES:
                    raise GraphBusinessCaseTypeResponseError()
        except urllib.error.HTTPError as error:
            status = error.code
            error.close()
        if status is not None:
            raise GraphBusinessCaseTypeHttpError(status)
        try:
            parsed_response = json.loads(raw_response.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GraphBusinessCaseTypeResponseError() from None
        if type(parsed_response) is not dict:
            raise GraphBusinessCaseTypeResponseError()
        return parsed_response

    def _open(self, request: urllib.request.Request):
        opener = urllib.request.build_opener(NoRedirectHandler())
        return opener.open(request, timeout=30)


class GraphGetClient(Protocol):
    base_url: str
    redirects_allowed: bool
    retains_error_body: bool

    def get(self, path: str) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class GraphBusinessCaseTypeRegistryReadScope:
    site_id: str
    list_id: str
    operation: str
    role: str
    runtime_permission: str
    site_grant_role: str

    def is_allowed(self) -> bool:
        roles = _OPERATION_ROLES.get(self.operation)
        return (
            type(self.site_id) is str
            and bool(self.site_id)
            and type(self.list_id) is str
            and bool(self.list_id)
            and roles is not None
            and self.role in roles
            and self.runtime_permission == "Sites.Selected"
            and self.site_grant_role == "read"
        )


@dataclass(frozen=True, slots=True)
class GraphBusinessCaseTypeRegistryReadAdapter:
    client: GraphGetClient
    scope: GraphBusinessCaseTypeRegistryReadScope

    def fetch_registry(
        self,
        *,
        site_id: str,
        business_case_type_id: str,
        catalog_version: str,
        if_none_match: str | None,
    ) -> RegistryFetchResult:
        if not self._request_is_allowed(site_id, business_case_type_id, catalog_version):
            return RegistryFetchResult.unavailable()

        collection_path = _collection_path(self.scope.site_id, self.scope.list_id)
        filter_expression = _filter_expression(business_case_type_id, catalog_version)
        path = _initial_path(collection_path, filter_expression)
        rows: list[BusinessCaseTypeRegistryRow] = []
        visited_next_links = {
            _canonical_collection_url(
                collection_path,
                {
                    "$select": _ITEM_SELECT,
                    "$expand": _FIELDS_EXPAND,
                    "$filter": filter_expression,
                },
            )
        }
        pages = 0

        while True:
            if pages >= MAX_PAGES:
                return RegistryFetchResult.unavailable()
            try:
                payload = self.client.get(path)
            except GraphBusinessCaseTypeHttpError as exc:
                return RegistryFetchResult.unavailable(_http_reason_code(exc.status))
            except GraphHttpError:
                return RegistryFetchResult.unavailable()
            except TimeoutError:
                return RegistryFetchResult.unavailable("transport_timeout")
            except Exception:
                return RegistryFetchResult.unavailable()
            pages += 1

            parsed_page = _parse_page(payload)
            if parsed_page is None:
                return RegistryFetchResult.unavailable()
            page_rows, next_link = parsed_page
            if len(rows) + len(page_rows) > MAX_ITEMS:
                return RegistryFetchResult.unavailable()
            rows.extend(page_rows)

            if next_link is None:
                break
            validated = _validated_next_link(next_link, collection_path, filter_expression)
            if validated is None:
                return RegistryFetchResult.unavailable()
            canonical_link, path = validated
            if canonical_link in visited_next_links:
                return RegistryFetchResult.unavailable()
            visited_next_links.add(canonical_link)

        if (
            len(rows) == 1
            and rows[0].business_case_type_id == business_case_type_id
            and rows[0].catalog_version == catalog_version
            and type(if_none_match) is str
            and bool(if_none_match)
            and rows[0].etag == if_none_match
        ):
            return RegistryFetchResult.not_modified()
        return RegistryFetchResult.ok(*rows, pages_complete=True)

    def _request_is_allowed(
        self,
        site_id: object,
        business_case_type_id: object,
        catalog_version: object,
    ) -> bool:
        try:
            return (
                self.scope.is_allowed()
                and type(self.client.base_url) is str
                and self.client.base_url == GRAPH_BASE_URL
                and self.client.redirects_allowed is False
                and self.client.retains_error_body is False
                and type(site_id) is str
                and site_id == self.scope.site_id
                and type(business_case_type_id) is str
                and bool(business_case_type_id)
                and type(catalog_version) is str
                and bool(catalog_version)
            )
        except Exception:
            return False


def _collection_path(site_id: str, list_id: str) -> str:
    site_segment = urllib.parse.quote(site_id, safe="")
    list_segment = urllib.parse.quote(list_id, safe="")
    return f"/sites/{site_segment}/lists/{list_segment}/items"


def _filter_expression(business_case_type_id: str, catalog_version: str) -> str:
    escaped_id = business_case_type_id.replace("'", "''")
    escaped_version = catalog_version.replace("'", "''")
    return (
        f"fields/BusinessCaseTypeId eq '{escaped_id}'"
        f" and fields/CatalogVersion eq '{escaped_version}'"
    )


def _initial_path(collection_path: str, filter_expression: str) -> str:
    encoded_filter = urllib.parse.quote(filter_expression, safe="/'")
    return (
        f"{collection_path}?$select={_ITEM_SELECT}"
        f"&$expand={_FIELDS_EXPAND}"
        f"&$filter={encoded_filter}"
    )


def _parse_page(
    payload: object,
) -> tuple[list[BusinessCaseTypeRegistryRow], str | None] | None:
    if type(payload) is not dict or type(payload.get("value")) is not list:
        return None
    if "@odata.nextLink" in payload and type(payload["@odata.nextLink"]) is not str:
        return None

    rows: list[BusinessCaseTypeRegistryRow] = []
    for item in payload["value"]:
        row = _parse_row(item)
        if row is None:
            return None
        rows.append(row)

    next_link = payload.get("@odata.nextLink")
    if next_link == "":
        return None
    return rows, next_link


def _parse_row(item: object) -> BusinessCaseTypeRegistryRow | None:
    if type(item) is not dict or type(item.get("fields")) is not dict:
        return None
    fields = item["fields"]
    values = (
        item.get("id"),
        item.get("eTag"),
        fields.get("BusinessCaseTypeId"),
        fields.get("LifecycleStatus"),
        fields.get("Selectable"),
        fields.get("CatalogVersion"),
    )
    item_id, etag, business_case_type_id, lifecycle_status, selectable, catalog_version = values
    if not (
        type(item_id) is str
        and bool(item_id)
        and type(etag) is str
        and bool(etag)
        and type(business_case_type_id) is str
        and bool(business_case_type_id)
        and type(lifecycle_status) is str
        and bool(lifecycle_status)
        and type(selectable) is bool
        and type(catalog_version) is str
        and bool(catalog_version)
    ):
        return None
    return BusinessCaseTypeRegistryRow(
        business_case_type_id=business_case_type_id,
        lifecycle_status=lifecycle_status,
        selectable=selectable,
        catalog_version=catalog_version,
        etag=etag,
    )


def _validated_next_link(
    next_link: str,
    collection_path: str,
    filter_expression: str,
) -> tuple[str, str] | None:
    try:
        parsed = urllib.parse.urlsplit(next_link)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "graph.microsoft.com"
            or parsed.fragment
            or not _same_collection(parsed.path, collection_path)
        ):
            return None
        pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
    except (TypeError, ValueError, UnicodeError):
        return None

    query: dict[str, str] = {}
    for key, value in pairs:
        if key in query:
            return None
        query[key] = value
    required = {
        "$select": _ITEM_SELECT,
        "$expand": _FIELDS_EXPAND,
        "$filter": filter_expression,
    }
    if any(query.get(key) != value for key, value in required.items()):
        return None
    if set(query) - set(required) - {"$skiptoken"}:
        return None
    if "$skiptoken" in query and not query["$skiptoken"]:
        return None

    canonical_query = urllib.parse.urlencode(sorted(query.items()), quote_via=urllib.parse.quote)
    canonical_link = _canonical_collection_url(collection_path, query)
    return canonical_link, f"{collection_path}?{canonical_query}"


def _canonical_collection_url(collection_path: str, query: dict[str, str]) -> str:
    canonical_query = urllib.parse.urlencode(sorted(query.items()), quote_via=urllib.parse.quote)
    return f"{GRAPH_BASE_URL}{collection_path}?{canonical_query}"


def _same_collection(candidate_path: str, collection_path: str) -> bool:
    candidate_parts = candidate_path.split("/")
    expected_parts = collection_path.split("/")
    if len(candidate_parts) != 7 or len(expected_parts) != 6:
        return False
    if candidate_parts[:3] != ["", "v1.0", "sites"]:
        return False
    if candidate_parts[4] != "lists" or candidate_parts[6] != "items":
        return False
    try:
        return (
            urllib.parse.unquote(candidate_parts[3], errors="strict")
            == urllib.parse.unquote(expected_parts[2], errors="strict")
            and urllib.parse.unquote(candidate_parts[5], errors="strict")
            == urllib.parse.unquote(expected_parts[4], errors="strict")
        )
    except (UnicodeDecodeError, ValueError):
        return False


def _http_reason_code(status: object) -> str:
    if status == 401:
        return "transport_authentication_failed"
    if status == 403:
        return "transport_authorization_failed"
    if status == 429:
        return "transport_rate_limited"
    if status in {408, 504}:
        return "transport_timeout"
    return "transport_unavailable"
