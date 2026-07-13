from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.test_environment import (  # noqa: E402
    ALLOWED_MATTER_ID,
    ALLOWED_PURPOSE,
    ALLOWED_WORKSPACE_ID,
    AccessDecision,
    TestEnvironmentBff,
    ValidatedClaims,
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
        "status": "in_review",
        "deadline": "2026-08-31",
        "tasks": [
            {
                "title": "Kaufvertragsentwurf prüfen",
                "status": "open",
                "sharepointItemId": "DO_NOT_EXPOSE_ITEM_ID",
            },
            {
                "title": "Beurkundung vorbereiten",
                "status": "planned",
            },
        ],
        "bpmn": {
            "modelKey": "immobilienkaufvertrag",
            "sha256": "a" * 64,
            "graphDownloadUrl": "DO_NOT_EXPOSE_DOWNLOAD_URL",
        },
        "siteId": "DO_NOT_EXPOSE_SITE_ID",
        "listId": "DO_NOT_EXPOSE_LIST_ID",
        "rawFields": {"Mandant": "DO_NOT_EXPOSE_MATTER_DATA"},
    }


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
    ) -> tuple[TestEnvironmentBff, _AccessPort, _GraphPort]:
        access = _AccessPort(decision)
        graph = _GraphPort(_projection() if projection is None else projection, graph_error)
        return (
            TestEnvironmentBff(
                expected_tenant_id="synthetic-tenant",
                access_decision_port=access,
                graph_rest_port=graph,
            ),
            access,
            graph,
        )

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
        self.assertEqual(response.body["schemaVersion"], "nac.m365-test-environment-workspace/v0.1")
        self.assertEqual(response.body["workspaceId"], ALLOWED_WORKSPACE_ID)
        self.assertEqual(response.body["matter"]["matterId"], ALLOWED_MATTER_ID)
        self.assertEqual(response.body["matter"]["businessCaseTypeId"], "immobilienkaufvertrag")
        self.assertEqual(response.body["matter"]["accessMode"], "assigned")
        self.assertEqual(response.body["matter"]["tasks"][0], {"title": "Kaufvertragsentwurf prüfen", "status": "open"})
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

    def test_denied_user_gets_generic_forbidden_without_graph_read(self) -> None:
        bff, _, graph = self._bff(decision=AccessDecision.deny())

        response = bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.body, {"detail": "access denied"})
        self.assertEqual(graph.calls, [])

    def test_workspace_matter_and_purpose_manipulation_fail_before_ports(self) -> None:
        for field, value in (
            ("workspace_id", "notary_team_02"),
            ("matter_id", "NAC-SYN-MATTER-999"),
            ("purpose", "export_all_matters"),
        ):
            with self.subTest(field=field):
                bff, access, graph = self._bff()
                request = {
                    "claims": self.claims,
                    "workspace_id": ALLOWED_WORKSPACE_ID,
                    "matter_id": ALLOWED_MATTER_ID,
                    "purpose": ALLOWED_PURPOSE,
                }
                request[field] = value

                response = bff.get_workspace(**request)

                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.body, {"detail": "resource not found"})
                self.assertEqual(access.calls, [])
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
        self.assertEqual(response.body, {"detail": "authentication required"})
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
        self.assertEqual(response.body, {"detail": "access denied"})
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
        self.assertEqual(missing.body, {"detail": "resource not found"})

        failed_bff, _, _ = self._bff(graph_error=RuntimeError("SENSITIVE GRAPH ERROR"))
        failed = failed_bff.get_workspace(
            claims=self.claims,
            workspace_id=ALLOWED_WORKSPACE_ID,
            matter_id=ALLOWED_MATTER_ID,
            purpose=ALLOWED_PURPOSE,
        )
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.body, {"detail": "service unavailable"})
        self.assertNotIn("SENSITIVE", json.dumps(failed.body))

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
        self.assertEqual(response.body, {"detail": "service unavailable"})
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
