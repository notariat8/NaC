from __future__ import annotations

import unittest
import json
import tempfile
from pathlib import Path

from business_os.engine import BusinessProcessEngine


REPO_ROOT = Path(__file__).resolve().parents[1]


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = BusinessProcessEngine(REPO_ROOT)

    def test_validate_all_example_processes(self) -> None:
        results = self.engine.validate_all_processes()
        self.assertTrue(results)
        self.assertTrue(all(result.ok for result in results))

    def test_invoice_summary_contains_customer(self) -> None:
        summary = self.engine.render_summary(Path("processes/invoices/2026/REQ-2026-0001.json"))
        self.assertIn("Acme GmbH", summary)
        self.assertIn("brutto=1428.00", summary)

    def test_monthly_close_aggregates_sample_data(self) -> None:
        report = self.engine.monthly_close(year=2026, month=3)
        self.assertEqual(report.invoice_total_gross, 1428.0)
        self.assertEqual(report.bookkeeping_debit, 1428.0)
        self.assertEqual(report.bookkeeping_credit, 1428.0)
        self.assertEqual(report.tax_cases, 1)

    def test_requires_approval_without_approver_fails(self) -> None:
        source_file = REPO_ROOT / "processes" / "invoices" / "2026" / "REQ-2026-0001.json"
        payload = json.loads(source_file.read_text(encoding="utf-8"))
        payload["actor_context"]["requested_decision_type"] = "requires_approval"
        payload["actor_context"].pop("approver_role", None)

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_file = Path(tmp_dir) / "REQ-2026-9001.json"
            temp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            result = self.engine.validate_document(temp_file)
            self.assertFalse(result.ok)
            self.assertTrue(any("requires_approval erfordert approver_role" in e for e in result.errors))

    def test_rvg_requires_rvg_qualification(self) -> None:
        source_file = REPO_ROOT / "processes" / "invoices" / "2026" / "REQ-2026-0001.json"
        payload = json.loads(source_file.read_text(encoding="utf-8"))
        payload["metadata"]["billing_regime"] = "rvg"
        payload["actor_context"]["requested_qualification"] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            temp_file = Path(tmp_dir) / "REQ-2026-9002.json"
            temp_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            result = self.engine.validate_document(temp_file)
            self.assertFalse(result.ok)
            self.assertTrue(any("RVG-Rechnung erfordert Qualifikation" in e for e in result.errors))


if __name__ == "__main__":
    unittest.main()
