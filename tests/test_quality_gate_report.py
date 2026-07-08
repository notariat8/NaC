from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import quality_gate


class QualityGateReportTests(unittest.TestCase):
    def test_markdown_report_surfaces_m365_release_readiness_go_no_go(self) -> None:
        payload = {
            "timestamp_utc": "2026-07-07T00:00:00+00:00",
            "profile": "strict",
            "overall_status": "PASSED",
            "checks": [
                {
                    "id": "m365_release_readiness_gate",
                    "title": "M365 Release Readiness Gate",
                    "command": ["python3", "scripts/validate_m365_release_readiness_gate.py"],
                    "return_code": 0,
                    "passed": True,
                    "duration_ms": 42,
                    "output": "STATUS: PASSED",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.md"

            quality_gate.write_markdown(report_path, payload)
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("## M365 MVP Readiness", report)
        self.assertIn("- Go/No-Go: `mvp_release_readiness=READY`", report)
        self.assertIn("- Runner summary: `release_gate_readiness=READY`", report)
        self.assertIn("- CI enforcement: `ENFORCED`", report)
        self.assertIn("- Gate check: `PASSED`", report)
        self.assertIn("release-gate-write-audit-pack", report)
        self.assertIn("verification.m365_matter_access_delegation", report)
        self.assertIn("`5/5` negative cases detected", report)
        self.assertIn("`missing_reason`, `expired_delegation`, `workspace_scope_violation`, `missing_cleanup`, `audit_readback_missing`", report)
        self.assertIn("fail-closed before Graph writes", report)

    def test_markdown_report_marks_readiness_gate_not_evaluated_when_missing(self) -> None:
        payload = {
            "timestamp_utc": "2026-07-07T00:00:00+00:00",
            "profile": "minimal",
            "overall_status": "PASSED",
            "checks": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            report_path = Path(tmp) / "report.md"

            quality_gate.write_markdown(report_path, payload)
            report = report_path.read_text(encoding="utf-8")

        self.assertIn("- CI enforcement: `NOT_EVALUATED`", report)
        self.assertIn("- Gate check: `NOT_ATTACHED`", report)


if __name__ == "__main__":
    unittest.main()
