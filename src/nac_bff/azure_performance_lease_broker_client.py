from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import threading
from typing import Any, Callable, Iterator, Mapping
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from uuid import UUID

from .azure_performance_authorization import (
    BLOB_LEASE_ACQUIRE,
    BLOB_LEASE_ASSERT_HELD,
    BLOB_LEASE_RELEASE,
    _authorize_live_action,
)
from .azure_performance_lease_broker import RECEIPT_VERSION


_OPERATIONS = frozenset({"acquire", "assert", "release"})
_OPERATION_ACTIONS = {
    "acquire": BLOB_LEASE_ACQUIRE,
    "assert": BLOB_LEASE_ASSERT_HELD,
    "release": BLOB_LEASE_RELEASE,
}
_SUCCESS = {
    "acquire": frozenset({"ACQUIRED", "ALREADY_ACQUIRED"}),
    "assert": frozenset({"HELD"}),
    "release": frozenset({"RELEASED", "ALREADY_RELEASED"}),
}
_RECEIPT_FIELDS = frozenset(
    {
        "binding_fingerprint",
        "operation",
        "outcome",
        "retry",
        "schema_version",
        "ticket_fingerprint",
    }
)


class BrokeredAzureBlobLeaseError(RuntimeError):
    """Stable local error that never includes tokens, tickets, URLs or bodies."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


@dataclass(frozen=True, slots=True)
class BrokeredLeaseReceipt:
    lease_binding_sha256: str
    target_binding_sha256: str
    lifecycle_state: str
    lifecycle_state_sha256: str
    broker_receipt_sha256: str

    def __post_init__(self) -> None:
        if (
            any(
                not _is_sha256(value)
                for value in (
                    self.lease_binding_sha256,
                    self.target_binding_sha256,
                    self.lifecycle_state_sha256,
                    self.broker_receipt_sha256,
                )
            )
            or self.lifecycle_state not in {"HELD", "RELEASED"}
        ):
            raise ValueError("BROKERED_LEASE_RECEIPT_INVALID")


class BrokeredAzureBlobLeaseAdapter:
    """Local lease port that can reach only the fixed BFF broker API.

    The adapter has no Azure Storage URL, scope, credential, lease identifier or
    header surface. All Blob authority remains inside the deployed BFF identity.
    """

    def __init__(
        self,
        *,
        broker_base_url: str,
        token_provider: Callable[[], str] | Any,
        ticket_provider: Callable[[str], Mapping[str, Any]],
        target_binding_sha256: str,
        lease_binding_sha256: str,
        infrastructure_safety_evidence_sha256: str,
        lease_acquisition_safety_evidence_sha256: str,
        expected_broker_binding_fingerprint: str,
        opener: Any | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        parsed = urlsplit(broker_base_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or parsed.port not in {None, 443}
        ):
            raise ValueError("BROKERED_LEASE_CONFIGURATION_INVALID")
        provider = token_provider
        if not callable(provider):
            provider = getattr(provider, "get_token", None)
        selected_opener = opener or urllib.request.build_opener(_NoRedirect())
        if (
            not callable(provider)
            or not callable(ticket_provider)
            or not callable(getattr(selected_opener, "open", None))
            or not _is_sha256(target_binding_sha256)
            or not _is_sha256(lease_binding_sha256)
            or not _is_sha256(infrastructure_safety_evidence_sha256)
            or not _is_sha256(lease_acquisition_safety_evidence_sha256)
            or not _is_sha256(expected_broker_binding_fingerprint)
            or isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < float(timeout_seconds) <= 20
        ):
            raise ValueError("BROKERED_LEASE_CONFIGURATION_INVALID")
        self._base_url = broker_base_url.rstrip("/")
        self._token_provider = provider
        self._ticket_provider = ticket_provider
        self._target_binding_sha256 = target_binding_sha256
        self._lease_binding_sha256 = lease_binding_sha256
        self._infrastructure_safety_evidence_sha256 = (
            infrastructure_safety_evidence_sha256
        )
        self._lease_acquisition_safety_evidence_sha256 = (
            lease_acquisition_safety_evidence_sha256
        )
        self._expected_binding_fingerprint = expected_broker_binding_fingerprint
        self._opener = selected_opener
        self._timeout_seconds = float(timeout_seconds)
        self._fence = threading.Lock()
        self._ticket_lock = threading.Lock()
        self._tickets: dict[str, dict[str, Any]] = {}

    @property
    def target_binding_sha256(self) -> str:
        return self._target_binding_sha256

    @property
    def lease_binding_sha256(self) -> str:
        return self._lease_binding_sha256

    @property
    def infrastructure_safety_evidence_sha256(self) -> str:
        return self._infrastructure_safety_evidence_sha256

    @property
    def lease_acquisition_safety_evidence_sha256(self) -> str:
        return self._lease_acquisition_safety_evidence_sha256

    @contextmanager
    def execution_fence(self, live_action_capability: object = None) -> Iterator[None]:
        del live_action_capability
        if not self._fence.acquire(blocking=False):
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_RUN_BUSY")
        try:
            yield
        finally:
            self._fence.release()

    def acquire(
        self, proposed_lease_id: UUID, live_action_capability: object = None
    ) -> BrokeredLeaseReceipt:
        return self._execute("acquire", proposed_lease_id, live_action_capability)

    def assert_held(
        self, lease_id: UUID, live_action_capability: object = None
    ) -> BrokeredLeaseReceipt:
        return self._execute("assert", lease_id, live_action_capability)

    def release(
        self, lease_id: UUID, live_action_capability: object = None
    ) -> BrokeredLeaseReceipt:
        return self._execute("release", lease_id, live_action_capability)

    def _execute(
        self, operation: str, local_fence_id: UUID, capability: object
    ) -> BrokeredLeaseReceipt:
        if operation not in _OPERATIONS or type(local_fence_id) is not UUID:
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_REQUEST_INVALID")
        action = _OPERATION_ACTIONS[operation]
        _authorize_live_action(
            capability,
            action=action,
            target_binding_sha256=self._target_binding_sha256,
            binding_sha256=self._lease_binding_sha256,
            consume=False,
        )
        _authorize_live_action(
            capability,
            action=action,
            target_binding_sha256=self._target_binding_sha256,
            binding_sha256=self._lease_binding_sha256,
            consume=True,
        )
        try:
            ticket = self._ticket_for(operation)
            token = self._token_provider()
        except Exception:
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_AUTH_UNAVAILABLE") from None
        if type(ticket) is not dict or not _valid_token(token):
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_AUTH_INVALID")
        body = _canonical_json({"ticket": ticket})
        if len(body) > 16_384:
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_REQUEST_INVALID")
        request = urllib.request.Request(
            f"{self._base_url}/v1/internal/performance-lease/{operation}",
            data=body,
            method="POST",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
        )
        try:
            response = self._opener.open(request, timeout=self._timeout_seconds)
            status = getattr(response, "status", None)
            raw = response.read(8_193)
        except (OSError, TimeoutError, urllib.error.URLError):
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_UNAVAILABLE") from None
        if status != 200 or len(raw) > 8_192:
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_DENIED")
        receipt = _validate_receipt(raw, operation=operation)
        if receipt["binding_fingerprint"] != self._expected_binding_fingerprint:
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_BINDING_MISMATCH")
        if receipt["outcome"] not in _SUCCESS[operation]:
            if receipt["retry"] not in {"RETRY_SAME_TICKET", "ASSERT_BEFORE_RETRY"}:
                self._discard_ticket(operation)
            raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_NOT_AVAILABLE")
        self._discard_ticket(operation)
        lifecycle = "RELEASED" if operation == "release" else "HELD"
        return BrokeredLeaseReceipt(
            lease_binding_sha256=self._lease_binding_sha256,
            target_binding_sha256=self._target_binding_sha256,
            lifecycle_state=lifecycle,
            lifecycle_state_sha256=_sha256(lifecycle.encode("ascii")),
            broker_receipt_sha256=_sha256(_canonical_json(receipt)),
        )

    def _ticket_for(self, operation: str) -> dict[str, Any]:
        with self._ticket_lock:
            existing = self._tickets.get(operation)
            if existing is not None:
                return existing
            generated = self._ticket_provider(operation)
            if type(generated) is not dict:
                raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_AUTH_INVALID")
            ticket = dict(generated)
            self._tickets[operation] = ticket
            return ticket

    def _discard_ticket(self, operation: str) -> None:
        with self._ticket_lock:
            self._tickets.pop(operation, None)


def _validate_receipt(raw: bytes, *, operation: str) -> dict[str, str]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_RESPONSE_INVALID") from None
    if (
        type(value) is not dict
        or set(value) != _RECEIPT_FIELDS
        or any(type(item) is not str for item in value.values())
        or value["schema_version"] != RECEIPT_VERSION
        or value["operation"] != ("assert_held" if operation == "assert" else operation)
        or not _is_sha256(value["binding_fingerprint"])
        or not _is_sha256(value["ticket_fingerprint"])
        or value["retry"] not in {
            "NONE",
            "RETRY_SAME_TICKET",
            "ASSERT_BEFORE_RETRY",
            "DO_NOT_RETRY",
        }
    ):
        raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_RESPONSE_INVALID")
    return value


def _valid_token(value: object) -> bool:
    return (
        type(value) is str
        and 32 <= len(value) <= 8_192
        and value == value.strip()
        and all(character not in value for character in "\r\n\x00")
    )


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _canonical_json(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError):
        raise BrokeredAzureBlobLeaseError("BROKERED_LEASE_REQUEST_INVALID") from None


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
