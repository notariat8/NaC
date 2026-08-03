from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import stat
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Any, Callable, ClassVar, Iterator, Mapping
from uuid import UUID


_API_VERSION = "2023-11-03"
_CONTAINER_NAME = "nac-bff-performance-leases"
_TOKEN_AUDIENCE = "https://storage.azure.com/"
_STATE_SCHEMA = "nac.azure-blob-performance-lease-state/v1"
_ACCOUNT_RE = re.compile(r"[a-z0-9]{3,24}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_MAX_STATE_BYTES = 16 * 1024
_TIMEOUT_SECONDS = 30

_ACQUIRE_INTENT = "ACQUIRE_INTENT"
_HELD = "HELD"
_RELEASE_INTENT = "RELEASE_INTENT"
_RELEASED = "RELEASED"
_STATES = frozenset({_ACQUIRE_INTENT, _HELD, _RELEASE_INTENT, _RELEASED})


class AzureBlobLeaseError(RuntimeError):
    """Stable, redacted failure at the performance lease boundary."""


@dataclass(frozen=True)
class AzureBlobLeaseBinding:
    """Immutable binding for the one pre-provisioned performance lock blob."""

    account_name: str
    bff_account_name: str
    worm_account_name: str
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
            or not _is_sha256(self.target_binding_sha256)
            or not _is_sha256(self.read_identity_binding_sha256)
            or not _is_sha256(self.write_identity_binding_sha256)
            or not _valid_etag(self.expected_etag)
        ):
            raise ValueError("AZURE_BLOB_LEASE_BINDING_INVALID")


@dataclass(frozen=True)
class AzureBlobLeaseReceipt:
    """Redacted lifecycle receipt whose values are hashes only."""

    lease_binding_sha256: str
    target_binding_sha256: str
    lease_id_sha256: str
    read_identity_binding_sha256: str
    write_identity_binding_sha256: str
    lifecycle_state_sha256: str


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
        self._lock_path = path.with_name(f".{path.name}.lock")

    @contextmanager
    def locked(self) -> Iterator[None]:
        self._ensure_private_parent()
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
        try:
            descriptor = os.open(self._lock_path, flags, 0o600)
            metadata = os.fstat(descriptor)
            if not _private_regular_file(metadata):
                raise OSError
            fcntl.flock(descriptor, fcntl.LOCK_EX)
        except OSError:
            try:
                os.close(descriptor)
            except (OSError, UnboundLocalError):
                pass
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None
        try:
            yield
        finally:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            finally:
                os.close(descriptor)

    def load(self) -> dict[str, Any] | None:
        try:
            descriptor = os.open(self._path, os.O_RDONLY | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        except OSError:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None
        try:
            metadata = os.fstat(descriptor)
            if (
                not _private_regular_file(metadata)
                or metadata.st_size > _MAX_STATE_BYTES
            ):
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

    def save(self, payload: Mapping[str, Any]) -> None:
        validated = _validated_payload(dict(payload))
        envelope = {
            "payload": validated,
            "payload_sha256": _sha256_json(validated),
            "schema_version": _STATE_SCHEMA,
        }
        encoded = (_canonical_json(envelope) + "\n").encode("ascii")
        if len(encoded) > _MAX_STATE_BYTES:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")
        self._ensure_private_parent()
        temporary = self._path.with_name(
            f".{self._path.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
        )
        descriptor = -1
        try:
            descriptor = os.open(
                temporary,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                descriptor = -1
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path)
            directory = os.open(
                self._path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            )
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_UNAVAILABLE") from None
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass

    def _ensure_private_parent(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            metadata = self._path.parent.lstat()
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) != 0o700
            ):
                raise OSError
        except OSError:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID") from None


class AzureBlobLeaseAdapter:
    """Direct Blob REST adapter with no redirect, retry, or blob-create path."""

    def __init__(
        self,
        *,
        binding: AzureBlobLeaseBinding,
        state_path: Path,
        token_provider: Callable[..., str] | Any,
        opener: Any | None = None,
        clock: Callable[[], datetime] | None = None,
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
        self._store = _PrivateLifecycleStore(state_path)
        self._token_provider = provider
        self._opener = selected_opener
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._binding_sha256 = _binding_sha256(binding)
        self._blob_url = (
            f"https://{binding.account_name}.blob.core.windows.net/"
            f"{_CONTAINER_NAME}/locks/{binding.target_binding_sha256}.lock"
        )
        self._lease_url = f"{self._blob_url}?comp=lease"

    def acquire(self, proposed_lease_id: UUID) -> AzureBlobLeaseReceipt:
        lease_id = _canonical_lease_id(proposed_lease_id)
        with self._store.locked():
            state = self._load_bound_state()
            if state is None:
                state = self._new_state(_ACQUIRE_INTENT, lease_id)
                self._store.save(state)
                self._acquire_remote(lease_id)
                state = self._transition(state, _HELD)
                self._store.save(state)
                return self._receipt(state)
            self._require_same_id(state, lease_id)
            if state["lifecycle_state"] in {_ACQUIRE_INTENT, _HELD}:
                classification = self._classify_head(lease_id)
                if classification != _HELD:
                    self._raise_head_classification(classification)
                if state["lifecycle_state"] == _ACQUIRE_INTENT:
                    state = self._transition(state, _HELD)
                    self._store.save(state)
                return self._receipt(state)
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_REACQUIRE_FORBIDDEN")

    def assert_held(self, lease_id: UUID) -> AzureBlobLeaseReceipt:
        canonical_id = _canonical_lease_id(lease_id)
        with self._store.locked():
            state = self._load_bound_state()
            if state is None:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_NOT_HELD")
            self._require_same_id(state, canonical_id)
            if state["lifecycle_state"] not in {_ACQUIRE_INTENT, _HELD}:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_NOT_HELD")
            classification = self._classify_head(canonical_id)
            if classification != _HELD:
                self._raise_head_classification(classification)
            if state["lifecycle_state"] == _ACQUIRE_INTENT:
                state = self._transition(state, _HELD)
                self._store.save(state)
            return self._receipt(state)

    def release(self, lease_id: UUID) -> AzureBlobLeaseReceipt:
        canonical_id = _canonical_lease_id(lease_id)
        with self._store.locked():
            state = self._load_bound_state()
            if state is None:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_NOT_HELD")
            self._require_same_id(state, canonical_id)
            lifecycle = state["lifecycle_state"]
            if lifecycle == _RELEASED:
                return self._receipt(state)
            if lifecycle == _ACQUIRE_INTENT:
                classification = self._classify_head(canonical_id)
                if classification != _HELD:
                    self._raise_head_classification(classification)
                state = self._transition(state, _HELD)
                self._store.save(state)
                lifecycle = _HELD
            if lifecycle == _HELD:
                state = self._transition(
                    state, _RELEASE_INTENT, release_attempts=1
                )
                self._store.save(state)
                self._release_remote(canonical_id)
                return self._confirm_released(state, canonical_id)
            if lifecycle != _RELEASE_INTENT:
                raise AzureBlobLeaseError("AZURE_BLOB_LEASE_STATE_INVALID")

            classification = self._classify_head(canonical_id)
            if classification == "NOT_PRESENT":
                return self._persist_released(state)
            if classification != _HELD:
                self._raise_head_classification(classification)
            if state["release_attempts"] >= 2:
                raise AzureBlobLeaseError(
                    "AZURE_BLOB_LEASE_RELEASE_RECONCILIATION_EXHAUSTED"
                )
            state = self._transition(
                state, _RELEASE_INTENT, release_attempts=2
            )
            self._store.save(state)
            self._release_remote(canonical_id)
            return self._confirm_released(state, canonical_id)

    def _acquire_remote(self, lease_id: str) -> None:
        headers = self._common_headers(
            lease_id, self._binding.write_identity_binding_sha256
        )
        headers.update(
            {
                "Content-Length": "0",
                "x-ms-lease-action": "acquire",
                "x-ms-lease-duration": "-1",
                "x-ms-proposed-lease-id": lease_id,
            }
        )
        result = self._request("PUT", self._lease_url, headers, b"")
        if result.status == 409:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_FOREIGN")
        if result.status == 412:
            self._raise_put_precondition(result)
        self._validate_success(result, 201)
        if _header(result.headers, "x-ms-lease-id") != lease_id:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RESPONSE_INVALID")

    def _release_remote(self, lease_id: str) -> None:
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
        result = self._request("PUT", self._lease_url, headers, b"")
        if result.status in {409, 412}:
            self._raise_put_precondition(result)
        self._validate_success(result, 200)

    def _classify_head(self, lease_id: str) -> str:
        headers = self._common_headers(
            lease_id, self._binding.read_identity_binding_sha256
        )
        headers["x-ms-lease-id"] = lease_id
        result = self._request("HEAD", self._blob_url, headers, None)
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
        self, state: Mapping[str, Any], lease_id: str
    ) -> AzureBlobLeaseReceipt:
        classification = self._classify_head(lease_id)
        if classification == "NOT_PRESENT":
            return self._persist_released(state)
        if classification == _HELD:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_RELEASE_UNCERTAIN")
        self._raise_head_classification(classification)

    def _persist_released(
        self, state: Mapping[str, Any]
    ) -> AzureBlobLeaseReceipt:
        released = self._transition(state, _RELEASED)
        self._store.save(released)
        return self._receipt(released)

    def _common_headers(
        self, lease_id: str, identity_binding_sha256: str
    ) -> dict[str, str]:
        token = self._access_token(identity_binding_sha256)
        try:
            now = self._clock()
            if not isinstance(now, datetime) or now.tzinfo is None:
                raise ValueError
            request_date = format_datetime(now.astimezone(timezone.utc), usegmt=True)
        except Exception:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_CLOCK_INVALID") from None
        return {
            "Authorization": f"Bearer {token}",
            "If-Match": self._binding.expected_etag,
            "x-ms-client-request-id": lease_id,
            "x-ms-date": request_date,
            "x-ms-version": _API_VERSION,
        }

    def _access_token(self, identity_binding_sha256: str) -> str:
        try:
            token = self._token_provider(
                audience=_TOKEN_AUDIENCE,
                identity_binding_sha256=identity_binding_sha256,
            )
        except Exception:
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_TOKEN_UNAVAILABLE") from None
        if (
            not isinstance(token, str)
            or not 1 <= len(token) <= 16 * 1024
            or token.strip() != token
            or any(ord(character) < 0x21 or ord(character) > 0x7E for character in token)
        ):
            raise AzureBlobLeaseError("AZURE_BLOB_LEASE_TOKEN_INVALID")
        return token

    def _request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
    ) -> _HttpResult:
        request = urllib.request.Request(
            url, data=body, headers=dict(headers), method=method
        )
        try:
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

    def _load_bound_state(self) -> dict[str, Any] | None:
        state = self._store.load()
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
        if isinstance(lifecycle, str) and lifecycle in {_ACQUIRE_INTENT, _HELD}
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
            "read_identity_binding_sha256": (
                binding.read_identity_binding_sha256
            ),
            "scheme": "https",
            "storage_account_name": binding.account_name,
            "target_binding_sha256": binding.target_binding_sha256,
            "token_audience": _TOKEN_AUDIENCE,
            "worm_storage_account_name": binding.worm_account_name,
            "write_identity_binding_sha256": (
                binding.write_identity_binding_sha256
            ),
        }
    )


def _canonical_lease_id(value: UUID) -> str:
    if type(value) is not UUID:
        raise TypeError("lease_id")
    return str(value)


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
