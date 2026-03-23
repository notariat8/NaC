from __future__ import annotations

import unittest
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


if __name__ == "__main__":
    unittest.main()
