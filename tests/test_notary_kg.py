from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from notary_kg.catalog import all_case_summaries, find_case, load_catalogs
from notary_kg.cli import main as kg_main


REPO_ROOT = Path(__file__).resolve().parents[1]


class NotaryKnowledgeGraphTests(unittest.TestCase):
    def test_loads_usecase_local_catalogs(self) -> None:
        catalogs = load_catalogs(REPO_ROOT)
        cases = all_case_summaries(catalogs)
        expected_count = len(list((REPO_ROOT / "usecases").glob("*/knowledge-graph.graph.json")))

        self.assertEqual(len(catalogs), expected_count)
        self.assertEqual(len(cases), expected_count)
        self.assertIn("usecase.bautraegervertrag", {catalog.graph_id for catalog in catalogs})
        self.assertIn("usecase.ao52aas-gemeinnuetzigkeit", {catalog.graph_id for catalog in catalogs})

    def test_all_required_information_values_stay_empty(self) -> None:
        catalogs = load_catalogs(REPO_ROOT)
        cases = all_case_summaries(catalogs)

        self.assertTrue(cases)
        self.assertTrue(all(case.ready_for_development for case in cases))
        self.assertEqual([case.slug for case in cases if case.non_empty_values], [])

    def test_case_summary_exposes_bautraegervertrag_development_inputs(self) -> None:
        catalogs = load_catalogs(REPO_ROOT)
        summary = find_case(catalogs, "bautraegervertrag")

        self.assertIsNotNone(summary)
        assert summary is not None
        self.assertEqual(summary.priority, "P0")
        self.assertGreaterEqual(summary.open_required_information, 6)
        self.assertIn("noc-grundbuch-portal", summary.plugin_dependencies)
        self.assertTrue(summary.first_open_questions)

    def test_cli_status_returns_json_totals(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "status"])

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        expected_count = len(list((REPO_ROOT / "usecases").glob("*/knowledge-graph.graph.json")))
        self.assertEqual(payload["totals"]["catalogs"], expected_count)
        self.assertEqual(payload["totals"]["cases"], expected_count)
        self.assertEqual(payload["totals"]["cases_ready_for_development"], expected_count)

    def test_cli_unknown_case_fails(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "case", "does-not-exist"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Unknown KG case slug", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()

