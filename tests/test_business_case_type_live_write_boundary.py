from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_live_write_boundary import (  # noqa: E402
    BusinessCaseTypeLiveWriteBoundary,
)
from nac_m365_graph.business_case_type_live_write_evidence import (  # noqa: E402
    LiveWriteEvidenceContext,
    S4dMutationEvidenceHook,
    s4d_evidence_operation_binding_sha256,
)
from nac_m365_graph.business_case_type_live_write_gate import (  # noqa: E402
    LiveWriteGateBlocked,
    OwnerApprovalVerification,
    WriteIdentityContext,
    build_unverified_live_write_approval_attestation,
    verify_live_write_owner_approval,
    validate_write_identity_context,
)
from nac_m365_graph.business_case_type_live_write_smoke import (  # noqa: E402
    build_business_case_type_live_write_smoke,
)
from nac_m365_graph.business_case_type_write_edge import (  # noqa: E402
    MutationPersistenceState,
)
from nac_runtime.immutable_evidence import (  # noqa: E402
    EvidenceRecord,
    InMemoryEvidenceOutbox,
    REGISTERED_BUSINESS_CASE_TYPE_IDS,
    REGISTERED_CATALOG_VERSIONS,
    actor_ref,
    correlation_ref,
    typed_identifier_registry,
)


TENANT_ID = "11111111-1111-4111-8111-111111111111"
ACTOR_ID = "22222222-2222-4222-8222-222222222222"
SOURCE_ID = "33333333-3333-4333-8333-333333333333"
ACTOR_KEY = b"actor-key-for-immutable-evidence"
PRINCIPAL_KEY = b"stable-principal-binding-key-0001"


class _OwnerVerifier:
    def __init__(self, *, verified: bool = True) -> None:
        self.verified = verified
        self.calls = 0

    def verify(self, attestation, *, expected):
        self.calls += 1
        return OwnerApprovalVerification(
            source="github_issue_owner_comment",
            issue_ref="https://github.com/notariat8/NaC/issues/700",
            owner_comment_sha256=attestation.owner_comment_sha256,
            owner_principal_binding_sha256="c" * 64,
            verifier_principal_binding_sha256=(
                attestation.owner_verifier_binding_sha256
            ),
            owner_allowlist_sha256=attestation.owner_allowlist_sha256,
            observed_at="2026-07-29T12:00:00Z",
            verified=self.verified,
        )


class _LocalHook:
    def __init__(self) -> None:
        self.state = MutationPersistenceState("clear", "absent", 0, 0, None)
        self.calls: list[str] = []

    def persistence_state(self, execution_key: str) -> MutationPersistenceState:
        return self.state

    def intent(self, evidence) -> bool:
        self.calls.append("local_intent")
        self.state = MutationPersistenceState(
            "clear",
            "open",
            evidence["intent_generation"],
            evidence["expected_intent_generation"],
            evidence["authorization_run_identity"],
        )
        return True

    def outcome(self, evidence) -> bool:
        self.calls.append("local_outcome")
        return True

    def readback(self, evidence) -> bool:
        self.calls.append(
            "local_close" if evidence["close_intent"] else "local_readback"
        )
        if evidence["close_intent"]:
            self.state = MutationPersistenceState(
                "clear",
                "closed",
                evidence["intent_generation"],
                evidence["intent_generation"],
                evidence["authorization_run_identity"],
            )
        return True

    def reconciliation_required(self, evidence) -> bool:
        self.calls.append("local_reconciliation")
        self.state = MutationPersistenceState(
            "required",
            "open",
            evidence["intent_generation"],
            0,
            evidence["authorization_run_identity"],
        )
        return True


class _FailingOutbox(InMemoryEvidenceOutbox):
    def append(self, event):
        raise RuntimeError("raw outbox provider failure")


class _SemanticallyDriftedOutbox(InMemoryEvidenceOutbox):
    def records(self, correlation_id: str) -> tuple[EvidenceRecord, ...]:
        records = list(super().records(correlation_id))
        if records:
            event = json.loads(json.dumps(records[0].event))
            event["privacy"]["monthly_access_review_required"] = 1
            records[0] = EvidenceRecord(
                event=event,
                event_sha256=records[0].event_sha256,
            )
        return tuple(records)


class _Publisher:
    def __init__(self, outbox: InMemoryEvidenceOutbox, calls: list[str]) -> None:
        self.outbox = outbox
        self.calls = calls
        self.fail = False

    def finalize(self, correlation_id: str):
        self.calls.append("publisher_finalize")
        if self.fail:
            raise RuntimeError("raw provider secret")
        records = self.outbox.records(correlation_id)
        head = records[-1].event_sha256
        return {
            "schema_version": "nac.immutable-evidence-publication/v0.1",
            "status": "SYNTHETIC_PORT_ORCHESTRATION_COMPLETE",
            "correlation_id": correlation_id,
            "chain_head_sha256": head,
            "event_count": 3,
            "broker_ack_count": 3,
            "anchor_ref_sha256": "a" * 64,
            "signature_ref_sha256": "b" * 64,
            "worm_receipt_ref_sha256": "c" * 64,
            "worm_readback_ref_sha256": "c" * 64,
            "worm_readback_verified": True,
            "production_durability_claim": False,
        }


class BusinessCaseTypeLiveWriteBoundaryTests(unittest.TestCase):
    def test_offline_smoke_composes_all_five_operations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = build_business_case_type_live_write_smoke(
                database_path=Path(directory) / "state.sqlite"
            )
        self.assertEqual(result["status"], "S4D_READY_OFFLINE")
        self.assertEqual(
            [item["operation"] for item in result["operations"]],
            [
                "case_create",
                "case_status_update",
                "task_create",
                "task_update",
                "business_case_type_backfill",
            ],
        )
        self.assertTrue(
            all(
                item["status"] == "S4D_WRITE_VERIFIED"
                and item["worm_readback_verified"] is True
                for item in result["operations"]
            )
        )
        for counter in (
            "socket_or_dns_calls",
            "external_credential_store_reads",
            "live_graph_calls",
            "azure_live_calls",
            "tenant_writes",
        ):
            self.assertEqual(result["summary"][counter], 0)
        serialized = json.dumps(result, sort_keys=True)
        for forbidden in (
            "synthetic.example,site-collection,site-01",
            "synthetic-write-identity-01",
            "synthetic-bff-uami-read-01",
            "raw provider secret",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_owner_attestation_is_exact_and_drift_fails_closed(self) -> None:
        values = {
            "workspace_id": "notary_team_01",
            "commit_sha": "1" * 40,
            "tree_sha": "2" * 40,
            "domain_contract_sha256": "3" * 64,
            "verification_contract_sha256": "4" * 64,
            "plan_binding_sha256": "5" * 64,
            "toolchain_sha256": "6" * 64,
            "step_sequence_sha256": "7" * 64,
            "evidence_policy_sha256": "8" * 64,
            "target_binding_sha256": "9" * 64,
            "write_principal_binding_sha256": "a" * 64,
            "bff_principal_binding_sha256": "b" * 64,
            "owner_verifier_binding_sha256": "c" * 64,
            "owner_allowlist_sha256": "d" * 64,
            "inspection_principal_binding_sha256": "e" * 64,
        }
        attestation = build_unverified_live_write_approval_attestation(
            **values
        )
        self.assertEqual(
            verify_live_write_owner_approval(
                attestation, expected=values, verifier=_OwnerVerifier()
            ),
            attestation,
        )
        drifted = dict(values, tree_sha="c" * 40)
        with self.assertRaises(LiveWriteGateBlocked):
            verify_live_write_owner_approval(
                attestation, expected=drifted, verifier=_OwnerVerifier()
            )

    def test_identity_readback_rejects_broader_or_shared_principal(self) -> None:
        exact = WriteIdentityContext(
            workspace_id="notary_team_01",
            site_binding_sha256="1" * 64,
            write_principal_binding_sha256="2" * 64,
            write_graph_permissions=("Sites.Selected",),
            write_site_roles=("write",),
            bff_principal_binding_sha256="3" * 64,
            bff_graph_permissions=("Sites.Selected",),
            bff_site_roles=("read",),
            inspection_source="synthetic-offline-owner-bound-readback",
            inspection_observed_at="2026-07-29T12:00:00Z",
            inspection_principal_binding_sha256="4" * 64,
            inspection_approval_sha256="5" * 64,
        )
        validate_write_identity_context(
            exact,
            workspace_id="notary_team_01",
            site_binding_sha256="1" * 64,
            write_principal_binding_sha256="2" * 64,
            bff_principal_binding_sha256="3" * 64,
            inspection_principal_binding_sha256="4" * 64,
            inspection_approval_sha256="5" * 64,
            now=datetime(2026, 7, 29, 12, 1, tzinfo=timezone.utc),
        )
        with self.assertRaises(LiveWriteGateBlocked):
            validate_write_identity_context(
                replace(
                    exact,
                    broader_write_graph_roles=("Sites.FullControl.All",),
                ),
                workspace_id="notary_team_01",
                site_binding_sha256="1" * 64,
                write_principal_binding_sha256="2" * 64,
                bff_principal_binding_sha256="3" * 64,
                inspection_principal_binding_sha256="4" * 64,
                inspection_approval_sha256="5" * 64,
                now=datetime(2026, 7, 29, 12, 1, tzinfo=timezone.utc),
            )
        with self.assertRaisesRegex(
            LiveWriteGateBlocked, "readback is stale"
        ):
            validate_write_identity_context(
                replace(
                    exact,
                    inspection_observed_at="2026-07-29T11:50:00Z",
                ),
                workspace_id="notary_team_01",
                site_binding_sha256="1" * 64,
                write_principal_binding_sha256="2" * 64,
                bff_principal_binding_sha256="3" * 64,
                inspection_principal_binding_sha256="4" * 64,
                inspection_approval_sha256="5" * 64,
                now=datetime(2026, 7, 29, 12, 1, tzinfo=timezone.utc),
            )

    def test_static_gate_blocks_before_identity_or_credentials(self) -> None:
        inspector = type("Inspector", (), {"calls": 0})()
        factory = type("Factory", (), {"calls": 0})()
        boundary = BusinessCaseTypeLiveWriteBoundary(
            target=object(),
            tenant_binding_sha256="1" * 64,
            database_path=Path("/not-used"),
            attestation=object(),
            expected_attestation={},
            owner_approval_verifier=_OwnerVerifier(),
            identity_inspector=inspector,
            identity_factory=factory,
            http_port=object(),
            outbox=object(),
            publisher=object(),
            evidence_context_factory=lambda _plan: object(),
        )
        with patch.object(
            boundary,
            "_validate_static_bindings",
            side_effect=LiveWriteGateBlocked("drift"),
        ):
            result = boundary.execute(plan=object(), plan_builder=object())
        self.assertEqual(result.status, "S4D_BLOCKED")
        self.assertEqual(result.transport_calls, 0)
        self.assertEqual(result.write_attempts, 0)
        self.assertEqual(inspector.calls, 0)
        self.assertEqual(factory.calls, 0)

    def test_real_static_plan_drift_stops_before_owner_and_identity(self) -> None:
        for fault in ("plan_sha", "approval_ref"):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                result = build_business_case_type_live_write_smoke(
                    database_path=Path(directory) / "state.sqlite",
                    fault=fault,
                )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(
                result["summary"]["owner_approval_verification_calls"], 0
            )
            self.assertEqual(result["summary"]["identity_readback_calls"], 0)
            self.assertEqual(result["summary"]["identity_factory_calls"], 0)
            self.assertEqual(result["summary"]["synthetic_http_port_calls"], 0)

    def test_owner_verification_and_identity_provenance_fail_closed(self) -> None:
        for fault, expected_owner_calls, expected_identity_calls in (
            ("owner_verification", 5, 0),
            ("identity_provenance", 5, 5),
        ):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as directory:
                result = build_business_case_type_live_write_smoke(
                    database_path=Path(directory) / "state.sqlite",
                    fault=fault,
                )
            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(
                result["summary"]["owner_approval_verification_calls"],
                expected_owner_calls,
            )
            self.assertEqual(
                result["summary"]["identity_readback_calls"],
                expected_identity_calls,
            )
            self.assertEqual(result["summary"]["identity_factory_calls"], 0)
            self.assertEqual(result["summary"]["synthetic_http_port_calls"], 0)

    def test_foreign_existing_chain_cannot_close_new_local_intent(self) -> None:
        outbox = InMemoryEvidenceOutbox()
        first_local = _LocalHook()
        first_publisher = _Publisher(outbox, first_local.calls)
        first = S4dMutationEvidenceHook(
            local=first_local,
            outbox=outbox,
            publisher=first_publisher,
            context=_evidence_context(),
        )
        intent, outcome, readback = _hook_evidence()
        self.assertTrue(first.intent(intent))
        self.assertTrue(first.outcome(outcome))
        self.assertTrue(first.readback(readback))

        foreign_intent = dict(
            intent,
            mutation_id="7" * 64,
            execution_key="8" * 64,
            plan_sha256="9" * 64,
        )
        foreign_outcome = dict(
            outcome,
            mutation_id="7" * 64,
            execution_key="8" * 64,
            plan_sha256="9" * 64,
        )
        foreign_readback = dict(
            readback,
            mutation_id="7" * 64,
            execution_key="8" * 64,
            plan_sha256="9" * 64,
        )
        second_local = _LocalHook()
        second = S4dMutationEvidenceHook(
            local=second_local,
            outbox=outbox,
            publisher=_Publisher(outbox, second_local.calls),
            context=replace(
                _evidence_context(),
                operation_binding_sha256=(
                    s4d_evidence_operation_binding_sha256(foreign_intent)
                ),
            ),
        )
        self.assertFalse(second.intent(foreign_intent))
        self.assertEqual(second_local.state.intent_state, "open")
        self.assertEqual(second_local.state.reconciliation_state, "required")
        self.assertEqual(len(outbox.records(_evidence_context().correlation_id)), 3)
        self.assertNotIn("local_close", second_local.calls)
        self.assertNotEqual(foreign_outcome, outcome)
        self.assertNotEqual(foreign_readback, readback)

    def test_existing_phase_requires_canonical_byte_identity(self) -> None:
        outbox = _SemanticallyDriftedOutbox()
        first_local = _LocalHook()
        first = S4dMutationEvidenceHook(
            local=first_local,
            outbox=outbox,
            publisher=_Publisher(outbox, first_local.calls),
            context=_evidence_context(),
        )
        intent, _, _ = _hook_evidence()
        self.assertTrue(first.intent(intent))

        second_local = _LocalHook()
        second = S4dMutationEvidenceHook(
            local=second_local,
            outbox=outbox,
            publisher=_Publisher(outbox, second_local.calls),
            context=_evidence_context(),
        )
        self.assertFalse(second.intent(intent))
        self.assertEqual(second_local.state.intent_state, "open")
        self.assertEqual(second_local.state.reconciliation_state, "required")

    def test_local_closure_occurs_only_after_complete_publication(self) -> None:
        local = _LocalHook()
        outbox = InMemoryEvidenceOutbox()
        calls = local.calls
        publisher = _Publisher(outbox, calls)
        hook = S4dMutationEvidenceHook(
            local=local,
            outbox=outbox,
            publisher=publisher,
            context=_evidence_context(),
        )
        intent, outcome, readback = _hook_evidence()
        self.assertTrue(hook.intent(intent))
        intent_event = outbox.records(_evidence_context().correlation_id)[0]
        self.assertEqual(
            intent_event.event["schema_version"],
            "nac.immutable-evidence-event/v0.2",
        )
        self.assertEqual(intent_event.event["action"], "case_create")
        self.assertEqual(
            intent_event.event["operation_binding_sha256"],
            s4d_evidence_operation_binding_sha256(intent),
        )
        self.assertTrue(hook.outcome(outcome))
        self.assertTrue(hook.readback(readback))
        self.assertLess(
            calls.index("publisher_finalize"), calls.index("local_close")
        )
        self.assertEqual(local.state.intent_state, "closed")
        readback_event = outbox.records(_evidence_context().correlation_id)[-1]
        self.assertEqual(
            readback_event.event["provider_state_sha256"],
            readback["provider_state_sha256"],
        )

    def test_s6_intent_failure_is_sticky_and_zero_write(self) -> None:
        local = _LocalHook()
        outbox = _FailingOutbox()
        hook = S4dMutationEvidenceHook(
            local=local,
            outbox=outbox,
            publisher=_Publisher(outbox, local.calls),
            context=_evidence_context(),
        )
        intent, _, _ = _hook_evidence()
        self.assertFalse(hook.intent(intent))
        self.assertEqual(local.state.intent_state, "open")
        self.assertEqual(local.state.reconciliation_state, "required")
        self.assertNotIn("local_close", local.calls)

    def test_publication_failure_is_sticky_and_does_not_close(self) -> None:
        local = _LocalHook()
        outbox = InMemoryEvidenceOutbox()
        publisher = _Publisher(outbox, local.calls)
        publisher.fail = True
        hook = S4dMutationEvidenceHook(
            local=local,
            outbox=outbox,
            publisher=publisher,
            context=_evidence_context(),
        )
        intent, outcome, readback = _hook_evidence()
        self.assertTrue(hook.intent(intent))
        self.assertTrue(hook.outcome(outcome))
        self.assertFalse(hook.readback(readback))
        self.assertEqual(local.state.reconciliation_state, "required")
        self.assertEqual(local.state.intent_state, "open")
        self.assertNotIn("local_close", local.calls)


def _evidence_context() -> LiveWriteEvidenceContext:
    actor = actor_ref(
        tenant_id=TENANT_ID,
        actor_object_id=ACTOR_ID,
        key_version=1,
        key=ACTOR_KEY,
        principal_key=PRINCIPAL_KEY,
    )
    correlation = correlation_ref(
        tenant_id=TENANT_ID,
        source_object_id=SOURCE_ID,
        key_version=1,
        key=ACTOR_KEY,
    )
    return LiveWriteEvidenceContext(
        correlation_id=correlation,
        actor_ref_value=actor,
        tool_id="tool-nac-cli",
        role_id="role-automation",
        action="case_create",
        business_case_type_id="immobilienkaufvertrag",
        catalog_version=next(iter(REGISTERED_CATALOG_VERSIONS)),
        identifier_registry=typed_identifier_registry(
            business_case_type_ids=REGISTERED_BUSINESS_CASE_TYPE_IDS,
            catalog_versions=REGISTERED_CATALOG_VERSIONS,
        ),
        manifest_sha256="a" * 64,
        etag_hmac_key=ACTOR_KEY,
        etag_hmac_key_version=1,
        occurred_at=lambda: "2026-07-29T12:00:00Z",
        operation_binding_sha256=(
            s4d_evidence_operation_binding_sha256(_hook_evidence()[0])
        ),
    )


def _hook_evidence():
    base = {
        "schema_version": "nac.business-case-type-write-evidence-hook/v0.1",
        "mutation_id": "1" * 64,
        "execution_key": "2" * 64,
        "operation": "case_create",
        "target_binding_hash": "3" * 64,
        "plan_sha256": "4" * 64,
        "authorization_run_identity": "5" * 64,
        "intent_generation": 1,
    }
    return (
        {
            **base,
            "result_code": "planned",
            "expected_intent_generation": 0,
            "prior_authorization_run_identity": None,
        },
        {**base, "result_code": "confirmed", "http_status": 201},
        {
            **base,
            "result_code": "verified_applied",
            "http_status": 200,
            "provider_state_sha256": "6" * 64,
            "close_intent": True,
            "completion_state": "terminal",
        },
    )
