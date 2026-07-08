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

from nac_cli import cli  # noqa: E402
from nac_m365_graph.matter_access_decision_replay import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
    replay_matter_access_decisions_from_path,
    write_matter_access_decision_replay_artifact,
)
from scripts import validate_m365_matter_access_decision_replay as validator  # noqa: E402


class M365MatterAccessDecisionReplayTests(unittest.TestCase):
    def test_replay_allows_assignments_and_active_deputy_grant(self) -> None:
        payload = replay_matter_access_decisions_from_path(
            snapshot_path=DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
            reference_time="2026-07-08T12:00:00Z",
            correlation_id="unit-replay",
        )

        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["schema_version"], "nac.m365-matter-access-decision-replay/v0.1")
        self.assertEqual(payload["summary"]["request_count"], 10)
        self.assertEqual(payload["summary"]["allowed_count"], 3)
        self.assertEqual(payload["summary"]["blocked_count"], 7)
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["executes_graph_writes"])
        self.assertFalse(payload["privacy"]["executesGraphRequests"])
        self.assertFalse(payload["privacy"]["executesGraphWrites"])

        codes = payload["summary"]["decision_code_counts"]
        for code in (
            "ALLOW_LEAD_NOTARY",
            "ALLOW_ASSIGNED_CLERK",
            "ALLOW_ACTIVE_DEPUTY_GRANT",
        ):
            self.assertEqual(codes[code], 1)
        self.assertTrue(all(decision["expected_match"] for decision in payload["decisions"]))

    def test_replay_blocks_scope_and_incomplete_deputy_grants(self) -> None:
        payload = replay_matter_access_decisions_from_path(
            snapshot_path=DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
            reference_time="2026-07-08T12:00:00Z",
            correlation_id="unit-replay",
        )

        codes = payload["summary"]["decision_code_counts"]
        for code in (
            "BLOCK_WORKSPACE_SCOPE",
            "BLOCK_CASE_SCOPE",
            "BLOCK_DEPUTY_GRANT_EXPIRED",
            "BLOCK_DEPUTY_GRANT_MISSING_REASON",
            "BLOCK_DEPUTY_GRANT_MISSING_APPROVER",
            "BLOCK_DEPUTY_GRANT_MISSING_AUDIT_CORRELATION",
            "BLOCK_BLANKET_VISIBILITY",
        ):
            self.assertEqual(codes[code], 1)

    def test_replay_evidence_is_redacted(self) -> None:
        payload = replay_matter_access_decisions_from_path(
            snapshot_path=DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
            reference_time="2026-07-08T12:00:00Z",
            correlation_id="unit-replay",
        )
        serialized = json.dumps(payload, ensure_ascii=False)

        self.assertNotIn("synthetic-", serialized)
        self.assertNotIn("NAC-SYN-MATTER", serialized)
        self.assertNotIn("NAC-SYN-GRANT", serialized)
        self.assertNotIn("NAC-SYN-AUDIT", serialized)
        self.assertNotIn("/sites/", serialized)
        self.assertNotIn("@", serialized)
        self.assertFalse(payload["privacy"]["storesMatterPayloads"])
        self.assertFalse(payload["privacy"]["storesTokensOrSecrets"])
        self.assertFalse(payload["privacy"]["storesRawSharePointItems"])

    def test_replay_artifact_writer_and_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "matter-access-decision-replay.redacted.json"
            payload = replay_matter_access_decisions_from_path(
                snapshot_path=DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT,
                reference_time="2026-07-08T12:00:00Z",
                correlation_id="unit-replay",
            )
            write_matter_access_decision_replay_artifact(payload, output_path)
            written = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(written["status"], "PASSED")

            cli_payload, return_code = _invoke_cli(
                [
                    "matter-access-decision-replay",
                    "--matter-access-decision-snapshot",
                    str(DEFAULT_MATTER_ACCESS_DECISION_REPLAY_SNAPSHOT),
                    "--matter-access-decision-replay-output",
                    str(output_path),
                    "--matter-access-decision-reference-time",
                    "2026-07-08T12:00:00Z",
                    "--mcp-smoke-correlation-id",
                    "cli-replay",
                    "--format",
                    "json",
                ]
            )
            self.assertEqual(return_code, 0)
            self.assertEqual(cli_payload["status"], "PASSED")
            self.assertEqual(cli_payload["summary"]["artifact_path"], str(output_path))
            self.assertFalse(cli_payload["summary"]["executes_graph_requests"])

    def test_decision_replay_validator_passes(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
