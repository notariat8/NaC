from __future__ import annotations

import io
import json
import sys
import tempfile
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
from notary_kg.deep_process_routing import (
    build_deep_process_candidate_routing,
    validate_deep_process_candidate_routing,
)
from notary_kg.editor import build_editor_view
from notary_kg.first_wave_gap_review import (
    build_first_wave_bpmn_outline_gap_review,
    validate_first_wave_bpmn_outline_gap_review,
    validate_first_wave_bpmn_outline_gap_review_artifact,
    write_first_wave_bpmn_outline_gap_review_artifact,
)
from notary_kg.first_wave_outline import (
    build_first_wave_bpmn_outline,
    validate_first_wave_bpmn_outline,
)
from notary_kg.ontology_scale_budget import (
    build_ontology_scale_budget_smoke,
    validate_ontology_scale_budget_smoke,
)
from notary_kg.ontology_storage_contract import (
    build_ontology_storage_contract,
    validate_ontology_storage_contract,
)
from notary_kg.pilot_checklist import build_pilot_intake_checklist
from notary_kg.process_ontology_contract import (
    build_process_ontology_contract,
    validate_process_ontology_contract,
)
from notary_kg.process_ontology_schema_apply_plan import (
    build_process_ontology_sharepoint_schema_apply_plan,
    validate_process_ontology_sharepoint_schema_apply_plan,
)
from notary_kg.process_ontology_schema_apply_readiness import (
    build_process_ontology_sharepoint_schema_apply_readiness,
    validate_process_ontology_sharepoint_schema_apply_readiness,
)
from notary_kg.process_ontology_schema_gap import (
    build_process_ontology_sharepoint_schema_gap,
    validate_process_ontology_sharepoint_schema_gap,
)
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

    def test_process_ontology_contract_binds_inventory_to_product_model(self) -> None:
        payload = build_process_ontology_contract(REPO_ROOT)
        validation = validate_process_ontology_contract(payload)
        contract = payload["contract"]
        summary = payload["evaluation"]["summary"]
        derived = payload["evaluation"]["derived_decision"]

        self.assertEqual(payload["schema_version"], "nac.notarial-process-ontology/v1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(contract["source_of_truth"]["runtime_store"], "sharepoint_metadata_lists_and_document_pointers")
        self.assertEqual(contract["graph_boundary"]["m365_data_plane"], "microsoft_graph_rest_v1")
        self.assertFalse(contract["graph_boundary"]["sdk_allowed"])
        self.assertFalse(contract["graph_boundary"]["legacy_sharepoint_api_allowed"])
        self.assertTrue(contract["sizing_policy"]["all_business_cases_must_be_included"])
        self.assertGreaterEqual(summary["business_case_count"], 20)
        self.assertEqual(summary["case_contract_index_count"], summary["business_case_count"])
        self.assertTrue(derived["ontology_is_product_model_contract"])
        self.assertFalse(derived["runtime_reasoning_on_request_path_allowed"])
        self.assertFalse(derived["live_apply_required_now"])
        self.assertIn("Matter", contract["canonical_entity_classes"])
        self.assertIn("archive", contract["required_process_phases"])
        self.assertIn("Akten", contract["sharepoint_projection_rules"]["required_lists_or_libraries"])

    def test_cli_process_ontology_contract_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "process-ontology-contract"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-process-ontology/v1")
        self.assertEqual(payload["status"], "PASSED")
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_process_ontology_contract_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "process-ontology-contract",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-process-ontology/v1")
        self.assertEqual(payload["status"], "PASSED")

    def test_process_ontology_schema_gap_surfaces_concrete_sharepoint_gaps(self) -> None:
        payload = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)
        validation = validate_process_ontology_sharepoint_schema_gap(payload)
        field_gap_ids = {gap["id"] for gap in payload["field_gaps"]}
        optional_gap_ids = {gap["id"] for gap in payload["optional_projection_gaps"]}
        choice_gap_ids = {gap["id"] for gap in payload["choice_gaps"]}

        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-gap/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["missing_required_list_count"], 0)
        self.assertGreaterEqual(payload["summary"]["business_case_count"], 20)
        self.assertGreaterEqual(payload["summary"]["field_gap_count"], 10)
        self.assertGreaterEqual(payload["summary"]["choice_gap_count"], 1)
        self.assertIn("Akten.ProcessInstanceId.missing", field_gap_ids)
        self.assertIn("AufgabenFristen.ProcessPhase.missing", field_gap_ids)
        self.assertIn("optional-list.Prozessregister", optional_gap_ids)
        self.assertIn("optional-library.BPMN Models", optional_gap_ids)
        self.assertIn("Akten.Vorgangstyp.choices", choice_gap_ids)
        self.assertFalse(payload["apply_boundary"]["executes_graph_requests"])
        self.assertFalse(payload["apply_boundary"]["writes_sharepoint"])
        self.assertTrue(payload["apply_boundary"]["owner_gate_required_before_apply"])

    def test_cli_process_ontology_schema_gap_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "process-ontology-schema-gap"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-gap/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_process_ontology_schema_gap_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "process-ontology-schema-gap",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-gap/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_process_ontology_schema_apply_plan_builds_graph_rest_steps_from_gaps(self) -> None:
        payload = build_process_ontology_sharepoint_schema_apply_plan(REPO_ROOT)
        validation = validate_process_ontology_sharepoint_schema_apply_plan(payload)
        operations = {step["operation"] for step in payload["steps"]}
        endpoints = payload["apply_boundary"]["future_apply_endpoint_families"]

        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-plan/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["source_total_gap_count"], 34)
        self.assertEqual(payload["summary"]["total_step_count"], 34)
        self.assertEqual(payload["summary"]["create_column_step_count"], 28)
        self.assertEqual(payload["summary"]["extend_choice_step_count"], 4)
        self.assertEqual(payload["summary"]["create_list_step_count"], 1)
        self.assertEqual(payload["summary"]["create_document_library_step_count"], 1)
        self.assertIn("create_list", operations)
        self.assertIn("create_document_library", operations)
        self.assertIn("create_column", operations)
        self.assertIn("extend_choice_column", operations)
        self.assertIn("POST /sites/{site-id}/lists", endpoints)
        self.assertIn("POST /sites/{site-id}/lists/{list-id}/columns", endpoints)
        self.assertIn("PATCH /sites/{site-id}/lists/{list-id}/columns/{column-id}", endpoints)
        self.assertFalse(payload["apply_boundary"]["executes_graph_requests"])
        self.assertFalse(payload["apply_boundary"]["writes_sharepoint"])
        self.assertFalse(payload["apply_boundary"]["changes_sharepoint_schema"])
        self.assertTrue(payload["apply_boundary"]["owner_gate_required_before_apply"])

    def test_cli_process_ontology_schema_apply_plan_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "process-ontology-schema-apply-plan"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-plan/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["total_step_count"], 34)
        for forbidden in ("client_secret", "private_key", "authorization", "bearer ", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_process_ontology_schema_apply_plan_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "process-ontology-schema-apply-plan",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-plan/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_process_ontology_schema_apply_readiness_expands_plan_per_workspace(self) -> None:
        payload = build_process_ontology_sharepoint_schema_apply_readiness(REPO_ROOT)
        validation = validate_process_ontology_sharepoint_schema_apply_readiness(payload)

        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-readiness/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["workspace_count"], 2)
        self.assertEqual(payload["summary"]["apply_plan_step_count"], 34)
        self.assertEqual(payload["summary"]["workspace_apply_unit_count"], 68)
        self.assertEqual(payload["summary"]["known_site_id_count"], 2)
        self.assertEqual(payload["summary"]["missing_required_list_id_count"], 0)
        self.assertEqual(payload["summary"]["dynamic_resource_resolution_count"], 12)
        self.assertEqual(payload["summary"]["live_apply_readiness"], "OWNER_GATE_REQUIRED")
        self.assertEqual(payload["permission_readiness"]["required_application_permission"], "Sites.Manage.All")
        self.assertTrue(payload["permission_readiness"]["permission_present_in_provisioned_state"])
        self.assertFalse(payload["permission_readiness"]["delegated_user_context_allowed_for_live_apply"])
        self.assertFalse(payload["apply_boundary"]["executes_graph_requests"])
        self.assertFalse(payload["apply_boundary"]["writes_sharepoint"])
        self.assertTrue(payload["apply_boundary"]["owner_gate_required_before_live_apply"])

    def test_cli_process_ontology_schema_apply_readiness_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(
                ["--repo-root", str(REPO_ROOT), "--format", "json", "process-ontology-schema-apply-readiness"]
            )

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-readiness/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["workspace_apply_unit_count"], 68)
        for forbidden in ("client_secret", "private_key", "authorization", "bearer ", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_process_ontology_schema_apply_readiness_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "process-ontology-schema-apply-readiness",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-readiness/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_deep_process_candidate_routing_prioritizes_high_and_explicit_cases(self) -> None:
        payload = build_deep_process_candidate_routing(REPO_ROOT)
        validation = validate_deep_process_candidate_routing(payload)
        routes = {route["slug"]: route for route in payload["routes"]}

        self.assertEqual(payload["schema_version"], "nac.notarial-deep-process-candidate-routing/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertFalse(payload["routing_policy"]["deep_modeling_required_for_all_candidates"])
        self.assertFalse(payload["guardrails"]["writes_sharepoint"])
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertEqual(routes["online-gmbh-gruendung"]["routing_lane"], "first_wave_deep_process")
        self.assertIn("complexity_band:high", routes["online-gmbh-gruendung"]["routing_reasons"])
        self.assertEqual(routes["immobilienkaufvertrag"]["routing_lane"], "first_wave_deep_process")
        self.assertEqual(routes["handelsregisteranmeldung"]["routing_lane"], "first_wave_deep_process")
        self.assertEqual(routes["grundstueckskaufvertrag"]["routing_lane"], "legacy_alias_dedupe")
        self.assertGreaterEqual(payload["summary"]["candidate_count"], payload["summary"]["first_wave_count"])

    def test_cli_deep_process_candidates_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "deep-process-candidates"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-deep-process-candidate-routing/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertIn("online-gmbh-gruendung", payload["recommended_batch"])
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_deep_process_candidates_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "deep-process-candidates",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-deep-process-candidate-routing/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_first_wave_bpmn_outline_binds_existing_sources(self) -> None:
        payload = build_first_wave_bpmn_outline(REPO_ROOT)
        validation = validate_first_wave_bpmn_outline(payload)
        outlines = {outline["slug"]: outline for outline in payload["outlines"]}

        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(set(outlines), set(payload["source"]["recommended_batch"]))
        self.assertIn("online-gmbh-gruendung", outlines)
        for outline in outlines.values():
            self.assertTrue(outline["sources"]["knowledge_graph_exists"])
            self.assertTrue(outline["sources"]["bpmn_exists"])
            self.assertFalse(outline["bpmn_outline"]["is_executable"])
            self.assertGreater(outline["bpmn_outline"]["flow_node_count"], 0)
            self.assertGreater(outline["kg_outline"]["required_information_nodes"], 0)
            self.assertFalse(outline["projection_plan"]["stores_matter_values"])
            self.assertFalse(outline["projection_plan"]["writes_sharepoint"])
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertTrue(payload["guardrails"]["bpmn_remains_process_model_not_runtime_engine"])

    def test_cli_first_wave_bpmn_outline_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "first-wave-bpmn-outline"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["first_wave_count"], 4)
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_first_wave_bpmn_outline_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "first-wave-bpmn-outline",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_first_wave_bpmn_outline_gap_review_surfaces_offline_plans(self) -> None:
        payload = build_first_wave_bpmn_outline_gap_review(REPO_ROOT)
        validation = validate_first_wave_bpmn_outline_gap_review(payload)
        review_items = {item["slug"]: item for item in payload["review_items"]}

        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline-gap-review/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(len(review_items), 4)
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertFalse(payload["guardrails"]["writes_sharepoint"])
        self.assertFalse(payload["guardrails"]["changes_sharepoint_schema"])
        self.assertIn("vorsorgevollmacht-patientenverfuegung", review_items)
        vorsorge_gaps = review_items["vorsorgevollmacht-patientenverfuegung"]["sharepoint_field_gap_plan"]["gaps"]
        self.assertIn("choice_extension_plan", {gap["gap_type"] for gap in vorsorge_gaps})
        for item in review_items.values():
            self.assertEqual(item["sharepoint_field_gap_plan"]["mode"], "plan_only")
            self.assertEqual(item["bpmn_gap_plan"]["mode"], "plan_only")
            self.assertEqual(item["ontology_projection_patch_plan"]["mode"], "plan_only")
            self.assertTrue(item["sharepoint_field_gap_plan"]["owner_gate_required_before_apply"])
            self.assertTrue(item["bpmn_gap_plan"]["owner_gate_required_before_apply"])
            self.assertTrue(item["ontology_projection_patch_plan"]["owner_gate_required_before_apply"])
            self.assertFalse(item["sharepoint_field_gap_plan"]["writes_sharepoint"])
            self.assertFalse(item["ontology_projection_patch_plan"]["stores_document_full_text"])
            self.assertEqual(len(item["ontology_projection_patch_plan"]["patches"]), 3)

    def test_cli_first_wave_gap_review_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "first-wave-gap-review"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline-gap-review/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["first_wave_count"], 4)
        self.assertGreaterEqual(payload["summary"]["sharepoint_field_gap_count"], 4)
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_first_wave_gap_review_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "first-wave-gap-review",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline-gap-review/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_first_wave_gap_review_artifact_writes_redacted_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            json_output = temp_root / "first-wave-gap-review.redacted.json"
            markdown_output = temp_root / "first-wave-gap-review.redacted.md"
            payload = write_first_wave_bpmn_outline_gap_review_artifact(REPO_ROOT, json_output, markdown_output)
            validation = validate_first_wave_bpmn_outline_gap_review_artifact(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
            json_exists = json_output.is_file()
            markdown_exists = markdown_output.is_file()
            artifact_text = json_output.read_text(encoding="utf-8").lower()
            markdown_text = markdown_output.read_text(encoding="utf-8").lower()

        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline-gap-review-artifact/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["first_wave_count"], 4)
        self.assertEqual(len(payload["review_index"]), 4)
        self.assertTrue(payload["redaction"]["redacted"])
        self.assertFalse(payload["redaction"]["contains_real_matter_data"])
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertFalse(payload["guardrails"]["writes_sharepoint"])
        self.assertNotIn("planned_value", serialized)
        self.assertNotIn("planned_value", artifact_text)
        self.assertIn("first-wave bpmn outline gap review artifact", markdown_text)
        for attachment in payload["evidence_attachments"]:
            self.assertTrue(attachment["redacted"])
            self.assertFalse(attachment["required_for_release_readiness"])

    def test_cli_first_wave_gap_review_artifact_writes_redacted_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            json_output = temp_root / "first-wave-gap-review.redacted.json"
            markdown_output = temp_root / "first-wave-gap-review.redacted.md"
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "first-wave-gap-review-artifact",
                        "--output",
                        str(json_output),
                        "--markdown-output",
                        str(markdown_output),
                    ]
                )

            payload = json.loads(buffer.getvalue())
            json_exists = json_output.is_file()
            markdown_exists = markdown_output.is_file()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline-gap-review-artifact/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)

    def test_nac_cli_first_wave_gap_review_artifact_accepts_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            json_output = temp_root / "first-wave-gap-review.redacted.json"
            markdown_output = temp_root / "first-wave-gap-review.redacted.md"
            parser = nac_cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "first-wave-gap-review-artifact",
                    "--output",
                    str(json_output),
                    "--markdown-output",
                    str(markdown_output),
                    "--format",
                    "json",
                ]
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = args.func(args)

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-bpmn-outline-gap-review-artifact/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(payload["artifact_paths"]["json"].endswith(".redacted.json"))

    def test_ontology_scale_budget_covers_full_inventory(self) -> None:
        payload = build_ontology_scale_budget_smoke(REPO_ROOT)
        validation = validate_ontology_scale_budget_smoke(payload)
        summary = payload["summary"]
        thresholds = payload["thresholds"]

        self.assertEqual(payload["schema_version"], "nac.notarial-ontology-scale-budget/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(summary["business_case_count"], summary["bpmn_source_count"])
        self.assertGreaterEqual(summary["business_case_count"], 20)
        self.assertLessEqual(
            summary["max_projection_entities_estimate"],
            thresholds["max_projection_entities_per_business_case"],
        )
        self.assertLessEqual(
            summary["max_projection_edges_estimate"],
            thresholds["max_projection_edges_per_business_case"],
        )
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertFalse(payload["guardrails"]["writes_sharepoint"])
        self.assertFalse(payload["guardrails"]["runtime_ontology_reasoning_on_request_path_allowed"])
        for item in payload["budget_cases"]:
            self.assertNotEqual(item["projection_entities_pressure"], "over_budget")
            self.assertNotEqual(item["projection_edges_pressure"], "over_budget")
            self.assertTrue(item["bpmn_exists"])
            self.assertGreater(item["bpmn_flow_nodes"], 0)

    def test_cli_ontology_scale_budget_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "ontology-scale-budget"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-ontology-scale-budget/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertGreaterEqual(payload["summary"]["business_case_count"], 20)
        for forbidden in ("client_secret", "private_key", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_ontology_scale_budget_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "ontology-scale-budget",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.notarial-ontology-scale-budget/v0.1")
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
