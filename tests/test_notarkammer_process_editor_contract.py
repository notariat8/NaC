from __future__ import annotations

import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "notarkammer-process-editor.contract.json"
DE_DOC = REPO_ROOT / "docs" / "de" / "architecture" / "notarkammer-process-editor.md"
EN_DOC = REPO_ROOT / "docs" / "en" / "architecture" / "notarkammer-process-editor.md"


class NotarkammerProcessEditorContractTests(unittest.TestCase):
    def test_contract_defines_safe_bpmn_editor_and_viewer_boundary(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

        self.assertEqual(contract["schema_version"], "nac.notarkammer-process-editor/v0.1")
        self.assertEqual(contract["template_source_of_truth"], "git")
        self.assertEqual(contract["runtime_data_plane"], "m365_sharepoint_event_journal")
        self.assertEqual(contract["primary_demo_usecase"], "immobilienkaufvertrag")
        self.assertEqual(contract["publication_flow"], ["draft", "review", "protected_pr", "template_catalog"])

        for surface in (
            "bpmn_template",
            "step_label",
            "duration_band",
            "parallel_group",
            "critical_path_hint",
            "xnp_snp_gate",
            "xnotar_xjustiz_handoff",
            "grundbuch_boundary",
            "card_reader_readiness",
        ):
            self.assertIn(surface, contract["editable_surfaces"])

        for guardrail in (
            "no_mandate_data",
            "no_productive_xnp_action",
            "no_live_register_query",
            "no_secret_values",
            "no_customer_identifier_in_public_view",
            "protected_pr_before_template_publish",
        ):
            self.assertTrue(contract["guardrails"][guardrail])

    def test_docs_explain_demo_safe_editor_runtime_and_graph_projection(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        german = DE_DOC.read_text(encoding="utf-8")
        english = EN_DOC.read_text(encoding="utf-8")
        combined = "\n".join([json.dumps(contract, sort_keys=True), german, english])

        for term in (
            "BPMN-Editor",
            "BPMN editor",
            "M365/SharePoint",
            "Graph-Projektion",
            "graph projection",
            "XNP/SNP",
            "kritischer Pfad",
            "critical path",
            "Dauerband",
            "duration band",
            "Keine Mandatsdaten",
            "No mandate data",
            "kein produktiver XNP-Zugriff",
            "no productive XNP access",
        ):
            self.assertIn(term, combined)


if __name__ == "__main__":
    unittest.main()
