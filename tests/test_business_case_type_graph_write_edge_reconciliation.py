from __future__ import annotations

import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nac_m365_graph.business_case_type_write_edge import (
    BusinessCaseTypeGraphWriteEdge,
    GraphResponse,
    MutationPersistenceState,
)
from nac_m365_graph.business_case_type_write_plan import (
    BoundWriteTarget,
    BusinessCaseTypeWritePlanBuilder,
    MutationAuthorization,
)
from notary_kg.business_case_type_mutation import (
    BusinessCaseTypeMutation,
    canonical_hash,
)

FIXTURE = ROOT / "tests/fixtures/business-case-type-graph-write-edge/valid-bindings.fixture.json"


class BusinessCaseTypeWriteEdgeReconciliationTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.target = BoundWriteTarget(**fixture["target"])
        self.authorization = MutationAuthorization(**fixture["authorization"])

    def test_execution_key_isolates_identical_mutation_across_targets(self) -> None:
        mutation = _case_create()
        second_target = replace(
            self.target,
            workspace_id="synthetic-workspace-02",
            site_id="synthetic.example,site-collection,site-02",
            akten_list_id="00000000-0000-4000-8000-000000000020",
            aufgaben_list_id="00000000-0000-4000-8000-000000000021",
            write_identity_id="synthetic-write-identity-02",
            bff_uami_identity_id="synthetic-bff-uami-read-02",
        )
        second_authorization = replace(
            self.authorization,
            workspace_id=second_target.workspace_id,
            site_id=second_target.site_id,
            list_id=second_target.akten_list_id,
            write_identity_id=second_target.write_identity_id,
            write_identity_site_id=second_target.site_id,
            bff_uami_identity_id=second_target.bff_uami_identity_id,
            bff_uami_site_id=second_target.site_id,
        )
        store = _ExecutionKeyStore()
        execution_keys: list[str] = []
        for item_id, target, authorization in (
            ("81", self.target, self.authorization),
            ("82", second_target, second_authorization),
        ):
            builder = BusinessCaseTypeWritePlanBuilder(target)
            plan = builder.build(mutation, authorization)
            evidence = _EvidenceHook(store)
            result = BusinessCaseTypeGraphWriteEdge(
                _Transport([
                    GraphResponse(200, {"value": []}),
                    GraphResponse(201, {"id": item_id}),
                    _item(item_id, f"etag-{item_id}", mutation.fields),
                ]),
                evidence,
                builder,
            ).execute(plan)
            self.assertEqual(result.status, "APPLIED")
            self.assertEqual(result.write_attempts, 1)
            execution_key = evidence.records[0][1]["execution_key"]
            self.assertEqual(
                execution_key,
                canonical_hash(
                    {
                        "target_binding_hash": plan.target_binding_hash,
                        "mutation_id": mutation.mutation_id,
                    }
                ),
            )
            execution_keys.append(execution_key)
        self.assertNotEqual(execution_keys[0], execution_keys[1])
        self.assertEqual(set(store.states), set(execution_keys))
        self.assertTrue(all(
            state.intent_state == "closed" for state in store.states.values()
        ))

    def test_retryable_statuses_allow_later_authorized_run(self) -> None:
        mutation, authorization, builder, plan = self._task_update_plan()
        for status in (408, 429, 401, 403):
            with self.subTest(status=status):
                store = _ExecutionKeyStore()
                first_evidence = _EvidenceHook(store)
                first_transport = _Transport([
                    _item("23", "etag-23", {"Status": "InArbeit"}),
                    GraphResponse(status, {}),
                    _item("23", "etag-23", {"Status": "InArbeit"}),
                ])
                first = BusinessCaseTypeGraphWriteEdge(
                    first_transport, first_evidence, builder
                ).execute(plan)
                self.assertEqual(first.status, "RETRYABLE_NOT_APPLIED")
                self.assertEqual(first.write_attempts, 1)
                self.assertEqual(first.transport_calls, 3)
                self.assertFalse(first.reconciliation_required)
                self.assertEqual(len(first_transport.requests), 3)
                execution_key = first_evidence.records[0][1]["execution_key"]
                self.assertEqual(store.state(execution_key).intent_state, "retryable")

                resumed_transport = _Transport([
                    _item("23", "etag-23", {"Status": "InArbeit"}),
                    GraphResponse(200, {}),
                    _item("23", "etag-24", mutation.fields),
                ])
                resumed = BusinessCaseTypeGraphWriteEdge(
                    resumed_transport, _EvidenceHook(store), builder
                ).execute(plan)
                self.assertEqual(resumed.status, "APPLIED")
                self.assertEqual(resumed.write_attempts, 1)
                self.assertEqual(store.state(execution_key).intent_state, "closed")

    def test_unclear_retryable_response_remains_sticky_without_retry(self) -> None:
        _, _, builder, plan = self._task_update_plan()
        store = _ExecutionKeyStore()
        transport = _Transport([
            _item("23", "etag-23", {"Status": "InArbeit"}),
            GraphResponse(429, {}),
            GraphResponse(503, {}),
        ])
        first = BusinessCaseTypeGraphWriteEdge(
            transport, _EvidenceHook(store), builder
        ).execute(plan)
        self.assertEqual(first.status, "RECONCILIATION_REQUIRED")
        self.assertEqual(first.write_attempts, 1)
        self.assertEqual(len(transport.requests), 3)

        replay_transport = _Transport([])
        replay = BusinessCaseTypeGraphWriteEdge(
            replay_transport, _EvidenceHook(store), builder
        ).execute(plan)
        self.assertEqual(replay.status, "BLOCKED_RECONCILIATION")
        self.assertEqual(replay.write_attempts, 0)
        self.assertEqual(replay_transport.requests, [])

    def test_terminal_rejection_closes_and_blocks_replay(self) -> None:
        _, _, builder, plan = self._task_update_plan()
        store = _ExecutionKeyStore()
        first = BusinessCaseTypeGraphWriteEdge(
            _Transport([
                _item("23", "etag-23", {"Status": "InArbeit"}),
                GraphResponse(400, {}),
                _item("23", "etag-24", {"Status": "InArbeit"}),
            ]),
            _EvidenceHook(store),
            builder,
        ).execute(plan)
        self.assertEqual(first.status, "WRITE_REJECTED")

        replay_transport = _Transport([])
        replay = BusinessCaseTypeGraphWriteEdge(
            replay_transport, _EvidenceHook(store), builder
        ).execute(plan)
        self.assertEqual(replay.status, "BLOCKED_COMPLETED_MUTATION")
        self.assertEqual(replay_transport.requests, [])

    def test_412_remains_terminal_no_retry(self) -> None:
        _, _, builder, plan = self._task_update_plan()
        store = _ExecutionKeyStore()
        first = BusinessCaseTypeGraphWriteEdge(
            _Transport([
                _item("23", "etag-23", {"Status": "InArbeit"}),
                GraphResponse(412, {}),
                _item("23", "etag-24", {"Status": "InArbeit"}),
            ]),
            _EvidenceHook(store),
            builder,
        ).execute(plan)
        self.assertEqual(first.status, "PRECONDITION_FAILED")
        replay_transport = _Transport([])
        replay = BusinessCaseTypeGraphWriteEdge(
            replay_transport, _EvidenceHook(store), builder
        ).execute(plan)
        self.assertEqual(replay.status, "BLOCKED_COMPLETED_MUTATION")
        self.assertEqual(replay_transport.requests, [])

    def test_dedupe_requires_fresh_stable_item_readback(self) -> None:
        mutation = _case_create()
        builder = BusinessCaseTypeWritePlanBuilder(self.target)
        plan = builder.build(mutation, self.authorization)
        preflight = GraphResponse(200, {"value": [{
            "id": "81", "eTag": "etag-81", "fields": dict(mutation.fields)
        }]})
        success_transport = _Transport([
            preflight, _item("81", "etag-81", mutation.fields)
        ])
        success = BusinessCaseTypeGraphWriteEdge(
            success_transport, _EvidenceHook(_ExecutionKeyStore()), builder
        ).execute(plan)
        self.assertEqual(success.status, "DEDUPLICATED")
        self.assertEqual(success.write_attempts, 0)
        self.assertEqual(success.transport_calls, 2)
        self.assertEqual(success_transport.requests[1].method, "GET")
        self.assertIn("/items/81?", success_transport.requests[1].url)

        drift_cases = {
            "deleted": GraphResponse(404, {}),
            "field_drift": _item(
                "81", "etag-81", {**dict(mutation.fields), "Status": "Vollzug"}
            ),
            "etag_drift": _item("81", "etag-82", mutation.fields),
            "item_drift": _item("82", "etag-81", mutation.fields),
        }
        for name, fresh_response in drift_cases.items():
            with self.subTest(name=name):
                transport = _Transport([preflight, fresh_response])
                result = BusinessCaseTypeGraphWriteEdge(
                    transport, _EvidenceHook(_ExecutionKeyStore()), builder
                ).execute(plan)
                self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
                self.assertTrue(result.reconciliation_required)
                self.assertEqual(result.write_attempts, 0)
                self.assertEqual(len(transport.requests), 2)

    def _task_update_plan(self):
        mutation = BusinessCaseTypeMutation.task_update(
            item_id="23", expected_etag="etag-23", fields={"Status": "Erledigt"}
        )
        authorization = replace(
            self.authorization,
            list_id=self.target.aufgaben_list_id,
            approved_operation="task_update",
        )
        builder = BusinessCaseTypeWritePlanBuilder(self.target)
        return mutation, authorization, builder, builder.build(mutation, authorization)


class _Transport:
    def __init__(self, responses: list[GraphResponse]) -> None:
        self.responses = list(responses)
        self.requests = []

    def request(self, request):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("unexpected transport call")
        return self.responses.pop(0)


class _ExecutionKeyStore:
    def __init__(self) -> None:
        self.states: dict[str, MutationPersistenceState] = {}

    def state(self, execution_key: str) -> MutationPersistenceState:
        return self.states.get(
            execution_key, MutationPersistenceState("clear", "absent", 0, 0)
        )

    def open_intent(self, evidence) -> bool:
        key = evidence["execution_key"]
        state = self.state(key)
        expected = evidence["expected_intent_generation"]
        generation = evidence["intent_generation"]
        if (
            state.reconciliation_state != "clear"
            or state.intent_state not in {"absent", "retryable"}
            or state.intent_generation != expected
            or state.closed_generation != expected
            or generation != expected + 1
        ):
            return False
        self.states[key] = MutationPersistenceState("clear", "open", generation, expected)
        return True

    def require_reconciliation(self, evidence) -> bool:
        key = evidence["execution_key"]
        state = self.state(key)
        generation = evidence["intent_generation"]
        if state.intent_state != "open" or state.intent_generation != generation:
            return False
        self.states[key] = MutationPersistenceState(
            "required", "open", generation, state.closed_generation
        )
        return True

    def accept_readback(self, evidence) -> bool:
        key = evidence["execution_key"]
        state = self.state(key)
        generation = evidence["intent_generation"]
        if state.intent_state != "open" or state.intent_generation != generation:
            return False
        if evidence["close_intent"]:
            completion = evidence.get("completion_state", "terminal")
            intent_state = "retryable" if completion == "retryable" else "closed"
            self.states[key] = MutationPersistenceState(
                "clear", intent_state, generation, generation
            )
        return True


class _EvidenceHook:
    def __init__(self, store: _ExecutionKeyStore) -> None:
        self.store = store
        self.records: list[tuple[str, dict]] = []

    def persistence_state(self, execution_key: str) -> MutationPersistenceState:
        return self.store.state(execution_key)

    def intent(self, evidence) -> bool:
        accepted = self.store.open_intent(evidence)
        if accepted:
            self.records.append(("intent", dict(evidence)))
        return accepted

    def outcome(self, evidence) -> bool:
        self.records.append(("outcome", dict(evidence)))
        return True

    def readback(self, evidence) -> bool:
        accepted = self.store.accept_readback(evidence)
        if accepted:
            self.records.append(("readback", dict(evidence)))
        return accepted

    def reconciliation_required(self, evidence) -> bool:
        accepted = self.store.require_reconciliation(evidence)
        if accepted:
            self.records.append(("reconciliation_required", dict(evidence)))
        return accepted


def _case_create() -> BusinessCaseTypeMutation:
    return BusinessCaseTypeMutation.case_create({
        "NacCaseId": "synthetic-case-01",
        "Aktenzeichen": "SYN-01",
        "Vorgangstyp": "immobilienkaufvertrag",
        "VorgangstypId": "immobilienkaufvertrag",
        "Status": "Entwurf",
        "NotarTeam": "NaC-Notar-01",
        "Vertraulichkeitsstufe": "Normal",
        "NacWorkflowVersion": "workflow-v1",
        "KgVersion": "kg-v1",
    })


def _item(item_id: str, etag: str, fields) -> GraphResponse:
    return GraphResponse(200, {
        "id": item_id, "eTag": etag, "fields": dict(fields)
    })


if __name__ == "__main__":
    unittest.main()
