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
    MutationAuthorization,
    BusinessCaseTypeWritePlanBuilder,
    WritePlanBlocked,
)
from notary_kg.business_case_type_mutation import (
    BusinessCaseTypeMutation,
    MutationValidationError,
    S5BackfillBinding,
    canonical_hash,
)


FIXTURE_ROOT = ROOT / "tests/fixtures/business-case-type-graph-write-edge"


class BusinessCaseTypeMutationTests(unittest.TestCase):
    def test_case_create_has_exact_fields_and_requires_legacy_mapping(self) -> None:
        mutation = BusinessCaseTypeMutation.case_create(
            {
                "NacCaseId": "synthetic-case-01",
                "Aktenzeichen": "SYN-01",
                "Vorgangstyp": "immobilienkaufvertrag",
                "VorgangstypId": "immobilienkaufvertrag",
                "Status": "Entwurf",
                "NotarTeam": "NaC-Notar-01",
                "Vertraulichkeitsstufe": "Normal",
                "NacWorkflowVersion": "workflow-v1",
                "KgVersion": "kg-v1",
            }
        )

        self.assertEqual(
            list(mutation.fields),
            [
                "NacCaseId",
                "Aktenzeichen",
                "Vorgangstyp",
                "VorgangstypId",
                "Status",
                "NotarTeam",
                "Vertraulichkeitsstufe",
                "NacWorkflowVersion",
                "KgVersion",
            ],
        )
        self.assertEqual(mutation.dedupe_field, "NacCaseId")

        invalid = dict(mutation.fields)
        invalid["Vorgangstyp"] = "bautraegervertrag"
        invalid["VorgangstypId"] = "bautraegervertrag"
        with self.assertRaisesRegex(MutationValidationError, "legacy"):
            BusinessCaseTypeMutation.case_create(invalid)

    def test_operation_field_allowlists_are_fail_closed(self) -> None:
        with self.assertRaisesRegex(MutationValidationError, "field"):
            BusinessCaseTypeMutation.case_status_update(
                item_id="17",
                expected_etag="synthetic-etag-17",
                fields={"Status": "Vollzug", "Aktenzeichen": "forbidden"},
            )

        task = BusinessCaseTypeMutation.task_create(
            {
                "NacTaskId": "synthetic-task-01",
                "NacCaseId": "synthetic-case-01",
                "BpmnStepCode": "draft-contract",
                "Status": "Offen",
                "RequiresNotaryApproval": True,
                "DueDate": "2026-08-31T16:00:00Z",
            }
        )
        self.assertEqual(task.dedupe_field, "NacTaskId")

        update = BusinessCaseTypeMutation.task_update(
            item_id="23",
            expected_etag="synthetic-etag-23",
            fields={"Status": "Erledigt", "BlockedReason": ""},
        )
        self.assertEqual(set(update.fields), {"Status", "BlockedReason"})

    def test_backfill_binds_exact_s5_operation_hash(self) -> None:
        fixture = _load_json("s5-backfill.fixture.json")
        operation = fixture["operation"]
        binding = S5BackfillBinding(
            manifest_hash=fixture["manifest_hash"],
            record_ref_hash=operation["record_ref_hash"],
            operation_hash=canonical_hash(operation),
            idempotency_key=operation["idempotency_key"],
        )
        mutation = BusinessCaseTypeMutation.business_case_type_backfill(
            item_id=fixture["item_id"],
            expected_etag=operation["if_match"],
            business_case_type_id=operation["value"],
            s5_binding=binding,
        )
        self.assertEqual(mutation.s5_operation_hash, canonical_hash(operation))
        self.assertEqual(mutation.fields, {"VorgangstypId": "immobilienkaufvertrag"})

        with self.assertRaisesRegex(MutationValidationError, "S5 operation hash"):
            BusinessCaseTypeMutation.business_case_type_backfill(
                item_id=fixture["item_id"],
                expected_etag=operation["if_match"],
                business_case_type_id=operation["value"],
                s5_binding=replace(binding, operation_hash="c" * 64),
            )

        unknown_target = "unknown-business-case-type"
        unknown_idempotency = canonical_hash(
            [
                fixture["manifest_hash"],
                operation["record_ref_hash"],
                unknown_target,
                operation["if_match"],
            ]
        )
        unknown_operation = {
            **operation,
            "value": unknown_target,
            "idempotency_key": unknown_idempotency,
        }
        with self.assertRaisesRegex(MutationValidationError, "canonical"):
            BusinessCaseTypeMutation.business_case_type_backfill(
                item_id=fixture["item_id"],
                expected_etag=operation["if_match"],
                business_case_type_id=unknown_target,
                s5_binding=S5BackfillBinding(
                    manifest_hash=fixture["manifest_hash"],
                    record_ref_hash=operation["record_ref_hash"],
                    operation_hash=canonical_hash(unknown_operation),
                    idempotency_key=unknown_idempotency,
                ),
            )


class BusinessCaseTypeWritePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = _load_json("valid-bindings.fixture.json")
        self.target = BoundWriteTarget(**fixture["target"])
        self.authorization = MutationAuthorization(**fixture["authorization"])
        self.builder = BusinessCaseTypeWritePlanBuilder(self.target)

    def test_five_operations_have_exact_graph_rest_v1_targets(self) -> None:
        operations = [
            (
                _case_create(),
                "POST",
                "/sites/synthetic.example,site-collection,site-01/lists/"
                "00000000-0000-4000-8000-000000000010/items",
            ),
            (
                BusinessCaseTypeMutation.case_status_update(
                    item_id="17",
                    expected_etag="synthetic-etag-17",
                    fields={"Status": "Vollzug"},
                ),
                "PATCH",
                "/sites/synthetic.example,site-collection,site-01/lists/"
                "00000000-0000-4000-8000-000000000010/items/17/fields",
            ),
            (
                _task_create(),
                "POST",
                "/sites/synthetic.example,site-collection,site-01/lists/"
                "00000000-0000-4000-8000-000000000011/items",
            ),
            (
                BusinessCaseTypeMutation.task_update(
                    item_id="23",
                    expected_etag="synthetic-etag-23",
                    fields={"Status": "Erledigt"},
                ),
                "PATCH",
                "/sites/synthetic.example,site-collection,site-01/lists/"
                "00000000-0000-4000-8000-000000000011/items/23/fields",
            ),
            (
                _backfill(),
                "PATCH",
                "/sites/synthetic.example,site-collection,site-01/lists/"
                "00000000-0000-4000-8000-000000000010/items/41/fields",
            ),
        ]
        for mutation, method, suffix in operations:
            with self.subTest(operation=mutation.operation):
                auth = _authorization_for(self.authorization, mutation)
                plan = self.builder.build(mutation, auth)
                self.assertEqual(plan.write_method, method)
                self.assertEqual(plan.write_url, "https://graph.microsoft.com/v1.0" + suffix)
                if method == "PATCH":
                    self.assertNotIn("$expand=fields&", plan.freshness_request.url)
                    self.assertIn(
                        "$expand=fields($select=", plan.freshness_request.url
                    )

    def test_target_hash_binds_both_lists_for_every_operation(self) -> None:
        cases = [
            (_case_create(), "aufgaben_list_id"),
            (_task_create(), "akten_list_id"),
        ]
        for mutation, inactive_list_attribute in cases:
            with self.subTest(operation=mutation.operation):
                fixture = _load_json("valid-bindings.fixture.json")
                target = BoundWriteTarget(**fixture["target"])
                authorization = MutationAuthorization(**fixture["authorization"])
                builder = BusinessCaseTypeWritePlanBuilder(target)
                plan = builder.build(
                    mutation, _authorization_for(authorization, mutation)
                )
                object.__setattr__(
                    target,
                    inactive_list_attribute,
                    "00000000-0000-4000-8000-000000000099",
                )
                transport = _FakeTransport([])

                result = BusinessCaseTypeGraphWriteEdge(
                    transport, _EvidenceHook(), builder
                ).execute(plan)

                self.assertEqual(result.status, "BLOCKED_PLAN")
                self.assertEqual(result.write_attempts, 0)
                self.assertEqual(transport.requests, [])

    def test_site_list_role_purpose_approval_and_identity_drift_block(self) -> None:
        mutation = _case_create()
        drifts = [
            {"site_id": "foreign-site"},
            {"list_id": self.target.aufgaben_list_id},
            {"actor_role": "viewer"},
            {"purpose": "inventory"},
            {"write_approved": False},
            {"approved_operation": "task_create"},
            {"write_identity_id": self.target.bff_uami_identity_id},
            {"write_site_grant_role": "read"},
            {"bff_uami_site_grant_role": "write"},
        ]
        for drift in drifts:
            with self.subTest(drift=drift):
                with self.assertRaises(WritePlanBlocked):
                    self.builder.build(mutation, replace(self.authorization, **drift))

    def test_write_and_bff_identities_must_be_separate(self) -> None:
        with self.assertRaisesRegex(WritePlanBlocked, "separate"):
            BusinessCaseTypeWritePlanBuilder(
                replace(
                    self.target,
                    write_identity_id=self.target.bff_uami_identity_id,
                )
            )


class BusinessCaseTypeGraphWriteEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = _load_json("valid-bindings.fixture.json")
        self.target = BoundWriteTarget(**fixture["target"])
        self.authorization = MutationAuthorization(**fixture["authorization"])
        self.builder = BusinessCaseTypeWritePlanBuilder(self.target)


    def test_all_five_operations_execute_with_canonical_revalidation(self) -> None:
        mutations = [
            _case_create(),
            BusinessCaseTypeMutation.case_status_update(
                item_id="17",
                expected_etag="synthetic-etag-17",
                fields={"Status": "Vollzug"},
            ),
            _task_create(),
            BusinessCaseTypeMutation.task_update(
                item_id="23",
                expected_etag="synthetic-etag-23",
                fields={"Status": "Erledigt"},
            ),
            _backfill(),
        ]
        for index, mutation in enumerate(mutations, start=1):
            with self.subTest(operation=mutation.operation):
                plan = self.builder.build(
                    mutation, _authorization_for(self.authorization, mutation)
                )
                item_id = mutation.item_id or str(80 + index)
                if plan.write_method == "POST":
                    responses = [
                        GraphResponse(200, {"value": []}),
                        GraphResponse(201, {"id": item_id, "eTag": f"synthetic-etag-{item_id}"}),
                        GraphResponse(
                            200,
                            {
                                "id": item_id,
                                "eTag": f"synthetic-etag-{item_id}",
                                "fields": dict(mutation.fields),
                            },
                        ),
                    ]
                else:
                    responses = [
                        GraphResponse(
                            200,
                            {
                                "id": item_id,
                                "eTag": mutation.expected_etag,
                                "fields": dict(mutation.fields),
                            },
                        ),
                        GraphResponse(200, {}),
                        GraphResponse(
                            200,
                            {
                                "id": item_id,
                                "eTag": f"{mutation.expected_etag}-after",
                                "fields": dict(mutation.fields),
                            },
                        ),
                    ]
                result = BusinessCaseTypeGraphWriteEdge(
                    _FakeTransport(responses), _EvidenceHook(), self.builder
                ).execute(plan)
                self.assertEqual(result.status, "APPLIED")

    def test_execute_rejects_forged_plan_components_before_transport(self) -> None:
        mutation = _case_create()
        plan = self.builder.build(mutation, self.authorization)
        forged_plans = [
            replace(plan, write_url="https://graph.microsoft.com/v1.0/sites/foreign/lists/foreign/items"),
            replace(plan, logical_list_name="AufgabenFristen"),
            replace(plan, target_binding_hash="0" * 64),
            replace(plan, plan_sha256="f" * 64),
            replace(plan, collection_url=plan.collection_url + "/forged"),
            replace(plan, write_payload={"fields": {"NacCaseId": "forged"}}),
            replace(
                plan,
                authorization=replace(plan.authorization, actor_role="viewer"),
            ),
            replace(
                plan,
                authorization=replace(
                    plan.authorization,
                    approval_ref="synthetic-approval-forged",
                ),
            ),
            replace(
                plan,
                dedupe_request=replace(
                    plan.dedupe_request,
                    url=plan.dedupe_request.url + "%20or%201%20eq%201",
                ),
            ),
        ]
        for forged in forged_plans:
            with self.subTest(field=forged):
                transport = _FakeTransport([])
                result = BusinessCaseTypeGraphWriteEdge(
                    transport, _EvidenceHook(), self.builder
                ).execute(forged)
                self.assertEqual(result.status, "BLOCKED_PLAN")
                self.assertEqual(result.reason_code, "plan_revalidation_failed")
                self.assertEqual(transport.requests, [])

        backfill = _backfill()
        backfill_plan = self.builder.build(
            backfill, _authorization_for(self.authorization, backfill)
        )
        object.__setattr__(
            backfill_plan.mutation, "s5_operation_hash", "c" * 64
        )
        transport = _FakeTransport([])
        result = BusinessCaseTypeGraphWriteEdge(
            transport, _EvidenceHook(), self.builder
        ).execute(backfill_plan)
        self.assertEqual(result.status, "BLOCKED_PLAN")
        self.assertEqual(transport.requests, [])

        patch = BusinessCaseTypeMutation.task_update(
            item_id="23",
            expected_etag="synthetic-etag-23",
            fields={"Status": "Erledigt"},
        )
        patch_plan = self.builder.build(
            patch, _authorization_for(self.authorization, patch)
        )
        forged_freshness = replace(
            patch_plan,
            freshness_request=replace(
                patch_plan.freshness_request,
                url=patch_plan.freshness_request.url + "&$select=Title",
            ),
        )
        transport = _FakeTransport([])
        result = BusinessCaseTypeGraphWriteEdge(
            transport, _EvidenceHook(), self.builder
        ).execute(forged_freshness)
        self.assertEqual(result.status, "BLOCKED_PLAN")
        self.assertEqual(transport.requests, [])

    def test_dedupe_next_link_is_ambiguous_without_write(self) -> None:
        mutation = _case_create()
        plan = self.builder.build(mutation, self.authorization)
        transport = _FakeTransport(
            [
                GraphResponse(
                    200,
                    {
                        "value": [],
                        "@odata.nextLink": "https://graph.microsoft.com/v1.0/secret-next-page",
                    },
                )
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(
            transport, evidence, self.builder
        ).execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
        self.assertEqual(result.write_attempts, 0)
        self.assertEqual(evidence.phases, ["intent", "outcome", "reconciliation_required", "readback"])
        self.assertNotIn("secret-next-page", str(result))
        self.assertNotIn("secret-next-page", str(evidence.records))

    def test_412_readback_distinguishes_actual_fields_and_invalid_shape(self) -> None:
        mutation = BusinessCaseTypeMutation.case_status_update(
            item_id="17",
            expected_etag="synthetic-etag-17",
            fields={"Status": "Vollzug"},
        )
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        cases = [
            (
                GraphResponse(200, {"id": "17", "eTag": "synthetic-etag-18", "fields": {"Status": "InPrüfung"}}),
                "PRECONDITION_FAILED",
                "verified_not_applied",
            ),
            (
                GraphResponse(
                    200,
                    {
                        "@odata.context": "synthetic-metadata",
                        "id": "17",
                        "eTag": "synthetic-etag-18",
                        "fields": {"Status": "Vollzug"},
                    },
                ),
                "PRECONDITION_FAILED_ALREADY_APPLIED",
                "verified_applied",
            ),
            (
                GraphResponse(500, {"fields": {"Status": "InPrüfung"}}),
                "RECONCILIATION_REQUIRED",
                "not_verified",
            ),
        ]
        for readback, expected_status, expected_code in cases:
            with self.subTest(expected_status=expected_status):
                evidence = _EvidenceHook()
                transport = _FakeTransport(
                    [
                        GraphResponse(200, {"id": "17", "eTag": "synthetic-etag-17", "fields": {"Status": "InPrüfung"}}),
                        GraphResponse(412, {}),
                        readback,
                    ]
                )
                result = BusinessCaseTypeGraphWriteEdge(
                    transport, evidence, self.builder
                ).execute(plan)
                self.assertEqual(result.status, expected_status)
                self.assertEqual(evidence.records[-1][1]["result_code"], expected_code)
                if expected_status == "RECONCILIATION_REQUIRED":
                    self.assertEqual(
                        evidence.phases,
                        ["intent", "outcome", "reconciliation_required", "readback"],
                    )

    def test_negative_readback_distinguishes_actual_fields_and_invalid_shape(self) -> None:
        mutation = BusinessCaseTypeMutation.task_update(
            item_id="23",
            expected_etag="synthetic-etag-23",
            fields={"Status": "Erledigt"},
        )
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        cases = [
            (
                GraphResponse(
                    200,
                    {
                        "id": "23",
                        "eTag": "synthetic-etag-24",
                        "fields": {"Status": "InArbeit"},
                    },
                ),
                "WRITE_REJECTED",
                "verified_not_applied",
            ),
            (
                GraphResponse(
                    200,
                    {
                        "id": "23",
                        "eTag": "synthetic-etag-24",
                        "fields": {"Status": "Erledigt"},
                    },
                ),
                "WRITE_REJECTED_STATE_ALREADY_APPLIED",
                "verified_applied",
            ),
            (
                GraphResponse(
                    200,
                    {
                        "id": "wrong-item",
                        "eTag": "synthetic-etag-24",
                        "fields": {"Status": "InArbeit"},
                    },
                ),
                "RECONCILIATION_REQUIRED",
                "not_verified",
            ),
        ]
        for readback, expected_status, expected_code in cases:
            with self.subTest(expected_status=expected_status):
                transport = _FakeTransport(
                    [
                        GraphResponse(
                            200,
                            {
                                "id": "23",
                                "eTag": "synthetic-etag-23",
                                "fields": {"Status": "InArbeit"},
                            },
                        ),
                        GraphResponse(400, {}),
                        readback,
                    ]
                )
                evidence = _EvidenceHook()
                result = BusinessCaseTypeGraphWriteEdge(
                    transport, evidence, self.builder
                ).execute(plan)
                self.assertEqual(result.status, expected_status)
                self.assertEqual(
                    evidence.records[-1][1]["result_code"], expected_code
                )
                if expected_status == "RECONCILIATION_REQUIRED":
                    self.assertEqual(
                        evidence.phases,
                        [
                            "intent",
                            "outcome",
                            "reconciliation_required",
                            "readback",
                        ],
                    )

    def test_preflight_transport_errors_are_structured_and_redacted(self) -> None:
        secret = "secret-token https://graph.microsoft.com/v1.0/sites/private/items/17"
        mutations = [
            (_case_create(), "dedupe_transport_unavailable"),
            (
                BusinessCaseTypeMutation.case_status_update(
                    item_id="17",
                    expected_etag="synthetic-etag-17",
                    fields={"Status": "Vollzug"},
                ),
                "freshness_transport_unavailable",
            ),
            (_task_create(), "dedupe_transport_unavailable"),
            (
                BusinessCaseTypeMutation.task_update(
                    item_id="23",
                    expected_etag="synthetic-etag-23",
                    fields={"Status": "Erledigt"},
                ),
                "freshness_transport_unavailable",
            ),
            (_backfill(), "freshness_transport_unavailable"),
        ]
        for mutation, reason in mutations:
            with self.subTest(operation=mutation.operation):
                auth = _authorization_for(self.authorization, mutation)
                plan = self.builder.build(mutation, auth)
                transport = _FakeTransport([RuntimeError(secret)])
                result = BusinessCaseTypeGraphWriteEdge(
                    transport, _EvidenceHook(), self.builder
                ).execute(plan)
                self.assertEqual(result.status, "BLOCKED_PREFLIGHT_TRANSPORT")
                self.assertEqual(result.reason_code, reason)
                self.assertNotIn(secret, str(result))
                self.assertEqual(result.write_attempts, 0)

    def test_unacknowledged_durable_intent_blocks_before_write(self) -> None:
        class _UnacknowledgedIntent(_EvidenceHook):
            def intent(self, evidence) -> bool:
                super().intent(evidence)
                return False

        mutation = _case_create()
        plan = self.builder.build(mutation, self.authorization)
        transport = _FakeTransport([GraphResponse(200, {"value": []})])

        result = BusinessCaseTypeGraphWriteEdge(
            transport, _UnacknowledgedIntent(), self.builder
        ).execute(plan)

        self.assertEqual(result.status, "BLOCKED_EVIDENCE")
        self.assertEqual(result.write_attempts, 0)
        self.assertEqual([request.method for request in transport.requests], ["GET"])

    def test_create_deduplicates_without_post_and_emits_complete_evidence(self) -> None:
        mutation = _case_create()
        plan = self.builder.build(mutation, self.authorization)
        item = {
            "id": "71",
            "eTag": "synthetic-etag-71",
            "fields": dict(mutation.fields),
        }
        transport = _FakeTransport(
            [
                GraphResponse(200, {"value": [item]}),
                GraphResponse(200, item),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder).execute(plan)

        self.assertEqual(result.status, "DEDUPLICATED")
        self.assertEqual(result.write_attempts, 0)
        self.assertEqual(
            [request.method for request in transport.requests], ["GET", "GET"]
        )
        self.assertIn("/items/71?", transport.requests[1].url)
        self.assertEqual(evidence.phases, ["intent", "outcome", "readback"])

    def test_create_identity_with_divergent_fields_requires_reconciliation(self) -> None:
        mutation = _case_create()
        plan = self.builder.build(mutation, self.authorization)
        divergent = dict(mutation.fields)
        divergent["Status"] = "Pausiert"
        transport = _FakeTransport(
            [
                GraphResponse(
                    200,
                    {
                        "value": [
                            {
                                "id": "71",
                                "eTag": "synthetic-etag-71",
                                "fields": divergent,
                            }
                        ]
                    },
                )
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder).execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
        self.assertEqual(result.write_attempts, 0)
        self.assertEqual([request.method for request in transport.requests], ["GET"])
        self.assertEqual(
            evidence.phases,
            ["intent", "outcome", "reconciliation_required", "readback"],
        )

    def test_concurrent_create_conflict_deduplicates_after_exact_readback(self) -> None:
        mutation = _task_create()
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                GraphResponse(409, {}),
                GraphResponse(
                    200,
                    {
                        "value": [
                            {
                                "id": "81",
                                "eTag": "synthetic-etag-81",
                                "fields": dict(mutation.fields),
                            }
                        ]
                    },
                ),
                GraphResponse(
                    200,
                    {
                        "id": "81",
                        "eTag": "synthetic-etag-81",
                        "fields": dict(mutation.fields),
                    },
                ),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder).execute(plan)

        self.assertEqual(result.status, "DEDUPLICATED")
        self.assertEqual(result.write_attempts, 1)
        self.assertEqual(
            [request.method for request in transport.requests],
            ["GET", "POST", "GET", "GET"],
        )
        self.assertIn("/items/81?", transport.requests[-1].url)
        self.assertEqual(evidence.phases, ["intent", "outcome", "readback"])

    def test_409_ambiguous_readback_requires_reconciliation_without_retry(self) -> None:
        mutation = _task_create()
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                GraphResponse(409, {}),
                GraphResponse(
                    200,
                    {
                        "value": [],
                        "@odata.nextLink": "https://graph.microsoft.com/v1.0/private",
                    },
                ),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(
            transport, evidence, self.builder
        ).execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
        self.assertEqual(result.write_attempts, 1)
        self.assertEqual([request.method for request in transport.requests], ["GET", "POST", "GET"])
        self.assertEqual(
            evidence.phases,
            ["intent", "outcome", "reconciliation_required", "readback"],
        )
        self.assertNotIn("private", str(evidence.records))

    def test_patch_uses_fresh_exact_etag_and_412_is_not_retried(self) -> None:
        mutation = BusinessCaseTypeMutation.case_status_update(
            item_id="17",
            expected_etag="synthetic-etag-17",
            fields={"Status": "Vollzug"},
        )
        plan = self.builder.build(
            mutation,
            replace(
                self.authorization,
                approved_operation="case_status_update",
                approval_ref="synthetic-approval-case-status-01",
            ),
        )
        transport = _FakeTransport(
            [
                GraphResponse(200, {"id": "17", "eTag": "synthetic-etag-17", "fields": {"Status": "InPrüfung"}}),
                GraphResponse(412, {}),
                GraphResponse(200, {"id": "17", "eTag": "synthetic-etag-18", "fields": {"Status": "InPrüfung"}}),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder).execute(plan)

        self.assertEqual(result.status, "PRECONDITION_FAILED")
        self.assertEqual(result.write_attempts, 1)
        self.assertEqual([request.method for request in transport.requests], ["GET", "PATCH", "GET"])
        self.assertEqual(transport.requests[1].headers["If-Match"], "synthetic-etag-17")
        self.assertEqual(evidence.phases, ["intent", "outcome", "readback"])

    def test_etag_drift_blocks_before_evidence_and_patch(self) -> None:
        mutation = BusinessCaseTypeMutation.task_update(
            item_id="23",
            expected_etag="synthetic-etag-23",
            fields={"Status": "Erledigt"},
        )
        plan = self.builder.build(
            mutation,
            _authorization_for(self.authorization, mutation),
        )
        transport = _FakeTransport(
            [
                GraphResponse(200, {"id": "23", "eTag": "synthetic-etag-24", "fields": {"Status": "InArbeit"}}),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder).execute(plan)

        self.assertEqual(result.status, "BLOCKED_ETAG_DRIFT")
        self.assertEqual(result.write_attempts, 0)
        self.assertEqual(evidence.phases, [])

    def test_uncertain_patch_uses_bound_item_readback_and_stays_sticky(self) -> None:
        mutation = BusinessCaseTypeMutation.task_update(
            item_id="23",
            expected_etag="synthetic-etag-23",
            fields={"Status": "Erledigt"},
        )
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        transport = _FakeTransport(
            [
                GraphResponse(
                    200,
                    {
                        "id": "23",
                        "eTag": "synthetic-etag-23",
                        "fields": {"Status": "InArbeit"},
                    },
                ),
                RuntimeError("secret PATCH transport failure"),
                GraphResponse(
                    200,
                    {
                        "id": "23",
                        "eTag": "synthetic-etag-24",
                        "fields": {"Status": "Erledigt"},
                    },
                ),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(
            transport, evidence, self.builder
        ).execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
        self.assertEqual([request.method for request in transport.requests], ["GET", "PATCH", "GET"])
        self.assertIn("/items/23?", transport.requests[-1].url)
        self.assertEqual(
            evidence.phases,
            ["intent", "outcome", "reconciliation_required", "readback"],
        )
        self.assertNotIn("secret PATCH", str(result))
        self.assertNotIn("secret PATCH", str(evidence.records))

    def test_uncertain_write_marks_sticky_reconciliation_before_readback(self) -> None:
        mutation = _task_create()
        plan = self.builder.build(
            mutation,
            _authorization_for(self.authorization, mutation),
        )
        transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                GraphResponse(503, {}),
                GraphResponse(200, {"value": []}),
            ]
        )
        evidence = _EvidenceHook()
        edge = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder)

        result = edge.execute(plan)
        first_request_count = len(transport.requests)
        replay = edge.execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
        self.assertTrue(result.reconciliation_required)
        self.assertEqual(
            evidence.phases,
            ["intent", "outcome", "reconciliation_required", "readback"],
        )
        self.assertEqual(replay.status, "BLOCKED_RECONCILIATION")
        self.assertEqual(len(transport.requests), first_request_count)

    def test_failed_marker_ack_blocks_restart_even_when_store_reports_clear(self) -> None:
        mutation = _task_create()
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        store = _PersistentEvidenceStore()
        first_transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                RuntimeError("synthetic uncertain write"),
                GraphResponse(200, {"value": []}),
            ]
        )
        first = BusinessCaseTypeGraphWriteEdge(
            first_transport,
            _EvidenceHook(store=store, fail_on={"reconciliation_required"}),
            self.builder,
        ).execute(plan)

        self.assertEqual(first.status, "RECONCILIATION_PERSISTENCE_FAILED")
        self.assertEqual(
            store.state(_execution_key(plan)).reconciliation_state, "clear"
        )
        self.assertEqual(
            store.state(_execution_key(plan)).intent_state, "open"
        )

        second_transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                GraphResponse(201, {"id": "81"}),
                GraphResponse(
                    200,
                    {
                        "id": "81",
                        "eTag": "synthetic-etag-81",
                        "fields": dict(mutation.fields),
                    },
                ),
            ]
        )
        restarted = BusinessCaseTypeGraphWriteEdge(
            second_transport,
            _EvidenceHook(store=store),
            self.builder,
        ).execute(plan)

        self.assertNotEqual(restarted.status, "APPLIED")
        self.assertEqual(restarted.write_attempts, 0)
        self.assertEqual(second_transport.requests, [])

    def test_lost_closure_confirmation_blocks_fresh_process_replay(self) -> None:
        mutation = _task_create()
        authorization = _authorization_for(self.authorization, mutation)
        plan = self.builder.build(mutation, authorization)
        store = _PersistentEvidenceStore()
        first_transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                GraphResponse(201, {"id": "81"}),
                GraphResponse(
                    200,
                    {
                        "id": "81",
                        "eTag": "synthetic-etag-81",
                        "fields": dict(mutation.fields),
                    },
                ),
            ]
        )
        first = BusinessCaseTypeGraphWriteEdge(
            first_transport,
            _ClosureConfirmationLostHook(store=store),
            self.builder,
        ).execute(plan)

        self.assertEqual(first.status, "RECONCILIATION_PERSISTENCE_FAILED")
        self.assertEqual(store.state(_execution_key(plan)).intent_state, "closed")

        fresh_builder = BusinessCaseTypeWritePlanBuilder(self.target)
        fresh_plan = fresh_builder.build(mutation, authorization)
        second_transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                GraphResponse(201, {"id": "82"}),
                GraphResponse(
                    200,
                    {
                        "id": "82",
                        "eTag": "synthetic-etag-82",
                        "fields": dict(mutation.fields),
                    },
                ),
            ]
        )
        replay = BusinessCaseTypeGraphWriteEdge(
            second_transport,
            _EvidenceHook(store=store),
            fresh_builder,
        ).execute(fresh_plan)

        self.assertNotEqual(replay.status, "APPLIED")
        self.assertEqual(replay.write_attempts, 0)
        self.assertEqual(second_transport.requests, [])

    def test_patch_5xx_ignores_foreign_response_id_for_readback(self) -> None:
        mutation = BusinessCaseTypeMutation.task_update(
            item_id="23",
            expected_etag="synthetic-etag-23",
            fields={"Status": "Erledigt"},
        )
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        transport = _FakeTransport(
            [
                GraphResponse(
                    200,
                    {
                        "id": "23",
                        "eTag": "synthetic-etag-23",
                        "fields": {"Status": "InArbeit"},
                    },
                ),
                GraphResponse(503, {"id": "99"}),
                GraphResponse(
                    200,
                    {
                        "id": "23",
                        "eTag": "synthetic-etag-24",
                        "fields": {"Status": "Erledigt"},
                    },
                ),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(
            transport, evidence, self.builder
        ).execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
        self.assertIn("/items/23?", transport.requests[-1].url)
        self.assertNotIn("/items/99", transport.requests[-1].url)
        for _, record in evidence.records:
            self.assertNotIn("item_id", record)
            self.assertNotIn("response_item_id", record)
            self.assertNotIn("readback_item_id", record)
            self.assertNotIn("99", record.values())

    def test_transport_exception_and_reconciliation_hook_failure_stay_sticky(self) -> None:
        mutation = _task_create()
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                RuntimeError("synthetic uncertain write"),
                GraphResponse(200, {"value": []}),
            ]
        )
        evidence = _EvidenceHook(fail_on={"reconciliation_required"})
        edge = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder)

        result = edge.execute(plan)
        replay = edge.execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_PERSISTENCE_FAILED")
        self.assertEqual(result.transport_calls, 3)
        restarted = BusinessCaseTypeGraphWriteEdge(
            transport, evidence, self.builder
        ).execute(plan)
        self.assertEqual(restarted.status, "BLOCKED_RECONCILIATION")
        self.assertEqual(replay.status, "BLOCKED_RECONCILIATION")

    def test_412_with_missing_outcome_evidence_requires_reconciliation(self) -> None:
        mutation = BusinessCaseTypeMutation.case_status_update(
            item_id="17",
            expected_etag="synthetic-etag-17",
            fields={"Status": "Vollzug"},
        )
        plan = self.builder.build(
            mutation, _authorization_for(self.authorization, mutation)
        )
        transport = _FakeTransport(
            [
                GraphResponse(200, {"id": "17", "eTag": "synthetic-etag-17", "fields": {"Status": "InPrüfung"}}),
                GraphResponse(412, {}),
                GraphResponse(200, {"id": "17", "eTag": "synthetic-etag-18", "fields": {"Status": "InPrüfung"}}),
            ]
        )
        evidence = _EvidenceHook(fail_on={"outcome"})

        result = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder).execute(plan)

        self.assertEqual(result.status, "RECONCILIATION_REQUIRED")
        self.assertTrue(result.reconciliation_required)

    def test_successful_create_orders_intent_write_outcome_and_readback(self) -> None:
        mutation = _task_create()
        plan = self.builder.build(mutation, _authorization_for(self.authorization, mutation))
        transport = _FakeTransport(
            [
                GraphResponse(200, {"value": []}),
                GraphResponse(201, {"id": "81", "eTag": "synthetic-etag-81"}),
                GraphResponse(
                    200,
                    {
                        "id": "81",
                        "eTag": "synthetic-etag-81",
                        "fields": dict(mutation.fields),
                    },
                ),
            ]
        )
        evidence = _EvidenceHook()

        result = BusinessCaseTypeGraphWriteEdge(transport, evidence, self.builder).execute(plan)

        self.assertEqual(result.status, "APPLIED")
        self.assertEqual([request.method for request in transport.requests], ["GET", "POST", "GET"])
        self.assertEqual(evidence.phases, ["intent", "outcome", "readback"])
        self.assertLess(evidence.order.index("intent"), transport.order.index("POST"))


class _FakeTransport:
    def __init__(self, responses: list[GraphResponse | BaseException]) -> None:
        self.responses = list(responses)
        self.requests = []
        self.order: list[str] = []

    def request(self, request):
        self.requests.append(request)
        self.order.append(request.method)
        if not self.responses:
            raise AssertionError("unexpected transport call")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class _PersistentEvidenceStore:
    def __init__(self) -> None:
        self.states: dict[str, MutationPersistenceState] = {}

    def state(self, execution_key: str) -> MutationPersistenceState:
        return self.states.get(
            execution_key,
            MutationPersistenceState(
                reconciliation_state="clear",
                intent_state="absent",
                intent_generation=0,
                closed_generation=0,
                authorization_run_identity=None,
            ),
        )

    def open_intent(self, evidence) -> bool:
        execution_key = evidence["execution_key"]
        state = self.state(execution_key)
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
        run_identity = evidence["authorization_run_identity"]
        prior_run_identity = evidence["prior_authorization_run_identity"]
        if (
            state.authorization_run_identity != prior_run_identity
            or (
                state.intent_state == "retryable"
                and run_identity == prior_run_identity
            )
        ):
            return False
        self.states[execution_key] = MutationPersistenceState(
            reconciliation_state="clear",
            intent_state="open",
            intent_generation=generation,
            closed_generation=expected,
            authorization_run_identity=run_identity,
        )
        return True

    def require_reconciliation(self, evidence) -> bool:
        execution_key = evidence["execution_key"]
        state = self.state(execution_key)
        generation = evidence["intent_generation"]
        if state.intent_state != "open" or state.intent_generation != generation:
            return False
        self.states[execution_key] = MutationPersistenceState(
            reconciliation_state="required",
            intent_state="open",
            intent_generation=generation,
            closed_generation=state.closed_generation,
            authorization_run_identity=state.authorization_run_identity,
        )
        return True

    def accept_readback(self, evidence) -> bool:
        execution_key = evidence["execution_key"]
        state = self.state(execution_key)
        generation = evidence["intent_generation"]
        if state.intent_state != "open" or state.intent_generation != generation:
            return False
        if evidence["close_intent"]:
            if state.reconciliation_state != "clear":
                return False
            self.states[execution_key] = MutationPersistenceState(
                reconciliation_state="clear",
                intent_state=(
                    "retryable"
                    if evidence.get("completion_state") == "retryable"
                    else "closed"
                ),
                intent_generation=generation,
                closed_generation=generation,
                authorization_run_identity=state.authorization_run_identity,
            )
        return True


class _EvidenceHook:
    def __init__(
        self,
        *,
        fail_on: set[str] | None = None,
        store: _PersistentEvidenceStore | None = None,
    ) -> None:
        self.phases: list[str] = []
        self.records: list[tuple[str, dict]] = []
        self.order = self.phases
        self.store = store or _PersistentEvidenceStore()
        self.fail_on = fail_on or set()

    def persistence_state(self, execution_key: str) -> MutationPersistenceState:
        if "persistence_state" in self.fail_on:
            return MutationPersistenceState(
                reconciliation_state="unavailable",
                intent_state="unavailable",
                intent_generation=0,
                closed_generation=0,
            )
        return self.store.state(execution_key)

    def intent(self, evidence) -> bool:
        self._ensure_available("intent")
        if not self.store.open_intent(evidence):
            return False
        self._record("intent", evidence)
        return True

    def outcome(self, evidence) -> bool:
        self._record("outcome", evidence)
        return True

    def readback(self, evidence) -> bool:
        self._ensure_available("readback")
        if not self.store.accept_readback(evidence):
            return False
        self._record("readback", evidence)
        return True

    def reconciliation_required(self, evidence) -> bool:
        if "reconciliation_required" in self.fail_on:
            return False
        if not self.store.require_reconciliation(evidence):
            return False
        self._record("reconciliation_required", evidence)
        return True

    def _ensure_available(self, phase: str) -> None:
        if phase in self.fail_on:
            raise RuntimeError(f"synthetic {phase} failure")

    def _record(self, phase: str, evidence) -> None:
        self._ensure_available(phase)
        payload = dict(evidence)
        self.phases.append(phase)
        self.records.append((phase, payload))


class _ClosureConfirmationLostHook(_EvidenceHook):
    def __init__(self, *, store: _PersistentEvidenceStore) -> None:
        super().__init__(store=store)
        self.failed_closed_confirmation = False

    def persistence_state(self, execution_key: str) -> MutationPersistenceState:
        state = super().persistence_state(execution_key)
        if state.intent_state == "closed" and not self.failed_closed_confirmation:
            self.failed_closed_confirmation = True
            return MutationPersistenceState(
                reconciliation_state="unavailable",
                intent_state="unavailable",
                intent_generation=state.intent_generation,
                closed_generation=state.closed_generation,
            )
        return state


def _load_json(name: str) -> dict:
    return json.loads((FIXTURE_ROOT / name).read_text(encoding="utf-8"))


def _execution_key(plan) -> str:
    return canonical_hash(
        {
            "target_binding_hash": plan.target_binding_hash,
            "mutation_id": plan.mutation.mutation_id,
        }
    )


def _case_create() -> BusinessCaseTypeMutation:
    return BusinessCaseTypeMutation.case_create(
        {
            "NacCaseId": "synthetic-case-01",
            "Aktenzeichen": "SYN-01",
            "Vorgangstyp": "immobilienkaufvertrag",
            "VorgangstypId": "immobilienkaufvertrag",
            "Status": "Entwurf",
            "NotarTeam": "NaC-Notar-01",
            "Vertraulichkeitsstufe": "Normal",
            "NacWorkflowVersion": "workflow-v1",
            "KgVersion": "kg-v1",
        }
    )


def _task_create() -> BusinessCaseTypeMutation:
    return BusinessCaseTypeMutation.task_create(
        {
            "NacTaskId": "synthetic-task-01",
            "NacCaseId": "synthetic-case-01",
            "BpmnStepCode": "draft-contract",
            "Status": "Offen",
            "RequiresNotaryApproval": True,
        }
    )


def _backfill() -> BusinessCaseTypeMutation:
    fixture = _load_json("s5-backfill.fixture.json")
    operation = fixture["operation"]
    return BusinessCaseTypeMutation.business_case_type_backfill(
        item_id=fixture["item_id"],
        expected_etag=operation["if_match"],
        business_case_type_id=operation["value"],
        s5_binding=S5BackfillBinding(
            manifest_hash=fixture["manifest_hash"],
            record_ref_hash=operation["record_ref_hash"],
            operation_hash=canonical_hash(operation),
            idempotency_key=operation["idempotency_key"],
        ),
    )


def _authorization_for(
    authorization: MutationAuthorization,
    mutation: BusinessCaseTypeMutation,
) -> MutationAuthorization:
    list_id = (
        "00000000-0000-4000-8000-000000000011"
        if mutation.operation.startswith("task_")
        else "00000000-0000-4000-8000-000000000010"
    )
    purpose = (
        "business_case_type_migration"
        if mutation.operation == "business_case_type_backfill"
        else "matter_workflow"
    )
    role = "BackfillOperator" if mutation.operation == "business_case_type_backfill" else "notary_clerk"
    return replace(
        authorization,
        list_id=list_id,
        actor_role=role,
        purpose=purpose,
        approved_operation=mutation.operation,
        approval_ref=f"synthetic-approval-{mutation.operation.replace('_', '-')}-01",
    )


if __name__ == "__main__":
    unittest.main()
