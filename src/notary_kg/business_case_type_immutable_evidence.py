from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from nac_runtime.immutable_evidence import (
    LIVE_STATUS,
    EvidencePhase,
    EvidenceRecord,
    ImmutableEvidencePublisher,
    S6_STATUS,
    InMemoryEvidenceOutbox,
    InMemoryReconciliationStore,
    actor_ref,
    build_event,
    correlation_ref,
    typed_identifier_registry,
    verify_chain,
)

from .business_case_type_runtime import BusinessCaseTypeCatalog


_TENANT_ID = "00000000-0000-4000-8000-000000000001"
_ACTOR_ID = "11111111-1111-4111-8111-111111111111"
_OPERATOR_ID = "22222222-2222-4222-8222-222222222222"
_APPROVER_ID = "33333333-3333-4333-8333-333333333333"
_SYNTHETIC_KEY = hashlib.sha256(b"nac-s6-synthetic-test-key-only").digest()
_SYNTHETIC_PRINCIPAL_KEY = hashlib.sha256(
    b"nac-s6-synthetic-principal-key-only"
).digest()
_NORMAL_CORRELATION = correlation_ref(
    tenant_id=_TENANT_ID,
    source_object_id="44444444-4444-4444-8444-444444444444",
    key_version=1,
    key=_SYNTHETIC_KEY,
)
_RECONCILIATION_CORRELATION = correlation_ref(
    tenant_id=_TENANT_ID,
    source_object_id="55555555-5555-4555-8555-555555555555",
    key_version=1,
    key=_SYNTHETIC_KEY,
)
_MANIFEST_SHA256 = hashlib.sha256(b"nac-s6-synthetic-manifest").hexdigest()
_OCCURRED_AT = "2026-07-20T12:00:00Z"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CATALOG = BusinessCaseTypeCatalog.from_repo(_REPO_ROOT)
_IDENTIFIER_REGISTRY = typed_identifier_registry(
    business_case_type_ids={
        entry.business_case_type_id for entry in _CATALOG.entries
    },
    catalog_versions={_CATALOG.catalog_version},
)


def build_synthetic_evidence_dry_run() -> dict[str, Any]:
    actor = actor_ref(
        tenant_id=_TENANT_ID,
        actor_object_id=_ACTOR_ID,
        key_version=1,
        key=_SYNTHETIC_KEY,
        principal_key=_SYNTHETIC_PRINCIPAL_KEY,
    )
    operator = actor_ref(
        tenant_id=_TENANT_ID,
        actor_object_id=_OPERATOR_ID,
        key_version=1,
        key=_SYNTHETIC_KEY,
        principal_key=_SYNTHETIC_PRINCIPAL_KEY,
    )
    approver = actor_ref(
        tenant_id=_TENANT_ID,
        actor_object_id=_APPROVER_ID,
        key_version=1,
        key=_SYNTHETIC_KEY,
        principal_key=_SYNTHETIC_PRINCIPAL_KEY,
    )

    normal = InMemoryEvidenceOutbox()
    _append(normal, _NORMAL_CORRELATION, actor, "intent")
    _append(
        normal,
        _NORMAL_CORRELATION,
        actor,
        "outcome",
        result_code="confirmed",
        etags={"matter": "synthetic-etag-2"},
    )
    _append(
        normal,
        _NORMAL_CORRELATION,
        actor,
        "readback",
        result_code="verified",
        etags={"matter": "synthetic-etag-2"},
    )

    reconciliation = InMemoryEvidenceOutbox()
    reconciliation_store = InMemoryReconciliationStore()
    _append(reconciliation, _RECONCILIATION_CORRELATION, actor, "intent")
    _append(
        reconciliation,
        _RECONCILIATION_CORRELATION,
        actor,
        "outcome",
        result_code="write-state-uncertain",
    )
    reconciliation_store.require(
        _RECONCILIATION_CORRELATION,
        "provider-readback-required",
        reconciliation.records(_RECONCILIATION_CORRELATION)[-1].event_sha256,
    )
    _append(
        reconciliation,
        _RECONCILIATION_CORRELATION,
        actor,
        "reconciliation_required",
        reconciliation_reason_code="provider-readback-required",
    )
    _append(
        reconciliation,
        _RECONCILIATION_CORRELATION,
        actor,
        "readback",
        result_code="verified",
        etags={"matter": "synthetic-etag-3"},
    )
    _append(
        reconciliation,
        _RECONCILIATION_CORRELATION,
        actor,
        "reconciliation_closed",
        result_code="reconciled",
        reconciliation_operator_ref=operator,
        reconciliation_approver_ref=approver,
    )
    reconciliation_store.close(
        _RECONCILIATION_CORRELATION,
        records=reconciliation.records(_RECONCILIATION_CORRELATION),
        operator_ref=operator,
        approver_ref=approver,
    )

    normal_publication = _publisher(normal, reconciliation_store).finalize(
        _NORMAL_CORRELATION
    )
    reconciliation_publication = _publisher(
        reconciliation, reconciliation_store
    ).finalize(_RECONCILIATION_CORRELATION)

    return {
        "schema_version": "nac.business-case-type-immutable-evidence-s6-dry-run/v0.1",
        "status": S6_STATUS,
        "live_status": LIVE_STATUS,
        "contains_production_data": False,
        "network_calls": 0,
        "provider_calls": 0,
        "tenant_calls": 0,
        "tenant_writes": 0,
        "credential_reads": 0,
        "live_mutations": 0,
        "production_worm_claim": False,
        "normal_chain": verify_chain(normal.records(_NORMAL_CORRELATION)),
        "reconciliation_chain": verify_chain(
            reconciliation.records(_RECONCILIATION_CORRELATION)
        ),
        "reconciliation_store_clear": not reconciliation_store.is_required(
            _RECONCILIATION_CORRELATION
        ),
        "normal_publication": normal_publication,
        "reconciliation_publication": reconciliation_publication,
        "required_production_ports": [
            "postgresql_outbox",
            "broker_with_dlq",
            "detached_signature_and_daily_anchor",
            "worm_journal_with_retention_readback",
            "persistent_reconciliation_store",
        ],
        "next_gate": "S6B_PROVIDER_ADAPTERS_AND_S7_DUAL_APPROVAL",
    }


class _SyntheticBroker:
    def publish(self, record: EvidenceRecord) -> dict[str, Any]:
        return {
            "ack_ref": f"broker-ack-v1-{record.event_sha256}",
            "event_id": record.event["event_id"],
            "event_sha256": record.event_sha256,
            "idempotency_key_sha256": record.event["idempotency_key_sha256"],
            "delivery_key_sha256": record.event["delivery_key_sha256"],
        }


class _SyntheticSignatureAnchor:
    def __init__(self) -> None:
        self._receipts: dict[str, dict[str, Any]] = {}
        self._by_idempotency_key: dict[str, dict[str, Any]] = {}

    def anchor(
        self,
        records: tuple[EvidenceRecord, ...],
        *,
        idempotency_key_sha256: str,
    ) -> dict[str, Any]:
        if idempotency_key_sha256 in self._by_idempotency_key:
            return dict(self._by_idempotency_key[idempotency_key_sha256])
        head = records[-1].event_sha256
        receipt = {
            "anchor_ref": f"anchor-v1-{head}",
            "signature_ref": f"signature-v1-{head}",
            "record_count": len(records),
            "first_event_sha256": records[0].event_sha256,
            "last_event_sha256": head,
            "head_sha256": head,
        }
        self._receipts[receipt["anchor_ref"]] = receipt
        self._by_idempotency_key[idempotency_key_sha256] = receipt
        return dict(receipt)

    def readback(self, anchor_ref: str) -> dict[str, Any]:
        return dict(self._receipts[anchor_ref])


class _SyntheticWormJournal:
    def __init__(self) -> None:
        self._receipts: dict[str, dict[str, Any]] = {}
        self._by_idempotency_key: dict[str, dict[str, Any]] = {}

    def commit(
        self,
        records: tuple[EvidenceRecord, ...],
        anchor: dict[str, Any],
        *,
        idempotency_key_sha256: str,
    ) -> dict[str, Any]:
        if idempotency_key_sha256 in self._by_idempotency_key:
            return dict(self._by_idempotency_key[idempotency_key_sha256])
        receipt_ref = f"worm-receipt-v1-{anchor['head_sha256']}"
        receipt = {
            "receipt_ref": receipt_ref,
            "head_sha256": records[-1].event_sha256,
        }
        self._by_idempotency_key[idempotency_key_sha256] = receipt
        self._receipts[receipt_ref] = {
            **receipt,
            "retention_years": records[0].event["retention"]["minimum_years"],
            "legal_hold_capable": records[0].event["retention"][
                "legal_hold_capable"
            ],
        }
        return receipt

    def readback(self, receipt_ref: str) -> dict[str, Any]:
        return dict(self._receipts[receipt_ref])


def _publisher(
    outbox: InMemoryEvidenceOutbox,
    reconciliation_store: InMemoryReconciliationStore,
) -> ImmutableEvidencePublisher:
    return ImmutableEvidencePublisher(
        outbox=outbox,
        broker=_SyntheticBroker(),
        signature_anchor=_SyntheticSignatureAnchor(),
        worm_journal=_SyntheticWormJournal(),
        reconciliation_store=reconciliation_store,
    )


def _append(
    outbox: InMemoryEvidenceOutbox,
    correlation_id: str,
    actor: str,
    phase: EvidencePhase,
    *,
    result_code: str | None = None,
    etags: dict[str, str] | None = None,
    reconciliation_reason_code: str | None = None,
    reconciliation_operator_ref: str | None = None,
    reconciliation_approver_ref: str | None = None,
) -> None:
    records = outbox.records(correlation_id)
    sequence = len(records) + 1
    previous = records[-1].event_sha256 if records else "0" * 64
    event = build_event(
        correlation_id=correlation_id,
        phase=phase,
        sequence=sequence,
        previous_event_sha256=previous,
        actor_ref_value=actor,
        tool_id="tool-nac-kg-business-case-type-evidence",
        role_id="role-automation",
        action="backfill",
        business_case_type_id="immobilienkaufvertrag",
        catalog_version=_CATALOG.catalog_version,
        identifier_registry=_IDENTIFIER_REGISTRY,
        manifest_sha256=_MANIFEST_SHA256,
        etag_hmac_key=_SYNTHETIC_KEY,
        etag_hmac_key_version=1,
        occurred_at=_OCCURRED_AT,
        result_code=result_code,
        etags=etags,
        reconciliation_reason_code=reconciliation_reason_code,
        reconciliation_operator_ref=reconciliation_operator_ref,
        reconciliation_approver_ref=reconciliation_approver_ref,
    )
    outbox.append(event)
