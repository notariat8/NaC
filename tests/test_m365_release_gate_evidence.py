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
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
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
        index = evidence["artifact_index"]
        self.assertEqual(index["schema_version"], "nac.m365-release-gate-evidence-index/v0.1")
        self.assertEqual(index["artifacts"][0]["attached"], False)
        self.assertEqual(index["artifacts"][2]["id"], "mcp_smoke_suite")
        self.assertEqual(index["artifacts"][2]["attached"], True)
        self.assertEqual(len(index["artifacts"][2]["artifact_sha256"]), 64)
        self.assertFalse(index["privacy"]["storesTokensOrSecrets"])
        report = render_release_gate_evidence_markdown(evidence)
        self.assertIn("mcp-smoke-suite --mcp-suite-cleanup", report)
        self.assertNotIn("raw-secret-value", json.dumps(evidence))
        self.assertNotIn("Raw Graph", report)

    def test_blocks_when_required_runtime_artifacts_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                require_runtime_artifacts=True,
            )

        self.assertEqual(evidence["status"], "BLOCKED")
        self.assertEqual(evidence["steps"][0]["status"], "BLOCKED")
        self.assertEqual(evidence["steps"][1]["status"], "BLOCKED")

    def test_reports_complete_when_runtime_and_mcp_artifacts_are_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            runtime_smoke_artifact = tmp_path / "runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            runtime_smoke_artifact.write_text(json.dumps(_runtime_smoke_payload()), encoding="utf-8")
            runtime_metadata_artifact.write_text(json.dumps(_runtime_metadata_payload()), encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_smoke_artifact=runtime_smoke_artifact,
                runtime_metadata_artifact=runtime_metadata_artifact,
                require_runtime_artifacts=True,
            )

        self.assertEqual(evidence["status"], "PASSED")
        self.assertEqual(evidence["summary"]["evidence_completeness"], "complete_release_gate_artifacts")
        self.assertEqual(evidence["summary"]["runtime_smoke_status"], "PASSED")
        self.assertEqual(evidence["summary"]["runtime_metadata_status"], "PASSED")

    def test_fails_when_attached_runtime_artifact_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            runtime_artifact = tmp_path / "runtime-smoke.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")
            runtime_artifact.write_text("{not-json", encoding="utf-8")

            evidence = build_release_gate_evidence(
                repo_root=REPO_ROOT,
                mcp_suite_artifact=suite_artifact,
                mcp_leftover_artifact=leftover_artifact,
                runtime_smoke_artifact=runtime_artifact,
            )

        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(evidence["steps"][0]["status"], "FAILED")

    def test_cli_writes_report_and_prints_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            suite_artifact = tmp_path / "suite.redacted.json"
            leftover_artifact = tmp_path / "leftover.redacted.json"
            report_path = tmp_path / "release-gate-evidence.redacted.md"
            json_path = tmp_path / "release-gate-evidence.redacted.json"
            index_path = tmp_path / "release-gate-artifact-index.redacted.json"
            runtime_smoke_artifact = tmp_path / "missing-runtime-smoke.redacted.json"
            runtime_metadata_artifact = tmp_path / "missing-runtime-metadata.redacted.json"
            suite_artifact.write_text(json.dumps(_suite_payload()), encoding="utf-8")
            leftover_artifact.write_text(json.dumps(_leftover_payload()), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/nac.py",
                    "--repo-root",
                    str(REPO_ROOT),
                    "m365",
                    "teams-sharepoint",
                    "release-gate-evidence",
                    "--release-gate-suite-artifact",
                    str(suite_artifact),
                    "--release-gate-leftover-artifact",
                    str(leftover_artifact),
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
        self.assertEqual(index_payload["artifacts"][2]["id"], "mcp_smoke_suite")
        self.assertEqual(len(index_payload["artifacts"][2]["artifact_sha256"]), 64)


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
