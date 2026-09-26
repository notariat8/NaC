"""Private, inactive-by-default diagnostic data for a synthetic workbench 403.

This module performs no I/O and never enables telemetry. A later, separately
authorized composition may supply a sink after proving its release bindings.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import hmac
from queue import Empty, Full, Queue
import re

from .test_environment import ALLOWED_MATTER_ID, ALLOWED_WORKSPACE_ID


REQUEST_SCOPE_REJECTED = "REQUEST_SCOPE_REJECTED"
ACCESS_DECISION_UNAVAILABLE = "ACCESS_DECISION_UNAVAILABLE"
ACCESS_DECISION_REJECTED = "ACCESS_DECISION_REJECTED"
DENIAL_UNCLASSIFIED = "DENIAL_UNCLASSIFIED"
REASON_CLASSES = frozenset(
    {
        REQUEST_SCOPE_REJECTED,
        ACCESS_DECISION_UNAVAILABLE,
        ACCESS_DECISION_REJECTED,
        DENIAL_UNCLASSIFIED,
    }
)
SCHEMA_VERSION = "nac.bff-403-diagnostic-event/v1"
_CORRELATION = re.compile(
    rb"spfx-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z"
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_ROUTE = (
    f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/"
    f"{ALLOWED_MATTER_ID}/workbench-snapshot"
)


@dataclass(slots=True)
class DenialReasonState:
    """One request's private decision, shared across the ASGI worker thread."""

    reason_class: str | None = None

    def record(self, reason_class: str) -> None:
        if reason_class not in REASON_CLASSES:
            raise ValueError("unknown diagnostic reason")
        if self.reason_class is not None:
            raise ValueError("diagnostic reason already recorded")
        self.reason_class = reason_class


class InactiveDiagnosticBuffer:
    """Bounded, process-local test buffer; never forwards data to a provider.

    This deliberately is not a telemetry sink or an activation interface. A
    separate approved release must implement and gate any external delivery.
    """

    __slots__ = ("_events",)

    def __init__(self) -> None:
        self._events: Queue[dict[str, str | int]] = Queue(maxsize=1)

    def record_nowait(self, event: dict[str, str | int]) -> bool:
        try:
            self._events.put_nowait(event)
        except Full:
            return False
        return True

    def take_nowait(self) -> dict[str, str | int] | None:
        try:
            return self._events.get_nowait()
        except Empty:
            return None


def is_bounded_workbench_get(*, path: object, method: object) -> bool:
    return path == _ROUTE and method == "GET"


def correlation_binding_from_scope(scope: Mapping[str, object]) -> str | None:
    """Hash exactly one canonical *received* header; never use fallback IDs."""

    headers = scope.get("headers")
    if not isinstance(headers, (list, tuple)):
        return None
    values: list[bytes] = []
    for pair in headers:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return None
        name, value = pair
        if not isinstance(name, bytes) or not isinstance(value, bytes):
            return None
        if name.lower() == b"x-correlation-id":
            values.append(value)
    if len(values) != 1 or _CORRELATION.fullmatch(values[0]) is None:
        return None
    return hashlib.sha256(values[0]).hexdigest()


def matches_protected_receipt(
    event_binding_sha256: object, receipt_binding_sha256: object
) -> bool:
    """Compare digests only; this does not establish receipt provenance."""

    return (
        isinstance(event_binding_sha256, str)
        and isinstance(receipt_binding_sha256, str)
        and _SHA256.fullmatch(event_binding_sha256) is not None
        and _SHA256.fullmatch(receipt_binding_sha256) is not None
        and hmac.compare_digest(event_binding_sha256, receipt_binding_sha256)
    )


def build_event(
    *,
    reason_class: str,
    correlation_binding_sha256: str,
    observed_at: datetime,
) -> dict[str, str | int]:
    """Build only the closed allowlist; never accept request-controlled text."""

    if reason_class not in REASON_CLASSES:
        raise ValueError("unknown diagnostic reason")
    if not isinstance(correlation_binding_sha256, str) or _SHA256.fullmatch(
        correlation_binding_sha256
    ) is None:
        raise ValueError("invalid correlation binding")
    if (
        not isinstance(observed_at, datetime)
        or observed_at.tzinfo is None
        or not 2020 <= observed_at.year <= 2100
    ):
        raise ValueError("invalid diagnostic timestamp")
    normalized = observed_at.astimezone(UTC).replace(microsecond=0)
    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at_utc": normalized.isoformat().replace("+00:00", "Z"),
        "route_class": "workbench_snapshot",
        "method": "GET",
        "http_class": 403,
        "reason_class": reason_class,
        "request_correlation_binding_sha256": correlation_binding_sha256,
    }
