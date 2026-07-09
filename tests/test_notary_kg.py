from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli  # noqa: E402
from notary_kg.catalog import all_case_summaries, find_case, load_catalogs
from notary_kg.business_case_inventory import (
    build_business_case_inventory,
    validate_business_case_inventory,
)
from notary_kg.cli import main as kg_main
from notary_kg.editor import build_editor_view
from notary_kg.ontology_storage_contract import (
    build_ontology_storage_contract,
    validate_ontology_storage_contract,
)
from notary_kg.pilot_checklist import build_pilot_intake_checklist
from notary_kg.workflow_contract import build_workflow_contract_draft
from nac_gnotkg.views import build_cost_review_view


class NotaryKnowledgeGraphTests(unittest.TestCase):
    def test_loads_usecase_local_catalogs(self) -> None:
        catalogs = load_catalogs(REPO_ROOT)
        cases = all_case_summaries(catalogs)
        expected_count = len(list((REPO_ROOT / "usecases").glob("*/knowledge-graph.graph.json")))

        self.assertEqual(len(catalogs), expected_count)
        self.assertEqual(len(cases), expected_count)
        self.assertIn("usecase.bautraegervertrag", {catalog.graph_id for catalog in catalogs})

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
        self.assertIn("nac-grundbuch-portal", summary.plugin_dependencies)
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

    def test_business_case_inventory_covers_canonical_sizing_scope(self) -> None:
        payload = build_business_case_inventory(REPO_ROOT)
        validation = validate_business_case_inventory(payload)
        cases = {entry["slug"]: entry for entry in payload["business_cases"]}

        self.assertEqual(payload["schema_version"], "nac.notarial-business-case-inventory/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["mode"], "thin_catalog_for_sizing")
        self.assertEqual(
            payload["storage_strategy"]["sharepoint_role"],
            "operative_mvp_data_store",
        )
        self.assertEqual(
            payload["storage_strategy"]["ontology_role"],
            "versioned_repo_catalog_and_projection_contract",
        )
        self.assertFalse(payload["generated_from"]["central_knowledge_graph_folder_allowed"])
        self.assertTrue(payload["generated_from"]["usecase_local_knowledge_graphs_remain_authoritative"])
        self.assertFalse(payload["privacy"]["contains_real_matter_data"])
        self.assertIn("immobilienkaufvertrag", cases)
        self.assertEqual(cases["immobilienkaufvertrag"]["implementation_depth"], "candidate_deep_process")
        self.assertIn("complexity_score", cases["handelsregisteranmeldung"]["sizing"])
        self.assertGreaterEqual(payload["summary"]["business_case_count"], 20)
        self.assertEqual(
            payload["summary"]["canonical_covered_count"],
            payload["summary"]["canonical_target_count"],
        )

    def test_cli_business_case_inventory_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "business-case-inventory"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-business-case-inventory/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["storage_strategy"]["document_content_role"], "outside_ontology_and_outside_git")
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_business_case_inventory_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "business-case-inventory",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-business-case-inventory/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_ontology_storage_contract_bounds_inventory_and_m365_store(self) -> None:
        payload = build_ontology_storage_contract(REPO_ROOT)
        validation = validate_ontology_storage_contract(payload)
        contract = payload["contract"]
        evaluation = payload["evaluation"]

        self.assertEqual(payload["schema_version"], "nac.notarial-ontology-sizing-storage/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertTrue(contract["scope"]["offline_contract_only"])
        self.assertFalse(contract["scope"]["executes_graph_requests_now"])
        self.assertFalse(contract["scope"]["changes_sharepoint_schema_now"])
        self.assertFalse(contract["scope"]["creates_central_knowledge_graph_folder"])
        self.assertTrue(contract["graph"]["rest_only"])
        self.assertFalse(contract["graph"]["legacy_sharepoint_api_allowed"])
        self.assertEqual(contract["storage_roles"]["sharepoint"]["role"], "operative_mvp_data_store")
        self.assertEqual(contract["storage_roles"]["ontology"]["role"], "versioned_repo_catalog_and_projection_contract")
        self.assertFalse(contract["projection_rules"]["runtime_reasoning_required"])
        self.assertFalse(contract["projection_rules"]["runtime_database_role_allowed"])
        self.assertTrue(evaluation["derived_decision"]["sharepoint_remains_mvp_store"])
        self.assertFalse(evaluation["derived_decision"]["runtime_reasoning_on_request_path_allowed"])
        self.assertGreaterEqual(
            evaluation["current_sizing"]["max_supported_business_cases_without_store_migration"],
            evaluation["current_sizing"]["business_case_count"],
        )

    def test_cli_ontology_storage_contract_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "ontology-storage-contract"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-ontology-sizing-storage/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["inventory_snapshot"]["status"], "PASSED")
        self.assertEqual(payload["contract"]["graph"]["base_url"], "https://graph.microsoft.com/v1.0")
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_ontology_storage_contract_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "ontology-storage-contract",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-ontology-sizing-storage/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_cli_unknown_case_fails(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "case", "does-not-exist"])

        self.assertEqual(exit_code, 1)
        self.assertIn("Unknown KG case slug", buffer.getvalue())

    def test_editor_view_exposes_no_code_tabs_without_value_fields(self) -> None:
        view = build_editor_view(REPO_ROOT, "immobilienkaufvertrag")
        tabs = view["editor_model"]["tabs"]

        self.assertEqual(
            [tab["id"] for tab in tabs],
            ["open_information", "documents", "decisions", "gates_evidence"],
        )
        self.assertEqual(
            [action["name"] for action in view["actions"]],
            ["get_graph", "propose_patch", "validate_graph_patch", "create_pull_request"],
        )
        open_information = tabs[0]
        self.assertEqual(open_information["render_as"], "checklist")
        self.assertIn("value", open_information["blocked_fields"])
        self.assertFalse(_contains_key(view, "value"))

    def test_cli_editor_view_returns_json_tabs(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                    "editor-view",
                    "immobilienkaufvertrag",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.kg-editor-view/v0.1")
        self.assertEqual(payload["editor_model"]["tabs"][0]["id"], "open_information")
        self.assertIn("value", payload["patch_policy"]["forbidden_fields"])

    def test_every_usecase_exposes_gnotkg_cost_gate(self) -> None:
        catalogs = load_catalogs(REPO_ROOT)
        missing: list[str] = []

        for catalog in catalogs:
            for case in catalog.payload.get("cases", []):
                gate_ids = {gate.get("id") for gate in case.get("gates", []) if isinstance(gate, dict)}
                information_ids = {
                    item.get("id")
                    for item in case.get("required_information", [])
                    if isinstance(item, dict)
                }
                decision_ids = {
                    decision.get("id")
                    for decision in case.get("decisions", [])
                    if isinstance(decision, dict)
                }
                evidence_ids = {
                    evidence.get("id")
                    for evidence in case.get("evidence", [])
                    if isinstance(evidence, dict)
                }
                if not {
                    "cost.business_value",
                    "decision.gnotkg_cost_path",
                    "gate.gnotkg_cost_review",
                    "evidence.gnotkg_cost_note",
                }.issubset(information_ids | decision_ids | gate_ids | evidence_ids):
                    missing.append(str(case.get("slug")))

        self.assertEqual(missing, [])

    def test_cli_cost_view_returns_safe_graph(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                    "cost-view",
                    "immobilienkaufvertrag",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, build_cost_review_view(REPO_ROOT, "immobilienkaufvertrag"))
        self.assertEqual(payload["rendering"]["preferred_renderer"], "xyflow")
        self.assertFalse(_contains_key(payload, "value"))

    def test_workflow_contract_draft_from_kg_exposes_safe_skeleton(self) -> None:
        payload = build_workflow_contract_draft(REPO_ROOT, "immobilienkaufvertrag")
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(payload["schema_version"], "nac.workflow-contract-draft/v0.1")
        self.assertEqual(payload["contract_id"], "workflow.immobilienkaufvertrag")
        self.assertEqual(payload["status"], "draft_from_knowledge_graph")
        self.assertEqual(payload["source"]["catalog_source"], "usecases/immobilienkaufvertrag/knowledge-graph.graph.json")
        self.assertGreaterEqual(len(payload["intake"]["required_information"]), 6)
        self.assertGreaterEqual(len(payload["gates"]), 1)
        self.assertIn("python scripts/validate_knowledge_graph.py", payload["validation_commands"])
        self.assertFalse(payload["guardrails"]["real_mandate_data_in_git"])
        self.assertFalse(payload["guardrails"]["value_fields_included"])
        self.assertTrue(payload["guardrails"]["protected_pr_required"])
        self.assertFalse(_contains_key(payload, "value"))
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_cli_workflow_contract_returns_safe_json_skeleton(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                    "workflow-contract",
                    "immobilienkaufvertrag",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, build_workflow_contract_draft(REPO_ROOT, "immobilienkaufvertrag"))
        self.assertEqual(payload["proposal_policy"]["mode"], "proposal_only")
        self.assertIn("value", payload["proposal_policy"]["forbidden_fields"])
        self.assertFalse(_contains_key(payload, "value"))

    def test_gmbh_ug_pilot_checklist_reads_kg_node_without_values(self) -> None:
        payload = build_pilot_intake_checklist(REPO_ROOT, "online-gmbh-gruendung")
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(payload["schema_version"], "nac.pilot-intake-checklist/v0.1")
        self.assertEqual(payload["pilot_usecase"]["slug"], "online-gmbh-gruendung")
        self.assertEqual(payload["workflow_binding"]["workflow_id"], "online-gmbh-gruendung:pilot-intake")
        self.assertEqual(payload["workflow_binding"]["approval_state"], "draft_requires_notarial_review")
        self.assertEqual([section["id"] for section in payload["sections"]], [
            "required_information",
            "documents",
            "decisions",
            "gates",
            "evidence",
        ])
        self.assertGreaterEqual(payload["summary"]["total_items"], 20)
        self.assertEqual(payload["summary"]["next_step"]["id"], "company.name")
        self.assertIn("nac-handelsregister", payload["summary"]["plugin_dependencies"])
        self.assertFalse(payload["guardrails"]["real_mandate_data_in_git"])
        self.assertFalse(payload["guardrails"]["productive_register_or_xnp_action"])
        self.assertFalse(_contains_key(payload, "value"))
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_cli_pilot_checklist_returns_gmbh_ug_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                    "pilot-checklist",
                    "online-gmbh-gruendung",
                ]
            )

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload, build_pilot_intake_checklist(REPO_ROOT, "online-gmbh-gruendung"))
        self.assertEqual(payload["summary"]["next_step"]["label"], "Gesellschaft Name")
        self.assertFalse(_contains_key(payload, "value"))


if __name__ == "__main__":
    unittest.main()


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False
