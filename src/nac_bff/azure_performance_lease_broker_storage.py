from __future__ import annotations

import base64
import binascii
import re
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit
from uuid import UUID

from .azure_performance_lease_broker import (
    AcquireOutcome,
    AssertOutcome,
    LeaseAcquireCommand,
    LeaseCommand,
    ReleaseOutcome,
)


AZURE_BLOB_API_VERSION = "2023-11-03"
AZURE_STORAGE_SCOPE = "https://storage.azure.com/.default"

_STATE_SCHEMA = "nac.azure-performance-lease-broker-blob-state/v2"
_TIMEOUT_SECONDS = 10
_MAX_RESPONSE_BODY_BYTES = 16 * 1024
_MAX_RESPONSE_HEADERS = 64
_MAX_RESPONSE_HEADER_BYTES = 16 * 1024
_MAX_HEADER_NAME_BYTES = 256
_MAX_HEADER_VALUE_BYTES = 8 * 1024
_MAX_TOKEN_BYTES = 8 * 1024
_MAX_PATH_BYTES = 2 * 1024

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_HOST_RE = re.compile(r"[a-z0-9]{3,24}\.blob\.core\.windows\.net\Z")
_BASE64URL_RE = re.compile(r"[A-Za-z0-9_-]{43}\Z")

_ACQUIRE_INTENT = "ACQUIRE_INTENT"
_ACQUIRE_IN_FLIGHT = "ACQUIRE_IN_FLIGHT"
_HELD = "HELD"
_RELEASE_INTENT = "RELEASE_INTENT"
_RELEASED = "RELEASED"
_LIFECYCLES = frozenset(
    {
        _ACQUIRE_INTENT,
        _ACQUIRE_IN_FLIGHT,
        _HELD,
        _RELEASE_INTENT,
        _RELEASED,
    }
)

_META_PREFIX = "x-ms-meta-"
_META_SCHEMA = f"{_META_PREFIX}schema_version"
_META_LIFECYCLE = f"{_META_PREFIX}lifecycle_state"
_META_RUN = f"{_META_PREFIX}run_fingerprint"
_META_OPERATION = f"{_META_PREFIX}operation_id"
_META_NONCE = f"{_META_PREFIX}nonce_key"
_META_BINDING = f"{_META_PREFIX}binding_fingerprint"
_META_PRIVATE_ID = f"{_META_PREFIX}private_lease_id"
_METADATA_HEADERS = frozenset(
    {
        _META_SCHEMA,
        _META_LIFECYCLE,
        _META_RUN,
        _META_OPERATION,
        _META_NONCE,
        _META_BINDING,
        _META_PRIVATE_ID,
    }
)


class AzureBlobLeaseStateMachineError(RuntimeError):
    """Stable, redacted failure at the fixed Azure Blob boundary."""


class _RequestUnavailable(Exception):
    pass


class _TokenUnavailable(_RequestUnavailable):
    pass


class _RetryableResponse(Exception):
    pass


class _MetadataConflict(Exception):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True, slots=True)
class _BlobState:
    run_fingerprint: str
    operation_id: str
    nonce_key: str
    binding_fingerprint: str
    private_lease_id: str
    lifecycle: str

    @property
    def azure_lease_id(self) -> str:
        raw = _decode_private_id(self.private_lease_id)
        return str(UUID(bytes=raw[:16]))

    def metadata(self) -> dict[str, str]:
        return {
            _META_SCHEMA: _STATE_SCHEMA,
            _META_LIFECYCLE: self.lifecycle,
            _META_RUN: self.run_fingerprint,
            _META_OPERATION: self.operation_id,
            _META_NONCE: self.nonce_key,
            _META_BINDING: self.binding_fingerprint,
            _META_PRIVATE_ID: self.private_lease_id,
        }

    def transition(self, lifecycle: str) -> _BlobState:
        return _BlobState(
            run_fingerprint=self.run_fingerprint,
            operation_id=self.operation_id,
            nonce_key=self.nonce_key,
            binding_fingerprint=self.binding_fingerprint,
            private_lease_id=self.private_lease_id,
            lifecycle=lifecycle,
        )

    def for_command(self, command: LeaseCommand, lifecycle: str | None = None) -> _BlobState:
        return _BlobState(
            run_fingerprint=self.run_fingerprint,
            operation_id=command.operation_id,
            nonce_key=command.nonce_key,
            binding_fingerprint=self.binding_fingerprint,
            private_lease_id=self.private_lease_id,
            lifecycle=self.lifecycle if lifecycle is None else lifecycle,
        )


@dataclass(frozen=True, slots=True)
class _HttpResult:
    status: int
    headers: Mapping[str, str]


class AzureBlobAtomicLeaseStateMachine:
    """Blob-backed ``AtomicLeaseStateMachinePort`` for one pinned blob.

    The constructor is the only place where deployment code supplies the
    target. Broker commands cannot select transport details. Each HTTP call is
    attempted once, redirects are rejected, and the blob body is never
    overwritten after the initial conditional zero-length creation.
    """

    def __init__(
        self,
        *,
        blob_url: str,
        expected_blob_path: str,
        token_provider: Any,
        opener: Any | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._blob_url = _fixed_blob_url(blob_url, expected_blob_path)
        self._lease_url = f"{self._blob_url}?comp=lease"
        self._metadata_url = f"{self._blob_url}?comp=metadata"
        provider = getattr(token_provider, "get_token", None)
        if not callable(provider):
            provider = token_provider if callable(token_provider) else None
        if provider is None:
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_CONFIGURATION_INVALID"
            )
        selected_opener = opener or urllib.request.build_opener(_NoRedirect())
        if not callable(getattr(selected_opener, "open", None)):
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_CONFIGURATION_INVALID"
            )
        if clock is not None and not callable(clock):
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_CONFIGURATION_INVALID"
            )
        self._token_provider = provider
        self._opener = selected_opener
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.RLock()

    def acquire(self, command: LeaseAcquireCommand, /) -> AcquireOutcome:
        state = _state_from_acquire_command(command)
        with self._lock:
            try:
                result = self._create(state)
            except _TokenUnavailable:
                return AcquireOutcome.RETRYABLE_FAILURE
            except _RequestUnavailable:
                return AcquireOutcome.INDETERMINATE_AFTER_CRASH

            if result.status == 201:
                etag = self._success_etag(result, 201)
                return self._start_acquire(state, etag, resumed=False)
            if not _is_existing_blob(result):
                if _retryable_status(result.status):
                    return AcquireOutcome.INDETERMINATE_AFTER_CRASH
                raise AzureBlobLeaseStateMachineError(
                    "AZURE_BLOB_BROKER_RESPONSE_INVALID"
                )

            try:
                existing, etag = self._load_state()
            except (_RequestUnavailable, _RetryableResponse):
                return AcquireOutcome.RETRYABLE_FAILURE
            if existing is None:
                return AcquireOutcome.RETRYABLE_FAILURE
            relationship = _relationship(existing, state)
            if relationship == "REPLAY":
                return AcquireOutcome.REPLAY_REJECTED
            if relationship == "OTHER":
                return AcquireOutcome.BUSY
            if existing.lifecycle in {_RELEASE_INTENT, _RELEASED}:
                return AcquireOutcome.REPLAY_REJECTED

            if existing.lifecycle == _ACQUIRE_INTENT:
                if relationship == "NEXT":
                    existing = existing.for_command(command)
                return self._start_acquire(existing, etag, resumed=True)
            if existing.lifecycle == _ACQUIRE_IN_FLIGHT:
                return self._reconcile_acquire(
                    existing,
                    etag,
                    next_command=command if relationship == "NEXT" else None,
                )
            if existing.lifecycle == _HELD:
                try:
                    classification, _, _ = self._probe_lease(existing, etag)
                except (_RequestUnavailable, _RetryableResponse):
                    return AcquireOutcome.RETRYABLE_FAILURE
                if classification == "HELD":
                    return AcquireOutcome.ALREADY_ACQUIRED
                if classification == "FOREIGN":
                    return AcquireOutcome.BUSY
                return AcquireOutcome.INDETERMINATE_AFTER_CRASH
            return AcquireOutcome.ALREADY_ACQUIRED

    def assert_held(self, command: LeaseCommand, /) -> AssertOutcome:
        _validate_command(command)
        with self._lock:
            try:
                state, etag = self._load_state()
            except (_RequestUnavailable, _RetryableResponse):
                return AssertOutcome.RETRYABLE_FAILURE
            if state is None:
                return AssertOutcome.NOT_ACQUIRED
            relationship = _relationship_to_command(state, command)
            if relationship == "REPLAY":
                return AssertOutcome.REPLAY_REJECTED
            if relationship == "OTHER":
                return AssertOutcome.NOT_ACQUIRED
            if state.lifecycle == _ACQUIRE_INTENT:
                return AssertOutcome.NOT_ACQUIRED
            if state.lifecycle == _RELEASED:
                return AssertOutcome.LOST
            if relationship == "NEXT" and state.lifecycle == _RELEASE_INTENT:
                return AssertOutcome.REPLAY_REJECTED

            try:
                classification, observed, observed_etag = self._probe_lease(
                    state, etag
                )
            except (_RequestUnavailable, _RetryableResponse):
                return AssertOutcome.RETRYABLE_FAILURE
            if classification == "HELD":
                updated = observed
                if relationship == "NEXT":
                    updated = observed.for_command(command)
                if state.lifecycle == _ACQUIRE_IN_FLIGHT:
                    updated = updated.transition(_HELD)
                if updated != observed:
                    try:
                        self._set_metadata(
                            updated,
                            observed_etag,
                            lease_id=updated.azure_lease_id,
                        )
                    except (_RequestUnavailable, _MetadataConflict):
                        return AssertOutcome.INDETERMINATE_AFTER_CRASH
                return AssertOutcome.HELD
            if state.lifecycle == _ACQUIRE_IN_FLIGHT:
                return AssertOutcome.INDETERMINATE_AFTER_CRASH
            return AssertOutcome.LOST

    def release(self, command: LeaseCommand, /) -> ReleaseOutcome:
        _validate_command(command)
        with self._lock:
            try:
                state, etag = self._load_state()
            except (_RequestUnavailable, _RetryableResponse):
                return ReleaseOutcome.RETRYABLE_FAILURE
            if state is None:
                return ReleaseOutcome.NOT_ACQUIRED
            relationship = _relationship_to_command(state, command)
            if relationship == "REPLAY":
                return ReleaseOutcome.REPLAY_REJECTED
            if relationship == "OTHER":
                return ReleaseOutcome.NOT_ACQUIRED
            if state.lifecycle == _ACQUIRE_INTENT:
                return ReleaseOutcome.NOT_ACQUIRED
            if state.lifecycle == _RELEASED:
                return ReleaseOutcome.ALREADY_RELEASED

            try:
                classification, observed, observed_etag = self._probe_lease(
                    state, etag
                )
            except (_RequestUnavailable, _RetryableResponse):
                return ReleaseOutcome.RETRYABLE_FAILURE
            if classification == "FOREIGN":
                return ReleaseOutcome.LOST
            if classification in {"MISSING", "CHANGED"}:
                return ReleaseOutcome.LOST
            if classification == "NOT_PRESENT":
                if state.lifecycle != _RELEASE_INTENT:
                    return ReleaseOutcome.LOST
                try:
                    self._set_metadata(
                        observed.transition(_RELEASED), observed_etag
                    )
                except (_RequestUnavailable, _MetadataConflict):
                    return ReleaseOutcome.INDETERMINATE_AFTER_CRASH
                return ReleaseOutcome.ALREADY_RELEASED

            current = observed
            current_etag = observed_etag
            if current.lifecycle in {_ACQUIRE_IN_FLIGHT, _HELD}:
                release_intent = current.for_command(command, _RELEASE_INTENT)
                try:
                    current_etag = self._set_metadata(
                        release_intent,
                        current_etag,
                        lease_id=release_intent.azure_lease_id,
                    )
                    current = release_intent
                except _TokenUnavailable:
                    return ReleaseOutcome.RETRYABLE_FAILURE
                except (_RequestUnavailable, _MetadataConflict):
                    return ReleaseOutcome.INDETERMINATE_AFTER_CRASH
            elif current.lifecycle != _RELEASE_INTENT:
                raise AzureBlobLeaseStateMachineError(
                    "AZURE_BLOB_BROKER_STATE_INVALID"
                )

            try:
                result = self._lease_action("release", current)
            except _RequestUnavailable:
                return ReleaseOutcome.INDETERMINATE_AFTER_CRASH
            if result.status != 200:
                if result.status in {409, 412}:
                    return ReleaseOutcome.INDETERMINATE_AFTER_CRASH
                if _retryable_status(result.status):
                    return ReleaseOutcome.INDETERMINATE_AFTER_CRASH
                raise AzureBlobLeaseStateMachineError(
                    "AZURE_BLOB_BROKER_RESPONSE_INVALID"
                )
            current_etag = self._success_etag(result, 200)
            try:
                self._set_metadata(current.transition(_RELEASED), current_etag)
            except (_RequestUnavailable, _MetadataConflict):
                return ReleaseOutcome.INDETERMINATE_AFTER_CRASH
            return ReleaseOutcome.RELEASED

    def _start_acquire(
        self, state: _BlobState, etag: str, *, resumed: bool
    ) -> AcquireOutcome:
        in_flight = state.transition(_ACQUIRE_IN_FLIGHT)
        try:
            etag = self._set_metadata(in_flight, etag)
        except _TokenUnavailable:
            return AcquireOutcome.RETRYABLE_FAILURE
        except (_RequestUnavailable, _MetadataConflict):
            return AcquireOutcome.INDETERMINATE_AFTER_CRASH
        return self._dispatch_acquire(in_flight, etag, resumed=resumed)

    def _dispatch_acquire(
        self, in_flight: _BlobState, etag: str, *, resumed: bool
    ) -> AcquireOutcome:
        try:
            result = self._lease_action("acquire", in_flight)
        except _RequestUnavailable:
            return AcquireOutcome.INDETERMINATE_AFTER_CRASH
        if result.status == 409:
            return AcquireOutcome.BUSY
        if result.status != 201:
            if result.status == 412 or _retryable_status(result.status):
                return AcquireOutcome.INDETERMINATE_AFTER_CRASH
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_RESPONSE_INVALID"
            )
        etag = self._success_etag(result, 201)
        if _header(result.headers, "x-ms-lease-id") != in_flight.azure_lease_id:
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_RESPONSE_INVALID"
            )
        try:
            self._set_metadata(
                in_flight.transition(_HELD),
                etag,
                lease_id=in_flight.azure_lease_id,
            )
        except (_RequestUnavailable, _MetadataConflict):
            return AcquireOutcome.INDETERMINATE_AFTER_CRASH
        return (
            AcquireOutcome.ALREADY_ACQUIRED if resumed else AcquireOutcome.ACQUIRED
        )

    def _reconcile_acquire(
        self,
        state: _BlobState,
        etag: str,
        *,
        next_command: LeaseAcquireCommand | None = None,
    ) -> AcquireOutcome:
        try:
            classification, observed, observed_etag = self._probe_lease(state, etag)
        except (_RequestUnavailable, _RetryableResponse):
            return AcquireOutcome.RETRYABLE_FAILURE
        if classification == "HELD":
            updated = observed
            if next_command is not None:
                updated = observed.for_command(next_command)
            try:
                self._set_metadata(
                    updated.transition(_HELD),
                    observed_etag,
                    lease_id=updated.azure_lease_id,
                )
            except (_RequestUnavailable, _MetadataConflict):
                return AcquireOutcome.INDETERMINATE_AFTER_CRASH
            return AcquireOutcome.ALREADY_ACQUIRED
        if classification == "FOREIGN":
            return AcquireOutcome.BUSY
        if classification == "NOT_PRESENT":
            dispatch_state = (
                state.for_command(next_command)
                if next_command is not None
                else state
            )
            return self._dispatch_acquire(
                dispatch_state, observed_etag, resumed=True
            )
        return AcquireOutcome.INDETERMINATE_AFTER_CRASH

    def _create(self, state: _BlobState) -> _HttpResult:
        headers = self._headers()
        headers.update(
            {
                "Content-Length": "0",
                "If-None-Match": "*",
                "x-ms-blob-type": "BlockBlob",
                **state.metadata(),
            }
        )
        return self._request("PUT", self._blob_url, headers, b"")

    def _load_state(self) -> tuple[_BlobState | None, str]:
        result = self._request("HEAD", self._blob_url, self._headers(), None)
        if result.status == 404:
            return None, ""
        if _retryable_status(result.status):
            raise _RetryableResponse
        etag = self._success_etag(result, 200)
        return _state_from_headers(result.headers), etag

    def _probe_lease(
        self, expected: _BlobState, etag: str
    ) -> tuple[str, _BlobState, str]:
        headers = self._headers()
        headers.update(
            {"If-Match": etag, "x-ms-lease-id": expected.azure_lease_id}
        )
        result = self._request("HEAD", self._blob_url, headers, None)
        if result.status == 200:
            observed_etag = self._success_etag(result, 200)
            observed = _state_from_headers(result.headers)
            if observed != expected:
                return "CHANGED", observed, observed_etag
            if (
                _header(result.headers, "x-ms-lease-state") != "leased"
                or _header(result.headers, "x-ms-lease-status") != "locked"
                or _header(result.headers, "x-ms-lease-duration") != "infinite"
            ):
                raise AzureBlobLeaseStateMachineError(
                    "AZURE_BLOB_BROKER_RESPONSE_INVALID"
                )
            return "HELD", observed, observed_etag
        if result.status == 404:
            return "MISSING", expected, etag
        if result.status == 412:
            code = _header(result.headers, "x-ms-error-code")
            if code == "LeaseNotPresentWithBlobOperation":
                return "NOT_PRESENT", expected, etag
            if code == "LeaseIdMismatchWithBlobOperation":
                return "FOREIGN", expected, etag
            if code == "ConditionNotMet":
                return "CHANGED", expected, etag
        if _retryable_status(result.status):
            raise _RetryableResponse
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_RESPONSE_INVALID"
        )

    def _set_metadata(
        self, state: _BlobState, etag: str, *, lease_id: str | None = None
    ) -> str:
        headers = self._headers()
        headers.update(
            {
                "Content-Length": "0",
                "If-Match": etag,
                **state.metadata(),
            }
        )
        if lease_id is not None:
            headers["x-ms-lease-id"] = lease_id
        result = self._request("PUT", self._metadata_url, headers, b"")
        if result.status == 412:
            raise _MetadataConflict
        if result.status != 200:
            if _retryable_status(result.status):
                raise _RequestUnavailable
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_RESPONSE_INVALID"
            )
        return self._success_etag(result, 200)

    def _lease_action(self, action: str, state: _BlobState) -> _HttpResult:
        headers = self._headers()
        headers.update(
            {
                "Content-Length": "0",
                "x-ms-lease-action": action,
            }
        )
        if action == "acquire":
            headers["x-ms-lease-duration"] = "-1"
            headers["x-ms-proposed-lease-id"] = state.azure_lease_id
        elif action == "release":
            headers["x-ms-lease-id"] = state.azure_lease_id
        else:  # The branch is private and makes the action allowlist explicit.
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_STATE_INVALID"
            )
        return self._request("PUT", self._lease_url, headers, b"")

    def _headers(self) -> dict[str, str]:
        try:
            access_token = self._token_provider(AZURE_STORAGE_SCOPE)
            token = getattr(access_token, "token", access_token)
        except Exception:
            raise _TokenUnavailable from None
        try:
            encoded_token = token.encode("ascii") if type(token) is str else b""
        except UnicodeEncodeError:
            raise _TokenUnavailable from None
        if not encoded_token or len(encoded_token) > _MAX_TOKEN_BYTES or any(
            character in token for character in "\r\n"
        ):
            raise _TokenUnavailable
        return {
            "Authorization": f"Bearer {token}",
            "x-ms-date": format_datetime(self._now(), usegmt=True),
            "x-ms-version": AZURE_BLOB_API_VERSION,
        }

    def _now(self) -> datetime:
        try:
            value = self._clock()
            if not isinstance(value, datetime) or value.tzinfo is None:
                raise ValueError
            return value.astimezone(timezone.utc)
        except Exception:
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_CLOCK_INVALID"
            ) from None

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
        except urllib.error.HTTPError as error:
            response = error
        except Exception:
            raise _RequestUnavailable from None
        try:
            with response:
                result = _bounded_result(response, url)
                payload = response.read(_MAX_RESPONSE_BODY_BYTES + 1)
                if (
                    not isinstance(payload, bytes)
                    or len(payload) > _MAX_RESPONSE_BODY_BYTES
                    or (200 <= result.status < 300 and payload != b"")
                ):
                    raise AzureBlobLeaseStateMachineError(
                        "AZURE_BLOB_BROKER_RESPONSE_INVALID"
                    )
                return result
        except AzureBlobLeaseStateMachineError:
            raise
        except Exception:
            raise _RequestUnavailable from None

    @staticmethod
    def _validate_success(result: _HttpResult, expected_status: int) -> None:
        if (
            result.status != expected_status
            or _header(result.headers, "x-ms-version")
            != AZURE_BLOB_API_VERSION
        ):
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_RESPONSE_INVALID"
            )

    def _success_etag(self, result: _HttpResult, expected_status: int) -> str:
        self._validate_success(result, expected_status)
        etag = _header(result.headers, "etag")
        if (
            etag is None
            or len(etag) > 256
            or not etag.startswith('"')
            or not etag.endswith('"')
        ):
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_RESPONSE_INVALID"
            )
        return etag


def _fixed_blob_url(blob_url: object, expected_path: object) -> str:
    if (
        type(blob_url) is not str
        or type(expected_path) is not str
        or not expected_path.startswith("/")
        or len(expected_path.encode("utf-8")) > _MAX_PATH_BYTES
        or any(character in expected_path for character in "\r\n?#")
        or any(part in {"", ".", ".."} for part in expected_path.split("/")[1:])
    ):
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_TARGET_INVALID"
        )
    try:
        parsed = urlsplit(blob_url)
        hostname = parsed.hostname
        port = parsed.port
    except (TypeError, ValueError):
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_TARGET_INVALID"
        ) from None
    if (
        parsed.scheme != "https"
        or hostname is None
        or _HOST_RE.fullmatch(hostname) is None
        or parsed.netloc != hostname
        or port is not None
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
        or parsed.password is not None
        or blob_url != f"https://{hostname}{expected_path}"
    ):
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_TARGET_INVALID"
        )
    return blob_url


def _state_from_acquire_command(command: object) -> _BlobState:
    if type(command) is not LeaseAcquireCommand:
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_COMMAND_INVALID"
        )
    _validate_command(command)
    try:
        _decode_private_id(command.private_lease_id)
    except ValueError:
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_COMMAND_INVALID"
        ) from None
    return _BlobState(
        run_fingerprint=command.run_fingerprint,
        operation_id=command.operation_id,
        nonce_key=command.nonce_key,
        binding_fingerprint=command.binding_fingerprint,
        private_lease_id=command.private_lease_id,
        lifecycle=_ACQUIRE_INTENT,
    )


def _validate_command(command: object) -> None:
    if type(command) not in {LeaseCommand, LeaseAcquireCommand} or not all(
        type(getattr(command, name, None)) is str
        and _SHA256_RE.fullmatch(getattr(command, name)) is not None
        for name in (
            "run_fingerprint",
            "operation_id",
            "nonce_key",
            "binding_fingerprint",
        )
    ):
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_COMMAND_INVALID"
        )


def _decode_private_id(value: object) -> bytes:
    if type(value) is not str or _BASE64URL_RE.fullmatch(value) is None:
        raise ValueError
    try:
        decoded = base64.b64decode(value + "=", altchars=b"-_", validate=True)
    except (ValueError, binascii.Error):
        raise ValueError from None
    if len(decoded) != 32 or base64.urlsafe_b64encode(decoded).rstrip(b"=").decode(
        "ascii"
    ) != value:
        raise ValueError
    return decoded


def _relationship(existing: _BlobState, proposed: _BlobState) -> str:
    if existing.run_fingerprint != proposed.run_fingerprint:
        return "OTHER"
    if existing.nonce_key != proposed.nonce_key:
        return "NEXT"
    if (
        existing.operation_id != proposed.operation_id
        or existing.binding_fingerprint != proposed.binding_fingerprint
        or existing.private_lease_id != proposed.private_lease_id
    ):
        return "REPLAY"
    return "SAME"


def _relationship_to_command(existing: _BlobState, command: LeaseCommand) -> str:
    if existing.run_fingerprint != command.run_fingerprint:
        return "OTHER"
    if existing.nonce_key != command.nonce_key:
        return "NEXT"
    if (
        existing.operation_id != command.operation_id
        or existing.binding_fingerprint != command.binding_fingerprint
    ):
        return "REPLAY"
    return "SAME"


def _state_from_headers(headers: Mapping[str, str]) -> _BlobState:
    metadata = {
        name: value
        for name, value in headers.items()
        if name.lower().startswith(_META_PREFIX)
    }
    if (
        set(metadata) != _METADATA_HEADERS
        or metadata.get(_META_SCHEMA) != _STATE_SCHEMA
    ):
        raise AzureBlobLeaseStateMachineError("AZURE_BLOB_BROKER_STATE_INVALID")
    lifecycle = metadata.get(_META_LIFECYCLE)
    run_fingerprint = metadata.get(_META_RUN)
    operation_id = metadata.get(_META_OPERATION)
    nonce_key = metadata.get(_META_NONCE)
    binding = metadata.get(_META_BINDING)
    private_id = metadata.get(_META_PRIVATE_ID)
    if (
        lifecycle not in _LIFECYCLES
        or any(
            type(value) is not str or _SHA256_RE.fullmatch(value) is None
            for value in (run_fingerprint, operation_id, nonce_key, binding)
        )
    ):
        raise AzureBlobLeaseStateMachineError("AZURE_BLOB_BROKER_STATE_INVALID")
    try:
        _decode_private_id(private_id)
    except ValueError:
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_STATE_INVALID"
        ) from None
    return _BlobState(
        run_fingerprint=run_fingerprint,
        operation_id=operation_id,
        nonce_key=nonce_key,
        binding_fingerprint=binding,
        private_lease_id=private_id,
        lifecycle=lifecycle,
    )


def _bounded_result(response: Any, expected_url: str) -> _HttpResult:
    try:
        status_value = getattr(response, "status", None)
        if status_value is None:
            status_value = response.getcode()
        status = int(status_value)
        actual_url = response.geturl()
        raw_headers = list(response.headers.items())
    except Exception:
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_RESPONSE_INVALID"
        ) from None
    if (
        actual_url != expected_url
        or not 100 <= status <= 599
        or len(raw_headers) > _MAX_RESPONSE_HEADERS
    ):
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_RESPONSE_INVALID"
        )
    normalized: dict[str, str] = {}
    total = 0
    for raw_name, raw_value in raw_headers:
        if type(raw_name) is not str or type(raw_value) is not str:
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_RESPONSE_INVALID"
            )
        name = raw_name.lower()
        name_size = len(name.encode("ascii", errors="ignore"))
        value_size = len(raw_value.encode("utf-8"))
        total += name_size + value_size
        if (
            name in normalized
            or not name
            or name_size != len(name)
            or name_size > _MAX_HEADER_NAME_BYTES
            or value_size > _MAX_HEADER_VALUE_BYTES
            or total > _MAX_RESPONSE_HEADER_BYTES
            or any(character in raw_name + raw_value for character in "\r\n")
        ):
            raise AzureBlobLeaseStateMachineError(
                "AZURE_BLOB_BROKER_RESPONSE_INVALID"
            )
        normalized[name] = raw_value
    if "location" in normalized:
        raise AzureBlobLeaseStateMachineError(
            "AZURE_BLOB_BROKER_RESPONSE_INVALID"
        )
    return _HttpResult(status=status, headers=normalized)


def _header(headers: Mapping[str, str], name: str) -> str | None:
    return headers.get(name.lower())


def _is_existing_blob(result: _HttpResult) -> bool:
    return (
        result.status == 412
        and _header(result.headers, "x-ms-error-code") == "ConditionNotMet"
    ) or (
        result.status == 409
        and _header(result.headers, "x-ms-error-code") == "BlobAlreadyExists"
    )


def _retryable_status(status: int) -> bool:
    return status in {408, 429} or 500 <= status <= 599
