from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli
from nac_m365_graph.matter_access_apply_live_smoke_retention import (
    build_matter_access_apply_live_smoke_retention_index,
    build_matter_access_apply_live_smoke_retention_readiness,
    format_matter_access_apply_live_smoke_retention_index,
    format_matter_access_apply_live_smoke_retention_readiness,
    retain_matter_access_apply_live_smoke_artifact,
    validate_matter_access_apply_live_smoke_redaction_shape,
)
from scripts import validate_m365_matter_access_apply_live_smoke_retention as validator


class M365MatterAccessApplyLiveSmokeRetentionTests(unittest.TestCase):
    def test_retains_redacted_live_smoke_and_updates_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "matter-access-apply-smoke.redacted.json"
            artifact.write_text(json.dumps(_apply_smoke_payload("corr-1")), encoding="utf-8")
            retention_root = tmp_path / "retention"

            payload = retain_matter_access_apply_live_smoke_artifact(
                artifact,
                retention_root=retention_root,
                now_utc="2026-07-08T15:00:00Z",
            )

            self.assertEqual(payload["status"], "PASSED")
            self.assertEqual(payload["summary"]["workspace_id"], "notary_team_01")
            self.assertEqual(payload["summary"]["correlation_id"], "corr-1")
            self.assertFalse(payload["summary"]["retention_executes_graph_requests"])
            self.assertFalse(payload["summary"]["retention_tenant_writes_executed"])
            self.assertTrue(Path(payload["summary"]["retained_artifact_path"]).is_file())
            self.assertTrue(Path(payload["summary"]["retention_json_path"]).is_file())
            self.assertTrue(Path(payload["summary"]["retention_index_json_path"]).is_file())
            self.assertEqual(payload["summary"]["redaction_shape_status"], "PASSED")
            self.assertEqual(payload["summary"]["redaction_shape_violation_count"], 0)
            self.assertGreater(payload["summary"]["redaction_shape_checked_node_count"], 0)
            self.assertEqual(payload["redaction_shape"]["status"], "PASSED")

            index = build_matter_access_apply_live_smoke_retention_index(retention_root=retention_root)
            self.assertEqual(index["status"], "PASSED")
            self.assertEqual(index["summary"]["run_count"], 1)
            self.assertEqual(index["summary"]["redaction_shape_status_counts"]["PASSED"], 1)
            self.assertEqual(index["summary"]["redaction_shape_legacy_missing_count"], 0)
            self.assertEqual(index["live_smokes"][0]["correlation_id"], "corr-1")
            self.assertEqual(index["live_smokes"][0]["status"], "PASSED")
            self.assertEqual(index["live_smokes"][0]["redaction_shape_status"], "PASSED")
            self.assertTrue(index["live_smokes"][0]["redaction_shape_evidence_present"])

    def test_index_filters_by_correlation_workspace_status_and_query(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            retention_root = tmp_path / "retention"
            for correlation_id, workspace_id in (("corr-a", "notary_team_01"), ("corr-b", "notary_team_02")):
                artifact = tmp_path / f"{correlation_id}.json"
                artifact.write_text(json.dumps(_apply_smoke_payload(correlation_id, workspace_id)), encoding="utf-8")
                retain_matter_access_apply_live_smoke_artifact(artifact, retention_root=retention_root)

            index = build_matter_access_apply_live_smoke_retention_index(
                retention_root=retention_root,
                correlation_id="corr-b",
                workspace_id="notary_team_02",
                status="PASSED",
                query="corr-b",
            )

            self.assertEqual(index["summary"]["run_count"], 1)
            self.assertEqual(index["live_smokes"][0]["correlation_id"], "corr-b")
            self.assertFalse(index["privacy"]["executesGraphRequests"])

    def test_index_surfaces_legacy_missing_redaction_shape_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            retention_root = tmp_path / "retention"
            artifact = tmp_path / "legacy.json"
            artifact.write_text(json.dumps(_apply_smoke_payload("legacy-corr")), encoding="utf-8")
            payload = retain_matter_access_apply_live_smoke_artifact(artifact, retention_root=retention_root)
            retention_json = Path(payload["summary"]["retention_json_path"])
            legacy_payload = json.loads(retention_json.read_text(encoding="utf-8"))
            legacy_payload.pop("redaction_shape", None)
            legacy_payload["summary"].pop("redaction_shape_status", None)
            legacy_payload["summary"].pop("redaction_shape_violation_count", None)
            legacy_payload["summary"].pop("redaction_shape_checked_node_count", None)
            retention_json.write_text(json.dumps(legacy_payload), encoding="utf-8")

            index = build_matter_access_apply_live_smoke_retention_index(retention_root=retention_root)
            readiness = build_matter_access_apply_live_smoke_retention_readiness(
                retention_root=retention_root,
                correlation_id="legacy-corr",
            )
            index_report = format_matter_access_apply_live_smoke_retention_index(index)
            readiness_report = format_matter_access_apply_live_smoke_retention_readiness(readiness)

            self.assertEqual(index["summary"]["redaction_shape_status_counts"]["NOT_EVALUATED"], 1)
            self.assertEqual(index["summary"]["redaction_shape_legacy_missing_count"], 1)
            self.assertTrue(index["summary"]["redaction_shape_upgrade_required"])
            self.assertEqual(index["summary"]["redaction_shape_upgrade_item_count"], 1)
            self.assertEqual(index["live_smokes"][0]["redaction_shape_status"], "NOT_EVALUATED")
            self.assertFalse(index["live_smokes"][0]["redaction_shape_evidence_present"])
            self.assertTrue(index["live_smokes"][0]["redaction_shape_legacy_missing"])
            self.assertTrue(index["live_smokes"][0]["upgrade_advice"]["required"])
            self.assertEqual(index["upgrade_advice"]["status"], "UPGRADE_REQUIRED")
            self.assertEqual(index["upgrade_advice"]["items"][0]["correlation_id"], "legacy-corr")
            self.assertFalse(index["upgrade_advice"]["items"][0]["executes_graph_requests"])
            self.assertFalse(index["upgrade_advice"]["items"][0]["tenant_writes_executed"])
            self.assertIn("matter-access-apply-live-smoke-retain", index["upgrade_advice"]["items"][0]["command"])
            self.assertEqual(readiness["status"], "NOT_READY")
            self.assertEqual(readiness["summary"]["latest_redaction_shape_status"], "NOT_EVALUATED")
            self.assertEqual(readiness["summary"]["redaction_shape_legacy_missing_count"], 1)
            self.assertTrue(readiness["summary"]["redaction_shape_upgrade_required"])
            self.assertEqual(readiness["upgrade_advice"]["status"], "UPGRADE_REQUIRED")
            self.assertIn("redaction-shape evidence", "\n".join(readiness["errors"]))
            self.assertIn("Upgrade Advice", index_report)
            self.assertIn("legacy-corr", readiness_report)
            self.assertIn("matter-access-apply-live-smoke-retain", readiness_report)

    def test_retention_blocks_invalid_source_without_copying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "invalid.json"
            payload = _apply_smoke_payload("corr-invalid")
            payload["summary"]["raw_graph_response_stored"] = True
            artifact.write_text(json.dumps(payload), encoding="utf-8")

            result = retain_matter_access_apply_live_smoke_artifact(
                artifact,
                retention_root=tmp_path / "retention",
            )

            self.assertEqual(result["status"], "BLOCKED")
            self.assertIn("raw_graph_response_stored", "\n".join(result["errors"]))
            self.assertFalse((tmp_path / "retention" / "corr-invalid").exists())

    def test_redaction_shape_blocks_forbidden_raw_graph_path_key_without_copying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "invalid-raw-path.json"
            payload = _apply_smoke_payload("corr-raw-path")
            payload["readBackShape"]["rawGraphPath"] = "/sites/example.sharepoint.com/lists/list-grants/items"
            artifact.write_text(json.dumps(payload), encoding="utf-8")

            result = retain_matter_access_apply_live_smoke_artifact(
                artifact,
                retention_root=tmp_path / "retention",
            )

            self.assertEqual(result["status"], "BLOCKED")
            self.assertEqual(result["summary"]["redaction_shape_status"], "BLOCKED")
            self.assertEqual(result["summary"]["redaction_shape_violation_count"], 2)
            self.assertIn("rawGraphPath", "\n".join(result["errors"]))
            self.assertIn("/sites/", "\n".join(result["errors"]))
            self.assertFalse((tmp_path / "retention" / "corr-raw-path").exists())

    def test_redaction_shape_blocks_secret_like_value_marker(self) -> None:
        payload = _apply_smoke_payload("corr-secret-marker")
        payload["writeResponseShape"]["diagnostic"] = "Authorization: Bearer redacted-but-invalid-shape"

        result = validate_matter_access_apply_live_smoke_redaction_shape(payload)

        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["summary"]["violation_count"], 1)
        self.assertIn("Authorization:", "\n".join(result["errors"]))
        self.assertFalse(result["privacy"]["executesGraphRequests"])

    def test_cli_retains_and_indexes_without_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "matter-access-apply-smoke.redacted.json"
            artifact.write_text(json.dumps(_apply_smoke_payload("cli-corr")), encoding="utf-8")
            retention_root = tmp_path / "retention"

            retain_payload, retain_rc = _invoke_cli(
                [
                    "matter-access-apply-live-smoke-retain",
                    "--matter-access-apply-live-smoke-artifact",
                    str(artifact),
                    "--matter-access-apply-live-smoke-retention-root",
                    str(retention_root),
                    "--format",
                    "json",
                ]
            )
            index_payload, index_rc = _invoke_cli(
                [
                    "matter-access-apply-live-smoke-retention-index",
                    "--matter-access-apply-live-smoke-retention-root",
                    str(retention_root),
                    "--matter-access-apply-live-smoke-correlation-id",
                    "cli-corr",
                    "--format",
                    "json",
                ]
            )

            self.assertEqual(retain_rc, 0)
            self.assertEqual(retain_payload["status"], "PASSED")
            self.assertEqual(index_rc, 0)
            self.assertEqual(index_payload["summary"]["run_count"], 1)
            self.assertEqual(index_payload["live_smokes"][0]["correlation_id"], "cli-corr")

    def test_readiness_reports_ready_for_retained_live_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "matter-access-apply-smoke.redacted.json"
            artifact.write_text(json.dumps(_apply_smoke_payload("ready-corr")), encoding="utf-8")
            retention_root = tmp_path / "retention"
            retain_matter_access_apply_live_smoke_artifact(artifact, retention_root=retention_root)

            readiness = build_matter_access_apply_live_smoke_retention_readiness(
                retention_root=retention_root,
                correlation_id="ready-corr",
                workspace_id="notary_team_01",
                now_utc="2026-07-08T16:00:00Z",
                write_artifact=True,
            )

            self.assertEqual(readiness["status"], "READY")
            self.assertEqual(readiness["summary"]["ready_run_count"], 1)
            self.assertEqual(readiness["summary"]["latest_correlation_id"], "ready-corr")
            self.assertEqual(readiness["summary"]["latest_redaction_shape_status"], "PASSED")
            self.assertEqual(readiness["summary"]["redaction_shape_passed_count"], 1)
            self.assertEqual(readiness["summary"]["redaction_shape_legacy_missing_count"], 0)
            self.assertFalse(readiness["summary"]["redaction_shape_upgrade_required"])
            self.assertEqual(readiness["upgrade_advice"]["status"], "CURRENT")
            self.assertFalse(readiness["summary"]["executes_graph_requests"])
            self.assertTrue(Path(readiness["summary"]["readiness_json_path"]).is_file())
            self.assertTrue(Path(readiness["summary"]["readiness_report_path"]).is_file())

    def test_readiness_blocks_when_no_retained_live_smoke_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            readiness = build_matter_access_apply_live_smoke_retention_readiness(
                retention_root=Path(tmp) / "retention",
                correlation_id="missing-corr",
            )

            self.assertEqual(readiness["status"], "NOT_READY")
            self.assertIn("retained_live_smoke_present", [check["id"] for check in readiness["checks"]])
            self.assertIn("At least one PASSED", "\n".join(readiness["errors"]))
            self.assertFalse(readiness["privacy"]["executesGraphRequests"])

    def test_cli_reports_live_smoke_retention_readiness_without_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            artifact = tmp_path / "matter-access-apply-smoke.redacted.json"
            artifact.write_text(json.dumps(_apply_smoke_payload("cli-ready-corr")), encoding="utf-8")
            retention_root = tmp_path / "retention"
            retain_matter_access_apply_live_smoke_artifact(artifact, retention_root=retention_root)

            payload, return_code = _invoke_cli(
                [
                    "matter-access-apply-live-smoke-retention-readiness",
                    "--matter-access-apply-live-smoke-retention-root",
                    str(retention_root),
                    "--matter-access-apply-live-smoke-correlation-id",
                    "cli-ready-corr",
                    "--matter-access-apply-live-smoke-write-readiness",
                    "--format",
                    "json",
                ]
            )

            self.assertEqual(return_code, 0)
            self.assertEqual(payload["status"], "READY")
            self.assertFalse(payload["summary"]["tenant_writes_executed"])
            self.assertTrue(Path(payload["summary"]["readiness_json_path"]).is_file())

    def test_cli_upgrade_advice_smoke_uses_legacy_fixture_and_reports_upgrade_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            retention_root = tmp_path / "retention"
            _write_legacy_retention_fixture(
                tmp_path=tmp_path,
                retention_root=retention_root,
                correlation_id="legacy-cli-corr",
            )

            index_payload, index_rc = _invoke_cli(
                [
                    "matter-access-apply-live-smoke-retention-index",
                    "--matter-access-apply-live-smoke-retention-root",
                    str(retention_root),
                    "--matter-access-apply-live-smoke-correlation-id",
                    "legacy-cli-corr",
                    "--format",
                    "json",
                ]
            )
            readiness_payload, readiness_rc = _invoke_cli(
                [
                    "matter-access-apply-live-smoke-retention-readiness",
                    "--matter-access-apply-live-smoke-retention-root",
                    str(retention_root),
                    "--matter-access-apply-live-smoke-correlation-id",
                    "legacy-cli-corr",
                    "--matter-access-apply-live-smoke-write-readiness",
                    "--format",
                    "json",
                ]
            )
            index_report, index_report_rc = _invoke_cli_text(
                [
                    "matter-access-apply-live-smoke-retention-index",
                    "--matter-access-apply-live-smoke-retention-root",
                    str(retention_root),
                    "--matter-access-apply-live-smoke-correlation-id",
                    "legacy-cli-corr",
                    "--format",
                    "text",
                ]
            )

            self.assertEqual(index_rc, 0)
            self.assertEqual(index_payload["summary"]["run_count"], 1)
            self.assertTrue(index_payload["summary"]["redaction_shape_upgrade_required"])
            self.assertEqual(index_payload["upgrade_advice"]["status"], "UPGRADE_REQUIRED")
            self.assertIn("matter-access-apply-live-smoke-retain", index_payload["upgrade_advice"]["items"][0]["command"])
            self.assertFalse(index_payload["upgrade_advice"]["privacy"]["executesGraphRequests"])
            self.assertEqual(readiness_rc, 2)
            self.assertEqual(readiness_payload["status"], "NOT_READY")
            self.assertTrue(readiness_payload["summary"]["redaction_shape_upgrade_required"])
            readiness_report_path = Path(readiness_payload["summary"]["readiness_report_path"])
            self.assertTrue(readiness_report_path.is_file())
            readiness_report = readiness_report_path.read_text(encoding="utf-8")
            self.assertEqual(index_report_rc, 0)
            self.assertIn("Upgrade Advice", index_report)
            self.assertIn("legacy-cli-corr", readiness_report)
            self.assertIn("matter-access-apply-live-smoke-retain", readiness_report)
            self.assertIn("performs no Graph request", readiness_report)

    def test_retention_validator_passes(self) -> None:
        self.assertEqual([], validator.validate())


def _invoke_cli(extra_args: list[str]) -> tuple[dict, int]:
    output, return_code = _invoke_cli_text(extra_args)
    return json.loads(output), return_code


def _invoke_cli_text(extra_args: list[str]) -> tuple[str, int]:
    parser = cli.build_parser()
    args = parser.parse_args(
        [
            "m365",
            "teams-sharepoint",
            *extra_args,
        ]
    )
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        return_code = args.func(args)
    return output.getvalue(), return_code


def _write_legacy_retention_fixture(*, tmp_path: Path, retention_root: Path, correlation_id: str) -> None:
    artifact = tmp_path / f"{correlation_id}.redacted.json"
    artifact.write_text(json.dumps(_apply_smoke_payload(correlation_id)), encoding="utf-8")
    payload = retain_matter_access_apply_live_smoke_artifact(artifact, retention_root=retention_root)
    retention_json = Path(payload["summary"]["retention_json_path"])
    legacy_payload = json.loads(retention_json.read_text(encoding="utf-8"))
    legacy_payload.pop("redaction_shape", None)
    legacy_payload["summary"].pop("redaction_shape_status", None)
    legacy_payload["summary"].pop("redaction_shape_violation_count", None)
    legacy_payload["summary"].pop("redaction_shape_checked_node_count", None)
    retention_json.write_text(json.dumps(legacy_payload), encoding="utf-8")


def _apply_smoke_payload(correlation_id: str, workspace_id: str = "notary_team_01") -> dict:
    return {
        "schema_version": "nac.m365-matter-access-apply-smoke/v0.1",
        "status": "PASSED",
        "generated_at": "2026-07-08T15:00:00Z",
        "summary": {
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
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
        "checks": [
            {"id": "grant_request_write_read", "status": "PASSED"},
            {"id": "audit_append_write_read", "status": "PASSED"},
            {"id": "cleanup", "status": "PASSED"},
            {"id": "apply_policy", "status": "PASSED"},
            {"id": "privacy", "status": "PASSED"},
        ],
        "privacy": {
            "storesTokensOrSecrets": False,
            "storesMatterPayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
        },
    }


if __name__ == "__main__":
    unittest.main()
