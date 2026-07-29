from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Protocol

from notary_kg.business_case_type_mutation import canonical_hash

from .business_case_type_write_plan import (
    MAX_DEDUPE_ROWS,
    BusinessCaseTypeWritePlan,
    BusinessCaseTypeWritePlanBuilder,
    GraphWriteRequest,
    WritePlanBlocked,
)


ReconciliationState = Literal["clear", "required", "unavailable"]
PersistentIntentState = Literal[
    "absent", "open", "retryable", "closed", "unavailable"
]
CompletionState = Literal["terminal", "retryable"]
_ITEM_ID = re.compile(r"[1-9][0-9]{0,18}\Z")
_RETRYABLE_HTTP_STATUSES = frozenset({401, 403, 408, 429})


@dataclass(frozen=True, slots=True)
class MutationPersistenceState:
    reconciliation_state: ReconciliationState
    intent_state: PersistentIntentState
    intent_generation: int
    closed_generation: int


class GraphWriteTransport(Protocol):
    def request(self, request: GraphWriteRequest) -> GraphResponse: ...


class MutationEvidenceHook(Protocol):
    def persistence_state(
        self, execution_key: str
    ) -> MutationPersistenceState: ...

    def intent(self, evidence: Mapping[str, Any]) -> bool: ...

    def outcome(self, evidence: Mapping[str, Any]) -> bool: ...

    def readback(self, evidence: Mapping[str, Any]) -> bool: ...

    def reconciliation_required(self, evidence: Mapping[str, Any]) -> bool: ...


@dataclass(frozen=True, slots=True)
class GraphResponse:
    status_code: int
    body: Mapping[str, Any]
    headers: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class MutationExecutionResult:
    status: str
    operation: str
    mutation_id: str
    transport_calls: int
    write_attempts: int
    reconciliation_required: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class _Observation:
    state: str
    http_status: int


class BusinessCaseTypeGraphWriteEdge:
    def __init__(
        self,
        transport: GraphWriteTransport,
        evidence_hook: MutationEvidenceHook,
        plan_builder: BusinessCaseTypeWritePlanBuilder,
    ) -> None:
        self._transport = transport
        self._evidence = evidence_hook
        self._plan_builder = plan_builder

    def execute(
        self, plan: BusinessCaseTypeWritePlan
    ) -> MutationExecutionResult:
        try:
            plan = self._plan_builder.revalidate(plan)
        except Exception:
            return _blocked_result(
                status="BLOCKED_PLAN",
                reason_code="plan_revalidation_failed",
            )

        persistence_state = self._persistence_state(plan)
        if persistence_state is None:
            return _result(
                plan,
                status="BLOCKED_RECONCILIATION_STATE",
                transport_calls=0,
                write_attempts=0,
                reconciliation_required=True,
                reason_code="persistence_state_unavailable",
            )
        if persistence_state.intent_state == "closed":
            return _result(
                plan,
                status="BLOCKED_COMPLETED_MUTATION",
                transport_calls=0,
                write_attempts=0,
                reconciliation_required=False,
                reason_code="persistent_closure_blocks_replay",
            )
        if (
            persistence_state.reconciliation_state == "required"
            or persistence_state.intent_state == "open"
        ):
            return _result(
                plan,
                status="BLOCKED_RECONCILIATION",
                transport_calls=0,
                write_attempts=0,
                reconciliation_required=True,
                reason_code=(
                    "open_reconciliation"
                    if persistence_state.reconciliation_state == "required"
                    else "open_persistent_intent"
                ),
            )

        transport_calls = 0
        write_attempts = 0
        if plan.dedupe_request is not None:
            response = self._request(plan.dedupe_request)
            transport_calls += 1
            if response is None:
                return _result(
                    plan,
                    status="BLOCKED_PREFLIGHT_TRANSPORT",
                    transport_calls=transport_calls,
                    write_attempts=0,
                    reconciliation_required=False,
                    reason_code="dedupe_transport_unavailable",
                )
            observation = _dedupe_observation(plan, response)
            if observation.state == "invalid":
                return _result(
                    plan,
                    status="BLOCKED_DEDUPE_READ",
                    transport_calls=transport_calls,
                    write_attempts=0,
                    reconciliation_required=False,
                    reason_code="dedupe_response_invalid",
                )
            if observation.state == "applied":
                candidate_id = _dedupe_candidate_item_id(response)
                candidate_etag = _dedupe_candidate_etag(response)
                if candidate_id is None or candidate_etag is None:
                    return _result(
                        plan,
                        status="BLOCKED_DEDUPE_READ",
                        transport_calls=transport_calls,
                        write_attempts=0,
                        reconciliation_required=False,
                        reason_code="dedupe_response_invalid",
                    )
                intent_generation = self._record_intent(
                    plan, persistence_state
                )
                if intent_generation is None:
                    return _evidence_blocked(plan, transport_calls)
                outcome_ok = self._record_outcome(
                    plan, "deduplicated", intent_generation=intent_generation
                )
                persisted = True
                if not outcome_ok:
                    persisted = self._persist_reconciliation(
                        plan,
                        "dedupe_evidence_incomplete",
                        intent_generation,
                    )
                fresh_response = self._request(
                    plan.item_readback_request(candidate_id)
                )
                transport_calls += 1
                fresh_observation = (
                    _item_observation(
                        plan,
                        fresh_response,
                        expected_item_id=candidate_id,
                    )
                    if fresh_response is not None
                    else _Observation("invalid", 0)
                )
                if (
                    fresh_response is not None
                    and _response_etag(fresh_response) != candidate_etag
                ):
                    fresh_observation = _Observation(
                        "invalid", fresh_observation.http_status
                    )
                verified = outcome_ok and fresh_observation.state == "applied"
                if not verified:
                    persisted = self._persist_reconciliation(
                        plan,
                        "dedupe_fresh_readback_uncertain",
                        intent_generation,
                    )
                readback_ok = self._record_readback(
                    plan,
                    _readback_result_code(fresh_observation),
                    fresh_observation.http_status,
                    intent_generation=intent_generation,
                    close_intent=verified,
                )
                if verified and readback_ok:
                    return _result(
                        plan,
                        status="DEDUPLICATED",
                        transport_calls=transport_calls,
                        write_attempts=0,
                        reconciliation_required=False,
                        reason_code="existing_create_identity",
                    )
                if not readback_ok and verified:
                    persisted = self._persist_reconciliation(
                        plan,
                        "dedupe_evidence_incomplete",
                        intent_generation,
                    )
                return self._reconciliation_result(
                    plan,
                    persisted=persisted,
                    transport_calls=transport_calls,
                    write_attempts=0,
                    reason_code="dedupe_fresh_readback_uncertain",
                )
            if observation.state != "not_applied":
                return self._reconcile_observation_without_write(
                    plan,
                    observation,
                    transport_calls=transport_calls,
                    reason_code="dedupe_collection_ambiguous",
                    persistence_state=persistence_state,
                )

        fresh_etag: str | None = None
        if plan.freshness_request is not None:
            response = self._request(plan.freshness_request)
            transport_calls += 1
            if response is None:
                return _result(
                    plan,
                    status="BLOCKED_PREFLIGHT_TRANSPORT",
                    transport_calls=transport_calls,
                    write_attempts=0,
                    reconciliation_required=False,
                    reason_code="freshness_transport_unavailable",
                )
            observation = _item_observation(
                plan, response, expected_item_id=plan.mutation.item_id
            )
            if observation.state == "invalid":
                return _result(
                    plan,
                    status="BLOCKED_FRESHNESS_READ",
                    transport_calls=transport_calls,
                    write_attempts=0,
                    reconciliation_required=False,
                    reason_code="freshness_response_invalid",
                )
            fresh_etag = _response_etag(response)
            if fresh_etag != plan.mutation.expected_etag:
                return _result(
                    plan,
                    status="BLOCKED_ETAG_DRIFT",
                    transport_calls=transport_calls,
                    write_attempts=0,
                    reconciliation_required=False,
                    reason_code="fresh_etag_mismatch",
                )

        intent_generation = self._record_intent(plan, persistence_state)
        if intent_generation is None:
            return _evidence_blocked(plan, transport_calls)
        try:
            write_request = plan.write_request(fresh_etag=fresh_etag)
        except WritePlanBlocked:
            return _result(
                plan,
                status="BLOCKED_PLAN",
                transport_calls=transport_calls,
                write_attempts=0,
                reconciliation_required=False,
                reason_code="plan_revalidation_failed",
            )
        write_attempts = 1
        write_response = self._request(write_request)
        transport_calls += 1
        if write_response is None:
            self._record_outcome(
                plan,
                "write_state_uncertain",
                intent_generation=intent_generation,
            )
            persisted = self._persist_reconciliation(
                plan, "transport_result_unknown", intent_generation
            )
            observation, calls = self._observe_after_write(
                plan, item_id=_default_readback_item_id(plan)
            )
            transport_calls += calls
            self._record_readback(
                plan,
                _readback_result_code(observation),
                observation.http_status,
                intent_generation=intent_generation,
                close_intent=False,
            )
            return self._reconciliation_result(
                plan,
                persisted=persisted,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reason_code="transport_result_unknown",
            )

        status = _status(write_response)
        if status == 412:
            return self._handle_412(
                plan,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                intent_generation=intent_generation,
            )
        if status == 409 and plan.write_method == "POST":
            return self._handle_409(
                plan,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                intent_generation=intent_generation,
            )
        if status in _RETRYABLE_HTTP_STATUSES:
            return self._handle_retryable_negative(
                plan,
                status=status,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                intent_generation=intent_generation,
            )
        if 500 <= status <= 599:
            self._record_outcome(
                plan,
                "write_state_uncertain",
                status,
                intent_generation=intent_generation,
            )
            persisted = self._persist_reconciliation(
                plan, "provider_5xx", intent_generation
            )
            observation, calls = self._observe_after_write(
                plan,
                item_id=(
                    _response_item_id(write_response)
                    if plan.write_method == "POST"
                    else plan.mutation.item_id
                ),
            )
            transport_calls += calls
            self._record_readback(
                plan,
                _readback_result_code(observation),
                observation.http_status,
                intent_generation=intent_generation,
                close_intent=False,
            )
            return self._reconciliation_result(
                plan,
                persisted=persisted,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reason_code="provider_5xx",
            )

        expected_success = (
            status in {200, 201}
            if plan.write_method == "POST"
            else status in {200, 204}
        )
        if not expected_success:
            return self._handle_negative(
                plan,
                status=status,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                intent_generation=intent_generation,
            )
        return self._handle_success(
            plan,
            write_response=write_response,
            status=status,
            transport_calls=transport_calls,
            write_attempts=write_attempts,
            intent_generation=intent_generation,
        )

    def _handle_retryable_negative(
        self,
        plan: BusinessCaseTypeWritePlan,
        *,
        status: int,
        transport_calls: int,
        write_attempts: int,
        intent_generation: int,
    ) -> MutationExecutionResult:
        outcome_ok = self._record_outcome(
            plan,
            "retryable_rejected",
            status,
            intent_generation=intent_generation,
        )
        observation, calls = self._observe_after_write(
            plan, item_id=_default_readback_item_id(plan)
        )
        transport_calls += calls
        safely_not_applied = outcome_ok and observation.state == "not_applied"
        already_applied = outcome_ok and observation.state == "applied"
        needs_reconciliation = not (safely_not_applied or already_applied)
        persisted = True
        if needs_reconciliation:
            persisted = self._persist_reconciliation(
                plan,
                "retryable_response_readback_uncertain",
                intent_generation,
            )
        readback_ok = self._record_readback(
            plan,
            _readback_result_code(observation),
            observation.http_status,
            intent_generation=intent_generation,
            close_intent=not needs_reconciliation,
            completion_state=(
                "retryable" if safely_not_applied else "terminal"
            ),
        )
        if not readback_ok and not needs_reconciliation:
            needs_reconciliation = True
            persisted = self._persist_reconciliation(
                plan,
                "retryable_response_evidence_incomplete",
                intent_generation,
            )
        if needs_reconciliation:
            return self._reconciliation_result(
                plan,
                persisted=persisted,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reason_code="retryable_response_readback_uncertain",
            )
        if already_applied:
            return _result(
                plan,
                status="RETRYABLE_RESPONSE_STATE_ALREADY_APPLIED",
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reconciliation_required=False,
                reason_code="retryable_response_state_already_applied",
            )
        return _result(
            plan,
            status="RETRYABLE_NOT_APPLIED",
            transport_calls=transport_calls,
            write_attempts=write_attempts,
            reconciliation_required=False,
            reason_code=(
                "authentication_refresh_required"
                if status in {401, 403}
                else "later_authorized_retry_required"
            ),
        )

    def _handle_412(
        self,
        plan: BusinessCaseTypeWritePlan,
        *,
        transport_calls: int,
        write_attempts: int,
        intent_generation: int,
    ) -> MutationExecutionResult:
        outcome_ok = self._record_outcome(
            plan,
            "precondition_failed",
            412,
            intent_generation=intent_generation,
        )
        observation, calls = self._observe_after_write(
            plan, item_id=plan.mutation.item_id
        )
        transport_calls += calls
        needs_reconciliation = not outcome_ok or observation.state == "invalid"
        persisted = True
        if needs_reconciliation:
            persisted = self._persist_reconciliation(
                plan, "precondition_readback_uncertain", intent_generation
            )
        readback_ok = self._record_readback(
            plan,
            _readback_result_code(observation),
            observation.http_status,
            intent_generation=intent_generation,
            close_intent=not needs_reconciliation,
        )
        if not readback_ok and not needs_reconciliation:
            needs_reconciliation = True
            persisted = self._persist_reconciliation(
                plan, "precondition_evidence_incomplete", intent_generation
            )
        if needs_reconciliation:
            return self._reconciliation_result(
                plan,
                persisted=persisted,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reason_code="precondition_readback_uncertain",
            )
        if observation.state == "applied":
            return _result(
                plan,
                status="PRECONDITION_FAILED_ALREADY_APPLIED",
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reconciliation_required=False,
                reason_code="if_match_failed_state_already_applied",
            )
        return _result(
            plan,
            status="PRECONDITION_FAILED",
            transport_calls=transport_calls,
            write_attempts=write_attempts,
            reconciliation_required=False,
            reason_code="if_match_precondition_failed_no_retry",
        )

    def _handle_409(
        self,
        plan: BusinessCaseTypeWritePlan,
        *,
        transport_calls: int,
        write_attempts: int,
        intent_generation: int,
    ) -> MutationExecutionResult:
        outcome_ok = self._record_outcome(
            plan,
            "create_conflict",
            409,
            intent_generation=intent_generation,
        )
        observation, calls = self._observe_after_write(plan, item_id=None)
        transport_calls += calls
        needs_reconciliation = (
            not outcome_ok
            or observation.state not in {"applied", "not_applied"}
        )
        persisted = True
        if needs_reconciliation:
            persisted = self._persist_reconciliation(
                plan, "create_conflict_readback_uncertain", intent_generation
            )
        readback_ok = self._record_readback(
            plan,
            _readback_result_code(observation),
            observation.http_status,
            intent_generation=intent_generation,
            close_intent=not needs_reconciliation,
        )
        if not readback_ok and not needs_reconciliation:
            needs_reconciliation = True
            persisted = self._persist_reconciliation(
                plan, "create_conflict_evidence_incomplete", intent_generation
            )
        if needs_reconciliation:
            return self._reconciliation_result(
                plan,
                persisted=persisted,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reason_code="create_conflict_readback_uncertain",
            )
        if observation.state == "applied":
            return _result(
                plan,
                status="DEDUPLICATED",
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reconciliation_required=False,
                reason_code="concurrent_create_identity",
            )
        return _result(
            plan,
            status="WRITE_REJECTED",
            transport_calls=transport_calls,
            write_attempts=write_attempts,
            reconciliation_required=False,
            reason_code="provider_rejected_create",
        )

    def _handle_negative(
        self,
        plan: BusinessCaseTypeWritePlan,
        *,
        status: int,
        transport_calls: int,
        write_attempts: int,
        intent_generation: int,
    ) -> MutationExecutionResult:
        outcome_ok = self._record_outcome(
            plan,
            "failed",
            status,
            intent_generation=intent_generation,
        )
        observation, calls = self._observe_after_write(
            plan, item_id=plan.mutation.item_id
        )
        transport_calls += calls
        needs_reconciliation = not outcome_ok or observation.state == "invalid"
        persisted = True
        if needs_reconciliation:
            persisted = self._persist_reconciliation(
                plan, "negative_readback_uncertain", intent_generation
            )
        readback_ok = self._record_readback(
            plan,
            _readback_result_code(observation),
            observation.http_status,
            intent_generation=intent_generation,
            close_intent=not needs_reconciliation,
        )
        if not readback_ok and not needs_reconciliation:
            needs_reconciliation = True
            persisted = self._persist_reconciliation(
                plan, "negative_evidence_incomplete", intent_generation
            )
        if needs_reconciliation:
            return self._reconciliation_result(
                plan,
                persisted=persisted,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reason_code="negative_readback_uncertain",
            )
        if observation.state == "applied":
            return _result(
                plan,
                status="WRITE_REJECTED_STATE_ALREADY_APPLIED",
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reconciliation_required=False,
                reason_code="provider_rejected_state_already_applied",
            )
        return _result(
            plan,
            status="WRITE_REJECTED",
            transport_calls=transport_calls,
            write_attempts=write_attempts,
            reconciliation_required=False,
            reason_code="provider_rejected_write",
        )

    def _handle_success(
        self,
        plan: BusinessCaseTypeWritePlan,
        *,
        write_response: GraphResponse,
        status: int,
        transport_calls: int,
        write_attempts: int,
        intent_generation: int,
    ) -> MutationExecutionResult:
        outcome_ok = self._record_outcome(
            plan,
            "confirmed",
            status,
            intent_generation=intent_generation,
        )
        item_id = (
            _response_item_id(write_response)
            if plan.write_method == "POST"
            else plan.mutation.item_id
        )
        preexisting_uncertainty = not outcome_ok or item_id is None
        persisted = True
        if preexisting_uncertainty:
            persisted = self._persist_reconciliation(
                plan, "write_completion_uncertain", intent_generation
            )
        observation, calls = self._observe_after_write(plan, item_id=item_id)
        transport_calls += calls
        needs_reconciliation = (
            preexisting_uncertainty or observation.state != "applied"
        )
        if needs_reconciliation and not preexisting_uncertainty:
            persisted = self._persist_reconciliation(
                plan, "readback_not_verified", intent_generation
            )
        readback_ok = self._record_readback(
            plan,
            _readback_result_code(observation),
            observation.http_status,
            intent_generation=intent_generation,
            close_intent=not needs_reconciliation,
        )
        if not readback_ok and not needs_reconciliation:
            needs_reconciliation = True
            persisted = self._persist_reconciliation(
                plan, "readback_evidence_incomplete", intent_generation
            )
        if needs_reconciliation:
            return self._reconciliation_result(
                plan,
                persisted=persisted,
                transport_calls=transport_calls,
                write_attempts=write_attempts,
                reason_code="write_completion_uncertain",
            )
        return _result(
            plan,
            status="APPLIED",
            transport_calls=transport_calls,
            write_attempts=write_attempts,
            reconciliation_required=False,
            reason_code="write_and_readback_verified",
        )

    def _reconcile_observation_without_write(
        self,
        plan: BusinessCaseTypeWritePlan,
        observation: _Observation,
        *,
        transport_calls: int,
        reason_code: str,
        persistence_state: MutationPersistenceState,
    ) -> MutationExecutionResult:
        intent_generation = self._record_intent(plan, persistence_state)
        if intent_generation is None:
            return _evidence_blocked(plan, transport_calls)
        self._record_outcome(
            plan,
            "write_state_uncertain",
            intent_generation=intent_generation,
        )
        persisted = self._persist_reconciliation(
            plan, reason_code, intent_generation
        )
        self._record_readback(
            plan,
            "not_verified",
            observation.http_status,
            intent_generation=intent_generation,
            close_intent=False,
        )
        return self._reconciliation_result(
            plan,
            persisted=persisted,
            transport_calls=transport_calls,
            write_attempts=0,
            reason_code=reason_code,
        )

    def _reconciliation_result(
        self,
        plan: BusinessCaseTypeWritePlan,
        *,
        persisted: bool,
        transport_calls: int,
        write_attempts: int,
        reason_code: str,
    ) -> MutationExecutionResult:
        return _result(
            plan,
            status=(
                "RECONCILIATION_REQUIRED"
                if persisted
                else "RECONCILIATION_PERSISTENCE_FAILED"
            ),
            transport_calls=transport_calls,
            write_attempts=write_attempts,
            reconciliation_required=True,
            reason_code=(
                reason_code
                if persisted
                else "reconciliation_persistence_unavailable"
            ),
        )

    def _observe_after_write(
        self,
        plan: BusinessCaseTypeWritePlan,
        *,
        item_id: str | None,
    ) -> tuple[_Observation, int]:
        try:
            request = (
                plan.item_readback_request(item_id)
                if item_id is not None
                else plan.collection_readback_request()
            )
        except Exception:
            return _Observation("invalid", 0), 0
        response = self._request(request)
        if response is None:
            return _Observation("invalid", 0), 1
        if item_id is None:
            return _dedupe_observation(plan, response), 1
        return _item_observation(plan, response, expected_item_id=item_id), 1

    def _request(self, request: GraphWriteRequest) -> GraphResponse | None:
        try:
            response = self._transport.request(request)
        except Exception:
            return None
        return response if isinstance(response, GraphResponse) else None

    def _persistence_state(
        self, plan: BusinessCaseTypeWritePlan
    ) -> MutationPersistenceState | None:
        try:
            state = self._evidence.persistence_state(_execution_key(plan))
        except Exception:
            return None
        validated = _validated_persistence_state(state)
        if validated is not None and validated.intent_state == "absent":
            # Compatibility for pre-S4b test hooks. Runtime persistence hooks
            # must key state by execution_key from the evidence payload.
            try:
                legacy = _validated_persistence_state(
                    self._evidence.persistence_state(
                        plan.mutation.mutation_id
                    )
                )
            except Exception:
                legacy = None
            if legacy is not None and legacy.intent_state != "absent":
                return legacy
        return validated

    def _persist_reconciliation(
        self,
        plan: BusinessCaseTypeWritePlan,
        reason_code: str,
        intent_generation: int,
    ) -> bool:
        try:
            acknowledged = self._evidence.reconciliation_required(
                _evidence(
                    plan,
                    result_code=reason_code,
                    intent_generation=intent_generation,
                )
            )
        except Exception:
            return False
        if acknowledged is not True:
            return False
        state = self._persistence_state(plan)
        return bool(
            state is not None
            and state.reconciliation_state == "required"
            and state.intent_state == "open"
            and state.intent_generation == intent_generation
            and state.closed_generation < intent_generation
        )

    def _record_intent(
        self,
        plan: BusinessCaseTypeWritePlan,
        prior_state: MutationPersistenceState,
    ) -> int | None:
        expected_generation = prior_state.intent_generation
        intent_generation = expected_generation + 1
        try:
            acknowledged = self._evidence.intent(
                _evidence(
                    plan,
                    result_code="planned",
                    intent_generation=intent_generation,
                    expected_intent_generation=expected_generation,
                )
            )
        except Exception:
            return None
        if acknowledged is not True:
            return None
        state = self._persistence_state(plan)
        if (
            state is None
            or state.reconciliation_state != "clear"
            or state.intent_state != "open"
            or state.intent_generation != intent_generation
            or state.closed_generation != expected_generation
        ):
            return None
        return intent_generation

    def _record_outcome(
        self,
        plan: BusinessCaseTypeWritePlan,
        result_code: str,
        http_status: int | None = None,
        *,
        intent_generation: int,
    ) -> bool:
        try:
            acknowledged = self._evidence.outcome(
                _evidence(
                    plan,
                    result_code=result_code,
                    http_status=http_status,
                    intent_generation=intent_generation,
                )
            )
        except Exception:
            return False
        return acknowledged is True

    def _record_readback(
        self,
        plan: BusinessCaseTypeWritePlan,
        result_code: str,
        http_status: int,
        *,
        intent_generation: int,
        close_intent: bool,
        completion_state: CompletionState = "terminal",
    ) -> bool:
        try:
            acknowledged = self._evidence.readback(
                _evidence(
                    plan,
                    result_code=result_code,
                    http_status=http_status,
                    intent_generation=intent_generation,
                    close_intent=close_intent,
                    completion_state=completion_state,
                )
            )
        except Exception:
            return False
        if acknowledged is not True:
            return False
        state = self._persistence_state(plan)
        if state is None or state.intent_generation != intent_generation:
            return False
        if close_intent:
            return bool(
                state.reconciliation_state == "clear"
                and state.intent_state
                == (
                    "retryable"
                    if completion_state == "retryable"
                    else "closed"
                )
                and state.closed_generation == intent_generation
            )
        return bool(
            state.intent_state == "open"
            and state.closed_generation < intent_generation
        )


def _validated_persistence_state(
    state: Any,
) -> MutationPersistenceState | None:
    if not isinstance(state, MutationPersistenceState):
        return None
    if (
        state.reconciliation_state not in {"clear", "required"}
        or state.intent_state not in {"absent", "open", "retryable", "closed"}
        or type(state.intent_generation) is not int
        or type(state.closed_generation) is not int
        or not 0 <= state.closed_generation <= state.intent_generation < 2**63
    ):
        return None
    valid_shape = (
        state.intent_state == "absent"
        and state.intent_generation == 0
        and state.closed_generation == 0
    ) or (
        state.intent_state == "open"
        and state.intent_generation == state.closed_generation + 1
    ) or (
        state.intent_state in {"retryable", "closed"}
        and state.intent_generation > 0
        and state.closed_generation == state.intent_generation
    )
    if not valid_shape:
        return None
    if (
        state.reconciliation_state == "required"
        and state.intent_state != "open"
    ):
        return None
    return state


def _blocked_result(*, status: str, reason_code: str) -> MutationExecutionResult:
    return MutationExecutionResult(
        status=status,
        operation="blocked",
        mutation_id="0" * 64,
        transport_calls=0,
        write_attempts=0,
        reconciliation_required=False,
        reason_code=reason_code,
    )


def _evidence_blocked(
    plan: BusinessCaseTypeWritePlan, transport_calls: int
) -> MutationExecutionResult:
    return _result(
        plan,
        status="BLOCKED_EVIDENCE",
        transport_calls=transport_calls,
        write_attempts=0,
        reconciliation_required=True,
        reason_code="intent_not_persisted_or_verified",
    )


def _result(
    plan: BusinessCaseTypeWritePlan,
    *,
    status: str,
    transport_calls: int,
    write_attempts: int,
    reconciliation_required: bool,
    reason_code: str,
) -> MutationExecutionResult:
    return MutationExecutionResult(
        status=status,
        operation=plan.mutation.operation,
        mutation_id=plan.mutation.mutation_id,
        transport_calls=transport_calls,
        write_attempts=write_attempts,
        reconciliation_required=reconciliation_required,
        reason_code=reason_code,
    )


def _evidence(
    plan: BusinessCaseTypeWritePlan,
    *,
    result_code: str,
    http_status: int | None = None,
    intent_generation: int | None = None,
    expected_intent_generation: int | None = None,
    close_intent: bool | None = None,
    completion_state: CompletionState | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "nac.business-case-type-write-evidence-hook/v0.1",
        "mutation_id": plan.mutation.mutation_id,
        "execution_key": _execution_key(plan),
        "operation": plan.mutation.operation,
        "target_binding_hash": plan.target_binding_hash,
        "plan_sha256": plan.plan_sha256,
        "result_code": result_code,
    }
    if plan.mutation.s5_operation_hash is not None:
        payload["s5_operation_hash"] = plan.mutation.s5_operation_hash
    if http_status is not None:
        payload["http_status"] = http_status
    if intent_generation is not None:
        payload["intent_generation"] = intent_generation
    if expected_intent_generation is not None:
        payload["expected_intent_generation"] = expected_intent_generation
    if close_intent is not None:
        payload["close_intent"] = close_intent
    if completion_state is not None:
        payload["completion_state"] = completion_state
    return payload


def _execution_key(plan: BusinessCaseTypeWritePlan) -> str:
    return canonical_hash(
        {
            "target_binding_hash": plan.target_binding_hash,
            "mutation_id": plan.mutation.mutation_id,
        }
    )


def _single_dedupe_row(
    response: GraphResponse,
) -> Mapping[str, Any] | None:
    if not isinstance(response.body, Mapping):
        return None
    rows = response.body.get("value")
    if type(rows) is not list or len(rows) != 1:
        return None
    row = rows[0]
    return row if isinstance(row, Mapping) else None


def _dedupe_candidate_item_id(response: GraphResponse) -> str | None:
    row = _single_dedupe_row(response)
    if row is None:
        return None
    item_id = row.get("id")
    return (
        item_id
        if type(item_id) is str and _ITEM_ID.fullmatch(item_id)
        else None
    )


def _dedupe_candidate_etag(response: GraphResponse) -> str | None:
    row = _single_dedupe_row(response)
    if row is None:
        return None
    etag = row.get("eTag")
    return etag if type(etag) is str and etag else None


def _dedupe_observation(
    plan: BusinessCaseTypeWritePlan,
    response: GraphResponse,
) -> _Observation:
    status = _status(response)
    if status != 200 or not isinstance(response.body, Mapping):
        return _Observation("invalid", status)
    if "@odata.nextLink" in response.body:
        return _Observation("paged", status)
    rows = response.body.get("value")
    if type(rows) is not list or len(rows) > MAX_DEDUPE_ROWS:
        return _Observation("invalid", status)
    dedupe_field = plan.mutation.dedupe_field
    if dedupe_field is None:
        return _Observation("invalid", status)
    if not rows:
        return _Observation("not_applied", status)
    states: list[str] = []
    for row in rows:
        if not isinstance(row, Mapping):
            return _Observation("invalid", status)
        row_state = _row_state(
            plan, row, expected_item_id=None, require_dedupe_identity=True
        )
        if row_state == "invalid":
            return _Observation("invalid", status)
        states.append(row_state)
    if len(states) > 1:
        return _Observation("duplicate", status)
    return _Observation(
        "divergent" if states[0] == "not_applied" else states[0],
        status,
    )


def _item_observation(
    plan: BusinessCaseTypeWritePlan,
    response: GraphResponse,
    *,
    expected_item_id: str | None,
) -> _Observation:
    status = _status(response)
    if status != 200 or not isinstance(response.body, Mapping):
        return _Observation("invalid", status)
    return _Observation(
        _row_state(
            plan,
            response.body,
            expected_item_id=expected_item_id,
            require_dedupe_identity=False,
        ),
        status,
    )


def _row_state(
    plan: BusinessCaseTypeWritePlan,
    row: Mapping[str, Any],
    *,
    expected_item_id: str | None,
    require_dedupe_identity: bool,
) -> str:
    item_id = row.get("id")
    etag = row.get("eTag")
    fields = row.get("fields")
    if (
        type(item_id) is not str
        or _ITEM_ID.fullmatch(item_id) is None
        or (expected_item_id is not None and item_id != expected_item_id)
        or type(etag) is not str
        or not etag
        or not isinstance(fields, Mapping)
        or set(fields) != set(plan.mutation.fields)
    ):
        return "invalid"
    if require_dedupe_identity:
        dedupe_field = plan.mutation.dedupe_field
        if (
            dedupe_field is None
            or fields.get(dedupe_field) != plan.mutation.fields[dedupe_field]
        ):
            return "invalid"
    return (
        "applied"
        if all(
            fields.get(name) == value
            for name, value in plan.mutation.fields.items()
        )
        else "not_applied"
    )


def _readback_result_code(observation: _Observation) -> str:
    if observation.state == "applied":
        return "verified_applied"
    if observation.state == "not_applied":
        return "verified_not_applied"
    return "not_verified"


def _default_readback_item_id(
    plan: BusinessCaseTypeWritePlan,
) -> str | None:
    return plan.mutation.item_id if plan.write_method == "PATCH" else None


def _response_etag(response: GraphResponse) -> str | None:
    if not isinstance(response.body, Mapping):
        return None
    etag = response.body.get("eTag")
    return etag if type(etag) is str and etag else None


def _response_item_id(response: GraphResponse) -> str | None:
    if not isinstance(response.body, Mapping):
        return None
    item_id = response.body.get("id")
    if type(item_id) is str and _ITEM_ID.fullmatch(item_id) is not None:
        return item_id
    return None


def _status(response: GraphResponse) -> int:
    return response.status_code if type(response.status_code) is int else 0
