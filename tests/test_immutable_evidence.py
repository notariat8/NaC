from __future__ import annotations

import gc
import hashlib
import hmac
import sys
import unittest
import weakref
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_runtime.immutable_evidence import (  # noqa: E402
    LIVE_STATUS,
    MINIMUM_RETENTION_YEARS,
    REGISTERED_BUSINESS_CASE_TYPE_IDS,
    REGISTERED_CATALOG_VERSIONS,
    S6_STATUS,
    ZERO_HASH,
    EvidenceRecord,
    ImmutableEvidenceError,
    ImmutableEvidencePublisher,
    InMemoryEvidenceOutbox,
    _ACTOR_REF_AUTHORITY,
    _CORRELATION_REF_AUTHORITY,
    _EVIDENCE_EVENT_AUTHORITY,
    _IDENTIFIER_REGISTRY_AUTHORITY,
    _ReconciliationStateError,
    InMemoryReconciliationStore,
    actor_ref,
    build_event,
    canonical_json_bytes,
    correlation_ref,
    typed_identifier_registry,
    verify_chain,
)


TENANT_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_OBJECT_ID = "22222222-2222-4222-8222-222222222222"
OPERATOR_OBJECT_ID = "33333333-3333-4333-8333-333333333333"
APPROVER_OBJECT_ID = "44444444-4444-4444-8444-444444444444"
ACTOR_KEY = b"actor-key-for-immutable-evidence"  # exactly 32 bytes
PRINCIPAL_KEY = b"stable-principal-binding-key-0001"
SOURCE_OBJECT_ID = "55555555-5555-4555-8555-555555555555"
CORRELATION_ID = correlation_ref(
    tenant_id=TENANT_ID,
    source_object_id=SOURCE_OBJECT_ID,
    key_version=3,
    key=ACTOR_KEY,
)
MANIFEST_SHA256 = "a" * 64
CATALOG_VERSION = next(iter(REGISTERED_CATALOG_VERSIONS))
SECOND_CATALOG_VERSION = "c" * 64
IDENTIFIER_REGISTRY = typed_identifier_registry(
    business_case_type_ids=REGISTERED_BUSINESS_CASE_TYPE_IDS,
    catalog_versions=REGISTERED_CATALOG_VERSIONS,
)


class _Broker:
    def __init__(
        self,
        *,
        missing_ack: bool = False,
        mutate_record: bool = False,
        unbound_ack: bool = False,
        duplicate_ack: bool = False,
        semantic_ack: bool = False,
        fail_after: int | None = None,
    ) -> None:
        self.missing_ack = missing_ack
        self.mutate_record = mutate_record
        self.unbound_ack = unbound_ack
        self.duplicate_ack = duplicate_ack
        self.semantic_ack = semantic_ack
        self.fail_after = fail_after
        self.calls = 0

    def publish(self, record: EvidenceRecord) -> dict[str, Any]:
        self.calls += 1
        event_id = record.event["event_id"]
        event_sha256 = record.event_sha256
        idempotency = record.event["idempotency_key_sha256"]
        delivery = record.event["delivery_key_sha256"]
        if self.mutate_record:
            record.event["tool_id"] = "mutated-by-port"
        if self.missing_ack or (
            self.fail_after is not None and self.calls > self.fail_after
        ):
            return {}
        ack_hash = "0" * 64 if self.duplicate_ack else event_sha256
        return {
            "ack_ref": (
                "broker-ack-v1-max-mustermann"
                if self.semantic_ack
                else f"broker-ack-v1-{ack_hash}"
            ),
            "event_id": "event-" + "f" * 64 if self.unbound_ack else event_id,
            "event_sha256": event_sha256,
            "idempotency_key_sha256": idempotency,
            "delivery_key_sha256": delivery,
        }


class _Anchor:
    def __init__(
        self, *, valid: bool = True, readback_valid: bool = True
    ) -> None:
        self.valid = valid
        self.readback_valid = readback_valid
        self.receipts: dict[str, dict[str, Any]] = {}
        self.anchor_calls = 0
        self.anchor_effects = 0
        self.readback_calls = 0
        self._by_idempotency_key: dict[str, dict[str, Any]] = {}

    def anchor(
        self,
        records: tuple[EvidenceRecord, ...],
        *,
        idempotency_key_sha256: str,
    ) -> dict[str, Any]:
        self.anchor_calls += 1
        if idempotency_key_sha256 in self._by_idempotency_key:
            return dict(self._by_idempotency_key[idempotency_key_sha256])
        self.anchor_effects += 1
        head = records[-1].event_sha256
        receipt = {
            "anchor_ref": f"anchor-v1-{head}",
            "signature_ref": f"signature-v1-{head}",
            "record_count": len(records) if self.valid else 0,
            "first_event_sha256": records[0].event_sha256,
            "last_event_sha256": head,
            "head_sha256": head,
        }
        self.receipts[receipt["anchor_ref"]] = receipt
        self._by_idempotency_key[idempotency_key_sha256] = receipt
        return dict(receipt)

    def readback(self, anchor_ref: str) -> dict[str, Any]:
        self.readback_calls += 1
        receipt = dict(self.receipts[anchor_ref])
        if not self.readback_valid:
            receipt["head_sha256"] = "f" * 64
        return receipt


class _Worm:
    def __init__(
        self,
        *,
        readback_verified: bool = True,
        retention_years: int | None = None,
    ) -> None:
        self.readback_verified = readback_verified
        self.retention_years = retention_years
        self.receipts: dict[str, dict[str, Any]] = {}
        self.commit_calls = 0
        self.commit_effects = 0
        self.readback_calls = 0
        self._by_idempotency_key: dict[str, dict[str, Any]] = {}

    def commit(
        self,
        records: tuple[EvidenceRecord, ...],
        anchor: dict[str, Any],
        *,
        idempotency_key_sha256: str,
    ) -> dict[str, Any]:
        self.commit_calls += 1
        if idempotency_key_sha256 in self._by_idempotency_key:
            return dict(self._by_idempotency_key[idempotency_key_sha256])
        self.commit_effects += 1
        receipt_ref = f"worm-receipt-v1-{anchor['head_sha256']}"
        receipt = {
            "receipt_ref": receipt_ref,
            "head_sha256": records[-1].event_sha256,
        }
        self._by_idempotency_key[idempotency_key_sha256] = receipt
        self.receipts[receipt_ref] = {
            **receipt,
            "retention_years": (
                self.retention_years
                if self.retention_years is not None
                else records[0].event["retention"]["minimum_years"]
            ),
            "legal_hold_capable": self.readback_verified,
        }
        return receipt

    def readback(self, receipt_ref: str) -> dict[str, Any]:
        self.readback_calls += 1
        return dict(self.receipts[receipt_ref])


class ImmutableEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actor = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=ACTOR_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=PRINCIPAL_KEY,
        )
        self.operator = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=OPERATOR_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=PRINCIPAL_KEY,
        )
        self.approver = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=APPROVER_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=PRINCIPAL_KEY,
        )

    def _event(
        self,
        phase: str,
        *,
        sequence: int,
        previous_event_sha256: str,
        **overrides: Any,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {
            "correlation_id": CORRELATION_ID,
            "phase": phase,
            "sequence": sequence,
            "previous_event_sha256": previous_event_sha256,
            "actor_ref_value": self.actor,
            "tool_id": "tool-nac-cli",
            "role_id": "role-migration-operator",
            "action": "schema_apply",
            "business_case_type_id": "immobilienkaufvertrag",
            "catalog_version": CATALOG_VERSION,
            "identifier_registry": IDENTIFIER_REGISTRY,
            "manifest_sha256": MANIFEST_SHA256,
            "etag_hmac_key": ACTOR_KEY,
            "etag_hmac_key_version": 1,
            "occurred_at": "2026-07-20T12:00:00Z",
        }
        if phase in {"outcome", "readback"}:
            values["result_code"] = "confirmed"
            values["etags"] = {
                "matter": "synthetic-state-etag"
            }
        elif phase == "reconciliation_required":
            values["reconciliation_reason_code"] = "readback-missing"
        elif phase == "reconciliation_closed":
            values.update(
                result_code="reconciled",
                reconciliation_operator_ref=self.operator,
                reconciliation_approver_ref=self.approver,
            )
        values.update(overrides)
        return build_event(**values)

    def _append(
        self,
        outbox: InMemoryEvidenceOutbox,
        phase: str,
        **overrides: Any,
    ) -> EvidenceRecord:
        records = outbox.records(CORRELATION_ID)
        return outbox.append(
            self._event(
                phase,
                sequence=len(records) + 1,
                previous_event_sha256=(
                    records[-1].event_sha256 if records else ZERO_HASH
                ),
                **overrides,
            )
        )

    def _normal_chain(self) -> tuple[EvidenceRecord, ...]:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome")
        self._append(outbox, "readback")
        return outbox.records(CORRELATION_ID)

    @staticmethod
    def _rehash(event: dict[str, Any]) -> EvidenceRecord:
        return EvidenceRecord(
            event=event,
            event_sha256=hashlib.sha256(canonical_json_bytes(event)).hexdigest(),
        )

    def test_actor_ref_uses_versioned_tenant_bound_hmac(self) -> None:
        domain = (
            b"nac.actor-ref.v1\x00"
            + TENANT_ID.encode("ascii")
            + b"\x00k3\x00"
        )
        expected_digest = hmac.new(
            ACTOR_KEY,
            domain + ACTOR_OBJECT_ID.encode("ascii"),
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(self.actor, f"actor-v1-k3-{expected_digest}")
        self.assertEqual(
            self.actor,
            actor_ref(
                tenant_id=TENANT_ID,
                actor_object_id=ACTOR_OBJECT_ID,
                key_version=3,
                key=ACTOR_KEY,
                principal_key=PRINCIPAL_KEY,
            ),
        )
        self.assertNotIn(TENANT_ID, self.actor)
        self.assertNotIn(ACTOR_OBJECT_ID, self.actor)

    def test_actor_ref_changes_with_tenant_key_version_actor_and_key(self) -> None:
        alternatives = (
            actor_ref(
                tenant_id="55555555-5555-4555-8555-555555555555",
                actor_object_id=ACTOR_OBJECT_ID,
                key_version=3,
                key=ACTOR_KEY,
                principal_key=PRINCIPAL_KEY,
            ),
            actor_ref(
                tenant_id=TENANT_ID,
                actor_object_id=ACTOR_OBJECT_ID,
                key_version=4,
                key=ACTOR_KEY,
                principal_key=PRINCIPAL_KEY,
            ),
            actor_ref(
                tenant_id=TENANT_ID,
                actor_object_id=OPERATOR_OBJECT_ID,
                key_version=3,
                key=ACTOR_KEY,
                principal_key=PRINCIPAL_KEY,
            ),
            actor_ref(
                tenant_id=TENANT_ID,
                actor_object_id=ACTOR_OBJECT_ID,
                key_version=3,
                key=b"different-actor-key-material-0001",
                principal_key=PRINCIPAL_KEY,
            ),
        )

        self.assertEqual(len(set(alternatives)), len(alternatives))
        for alternative in alternatives:
            self.assertNotEqual(alternative, self.actor)
            self.assertRegex(alternative, r"^actor-v1-k[0-9]+-[0-9a-f]{64}$")

    def test_actor_ref_rejects_invalid_identifiers_versions_and_keys(self) -> None:
        valid = {
            "tenant_id": TENANT_ID,
            "actor_object_id": ACTOR_OBJECT_ID,
            "key_version": 3,
            "key": ACTOR_KEY,
            "principal_key": PRINCIPAL_KEY,
        }
        invalid_overrides = (
            {"tenant_id": "not-a-uuid"},
            {"actor_object_id": "{22222222-2222-4222-8222-222222222222}"},
            {"key_version": 0},
            {"key_version": True},
            {"key": b"too-short"},
            {"key": bytearray(ACTOR_KEY)},
            {"principal_key": b"too-short"},
            {"principal_key": bytearray(PRINCIPAL_KEY)},
        )

        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ImmutableEvidenceError):
                    actor_ref(**(valid | overrides))

    def test_identifier_registry_authority_cannot_be_resealed(self) -> None:
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "must exactly match the S3 catalog"
        ):
            typed_identifier_registry(
                business_case_type_ids={"forged-case-type"},
                catalog_versions={"f" * 64},
            )
        original_case_types = IDENTIFIER_REGISTRY.business_case_type_ids
        original_versions = IDENTIFIER_REGISTRY.catalog_versions
        object.__setattr__(
            IDENTIFIER_REGISTRY,
            "business_case_type_ids",
            frozenset({"forged-case-type"}),
        )
        object.__setattr__(
            IDENTIFIER_REGISTRY,
            "catalog_versions",
            frozenset({"f" * 64}),
        )

        self.assertEqual(
            IDENTIFIER_REGISTRY.business_case_type_ids, original_case_types
        )
        self.assertEqual(
            IDENTIFIER_REGISTRY.catalog_versions, original_versions
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "not a registered typed identifier"
        ):
            self._event(
                "intent",
                sequence=1,
                previous_event_sha256=ZERO_HASH,
                business_case_type_id="forged-case-type",
            )

    def test_authority_registries_release_dead_verified_objects(self) -> None:
        def temporary_authorities() -> tuple[
            tuple[int, weakref.ReferenceType[Any], dict[int, tuple[Any, ...]]],
            ...,
        ]:
            temporary_actor = actor_ref(
                tenant_id=TENANT_ID,
                actor_object_id="77777777-7777-4777-8777-777777777777",
                key_version=3,
                key=ACTOR_KEY,
                principal_key=PRINCIPAL_KEY,
            )
            temporary_correlation = correlation_ref(
                tenant_id=TENANT_ID,
                source_object_id="88888888-8888-4888-8888-888888888888",
                key_version=3,
                key=ACTOR_KEY,
            )
            temporary_registry = typed_identifier_registry(
                business_case_type_ids=REGISTERED_BUSINESS_CASE_TYPE_IDS,
                catalog_versions=REGISTERED_CATALOG_VERSIONS,
            )
            temporary_event = self._event(
                "intent",
                sequence=1,
                previous_event_sha256=ZERO_HASH,
                correlation_id=temporary_correlation,
                actor_ref_value=temporary_actor,
                identifier_registry=temporary_registry,
            )
            return (
                (
                    id(temporary_actor),
                    weakref.ref(temporary_actor),
                    _ACTOR_REF_AUTHORITY,
                ),
                (
                    id(temporary_correlation),
                    weakref.ref(temporary_correlation),
                    _CORRELATION_REF_AUTHORITY,
                ),
                (
                    id(temporary_registry),
                    weakref.ref(temporary_registry),
                    _IDENTIFIER_REGISTRY_AUTHORITY,
                ),
                (
                    id(temporary_event),
                    weakref.ref(temporary_event),
                    _EVIDENCE_EVENT_AUTHORITY,
                ),
            )

        authorities = temporary_authorities()
        gc.collect()

        for object_id, reference, registry in authorities:
            self.assertIsNone(reference())
            self.assertNotIn(object_id, registry)

    def test_normal_intent_outcome_readback_chain_is_complete(self) -> None:
        records = self._normal_chain()

        status = verify_chain(records)

        self.assertEqual(
            [record.event["phase"] for record in records],
            ["intent", "outcome", "readback"],
        )
        self.assertEqual(records[0].event["previous_event_sha256"], ZERO_HASH)
        self.assertEqual(
            records[1].event["previous_event_sha256"], records[0].event_sha256
        )
        self.assertEqual(
            records[2].event["previous_event_sha256"], records[1].event_sha256
        )
        self.assertEqual(status["schema_version"], "nac.immutable-evidence-chain-status/v0.1")
        self.assertEqual(status["s6_status"], S6_STATUS)
        self.assertEqual(status["live_status"], LIVE_STATUS)
        self.assertEqual(status["correlation_id"], CORRELATION_ID)
        self.assertEqual(status["event_count"], 3)
        self.assertEqual(status["head_sha256"], records[-1].event_sha256)
        self.assertEqual(status["phases"], ["intent", "outcome", "readback"])
        self.assertTrue(status["complete"])
        self.assertFalse(status["reconciliation_required"])
        self.assertFalse(status["production_worm_claim"])

    def test_reconciliation_chain_stays_required_until_dual_control_close(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        store = InMemoryReconciliationStore()
        self._append(outbox, "intent")
        self._append(
            outbox, "outcome", result_code="write-state-uncertain"
        )
        required_head = outbox.records(CORRELATION_ID)[-1].event_sha256
        store.require(CORRELATION_ID, "readback-missing", required_head)
        self._append(outbox, "reconciliation_required")

        required_status = verify_chain(outbox.records(CORRELATION_ID))
        self.assertFalse(required_status["complete"])
        self.assertTrue(required_status["reconciliation_required"])
        self.assertTrue(store.is_required(CORRELATION_ID))

        self._append(outbox, "readback")
        readback_status = verify_chain(outbox.records(CORRELATION_ID))
        self.assertFalse(readback_status["complete"])
        self.assertTrue(readback_status["reconciliation_required"])

        self._append(outbox, "reconciliation_closed")
        store.close(
            CORRELATION_ID,
            operator_ref=self.operator,
            records=outbox.records(CORRELATION_ID),
            approver_ref=self.approver,
        )
        closed_status = verify_chain(outbox.records(CORRELATION_ID))

        self.assertEqual(
            closed_status["phases"],
            [
                "intent",
                "outcome",
                "reconciliation_required",
                "readback",
                "reconciliation_closed",
            ],
        )
        self.assertTrue(closed_status["complete"])
        self.assertFalse(closed_status["reconciliation_required"])
        self.assertFalse(store.is_required(CORRELATION_ID))

    def test_reconciliation_close_requires_separate_principals(self) -> None:
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "requires separate principals"
        ):
            self._event(
                "reconciliation_closed",
                sequence=5,
                previous_event_sha256="b" * 64,
                reconciliation_operator_ref=self.operator,
                reconciliation_approver_ref=self.operator,
            )

        store = InMemoryReconciliationStore()
        store.require(CORRELATION_ID, "readback-missing", MANIFEST_SHA256)
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "requires separate principals"
        ):
            store.close(
                CORRELATION_ID,
                operator_ref=self.operator,
                records=(),
                approver_ref=self.operator,
            )
        self.assertTrue(store.is_required(CORRELATION_ID))

    def test_build_event_enforces_phase_specific_fields(self) -> None:
        invalid_cases = (
            ("intent", {"result_code": "unexpected"}),
            ("intent", {"reconciliation_reason_code": "unexpected"}),
            ("outcome", {"result_code": None}),
            ("outcome", {"reconciliation_reason_code": "unexpected"}),
            ("readback", {"result_code": None}),
            (
                "reconciliation_required",
                {"reconciliation_reason_code": None},
            ),
            ("reconciliation_required", {"result_code": "unexpected"}),
            (
                "reconciliation_closed",
                {"reconciliation_operator_ref": None},
            ),
            (
                "reconciliation_closed",
                {"reconciliation_approver_ref": None},
            ),
        )

        for phase, overrides in invalid_cases:
            with self.subTest(phase=phase, overrides=overrides):
                with self.assertRaises(ImmutableEvidenceError):
                    self._event(
                        phase,
                        sequence=1 if phase == "intent" else 2,
                        previous_event_sha256=(
                            ZERO_HASH if phase == "intent" else "b" * 64
                        ),
                        **overrides,
                    )

    def test_reconciliation_rejects_undeclared_repeated_requirement(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(
            outbox,
            "reconciliation_required",
            reconciliation_reason_code="readback-missing",
        )
        self._append(outbox, "readback", result_code="failed")

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "phase transition is invalid"
        ):
            self._append(
                outbox,
                "reconciliation_required",
                reconciliation_reason_code="provider-readback-required",
            )

    def test_declared_readback_recovery_sequence_remains_complete(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="failed")
        self._append(
            outbox,
            "reconciliation_required",
            reconciliation_reason_code="provider-readback-required",
        )
        self._append(outbox, "readback", result_code="verified")
        self._append(
            outbox, "reconciliation_closed", result_code="reconciled"
        )

        status = verify_chain(outbox.records(CORRELATION_ID))

        self.assertTrue(status["complete"])
        self.assertFalse(status["reconciliation_required"])

    def test_outbox_rejects_invalid_phase_transitions(self) -> None:
        outcome_first = InMemoryEvidenceOutbox()
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "phase transition is invalid"
        ):
            outcome_first.append(
                self._event(
                    "outcome",
                    sequence=1,
                    previous_event_sha256=ZERO_HASH,
                )
            )

        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "phase transition is invalid"
        ):
            self._append(outbox, "readback")
        self.assertEqual(len(outbox.records(CORRELATION_ID)), 1)

    def test_verify_chain_rejects_empty_and_non_record_input(self) -> None:
        with self.assertRaisesRegex(ImmutableEvidenceError, "chain is empty"):
            verify_chain(())
        with self.assertRaisesRegex(ImmutableEvidenceError, "record is invalid"):
            verify_chain(({"event": "not-a-record"},))

    def test_verify_chain_detects_event_hash_tamper(self) -> None:
        records = list(self._normal_chain())
        tampered_event = dict(records[1].event, result_code="tampered")
        records[1] = EvidenceRecord(
            event=tampered_event,
            event_sha256=records[1].event_sha256,
        )

        with self.assertRaisesRegex(ImmutableEvidenceError, "event hash is invalid"):
            verify_chain(records)

    def test_verify_chain_detects_sequence_tamper_even_with_rehashed_event(self) -> None:
        records = list(self._normal_chain())
        records[1] = self._rehash(dict(records[1].event, sequence=7))

        with self.assertRaisesRegex(ImmutableEvidenceError, "event sequence is invalid"):
            verify_chain(records)

    def test_verify_chain_detects_previous_hash_tamper_even_when_rehashed(self) -> None:
        records = list(self._normal_chain())
        records[1] = self._rehash(
            dict(records[1].event, previous_event_sha256="f" * 64)
        )

        with self.assertRaisesRegex(ImmutableEvidenceError, "event chain is invalid"):
            verify_chain(records)

    def test_verify_chain_detects_correlation_and_envelope_binding_tamper(self) -> None:
        records = self._normal_chain()
        binding_changes = {
            "correlation_id": "foreign-correlation",
            "actor_ref": self.operator,
            "tool_id": "tool-nac-kg-business-case-type-migration",
            "role_id": "role-migration-reviewer",
            "action": "rollback",
            "business_case_type_id": "handelsregisteranmeldung",
            "catalog_version": SECOND_CATALOG_VERSION,
            "manifest_sha256": "f" * 64,
        }

        for field, value in binding_changes.items():
            with self.subTest(field=field):
                changed = dict(records[1].event, **{field: value})
                with self.assertRaisesRegex(
                    ImmutableEvidenceError,
                    "correlation binding changed|evidence binding changed",
                ):
                    verify_chain((records[0], self._rehash(changed)))

    def test_verify_chain_rejects_rehashed_policy_and_identity_tamper(self) -> None:
        intent = self._normal_chain()[0]
        tampered_events = (
            dict(
                intent.event,
                retention={
                    "minimum_years": MINIMUM_RETENTION_YEARS - 1,
                    "legal_hold_capable": True,
                },
            ),
            dict(
                intent.event,
                privacy={
                    "classification": "public",
                    "read_role": "all_users",
                    "monthly_access_review_required": False,
                },
            ),
            dict(intent.event, event_id="event-" + "f" * 64),
            dict(intent.event, idempotency_key_sha256="f" * 64),
            dict(intent.event, unexpected_payload="forbidden"),
        )

        for event in tampered_events:
            with self.subTest(fields=sorted(event)):
                with self.assertRaises(ImmutableEvidenceError):
                    verify_chain((self._rehash(event),))


    def test_outbox_rejects_skipped_sequence_wrong_hash_and_duplicate(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        intent = self._append(outbox, "intent")

        skipped = self._event(
            "outcome",
            sequence=3,
            previous_event_sha256=intent.event_sha256,
        )
        with self.assertRaisesRegex(ImmutableEvidenceError, "sequence is not contiguous"):
            outbox.append(skipped)

        wrongly_bound = self._event(
            "outcome",
            sequence=2,
            previous_event_sha256="f" * 64,
        )
        with self.assertRaisesRegex(ImmutableEvidenceError, "hash binding is invalid"):
            outbox.append(wrongly_bound)

        with self.assertRaises(ImmutableEvidenceError):
            outbox.append(intent.event)
        self.assertEqual(outbox.records(CORRELATION_ID), (intent,))

        with self.assertRaises(ImmutableEvidenceError):
            verify_chain((intent, intent))

    def test_outbox_canonicalizes_and_copies_input(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        event = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            etags={"task": '"z"', "deadline": '"a"'},
        )

        record = outbox.append(event)
        event["tool_id"] = "mutated-after-append"

        self.assertEqual(record.event["tool_id"], "tool-nac-cli")
        self.assertEqual(list(record.event["etags"]), ["deadline", "task"])
        self.assertEqual(
            record.event_sha256,
            hashlib.sha256(canonical_json_bytes(record.event)).hexdigest(),
        )
        record.event["tool_id"] = "mutated-return-record"
        first_read = outbox.records(CORRELATION_ID)
        self.assertEqual(first_read[0].event["tool_id"], "tool-nac-cli")
        first_read[0].event["tool_id"] = "mutated-read-record"
        self.assertEqual(
            outbox.records(CORRELATION_ID)[0].event["tool_id"],
            "tool-nac-cli",
        )

    def test_sensitive_fields_are_rejected_at_any_depth_case_insensitively(self) -> None:
        forbidden_fields = (
            "actor_object_id",
            "entra_object_id",
            "owner_id",
            "private_key",
            "client_secret",
            "access_token",
            "refresh_token",
            "raw_payload",
            "document_content",
            "aktenzeichen",
            "mandatsdaten",
        )

        for field in forbidden_fields:
            with self.subTest(field=field):
                with self.assertRaisesRegex(
                    ImmutableEvidenceError, "sensitive evidence field is forbidden"
                ):
                    canonical_json_bytes(
                        {"safe": [{field.upper(): "must-not-be-persisted"}]}
                    )

    def test_canonical_json_rejects_non_json_and_non_string_object_keys(self) -> None:
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "JSON object keys must be strings"
        ):
            canonical_json_bytes({1: "value"})
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "unsupported evidence value"
        ):
            canonical_json_bytes({"value": object()})
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "unsupported evidence value"
        ):
            canonical_json_bytes({"value": float("nan")})

    def test_event_contains_only_pseudonymous_actor_reference(self) -> None:
        event = self._event(
            "intent", sequence=1, previous_event_sha256=ZERO_HASH
        )
        serialized = canonical_json_bytes(event).decode("ascii")

        self.assertEqual(event["actor_ref"], self.actor)
        self.assertNotIn("actor_object_id", event)
        self.assertNotIn(TENANT_ID, serialized)
        self.assertNotIn(ACTOR_OBJECT_ID, serialized)
        self.assertNotIn(ACTOR_KEY.decode("ascii"), serialized)
        self.assertRegex(event["event_id"], r"^event-[0-9a-f]{64}$")
        self.assertRegex(event["idempotency_key_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(event["delivery_key_sha256"], r"^[0-9a-f]{64}$")
        self.assertNotEqual(
            event["idempotency_key_sha256"],
            event["delivery_key_sha256"],
        )
        self.assertEqual(
            event["privacy"],
            {
                "classification": "pseudonymous_personal_data",
                "read_role": "revision_audit",
                "monthly_access_review_required": True,
            },
        )

    def test_retention_defaults_to_ten_years_with_legal_hold(self) -> None:
        event = self._event(
            "intent", sequence=1, previous_event_sha256=ZERO_HASH
        )

        self.assertEqual(
            event["retention"],
            {
                "minimum_years": MINIMUM_RETENTION_YEARS,
                "legal_hold_capable": True,
            },
        )

        extended = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            retention_years=25,
        )
        self.assertEqual(extended["retention"]["minimum_years"], 25)

    def test_retention_rejects_short_non_integer_and_disabled_legal_hold(self) -> None:
        invalid_overrides = (
            {"retention_years": MINIMUM_RETENTION_YEARS - 1},
            {"retention_years": True},
            {"legal_hold": False},
            {"legal_hold": 1},
        )

        for overrides in invalid_overrides:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ImmutableEvidenceError):
                    self._event(
                        "intent",
                        sequence=1,
                        previous_event_sha256=ZERO_HASH,
                        **overrides,
                    )

    def test_reconciliation_store_require_is_idempotent_but_reason_is_immutable(
        self,
    ) -> None:
        store = InMemoryReconciliationStore()

        store.require(CORRELATION_ID, "readback-missing", MANIFEST_SHA256)
        store.require(CORRELATION_ID, "readback-missing", MANIFEST_SHA256)
        self.assertTrue(store.is_required(CORRELATION_ID))

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "requirement cannot be replaced"
        ):
            store.require(CORRELATION_ID, "provider-readback-required", MANIFEST_SHA256)
        self.assertTrue(store.is_required(CORRELATION_ID))

    def test_reconciliation_store_close_lifecycle_is_fail_closed(self) -> None:
        store = InMemoryReconciliationStore()
        outbox = InMemoryEvidenceOutbox()

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "reconciliation is not required"
        ):
            store.close(
                CORRELATION_ID,
                records=(),
                operator_ref=self.operator,
                approver_ref=self.approver,
            )

        self._append(outbox, "intent")
        self._append(
            outbox, "outcome", result_code="write-state-uncertain"
        )
        required_head = outbox.records(CORRELATION_ID)[-1].event_sha256
        store.require(CORRELATION_ID, "readback-missing", required_head)
        self._append(outbox, "reconciliation_required")
        with self.assertRaises(ImmutableEvidenceError):
            store.close(
                CORRELATION_ID,
                records=outbox.records(CORRELATION_ID),
                operator_ref=self.operator,
                approver_ref=self.approver,
            )
        self.assertTrue(store.is_required(CORRELATION_ID))

        self._append(outbox, "readback")
        self._append(outbox, "reconciliation_closed")
        store.close(
            CORRELATION_ID,
            records=outbox.records(CORRELATION_ID),
            operator_ref=self.operator,
            approver_ref=self.approver,
        )
        self.assertFalse(store.is_required(CORRELATION_ID))

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "reconciliation is not required"
        ):
            store.close(
                CORRELATION_ID,
                records=outbox.records(CORRELATION_ID),
                operator_ref=self.operator,
                approver_ref=self.approver,
            )

    def test_confirmed_outcome_with_missing_readback_enters_reconciliation(
        self,
    ) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(
            outbox,
            "reconciliation_required",
            reconciliation_reason_code="readback-missing",
        )

        self.assertEqual(
            verify_chain(outbox.records(CORRELATION_ID))["phases"],
            ["intent", "outcome", "reconciliation_required"],
        )

    def test_failed_readback_cannot_complete_or_close_reconciliation(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        store = InMemoryReconciliationStore()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="write-state-uncertain")
        required_head = outbox.records(CORRELATION_ID)[-1].event_sha256
        store.require(CORRELATION_ID, "readback-missing", required_head)
        self._append(outbox, "reconciliation_required")
        self._append(outbox, "readback", result_code="failed")
        self._append(outbox, "reconciliation_closed", result_code="failed")

        status = verify_chain(outbox.records(CORRELATION_ID))
        self.assertFalse(status["complete"])
        self.assertTrue(status["reconciliation_required"])
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "closure evidence is incomplete"
        ):
            store.close(
                CORRELATION_ID,
                records=outbox.records(CORRELATION_ID),
                operator_ref=self.operator,
                approver_ref=self.approver,
            )
        self.assertTrue(store.is_required(CORRELATION_ID))

        self._append(outbox, "readback", result_code="verified")
        self._append(
            outbox, "reconciliation_closed", result_code="reconciled"
        )
        store.close(
            CORRELATION_ID,
            records=outbox.records(CORRELATION_ID),
            operator_ref=self.operator,
            approver_ref=self.approver,
        )
        self.assertFalse(store.is_required(CORRELATION_ID))

    def test_retention_and_privacy_cannot_change_within_chain(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent", retention_years=25)

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "evidence binding changed: retention"
        ):
            self._append(outbox, "outcome", retention_years=10)

    def test_event_id_binds_complete_event_payload(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        intent = self._append(outbox, "intent")
        confirmed = self._event(
            "outcome",
            sequence=2,
            previous_event_sha256=intent.event_sha256,
            result_code="confirmed",
        )
        failed = self._event(
            "outcome",
            sequence=2,
            previous_event_sha256=intent.event_sha256,
            result_code="failed",
        )

        self.assertNotEqual(confirmed["event_id"], failed["event_id"])
        changed = dict(confirmed, result_code="failed")
        delivery_payload = dict(changed)
        delivery_payload.pop("event_id")
        delivery_payload.pop("delivery_key_sha256")
        changed["delivery_key_sha256"] = hashlib.sha256(
            b"nac.delivery-key.v1\x00"
            + canonical_json_bytes(delivery_payload)
        ).hexdigest()
        with self.assertRaisesRegex(ImmutableEvidenceError, "event identity is invalid"):
            verify_chain((intent, self._rehash(changed)))

    def test_sensitive_values_and_raw_etags_are_not_persisted(self) -> None:
        sensitive_values = (
            TENANT_ID,
            "owner@example.invalid",
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature",
            "-----BEGIN PRIVATE KEY-----",
            "Bearer secret-token",
        )
        for value in sensitive_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ImmutableEvidenceError, "sensitive evidence value is forbidden"
                ):
                    canonical_json_bytes({"correlation_id": value})

        with self.assertRaises(ImmutableEvidenceError):
            self._event(
                "intent",
                sequence=1,
                previous_event_sha256=ZERO_HASH,
                etags={"tenant_id": "opaque"},
            )
        with self.assertRaises(ImmutableEvidenceError):
            self._event(
                "intent",
                sequence=1,
                previous_event_sha256=ZERO_HASH,
                etags={"matter": TENANT_ID},
            )

        event = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            etags={"matter": "opaque-provider-etag"},
        )
        self.assertEqual(
            event["etags"]["matter"],
            "hmac-sha256:k1:"
            + hmac.new(
                ACTOR_KEY,
                b"nac.etag-evidence.v1\x00"
                + hashlib.sha256(
                    b"nac.tenant-binding.v1\x00"
                    + TENANT_ID.encode("ascii")
                ).hexdigest().encode("ascii")
                + b"\x00k1\x00matter\x00"
                + b"opaque-provider-etag",
                hashlib.sha256,
            ).hexdigest(),
        )
        self.assertNotIn("opaque-provider-etag", canonical_json_bytes(event).decode())

    def test_port_orchestration_requires_all_receipts_and_is_redacted(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        store = InMemoryReconciliationStore()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )

        result = publisher.finalize(CORRELATION_ID)

        self.assertEqual(result["broker_ack_count"], 3)
        self.assertTrue(result["worm_readback_verified"])
        self.assertFalse(result["production_durability_claim"])
        self.assertFalse(store.is_required(CORRELATION_ID))
        self.assertNotIn("ack-", str(result))
        self.assertNotIn("receipt-", str(result))

    def test_missing_port_receipt_creates_sticky_reconciliation(self) -> None:
        scenarios = (
            ("incomplete-chain", False, _Broker(), _Anchor(), _Worm()),
            (
                "missing-broker-ack",
                True,
                _Broker(missing_ack=True),
                _Anchor(),
                _Worm(),
            ),
            (
                "unbound-broker-ack",
                True,
                _Broker(unbound_ack=True),
                _Anchor(),
                _Worm(),
            ),
            ("invalid-anchor", True, _Broker(), _Anchor(valid=False), _Worm()),
            ("invalid-worm-readback", True, _Broker(), _Anchor(), _Worm(readback_verified=False)),
        )
        for name, complete_chain, broker, anchor, worm in scenarios:
            with self.subTest(name=name):
                outbox = InMemoryEvidenceOutbox()
                store = InMemoryReconciliationStore()
                self._append(outbox, "intent")
                if complete_chain:
                    self._append(outbox, "outcome", result_code="confirmed")
                    self._append(outbox, "readback", result_code="verified")
                publisher = ImmutableEvidencePublisher(
                    outbox=outbox,
                    broker=broker,
                    signature_anchor=anchor,
                    worm_journal=worm,
                    reconciliation_store=store,
                )

                with self.assertRaises(ImmutableEvidenceError):
                    publisher.finalize(CORRELATION_ID)
                self.assertTrue(store.is_required(CORRELATION_ID))
                with self.assertRaisesRegex(
                    ImmutableEvidenceError, "requirement cannot be replaced"
                ):
                    store.require(
                        CORRELATION_ID,
                        "provider-readback-required",
                        outbox.records(CORRELATION_ID)[-1].event_sha256,
                    )

    def test_failed_mutation_with_verified_readback_is_terminal(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="failed")
        self._append(outbox, "readback", result_code="verified")

        status = verify_chain(outbox.records(CORRELATION_ID))

        self.assertTrue(status["complete"])
        self.assertFalse(status["reconciliation_required"])
        self.assertEqual(status["mutation_result"], "failed")

    def test_actor_and_correlation_references_are_opaque_and_factory_bound(self) -> None:
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "must be created by actor_ref"
        ):
            self._event(
                "intent",
                sequence=1,
                previous_event_sha256=ZERO_HASH,
                actor_ref_value="actor-v1-k999-" + "0" * 64,
            )
        for raw_correlation in (
            "max-mustermann",
            "akte-2026-0042",
            "sk-proj-secretvalue",
            "correlation-v1-k9-" + "0" * 64,
        ):
            with self.subTest(raw_correlation=raw_correlation):
                with self.assertRaisesRegex(
                    ImmutableEvidenceError, "created by correlation_ref"
                ):
                    self._event(
                        "intent",
                        sequence=1,
                        previous_event_sha256=ZERO_HASH,
                        correlation_id=raw_correlation,
                    )

        changed_version = correlation_ref(
            tenant_id=TENANT_ID,
            source_object_id=SOURCE_OBJECT_ID,
            key_version=4,
            key=ACTOR_KEY,
        )
        self.assertNotEqual(changed_version, CORRELATION_ID)
        self.assertNotIn(TENANT_ID, CORRELATION_ID)
        self.assertNotIn(SOURCE_OBJECT_ID, CORRELATION_ID)
        self.assertRegex(
            CORRELATION_ID, r"^correlation-v1-k[0-9]+-[0-9a-f]{64}$"
        )

    def test_ports_receive_defensive_copies_and_unbound_ack_is_rejected(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        store = InMemoryReconciliationStore()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(mutate_record=True),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )

        publisher.finalize(CORRELATION_ID)

        self.assertEqual(
            outbox.records(CORRELATION_ID)[0].event["tool_id"], "tool-nac-cli"
        )

    def test_reconciliation_cannot_close_with_substitute_chain(self) -> None:
        original = InMemoryEvidenceOutbox()
        store = InMemoryReconciliationStore()
        self._append(original, "intent")
        self._append(
            original, "outcome", result_code="write-state-uncertain"
        )
        original_head = original.records(CORRELATION_ID)[-1].event_sha256
        store.require(CORRELATION_ID, "readback-missing", original_head)

        substitute = InMemoryEvidenceOutbox()
        self._append(
            substitute,
            "intent",
            business_case_type_id="handelsregisteranmeldung",
        )
        self._append(
            substitute,
            "outcome",
            result_code="write-state-uncertain",
            business_case_type_id="handelsregisteranmeldung",
        )
        self._append(
            substitute,
            "reconciliation_required",
            business_case_type_id="handelsregisteranmeldung",
        )
        self._append(
            substitute,
            "readback",
            result_code="verified",
            business_case_type_id="handelsregisteranmeldung",
        )
        self._append(
            substitute,
            "reconciliation_closed",
            result_code="reconciled",
            business_case_type_id="handelsregisteranmeldung",
        )

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "chain head is not bound"
        ):
            store.close(
                CORRELATION_ID,
                records=substitute.records(CORRELATION_ID),
                operator_ref=self.operator,
                approver_ref=self.approver,
            )
        self.assertTrue(store.is_required(CORRELATION_ID))

    def test_outbox_requires_untampered_factory_event(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        event = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
        )

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "created by build_event"
        ):
            outbox.append(dict(event))

        event["actor_ref"] = "actor-v1-k9-" + "0" * 64
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "changed after build_event"
        ):
            outbox.append(event)

    def test_domain_identifiers_must_be_registered(self) -> None:
        invalid = (
            {"tool_id": "tool-max-mustermann"},
            {"role_id": "role-oliver-funk"},
            {
                "business_case_type_id":
                    "akte-2026-0042"
            },
            {"catalog_version": "d" * 64},
        )
        for overrides in invalid:
            with self.subTest(overrides=overrides):
                with self.assertRaisesRegex(
                    ImmutableEvidenceError,
                    "not a registered typed identifier",
                ):
                    self._event(
                        "intent",
                        sequence=1,
                        previous_event_sha256=ZERO_HASH,
                        **overrides,
                    )

    def test_publisher_snapshots_untrusted_outbox_before_verification(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        source_records = list(outbox.records(CORRELATION_ID))

        class MutableSourceOutbox:
            def records(self, _correlation_id: str) -> tuple[EvidenceRecord, ...]:
                return tuple(source_records)

        class SourceMutatingBroker(_Broker):
            def publish(self, record: EvidenceRecord) -> dict[str, Any]:
                source_records[0].event["tool_id"] = "tool-nac-kg-business-case-type-migration"
                return super().publish(record)

        result = ImmutableEvidencePublisher(
            outbox=MutableSourceOutbox(),
            broker=SourceMutatingBroker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        ).finalize(CORRELATION_ID)

        self.assertEqual(
            result["status"], "SYNTHETIC_PORT_ORCHESTRATION_COMPLETE"
        )
        self.assertEqual(source_records[0].event["tool_id"], "tool-nac-kg-business-case-type-migration")

    def test_publication_retry_cannot_clear_domain_reconciliation(self) -> None:
        store = InMemoryReconciliationStore()
        store.require(CORRELATION_ID, "readback-missing", MANIFEST_SHA256)

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "not publication-retry eligible"
        ):
            store.authorize_publication_retry(
                CORRELATION_ID,
                operator_ref=self.operator,
                approver_ref=self.approver,
            )

        self.assertTrue(store.is_required(CORRELATION_ID))
        self.assertEqual(
            store.requirement(CORRELATION_ID)["reason_code"],
            "readback-missing",
        )

    def test_publisher_rejects_outbox_chain_for_other_correlation(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        other_correlation = correlation_ref(
            tenant_id=TENANT_ID,
            source_object_id="66666666-6666-4666-8666-666666666666",
            key_version=3,
            key=ACTOR_KEY,
        )

        class SubstitutingOutbox:
            def records(
                self, _correlation_id: str
            ) -> tuple[EvidenceRecord, ...]:
                return outbox.records(CORRELATION_ID)

        publisher = ImmutableEvidencePublisher(
            outbox=SubstitutingOutbox(),
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "correlation does not match request"
        ):
            publisher.finalize(other_correlation)

    def test_completed_replay_requires_exact_acknowledgement_history(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        broker = _Broker()
        store = InMemoryReconciliationStore()
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=broker,
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )
        publisher.finalize(CORRELATION_ID)
        progress = store._publications[CORRELATION_ID]["progress"]
        progress["acknowledged_event_sha256s"][0] = "f" * 64
        progress["acknowledged_event_sha256s"][1] = "e" * 64

        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            "evidence publication state is unavailable",
        ):
            publisher.finalize(CORRELATION_ID)
        self.assertEqual(broker.calls, 3)

    def test_untrusted_reconciliation_state_error_is_redacted(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        class SecretConflictStore(InMemoryReconciliationStore):
            def claim_publication(
                self,
                correlation_id: str,
                chain_head_sha256: str,
                *,
                claim_id: str,
                tenant_binding_sha256: str,
                principal_key_binding_sha256: str,
                event_sha256s: tuple[str, ...],
            ) -> dict[str, Any]:
                raise _ReconciliationStateError(
                    "secret-state-provider-detail"
                )

        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=SecretConflictStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as error:
            publisher.finalize(CORRELATION_ID)
        self.assertEqual(
            str(error.exception), "evidence publication state is unavailable"
        )
        self.assertNotIn("secret-state-provider-detail", str(error.exception))

    def test_preclaim_retry_is_principal_key_bound_and_audited(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        store = InMemoryReconciliationStore()
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "evidence chain is incomplete"
        ):
            publisher.finalize(CORRELATION_ID)
        requirement = store.requirement(CORRELATION_ID)
        self.assertEqual(
            requirement["principal_key_binding_sha256"],
            self.actor._principal_key_binding_sha256,
        )
        alternate_principal_key = b"alternate-principal-binding-key-01"
        foreign_operator = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=OPERATOR_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=alternate_principal_key,
        )
        foreign_approver = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=APPROVER_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=alternate_principal_key,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "principal key binding differs"
        ):
            store.authorize_publication_retry(
                CORRELATION_ID,
                operator_ref=foreign_operator,
                approver_ref=foreign_approver,
            )
        self.assertTrue(store.is_required(CORRELATION_ID))

        store.authorize_publication_retry(
            CORRELATION_ID,
            operator_ref=self.operator,
            approver_ref=self.approver,
        )
        authorized = store.requirement(CORRELATION_ID)
        self.assertTrue(authorized["retry_authorized"])
        self.assertEqual(len(authorized["retry_authorizations"]), 1)

        self._append(outbox, "readback", result_code="verified")
        result = publisher.finalize(CORRELATION_ID)
        self.assertEqual(result["broker_ack_count"], 3)
        state = store._publications[CORRELATION_ID]
        self.assertEqual(state["retry_authorization_count"], 1)
        self.assertEqual(len(state["retry_authorizations"]), 1)
        self.assertFalse(store.is_required(CORRELATION_ID))

    def test_preclaim_retry_without_principal_binding_fails_closed(self) -> None:
        store = InMemoryReconciliationStore()
        store.require(
            CORRELATION_ID,
            "evidence-publication-incomplete",
            MANIFEST_SHA256,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "security binding is unavailable"
        ):
            store.authorize_publication_retry(
                CORRELATION_ID,
                operator_ref=self.operator,
                approver_ref=self.approver,
            )
        self.assertTrue(store.is_required(CORRELATION_ID))

    def test_preclaim_retry_with_security_binding_but_no_prefix_fails(self) -> None:
        store = InMemoryReconciliationStore()
        store.require(
            CORRELATION_ID,
            "evidence-publication-incomplete",
            MANIFEST_SHA256,
            tenant_binding_sha256=self.actor._tenant_binding_sha256,
            principal_key_binding_sha256=(
                self.actor._principal_key_binding_sha256
            ),
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "event prefix is unavailable"
        ):
            store.authorize_publication_retry(
                CORRELATION_ID,
                operator_ref=self.operator,
                approver_ref=self.approver,
            )
        self.assertTrue(store.is_required(CORRELATION_ID))

    def test_preclaim_retry_cannot_authorize_substituted_chain(self) -> None:
        original = InMemoryEvidenceOutbox()
        self._append(original, "intent")
        self._append(original, "outcome", result_code="confirmed")
        store = InMemoryReconciliationStore()
        original_publisher = ImmutableEvidencePublisher(
            outbox=original,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "evidence chain is incomplete"
        ):
            original_publisher.finalize(CORRELATION_ID)
        authorized_prefix = [
            record.event_sha256 for record in original.records(CORRELATION_ID)
        ]
        self.assertEqual(
            store.requirement(CORRELATION_ID)["event_sha256s"],
            authorized_prefix,
        )
        store.authorize_publication_retry(
            CORRELATION_ID,
            operator_ref=self.operator,
            approver_ref=self.approver,
        )

        substituted = InMemoryEvidenceOutbox()
        previous = ZERO_HASH
        for sequence, (phase, result_code) in enumerate(
            (("intent", None), ("outcome", "confirmed"),
             ("readback", "verified")),
            start=1,
        ):
            overrides: dict[str, Any] = {
                "business_case_type_id": "handelsregisteranmeldung"
            }
            if result_code is not None:
                overrides["result_code"] = result_code
            record = substituted.append(
                self._event(
                    phase,
                    sequence=sequence,
                    previous_event_sha256=previous,
                    **overrides,
                )
            )
            previous = record.event_sha256
        substituted_publisher = ImmutableEvidencePublisher(
            outbox=substituted,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "security binding does not match"
        ):
            substituted_publisher.finalize(CORRELATION_ID)
        self.assertTrue(store.is_required(CORRELATION_ID))

    def test_verified_security_metadata_cannot_be_resealed(self) -> None:
        original_principal = self.operator._principal_ref
        with self.assertRaisesRegex(AttributeError, "metadata is immutable"):
            self.operator._principal_ref = self.approver._principal_ref
        object.__setattr__(
            self.operator, "_principal_ref", self.approver._principal_ref
        )
        self.assertEqual(self.operator._principal_ref, original_principal)
        with self.assertRaises(AttributeError):
            _ = self.operator.__dict__

        original_tenant_binding = CORRELATION_ID._tenant_binding_sha256
        object.__setattr__(
            CORRELATION_ID, "_tenant_binding_sha256", "f" * 64
        )
        self.assertEqual(
            CORRELATION_ID._tenant_binding_sha256, original_tenant_binding
        )

        event = self._event(
            "intent", sequence=1, previous_event_sha256=ZERO_HASH
        )
        original_payload_sha256 = event._payload_sha256
        with self.assertRaisesRegex(AttributeError, "metadata is immutable"):
            event._payload_sha256 = "f" * 64
        object.__setattr__(event, "_payload_sha256", "f" * 64)
        event["actor_ref"] = str(self.approver)
        self.assertEqual(event._payload_sha256, original_payload_sha256)
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "changed after build_event"
        ):
            InMemoryEvidenceOutbox().append(event)

    def test_provider_secret_is_absent_from_exception_context_chain(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        class SecretBroker(_Broker):
            def publish(self, record: EvidenceRecord) -> dict[str, Any]:
                raise ImmutableEvidenceError("provider-context-secret")

        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=SecretBroker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        self.assertNotIn("provider-context-secret", " ".join(messages))

    def test_lazy_provider_mapping_failure_is_redacted(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        class LazySecretMapping(dict[str, Any]):
            def items(self) -> Any:
                raise ImmutableEvidenceError("lazy-provider-secret")

        class LazyBroker(_Broker):
            def publish(self, record: EvidenceRecord) -> dict[str, Any]:
                self.calls += 1
                return LazySecretMapping()

        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=LazyBroker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        self.assertNotIn("lazy-provider-secret", " ".join(messages))

    def test_malformed_outbox_snapshot_is_redacted(self) -> None:
        class MalformedOutbox:
            def records(
                self, _correlation_id: str
            ) -> tuple[EvidenceRecord, ...]:
                return (
                    EvidenceRecord(
                        event={"customer@example.com": object()},
                        event_sha256="a" * 64,
                    ),
                )

        publisher = ImmutableEvidencePublisher(
            outbox=MalformedOutbox(),
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        rendered = " ".join(messages)
        self.assertEqual(
            str(caught.exception),
            "evidence publication requires reconciliation",
        )
        self.assertNotIn("customer@example.com", rendered)

    def test_lazy_outbox_generator_failure_is_redacted(self) -> None:
        class LazyGeneratorOutbox:
            def records(self, _correlation_id: str) -> Any:
                def records() -> Any:
                    raise ImmutableEvidenceError("lazy-generator-secret")
                    yield

                return records()

        publisher = ImmutableEvidencePublisher(
            outbox=LazyGeneratorOutbox(),
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        self.assertNotIn("lazy-generator-secret", " ".join(messages))

    def test_lazy_evidence_record_failure_is_redacted(self) -> None:
        class LazySecretEvent(dict[str, Any]):
            def items(self) -> Any:
                raise ImmutableEvidenceError("lazy-record-secret")

        class LazyRecordOutbox:
            def records(self, _correlation_id: str) -> tuple[EvidenceRecord, ...]:
                return (
                    EvidenceRecord(
                        event=LazySecretEvent(),
                        event_sha256="a" * 64,
                    ),
                )

        publisher = ImmutableEvidencePublisher(
            outbox=LazyRecordOutbox(),
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        self.assertNotIn("lazy-record-secret", " ".join(messages))

    def test_unsupported_external_scalar_is_rejected_inside_boundary(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        class SecretScalar:
            def __eq__(self, other: object) -> bool:
                raise ImmutableEvidenceError("arbitrary-scalar-secret")

        class ArbitraryScalarStore(InMemoryReconciliationStore):
            def claim_publication(
                self,
                correlation_id: str,
                chain_head_sha256: str,
                *,
                claim_id: str,
                tenant_binding_sha256: str,
                principal_key_binding_sha256: str,
                event_sha256s: tuple[str, ...],
            ) -> dict[str, Any]:
                result = dict(
                    super().claim_publication(
                        correlation_id,
                        chain_head_sha256,
                        claim_id=claim_id,
                        tenant_binding_sha256=tenant_binding_sha256,
                        principal_key_binding_sha256=(
                            principal_key_binding_sha256
                        ),
                        event_sha256s=event_sha256s,
                    )
                )
                result["status"] = SecretScalar()
                return result

        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=ArbitraryScalarStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        self.assertEqual(
            str(caught.exception),
            "evidence publication state is unavailable",
        )
        self.assertNotIn("arbitrary-scalar-secret", " ".join(messages))

    def test_external_scalar_subclasses_are_materialized_before_validation(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        class SecretStatus(str):
            def __eq__(self, other: object) -> bool:
                raise ImmutableEvidenceError("status-comparison-secret")

        class ScalarSubclassStore(InMemoryReconciliationStore):
            def claim_publication(
                self,
                correlation_id: str,
                chain_head_sha256: str,
                *,
                claim_id: str,
                tenant_binding_sha256: str,
                principal_key_binding_sha256: str,
                event_sha256s: tuple[str, ...],
            ) -> dict[str, Any]:
                result = dict(
                    super().claim_publication(
                        correlation_id,
                        chain_head_sha256,
                        claim_id=claim_id,
                        tenant_binding_sha256=tenant_binding_sha256,
                        principal_key_binding_sha256=(
                            principal_key_binding_sha256
                        ),
                        event_sha256s=event_sha256s,
                    )
                )
                result["status"] = SecretStatus(result["status"])
                return result

        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=ScalarSubclassStore(),
        )

        result = publisher.finalize(CORRELATION_ID)

        self.assertTrue(result["worm_readback_verified"])

    def test_partial_publish_progress_is_sticky_until_dual_control_resume(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        records = outbox.records(CORRELATION_ID)
        store = InMemoryReconciliationStore()
        failing = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(fail_after=1),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )

        with self.assertRaises(ImmutableEvidenceError):
            failing.finalize(CORRELATION_ID)

        requirement = store.requirement(CORRELATION_ID)
        self.assertEqual(
            requirement["publication_progress"]["stage"],
            "broker-in-flight",
        )
        self.assertEqual(
            requirement["publication_progress"][
                "acknowledged_event_sha256s"
            ],
            [records[0].event_sha256],
        )
        retry_broker = _Broker()
        retry = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=retry_broker,
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "blocked by reconciliation"
        ):
            retry.finalize(CORRELATION_ID)

        store.authorize_publication_retry(
            CORRELATION_ID,
            operator_ref=self.operator,
            approver_ref=self.approver,
        )
        result = retry.finalize(CORRELATION_ID)
        self.assertEqual(result["broker_ack_count"], len(records))
        self.assertEqual(retry_broker.calls, len(records) - 1)

    def test_completed_publication_replay_has_no_second_provider_effect(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        broker = _Broker()
        anchor = _Anchor()
        worm = _Worm()
        store = InMemoryReconciliationStore()
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=broker,
            signature_anchor=anchor,
            worm_journal=worm,
            reconciliation_store=store,
        )

        first = publisher.finalize(CORRELATION_ID)
        second = publisher.finalize(CORRELATION_ID)

        self.assertEqual(second, first)
        self.assertEqual(broker.calls, 3)
        self.assertEqual(anchor.anchor_calls, 1)
        self.assertEqual(anchor.readback_calls, 1)
        self.assertEqual(worm.commit_calls, 1)
        self.assertEqual(worm.readback_calls, 1)
        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            "completed publication cannot require reconciliation",
        ):
            store.require(
                CORRELATION_ID,
                "evidence-publication-incomplete",
                outbox.records(CORRELATION_ID)[-1].event_sha256,
            )

    def test_process_interruption_requires_dual_control_before_resume(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        store = InMemoryReconciliationStore()

        class InterruptingBroker(_Broker):
            def publish(self, record: EvidenceRecord) -> dict[str, Any]:
                raise KeyboardInterrupt("synthetic process interruption")

        interrupted = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=InterruptingBroker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )
        with self.assertRaises(KeyboardInterrupt):
            interrupted.finalize(CORRELATION_ID)
        self.assertTrue(store.is_required(CORRELATION_ID))

        retry_broker = _Broker()
        retry = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=retry_broker,
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "active claim"
        ):
            retry.finalize(CORRELATION_ID)

        store.authorize_publication_retry(
            CORRELATION_ID,
            operator_ref=self.operator,
            approver_ref=self.approver,
        )
        result = retry.finalize(CORRELATION_ID)
        self.assertEqual(result["broker_ack_count"], 3)
        self.assertEqual(retry_broker.calls, 3)

    def test_outbox_snapshot_failure_creates_redacted_sticky_requirement(self) -> None:
        class FailingOutbox:
            def records(self, correlation_id: str) -> tuple[EvidenceRecord, ...]:
                raise RuntimeError("synthetic outbox snapshot failure")

        store = InMemoryReconciliationStore()
        publisher = ImmutableEvidencePublisher(
            outbox=FailingOutbox(),
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "requires reconciliation"
        ):
            publisher.finalize(CORRELATION_ID)

        requirement = store.requirement(CORRELATION_ID)
        self.assertEqual(requirement["chain_head_sha256"], ZERO_HASH)
        self.assertEqual(
            requirement["publication_progress"]["stage"],
            "outbox-snapshot",
        )
        self.assertNotIn("synthetic outbox snapshot failure", str(requirement))

    def test_publication_progress_is_monotone_and_stage_bound(self) -> None:
        store = InMemoryReconciliationStore()
        claim_id = "claim-v1-" + "1" * 64
        store.claim_publication(
            CORRELATION_ID,
            MANIFEST_SHA256,
            claim_id=claim_id,
            tenant_binding_sha256=self.actor._tenant_binding_sha256,
            principal_key_binding_sha256=(
                self.actor._principal_key_binding_sha256
            ),
            event_sha256s=(MANIFEST_SHA256,),
        )
        base = {
            "stage": "broker-in-flight",
            "acknowledged_event_sha256s": [MANIFEST_SHA256],
            "anchor_ref_sha256": None,
            "signature_ref_sha256": None,
            "worm_receipt_ref_sha256": None,
        }
        store.advance_publication(
            CORRELATION_ID,
            claim_id=claim_id,
            publication_progress=base,
        )

        regressed = dict(base, stage="outbox-snapshot")
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "cannot regress"
        ):
            store.advance_publication(
                CORRELATION_ID,
                claim_id=claim_id,
                publication_progress=regressed,
            )

        removed_ack = dict(base, acknowledged_event_sha256s=[])
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "not append-only"
        ):
            store.advance_publication(
                CORRELATION_ID,
                claim_id=claim_id,
                publication_progress=removed_ack,
            )

        missing_anchor = dict(base, stage="anchor-readback-in-flight")
        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            "anchor reference does not match",
        ):
            store.advance_publication(
                CORRELATION_ID,
                claim_id=claim_id,
                publication_progress=missing_anchor,
            )

    def test_publication_completion_binds_full_claimed_event_sequence(self) -> None:
        event_sha256s = ("a" * 64, "b" * 64, "c" * 64)
        store = InMemoryReconciliationStore()
        claim_id = "claim-v1-" + "3" * 64
        store.claim_publication(
            CORRELATION_ID,
            event_sha256s[-1],
            claim_id=claim_id,
            tenant_binding_sha256=self.actor._tenant_binding_sha256,
            principal_key_binding_sha256=(
                self.actor._principal_key_binding_sha256
            ),
            event_sha256s=event_sha256s,
        )
        skipped = {
            "stage": "worm-readback-complete",
            "acknowledged_event_sha256s": list(event_sha256s),
            "anchor_ref_sha256": "d" * 64,
            "signature_ref_sha256": "e" * 64,
            "worm_receipt_ref_sha256": "f" * 64,
        }
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "cannot skip stages"
        ):
            store.advance_publication(
                CORRELATION_ID,
                claim_id=claim_id,
                publication_progress=skipped,
            )

        corrupted_progress = dict(
            skipped,
            acknowledged_event_sha256s=[event_sha256s[0], event_sha256s[2]],
        )
        store._publications[CORRELATION_ID]["progress"] = corrupted_progress
        corrupted_result = {
            "schema_version": "nac.immutable-evidence-publication/v0.1",
            "status": "SYNTHETIC_PORT_ORCHESTRATION_COMPLETE",
            "correlation_id": str(CORRELATION_ID),
            "chain_head_sha256": event_sha256s[-1],
            "event_count": 2,
            "broker_ack_count": 2,
            "anchor_ref_sha256": "d" * 64,
            "signature_ref_sha256": "e" * 64,
            "worm_receipt_ref_sha256": "f" * 64,
            "worm_readback_ref_sha256": "f" * 64,
            "worm_readback_verified": True,
            "production_durability_claim": False,
        }
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "claimed event sequence"
        ):
            store.complete_publication(
                CORRELATION_ID,
                claim_id=claim_id,
                result=corrupted_result,
            )

    def test_same_principal_is_rejected_across_actor_key_rotation(self) -> None:
        rotated_operator = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=OPERATOR_OBJECT_ID,
            key_version=4,
            key=b"rotated-actor-key-for-evidence-1",
            principal_key=PRINCIPAL_KEY,
        )
        self.assertNotEqual(rotated_operator, self.operator)

        with self.assertRaisesRegex(
            ImmutableEvidenceError, "requires separate principals"
        ):
            self._event(
                "reconciliation_closed",
                sequence=5,
                previous_event_sha256="b" * 64,
                reconciliation_operator_ref=self.operator,
                reconciliation_approver_ref=rotated_operator,
            )

        store = InMemoryReconciliationStore()
        store.require(CORRELATION_ID, "readback-missing", MANIFEST_SHA256)
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "requires separate principals"
        ):
            store.close(
                CORRELATION_ID,
                operator_ref=self.operator,
                records=(),
                approver_ref=rotated_operator,
            )

    def test_delivery_keys_are_per_event_and_etags_use_keyed_hmac(self) -> None:
        records = self._normal_chain()
        operation_keys = {
            record.event["idempotency_key_sha256"] for record in records
        }
        delivery_keys = {
            record.event["delivery_key_sha256"] for record in records
        }
        self.assertEqual(len(operation_keys), 1)
        self.assertEqual(len(delivery_keys), 3)

        first = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            etags={"matter": "1"},
        )
        second = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            etags={"matter": "1"},
            etag_hmac_key=b"independent-etag-key-material-01",
        )
        plain = hashlib.sha256(b"1").hexdigest()
        self.assertNotEqual(first["etags"]["matter"], "hmac-sha256:" + plain)
        self.assertNotEqual(first["etags"]["matter"], second["etags"]["matter"])

    def test_uncertain_outcome_requires_reconciliation_before_readback(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(
            outbox, "outcome", result_code="write-state-uncertain"
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError, "phase transition is invalid"
        ):
            self._append(outbox, "readback", result_code="verified")

    def test_duplicate_ack_and_anchor_readback_mismatch_fail_closed(self) -> None:
        scenarios = (
            (_Broker(duplicate_ack=True), _Anchor()),
            (_Broker(semantic_ack=True), _Anchor()),
            (_Broker(), _Anchor(readback_valid=False)),
        )
        for broker, anchor in scenarios:
            with self.subTest(
                broker=type(broker).__name__,
                anchor_readback=anchor.readback_valid,
            ):
                outbox = InMemoryEvidenceOutbox()
                self._append(outbox, "intent")
                self._append(outbox, "outcome", result_code="confirmed")
                self._append(outbox, "readback", result_code="verified")
                store = InMemoryReconciliationStore()
                publisher = ImmutableEvidencePublisher(
                    outbox=outbox,
                    broker=broker,
                    signature_anchor=anchor,
                    worm_journal=_Worm(),
                    reconciliation_store=store,
                )
                with self.assertRaises(ImmutableEvidenceError):
                    publisher.finalize(CORRELATION_ID)
                self.assertTrue(store.is_required(CORRELATION_ID))

    def test_worm_readback_accepts_stronger_retention(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        result = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(retention_years=25),
            reconciliation_store=InMemoryReconciliationStore(),
        ).finalize(CORRELATION_ID)

        self.assertTrue(result["worm_readback_verified"])

    def test_successful_readback_requires_matching_nonempty_etags(self) -> None:
        for readback_etags in ({}, {"matter": "different-etag"}):
            with self.subTest(readback_etags=readback_etags):
                outbox = InMemoryEvidenceOutbox()
                self._append(outbox, "intent")
                self._append(
                    outbox,
                    "outcome",
                    result_code="confirmed",
                    etags={"matter": "outcome-etag"},
                )
                with self.assertRaisesRegex(
                    ImmutableEvidenceError,
                    "readback.*ETags|provider ETags",
                ):
                    self._append(
                        outbox,
                        "readback",
                        result_code="verified",
                        etags=readback_etags,
                    )

    def test_etag_hmac_is_tenant_and_key_version_bound(self) -> None:
        other_tenant_id = "66666666-6666-4666-8666-666666666666"
        other_tenant_actor = actor_ref(
            tenant_id=other_tenant_id,
            actor_object_id=ACTOR_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=PRINCIPAL_KEY,
        )
        other_tenant_correlation = correlation_ref(
            tenant_id=other_tenant_id,
            source_object_id=SOURCE_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
        )
        base = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            etags={"matter": "same-provider-etag"},
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            "correlation and actor tenant binding differ",
        ):
            self._event(
                "intent",
                sequence=1,
                previous_event_sha256=ZERO_HASH,
                actor_ref_value=other_tenant_actor,
                etags={"matter": "same-provider-etag"},
            )
        other_tenant = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            correlation_id=other_tenant_correlation,
            actor_ref_value=other_tenant_actor,
            etags={"matter": "same-provider-etag"},
        )
        other_key_version = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
            etags={"matter": "same-provider-etag"},
            etag_hmac_key_version=2,
        )
        self.assertRegex(base["etags"]["matter"], r"^hmac-sha256:k1:[0-9a-f]{64}$")
        self.assertNotEqual(base["etags"], other_tenant["etags"])
        self.assertNotEqual(base["etags"], other_key_version["etags"])

    def test_delivery_key_binds_event_content_not_only_phase_and_sequence(self) -> None:
        intent = self._event(
            "intent",
            sequence=1,
            previous_event_sha256=ZERO_HASH,
        )
        intent_record = self._rehash(dict(intent))
        confirmed = self._event(
            "outcome",
            sequence=2,
            previous_event_sha256=intent_record.event_sha256,
            result_code="confirmed",
        )
        failed = self._event(
            "outcome",
            sequence=2,
            previous_event_sha256=intent_record.event_sha256,
            result_code="failed",
        )
        self.assertNotEqual(
            confirmed["delivery_key_sha256"],
            failed["delivery_key_sha256"],
        )

    def test_corrupted_completed_state_cannot_suppress_provider_replay(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        broker = _Broker()
        store = InMemoryReconciliationStore()
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=broker,
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=store,
        )
        publisher.finalize(CORRELATION_ID)
        corrupted = store._publications[CORRELATION_ID]["result"]
        corrupted["event_count"] = 999
        corrupted["broker_ack_count"] = 999
        for field in (
            "anchor_ref_sha256",
            "signature_ref_sha256",
            "worm_receipt_ref_sha256",
            "worm_readback_ref_sha256",
        ):
            corrupted[field] = "f" * 64

        corrupted["customer@example.com"] = 1.5
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        self.assertEqual(
            str(caught.exception),
            "evidence publication state is unavailable",
        )
        self.assertNotIn("customer@example.com", " ".join(messages))
        self.assertEqual(broker.calls, 3)

    def test_publication_claim_is_atomic_and_retry_uses_stable_principals(self) -> None:
        store = InMemoryReconciliationStore()
        first_claim = "claim-v1-" + "1" * 64
        second_claim = "claim-v1-" + "2" * 64
        store.claim_publication(
            CORRELATION_ID,
            MANIFEST_SHA256,
            claim_id=first_claim,
            tenant_binding_sha256=self.actor._tenant_binding_sha256,
            principal_key_binding_sha256=(
                self.actor._principal_key_binding_sha256
            ),
            event_sha256s=(MANIFEST_SHA256,),
        )
        with self.assertRaisesRegex(ImmutableEvidenceError, "active claim"):
            store.claim_publication(
                CORRELATION_ID,
                MANIFEST_SHA256,
                claim_id=second_claim,
                tenant_binding_sha256=self.actor._tenant_binding_sha256,
                principal_key_binding_sha256=(
                    self.actor._principal_key_binding_sha256
                ),
                event_sha256s=(MANIFEST_SHA256,),
            )

        rotated_operator = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=OPERATOR_OBJECT_ID,
            key_version=4,
            key=b"rotated-actor-key-for-evidence-1",
            principal_key=PRINCIPAL_KEY,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            "separate principals",
        ):
            store.authorize_publication_retry(
                CORRELATION_ID,
                operator_ref=self.operator,
                approver_ref=rotated_operator,
            )

        store.authorize_publication_retry(
            CORRELATION_ID,
            operator_ref=self.operator,
            approver_ref=self.approver,
        )
        resumed = store.claim_publication(
            CORRELATION_ID,
            MANIFEST_SHA256,
            claim_id=second_claim,
            tenant_binding_sha256=self.actor._tenant_binding_sha256,
            principal_key_binding_sha256=(
                self.actor._principal_key_binding_sha256
            ),
            event_sha256s=(MANIFEST_SHA256,),
        )
        self.assertEqual(resumed["status"], "publishing")
        authorization = store._publications[CORRELATION_ID][
            "retry_authorizations"
        ][0]
        self.assertNotEqual(
            authorization["operator_principal_ref"],
            authorization["approver_principal_ref"],
        )

    def test_principal_key_and_tenant_boundaries_fail_closed(self) -> None:
        store = InMemoryReconciliationStore()
        claim_id = "claim-v1-" + "3" * 64
        store.claim_publication(
            CORRELATION_ID,
            MANIFEST_SHA256,
            claim_id=claim_id,
            tenant_binding_sha256=self.actor._tenant_binding_sha256,
            principal_key_binding_sha256=(
                self.actor._principal_key_binding_sha256
            ),
            event_sha256s=(MANIFEST_SHA256,),
        )
        alternate_key_operator = actor_ref(
            tenant_id=TENANT_ID,
            actor_object_id=OPERATOR_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=b"alternate-principal-binding-key-01",
        )
        self.assertEqual(alternate_key_operator, self.operator)
        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            "principal key binding differs",
        ):
            store.authorize_publication_retry(
                CORRELATION_ID,
                operator_ref=self.operator,
                approver_ref=alternate_key_operator,
            )

        foreign_tenant = "77777777-7777-4777-8777-777777777777"
        foreign_operator = actor_ref(
            tenant_id=foreign_tenant,
            actor_object_id=OPERATOR_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=PRINCIPAL_KEY,
        )
        foreign_approver = actor_ref(
            tenant_id=foreign_tenant,
            actor_object_id=APPROVER_OBJECT_ID,
            key_version=3,
            key=ACTOR_KEY,
            principal_key=PRINCIPAL_KEY,
        )
        with self.assertRaisesRegex(
            ImmutableEvidenceError,
            "principal tenant binding differs",
        ):
            store.authorize_publication_retry(
                CORRELATION_ID,
                operator_ref=foreign_operator,
                approver_ref=foreign_approver,
            )

    def test_worm_side_effect_is_idempotent_across_process_interruption(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")
        store = InMemoryReconciliationStore()
        anchor = _Anchor()

        class InterruptingWorm(_Worm):
            def commit(
                self,
                records: tuple[EvidenceRecord, ...],
                anchor_value: dict[str, Any],
                *,
                idempotency_key_sha256: str,
            ) -> dict[str, Any]:
                receipt = super().commit(
                    records,
                    anchor_value,
                    idempotency_key_sha256=idempotency_key_sha256,
                )
                if self.commit_calls == 1:
                    raise KeyboardInterrupt(
                        "synthetic interruption after WORM side effect"
                    )
                return receipt

        worm = InterruptingWorm()
        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=anchor,
            worm_journal=worm,
            reconciliation_store=store,
        )
        with self.assertRaises(KeyboardInterrupt):
            publisher.finalize(CORRELATION_ID)

        store.authorize_publication_retry(
            CORRELATION_ID,
            operator_ref=self.operator,
            approver_ref=self.approver,
        )
        result = publisher.finalize(CORRELATION_ID)
        self.assertTrue(result["worm_readback_verified"])
        self.assertEqual(anchor.anchor_calls, 2)
        self.assertEqual(anchor.anchor_effects, 1)
        self.assertEqual(worm.commit_calls, 2)
        self.assertEqual(worm.commit_effects, 1)

    def test_store_exception_string_conversion_is_redacted(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        class SecretStateError(_ReconciliationStateError):
            def __str__(self) -> str:
                raise ImmutableEvidenceError("store-str-secret")

        class SecretStateStore(InMemoryReconciliationStore):
            def claim_publication(
                self,
                correlation_id: str,
                chain_head_sha256: str,
                *,
                claim_id: str,
                tenant_binding_sha256: str,
                principal_key_binding_sha256: str,
                event_sha256s: tuple[str, ...],
            ) -> dict[str, Any]:
                raise SecretStateError("untrusted-state")

        publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=SecretStateStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as caught:
            publisher.finalize(CORRELATION_ID)
        messages: list[str] = []
        current: BaseException | None = caught.exception
        while current is not None:
            messages.append(str(current))
            current = current.__context__
        self.assertEqual(
            str(caught.exception),
            "evidence publication state is unavailable",
        )
        self.assertNotIn("store-str-secret", " ".join(messages))

    def test_store_failures_are_redacted_at_publisher_boundary(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        self._append(outbox, "intent")
        self._append(outbox, "outcome", result_code="confirmed")
        self._append(outbox, "readback", result_code="verified")

        class ClaimFailureStore(InMemoryReconciliationStore):
            def claim_publication(
                self,
                correlation_id: str,
                chain_head_sha256: str,
                *,
                claim_id: str,
                tenant_binding_sha256: str,
                principal_key_binding_sha256: str,
                event_sha256s: tuple[str, ...],
            ) -> dict[str, Any]:
                raise ImmutableEvidenceError("secret-claim-provider-detail")

        class RequireFailureStore(InMemoryReconciliationStore):
            def require(self, *args: Any, **kwargs: Any) -> None:
                raise ImmutableEvidenceError(
                    "secret-reconciliation-provider-detail"
                )

        claim_publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=ClaimFailureStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as claim_error:
            claim_publisher.finalize(CORRELATION_ID)
        self.assertEqual(
            str(claim_error.exception),
            "evidence publication state is unavailable",
        )

        class SecretBroker(_Broker):
            def publish(self, record: EvidenceRecord) -> dict[str, Any]:
                raise ImmutableEvidenceError("provider-secret-detail")

        provider_publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=SecretBroker(),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=InMemoryReconciliationStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as provider_error:
            provider_publisher.finalize(CORRELATION_ID)
        self.assertEqual(
            str(provider_error.exception),
            "evidence publication requires reconciliation",
        )

        require_publisher = ImmutableEvidencePublisher(
            outbox=outbox,
            broker=_Broker(missing_ack=True),
            signature_anchor=_Anchor(),
            worm_journal=_Worm(),
            reconciliation_store=RequireFailureStore(),
        )
        with self.assertRaises(ImmutableEvidenceError) as require_error:
            require_publisher.finalize(CORRELATION_ID)
        self.assertEqual(
            str(require_error.exception),
            "evidence publication state is unavailable",
        )

    def test_reconciliation_store_validates_all_external_values(self) -> None:
        store = InMemoryReconciliationStore()
        with self.assertRaises(ImmutableEvidenceError):
            store.require("Invalid Correlation", "readback-missing", MANIFEST_SHA256)
        with self.assertRaises(ImmutableEvidenceError):
            store.require(CORRELATION_ID, "Invalid Reason", MANIFEST_SHA256)

        store.require(CORRELATION_ID, "readback-missing", MANIFEST_SHA256)
        for operator, approver in (
            ("raw-object-id", self.approver),
            (self.operator, "raw-object-id"),
        ):
            with self.subTest(operator=operator, approver=approver):
                with self.assertRaises(ImmutableEvidenceError):
                    store.close(
                        CORRELATION_ID,
                        operator_ref=operator,
                        records=(),
                        approver_ref=approver,
                    )
        self.assertTrue(store.is_required(CORRELATION_ID))


if __name__ == "__main__":
    unittest.main()
