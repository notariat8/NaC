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
    retain_matter_access_apply_live_smoke_artifact,
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

            index = build_matter_access_apply_live_smoke_retention_index(retention_root=retention_root)
            self.assertEqual(index["status"], "PASSED")
            self.assertEqual(index["summary"]["run_count"], 1)
            self.assertEqual(index["live_smokes"][0]["correlation_id"], "corr-1")
            self.assertEqual(index["live_smokes"][0]["status"], "PASSED")

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

    def test_retention_validator_passes(self) -> None:
        self.assertEqual([], validator.validate())


def _invoke_cli(extra_args: list[str]) -> tuple[dict, int]:
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
    return json.loads(output.getvalue()), return_code


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
