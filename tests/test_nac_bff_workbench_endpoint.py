from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import unittest

from nac_bff.bpmn_asset import (
    BpmnAssetError,
    CANONICAL_BPMN_MODEL_KEY,
    CANONICAL_BPMN_SHA256,
    CanonicalBpmnAssetFilePort,
)
from nac_bff.synthetic_workspace_graph import GraphRequestError, GraphResponseError
from nac_bff.fastapi_adapter import create_fastapi_app, _should_emit_instance_epoch
from nac_bff.test_environment import (
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
    TestEnvironmentBff,
    ValidatedClaims,
)
from nac_bff.workbench_endpoint import (
    RecursiveRedactionVerifier,
    WorkbenchEndpoint,
)
from nac_bff.workbench_projection import workbench_projection_content_sha256
from nac_mvp_test_environment import (
    BUSINESS_CASE_TYPE_ID,
    DEADLINE,
    MATTER_STATUS,
    TASKS,
)


TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
ACTOR_ID = "actor:synthetic:001"
NOW = datetime(2026, 8, 1, 9, 1, 0, tzinfo=UTC)
ISSUED_AT = "2026-08-01T09:00:00Z"
EXPIRES_AT = "2026-08-01T09:04:00Z"


def _workspace_projection() -> dict:
    return {
        "status": MATTER_STATUS,
        "deadline": DEADLINE,
        "tasks": [
            {
                "taskId": task["task_id"],
                "title": task["title"],
                "stepCode": task["step_code"],
                "status": task["status"],
                "requiresNotaryApproval": task["requires_notary_approval"],
                "dueAt": task["due_at"],
            }
            for task in TASKS
        ],
    }


def _assigned_decision(**changes: object) -> AccessDecision:
    values = {
        "decision_id": "access:NAC-SYN-MATTER-001:1",
        "decision_version": "policy-v1",
        "subject_id": ACTOR_ID,
        "role": "notary",
        "workspace_id": ALLOWED_WORKSPACE_ID,
        "matter_id": ALLOWED_MATTER_ID,
        "purpose": ALLOWED_PURPOSE,
        "issued_at": ISSUED_AT,
        "expires_at": EXPIRES_AT,
    }
    values.update(changes)
    return AccessDecision.assigned(**values)


class _AccessPort:
    def __init__(self, decision: AccessDecision) -> None:
        self.decision = decision
        self.calls: list[dict[str, str]] = []

    def decide(self, **request: str) -> AccessDecision:
        self.calls.append(request)
        return self.decision


class _GraphPort:
    def __init__(self, projection: object = None) -> None:
        self.projection = _workspace_projection() if projection is None else projection
        self.calls: list[dict[str, str]] = []

    def read_synthetic_workspace(self, **request: str):
        self.calls.append(request)
        return self.projection


class _BpmnPort:
    def __init__(self) -> None:
        self.delegate = CanonicalBpmnAssetFilePort()
        self.calls = 0

    def read_canonical_bpmn(self):
        self.calls += 1
        return self.delegate.read_canonical_bpmn()


class WorkbenchEndpointTests(unittest.TestCase):
    def test_instance_epoch_is_scoped_to_successful_workbench_response(self) -> None:
        path = (
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/"
            f"{ALLOWED_MATTER_ID}/workbench-snapshot"
        )
        self.assertTrue(_should_emit_instance_epoch(path, 200))
        self.assertFalse(_should_emit_instance_epoch(path, 401))
        self.assertFalse(_should_emit_instance_epoch(path, 403))
        self.assertFalse(_should_emit_instance_epoch("/healthz", 200))

    def setUp(self) -> None:
        self.claims = ValidatedClaims(
            object_id=ACTOR_ID,
            tenant_id=TENANT_ID,
            subject=ACTOR_ID,
        )

    def _endpoint(
        self,
        *,
        decision: AccessDecision | None = None,
        projection: object = None,
        redaction_verifier=None,
        diagnostic_sink=None,
        clock=None,
        request_budget_factory=None,
    ) -> tuple[WorkbenchEndpoint, _AccessPort, _GraphPort, _BpmnPort]:
        access = _AccessPort(decision or _assigned_decision())
        graph = _GraphPort(projection)
        bpmn = _BpmnPort()
        endpoint = WorkbenchEndpoint(
            expected_tenant_id=TENANT_ID,
            access_decision_port=access,
            graph_rest_port=graph,
            bpmn_asset_port=bpmn,
            clock=clock or (lambda: NOW),
            redaction_verifier=redaction_verifier,
            request_budget_factory=request_budget_factory,
            unavailable_diagnostic_sink=diagnostic_sink,
        )
        return endpoint, access, graph, bpmn

    def test_assigned_snapshot_is_minimal_bound_and_exactly_serialized(self) -> None:
        endpoint, access, graph, bpmn = self._endpoint()

        response = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["schemaVersion"], "nac.workbench.snapshot/v1")
        self.assertEqual(
            response.body["scope"],
            {
                "workspaceId": ALLOWED_WORKSPACE_ID,
                "matterId": ALLOWED_MATTER_ID,
                "purpose": ALLOWED_PURPOSE,
            },
        )
        self.assertEqual(response.body["access"]["subjectId"], ACTOR_ID)
        self.assertEqual(response.body["access"]["role"], "notary")
        self.assertEqual(response.body["matter"]["currentStepId"], None)
        self.assertEqual(
            response.body["matter"]["modelReference"],
            {
                "kind": "bpmn",
                "modelKey": CANONICAL_BPMN_MODEL_KEY,
                "sha256": CANONICAL_BPMN_SHA256,
            },
        )
        self.assertEqual(response.body["attention"], [])
        self.assertEqual(response.body["decisions"], [])
        self.assertEqual(response.body["capabilities"], [])
        self.assertEqual(response.body["agents"], [])
        self.assertEqual(len(response.body["evidence"]), 1)
        self.assertEqual(
            response.body["redaction"]["contentSha256"],
            workbench_projection_content_sha256(
                {key: value for key, value in response.body.items() if key != "redaction"}
            ),
        )
        expected_bytes = json.dumps(
            response.body, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(response.body_bytes, expected_bytes)
        self.assertNotIn(b": ", response.body_bytes)
        self.assertEqual(len(access.calls), 1)
        self.assertEqual(len(graph.calls), 1)
        self.assertEqual(bpmn.calls, 1)

    def test_exact_allowlist_and_validated_claim_type_precede_every_port(self) -> None:
        endpoint, access, graph, bpmn = self._endpoint()
        requests = (
            {
                "claims": {"oid": ACTOR_ID},
                "workspace_id": ALLOWED_WORKSPACE_ID,
                "matter_id": ALLOWED_MATTER_ID,
                "purpose": ALLOWED_PURPOSE,
                "status": 401,
                "code": "AUTHENTICATION_REQUIRED",
            },
            {
                "claims": ValidatedClaims(ACTOR_ID, "other-tenant", ACTOR_ID),
                "workspace_id": ALLOWED_WORKSPACE_ID,
                "matter_id": ALLOWED_MATTER_ID,
                "purpose": ALLOWED_PURPOSE,
                "status": 403,
                "code": "ACCESS_DENIED",
            },
            {
                "claims": self.claims,
                "workspace_id": "notary_team_02",
                "matter_id": ALLOWED_MATTER_ID,
                "purpose": ALLOWED_PURPOSE,
                "status": 403,
                "code": "ACCESS_DENIED",
            },
            {
                "claims": self.claims,
                "workspace_id": ALLOWED_WORKSPACE_ID,
                "matter_id": "NAC-SYN-MATTER-999",
                "purpose": ALLOWED_PURPOSE,
                "status": 403,
                "code": "ACCESS_DENIED",
            },
            {
                "claims": self.claims,
                "workspace_id": ALLOWED_WORKSPACE_ID,
                "matter_id": ALLOWED_MATTER_ID,
                "purpose": "export_all_matters",
                "status": 403,
                "code": "ACCESS_DENIED",
            },
        )
        for request in requests:
            with self.subTest(request=request):
                status = request.pop("status")
                code = request.pop("code")
                response = endpoint.get_snapshot(**request)
                self.assertEqual(response.status_code, status)
                self.assertEqual(
                    response.body,
                    {"status": status, "error": {"code": code}},
                )
        invalid_query = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
            request_filters={"invalid_query_shape": True},
        )
        self.assertEqual(
            invalid_query.body,
            {"status": 403, "error": {"code": "ACCESS_DENIED"}},
        )
        self.assertEqual(access.calls, [])
        self.assertEqual(graph.calls, [])
        self.assertEqual(bpmn.calls, 0)

        configured_for_other_tenant = WorkbenchEndpoint(
            expected_tenant_id="other-tenant",
            access_decision_port=access,
            graph_rest_port=graph,
            bpmn_asset_port=bpmn,
            clock=lambda: NOW,
        )
        configured_claims = ValidatedClaims(
            ACTOR_ID,
            "other-tenant",
            ACTOR_ID,
        )
        configured_response = configured_for_other_tenant.get_snapshot(
            claims=configured_claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(configured_response.status_code, 403)
        self.assertEqual(access.calls, [])

    def test_deputy_requires_rich_grant_and_audit_metadata(self) -> None:
        deputy = AccessDecision.deputy(
            decision_id="access:NAC-SYN-MATTER-001:1",
            decision_version="policy-v1",
            subject_id=ACTOR_ID,
            role="deputy_clerk",
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
            issued_at=ISSUED_AT,
            expires_at=EXPIRES_AT,
            reason="Synthetische Urlaubsvertretung",
            active_approved_grant=True,
            matching_audit_event=True,
        )
        endpoint, _, _, _ = self._endpoint(decision=deputy)

        allowed = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.body["access"]["mode"], "deputy")
        self.assertEqual(allowed.body["access"]["reason"], deputy.reason)

        for field in ("active_approved_grant", "matching_audit_event"):
            denied_decision = AccessDecision.deputy(
                **{
                    **{
                        "decision_id": deputy.decision_id,
                        "decision_version": deputy.decision_version,
                        "subject_id": deputy.subject_id,
                        "role": deputy.role,
                        "workspace_id": deputy.workspace_id,
                        "matter_id": deputy.matter_id,
                        "purpose": deputy.purpose,
                        "issued_at": deputy.issued_at,
                        "expires_at": deputy.expires_at,
                        "reason": deputy.reason,
                        "active_approved_grant": True,
                        "matching_audit_event": True,
                    },
                    field: False,
                }
            )
            rejected, _, rejected_graph, rejected_bpmn = self._endpoint(
                decision=denied_decision
            )
            response = rejected.get_snapshot(
                claims=self.claims,
                workspace_id=ALLOWED_WORKSPACE_ID,
                matter_id=ALLOWED_MATTER_ID,
                purpose=ALLOWED_PURPOSE,
            )
            self.assertEqual(response.status_code, 403)
            self.assertEqual(rejected_graph.calls, [])
            self.assertEqual(rejected_bpmn.calls, 0)

        for reason in (
            "Bearer sensitive-token",
            "Vertretung fuer Max Mustermann",
        ):
            with self.subTest(reason=reason):
                malformed, _, malformed_graph, malformed_bpmn = self._endpoint(
                    decision=AccessDecision.deputy(
                        decision_id=deputy.decision_id,
                        decision_version=deputy.decision_version,
                        subject_id=deputy.subject_id,
                        role=deputy.role,
                        workspace_id=deputy.workspace_id,
                        matter_id=deputy.matter_id,
                        purpose=deputy.purpose,
                        issued_at=deputy.issued_at,
                        expires_at=deputy.expires_at,
                        reason=reason,
                        active_approved_grant=True,
                        matching_audit_event=True,
                    )
                )
                malformed_response = malformed.get_snapshot(
                    claims=self.claims,
                    workspace_id=ALLOWED_WORKSPACE_ID,
                    matter_id=ALLOWED_MATTER_ID,
                    purpose=ALLOWED_PURPOSE,
                )
                self.assertEqual(malformed_response.status_code, 403)
                self.assertEqual(malformed_graph.calls, [])
                self.assertEqual(malformed_bpmn.calls, 0)

    def test_invalid_access_decisions_are_exact_denials_before_data_ports(self) -> None:
        cases = {
            "explicit_deny": AccessDecision.deny(),
            "unsupported_role": _assigned_decision(role="administrator"),
            "mismatched_subject": _assigned_decision(subject_id="actor:other"),
            "mismatched_workspace": _assigned_decision(
                workspace_id="notary_team_02"
            ),
            "future_issuance": _assigned_decision(
                issued_at="2026-08-01T09:02:00Z"
            ),
            "expired_lease": _assigned_decision(
                expires_at="2026-08-01T09:00:30Z"
            ),
            "oversized_lease": _assigned_decision(
                expires_at="2026-08-01T09:06:00Z"
            ),
        }
        for name, decision in cases.items():
            with self.subTest(name=name):
                endpoint, _, graph, bpmn = self._endpoint(decision=decision)
                response = endpoint.get_snapshot(
                    claims=self.claims,
                    workspace_id=ALLOWED_WORKSPACE_ID,
                    matter_id=ALLOWED_MATTER_ID,
                    purpose=ALLOWED_PURPOSE,
                )
                self.assertEqual(
                    (response.status_code, response.body_bytes),
                    (
                        403,
                        b'{"status":403,"error":{"code":"ACCESS_DENIED"}}',
                    ),
                )
                self.assertEqual(graph.calls, [])
                self.assertEqual(bpmn.calls, 0)

    def test_recursive_redaction_failure_is_generic_and_emits_no_snapshot(self) -> None:
        projection = _workspace_projection()
        projection["tasks"][0]["title"] = "Bearer sensitive-token"
        endpoint, _, _, _ = self._endpoint(projection=projection)

        response = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.body,
            {"status": 503, "error": {"code": "SERVICE_UNAVAILABLE"}},
        )
        self.assertNotIn(b"sensitive-token", response.body_bytes)

    def test_503_diagnostic_classifies_only_fixed_internal_stages(self) -> None:
        cases = (
            (GraphRequestError("Bearer sensitive-token"), "GRAPH_REQUEST"),
            (GraphResponseError("Bearer sensitive-token"), "GRAPH_RESPONSE"),
            (RuntimeError("Bearer sensitive-token"), "GRAPH_UNEXPECTED"),
        )
        for failure, expected_stage in cases:
            with self.subTest(stage=expected_stage):
                stages: list[str] = []
                endpoint, _, graph, _ = self._endpoint(diagnostic_sink=stages.append)

                def fail_graph(**_: str) -> None:
                    raise failure

                graph.read_synthetic_workspace = fail_graph
                response = endpoint.get_snapshot(
                    claims=self.claims,
                    workspace_id=ALLOWED_WORKSPACE_ID,
                    matter_id=ALLOWED_MATTER_ID,
                    purpose=ALLOWED_PURPOSE,
                )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(stages, [expected_stage])
                self.assertNotIn(b"sensitive-token", response.body_bytes)

    def test_503_diagnostic_distinguishes_missing_graph_bpmn_and_projection(self) -> None:
        stages: list[str] = []
        endpoint, _, graph, bpmn = self._endpoint(diagnostic_sink=stages.append)
        graph.projection = []
        response = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(stages, ["GRAPH_RESULT_INVALID"])

        stages.clear()
        graph.projection = _workspace_projection()

        def fail_bpmn() -> None:
            raise BpmnAssetError("Bearer sensitive-token")

        bpmn.read_canonical_bpmn = fail_bpmn
        response = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(stages, ["BPMN_ASSET"])

        stages.clear()
        endpoint, _, _, _ = self._endpoint(
            diagnostic_sink=stages.append,
            redaction_verifier=lambda _: (_ for _ in ()).throw(
                ValueError("Bearer sensitive-token")
            ),
        )
        response = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(stages, ["PROJECTION"])

    def test_503_diagnostic_sink_failure_never_changes_neutral_response(self) -> None:
        def fail_sink(_: str) -> None:
            raise RuntimeError("Bearer sensitive-token")

        endpoint, _, graph, _ = self._endpoint(diagnostic_sink=fail_sink)
        graph.projection = []
        response = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(
            response.body_bytes,
            b'{"status":503,"error":{"code":"SERVICE_UNAVAILABLE"}}',
        )

    def test_503_diagnostic_classifies_budget_and_clock_without_details(self) -> None:
        def fail_with_secret() -> None:
            raise RuntimeError("Bearer sensitive-token")

        for override, expected_stage in (
            ({"request_budget_factory": fail_with_secret}, "REQUEST_BUDGET"),
            ({"clock": fail_with_secret}, "CLOCK"),
        ):
            with self.subTest(stage=expected_stage):
                stages: list[str] = []
                endpoint, _, _, _ = self._endpoint(
                    diagnostic_sink=stages.append, **override
                )
                response = endpoint.get_snapshot(
                    claims=self.claims,
                    workspace_id=ALLOWED_WORKSPACE_ID,
                    matter_id=ALLOWED_MATTER_ID,
                    purpose=ALLOWED_PURPOSE,
                )
                self.assertEqual(response.status_code, 503)
                self.assertEqual(stages, [expected_stage])
                self.assertNotIn(b"sensitive-token", response.body_bytes)

    def test_success_and_access_denial_emit_no_503_diagnostic(self) -> None:
        stages: list[str] = []
        endpoint, _, _, _ = self._endpoint(diagnostic_sink=stages.append)
        success = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        denied = endpoint.get_snapshot(
            claims=self.claims,
            workspace_id="another-workspace",
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual((success.status_code, denied.status_code), (200, 403))
        self.assertEqual(stages, [])

    def test_recursive_verifier_rejects_numbers_and_unpaired_surrogates(self) -> None:
        verifier = RecursiveRedactionVerifier(clock=lambda: NOW)
        for payload in (
            {"nested": [{"count": 1}]},
            {"nested": [{"value": "\ud800"}]},
        ):
            with self.subTest(payload=repr(payload)):
                with self.assertRaises(ValueError):
                    verifier(payload)

    def test_normative_canonicalization_fixture_matches_digest(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "workflows"
            / "fixtures"
            / "workbench-live-read-canonicalization.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

        canonical = json.dumps(
            fixture["content"],
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        self.assertEqual(canonical, fixture["canonical_utf8_json"])
        self.assertEqual(
            workbench_projection_content_sha256(fixture["content"]),
            fixture["sha256"],
        )

    def test_fastapi_route_enforces_query_cardinality_wire_and_no_store(self) -> None:
        try:
            from fastapi import HTTPException
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        endpoint, _, _, _ = self._endpoint()
        legacy_bff = TestEnvironmentBff(
            expected_tenant_id=TENANT_ID,
            access_decision_port=_AccessPort(AccessDecision.assigned()),
            graph_rest_port=_GraphPort(),
            bpmn_asset_port=_BpmnPort(),
        )

        async def validated_claims() -> ValidatedClaims:
            return self.claims

        client = TestClient(
            create_fastapi_app(
                bff=legacy_bff,
                workbench_endpoint=endpoint,
                validated_claims_dependency=validated_claims,
            )
        )
        path = (
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/"
            f"{ALLOWED_MATTER_ID}/workbench-snapshot"
        )
        response = client.get(path, params={"purpose": ALLOWED_PURPOSE})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, endpoint.get_snapshot(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        ).body_bytes)
        self.assertEqual(response.headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(response.headers["pragma"], "no-cache")
        self.assertRegex(response.headers["x-nac-instance-epoch"], r"^[0-9a-f]{32}$")

        baseline = client.get(path + "?purpose=wrong")
        self.assertEqual(
            (baseline.status_code, baseline.content),
            (
                403,
                b'{"status":403,"error":{"code":"ACCESS_DENIED"}}',
            ),
        )
        for suffix in (
            "",
            f"?purpose={ALLOWED_PURPOSE}&purpose={ALLOWED_PURPOSE}",
            f"?purpose={ALLOWED_PURPOSE}&extra=1",
        ):
            with self.subTest(suffix=suffix):
                denied = client.get(path + suffix)
                self.assertEqual(
                    (denied.status_code, denied.content),
                    (baseline.status_code, baseline.content),
                )
                self.assertEqual(denied.headers["cache-control"], "no-store")

        async def authentication_failure():
            raise HTTPException(status_code=401, detail="token detail")

        auth_client = TestClient(
            create_fastapi_app(
                bff=legacy_bff,
                workbench_endpoint=endpoint,
                validated_claims_dependency=authentication_failure,
            )
        )
        unauthorized = auth_client.get(path, params={"purpose": ALLOWED_PURPOSE})
        self.assertEqual(
            (unauthorized.status_code, unauthorized.content),
            (
                401,
                b'{"status":401,"error":{"code":"AUTHENTICATION_REQUIRED"}}',
            ),
        )
        self.assertEqual(unauthorized.headers["cache-control"], "no-store")

        class _UnavailableWorkbench:
            def get_snapshot(self, **_: object):
                raise RuntimeError("sensitive backend detail")

        stages: list[str] = []
        unavailable_client = TestClient(
            create_fastapi_app(
                bff=legacy_bff,
                workbench_endpoint=_UnavailableWorkbench(),
                validated_claims_dependency=validated_claims,
                unavailable_diagnostic_sink=stages.append,
            )
        )
        unavailable = unavailable_client.get(path, params={"purpose": ALLOWED_PURPOSE})
        self.assertEqual(
            (unavailable.status_code, unavailable.content),
            (
                503,
                b'{"status":503,"error":{"code":"SERVICE_UNAVAILABLE"}}',
            ),
        )
        self.assertEqual(unavailable.headers["cache-control"], "no-store")
        self.assertNotIn("sensitive backend detail", unavailable.text)
        self.assertEqual(stages, ["BOUNDARY_UNEXPECTED"])

        class _TimedOutWorkbench:
            def get_snapshot(self, **_: object):
                raise TimeoutError("Bearer sensitive-token")

        stages.clear()
        timeout_client = TestClient(
            create_fastapi_app(
                bff=legacy_bff,
                workbench_endpoint=_TimedOutWorkbench(),
                validated_claims_dependency=validated_claims,
                unavailable_diagnostic_sink=stages.append,
            )
        )
        timed_out = timeout_client.get(path, params={"purpose": ALLOWED_PURPOSE})
        self.assertEqual(timed_out.status_code, 503)
        self.assertEqual(stages, ["REQUEST_TIMEOUT"])
        self.assertNotIn("sensitive-token", timed_out.text)

    def test_existing_v0_2_route_body_is_unchanged(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        endpoint, _, _, _ = self._endpoint()
        legacy_bff = TestEnvironmentBff(
            expected_tenant_id=TENANT_ID,
            access_decision_port=_AccessPort(_assigned_decision()),
            graph_rest_port=_GraphPort(),
            bpmn_asset_port=_BpmnPort(),
        )

        async def validated_claims() -> ValidatedClaims:
            return self.claims

        client = TestClient(
            create_fastapi_app(
                bff=legacy_bff,
                workbench_endpoint=endpoint,
                validated_claims_dependency=validated_claims,
            )
        )
        response = client.get(
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/{ALLOWED_MATTER_ID}",
            params={"purpose": ALLOWED_PURPOSE},
        )

        expected = legacy_bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        expected_wire = json.dumps(
            expected.body,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected.body)
        self.assertEqual(response.content, expected_wire)
        self.assertEqual(response.json()["schemaVersion"], "nac.m365-test-environment-workspace/v0.2")
        self.assertEqual(response.json()["matter"]["accessMode"], "assigned")
        self.assertEqual(response.json()["matter"]["businessCaseTypeId"], BUSINESS_CASE_TYPE_ID)
        self.assertIn("xml", response.json()["matter"]["bpmn"])
        self.assertNotIn("decisionId", response.text)
        self.assertNotIn("subjectId", response.text)


if __name__ == "__main__":
    unittest.main()
