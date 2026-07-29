from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from typing import Callable, Literal, Mapping, Protocol
from urllib.parse import quote

from nac_runtime.azure_blob_worm import (
    AzureBlobContainerPolicy,
    AzureBlobObject,
    AzureBlobProviderContext,
    AzureBlobPutResult,
    AzureBlobVersionItem,
)


AZURE_MANAGEMENT_HOST = "management.azure.com"
AZURE_MANAGEMENT_API_VERSION = "2023-05-01"
AZURE_SUBSCRIPTION_API_VERSION = "2022-12-01"
AZURE_BLOB_API_VERSION = "2023-11-03"
MAX_RESPONSE_BYTES = 4 * 1024 * 1024

_PUBLIC_MANAGEMENT_ORIGIN = f"https://{AZURE_MANAGEMENT_HOST}"
_READBACK_SOURCE = "azure-subscription-resource-tenant-readback"
_LEGAL_HOLD_SOURCE = "container-policy-properties"
_KEY_SOURCE = "Microsoft.Keyvault"
_TENANT_ID = re.compile(
    r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\Z"
)
_SUBSCRIPTION_RESOURCE_ID = re.compile(
    r"/subscriptions/(?P<subscription>[0-9a-fA-F]{8}"
    r"-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})\Z"
)
_STORAGE_RESOURCE_ID = re.compile(
    r"(?P<subscription_resource>/subscriptions/[0-9a-fA-F]{8}"
    r"-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})"
    r"/resourceGroups/(?P<resource_group>[-A-Za-z0-9._()]{1,90})"
    r"/providers/Microsoft\.Storage/storageAccounts/"
    r"(?P<account>[a-z0-9]{3,24})\Z"
)
_AZURE_NAME = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])?\Z"
)
_BLOB_NAME = re.compile(
    r"tenant/[0-9a-f]{64}/journal/commit-v1-[0-9a-f]{32}\.json\Z"
)
_VERSION_ID = re.compile(r"[A-Za-z0-9._~:%+-]{1,256}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_METADATA_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,127}\Z")
_ETAG = re.compile(r'(?:W/)?"[^"\r\n]{1,1024}"\Z')
_ALLOWED_METHODS = frozenset({"GET", "PUT"})
_NO_BODY = frozenset({"GET"})


class AzureBlobAccessTokenProvider(Protocol):
    def fetch_access_token(self) -> str: ...


@dataclass(frozen=True, slots=True)
class AzureBlobHttpResponse:
    status_code: int
    body: bytes
    headers: Mapping[str, str] = field(default_factory=dict)


class AzureBlobHttpPort(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        follow_redirects: Literal[False],
        automatic_retries: Literal[0],
        max_response_bytes: int,
    ) -> AzureBlobHttpResponse: ...


@dataclass(frozen=True, slots=True)
class AzureBlobWormRestBinding:
    """Owner-bound public Azure target; no endpoint is accepted at call time."""

    management_host: str
    blob_host: str
    tenant_id: str
    subscription_resource_id: str
    storage_account_resource_id: str
    container_name: str
    encryption_scope: str
    customer_managed_key_ref_sha256: str

    def __post_init__(self) -> None:
        _validate_binding(self)


AzureBlobWormRestConfig = AzureBlobWormRestBinding


class AzureBlobWormRestTransportError(RuntimeError):
    """Stable failure without URLs, tokens, payloads, or provider bodies."""

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class AzureBlobWormRestTransport:
    """Strict Azure REST implementation of the read-only-policy WORM port."""

    def __init__(
        self,
        *,
        binding: AzureBlobWormRestBinding,
        management_token_provider: AzureBlobAccessTokenProvider,
        blob_token_provider: AzureBlobAccessTokenProvider,
        http_port: AzureBlobHttpPort,
        utc_now: Callable[[], datetime] | None = None,
    ) -> None:
        if type(binding) is not AzureBlobWormRestBinding:
            raise ValueError("azure_blob_worm_binding_invalid")
        _validate_binding(binding)
        if not callable(getattr(management_token_provider, "fetch_access_token", None)):
            raise ValueError("management_token_provider_invalid")
        if not callable(getattr(blob_token_provider, "fetch_access_token", None)):
            raise ValueError("blob_token_provider_invalid")
        if not callable(getattr(http_port, "request", None)):
            raise ValueError("http_port_invalid")
        if utc_now is not None and not callable(utc_now):
            raise ValueError("utc_now_invalid")
        self._binding = binding
        self._management_token_provider = management_token_provider
        self._blob_token_provider = blob_token_provider
        self._http_port = http_port
        self._utc_now = utc_now or (lambda: datetime.now(timezone.utc))

    def get_provider_context(
        self, container_name: str
    ) -> AzureBlobProviderContext:
        self._require_container(container_name)
        subscription = self._management_json(
            self._management_url(
                self._binding.subscription_resource_id,
                AZURE_SUBSCRIPTION_API_VERSION,
            )
        )
        storage = self._management_json(
            self._management_url(
                self._binding.storage_account_resource_id,
                AZURE_MANAGEMENT_API_VERSION,
            )
        )
        if (
            subscription.get("id")
            != self._binding.subscription_resource_id
            or subscription.get("subscriptionId")
            != self._subscription_id
            or subscription.get("tenantId") != self._binding.tenant_id
            or storage.get("id")
            != self._binding.storage_account_resource_id
            or storage.get("name") != self._storage_account
            or storage.get("type") != "Microsoft.Storage/storageAccounts"
        ):
            raise AzureBlobWormRestTransportError(
                "provider_context_readback_mismatch"
            )
        return AzureBlobProviderContext(
            tenant_id=self._binding.tenant_id,
            subscription_resource_id=self._binding.subscription_resource_id,
            resource_id=self._binding.storage_account_resource_id,
            readback_source=_READBACK_SOURCE,
        )

    def get_container_policy(
        self, container_name: str
    ) -> AzureBlobContainerPolicy:
        self._require_container(container_name)
        container_id = self._container_resource_id
        container = self._management_json(
            self._management_url(
                container_id,
                AZURE_MANAGEMENT_API_VERSION,
            )
        )
        policy_id = f"{container_id}/immutabilityPolicies/default"
        policy = self._management_json(
            self._management_url(
                policy_id,
                AZURE_MANAGEMENT_API_VERSION,
            )
        )
        scope_id = (
            f"{self._binding.storage_account_resource_id}"
            f"/encryptionScopes/{self._binding.encryption_scope}"
        )
        scope = self._management_json(
            self._management_url(
                scope_id,
                AZURE_MANAGEMENT_API_VERSION,
            )
        )
        container_properties = _object_field(container, "properties")
        policy_properties = _object_field(policy, "properties")
        scope_properties = _object_field(scope, "properties")
        immutable_storage = _object_field(
            container_properties, "immutableStorageWithVersioning"
        )
        legal_hold = _object_field(container_properties, "legalHold")
        key_vault = _object_field(scope_properties, "keyVaultProperties")
        key_identifier = key_vault.get("currentVersionedKeyIdentifier")
        retention_days = policy_properties.get(
            "immutabilityPeriodSinceCreationInDays"
        )
        etag = policy.get("etag")
        if (
            container.get("id") != container_id
            or container.get("type")
            != "Microsoft.Storage/storageAccounts/blobServices/containers"
            or immutable_storage.get("enabled") is not True
            or container_properties.get("defaultEncryptionScope")
            != self._binding.encryption_scope
            or container_properties.get("denyEncryptionScopeOverride")
            is not True
            or type(legal_hold.get("hasLegalHold")) is not bool
            or policy.get("id") != policy_id
            or policy_properties.get("state") != "Locked"
            or type(retention_days) is not int
            or retention_days <= 0
            or not _valid_etag(etag)
            or scope.get("id") != scope_id
            or scope.get("name") != self._binding.encryption_scope
            or scope_properties.get("state") != "Enabled"
            or scope_properties.get("source") != "Microsoft.KeyVault"
            or type(key_identifier) is not str
            or not _safe_text(key_identifier, maximum=4096)
            or hashlib.sha256(key_identifier.encode("utf-8")).hexdigest()
            != self._binding.customer_managed_key_ref_sha256
        ):
            raise AzureBlobWormRestTransportError(
                "container_policy_attestation_failed"
            )
        evidence = self._provider_context_evidence()
        return AzureBlobContainerPolicy(
            default_immutability_policy_mode="Locked",
            default_retention_days=retention_days,
            legal_hold_capable=True,
            legal_hold_capability_source=_LEGAL_HOLD_SOURCE,
            encryption_scope=self._binding.encryption_scope,
            encryption_key_source=_KEY_SOURCE,
            customer_managed_key_ref_sha256=(
                self._binding.customer_managed_key_ref_sha256
            ),
            **evidence,
        )

    def put_blob_if_absent(
        self,
        container_name: str,
        blob_name: str,
        body: bytes,
        metadata: Mapping[str, str],
        *,
        encryption_scope: str,
        if_none_match: str,
    ) -> AzureBlobPutResult:
        self._require_container(container_name)
        exact_blob_name = _validated_blob_name(blob_name)
        if (
            type(body) is not bytes
            or not body
            or len(body) > MAX_RESPONSE_BYTES
            or encryption_scope != self._binding.encryption_scope
            or if_none_match != "*"
        ):
            raise AzureBlobWormRestTransportError("blob_create_not_allowed")
        safe_metadata = _validated_metadata(metadata)
        headers = {
            "Accept": "application/xml",
            "Content-Length": str(len(body)),
            "Content-Type": "application/json",
            "If-None-Match": "*",
            "x-ms-blob-type": "BlockBlob",
            "x-ms-encryption-scope": self._binding.encryption_scope,
            **{
                f"x-ms-meta-{name.lower()}": value
                for name, value in sorted(safe_metadata.items())
            },
        }
        response = self._blob_request(
            method="PUT",
            url=self._blob_url(exact_blob_name),
            headers=headers,
            body=body,
        )
        if response.status_code == 412:
            return AzureBlobPutResult(
                status_code=412,
                etag=None,
                version_id=None,
            )
        if response.status_code != 201 or response.body:
            raise AzureBlobWormRestTransportError(
                "blob_create_response_invalid"
            )
        etag = _single_header(response.headers, "etag")
        version_id = _single_header(response.headers, "x-ms-version-id")
        if not _valid_etag(etag) or not _valid_version_id(version_id):
            raise AzureBlobWormRestTransportError(
                "blob_create_response_invalid"
            )
        return AzureBlobPutResult(
            status_code=201,
            etag=etag,
            version_id=version_id,
        )

    def list_blob_versions(
        self, container_name: str, blob_name: str
    ) -> tuple[AzureBlobVersionItem, ...]:
        self._require_container(container_name)
        exact_blob_name = _validated_blob_name(blob_name)
        query = (
            "restype=container&comp=list&include=versions&prefix="
            + quote(exact_blob_name, safe="")
        )
        response = self._blob_request(
            method="GET",
            url=f"{self._container_url}?{query}",
            headers={"Accept": "application/xml"},
            body=None,
        )
        if response.status_code != 200:
            raise AzureBlobWormRestTransportError(
                "blob_version_list_failed"
            )
        return _parse_version_list(response.body, exact_blob_name)

    def get_blob(
        self,
        container_name: str,
        blob_name: str,
        *,
        version_id: str,
    ) -> AzureBlobObject:
        self._require_container(container_name)
        exact_blob_name = _validated_blob_name(blob_name)
        exact_version_id = _validated_version_id(version_id)
        response = self._blob_request(
            method="GET",
            url=(
                f"{self._blob_url(exact_blob_name)}?versionid="
                f"{quote(exact_version_id, safe='')}"
            ),
            headers={"Accept": "application/octet-stream"},
            body=None,
        )
        if response.status_code != 200:
            raise AzureBlobWormRestTransportError("blob_readback_failed")
        headers = _normalized_headers(response.headers)
        response_version = _required_header(headers, "x-ms-version-id")
        etag = _required_header(headers, "etag")
        created_at = _azure_datetime(
            _required_header(headers, "x-ms-creation-time")
        )
        retention_until = _azure_datetime(
            _required_header(
                headers, "x-ms-immutability-policy-until-date"
            )
        )
        legal_hold = headers.get("x-ms-legal-hold", "false")
        if (
            response_version != exact_version_id
            or not _valid_etag(etag)
            or _required_header(headers, "x-ms-immutability-policy-mode")
            != "locked"
            or legal_hold not in {"true", "false"}
            or _required_header(headers, "x-ms-encryption-scope")
            != self._binding.encryption_scope
            or _required_header(headers, "x-ms-server-encrypted") != "true"
        ):
            raise AzureBlobWormRestTransportError(
                "blob_readback_attestation_failed"
            )
        metadata = {
            key.removeprefix("x-ms-meta-"): value
            for key, value in headers.items()
            if key.startswith("x-ms-meta-")
        }
        _validated_metadata(metadata)
        policy = self.get_container_policy(container_name)
        return AzureBlobObject(
            body=response.body,
            metadata=metadata,
            etag=etag,
            version_id=response_version,
            created_at=created_at,
            immutability_policy_mode="Locked",
            retention_until=retention_until,
            legal_hold_active=legal_hold == "true",
            encryption_scope=self._binding.encryption_scope,
            encryption_key_source=policy.encryption_key_source,
            customer_managed_key_ref_sha256=(
                policy.customer_managed_key_ref_sha256
            ),
        )

    @property
    def _subscription_id(self) -> str:
        match = _SUBSCRIPTION_RESOURCE_ID.fullmatch(
            self._binding.subscription_resource_id
        )
        assert match is not None
        return match.group("subscription")

    @property
    def _storage_account(self) -> str:
        match = _STORAGE_RESOURCE_ID.fullmatch(
            self._binding.storage_account_resource_id
        )
        assert match is not None
        return match.group("account")

    @property
    def _container_resource_id(self) -> str:
        return (
            f"{self._binding.storage_account_resource_id}"
            f"/blobServices/default/containers/{self._binding.container_name}"
        )

    @property
    def _container_url(self) -> str:
        return (
            f"https://{self._binding.blob_host}/"
            f"{self._binding.container_name}"
        )

    def _blob_url(self, blob_name: str) -> str:
        return (
            f"{self._container_url}/"
            f"{quote(blob_name, safe='/')}"
        )

    def _management_url(self, resource_id: str, api_version: str) -> str:
        return (
            f"{_PUBLIC_MANAGEMENT_ORIGIN}{resource_id}"
            f"?api-version={api_version}"
        )

    def _management_json(self, url: str) -> dict[str, object]:
        response = self._request(
            method="GET",
            url=url,
            headers={"Accept": "application/json"},
            body=None,
            token_provider=self._management_token_provider,
            service="management",
        )
        if response.status_code != 200:
            raise AzureBlobWormRestTransportError(
                "management_readback_failed"
            )
        return _json_object(response.body)

    def _blob_request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
    ) -> AzureBlobHttpResponse:
        return self._request(
            method=method,
            url=url,
            headers=headers,
            body=body,
            token_provider=self._blob_token_provider,
            service="blob",
        )

    def _request(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        token_provider: AzureBlobAccessTokenProvider,
        service: Literal["management", "blob"],
    ) -> AzureBlobHttpResponse:
        if method not in _ALLOWED_METHODS or (
            method in _NO_BODY and body is not None
        ):
            raise AzureBlobWormRestTransportError("request_not_allowed")
        token = _fetch_token(token_provider)
        outbound_headers: dict[str, str] = {
            "Authorization": f"Bearer {token}",
            **dict(headers),
        }
        if service == "blob":
            try:
                now = self._utc_now()
            except Exception:
                raise AzureBlobWormRestTransportError(
                    "clock_unavailable"
                ) from None
            if (
                type(now) is not datetime
                or now.tzinfo is None
                or now.utcoffset() is None
            ):
                raise AzureBlobWormRestTransportError("clock_unavailable")
            outbound_headers["x-ms-date"] = format_datetime(
                now.astimezone(timezone.utc), usegmt=True
            )
            outbound_headers["x-ms-version"] = AZURE_BLOB_API_VERSION
        failed = False
        response: object | None = None
        try:
            response = self._http_port.request(
                method=method,
                url=url,
                headers=outbound_headers,
                body=body,
                follow_redirects=False,
                automatic_retries=0,
                max_response_bytes=MAX_RESPONSE_BYTES,
            )
        except Exception:
            failed = True
        if failed:
            raise AzureBlobWormRestTransportError(
                "http_transport_unavailable"
            )
        if not isinstance(response, AzureBlobHttpResponse):
            raise AzureBlobWormRestTransportError("http_response_invalid")
        if (
            type(response.status_code) is not int
            or not 100 <= response.status_code <= 599
            or type(response.body) is not bytes
            or len(response.body) > MAX_RESPONSE_BYTES
        ):
            raise AzureBlobWormRestTransportError("http_response_invalid")
        _normalized_headers(response.headers)
        return response

    def _require_container(self, container_name: str) -> None:
        if container_name != self._binding.container_name:
            raise AzureBlobWormRestTransportError("request_not_allowed")

    def _provider_context_evidence(self) -> dict[str, str]:
        tenant_binding = _domain_hash(
            "nac.azure-provider-tenant.v1", self._binding.tenant_id
        )
        subscription_binding = _domain_hash(
            "nac.azure-subscription-resource.v1",
            self._binding.subscription_resource_id,
        )
        resource_binding = _domain_hash(
            "nac.azure-storage-resource.v1",
            self._binding.storage_account_resource_id,
        )
        context_binding = hashlib.sha256(
            (
                "nac.azure-provider-context.v1|"
                f"{tenant_binding}|{subscription_binding}|{resource_binding}"
            ).encode("ascii")
        ).hexdigest()
        return {
            "provider_tenant_binding_sha256": tenant_binding,
            "provider_subscription_binding_sha256": subscription_binding,
            "provider_resource_binding_sha256": resource_binding,
            "provider_context_binding_sha256": context_binding,
            "provider_context_binding_source": _READBACK_SOURCE,
        }


def _validate_binding(binding: AzureBlobWormRestBinding) -> None:
    subscription = _SUBSCRIPTION_RESOURCE_ID.fullmatch(
        binding.subscription_resource_id
    ) if type(binding.subscription_resource_id) is str else None
    storage = _STORAGE_RESOURCE_ID.fullmatch(
        binding.storage_account_resource_id
    ) if type(binding.storage_account_resource_id) is str else None
    if (
        binding.management_host != AZURE_MANAGEMENT_HOST
        or storage is None
        or subscription is None
        or storage.group("subscription_resource")
        != binding.subscription_resource_id
        or binding.blob_host
        != f"{storage.group('account')}.blob.core.windows.net"
        or type(binding.tenant_id) is not str
        or _TENANT_ID.fullmatch(binding.tenant_id) is None
        or type(binding.container_name) is not str
        or _AZURE_NAME.fullmatch(binding.container_name) is None
        or type(binding.encryption_scope) is not str
        or _AZURE_NAME.fullmatch(binding.encryption_scope) is None
        or type(binding.customer_managed_key_ref_sha256) is not str
        or _SHA256.fullmatch(
            binding.customer_managed_key_ref_sha256
        ) is None
    ):
        raise ValueError("azure_blob_worm_binding_invalid")


def _validated_blob_name(value: object) -> str:
    if type(value) is not str or _BLOB_NAME.fullmatch(value) is None:
        raise AzureBlobWormRestTransportError("request_not_allowed")
    return value


def _validated_version_id(value: object) -> str:
    if not _valid_version_id(value):
        raise AzureBlobWormRestTransportError("request_not_allowed")
    assert isinstance(value, str)
    return value


def _valid_version_id(value: object) -> bool:
    return type(value) is str and _VERSION_ID.fullmatch(value) is not None


def _validated_metadata(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping):
        raise AzureBlobWormRestTransportError("blob_metadata_invalid")
    try:
        items = tuple(value.items())
    except Exception:
        raise AzureBlobWormRestTransportError(
            "blob_metadata_invalid"
        ) from None
    result: dict[str, str] = {}
    for key, item in items:
        lowered = key.lower() if type(key) is str else ""
        if (
            type(key) is not str
            or _METADATA_NAME.fullmatch(key) is None
            or lowered in result
            or type(item) is not str
            or not _safe_text(item, maximum=2048)
        ):
            raise AzureBlobWormRestTransportError(
                "blob_metadata_invalid"
            )
        result[lowered] = item
    if len(result) > 64:
        raise AzureBlobWormRestTransportError("blob_metadata_invalid")
    return result


def _fetch_token(provider: AzureBlobAccessTokenProvider) -> str:
    failed = False
    token: object | None = None
    try:
        token = provider.fetch_access_token()
    except Exception:
        failed = True
    if (
        failed
        or type(token) is not str
        or not _safe_text(token, maximum=16_384)
        or any(char.isspace() for char in token)
    ):
        raise AzureBlobWormRestTransportError("access_token_unavailable")
    return token


def _normalized_headers(headers: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(headers, Mapping):
        raise AzureBlobWormRestTransportError("http_response_invalid")
    try:
        items = tuple(headers.items())
    except Exception:
        raise AzureBlobWormRestTransportError(
            "http_response_invalid"
        ) from None
    result: dict[str, str] = {}
    for key, value in items:
        lowered = key.lower() if type(key) is str else ""
        if (
            type(key) is not str
            or type(value) is not str
            or lowered in result
            or not _safe_text(value, maximum=16_384)
        ):
            raise AzureBlobWormRestTransportError(
                "http_response_invalid"
            )
        result[lowered] = value
    return result


def _single_header(headers: Mapping[str, str], name: str) -> str | None:
    return _normalized_headers(headers).get(name)


def _required_header(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name)
    if value is None:
        raise AzureBlobWormRestTransportError("http_response_invalid")
    return value


def _valid_etag(value: object) -> bool:
    return type(value) is str and _ETAG.fullmatch(value) is not None


def _safe_text(value: str, *, maximum: int) -> bool:
    return bool(
        value
        and len(value) <= maximum
        and all(ord(char) >= 0x20 and ord(char) != 0x7F for char in value)
    )


def _json_object(body: bytes) -> dict[str, object]:
    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    try:
        value = json.loads(
            body.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=lambda _value: (_ for _ in ()).throw(ValueError()),
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        RecursionError,
    ):
        raise AzureBlobWormRestTransportError(
            "management_response_invalid"
        ) from None
    if type(value) is not dict:
        raise AzureBlobWormRestTransportError(
            "management_response_invalid"
        )
    return value


def _object_field(
    value: Mapping[str, object], field_name: str
) -> Mapping[str, object]:
    field = value.get(field_name)
    if type(field) is not dict:
        raise AzureBlobWormRestTransportError(
            "management_response_invalid"
        )
    return field


def _parse_version_list(
    body: bytes, expected_blob_name: str
) -> tuple[AzureBlobVersionItem, ...]:
    if not body or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        raise AzureBlobWormRestTransportError(
            "blob_version_list_invalid"
        )
    try:
        root = ElementTree.fromstring(body)
    except (ElementTree.ParseError, RecursionError, ValueError):
        raise AzureBlobWormRestTransportError(
            "blob_version_list_invalid"
        ) from None
    if root.tag != "EnumerationResults":
        raise AzureBlobWormRestTransportError(
            "blob_version_list_invalid"
        )
    next_marker = root.findtext("NextMarker")
    if next_marker not in {None, ""}:
        raise AzureBlobWormRestTransportError(
            "blob_version_list_incomplete"
        )
    versions: list[AzureBlobVersionItem] = []
    seen: set[str] = set()
    blobs = root.find("Blobs")
    if blobs is None:
        raise AzureBlobWormRestTransportError(
            "blob_version_list_invalid"
        )
    for blob in blobs.findall("Blob"):
        if blob.findtext("Name") != expected_blob_name:
            raise AzureBlobWormRestTransportError(
                "blob_version_list_invalid"
            )
        version_id = blob.findtext("VersionId")
        if not _valid_version_id(version_id) or version_id in seen:
            raise AzureBlobWormRestTransportError(
                "blob_version_list_invalid"
            )
        assert version_id is not None
        seen.add(version_id)
        versions.append(AzureBlobVersionItem(version_id=version_id))
    return tuple(versions)


def _azure_datetime(value: str) -> str:
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        raise AzureBlobWormRestTransportError(
            "blob_readback_attestation_failed"
        ) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AzureBlobWormRestTransportError(
            "blob_readback_attestation_failed"
        )
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _domain_hash(domain: str, value: str) -> str:
    return hashlib.sha256(f"{domain}|{value}".encode("ascii")).hexdigest()
