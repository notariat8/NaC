from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Mapping

from notary_kg.business_case_type_mutation import canonical_hash

from nac_runtime.immutable_evidence import (
    ZERO_HASH,
    ImmutableEvidencePublisher,
    OutboxPort,
    build_event,
    canonical_json_bytes,
)

from .business_case_type_write_edge import (
    MutationEvidenceHook,
    MutationPersistenceState,
)


class LiveWriteEvidenceError(RuntimeError):
    """Redacted failure at the composed S4d evidence boundary."""


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class LiveWriteEvidenceContext:
    correlation_id: str
    actor_ref_value: str
    tool_id: str
    role_id: str
    action: str
    business_case_type_id: str
    catalog_version: str
    identifier_registry: Any
    manifest_sha256: str
    etag_hmac_key: bytes
    etag_hmac_key_version: int
    occurred_at: Callable[[], str]
    operation_binding_sha256: str


class S4dMutationEvidenceHook(MutationEvidenceHook):
    """Closes local S4c state only after complete canonical WORM readback."""

    def __init__(
        self,
        *,
        local: MutationEvidenceHook,
        outbox: OutboxPort,
        publisher: ImmutableEvidencePublisher,
        context: LiveWriteEvidenceContext,
    ) -> None:
        self._local = local
        self._outbox = outbox
        self._publisher = publisher
        self._context = context
        self._publication_result: dict[str, Any] | None = None

    @property
    def publication_result(self) -> Mapping[str, Any] | None:
        return (
            dict(self._publication_result)
            if self._publication_result is not None
            else None
        )

    def persistence_state(
        self, execution_key: str
    ) -> MutationPersistenceState:
        return self._local.persistence_state(execution_key)

    def intent(self, evidence: Mapping[str, Any]) -> bool:
        if self._local.intent(evidence) is not True:
            return False
        try:
            self._append("intent", evidence)
            return True
        except Exception:
            self._require_local_reconciliation(evidence)
            return False

    def outcome(self, evidence: Mapping[str, Any]) -> bool:
        if self._local.outcome(evidence) is not True:
            return False
        try:
            self._append("outcome", evidence)
            return True
        except Exception:
            return False

    def reconciliation_required(self, evidence: Mapping[str, Any]) -> bool:
        local_ok = self._require_local_reconciliation(evidence)
        try:
            self._append("reconciliation_required", evidence)
        except Exception:
            pass
        return local_ok

    def readback(self, evidence: Mapping[str, Any]) -> bool:
        close_intent = evidence.get("close_intent") is True
        try:
            self._append("readback", evidence)
            if close_intent:
                result = self._publisher.finalize(
                    self._context.correlation_id
                )
                self._publication_result = _validated_publication_result(
                    result,
                    correlation_id=self._context.correlation_id,
                )
            return self._local.readback(_local_evidence(evidence)) is True
        except Exception:
            self._require_local_reconciliation(evidence)
            if close_intent:
                self._record_non_closing_readback(evidence)
            return False

    def _append(
        self, phase: str, evidence: Mapping[str, Any]
    ) -> None:
        operation_binding = s4d_evidence_operation_binding_sha256(evidence)
        if (
            evidence.get("operation") != self._context.action
            or operation_binding != self._context.operation_binding_sha256
        ):
            raise LiveWriteEvidenceError(
                "canonical mutation binding is invalid"
            )
        records = self._outbox.records(self._context.correlation_id)
        matches = [
            (index, record)
            for index, record in enumerate(records)
            if record.event.get("phase") == phase
        ]
        if len(matches) > 1:
            raise LiveWriteEvidenceError(
                "canonical outbox contains duplicate phases"
            )
        existing = matches[0] if matches else None
        if existing is None:
            sequence = len(records) + 1
            previous = records[-1].event_sha256 if records else ZERO_HASH
            occurred_at = self._context.occurred_at()
        else:
            index, record = existing
            sequence = index + 1
            previous = records[index - 1].event_sha256 if index else ZERO_HASH
            occurred_at = record.event["occurred_at"]
        event = build_event(
            correlation_id=self._context.correlation_id,
            phase=phase,
            sequence=sequence,
            previous_event_sha256=previous,
            actor_ref_value=self._context.actor_ref_value,
            tool_id=self._context.tool_id,
            role_id=self._context.role_id,
            action=self._context.action,
            business_case_type_id=self._context.business_case_type_id,
            catalog_version=self._context.catalog_version,
            identifier_registry=self._context.identifier_registry,
            manifest_sha256=self._context.manifest_sha256,
            occurred_at=occurred_at,
            result_code=_canonical_result_code(phase, evidence),
            etags={},
            etag_hmac_key=self._context.etag_hmac_key,
            etag_hmac_key_version=self._context.etag_hmac_key_version,
            operation_binding_sha256=operation_binding,
            provider_state_sha256=(
                evidence.get("provider_state_sha256")
                if phase == "readback"
                else None
            ),
            reconciliation_reason_code=(
                "provider-readback-required"
                if phase == "reconciliation_required"
                else None
            ),
        )
        if existing is not None:
            if canonical_json_bytes(event) != canonical_json_bytes(
                existing[1].event
            ):
                raise LiveWriteEvidenceError(
                    "canonical outbox phase belongs to another mutation"
                )
            return
        record = self._outbox.append(event)
        readback = self._outbox.records(self._context.correlation_id)
        if (
            not readback
            or readback[-1].event_sha256 != record.event_sha256
        ):
            raise LiveWriteEvidenceError(
                "canonical outbox readback is incomplete"
            )

    def _require_local_reconciliation(
        self, evidence: Mapping[str, Any]
    ) -> bool:
        generation = evidence.get("intent_generation")
        execution_key = evidence.get("execution_key")
        if type(execution_key) is not str or type(generation) is not int:
            return False
        try:
            state = self._local.persistence_state(execution_key)
        except Exception:
            return False
        if (
            state.reconciliation_state == "required"
            and state.intent_state == "open"
            and state.intent_generation == generation
            and state.authorization_run_identity
            == evidence.get("authorization_run_identity")
        ):
            return True
        reconciliation = {
            field: evidence[field]
            for field in (
                "schema_version",
                "mutation_id",
                "execution_key",
                "operation",
                "target_binding_hash",
                "plan_sha256",
                "authorization_run_identity",
                "intent_generation",
            )
            if field in evidence
        }
        if "s5_operation_hash" in evidence:
            reconciliation["s5_operation_hash"] = evidence[
                "s5_operation_hash"
            ]
        reconciliation["result_code"] = "write_completion_uncertain"
        return self._local.reconciliation_required(reconciliation) is True

    def _record_non_closing_readback(
        self, evidence: Mapping[str, Any]
    ) -> bool:
        non_closing = {
            field: evidence[field]
            for field in (
                "schema_version",
                "mutation_id",
                "execution_key",
                "operation",
                "target_binding_hash",
                "plan_sha256",
                "authorization_run_identity",
                "intent_generation",
                "http_status",
            )
            if field in evidence
        }
        if "s5_operation_hash" in evidence:
            non_closing["s5_operation_hash"] = evidence[
                "s5_operation_hash"
            ]
        non_closing.update(
            result_code="not_verified",
            close_intent=False,
            completion_state="terminal",
        )
        return self._local.readback(non_closing) is True


def _local_evidence(evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in evidence.items()
        if key != "provider_state_sha256"
    }


def s4d_evidence_operation_binding_sha256(
    evidence: Mapping[str, Any],
) -> str:
    required = (
        "mutation_id",
        "execution_key",
        "operation",
        "target_binding_hash",
        "plan_sha256",
        "authorization_run_identity",
    )
    payload: dict[str, Any] = {
        "schema_version": "nac.s4d-operation-binding/v0.1",
    }
    for field in required:
        value = evidence.get(field)
        if type(value) is not str or not value:
            raise LiveWriteEvidenceError(
                f"canonical mutation field is invalid: {field}"
            )
        payload[field] = value
    if "s5_operation_hash" in evidence:
        value = evidence["s5_operation_hash"]
        if type(value) is not str or _SHA256.fullmatch(value) is None:
            raise LiveWriteEvidenceError(
                "canonical mutation field is invalid: s5_operation_hash"
            )
        payload["s5_operation_hash"] = value
    return canonical_hash(payload)


def _canonical_result_code(
    phase: str, evidence: Mapping[str, Any]
) -> str | None:
    result_code = evidence.get("result_code")
    if phase == "intent" or phase == "reconciliation_required":
        return None
    if phase == "outcome":
        if result_code in {"confirmed", "deduplicated"}:
            return "confirmed"
        if result_code == "write_state_uncertain":
            return "write-state-uncertain"
        return "failed"
    if phase == "readback":
        return "verified" if result_code == "verified_applied" else "failed"
    raise LiveWriteEvidenceError("canonical evidence phase is invalid")


def _validated_publication_result(
    result: Mapping[str, Any], *, correlation_id: str
) -> dict[str, Any]:
    fields = {
        "schema_version",
        "status",
        "correlation_id",
        "chain_head_sha256",
        "event_count",
        "broker_ack_count",
        "anchor_ref_sha256",
        "signature_ref_sha256",
        "worm_receipt_ref_sha256",
        "worm_readback_ref_sha256",
        "worm_readback_verified",
        "production_durability_claim",
    }
    if not isinstance(result, Mapping) or set(result) != fields:
        raise LiveWriteEvidenceError("canonical publication is incomplete")
    if (
        result["schema_version"]
        != "nac.immutable-evidence-publication/v0.1"
        or result["status"]
        != "SYNTHETIC_PORT_ORCHESTRATION_COMPLETE"
        or result["correlation_id"] != correlation_id
        or result["event_count"] != 3
        or result["broker_ack_count"] != 3
        or result["worm_readback_verified"] is not True
        or result["production_durability_claim"] is not False
    ):
        raise LiveWriteEvidenceError("canonical publication is incomplete")
    for field in (
        "chain_head_sha256",
        "anchor_ref_sha256",
        "signature_ref_sha256",
        "worm_receipt_ref_sha256",
        "worm_readback_ref_sha256",
    ):
        if (
            type(result[field]) is not str
            or _SHA256.fullmatch(result[field]) is None
        ):
            raise LiveWriteEvidenceError(
                "canonical publication binding is invalid"
            )
    if result["worm_receipt_ref_sha256"] != result["worm_readback_ref_sha256"]:
        raise LiveWriteEvidenceError(
            "canonical WORM readback binding is invalid"
        )
    return dict(result)
