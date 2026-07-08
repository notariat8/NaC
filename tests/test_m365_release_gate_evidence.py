from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.release_gate_evidence import (  # noqa: E402
    build_release_gate_evidence,
    render_release_gate_evidence_markdown,
)


class M365ReleaseGateEvidenceTests(unittest.TestCase):
    def test_builds_redacted_evidence_from_mcp_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
                generated_at="2026-07-06T20:30:00Z",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["evidence_completeness"], "mcp_artifacts_only")
        self.assertEqual(evidence["summary"]["workspace_id"], "notary_team_01")
        self.assertFalse(evidence["summary"]["stores_tokens_or_secrets"])
        self.assertFalse(evidence["summary"]["stores_raw_graph_response"])
        self.assertFalse(evidence["summary"]["reads_sharepoint_file_content"])
        self.assertEqual(evidence["steps"][0]["status"], "NOT_ATTACHED")
        self.assertEqual(evidence["steps"][1]["status"], "NOT_ATTACHED")
        index = evidence["artifact_index"]
        self.assertEqual(index["schema_version"], "nac.m365-release-gate-evidence-index/v0.1")
        self.assertEqual(index["artifacts"][0]["attached"], False)
        self.assertEqual(index["artifacts"][1]["id"], "runtime_env_bootstrap")
        self.assertEqual(index["artifacts"][1]["attached"], False)
        self.assertEqual(index["artifacts"][4]["id"], "mcp_inventory_smoke")
        self.assertEqual(index["artifacts"][4]["attached"], False)
        self.assertEqual(index["artifacts"][5]["id"], "matter_access_delegation_smoke")
        self.assertEqual(index["artifacts"][5]["attached"], False)
        self.assertEqual(index["artifacts"][6]["id"], "matter_access_apply_readiness")
        self.assertEqual(index["artifacts"][6]["attached"], False)
        self.assertEqual(index["artifacts"][7]["id"], "matter_access_apply_request_plan")
        self.assertEqual(index["artifacts"][7]["attached"], False)
        self.assertEqual(index["artifacts"][8]["id"], "mcp_smoke_suite")
        self.assertEqual(index["artifacts"][8]["attached"], True)
        self.assertEqual(len(index["artifacts"][8]["artifact_sha256"]), 64)
        self.assertFalse(index["privacy"]["storesTokensOrSecrets"])
        report = render_release_gate_evidence_markdown(evidence)
        self.assertIn("mcp-inventory-smoke", report)
        self.assertIn("mcp-smoke-suite --mcp-suite-cleanup", report)
        self.assertNotIn("raw-secret-value", json.dumps(evidence))
        self.assertNotIn("Raw Graph", report)

    def test_blocks_when_required_runtime_artifacts_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                require_runtime_artifacts=True,
            )

        self.assertEqual(evidence["status"], "BLOCKED")
        self.assertEqual(evidence["steps"][0]["status"], "BLOCKED")
        self.assertEqual(evidence["steps"][2]["status"], "BLOCKED")
        self.assertEqual(evidence["steps"][3]["status"], "BLOCKED")

    def test_reports_complete_when_runtime_and_mcp_artifacts_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "runtime-certificate-expiry-monitor.redacted.json"
            runtime_smoke_artifact = tmp_path / "runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            runtime_certificate_expiry_artifact.write_text(
                json.dumps(_runtime_certificate_expiry_payload()),
                encoding="utf-8",
            )
            runtime_smoke_artifact.write_text(json.dumps(_runtime_smoke_payload()), encoding="utf-8")
            runtime_metadata_artifact.write_text(json.dumps(_runtime_metadata_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                require_runtime_artifacts=True,
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["evidence_completeness"], "complete_release_gate_artifacts")
        self.assertEqual(evidence["summary"]["runtime_certificate_expiry_status"], "PASSED")
        self.assertEqual(evidence["summary"]["runtime_env_bootstrap_status"], "NOT_ATTACHED")
        self.assertEqual(evidence["summary"]["runtime_smoke_status"], "PASSED")
        self.assertEqual(evidence["summary"]["runtime_metadata_status"], "PASSED")
        self.assertEqual(evidence["summary"]["mcp_inventory_smoke_status"], "NOT_ATTACHED")
        self.assertEqual(evidence["summary"]["matter_access_delegation_smoke_status"], "NOT_ATTACHED")
        self.assertEqual(evidence["summary"]["matter_access_apply_readiness_status"], "NOT_ATTACHED")
        self.assertEqual(evidence["summary"]["matter_access_apply_request_plan_status"], "NOT_ATTACHED")

    def test_attaches_optional_runtime_env_bootstrap_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            runtime_env_bootstrap_artifact.write_text(
                json.dumps(_runtime_env_bootstrap_payload()),
                encoding="utf-8",
            )

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["runtime_env_bootstrap_status"], "PASSED")
        bootstrap_step = evidence["steps"][1]
        self.assertEqual(bootstrap_step["id"], "runtime_env_bootstrap")
        self.assertEqual(bootstrap_step["summary"]["env_overlay_variable_count"], 4)
        self.assertEqual(
            bootstrap_step["summary"]["runtime_authentication_mode"],
            "client_credentials_with_certificate",
        )
        self.assertFalse(bootstrap_step["summary"]["tenant_id_emitted"])
        self.assertFalse(bootstrap_step["summary"]["client_id_emitted"])
        self.assertFalse(bootstrap_step["summary"]["certificate_thumbprint_emitted"])
        self.assertFalse(bootstrap_step["summary"]["credential_files_read"])
        self.assertFalse(bootstrap_step["summary"]["secret_env_values_read"])
        self.assertFalse(bootstrap_step["summary"]["executes_graph_requests"])
        self.assertTrue(bootstrap_step["summary"]["owner_gate_required_for_live_use"])
        self.assertTrue(evidence["artifact_index"]["artifacts"][1]["attached"])
        self.assertEqual(len(evidence["artifact_index"]["artifacts"][1]["artifact_sha256"]), 64)
        self.assertNotIn("tenant-guid", json.dumps(evidence))
        self.assertNotIn("runtime-client-guid", json.dumps(evidence))
        self.assertNotIn("certificate-thumbprint", json.dumps(evidence))

    def test_attaches_optional_inventory_smoke_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "mcp-inventory-smoke.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            inventory_artifact.write_text(json.dumps(_inventory_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["mcp_inventory_smoke_status"], "PASSED")
        inventory_step = evidence["steps"][4]
        self.assertEqual(inventory_step["id"], "mcp_inventory_smoke")
        self.assertEqual(inventory_step["summary"]["interface_count"], 10)
        self.assertFalse(inventory_step["summary"]["graph_requests_executed"])
        self.assertTrue(evidence["artifact_index"]["artifacts"][4]["attached"])
        self.assertEqual(len(evidence["artifact_index"]["artifacts"][4]["artifact_sha256"]), 64)
        self.assertNotIn("bnotk-html-body", json.dumps(evidence))

    def test_attaches_optional_matter_access_smoke_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "matter-access-delegation-smoke.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            matter_access_artifact.write_text(json.dumps(_matter_access_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["matter_access_delegation_smoke_status"], "PASSED")
        matter_step = evidence["steps"][5]
        self.assertEqual(matter_step["id"], "matter_access_delegation_smoke")
        self.assertEqual(matter_step["summary"]["workspace_operation_count"], 6)
        self.assertEqual(matter_step["summary"]["owner_gated_workspace_operations"], 3)
        self.assertFalse(matter_step["summary"]["executes_graph_requests"])
        self.assertTrue(evidence["artifact_index"]["artifacts"][5]["attached"])
        self.assertEqual(len(evidence["artifact_index"]["artifacts"][5]["artifact_sha256"]), 64)
        self.assertNotIn("/sites/{site-id}/", json.dumps(evidence))

    def test_attaches_optional_matter_access_apply_readiness_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "matter-access-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            apply_readiness_artifact.write_text(json.dumps(_matter_access_apply_readiness_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["matter_access_apply_readiness_status"], "PASSED")
        readiness_step = evidence["steps"][6]
        self.assertEqual(readiness_step["id"], "matter_access_apply_readiness")
        self.assertEqual(readiness_step["summary"]["future_apply_mode"], "owner_gated_graph_rest_item_writes")
        self.assertEqual(readiness_step["summary"]["planned_apply_operation_count"], 2)
        self.assertTrue(readiness_step["summary"]["grant_request_ready"])
        self.assertTrue(readiness_step["summary"]["audit_append_ready"])
        self.assertFalse(readiness_step["summary"]["executes_graph_requests"])
        self.assertTrue(evidence["artifact_index"]["artifacts"][6]["attached"])
        self.assertEqual(len(evidence["artifact_index"]["artifacts"][6]["artifact_sha256"]), 64)
        self.assertNotIn("/sites/{site-id}/", json.dumps(evidence))

    def test_attaches_optional_matter_access_apply_request_plan_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "matter-access-apply-request-plan.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            apply_request_artifact.write_text(json.dumps(_matter_access_apply_request_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["matter_access_apply_request_plan_status"], "PASSED")
        request_step = evidence["steps"][7]
        self.assertEqual(request_step["id"], "matter_access_apply_request_plan")
        self.assertEqual(request_step["summary"]["future_apply_mode"], "owner_gated_graph_rest_item_writes")
        self.assertEqual(request_step["summary"]["planned_write_count"], 2)
        self.assertEqual(request_step["summary"]["planned_tools"], ["grant_request", "audit_append"])
        self.assertFalse(request_step["summary"]["executes_graph_requests"])
        self.assertTrue(evidence["artifact_index"]["artifacts"][7]["attached"])
        self.assertEqual(len(evidence["artifact_index"]["artifacts"][7]["artifact_sha256"]), 64)
        self.assertNotIn("grant-raw", json.dumps(evidence))

    def test_attaches_optional_matter_access_apply_smoke_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            apply_smoke_artifact = tmp_path / "matter-access-apply-smoke.redacted.json"
            missing_artifact = tmp_path / "missing.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            apply_smoke_artifact.write_text(json.dumps(_matter_access_apply_smoke_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=missing_artifact,
                matter_access_artifact=missing_artifact,
                matter_access_apply_readiness_artifact=missing_artifact,
                matter_access_apply_request_artifact=missing_artifact,
                matter_access_apply_smoke_artifact=apply_smoke_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=missing_artifact,
                runtime_certificate_expiry_artifact=missing_artifact,
                runtime_smoke_artifact=missing_artifact,
                runtime_metadata_artifact=missing_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["matter_access_apply_smoke_status"], "PASSED")
        smoke_step = evidence["steps"][10]
        self.assertEqual(smoke_step["id"], "matter_access_apply_smoke")
        self.assertEqual(smoke_step["summary"]["write_tools"], ["grant_request", "audit_append"])
        self.assertTrue(smoke_step["summary"]["executed_graph_requests"])
        self.assertTrue(smoke_step["summary"]["executed_graph_writes"])
        self.assertTrue(smoke_step["summary"]["cleanup_requested"])
        self.assertEqual(smoke_step["summary"]["grant_cleanup_read_after_value_count"], 0)
        self.assertTrue(evidence["artifact_index"]["artifacts"][10]["attached"])
        self.assertEqual(len(evidence["artifact_index"]["artifacts"][10]["artifact_sha256"]), 64)
        self.assertNotIn("NAC-SMOKE-GRANT-20260708T000000Z", json.dumps(evidence))

    def test_does_not_auto_attach_matter_access_apply_smoke_default_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            missing_artifact = tmp_path / "missing.redacted.json"
            default_apply_smoke_artifact = (
                tmp_path / "out/m365/teams-sharepoint/matter-access-apply-smoke.redacted.json"
            )
            default_apply_smoke_artifact.parent.mkdir(parents=True, exist_ok=True)
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            mismatched_payload = _matter_access_apply_smoke_payload()
            mismatched_payload["summary"]["correlation_id"] = "live-correlation-from-previous-run"
            default_apply_smoke_artifact.write_text(json.dumps(mismatched_payload), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=tmp_path,
                mcp_inventory_artifact=missing_artifact,
                matter_access_artifact=missing_artifact,
                matter_access_apply_readiness_artifact=missing_artifact,
                matter_access_apply_request_artifact=missing_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=missing_artifact,
                runtime_certificate_expiry_artifact=missing_artifact,
                runtime_smoke_artifact=missing_artifact,
                runtime_metadata_artifact=missing_artifact,
                expected_workspace_id="notary_team_01",
                expected_correlation_id="corr-1",
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["matter_access_apply_smoke_status"], "NOT_ATTACHED")
        smoke_step = evidence["steps"][10]
        self.assertEqual(smoke_step["artifact_path"], str(default_apply_smoke_artifact))
        self.assertEqual(smoke_step["status"], "NOT_ATTACHED")
        self.assertFalse(evidence["artifact_index"]["artifacts"][10]["attached"])
        self.assertNotIn("live-correlation-from-previous-run", json.dumps(evidence))

    def test_fails_when_attached_runtime_artifact_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "missing-inventory.redacted.json"
            matter_access_artifact = tmp_path / "missing-matter-access.redacted.json"
            apply_readiness_artifact = tmp_path / "missing-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "missing-apply-request.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            runtime_artifact = tmp_path / "runtime-smoke.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            runtime_artifact.write_text("{not-json", encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_inventory_artifact=inventory_artifact,
                matter_access_artifact=matter_access_artifact,
                matter_access_apply_readiness_artifact=apply_readiness_artifact,
                matter_access_apply_request_artifact=apply_request_artifact,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_env_bootstrap_artifact=runtime_env_bootstrap_artifact,
                runtime_certificate_expiry_artifact=runtime_certificate_expiry_artifact,
                runtime_smoke_artifact=runtime_artifact,
            )

        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(evidence["steps"][2]["status"], "FAILED")

    def test_cli_writes_report_and_prints_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            inventory_artifact = tmp_path / "mcp-inventory-smoke.redacted.json"
            matter_access_artifact = tmp_path / "matter-access-delegation-smoke.redacted.json"
            apply_readiness_artifact = tmp_path / "matter-access-apply-readiness.redacted.json"
            apply_request_artifact = tmp_path / "matter-access-apply-request-plan.redacted.json"
            runtime_env_bootstrap_artifact = tmp_path / "missing-runtime-env-bootstrap.redacted.json"
            runtime_certificate_expiry_artifact = tmp_path / "missing-runtime-certificate-expiry.redacted.json"
            report_path = tmp_path / "release-gate-evidence.redacted.md"
            json_path = tmp_path / "release-gate-evidence.redacted.json"
            index_path = tmp_path / "release-gate-artifact-index.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            inventory_artifact.write_text(json.dumps(_inventory_payload()), encoding="utf-8")
            matter_access_artifact.write_text(json.dumps(_matter_access_payload()), encoding="utf-8")
            apply_readiness_artifact.write_text(json.dumps(_matter_access_apply_readiness_payload()), encoding="utf-8")
            apply_request_artifact.write_text(json.dumps(_matter_access_apply_request_payload()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/nac.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "release-gate-evidence",
                    "--release-gate-inventory-artifact",
                    str(inventory_artifact),
                    "--release-gate-matter-access-artifact",
                    str(matter_access_artifact),
                    "--release-gate-matter-access-apply-readiness-artifact",
                    str(apply_readiness_artifact),
                    "--release-gate-matter-access-apply-request-artifact",
                    str(apply_request_artifact),
                    "--release-gate-suite-artifact",
                    str(suite_artifact),
                    "--release-gate-leftover-artifact",
                    str(leftover_artifact),
                    "--release-gate-runtime-certificate-expiry-artifact",
                    str(runtime_certificate_expiry_artifact),
                    "--release-gate-runtime-env-bootstrap-artifact",
                    str(runtime_env_bootstrap_artifact),
                    "--release-gate-runtime-smoke-artifact",
                    str(runtime_smoke_artifact),
                    "--release-gate-runtime-metadata-artifact",
                    str(runtime_metadata_artifact),
                    "--release-gate-evidence-output",
                    str(report_path),
                    "--release-gate-evidence-json-output",
                    str(json_path),
                    "--release-gate-artifact-index-output",
                    str(index_path),
                    "--mcp-smoke-workspace-id",
                    "notary_team_01",
                    "--mcp-smoke-correlation-id",
                    "corr-1",
                    "--format",
                    "json",
                ],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=False,
                timeout=5,
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "PASSED")
            self.assertEqual(payload["summary"]["report_path"], str(report_path))
            self.assertEqual(payload["summary"]["json_path"], str(json_path))
            self.assertEqual(payload["summary"]["artifact_index_path"], str(index_path))
            self.assertTrue(report_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(index_path.exists())
            report = report_path.read_text(encoding="utf-8")
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))

        self.assertIn("M365 Runtime Release Gate Evidence", report)
        self.assertIn("Graph requests executed by exporter: `false`", report)
        self.assertEqual(json_payload["artifact_index"]["schema_version"], "nac.m365-release-gate-evidence-index/v0.1")
        self.assertEqual(index_payload["status"], "PASSED")
        self.assertEqual(index_payload["json_path"], str(json_path))
        self.assertEqual(index_payload["artifacts"][4]["id"], "mcp_inventory_smoke")
        self.assertEqual(index_payload["artifacts"][5]["id"], "matter_access_delegation_smoke")
        self.assertEqual(index_payload["artifacts"][6]["id"], "matter_access_apply_readiness")
        self.assertEqual(index_payload["artifacts"][7]["id"], "matter_access_apply_request_plan")
        self.assertEqual(index_payload["artifacts"][8]["id"], "mcp_smoke_suite")
        self.assertEqual(len(index_payload["artifacts"][8]["artifact_sha256"]), 64)


def _suite_payload() -> dict:
    return {
        "status": "PASSED",
        "generated_at": "2026-07-06T20:09:31Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "case_id_sha256": "sha256-only",
            "correlation_id": "corr-1",
            "positive_write_read_status": "PASSED",
            "write_status": "PASSED",
            "read_status": "PASSED",
            "read_value_count": 1,
            "cleanup_requested": True,
            "cleanup_status": "PASSED",
            "cleanup_read_after_value_count": 0,
            "graph_rest_only": True,
            "raw_case_id_stored": False,
            "raw_write_payload_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "positiveWriteReadShape": {
            "writeRequest": {
                "payloadFieldNames": ["NacCaseId", "Status"],
                "raw": "raw-secret-value",
            }
        },
    }


def _leftover_payload() -> dict:
    return {
        "status": "PASSED",
        "generated_at": "2026-07-06T20:09:43Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "correlation_id": "corr-1",
            "cleanup_target": "synthetic_mcp_smoke_leftovers",
            "read_before_value_count": 0,
            "delete_requested": False,
            "deleted_value_count": 0,
            "read_after_value_count": 0,
            "graph_rest_only": True,
            "raw_case_id_stored": False,
            "raw_item_id_stored": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
    }


def _inventory_payload() -> dict:
    return {
        "status": "PASSED",
        "generated_at": "2026-07-07T10:33:51Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "correlation_id": "corr-1",
            "tool_call_count": 4,
            "inventory_tool_count": 2,
            "interface_count": 10,
            "metadata_boundary_status": "allowed_metadata_only",
            "owner_gated_boundary_status": "owner_gate_required",
            "closed_gate_blocks": True,
            "graph_requests_executed": False,
            "external_bnotk_calls_executed": False,
            "raw_source_content_stored": False,
        },
        "checks": [
            {
                "tool": "notarial_interface_inventory_list",
                "status": "PASSED",
                "message": "inventory list returned metadata-only rows",
                "interfaceCount": 10,
                "executesGraphRequests": False,
                "runtimeMode": "metadata_inventory_only",
            }
        ],
        "privacy": {
            "metadataOnly": True,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMessagePayloads": False,
            "executesGraphRequests": False,
            "callsExternalBnotkSystems": False,
        },
        "redactionFixture": "bnotk-html-body",
        "errors": [],
    }


def _matter_access_payload() -> dict:
    return {
        "schema_version": "nac.m365-matter-access-delegation-smoke/v0.1",
        "status": "PASSED",
        "generated_at": "2026-07-07T10:45:00Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "correlation_id": "corr-1",
            "contract_id": "m365.matter_access_delegation",
            "workspace_count": 2,
            "operation_count": 12,
            "workspace_operation_count": 6,
            "list_count": 3,
            "mcp_tool_contract_count": 4,
            "owner_gated_operations": 6,
            "owner_gated_workspace_operations": 3,
            "planned_action_count": 6,
            "graph_rest_only": True,
            "legacy_sharepoint_api_allowed": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "reads_sharepoint_file_content": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_payloads": False,
            "owner_gate_required_before_future_apply": True,
        },
        "operation_summary": {
            "workspace_actions": [
                "append_access_audit_event",
                "read_active_deputy_grants",
                "read_delegation_audit_events",
                "read_primary_matter_assignment",
                "revoke_deputy_grant",
                "write_deputy_grant_request",
            ],
        },
        "checks": [{"id": "contract_valid", "status": "PASSED", "executesGraphRequests": False}],
        "privacy": {
            "metadataOnly": True,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesMessagePayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
        },
        "errors": [],
    }


def _matter_access_apply_readiness_payload() -> dict:
    return {
        "schema_version": "nac.m365-matter-access-apply-readiness/v0.1",
        "status": "PASSED",
        "generated_at": "2026-07-07T11:00:00Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "correlation_id": "corr-1",
            "contract_id": "m365.matter_access_delegation",
            "future_apply_mode": "owner_gated_graph_rest_item_writes",
            "workspace_operation_count": 6,
            "planned_apply_operation_count": 2,
            "grant_request_ready": True,
            "audit_append_ready": True,
            "required_write_approval": True,
            "owner_gate_required": True,
            "role_case_purpose_gate_required": True,
            "reason_required": True,
            "valid_from_required": True,
            "valid_until_required": True,
            "valid_until_after_valid_from_required": True,
            "approver_required": True,
            "audit_correlation_required": True,
            "automation_may_approve_grant": False,
            "graph_rest_only": True,
            "legacy_sharepoint_api_allowed": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "reads_sharepoint_file_content": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_payloads": False,
        },
        "readiness_boundary": {
            "planned_mcp_tools": ["grant_request", "audit_append"],
            "planned_apply_lists": ["Vertretungsfreigaben", "AuditJournalLite"],
        },
        "checks": [{"id": "mcp_apply_tools_ready", "status": "PASSED", "executesGraphRequests": False}],
        "privacy": {
            "metadataOnly": True,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesMessagePayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
            "sharePointItemPermissionMutationAllowed": False,
        },
        "errors": [],
    }


def _matter_access_apply_request_payload() -> dict:
    return {
        "schema_version": "nac.m365-matter-access-apply-request-plan/v0.1",
        "status": "PASSED",
        "generated_at": "2026-07-07T11:05:00Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "correlation_id": "corr-1",
            "future_apply_mode": "owner_gated_graph_rest_item_writes",
            "planned_write_count": 2,
            "planned_tools": ["grant_request", "audit_append"],
            "planned_lists": ["Vertretungsfreigaben", "AuditJournalLite"],
            "required_write_approval": True,
            "owner_gate_required": True,
            "role_case_purpose_gate_required": True,
            "graph_rest_only": True,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_payloads": False,
            "reads_sharepoint_file_content": False,
        },
        "request_plans": [
            {
                "tool": "grant_request",
                "method": "POST",
                "list_name": "Vertretungsfreigaben",
                "path_sha256": "a" * 64,
                "path_template": "/sites/{site-id}/lists/{list-id}/items",
                "payload_field_names": ["GrantId", "NacCaseId", "Reason"],
                "payload_value_hashes": {
                    "GrantId": "b" * 64,
                    "NacCaseId": "c" * 64,
                    "Reason": "d" * 64,
                },
                "reads_items": False,
                "reads_files": False,
                "writes_items": True,
                "owner_gate_required": True,
                "role_case_gate_required": True,
                "graph_rest_only": True,
                "executes_graph_requests_now": False,
                "stores_raw_graph_path": False,
                "stores_raw_graph_response": False,
            },
            {
                "tool": "audit_append",
                "method": "POST",
                "list_name": "AuditJournalLite",
                "path_sha256": "e" * 64,
                "path_template": "/sites/{site-id}/lists/{list-id}/items",
                "payload_field_names": ["EventId", "NacCaseId", "ObjectId"],
                "payload_value_hashes": {
                    "EventId": "f" * 64,
                    "NacCaseId": "c" * 64,
                    "ObjectId": "b" * 64,
                },
                "reads_items": False,
                "reads_files": False,
                "writes_items": True,
                "owner_gate_required": True,
                "role_case_gate_required": True,
                "graph_rest_only": True,
                "executes_graph_requests_now": False,
                "stores_raw_graph_path": False,
                "stores_raw_graph_response": False,
            },
        ],
        "checks": [{"id": "privacy", "status": "PASSED", "executesGraphRequests": False}],
        "privacy": {
            "metadataOnly": True,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesMessagePayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
            "sharePointItemPermissionMutationAllowed": False,
        },
        "errors": [],
    }


def _matter_access_apply_smoke_payload() -> dict:
    return {
        "schema_version": "nac.m365-matter-access-apply-smoke/v0.1",
        "status": "PASSED",
        "generated_at": "2026-07-08T11:05:00Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "correlation_id": "corr-1",
            "grant_id_sha256": "a" * 64,
            "case_id_sha256": "b" * 64,
            "event_id_sha256": "c" * 64,
            "from_user_sha256": "d" * 64,
            "to_user_sha256": "e" * 64,
            "approved_by_sha256": "f" * 64,
            "reason_sha256": "1" * 64,
            "valid_from": "2026-07-08T11:05:00Z",
            "valid_until": "2026-07-09T11:05:00Z",
            "granted_role": "SachbearbeitungVertretung",
            "grant_status": "Aktiv",
            "write_tools": ["grant_request", "audit_append"],
            "write_lists": ["Vertretungsfreigaben", "AuditJournalLite"],
            "planned_write_count": 2,
            "executed_graph_requests": True,
            "executed_graph_writes": True,
            "sharepoint_item_writes_executed": True,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "grant_read_value_count": 1,
            "audit_read_value_count": 1,
            "cleanup_requested": True,
            "grant_cleanup_read_after_value_count": 0,
            "audit_cleanup_read_after_value_count": 0,
            "graph_rest_only": True,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "raw_write_payload_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "writeRequestShapes": [],
        "writeResponseShape": {"storesRawGraphResponse": False},
        "readBackShape": {"storesRawGraphPath": False, "storesRawGraphResponse": False},
        "cleanupShape": {
            "requested": True,
            "target": "synthetic_matter_access_apply_smoke_items",
            "grantIdPrefixRequired": "NAC-SMOKE-GRANT-",
            "caseIdPrefixRequired": "NAC-SMOKE-MATTER-",
            "grantDeleteStatus": "PASSED",
            "auditDeleteStatus": "PASSED",
            "grantReadAfterValueCount": 0,
            "auditReadAfterValueCount": 0,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
        },
        "checks": [{"id": "cleanup", "status": "PASSED"}],
        "privacy": {
            "metadataOnly": False,
            "storesSourceFullText": False,
            "storesRawXsd": False,
            "storesCredentials": False,
            "storesTokensOrSecrets": False,
            "storesMatterData": False,
            "storesMatterPayloads": False,
            "storesRawWritePayload": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "executesGraphRequests": True,
            "executesGraphWrites": True,
            "tenantWritesExecuted": False,
            "teamMembershipMutationAllowed": False,
            "sharePointItemPermissionMutationAllowed": False,
        },
    }


def _runtime_env_bootstrap_payload() -> dict:
    return {
        "schema_version": "nac.m365-runtime-env-bootstrap/v0.1",
        "status": "PASSED",
        "generated_at": "2026-07-07T05:30:00Z",
        "summary": {
            "runtime_state_attached": True,
            "preferred_authentication_mode": "client_credentials_with_certificate",
            "runtime_authentication_mode": "client_credentials_with_certificate",
            "explicit_runtime_credential_mode": None,
            "env_overlay_variable_count": 4,
            "env_overlay_variable_names": [
                "M365_RUNTIME_CLIENT_CERTIFICATE_PATH",
                "M365_RUNTIME_CLIENT_ID",
                "M365_RUNTIME_CLIENT_KEY_PATH",
                "M365_TENANT_ID",
            ],
            "required_environment_variables": [
                "M365_TENANT_ID",
                "M365_RUNTIME_CLIENT_ID",
                "M365_RUNTIME_CLIENT_CERTIFICATE_PATH",
                "M365_RUNTIME_CLIENT_KEY_PATH",
            ],
            "secret_environment_variables_supported_but_not_read": [
                "M365_RUNTIME_GRAPH_ACCESS_TOKEN",
                "M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE",
                "M365_RUNTIME_CLIENT_SECRET",
                "M365_RUNTIME_CLIENT_KEY_PASSWORD",
            ],
            "tenant_id_resolved_from_state": True,
            "client_id_resolved_from_state": True,
            "tenant_id_emitted": False,
            "client_id_emitted": False,
            "certificate_thumbprint_emitted": False,
            "certificate_files_required": True,
            "certificate_path_supplied": True,
            "private_key_path_supplied": True,
            "certificate_file_exists": True,
            "private_key_file_exists": True,
            "credential_files_read": False,
            "secret_env_values_read": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "stores_tokens_or_secrets": False,
            "owner_gate_required_for_live_use": True,
        },
        "redactionFixture": "tenant-guid runtime-client-guid certificate-thumbprint",
        "checks": [],
        "errors": [],
    }


def _runtime_smoke_payload() -> dict:
    return {
        "status": "PASSED",
        "generated_at": "2026-07-07T04:30:00Z",
        "summary": {
            "workspaces": 2,
            "sites_read": 2,
            "missing_lists": 0,
            "graph_rest_only": True,
            "raw_site_id_stored": False,
            "raw_site_url_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
            "list_items_read": 0,
        },
    }


def _runtime_certificate_expiry_payload() -> dict:
    return {
        "status": "PASSED",
        "schema_version": "nac.m365-runtime-certificate-expiry-monitor/v0.1",
        "summary": {
            "certificate_expires_at_utc": "2027-07-07T07:22:21Z",
            "certificate_days_until_expiry": 365,
            "certificate_expiry_level": "OK",
            "certificate_expiry_warning_days": 90,
            "certificate_expiry_critical_days": 30,
            "certificate_rotation_required": False,
            "certificate_thumbprint_emitted": False,
            "runtime_metadata_thumbprint_matches_smoke": True,
            "graph_rest_only": True,
            "raw_site_id_stored": False,
            "raw_site_url_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
            "credential_files_read": False,
            "executes_graph_requests": False,
        },
    }


def _runtime_metadata_payload() -> dict:
    return {
        "status": "PASSED",
        "generated_at": "2026-07-07T04:30:00Z",
        "summary": {
            "workspaces": 2,
            "sites_read": 2,
            "expected_lists": 12,
            "expected_document_libraries": 4,
            "missing_lists": 0,
            "missing_document_libraries": 0,
            "list_items_read": 0,
            "graph_rest_only": True,
            "raw_site_id_stored": False,
            "raw_site_url_stored": False,
            "raw_list_id_stored": False,
            "raw_drive_id_stored": False,
            "raw_graph_response_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
    }


if __name__ == "__main__":
    unittest.main()
