from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Callable, ClassVar, Iterator, Mapping
from uuid import UUID

from .azure_performance_authorization import (
    BLOB_BOOTSTRAP,
    BLOB_LEASE_ACQUIRE,
    BLOB_LEASE_ASSERT_HELD,
    BLOB_LEASE_RELEASE,
    PerformanceLiveAuthorizationError,
    SecurePerformancePathError,
    VerifiedLiveActionCapability,
    _authorize_live_action,
    _open_root_anchored_private_parent,
)
from .azure_performance_infrastructure_safety import (
    validate_infrastructure_safety_evidence,
)


_API_VERSION = "2023-11-03"
_CONTAINER_NAME = "nac-bff-performance-leases"
_TOKEN_AUDIENCE = "https://storage.azure.com/.default"
_STATE_SCHEMA = "nac.azure-blob-performance-lease-state/v1"
_ACQUISITION_SAFETY_SCHEMA = "nac.azure-blob-performance-lease-acquisition-safety/v1"
_ACCOUNT_RE = re.compile(r"[a-z0-9]{3,24}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_STORAGE_ACCOUNT_RESOURCE_ID_RE = re.compile(
    r"^/subscriptions/[^/]+/resourceGroups/[^/]+/providers/"
    r"Microsoft\.Storage/storageAccounts/(?P<name>[a-z0-9]{3,24})$",
    re.IGNORECASE,
)
_MAX_STATE_BYTES = 16 * 1024
_TIMEOUT_SECONDS = 30
_INFRASTRUCTURE_SAFETY_MAX_AGE = timedelta(minutes=5)
_INFRASTRUCTURE_SAFETY_MAX_FUTURE_SKEW = timedelta(seconds=30)
_BOOTSTRAP_EXISTING_RESPONSES = frozenset(
    {
        (409, "BlobAlreadyExists"),
        (412, "ConditionNotMet"),
    }
)
_AZURE_STORAGE_TOKEN_ATTESTATION_SEAL = object()

_ACQUIRE_INTENT = "ACQUIRE_INTENT"
_ACQUIRE_IN_FLIGHT = "ACQUIRE_IN_FLIGHT"
_HELD = "HELD"
_RELEASE_INTENT = "RELEASE_INTENT"
_RELEASED = "RELEASED"
_STATES = frozenset(
    {_ACQUIRE_INTENT, _ACQUIRE_IN_FLIGHT, _HELD, _RELEASE_INTENT, _RELEASED}
)


class AzureBlobLeaseError(RuntimeError):
    """Stable, redacted failure at the performance lease boundary."""


class AttestedAzureStorageAccessToken:
    """Opaque provider result bound to one exact storage identity request."""

    __slots__ = (
        "_seal",
        "expires_at",
        "identity_binding_sha256",
        "not_before",
        "scope",
        "source_attestation_sha256",
        "subject",
        "tenant_id",
        "token",
    )

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise TypeError("attested Azure storage tokens cannot be constructed")

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, "_seal"):
            raise AttributeError("attested Azure storage tokens are immutable")
        object.__setattr__(self, name, value)


def _issue_attested_azure_storage_access_token(
    token: str,
    *,
    scope: str,
    identity_binding_sha256: str,
    subject: str,
    tenant_id: str,
    not_before: int | float,
    expires_at: int | float,
    source_attestation_sha256: str,
) -> AttestedAzureStorageAccessToken:
    result = object.__new__(AttestedAzureStorageAccessToken)
    result.token = token
    result.scope = scope
    result.identity_binding_sha256 = identity_binding_sha256
    result.subject = subject
    result.tenant_id = tenant_id
    result.not_before = not_before
    result.expires_at = expires_at
    result.source_attestation_sha256 = source_attestation_sha256
    result._seal = _AZURE_STORAGE_TOKEN_ATTESTATION_SEAL
    return result


def lease_policy() -> dict[str, Any]:
    """Return the immutable operation boundary for the dedicated lock blob."""

    return {
        "api_version": _API_VERSION,
        "container_name": _CONTAINER_NAME,
        "token_audience": _TOKEN_AUDIENCE,
        "lease_duration": -1,
        "allowed_operations": ["acquire", "assert_held", "release"],
        "forbidden_operations": ["break", "change", "create", "delete", "renew"],
        "lifecycle_states": [
            _ACQUIRE_INTENT,
            _ACQUIRE_IN_FLIGHT,
            _HELD,
            _RELEASE_INTENT,
            _RELEASED,
        ],
        "release_reconciliation_attempts_maximum": 1,
        "acquisition_safety_evidence_required": True,
        "acquisition_bindings": [
            "owner_approval_body_sha256",
            "lease_binding_sha256",
            "coordination_storage_account_resource_id",
            "expected_etag",
            "token_subject_oid",
            "token_tenant_id",
            "target_binding_sha256",
        ],
        "infrastructure_safety_max_age_seconds": int(
            _INFRASTRUCTURE_SAFETY_MAX_AGE.total_seconds()
        ),
        "token_tenant_binding_required": True,
        "passed_state_requires": _RELEASED,
        "redirects_followed": 0,
        "client_retries": 0,
    }


def lease_policy_sha256() -> str:
    return _sha256_json(lease_policy())


def lease_bootstrap_policy() -> dict[str, Any]:
    """Return the one-shot policy that creates or reads the exact lock blob."""

    return {
        "api_version": _API_VERSION,
        "container_name": _CONTAINER_NAME,
        "token_audience": _TOKEN_AUDIENCE,
        "allowed_operations": ["put_blob_if_absent", "head_blob"],
        "forbidden_operations": [
            "delete",
            "overwrite",
            "lease_break",
            "lease_change",
            "lease_renew",
        ],
        "put_precondition": "If-None-Match:*",
        "blob_type": "BlockBlob",
        "content_length": 0,
        "created_response_status": 201,
        "existing_blob_responses": [
            {"error_code": "BlobAlreadyExists", "status": 409},
            {"error_code": "ConditionNotMet", "status": 412},
        ],
        "redirects_followed": 0,
        "client_retries": 0,
        "strong_etag_readback_required": True,
        "infrastructure_safety_evidence_required": True,
        "infrastructure_safety_max_age_seconds": int(
            _INFRASTRUCTURE_SAFETY_MAX_AGE.total_seconds()
        ),
        "owner_principal_tenant_resource_target_binding_required": True,
        "token_subject_and_tenant_validation_required": True,
        "distinct_bootstrap_runtime_identity_bindings_required": True,
        "runtime_binding_handoff_required": True,
        "binding_source": "independent_head_readback",
        "enforcement_boundary": "sealed_application_api_defense_in_depth",
        "azure_rbac_write_operation_filtering": False,
    }


def lease_bootstrap_policy_sha256() -> str:
    return _sha256_json(lease_bootstrap_policy())


@dataclass(frozen=True)
class AzureBlobLeaseBootstrapBinding:
    """Inputs known before the dedicated coordination blob exists."""

    account_name: str
    bff_account_name: str
    worm_account_name: str
    coordination_storage_account_resource_id: str
    owner_approval_body_sha256: str
    token_subject: str
    token_tenant_id: str
    target_binding_sha256: str
    read_identity_binding_sha256: str
    write_identity_binding_sha256: str
    runtime_token_subject: str
    runtime_read_identity_binding_sha256: str
    runtime_write_identity_binding_sha256: str

    def __post_init__(self) -> None:
        accounts = (
            self.account_name,
            self.bff_account_name,
            self.worm_account_name,
        )
        if (
            any(
                not isinstance(value, str) or _ACCOUNT_RE.fullmatch(value) is None
                for value in accounts
            )
            or len(set(accounts)) != 3
            or _storage_account_name_from_resource_id(
                self.coordination_storage_account_resource_id
            )
            != self.account_name
            or not _is_sha256(self.owner_approval_body_sha256)
            or _canonical_uuid(self.token_subject) is None
            or _canonical_uuid(self.token_tenant_id) is None
            or not _is_sha256(self.target_binding_sha256)
            or not _is_sha256(self.read_identity_binding_sha256)
            or not _is_sha256(self.write_identity_binding_sha256)
            or _canonical_uuid(self.runtime_token_subject) is None
            or _canonical_uuid(self.runtime_token_subject)
            == _canonical_uuid(self.token_subject)
            or not _is_sha256(self.runtime_read_identity_binding_sha256)
            or not _is_sha256(self.runtime_write_identity_binding_sha256)
            or len(
                {
                    self.read_identity_binding_sha256,
                    self.write_identity_binding_sha256,
                    self.runtime_read_identity_binding_sha256,
                    self.runtime_write_identity_binding_sha256,
                }
            )
            != 4
        ):
            raise ValueError("AZURE_BLOB_LEASE_BOOTSTRAP_BINDING_INVALID")


@dataclass(frozen=True)
class AzureBlobLeaseBinding:
    """Immutable binding for the one pre-provisioned performance lock blob."""

    account_name: str
    bff_account_name: str
    worm_account_name: str
    coordination_storage_account_resource_id: str
    owner_approval_body_sha256: str
    token_subject: str
    token_tenant_id: str
    target_binding_sha256: str
    expected_etag: str
    read_identity_binding_sha256: str
    write_identity_binding_sha256: str

    api_version: ClassVar[str] = _API_VERSION
    container_name: ClassVar[str] = _CONTAINER_NAME
    token_audience: ClassVar[str] = _TOKEN_AUDIENCE

    def __post_init__(self) -> None:
        accounts = (
            self.account_name,
            self.bff_account_name,
            self.worm_account_name,
        )
        if (
            any(
                not isinstance(value, str) or _ACCOUNT_RE.fullmatch(value) is None
                for value in accounts
            )
            or self.account_name
            in {self.bff_account_name, self.worm_account_name}
            or _storage_account_name_from_resource_id(
                self.coordination_storage_account_resource_id
            )
            != self.account_name
            or not _is_sha256(self.owner_approval_body_sha256)
            or _canonical_uuid(self.token_subject) is None
            or _canonical_uuid(self.token_tenant_id) is None
            or not _is_sha256(self.target_binding_sha256)
            or not _is_sha256(self.read_identity_binding_sha256)
            or not _is_sha256(self.write_identity_binding_sha256)
            or not _valid_etag(self.expected_etag)
        ):
            raise ValueError("AZURE_BLOB_LEASE_BINDING_INVALID")


def build_lease_acquisition_safety_evidence(
    *,
    binding: AzureBlobLeaseBinding,
    infrastructure_safety_evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Cross-bind the post-bootstrap lease to validated infrastructure safety."""

    if not isinstance(binding, AzureBlobLeaseBinding):
        raise TypeError("binding")
    try:
        infrastructure = validate_infrastructure_safety_evidence(
            infrastructure_safety_evidence
        )
    except Exception:
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID"
        ) from None
    payload = {
        "schema_version": _ACQUISITION_SAFETY_SCHEMA,
        "status": "SAFE",
        "infrastructure_safety_evidence": infrastructure,
        "infrastructure_safety_evidence_sha256": infrastructure[
            "infrastructure_safety_evidence_sha256"
        ],
        "lease_binding_sha256": _binding_sha256(binding),
        "owner_approval_body_sha256": binding.owner_approval_body_sha256,
        "coordination_storage_account_resource_id": (
            binding.coordination_storage_account_resource_id
        ),
        "expected_etag": binding.expected_etag,
        "token_subject": str(UUID(binding.token_subject)),
        "token_tenant_id": str(UUID(binding.token_tenant_id)),
        "target_binding_sha256": binding.target_binding_sha256,
    }
    payload["lease_acquisition_safety_evidence_sha256"] = _sha256_json(payload)
    return _validated_lease_acquisition_safety_evidence(payload, binding=binding)


@dataclass(frozen=True)
class AzureBlobLeaseReceipt:
    """Redacted receipt with an explicit, independently checkable lifecycle."""

    lease_binding_sha256: str
    target_binding_sha256: str
    lease_id_sha256: str
    read_identity_binding_sha256: str
    write_identity_binding_sha256: str
    lifecycle_state: str
    lifecycle_state_sha256: str

    def __post_init__(self) -> None:
        digests = (
            self.lease_binding_sha256,
            self.target_binding_sha256,
            self.lease_id_sha256,
            self.read_identity_binding_sha256,
            self.write_identity_binding_sha256,
            self.lifecycle_state_sha256,
        )
        if (
            any(not _is_sha256(value) for value in digests)
            or self.lifecycle_state not in _STATES
        ):
            raise ValueError("AZURE_BLOB_LEASE_RECEIPT_INVALID")


@dataclass(frozen=True)
class _HttpResult:
    status: int
    headers: Mapping[str, str]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class _PrivateLifecycleStore:
    def __init__(self, path: Path) -> None:
        if not isinstance(path, Path) or path.name in {"", ".", ".."}:
            raise ValueError("AZURE_BLOB_LEASE_STATE_PATH_INVALID")
        self._path = path
        self._state_name = path.name
        self._lock_name = f".{path.name}.lock"
        self._run_lock_name = f".{path.name}.run.lock"
        self._directory_identity: tuple[int, int] | None = None
        directory = self._open_private_parent()
        os.close(directory)

    @contextmanager
    def run_locked(self) -> Iterator[None]:
        """Fence the complete measurement/finalization lifecycle per state path."""

        directory = -1
        descriptor = -1
        try:
            directory = self._open_private_parent()
            descriptor = os.open(
                self._run_lock_name,
                os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            self._validate_named_file(directory, self._run_lock_name, descriptor)
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._validate_named_file(directory, self._run_lock_name, descriptor)
        except BlockingIOError:
            if descriptor >= 0:
                os.close(descriptor)
            if directory >= 0:
                os.close(directory)
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_CONCURRENT_RUN") from None
        except OSError:
            if descriptor >= 0:
                os.close(descriptor)
            if directory >= 0:
                os.close(directory)
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None
        try:
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
                os.close(directory)

    @contextmanager
    def locked(self) -> Iterator[int]:
        directory = -1
        descriptor = -1
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
        try:
            directory = self._open_private_parent()
            descriptor = os.open(
                self._lock_name, flags, 0o600, dir_fd=directory
            )
            self._validate_named_file(directory, self._lock_name, descriptor)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            self._validate_named_file(directory, self._lock_name, descriptor)
        except OSError:
            if descriptor >= 0:
                os.close(descriptor)
            if directory >= 0:
                os.close(directory)
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None
        try:
            yield directory
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)
                os.close(directory)

    def load(self, directory: int) -> dict[str, Any] | None:
        try:
            self._validate_directory_descriptor(directory)
            descriptor = os.open(
                self._state_name,
                os.O_RDONLY | os.O_NOFOLLOW,
                dir_fd=directory,
            )
        except FileNotFoundError:
            return None
        except OSError:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None
        try:
            self._validate_named_file(directory, self._state_name, descriptor)
            metadata = os.fstat(descriptor)
            if metadata.st_size > _MAX_STATE_BYTES:
                raise ValueError
            with os.fdopen(descriptor, "r", encoding="ascii") as stream:
                descriptor = -1
                value = json.load(stream)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        return _validated_envelope(value)

    def save(self, payload: Mapping[str, Any], directory: int) -> None:
        validated = _validated_payload(dict(payload))
        envelope = {
            "payload": validated,
            "payload_sha256": _sha256_json(validated),
            "schema_version": _STATE_SCHEMA,
        }
        encoded = (_canonical_json(envelope) + "\n").encode("ascii")
        if len(encoded) > _MAX_STATE_BYTES:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")
        temporary = (
            f".{self._state_name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
        )
        descriptor = -1
        try:
            self._validate_directory_descriptor(directory)
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=directory,
            )
            self._validate_named_file(directory, temporary, descriptor)
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            self._validate_directory_descriptor(directory)
            os.replace(
                temporary,
                self._state_name,
                src_dir_fd=directory,
                dst_dir_fd=directory,
            )
            self._validate_directory_descriptor(directory)
            os.fsync(directory)
        except OSError:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_UNAVAILABLE") from None
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                os.unlink(temporary, dir_fd=directory)
            except FileNotFoundError:
                pass
            except OSError:
                pass

    def _open_private_parent(self) -> int:
        descriptor = -1
        try:
            opened = _open_root_anchored_private_parent(
                self._path, create=True
            )
            if opened is None:
                raise OSError
            descriptor = opened
            self._validate_directory_descriptor(descriptor, pin=True)
            return descriptor
        except (OSError, SecurePerformancePathError):
            if descriptor >= 0:
                os.close(descriptor)
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None

    def _validate_directory_descriptor(
        self, descriptor: int, *, pin: bool = False
    ) -> None:
        metadata = os.fstat(descriptor)
        path_metadata = self._path.parent.lstat()
        identity = (metadata.st_dev, metadata.st_ino)
        if (
            not _private_directory(metadata)
            or stat.S_ISLNK(path_metadata.st_mode)
            or not _private_directory(path_metadata)
            or identity != (path_metadata.st_dev, path_metadata.st_ino)
            or (
                self._directory_identity is not None
                and identity != self._directory_identity
            )
        ):
            raise OSError
        if pin and self._directory_identity is None:
            self._directory_identity = identity

    def _validate_named_file(
        self, directory: int, name: str, descriptor: int
    ) -> None:
        self._validate_directory_descriptor(directory)
        metadata = os.fstat(descriptor)
        path_metadata = os.stat(name, dir_fd=directory, follow_symlinks=False)
        if (
            not _private_regular_file(metadata)
            or not _private_regular_file(path_metadata)
            or (metadata.st_dev, metadata.st_ino)
            != (path_metadata.st_dev, path_metadata.st_ino)
        ):
            raise OSError


class AzureBlobLeaseBootstrapAdapter:
    """Create the exact zero-byte lock blob once and return its strong ETag."""

    def __init__(
        self,
        *,
        binding: AzureBlobLeaseBootstrapBinding,
        infrastructure_safety_evidence: Mapping[str, Any],
        token_provider: Callable[..., str] | Any,
        opener: Any | None = None,
        clock: Callable[[], datetime] | None = None,
        _test_live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> None:
        if not isinstance(binding, AzureBlobLeaseBootstrapBinding):
            raise TypeError("binding")
        provider = token_provider
        if not callable(provider):
            provider = getattr(token_provider, "get_token", None)
        if not callable(provider):
            raise TypeError("token_provider")
        selected_opener = opener or urllib.request.build_opener(_NoRedirect())
        if not callable(getattr(selected_opener, "open", None)):
            raise TypeError("opener")
        if clock is not None and not callable(clock):
            raise TypeError("clock")
        self._binding = binding
        self._infrastructure_safety_evidence = (
            _validated_bootstrap_infrastructure_safety_evidence(
                infrastructure_safety_evidence,
                binding=binding,
            )
        )
        self._token_provider = provider
        self._opener = selected_opener
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._test_live_action_capability = _test_live_action_capability
        self._binding_sha256 = _bootstrap_binding_sha256(binding)
        self._blob_url = (
            f"https://{binding.account_name}.blob.core.windows.net/"
            f"{_CONTAINER_NAME}/locks/{binding.target_binding_sha256}.lock"
        )

    @property
    def bootstrap_binding_sha256(self) -> str:
        return self._binding_sha256

    def bootstrap(
        self,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> AzureBlobLeaseBinding:
        capability = live_action_capability or self._test_live_action_capability
        self._authorize_capability(capability, consume=False)
        headers = self._headers(
            self._binding.write_identity_binding_sha256,
            capability,
        )
        headers.update(
            {
                "Content-Length": "0",
                "If-None-Match": "*",
                "x-ms-blob-type": "BlockBlob",
            }
        )
        result = self._request("PUT", headers, b"")
        created_etag: str | None = None
        if result.status == 201:
            created_etag = self._validate_blob_response(result)
        elif result.status in {409, 412}:
            conflict = (result.status, _header(result.headers, "x-ms-error-code"))
            if conflict not in _BOOTSTRAP_EXISTING_RESPONSES:
                raise AzureBlobLeaseError(
                    "AZURE_BLOB_LEASE_BOOTSTRAP_RESPONSE_INVALID"
                )
        else:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BOOTSTRAP_FAILED")
        etag = self._read_existing(capability)
        if created_etag is not None and etag != created_etag:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BOOTSTRAP_DRIFT")
        return AzureBlobLeaseBinding(
            account_name=self._binding.account_name,
            bff_account_name=self._binding.bff_account_name,
            worm_account_name=self._binding.worm_account_name,
            coordination_storage_account_resource_id=(
                self._binding.coordination_storage_account_resource_id
            ),
            owner_approval_body_sha256=(
                self._binding.owner_approval_body_sha256
            ),
            token_subject=self._binding.runtime_token_subject,
            token_tenant_id=self._binding.token_tenant_id,
            target_binding_sha256=self._binding.target_binding_sha256,
            expected_etag=etag,
            read_identity_binding_sha256=(
                self._binding.runtime_read_identity_binding_sha256
            ),
            write_identity_binding_sha256=(
                self._binding.runtime_write_identity_binding_sha256
            ),
        )

    def _read_existing(self, capability: VerifiedLiveActionCapability) -> str:
        result = self._request(
            "HEAD",
            self._headers(
                self._binding.read_identity_binding_sha256,
                capability,
            ),
            None,
        )
        if result.status != 200:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BOOTSTRAP_FAILED")
        if (
            _header(result.headers, "content-length") != "0"
            or _header(result.headers, "x-ms-blob-type") != "BlockBlob"
        ):
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BOOTSTRAP_DRIFT")
        return self._validate_blob_response(result)

    def _headers(
        self,
        identity_binding_sha256: str,
        capability: VerifiedLiveActionCapability,
    ) -> dict[str, str]:
        try:
            self._authorize_capability(capability, consume=True)
            self._require_current_infrastructure_safety()
            token_result = self._token_provider(
                audience=_TOKEN_AUDIENCE,
                identity_binding_sha256=identity_binding_sha256,
            )
            now = self._require_current_infrastructure_safety()
            token = _validated_access_token(
                token_result,
                now=now,
                expected_identity_binding_sha256=identity_binding_sha256,
                expected_subject=self._binding.token_subject,
                expected_tenant=self._binding.token_tenant_id,
                invalid_code="AZURE_BLOB_LEASE_BOOTSTRAP_TOKEN_INVALID",
                subject_code=(
                    "AZURE_BLOB_LEASE_BOOTSTRAP_TOKEN_SUBJECT_MISMATCH"
                ),
                tenant_code="AZURE_BLOB_LEASE_BOOTSTRAP_TOKEN_TENANT_MISMATCH",
            )
            request_date = format_datetime(now.astimezone(timezone.utc), usegmt=True)
        except AzureBlobLeaseError:
            raise
        except Exception:
            raise AzureBlobLeaseError(
                "AZURE_BLOB_LEASE_BOOTSTRAP_AUTH_UNAVAILABLE"
            ) from None
        return {
            "Authorization": f"Bearer {token}",
            "x-ms-date": request_date,
            "x-ms-version": _API_VERSION,
        }

    def _request(
        self,
        method: str,
        headers: Mapping[str, str],
        body: bytes | None,
    ) -> _HttpResult:
        request = urllib.request.Request(
            self._blob_url,
            data=body,
            headers=dict(headers),
            method=method,
        )
        try:
            if method == "PUT":
                self._require_current_infrastructure_safety()
            response = self._opener.open(request, timeout=_TIMEOUT_SECONDS)
            with response:
                result = AzureBlobLeaseAdapter._result_from_response(
                    response, self._blob_url
                )
                if 200 <= result.status < 300 and response.read(1) != b"":
                    raise AzureBlobLeaseError(
                        "AZURE_BLOB_LEASE_BOOTSTRAP_RESPONSE_INVALID"
                    )
                return result
        except urllib.error.HTTPError as error:
            try:
                return AzureBlobLeaseAdapter._result_from_response(
                    error, self._blob_url
                )
            finally:
                error.close()
        except AzureBlobLeaseError:
            raise
        except Exception:
            raise AzureBlobLeaseError(
                "AZURE_BLOB_LEASE_BOOTSTRAP_TRANSPORT_UNAVAILABLE"
            ) from None

    def _authorize_capability(
        self,
        capability: object,
        *,
        consume: bool,
    ) -> None:
        _authorize_blob_capability(
            capability,
            action=BLOB_BOOTSTRAP,
            target_binding_sha256=self._binding.target_binding_sha256,
            binding_sha256=self._binding_sha256,
            consume=consume,
        )

    def _require_current_infrastructure_safety(self) -> datetime:
        try:
            now = self._clock()
            if not isinstance(now, datetime) or now.tzinfo is None:
                raise ValueError
            _require_current_infrastructure_safety(
                self._infrastructure_safety_evidence,
                now=now,
            )
            return now
        except AzureBlobLeaseError:
            raise
        except Exception:
            raise AzureBlobLeaseError(
                "AZURE_BLOB_LEASE_BOOTSTRAP_AUTH_UNAVAILABLE"
            ) from None

    @staticmethod
    def _validate_blob_response(result: _HttpResult) -> str:
        etag = _header(result.headers, "etag")
        if (
            _header(result.headers, "x-ms-version") != _API_VERSION
            or not _valid_etag(etag)
        ):
            raise AzureBlobLeaseError(
                "AZURE_BLOB_LEASE_BOOTSTRAP_RESPONSE_INVALID"
            )
        return etag


class AzureBlobLeaseAdapter:
    """Direct Blob REST adapter with no redirect, retry, or blob-create path."""

    def __init__(
        self,
        *,
        binding: AzureBlobLeaseBinding,
        acquisition_safety_evidence: Mapping[str, Any],
        state_path: Path,
        token_provider: Callable[..., str] | Any,
        opener: Any | None = None,
        clock: Callable[[], datetime] | None = None,
        _test_live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> None:
        if not isinstance(binding, AzureBlobLeaseBinding):
            raise TypeError("binding")
        provider = token_provider
        if not callable(provider):
            provider = getattr(token_provider, "get_token", None)
        if not callable(provider):
            raise TypeError("token_provider")
        selected_opener = opener or urllib.request.build_opener(_NoRedirect())
        if not callable(getattr(selected_opener, "open", None)):
            raise TypeError("opener")
        if clock is not None and not callable(clock):
            raise TypeError("clock")
        self._binding = binding
        self._acquisition_safety_evidence = (
            _validated_lease_acquisition_safety_evidence(
                acquisition_safety_evidence,
                binding=binding,
            )
        )
        self._store = _PrivateLifecycleStore(state_path)
        self._token_provider = provider
        self._opener = selected_opener
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._test_live_action_capability = _test_live_action_capability
        self._binding_sha256 = _binding_sha256(binding)
        self._blob_url = (
            f"https://{binding.account_name}.blob.core.windows.net/"
            f"{_CONTAINER_NAME}/locks/{binding.target_binding_sha256}.lock"
        )
        self._lease_url = f"{self._blob_url}?comp=lease"

    @property
    def target_binding_sha256(self) -> str:
        return self._binding.target_binding_sha256

    @property
    def lease_binding_sha256(self) -> str:
        return self._binding_sha256

    @property
    def infrastructure_safety_evidence_sha256(self) -> str:
        return self._acquisition_safety_evidence[
            "infrastructure_safety_evidence_sha256"
        ]

    @property
    def lease_acquisition_safety_evidence_sha256(self) -> str:
        return self._acquisition_safety_evidence[
            "lease_acquisition_safety_evidence_sha256"
        ]

    def execution_fence(
        self,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> Iterator[None]:
        capability = live_action_capability or self._test_live_action_capability
        if capability is not None:
            self._authorize_capability(
                capability,
                action=BLOB_LEASE_ASSERT_HELD,
                consume=False,
            )
        return self._store.run_locked()

    def acquire(
        self,
        proposed_lease_id: UUID,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> AzureBlobLeaseReceipt:
        capability = live_action_capability or self._test_live_action_capability
        self._authorize_capability(
            capability, action=BLOB_LEASE_ACQUIRE, consume=False
        )
        lease_id = _canonical_lease_id(proposed_lease_id)
        acquisition_safety = _validated_lease_acquisition_safety_evidence(
            self._acquisition_safety_evidence,
            binding=self._binding,
        )
        _require_current_infrastructure_safety(
            acquisition_safety["infrastructure_safety_evidence"],
            now=self._now(),
        )
        self._authorize_capability(
            capability,
            action=BLOB_LEASE_ACQUIRE,
            consume=True,
        )
        with self._store.locked() as directory:
            state = self._load_bound_state(directory)
            if state is None:
                acquisition_token = self._access_token(
                    self._binding.write_identity_binding_sha256
                )
                self._require_current_infrastructure_safety()
                state = self._new_state(_ACQUIRE_INTENT, lease_id)
                self._store.save(state, directory)
                state = self._transition(state, _ACQUIRE_IN_FLIGHT)
                self._store.save(state, directory)
                self._acquire_remote(lease_id, acquisition_token, capability)
                state = self._transition(state, _HELD)
                self._store.save(state, directory)
                return self._receipt(state)
            self._require_same_id(state, lease_id)
            if state["lifecycle_state"] in {
                _ACQUIRE_INTENT,
                _ACQUIRE_IN_FLIGHT,
                _HELD,
            }:
                classification = self._classify_head(
                    lease_id, capability, BLOB_LEASE_ACQUIRE
                )
                if classification != _HELD:
                    self._raise_head_classification(classification)
                if state["lifecycle_state"] != _HELD:
                    state = self._transition(state, _HELD)
                    self._store.save(state, directory)
                return self._receipt(state)
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_REACQUIRE_FORBIDDEN")

    def assert_held(
        self,
        lease_id: UUID,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> AzureBlobLeaseReceipt:
        capability = live_action_capability or self._test_live_action_capability
        self._authorize_capability(
            capability, action=BLOB_LEASE_ASSERT_HELD, consume=False
        )
        canonical_id = _canonical_lease_id(lease_id)
        with self._store.locked() as directory:
            state = self._load_bound_state(directory)
            if state is None:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_NOT_HELD")
            self._require_same_id(state, canonical_id)
            if state["lifecycle_state"] not in {
                _ACQUIRE_INTENT,
                _ACQUIRE_IN_FLIGHT,
                _HELD,
            }:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_NOT_HELD")
            classification = self._classify_head(
                canonical_id, capability, BLOB_LEASE_ASSERT_HELD
            )
            if classification != _HELD:
                self._raise_head_classification(classification)
            if state["lifecycle_state"] != _HELD:
                state = self._transition(state, _HELD)
                self._store.save(state, directory)
            return self._receipt(state)

    def release(
        self,
        lease_id: UUID,
        live_action_capability: VerifiedLiveActionCapability | None = None,
    ) -> AzureBlobLeaseReceipt:
        capability = live_action_capability or self._test_live_action_capability
        self._authorize_capability(
            capability, action=BLOB_LEASE_RELEASE, consume=False
        )
        canonical_id = _canonical_lease_id(lease_id)
        with self._store.locked() as directory:
            state = self._load_bound_state(directory)
            if state is None:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_NOT_HELD")
            self._require_same_id(state, canonical_id)
            lifecycle = state["lifecycle_state"]
            if lifecycle == _RELEASED:
                self._assert_released_remote(canonical_id, capability)
                return self._receipt(state)
            if lifecycle in {_ACQUIRE_INTENT, _ACQUIRE_IN_FLIGHT}:
                classification = self._classify_head(
                    canonical_id, capability, BLOB_LEASE_RELEASE
                )
                if classification != _HELD:
                    self._raise_head_classification(classification)
                state = self._transition(state, _HELD)
                self._store.save(state, directory)
                lifecycle = _HELD
            if lifecycle == _HELD:
                state = self._transition(
                    state, _RELEASE_INTENT, release_attempts=1
                )
                self._store.save(state, directory)
                self._release_remote(canonical_id, capability)
                return self._confirm_released(
                    state, canonical_id, directory, capability
                )
            if lifecycle != _RELEASE_INTENT:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")

            classification = self._classify_head(
                canonical_id, capability, BLOB_LEASE_RELEASE
            )
            if classification == "NOT_PRESENT":
                return self._confirm_released(
                    state, canonical_id, directory, capability
                )
            if classification != _HELD:
                self._raise_head_classification(classification)
            if state["release_attempts"] >= 2:
                raise AzureBlobLeaseError(
                    "AZURE_BLOB_LEASE_RELEASE_RECONCILIATION_EXHAUSTED"
                )
            state = self._transition(
                state, _RELEASE_INTENT, release_attempts=2
            )
            self._store.save(state, directory)
            self._release_remote(canonical_id, capability)
            return self._confirm_released(
                state, canonical_id, directory, capability
            )

    def _acquire_remote(
        self,
        lease_id: str,
        token: str,
        capability: VerifiedLiveActionCapability,
    ) -> None:
        headers = self._common_headers(
            lease_id,
            self._binding.write_identity_binding_sha256,
            token=token,
        )
        headers.update(
            {
                "Content-Length": "0",
                "x-ms-lease-action": "acquire",
                "x-ms-lease-duration": "-1",
                "x-ms-proposed-lease-id": lease_id,
            }
        )
        result = self._request(
            "PUT",
            self._lease_url,
            headers,
            b"",
            capability=capability,
            action=BLOB_LEASE_ACQUIRE,
            capability_already_consumed=True,
        )
        if result.status == 409:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_FOREIGN")
        if result.status == 412:
            self._raise_put_precondition(result)
        self._validate_success(result, 201)
        if _header(result.headers, "x-ms-lease-id") != lease_id:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")

    def _release_remote(
        self,
        lease_id: str,
        capability: VerifiedLiveActionCapability,
    ) -> None:
        self._authorize_capability(
            capability, action=BLOB_LEASE_RELEASE, consume=True
        )
        headers = self._common_headers(
            lease_id, self._binding.write_identity_binding_sha256
        )
        headers.update(
            {
                "Content-Length": "0",
                "x-ms-lease-action": "release",
                "x-ms-lease-id": lease_id,
            }
        )
        result = self._request(
            "PUT",
            self._lease_url,
            headers,
            b"",
            capability=capability,
            action=BLOB_LEASE_RELEASE,
            capability_already_consumed=True,
        )
        if result.status in {409, 412}:
            self._raise_put_precondition(result)
        self._validate_success(result, 200)

    def _classify_head(
        self,
        lease_id: str,
        capability: VerifiedLiveActionCapability,
        action: str,
    ) -> str:
        already_consumed = action == BLOB_LEASE_ACQUIRE
        if not already_consumed:
            self._authorize_capability(capability, action=action, consume=True)
        headers = self._common_headers(
            lease_id, self._binding.read_identity_binding_sha256
        )
        headers["x-ms-lease-id"] = lease_id
        result = self._request(
            "HEAD",
            self._blob_url,
            headers,
            None,
            capability=capability,
            action=action,
            capability_already_consumed=True,
        )
        if result.status == 200:
            self._validate_success(result, 200)
            if (
                _header(result.headers, "x-ms-lease-state") != "leased"
                or _header(result.headers, "x-ms-lease-status") != "locked"
                or _header(result.headers, "x-ms-lease-duration") != "infinite"
            ):
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")
            return _HELD
        if result.status == 412:
            error_code = _header(result.headers, "x-ms-error-code")
            if error_code == "LeaseNotPresentWithBlobOperation":
                return "NOT_PRESENT"
            if error_code == "LeaseIdMismatchWithBlobOperation":
                return "FOREIGN"
            if error_code == "ConditionNotMet":
                return "BINDING_DRIFT"
        if result.status == 404:
            return "BINDING_DRIFT"
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")

    def _confirm_released(
        self,
        state: Mapping[str, Any],
        lease_id: str,
        directory: int,
        capability: VerifiedLiveActionCapability,
    ) -> AzureBlobLeaseReceipt:
        self._assert_released_remote(lease_id, capability)
        return self._persist_released(state, directory)

    def _assert_released_remote(
        self,
        lease_id: str,
        capability: VerifiedLiveActionCapability,
    ) -> None:
        self._authorize_capability(
            capability, action=BLOB_LEASE_RELEASE, consume=True
        )
        headers = self._common_headers(
            lease_id, self._binding.read_identity_binding_sha256
        )
        result = self._request(
            "HEAD",
            self._blob_url,
            headers,
            None,
            capability=capability,
            action=BLOB_LEASE_RELEASE,
            capability_already_consumed=True,
        )
        if result.status == 200:
            self._validate_success(result, 200)
            state = _header(result.headers, "x-ms-lease-state")
            status = _header(result.headers, "x-ms-lease-status")
            duration = _header(result.headers, "x-ms-lease-duration")
            if state == "available" and status == "unlocked" and duration is None:
                return
            if state == "leased" and status == "locked":
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RELEASE_UNCERTAIN")
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")
        if result.status == 412:
            error_code = _header(result.headers, "x-ms-error-code")
            if error_code == "LeaseIdMismatchWithBlobOperation":
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_FOREIGN")
            if error_code == "ConditionNotMet":
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BINDING_DRIFT")
        if result.status == 404:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BINDING_DRIFT")
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")

    def _persist_released(
        self, state: Mapping[str, Any], directory: int
    ) -> AzureBlobLeaseReceipt:
        released = self._transition(state, _RELEASED)
        self._store.save(released, directory)
        return self._receipt(released)

    def _common_headers(
        self,
        lease_id: str,
        identity_binding_sha256: str,
        *,
        token: str | None = None,
    ) -> dict[str, str]:
        access_token = token or self._access_token(identity_binding_sha256)
        request_date = format_datetime(
            self._now().astimezone(timezone.utc), usegmt=True
        )
        return {
            "Authorization": f"Bearer {access_token}",
            "If-Match": self._binding.expected_etag,
            "x-ms-client-request-id": lease_id,
            "x-ms-date": request_date,
            "x-ms-version": _API_VERSION,
        }

    def _access_token(self, identity_binding_sha256: str) -> str:
        try:
            token_result = self._token_provider(
                audience=_TOKEN_AUDIENCE,
                identity_binding_sha256=identity_binding_sha256,
            )
        except Exception:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_TOKEN_UNAVAILABLE") from None
        return _validated_access_token(
            token_result,
            now=self._now(),
            expected_identity_binding_sha256=identity_binding_sha256,
            expected_subject=self._binding.token_subject,
            expected_tenant=self._binding.token_tenant_id,
            invalid_code="AZURE_BLOB_LEASE_TOKEN_INVALID",
            subject_code="AZURE_BLOB_LEASE_TOKEN_SUBJECT_MISMATCH",
            tenant_code="AZURE_BLOB_LEASE_TOKEN_TENANT_MISMATCH",
        )

    def _now(self) -> datetime:
        try:
            now = self._clock()
            if not isinstance(now, datetime) or now.tzinfo is None:
                raise ValueError
            return now
        except Exception:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_CLOCK_INVALID") from None

    def _request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        *,
        capability: VerifiedLiveActionCapability,
        action: str,
        capability_already_consumed: bool = False,
    ) -> _HttpResult:
        if not capability_already_consumed:
            self._authorize_capability(capability, action=action, consume=True)
        request = urllib.request.Request(
            url, data=body, headers=dict(headers), method=method
        )
        try:
            if method == "PUT" and action == BLOB_LEASE_ACQUIRE:
                self._require_current_infrastructure_safety()
            response = self._opener.open(request, timeout=_TIMEOUT_SECONDS)
            with response:
                result = self._result_from_response(response, url)
                if 200 <= result.status < 300 and response.read(1) != b"":
                    raise AzureBlobLeaseError(
                        "AZURE_BLOB_LEASE_RESPONSE_INVALID"
                    )
                return result
        except urllib.error.HTTPError as error:
            try:
                return self._result_from_response(error, url)
            except AzureBlobLeaseError:
                raise
            finally:
                error.close()
        except AzureBlobLeaseError:
            raise
        except Exception:
            raise AzureBlobLeaseError(
                "AZURE_BLOB_LEASE_TRANSPORT_UNAVAILABLE"
            ) from None

    def _require_current_infrastructure_safety(self) -> None:
        _require_current_infrastructure_safety(
            self._acquisition_safety_evidence[
                "infrastructure_safety_evidence"
            ],
            now=self._now(),
        )

    def _authorize_capability(
        self,
        capability: object,
        *,
        action: str,
        consume: bool,
    ) -> None:
        _authorize_blob_capability(
            capability,
            action=action,
            target_binding_sha256=self._binding.target_binding_sha256,
            binding_sha256=self._binding_sha256,
            consume=consume,
        )

    @staticmethod
    def _result_from_response(response: Any, expected_url: str) -> _HttpResult:
        try:
            status_code = getattr(response, "status", None)
            if status_code is None:
                status_code = response.getcode()
            status_code = int(status_code)
            actual_url = response.geturl()
            headers = _normalized_headers(response.headers)
        except Exception:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID") from None
        if (
            actual_url != expected_url
            or not 100 <= status_code <= 599
            or "location" in headers
        ):
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")
        return _HttpResult(status=status_code, headers=headers)

    def _validate_success(self, result: _HttpResult, expected_status: int) -> None:
        if (
            result.status != expected_status
            or _header(result.headers, "etag") != self._binding.expected_etag
            or _header(result.headers, "x-ms-version") != _API_VERSION
        ):
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")

    @staticmethod
    def _raise_put_precondition(result: _HttpResult) -> None:
        error_code = _header(result.headers, "x-ms-error-code")
        if error_code == "ConditionNotMet":
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BINDING_DRIFT")
        if error_code in {
            "LeaseAlreadyPresent",
            "LeaseIdMismatchWithLeaseOperation",
            "LeaseNotPresentWithLeaseOperation",
        }:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_FOREIGN")
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")

    def _load_bound_state(self, directory: int) -> dict[str, Any] | None:
        state = self._store.load(directory)
        if state is not None and (
            state["lease_binding_sha256"] != self._binding_sha256
            or state["target_binding_sha256"]
            != self._binding.target_binding_sha256
        ):
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_CONFLICT")
        return state

    def _new_state(self, lifecycle: str, lease_id: str) -> dict[str, Any]:
        return {
            "generation": 1,
            "lease_binding_sha256": self._binding_sha256,
            "lease_id": lease_id,
            "lease_id_sha256": _sha256_text(lease_id),
            "lifecycle_state": lifecycle,
            "release_attempts": 0,
            "target_binding_sha256": self._binding.target_binding_sha256,
        }

    @staticmethod
    def _transition(
        state: Mapping[str, Any],
        lifecycle: str,
        *,
        release_attempts: int | None = None,
    ) -> dict[str, Any]:
        updated = dict(state)
        updated["generation"] = int(state["generation"]) + 1
        updated["lifecycle_state"] = lifecycle
        if release_attempts is not None:
            updated["release_attempts"] = release_attempts
        return _validated_payload(updated)

    @staticmethod
    def _require_same_id(state: Mapping[str, Any], lease_id: str) -> None:
        if state["lease_id"] != lease_id:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_ID_MISMATCH")

    @staticmethod
    def _raise_head_classification(classification: str) -> None:
        if classification == "FOREIGN":
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_FOREIGN")
        if classification == "BINDING_DRIFT":
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_BINDING_DRIFT")
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_NOT_HELD")

    def _receipt(self, state: Mapping[str, Any]) -> AzureBlobLeaseReceipt:
        return AzureBlobLeaseReceipt(
            lease_binding_sha256=self._binding_sha256,
            target_binding_sha256=self._binding.target_binding_sha256,
            lease_id_sha256=state["lease_id_sha256"],
            read_identity_binding_sha256=(
                self._binding.read_identity_binding_sha256
            ),
            write_identity_binding_sha256=(
                self._binding.write_identity_binding_sha256
            ),
            lifecycle_state=state["lifecycle_state"],
            lifecycle_state_sha256=_sha256_json(state),
        )


def _validated_envelope(value: Any) -> dict[str, Any]:
    if (
        not isinstance(value, dict)
        or set(value) != {"payload", "payload_sha256", "schema_version"}
        or value.get("schema_version") != _STATE_SCHEMA
        or not _is_sha256(value.get("payload_sha256"))
        or not isinstance(value.get("payload"), dict)
    ):
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")
    payload = _validated_payload(value["payload"])
    if value["payload_sha256"] != _sha256_json(payload):
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")
    return payload


def _validated_lease_acquisition_safety_evidence(
    value: Mapping[str, Any],
    *,
    binding: AzureBlobLeaseBinding,
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID"
        )
    result = dict(value)
    digest = result.pop("lease_acquisition_safety_evidence_sha256", None)
    required = {
        "schema_version",
        "status",
        "infrastructure_safety_evidence",
        "infrastructure_safety_evidence_sha256",
        "lease_binding_sha256",
        "owner_approval_body_sha256",
        "coordination_storage_account_resource_id",
        "expected_etag",
        "token_subject",
        "token_tenant_id",
        "target_binding_sha256",
    }
    try:
        infrastructure = validate_infrastructure_safety_evidence(
            result.get("infrastructure_safety_evidence")
        )
    except Exception:
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID"
        ) from None
    token_subject = _canonical_uuid(result.get("token_subject"))
    token_tenant = _canonical_uuid(result.get("token_tenant_id"))
    infrastructure_subject = _canonical_uuid(
        infrastructure.get("runtime_principal_id")
    )
    infrastructure_tenant = _canonical_uuid(infrastructure.get("tenant_id"))
    bff_account = _storage_account_name_from_resource_id(
        infrastructure.get("bff_storage_account_resource_id")
    )
    worm_account = _storage_account_name_from_resource_id(
        infrastructure.get("worm_storage_account_resource_id")
    )
    if (
        set(result) != required
        or result.get("schema_version") != _ACQUISITION_SAFETY_SCHEMA
        or result.get("status") != "SAFE"
        or not _is_sha256(digest)
        or digest != _sha256_json(result)
        or result.get("infrastructure_safety_evidence_sha256")
        != infrastructure.get("infrastructure_safety_evidence_sha256")
        or result.get("lease_binding_sha256") != _binding_sha256(binding)
        or result.get("owner_approval_body_sha256")
        != binding.owner_approval_body_sha256
        or infrastructure.get("owner_binding_sha256")
        != binding.owner_approval_body_sha256
        or result.get("coordination_storage_account_resource_id")
        != binding.coordination_storage_account_resource_id
        or str(infrastructure.get("coordination_storage_account_resource_id", "")).casefold()
        != binding.coordination_storage_account_resource_id.casefold()
        or result.get("expected_etag") != binding.expected_etag
        or token_subject != binding.token_subject
        or infrastructure_subject != binding.token_subject
        or token_tenant != binding.token_tenant_id
        or infrastructure_tenant != binding.token_tenant_id
        or result.get("target_binding_sha256") != binding.target_binding_sha256
        or infrastructure.get("target_binding_sha256")
        != binding.target_binding_sha256
        or infrastructure.get("lease_blob_path")
        != f"locks/{binding.target_binding_sha256}.lock"
        or bff_account != binding.bff_account_name
        or worm_account != binding.worm_account_name
    ):
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_ACQUISITION_SAFETY_INVALID"
        )
    return {
        **result,
        "infrastructure_safety_evidence": infrastructure,
        "lease_acquisition_safety_evidence_sha256": digest,
    }


def _validated_bootstrap_infrastructure_safety_evidence(
    value: Mapping[str, Any],
    *,
    binding: AzureBlobLeaseBootstrapBinding,
) -> dict[str, Any]:
    try:
        infrastructure = validate_infrastructure_safety_evidence(value)
    except Exception:
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_BOOTSTRAP_SAFETY_INVALID"
        ) from None
    bff_account = _storage_account_name_from_resource_id(
        infrastructure.get("bff_storage_account_resource_id")
    )
    worm_account = _storage_account_name_from_resource_id(
        infrastructure.get("worm_storage_account_resource_id")
    )
    expected_container_resource_id = (
        f"{binding.coordination_storage_account_resource_id}/"
        f"blobServices/default/containers/{_CONTAINER_NAME}"
    )
    if (
        infrastructure.get("owner_binding_sha256")
        != binding.owner_approval_body_sha256
        or _canonical_uuid(infrastructure.get("bootstrap_principal_id"))
        != binding.token_subject
        or _canonical_uuid(infrastructure.get("runtime_principal_id"))
        != binding.runtime_token_subject
        or _canonical_uuid(infrastructure.get("tenant_id"))
        != binding.token_tenant_id
        or str(
            infrastructure.get("coordination_storage_account_resource_id", "")
        ).casefold()
        != binding.coordination_storage_account_resource_id.casefold()
        or infrastructure.get("coordination_storage_account_name")
        != binding.account_name
        or str(infrastructure.get("lease_container_resource_id", "")).casefold()
        != expected_container_resource_id.casefold()
        or infrastructure.get("lease_blob_path")
        != f"locks/{binding.target_binding_sha256}.lock"
        or infrastructure.get("target_binding_sha256")
        != binding.target_binding_sha256
        or bff_account != binding.bff_account_name
        or worm_account != binding.worm_account_name
    ):
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_BOOTSTRAP_SAFETY_INVALID"
        )
    return infrastructure


def _require_current_infrastructure_safety(
    infrastructure: Mapping[str, Any],
    *,
    now: datetime,
) -> None:
    verified_at_value = infrastructure.get("verified_at_utc")
    try:
        if not isinstance(verified_at_value, str):
            raise ValueError
        verified_at = datetime.strptime(
            verified_at_value, "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)
        current = now.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_INFRASTRUCTURE_SAFETY_INVALID"
        ) from None
    age = current - verified_at
    if not (
        -_INFRASTRUCTURE_SAFETY_MAX_FUTURE_SKEW
        <= age
        <= _INFRASTRUCTURE_SAFETY_MAX_AGE
    ):
        raise AzureBlobLeaseError(
            "AZURE_BLOB_LEASE_INFRASTRUCTURE_SAFETY_STALE"
        )


def _validated_access_token(
    value: Any,
    *,
    now: datetime,
    expected_identity_binding_sha256: str,
    expected_subject: str,
    expected_tenant: str,
    invalid_code: str,
    subject_code: str,
    tenant_code: str,
) -> str:
    if (
        type(value) is not AttestedAzureStorageAccessToken
        or value._seal is not _AZURE_STORAGE_TOKEN_ATTESTATION_SEAL
        or not isinstance(value.token, str)
        or not 1 <= len(value.token) <= 16 * 1024
        or value.token.strip() != value.token
        or any(
            ord(character) < 0x21 or ord(character) > 0x7E
            for character in value.token
        )
        or value.scope != _TOKEN_AUDIENCE
        or value.identity_binding_sha256 != expected_identity_binding_sha256
        or value.source_attestation_sha256
        != expected_identity_binding_sha256
        or _jwt_algorithm(value.token) != "RS256"
    ):
        raise AzureBlobLeaseError(invalid_code)
    expires_at = value.expires_at
    not_before = value.not_before
    now_timestamp = now.timestamp()
    if (
        not _numeric_date(expires_at)
        or not _numeric_date(not_before)
        or now_timestamp >= expires_at
        or now_timestamp < not_before
    ):
        raise AzureBlobLeaseError(invalid_code)
    if _canonical_uuid(value.subject) != expected_subject:
        raise AzureBlobLeaseError(subject_code)
    if _canonical_uuid(value.tenant_id) != expected_tenant:
        raise AzureBlobLeaseError(tenant_code)
    return value.token


def _numeric_date(value: Any) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _validated_payload(value: dict[str, Any]) -> dict[str, Any]:
    if set(value) != {
        "generation",
        "lease_binding_sha256",
        "lease_id",
        "lease_id_sha256",
        "lifecycle_state",
        "release_attempts",
        "target_binding_sha256",
    }:
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")
    try:
        lease_id = str(UUID(value["lease_id"]))
    except (ValueError, TypeError, AttributeError):
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None
    lifecycle = value["lifecycle_state"]
    attempts = value["release_attempts"]
    valid_attempts = (
        attempts == 0
        if isinstance(lifecycle, str)
        and lifecycle in {_ACQUIRE_INTENT, _ACQUIRE_IN_FLIGHT, _HELD}
        else type(attempts) is int and attempts in {1, 2}
    )
    if (
        type(value["generation"]) is not int
        or value["generation"] < 1
        or not isinstance(lifecycle, str)
        or lifecycle not in _STATES
        or not valid_attempts
        or value["lease_id"] != lease_id
        or value["lease_id_sha256"] != _sha256_text(lease_id)
        or not _is_sha256(value["lease_binding_sha256"])
        or not _is_sha256(value["target_binding_sha256"])
    ):
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")
    return value


def _normalized_headers(headers: Any) -> dict[str, str]:
    try:
        items = headers.items()
    except AttributeError:
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID") from None
    normalized: dict[str, str] = {}
    try:
        for raw_name, raw_value in items:
            name = str(raw_name).lower()
            value = str(raw_value)
            if (
                not name
                or name in normalized
                or any(character in name for character in "\r\n")
                or any(character in value for character in "\r\n")
            ):
                raise ValueError
            normalized[name] = value
    except Exception:
        raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID") from None
    return normalized


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return headers.get(name.lower())


def _binding_sha256(binding: AzureBlobLeaseBinding) -> str:
    return _sha256_json(
        {
            "api_version": _API_VERSION,
            "bff_storage_account_name": binding.bff_account_name,
            "blob_path": f"locks/{binding.target_binding_sha256}.lock",
            "container_name": _CONTAINER_NAME,
            "expected_etag": binding.expected_etag,
            "host": f"{binding.account_name}.blob.core.windows.net",
            "owner_approval_body_sha256": (
                binding.owner_approval_body_sha256
            ),
            "coordination_storage_account_resource_id": (
                binding.coordination_storage_account_resource_id
            ),
            "read_identity_binding_sha256": (
                binding.read_identity_binding_sha256
            ),
            "scheme": "https",
            "storage_account_name": binding.account_name,
            "target_binding_sha256": binding.target_binding_sha256,
            "token_subject": binding.token_subject,
            "token_tenant_id": binding.token_tenant_id,
            "token_audience": _TOKEN_AUDIENCE,
            "worm_storage_account_name": binding.worm_account_name,
            "write_identity_binding_sha256": (
                binding.write_identity_binding_sha256
            ),
        }
    )


def _bootstrap_binding_sha256(binding: AzureBlobLeaseBootstrapBinding) -> str:
    return _sha256_json(
        {
            "api_version": _API_VERSION,
            "bff_storage_account_name": binding.bff_account_name,
            "blob_path": f"locks/{binding.target_binding_sha256}.lock",
            "container_name": _CONTAINER_NAME,
            "coordination_storage_account_resource_id": (
                binding.coordination_storage_account_resource_id
            ),
            "host": f"{binding.account_name}.blob.core.windows.net",
            "owner_approval_body_sha256": binding.owner_approval_body_sha256,
            "read_identity_binding_sha256": (
                binding.read_identity_binding_sha256
            ),
            "runtime_read_identity_binding_sha256": (
                binding.runtime_read_identity_binding_sha256
            ),
            "runtime_token_subject": binding.runtime_token_subject,
            "runtime_write_identity_binding_sha256": (
                binding.runtime_write_identity_binding_sha256
            ),
            "scheme": "https",
            "storage_account_name": binding.account_name,
            "target_binding_sha256": binding.target_binding_sha256,
            "token_audience": _TOKEN_AUDIENCE,
            "token_subject": binding.token_subject,
            "token_tenant_id": binding.token_tenant_id,
            "worm_storage_account_name": binding.worm_account_name,
            "write_identity_binding_sha256": (
                binding.write_identity_binding_sha256
            ),
        }
    )


def calculate_azure_blob_lease_bootstrap_binding_sha256(
    binding: AzureBlobLeaseBootstrapBinding,
) -> str:
    """Return the canonical bootstrap binding digest used by the adapter."""

    if type(binding) is not AzureBlobLeaseBootstrapBinding:
        raise TypeError("binding")
    return _bootstrap_binding_sha256(binding)


def _authorize_blob_capability(
    capability: object,
    *,
    action: str,
    target_binding_sha256: str,
    binding_sha256: str,
    consume: bool,
) -> None:
    try:
        _authorize_live_action(
            capability,
            action=action,
            target_binding_sha256=target_binding_sha256,
            binding_sha256=binding_sha256,
            consume=consume,
        )
    except PerformanceLiveAuthorizationError as exc:
        code = str(exc).replace("PERFORMANCE_", "AZURE_BLOB_LEASE_", 1)
        raise AzureBlobLeaseError(code) from None


def _canonical_lease_id(value: UUID) -> str:
    if type(value) is not UUID:
        raise TypeError("lease_id")
    return str(value)


def _canonical_uuid(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        canonical = str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None
    return canonical if canonical == value else None


def _storage_account_name_from_resource_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    match = _STORAGE_ACCOUNT_RESOURCE_ID_RE.fullmatch(value)
    if match is None:
        return None
    return match.group("name").lower()


def _jwt_algorithm(token: str) -> str | None:
    parts = token.split(".")
    if len(parts) != 3 or any(not part for part in parts):
        return None
    encoded = parts[0]
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = base64.b64decode(
            encoded + padding,
            altchars=b"-_",
            validate=True,
        )
        if len(payload) > 16 * 1024:
            raise ValueError
        header = json.loads(payload.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(header, dict) or set(header) - {"alg", "kid", "typ"}:
        return None
    algorithm = header.get("alg")
    return algorithm if isinstance(algorithm, str) else None


def _valid_etag(value: Any) -> bool:
    return (
        isinstance(value, str)
        and 3 <= len(value) <= 256
        and value.startswith('"')
        and value.endswith('"')
        and not value.startswith('W/')
        and value != '"*"'
        and all(0x20 <= ord(character) <= 0x7E for character in value)
        and "\r" not in value
        and "\n" not in value
    )


def _private_regular_file(metadata: os.stat_result) -> bool:
    return (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o600
    )


def _private_directory(metadata: os.stat_result) -> bool:
    return (
        stat.S_ISDIR(metadata.st_mode)
        and metadata.st_uid == os.geteuid()
        and stat.S_IMODE(metadata.st_mode) == 0o700
    )


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
