from __future__ import annotations

import copy
import importlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.bpmn_asset import (  # noqa: E402
    BpmnAsset,
    CANONICAL_BPMN_MIME_TYPE,
    CANONICAL_BPMN_MODEL_KEY,
    CANONICAL_BPMN_SHA256,
    CanonicalBpmnAssetFilePort,
)
from nac_bff import test_environment as bff_contract  # noqa: E402
from nac_bff.test_environment import (  # noqa: E402
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
    DeterministicSyntheticAccessDecisionPort,
    TestEnvironmentBff,
    ValidatedClaims,
)
from nac_mvp_test_environment import (  # noqa: E402
    DEADLINE,
    MATTER_STATUS,
    SYNTHETIC_POLICY_STATE,
    TASKS,
)


class _AccessPort:
    def __init__(self, decision: AccessDecision) -> None:
        self.decision = decision
        self.calls: list[dict[str, str]] = []

    def decide(self, *, actor_id: str, tenant_id: str, workspace_id: str, matter_id: str, purpose: str) -> AccessDecision:
        self.calls.append(
            {
                "actor_id": actor_id,
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "matter_id": matter_id,
                "purpose": purpose,
            }
        )
        return self.decision


class _GraphPort:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls: list[dict[str, str]] = []

    def read_synthetic_workspace(self, *, workspace_id: str, matter_id: str) -> dict | None:
        self.calls.append({"workspace_id": workspace_id, "matter_id": matter_id})
        if self.error is not None:
            raise self.error
        return self.payload


def _projection() -> dict:
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
                "sharepointItemId": "DO_NOT_EXPOSE_ITEM_ID",
            }
            for task in TASKS
        ],
        "siteId": "DO_NOT_EXPOSE_SITE_ID",
        "listId": "DO_NOT_EXPOSE_LIST_ID",
        "rawFields": {"Mandant": "DO_NOT_EXPOSE_MATTER_DATA"},
    }


_CANONICAL_ASSET = CanonicalBpmnAssetFilePort(
    REPO_ROOT / "bpmn/immobilienkaufvertrag.bpmn"
).read_canonical_bpmn()


class _BpmnPort:
    def __init__(
        self,
        payload: BpmnAsset = _CANONICAL_ASSET,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.error = error
        self.calls = 0

    def read_canonical_bpmn(self) -> BpmnAsset:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.payload


class M365TestEnvironmentBffTests(unittest.TestCase):
    def setUp(self) -> None:
        self.claims = ValidatedClaims(
            object_id="synthetic-assigned-user",
            tenant_id="synthetic-tenant",
            subject="synthetic-subject",
        )

    def _bff(
        self,
        *,
        decision: AccessDecision = AccessDecision.assigned(),
        projection: dict | None = None,
        graph_error: Exception | None = None,
        bpmn_error: Exception | None = None,
    ) -> tuple[TestEnvironmentBff, _AccessPort, _GraphPort]:
        access = _AccessPort(decision)
        graph = _GraphPort(_projection() if projection is None else projection, graph_error)
        bpmn = _BpmnPort(error=bpmn_error)
        self.last_bpmn_port = bpmn
        return (
            TestEnvironmentBff(
                expected_tenant_id="synthetic-tenant",
                access_decision_port=access,
                graph_rest_port=graph,
                bpmn_asset_port=bpmn,
            ),
            access,
            graph,
        )

    def _policy_response(
        self,
        actor_id: str,
        *,
        policy_state: dict | None = None,
    ) -> tuple[object, _GraphPort]:
        graph = _GraphPort(_projection())
        bpmn = _BpmnPort()
        self.last_bpmn_port = bpmn
        bff = TestEnvironmentBff(
            expected_tenant_id="synthetic-tenant",
            access_decision_port=DeterministicSyntheticAccessDecisionPort(
                policy_state=SYNTHETIC_POLICY_STATE if policy_state is None else policy_state
            ),
            graph_rest_port=graph,
            bpmn_asset_port=bpmn,
        )
        response = bff.get_workspace(
            claims=ValidatedClaims(
                object_id=actor_id,
                tenant_id="synthetic-tenant",
                subject="synthetic-subject",
            ),
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        return response, graph

    def test_allowlists_are_exactly_the_single_synthetic_target(self) -> None:
        self.assertEqual(ALLOWED_WORKSPACE_ID, "notary_team_01")
        self.assertEqual(ALLOWED_MATTER_ID, "NAC-SYN-MATTER-001")
        self.assertEqual(ALLOWED_PURPOSE, "view_synthetic_matter_workspace")

    def test_assigned_user_receives_only_the_redacted_workspace_dto(self) -> None:
        bff, access, graph = self._bff()

        response = bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["schemaVersion"], "nac.m365-test-environment-workspace/v0.2")
        self.assertEqual(response.body["workspaceId"], ALLOWED_WORKSPACE_ID)
        self.assertEqual(response.body["matter"]["matterId"], ALLOWED_MATTER_ID)
        self.assertEqual(response.body["matter"]["businessCaseTypeId"], "immobilienkaufvertrag")
        self.assertEqual(response.body["matter"]["accessMode"], "assigned")
        self.assertEqual(
            response.body["matter"]["bpmn"],
            {
                "modelKey": CANONICAL_BPMN_MODEL_KEY,
                "mimeType": CANONICAL_BPMN_MIME_TYPE,
                "sha256": CANONICAL_BPMN_SHA256,
                "xml": _CANONICAL_ASSET.xml,
            },
        )
        self.assertEqual(
            response.body["matter"]["tasks"],
            [
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
        )
        serialized = json.dumps(response.body, ensure_ascii=False)
        for sentinel in (
            "DO_NOT_EXPOSE_ITEM_ID",
            "DO_NOT_EXPOSE_DOWNLOAD_URL",
            "DO_NOT_EXPOSE_SITE_ID",
            "DO_NOT_EXPOSE_LIST_ID",
            "DO_NOT_EXPOSE_MATTER_DATA",
            "synthetic-assigned-user",
            "synthetic-tenant",
            "synthetic-subject",
        ):
            self.assertNotIn(sentinel, serialized)
        self.assertEqual(len(access.calls), 1)
        self.assertEqual(access.calls[0]["actor_id"], "synthetic-assigned-user")
        self.assertEqual(graph.calls, [{"workspace_id": ALLOWED_WORKSPACE_ID, "matter_id": ALLOWED_MATTER_ID}])
        self.assertEqual(self.last_bpmn_port.calls, 1)

    def test_task_step_not_present_in_canonical_bpmn_fails_closed(self) -> None:
        projection = _projection()
        projection["tasks"][0]["stepCode"] = "Task_DoesNotExist"
        patched_tasks = [dict(task) for task in TASKS]
        patched_tasks[0]["step_code"] = "Task_DoesNotExist"
        bff, _, _ = self._bff(projection=projection)

        with patch.object(bff_contract, "TASKS", tuple(patched_tasks)):
            response = bff.get_workspace(
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

    def test_task_bpmn_kg_reference_mismatch_fails_closed(self) -> None:
        bff, _, _ = self._bff(projection=_projection())

        with patch.object(bff_contract, "BUSINESS_CASE_TYPE_ID", "other"):
            response = bff.get_workspace(
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

    def test_numeric_boolean_projection_fails_closed(self) -> None:
        projection = _projection()
        projection["tasks"][0]["requiresNotaryApproval"] = 1
        bff, _, _ = self._bff(projection=projection)

        response = bff.get_workspace(
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

    def test_canonical_policy_allows_assignment_and_valid_deputy_but_denies_unassigned(self) -> None:
        assigned, assigned_graph = self._policy_response("nac-synthetic-assigned")
        deputy, deputy_graph = self._policy_response("nac-synthetic-deputy")
        denied, denied_graph = self._policy_response("nac-synthetic-unassigned")

        self.assertEqual((assigned.status_code, assigned.body["matter"]["accessMode"]), (200, "assigned"))
        self.assertEqual((deputy.status_code, deputy.body["matter"]["accessMode"]), (200, "deputy"))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.body, {"status": 403, "error": {"code": "ACCESS_DENIED"}})
        self.assertEqual(len(assigned_graph.calls), 1)
        self.assertEqual(len(deputy_graph.calls), 1)
        self.assertEqual(denied_graph.calls, [])

    def test_deputy_policy_requires_reason_duration_audit_and_approval(self) -> None:
        invalid_states: list[tuple[str, dict]] = []
        for field, value in (
            ("reason", " "),
            ("valid_until", "2026-07-13T07:00:00Z"),
            ("approved_by", ""),
            ("approval_status", "pending"),
            ("audit_correlation_id", ""),
        ):
            state = copy.deepcopy(SYNTHETIC_POLICY_STATE)
            state["deputy_grants"][0][field] = value
            invalid_states.append((field, state))
        missing_audit = copy.deepcopy(SYNTHETIC_POLICY_STATE)
        missing_audit["audit_events"] = []
        invalid_states.append(("audit_event", missing_audit))

        for field, state in invalid_states:
            with self.subTest(field=field):
                response, graph = self._policy_response(
                    "nac-synthetic-deputy", policy_state=state
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.body, {"status": 403, "error": {"code": "ACCESS_DENIED"}})
                self.assertEqual(graph.calls, [])
                self.assertEqual(self.last_bpmn_port.calls, 0)

    def test_deputy_decision_is_visible_only_as_access_mode(self) -> None:
        bff, _, _ = self._bff(decision=AccessDecision.deputy())

        response = bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["matter"]["accessMode"], "deputy")
        self.assertEqual(self.last_bpmn_port.calls, 1)

    def test_denied_user_gets_generic_forbidden_without_graph_read(self) -> None:
        bff, _, graph = self._bff(decision=AccessDecision.deny())

        response = bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.body, {"status": 403, "error": {"code": "ACCESS_DENIED"}})
        self.assertEqual(graph.calls, [])
        self.assertEqual(self.last_bpmn_port.calls, 0)

    def test_unauthorized_and_manipulated_inputs_are_externally_indistinguishable(self) -> None:
        denied_bff, denied_access, denied_graph = self._bff(
            decision=AccessDecision.deny()
        )
        denied = denied_bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        expected_external_response = (denied.status_code, denied.body)

        self.assertEqual(expected_external_response, (403, {"status": 403, "error": {"code": "ACCESS_DENIED"}}))
        self.assertEqual(len(denied_access.calls), 1)
        self.assertEqual(denied_graph.calls, [])

        manipulations = (
            ("workspace", {"workspace_id": "notary_team_02"}),
            ("matter", {"matter_id": "NAC-SYN-MATTER-999"}),
            ("purpose", {"purpose": "export_all_matters"}),
            ("filter", {"request_filters": {"$filter": "Status eq 'Offen'"}}),
            ("malformed_filters", {"request_filters": "Status eq 'Offen'"}),
        )
        for label, overrides in manipulations:
            with self.subTest(label=label):
                bff, access, graph = self._bff()
                request = {
                    "claims": self.claims,
                    "workspace_id": ALLOWED_WORKSPACE_ID,
                    "matter_id": ALLOWED_MATTER_ID,
                    "purpose": ALLOWED_PURPOSE,
                    "request_filters": {},
                }
                request.update(overrides)

                response = bff.get_workspace(**request)

                self.assertEqual(
                    (response.status_code, response.body), expected_external_response
                )
                self.assertEqual(access.calls, [])
                self.assertEqual(graph.calls, [])
                self.assertEqual(self.last_bpmn_port.calls, 0)

    def test_fastapi_query_shape_rejects_filters_duplicates_and_missing_purpose(self) -> None:
        from nac_bff.fastapi_adapter import _parse_workspace_query

        purpose, filters = _parse_workspace_query([("purpose", ALLOWED_PURPOSE)])
        self.assertEqual((purpose, filters), (ALLOWED_PURPOSE, {}))

        invalid_shapes = (
            [],
            [("purpose", "")],
            [("purpose", "x" * 81)],
            [("purpose", ALLOWED_PURPOSE), ("purpose", ALLOWED_PURPOSE)],
            [("purpose", ALLOWED_PURPOSE), ("$filter", "Status eq 'Offen'")],
            [("$filter", "Status eq 'Offen'")],
        )
        for query_items in invalid_shapes:
            with self.subTest(query_items=query_items):
                parsed_purpose, parsed_filters = _parse_workspace_query(query_items)
                self.assertEqual(parsed_purpose, "")
                self.assertEqual(parsed_filters, {"invalid_query_shape": True})

    def test_fastapi_http_responses_do_not_leak_matter_existence(self) -> None:
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            self.skipTest("FastAPI runtime dependencies are not installed")

        from nac_bff.fastapi_adapter import create_fastapi_app

        access = _AccessPort(AccessDecision.deny())
        graph = _GraphPort(_projection())
        bff = TestEnvironmentBff(
            expected_tenant_id="synthetic-tenant",
            access_decision_port=access,
            graph_rest_port=graph,
            bpmn_asset_port=_BpmnPort(),
        )

        async def validated_claims() -> ValidatedClaims:
            return self.claims

        client = TestClient(
            create_fastapi_app(
                bff=bff,
                validated_claims_dependency=validated_claims,
            )
        )
        base_path = f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/{ALLOWED_MATTER_ID}"
        baseline = client.get(base_path, params={"purpose": ALLOWED_PURPOSE})
        expected_external_response = (baseline.status_code, baseline.json())
        self.assertEqual(expected_external_response, (403, {"status": 403, "error": {"code": "ACCESS_DENIED"}}))

        manipulated_urls = (
            f"/v1/workspaces/notary_team_02/matters/{ALLOWED_MATTER_ID}?purpose={ALLOWED_PURPOSE}",
            f"/v1/workspaces/{ALLOWED_WORKSPACE_ID}/matters/NAC-SYN-MATTER-999?purpose={ALLOWED_PURPOSE}",
            f"{base_path}?purpose=export_all_matters",
            f"{base_path}?purpose={ALLOWED_PURPOSE}&%24filter=Status%20eq%20Offen",
            f"{base_path}?purpose={ALLOWED_PURPOSE}&purpose={ALLOWED_PURPOSE}",
            base_path,
        )
        for url in manipulated_urls:
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(
                    (response.status_code, response.json()), expected_external_response
                )

        self.assertEqual(len(access.calls), 1)
        self.assertEqual(graph.calls, [])

    def test_identity_is_accepted_only_as_injected_validated_claims(self) -> None:
        bff, access, graph = self._bff()

        response = bff.get_workspace(
            claims={"oid": "browser-supplied-actor"},
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.body, {"status": 401, "error": {"code": "AUTHENTICATION_REQUIRED"}})
        self.assertEqual(access.calls, [])
        self.assertEqual(graph.calls, [])

    def test_wrong_tenant_fails_closed_before_access_decision(self) -> None:
        bff, access, graph = self._bff()
        claims = ValidatedClaims(object_id="actor", tenant_id="other-tenant", subject="subject")

        response = bff.get_workspace(
            claims=claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.body, {"status": 403, "error": {"code": "ACCESS_DENIED"}})
        self.assertEqual(access.calls, [])
        self.assertEqual(graph.calls, [])

    def test_missing_graph_item_and_graph_error_are_generic(self) -> None:
        bff, _, _ = self._bff(projection={})
        missing = bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.body, {"status": 404, "error": {"code": "RESOURCE_NOT_FOUND"}})
        self.assertEqual(self.last_bpmn_port.calls, 0)

        failed_bff, _, _ = self._bff(graph_error=RuntimeError("SENSITIVE GRAPH ERROR"))
        failed = failed_bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.body, {"status": 503, "error": {"code": "SERVICE_UNAVAILABLE"}})
        self.assertNotIn("SENSITIVE", json.dumps(failed.body))
        self.assertEqual(self.last_bpmn_port.calls, 0)

    def test_bpmn_asset_failure_is_generic_after_authorization_and_graph_read(self) -> None:
        bff, _, graph = self._bff(
            bpmn_error=RuntimeError("SENSITIVE BPMN ASSET ERROR")
        )

        response = bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(
            (response.status_code, response.body),
            (503, {"status": 503, "error": {"code": "SERVICE_UNAVAILABLE"}}),
        )
        self.assertEqual(len(graph.calls), 1)
        self.assertEqual(self.last_bpmn_port.calls, 1)
        self.assertNotIn("SENSITIVE", json.dumps(response.body))

    def test_malformed_graph_projection_fails_closed_without_raw_values(self) -> None:
        malformed = _projection()
        malformed["deadline"] = "tomorrow; DO_NOT_EXPOSE_MATTER_DATA"
        bff, _, _ = self._bff(projection=malformed)

        response = bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.body, {"status": 503, "error": {"code": "SERVICE_UNAVAILABLE"}})
        self.assertNotIn("DO_NOT_EXPOSE", json.dumps(response.body))

    def test_fastapi_adapter_module_imports_without_fastapi_installed(self) -> None:
        module = importlib.import_module("nac_bff.fastapi_adapter")
        self.assertTrue(callable(module.create_fastapi_app))

    def test_container_declares_external_adapter_dependencies_only_in_runtime_requirements(self) -> None:
        requirements = (REPO_ROOT / "deploy/runtime/onprem/nac-bff/requirements.txt").read_text(encoding="utf-8")
        dockerfile = (REPO_ROOT / "deploy/runtime/onprem/nac-bff/Dockerfile").read_text(encoding="utf-8")
        pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertIn("fastapi==", requirements)
        self.assertIn("uvicorn==", requirements)
        self.assertNotIn("fastapi", pyproject.lower())
        self.assertNotIn("microsoft-graph", requirements.lower())
        self.assertNotIn("msgraph", requirements.lower())
        self.assertIn("USER 65532:65532", dockerfile)
        self.assertIn("create_unconfigured_app", dockerfile)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
