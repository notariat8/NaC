"""Inactive, request-local terminal denial result for the synthetic BFF.

These codes are not a public response or a telemetry sink. Inference-bearing
codes must not leave process memory without a separately approved privacy gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from .test_environment import AccessDecision, AccessMode


GRAPH_READ_UNAVAILABLE = "GRAPH_READ_UNAVAILABLE"
CASE_BINDING_INVALID = "CASE_BINDING_INVALID"
ACTOR_ASSIGNMENT_MISSING = "ACTOR_ASSIGNMENT_MISSING"
DEPUTY_GRANT_INVALID = "DEPUTY_GRANT_INVALID"
GRANT_AUDIT_INVALID = "GRANT_AUDIT_INVALID"
DECISION_PROJECTION_INVALID = "DECISION_PROJECTION_INVALID"
DENIAL_UNCLASSIFIED = "DENIAL_UNCLASSIFIED"

TERMINAL_REASONS = frozenset({
    GRAPH_READ_UNAVAILABLE,
    CASE_BINDING_INVALID,
    ACTOR_ASSIGNMENT_MISSING,
    DEPUTY_GRANT_INVALID,
    GRANT_AUDIT_INVALID,
    DECISION_PROJECTION_INVALID,
    DENIAL_UNCLASSIFIED,
})


@dataclass(frozen=True, slots=True, repr=False)
class PrivateDecisionResult:
    decision: AccessDecision
    reason_class: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, AccessDecision):
            raise TypeError("invalid decision")
        if self.reason_class is not None and self.reason_class not in TERMINAL_REASONS:
            raise ValueError("invalid terminal reason")
        if (self.decision.mode is AccessMode.DENY) != (self.reason_class is not None):
            raise ValueError("terminal reason and decision disagree")

    def __repr__(self) -> str:
        return "PrivateDecisionResult(redacted)"


class TerminalReasonCapture:
    """One request's in-memory terminal reason, with no output or sink method."""

    __slots__ = ("reason_class",)

    def __init__(self) -> None:
        self.reason_class: str | None = None

    def record(self, reason_class: str) -> None:
        if reason_class not in TERMINAL_REASONS:
            raise ValueError("invalid terminal reason")
        if self.reason_class is not None:
            raise ValueError("terminal reason already recorded")
        self.reason_class = reason_class

    def __repr__(self) -> str:
        return "TerminalReasonCapture(redacted)"


__all__ = [
    "ACTOR_ASSIGNMENT_MISSING",
    "CASE_BINDING_INVALID",
    "DECISION_PROJECTION_INVALID",
    "DENIAL_UNCLASSIFIED",
    "DEPUTY_GRANT_INVALID",
    "GRAPH_READ_UNAVAILABLE",
    "GRANT_AUDIT_INVALID",
    "PrivateDecisionResult",
    "TERMINAL_REASONS",
    "TerminalReasonCapture",
]
