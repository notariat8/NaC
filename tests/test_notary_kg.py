from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_cli import cli as nac_cli  # noqa: E402
from nac_m365_graph.graph_client import GraphHttpError
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
from notary_kg.first_wave_process_deep_model import (
    build_first_wave_process_deep_model,
    validate_first_wave_process_deep_model,
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
from notary_kg.process_ontology_schema_apply_binding import (
    build_process_ontology_sharepoint_schema_apply_binding,
)
from notary_kg.process_ontology_schema_apply_execution_contract import (
    build_process_ontology_sharepoint_schema_apply_execution_contract,
    validate_process_ontology_sharepoint_schema_apply_execution_contract,
)
from notary_kg.process_ontology_schema_apply_graph_dispatcher import (
    run_process_ontology_sharepoint_schema_apply_graph_dispatcher,
    validate_process_ontology_sharepoint_schema_apply_graph_dispatcher,
    write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact,
)
from notary_kg import process_ontology_schema_apply_graph_dispatcher as graph_dispatcher_module
from notary_kg.process_ontology_schema_apply_owner_gated_live_plan import (
    validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
    write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
)
from notary_kg.process_ontology_schema_apply_owner_gated_runner_contract import (
    validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract,
    write_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract,
)
from notary_kg.process_ontology_schema_apply_live_runner import (
    build_process_ontology_sharepoint_schema_apply_live_runner,
    validate_process_ontology_sharepoint_schema_apply_live_runner,
    write_process_ontology_sharepoint_schema_apply_live_runner,
)
from notary_kg.process_ontology_schema_apply_readiness import (
    build_process_ontology_sharepoint_schema_apply_readiness,
    validate_process_ontology_sharepoint_schema_apply_readiness,
)
from notary_kg.process_ontology_schema_apply_runner_dry_run import (
    build_process_ontology_sharepoint_schema_apply_runner_dry_run,
    validate_process_ontology_sharepoint_schema_apply_artifact_index,
    validate_process_ontology_sharepoint_schema_apply_live_readiness_gate,
    validate_process_ontology_sharepoint_schema_apply_runner_dry_run,
    validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
    write_process_ontology_sharepoint_schema_apply_artifact_index,
    write_process_ontology_sharepoint_schema_apply_live_readiness_gate,
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
)
from notary_kg.process_ontology_schema_gap import (
    build_process_ontology_sharepoint_schema_gap,
    validate_process_ontology_sharepoint_schema_gap,
)
from notary_kg.workflow_contract import build_workflow_contract_draft
from nac_gnotkg.views import build_cost_review_view


class FakeProcessOntologySchemaApplyGraphClient:
    def __init__(
        self,
        *,
        fail_readback_after_write: bool = False,
        fail_mutation: bool = False,
        required_checkpoint_path: Path | None = None,
    ) -> None:
        self.requests: list[tuple[str, str]] = []
        self.posts: list[tuple[str, dict]] = []
        self.patches: list[tuple[str, dict]] = []
        self.get_counts: dict[str, int] = {}
        self.choice_columns = {"Vorgangstyp", "CurrentPhase", "ProcessPhase", "RoleTemplate"}
        self.objects: dict[tuple[str, str, str], dict] = {}
        self.choice_state: dict[str, dict] = {}
        self.fail_readback_after_write = fail_readback_after_write
        self.fail_mutation = fail_mutation
        self.fail_next_readback = False
        self.required_checkpoint_path = required_checkpoint_path
        self.checkpoint_observed_before_first_request = False

    def get(self, path: str) -> dict:
        if not self.requests and self.required_checkpoint_path is not None:
            checkpoint = json.loads(self.required_checkpoint_path.read_text(encoding="utf-8"))
            self.checkpoint_observed_before_first_request = checkpoint["status"] == "RUNNING"
        self.requests.append(("GET", path))
        self.get_counts[path] = self.get_counts.get(path, 0) + 1
        if self.fail_next_readback:
            self.fail_next_readback = False
            raise GraphHttpError(503, "secret-response-body-must-not-be-stored")
        if "$filter=displayName" in path:
            return self._filter_response(path, "displayName")
        if "$filter=name" in path:
            name = self._quoted_filter_value(path)
            if name in self.choice_columns:
                column_id = f"fake-choice-column-{name}"
                choice = self.choice_state.setdefault(
                    column_id,
                    {"choices": ["LegacyCustom"], "allowTextEntry": False, "displayAs": "dropDownMenu"},
                )
                return {"value": [{"id": column_id, "name": name, "choice": dict(choice)}]}
            return self._filter_response(path, "name")
        if "/columns/fake-choice-column" in path or "/columns/fake-choice-" in path:
            column_id = path.split("/columns/", 1)[1].split("?", 1)[0]
            choice = self.choice_state.setdefault(
                column_id,
                {"choices": ["LegacyCustom"], "allowTextEntry": False, "displayAs": "dropDownMenu"},
            )
            return {"id": column_id, "choice": dict(choice)}
        return {"value": [{"id": "fake-existing"}]}

    def post(self, path: str, payload: dict) -> dict:
        self.requests.append(("POST", path))
        if self.fail_mutation:
            raise GraphHttpError(502, "secret-mutation-body-must-not-be-stored")
        self.posts.append((path, payload))
        object_id = f"fake-post-{len(self.posts)}"
        for key in ("displayName", "name"):
            if payload.get(key):
                self.objects[(path, key, str(payload[key]))] = {"id": object_id, key: payload[key]}
        if self.fail_readback_after_write:
            self.fail_next_readback = True
        return {"id": object_id}

    def patch(self, path: str, payload: dict) -> dict:
        self.requests.append(("PATCH", path))
        if self.fail_mutation:
            raise GraphHttpError(502, "secret-mutation-body-must-not-be-stored")
        self.patches.append((path, payload))
        object_id = path.split("/columns/", 1)[1].split("?", 1)[0] if "/columns/" in path else f"fake-patch-{len(self.patches)}"
        if isinstance(payload.get("choice"), dict):
            self.choice_state[object_id] = dict(payload["choice"])
        if self.fail_readback_after_write:
            self.fail_next_readback = True
        return {"id": object_id}

    def _filter_response(self, path: str, key: str) -> dict:
        base = path.split("?", 1)[0]
        value = self._quoted_filter_value(path)
        item = self.objects.get((base, key, value))
        return {"value": [dict(item)] if item else []}

    def _quoted_filter_value(self, path: str) -> str:
        marker = "%27"
        if marker in path:
            parts = path.split(marker)
            if len(parts) >= 3:
                from urllib.parse import unquote

                return unquote(parts[1])
        if "'" in path:
            parts = path.split("'")
            if len(parts) >= 3:
                from urllib.parse import unquote

                return unquote(parts[1])
        return "fake"


def _write_notary_team_01_schema_apply_gate(temp_root: Path) -> Path:
    artifact_root = temp_root / "artifacts"
    artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
    artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
    gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
    gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
        REPO_ROOT,
        artifact_json,
        artifact_md,
    )
    write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
        REPO_ROOT,
        artifact_root,
        gate_json,
        gate_md,
        workspace_ids=["notary_team_01"],
    )
    return gate_json


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

    def test_process_ontology_schema_apply_execution_contract_is_owner_gated(self) -> None:
        payload = build_process_ontology_sharepoint_schema_apply_execution_contract(REPO_ROOT)
        validation = validate_process_ontology_sharepoint_schema_apply_execution_contract(payload)
        summary = payload["summary"]
        boundary = payload["execution_boundary"]

        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-execution-contract/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(summary["workspace_count"], 2)
        self.assertEqual(summary["execution_phase_count"], 8)
        self.assertEqual(summary["workspace_apply_unit_count"], 68)
        self.assertEqual(summary["mutating_operation_count"], 68)
        self.assertTrue(summary["owner_gate_required_before_live_apply"])
        self.assertEqual(summary["live_apply_contract_status"], "READY_FOR_OWNER_GATED_EXECUTION")
        self.assertTrue(boundary["future_runner_must_require_owner_approval"])
        self.assertTrue(boundary["future_runner_must_require_explicit_live_flag"])
        self.assertIn("--execute-live-schema-apply", boundary["future_runner_required_flags"])
        self.assertFalse(boundary["executes_graph_requests"])
        self.assertFalse(boundary["writes_sharepoint"])
        self.assertFalse(boundary["changes_sharepoint_schema"])
        self.assertFalse(payload["permission_gate"]["delegated_user_context_allowed"])
        self.assertTrue(payload["stop_rules"]["stop_on_first_failed_preflight"])
        self.assertFalse(payload["stop_rules"]["automatic_rollback_allowed"])
        self.assertFalse(payload["evidence_contract"]["raw_graph_response_allowed"])

    def test_cli_process_ontology_schema_apply_execution_contract_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                    "process-ontology-schema-apply-execution-contract",
                ]
            )

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-execution-contract/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["workspace_apply_unit_count"], 68)
        for forbidden in ("client_secret", "private_key", "authorization", "bearer ", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_process_ontology_schema_apply_execution_contract_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "process-ontology-schema-apply-execution-contract",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-execution-contract/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")

    def test_process_ontology_schema_apply_runner_dry_run_exposes_planned_requests(self) -> None:
        payload = build_process_ontology_sharepoint_schema_apply_runner_dry_run(REPO_ROOT)
        validation = validate_process_ontology_sharepoint_schema_apply_runner_dry_run(payload)
        summary = payload["summary"]
        first_step = payload["dry_run_steps"][0]

        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-runner-dry-run/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(summary["workspace_count"], 2)
        self.assertEqual(summary["dry_run_step_count"], 68)
        self.assertEqual(summary["preflight_request_count"], 68)
        self.assertEqual(summary["future_mutation_request_count"], 68)
        self.assertEqual(summary["readback_request_count"], 68)
        self.assertFalse(summary["executes_graph_requests"])
        self.assertFalse(summary["writes_sharepoint"])
        self.assertFalse(summary["changes_sharepoint_schema"])
        self.assertEqual(first_step["mode"], "dry_run_only")
        self.assertFalse(first_step["executes_graph_requests"])
        self.assertIn("path_template", first_step["preflight_request"])
        self.assertIn("body_shape", first_step["future_mutation_request"])
        self.assertFalse(payload["evidence_plan"]["raw_graph_response_allowed"])

    def test_cli_process_ontology_schema_apply_runner_dry_run_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "--format",
                    "json",
                    "process-ontology-schema-apply-runner-dry-run",
                ]
            )

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-runner-dry-run/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["dry_run_step_count"], 68)
        for forbidden in ("client_secret", "private_key", "authorization", "bearer ", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_process_ontology_schema_apply_runner_dry_run_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "process-ontology-schema-apply-runner-dry-run",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-runner-dry-run/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")

    def test_process_ontology_schema_apply_runner_dry_run_artifact_writes_redacted_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            json_output = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            markdown_output = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            payload = write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                json_output,
                markdown_output,
            )
            validation = validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
            json_exists = json_output.is_file()
            markdown_exists = markdown_output.is_file()
            artifact_text = json_output.read_text(encoding="utf-8").lower()
            markdown_text = markdown_output.read_text(encoding="utf-8").lower()

        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-runner-dry-run-artifact/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["dry_run_step_count"], 68)
        self.assertEqual(len(payload["dry_run_step_index"]), 68)
        self.assertTrue(payload["redaction"]["redacted"])
        self.assertFalse(payload["redaction"]["contains_site_ids"])
        self.assertFalse(payload["redaction"]["contains_request_headers"])
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertFalse(payload["guardrails"]["writes_sharepoint"])
        self.assertNotIn("funktion8.sharepoint.com", serialized)
        self.assertNotIn('"headers"', artifact_text)
        self.assertIn("process ontology sharepoint schema apply runner dry-run artifact", markdown_text)
        for attachment in payload["evidence_attachments"]:
            self.assertTrue(attachment["redacted"])
            self.assertTrue(attachment["required_for_live_apply_readiness"])

    def test_cli_process_ontology_schema_apply_runner_dry_run_artifact_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            json_output = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            markdown_output = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "process-ontology-schema-apply-runner-dry-run-artifact",
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
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-runner-dry-run-artifact/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)

    def test_nac_cli_process_ontology_schema_apply_runner_dry_run_artifact_accepts_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            json_output = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            markdown_output = temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            parser = nac_cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "process-ontology-schema-apply-runner-dry-run-artifact",
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
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-runner-dry-run-artifact/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")

    def test_process_ontology_schema_apply_artifact_index_lists_redacted_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            index_json = temp_root / "process-ontology-schema-apply-artifact-index.redacted.json"
            index_md = temp_root / "process-ontology-schema-apply-artifact-index.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            payload = write_process_ontology_sharepoint_schema_apply_artifact_index(
                REPO_ROOT,
                artifact_root,
                index_json,
                index_md,
                ensure_default_artifact=False,
            )
            validation = validate_process_ontology_sharepoint_schema_apply_artifact_index(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
            json_exists = index_json.is_file()
            markdown_exists = index_md.is_file()

        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-artifact-index/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["artifact_count"], 1)
        self.assertEqual(payload["summary"]["total_dry_run_step_count"], 68)
        self.assertEqual(payload["artifacts"][0]["dry_run_step_count"], 68)
        self.assertTrue(payload["artifacts"][0]["required_for_live_apply_readiness"])
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertFalse(payload["guardrails"]["writes_sharepoint"])
        self.assertNotIn("funktion8.sharepoint.com", serialized)
        self.assertNotIn('"headers"', serialized)

    def test_cli_process_ontology_schema_apply_artifact_index_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            index_json = temp_root / "process-ontology-schema-apply-artifact-index.redacted.json"
            index_md = temp_root / "process-ontology-schema-apply-artifact-index.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "process-ontology-schema-apply-artifact-index",
                        "--artifact-root",
                        str(artifact_root),
                        "--output",
                        str(index_json),
                        "--markdown-output",
                        str(index_md),
                        "--no-ensure-default-artifact",
                    ]
                )

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-artifact-index/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["artifact_count"], 1)

    def test_nac_cli_process_ontology_schema_apply_artifact_index_accepts_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            index_json = temp_root / "process-ontology-schema-apply-artifact-index.redacted.json"
            index_md = temp_root / "process-ontology-schema-apply-artifact-index.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            parser = nac_cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "process-ontology-schema-apply-artifact-index",
                    "--artifact-root",
                    str(artifact_root),
                    "--output",
                    str(index_json),
                    "--markdown-output",
                    str(index_md),
                    "--no-ensure-default-artifact",
                    "--format",
                    "json",
                ]
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = args.func(args)

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-artifact-index/v0.1")
        self.assertEqual(payload["status"], "PASSED")

    def test_process_ontology_schema_apply_live_readiness_gate_requires_artifacts_and_owner_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            index_json = artifact_root / "process-ontology-schema-apply-artifact-index.redacted.json"
            index_md = artifact_root / "process-ontology-schema-apply-artifact-index.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            payload = write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_json,
                gate_md,
                workspace_ids=["notary_team_01"],
                ensure_default_artifacts=False,
            )
            validation = validate_process_ontology_sharepoint_schema_apply_live_readiness_gate(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
            json_exists = gate_json.is_file()
            markdown_exists = gate_md.is_file()
            index_json_exists = index_json.is_file()
            index_md_exists = index_md.is_file()

        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-live-readiness-gate/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["check_count"], 7)
        self.assertEqual(payload["summary"]["approved_workspace_count"], 1)
        self.assertEqual(payload["summary"]["approved_workspace_apply_unit_count"], 34)
        self.assertEqual(payload["summary"]["blocked_check_count"], 0)
        self.assertEqual(payload["summary"]["workspace_apply_unit_count"], 68)
        self.assertEqual(payload["summary"]["dry_run_step_count"], 68)
        self.assertEqual(payload["summary"]["artifact_count"], 1)
        self.assertTrue(payload["summary"]["owner_gate_required_before_live_apply"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["writes_sharepoint"])
        self.assertFalse(payload["summary"]["changes_sharepoint_schema"])
        self.assertEqual(
            payload["next_batch"]["owner_gate_required_before"],
            ["graph_live_write", "sharepoint_schema_apply", "runner_live_execution"],
        )
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)
        self.assertTrue(index_json_exists)
        self.assertTrue(index_md_exists)
        self.assertIn("dry_run_artifact_index", payload["evidence"])
        self.assertEqual(len(payload["evidence"]["indexed_artifacts"]), 1)
        self.assertNotIn("funktion8.sharepoint.com", serialized)
        self.assertNotIn('"headers"', serialized)

    def test_process_ontology_schema_apply_live_readiness_gate_rejects_inconsistent_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gate_json = _write_notary_team_01_schema_apply_gate(Path(temp_dir))
            payload = json.loads(gate_json.read_text(encoding="utf-8"))
            payload["checks"][0]["status"] = "BLOCKED"
            payload["blockers"] = []
            payload["summary"]["blocked_check_count"] = 0
            validation = validate_process_ontology_sharepoint_schema_apply_live_readiness_gate(payload)
            empty = json.loads(gate_json.read_text(encoding="utf-8"))
            empty["checks"] = []
            empty["blockers"] = []
            empty["summary"]["check_count"] = 0
            empty["summary"]["passed_check_count"] = 0
            empty["summary"]["blocked_check_count"] = 0
            empty_validation = validate_process_ontology_sharepoint_schema_apply_live_readiness_gate(empty)

        self.assertEqual(validation.status, "FAILED")
        self.assertIn("blockers must exactly match all non-passing checks", validation.errors)
        self.assertEqual(empty_validation.status, "FAILED")
        self.assertIn(
            "live readiness gate must include every required check exactly once and in canonical order",
            empty_validation.errors,
        )

    def test_process_ontology_schema_apply_binding_covers_permission_and_readiness_state(self) -> None:
        baseline = build_process_ontology_sharepoint_schema_apply_binding(REPO_ROOT, ["notary_team_01"])
        readiness = build_process_ontology_sharepoint_schema_apply_readiness(REPO_ROOT)
        changed = json.loads(json.dumps(readiness))
        changed["status"] = "FAILED"
        changed["permission_readiness"]["permission_present_in_provisioned_state"] = False
        changed["errors"] = ["permission readiness changed"]

        with patch(
            "notary_kg.process_ontology_schema_apply_binding.build_process_ontology_sharepoint_schema_apply_readiness",
            return_value=changed,
        ):
            altered = build_process_ontology_sharepoint_schema_apply_binding(REPO_ROOT, ["notary_team_01"])

        self.assertNotEqual(baseline["workspace_readiness_sha256"], altered["workspace_readiness_sha256"])
        self.assertNotEqual(baseline["binding_sha256"], altered["binding_sha256"])

    def test_cli_process_ontology_schema_apply_live_readiness_gate_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "process-ontology-schema-apply-live-readiness-gate",
                        "--workspace-id",
                        "notary_team_01",
                        "--artifact-root",
                        str(artifact_root),
                        "--output",
                        str(gate_json),
                        "--markdown-output",
                        str(gate_md),
                        "--no-ensure-default-artifacts",
                    ]
                )

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-live-readiness-gate/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["artifact_count"], 1)

    def test_nac_cli_process_ontology_schema_apply_live_readiness_gate_accepts_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            parser = nac_cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "process-ontology-schema-apply-live-readiness-gate",
                    "--workspace-id",
                    "notary_team_01",
                    "--artifact-root",
                    str(artifact_root),
                    "--output",
                    str(gate_json),
                    "--markdown-output",
                    str(gate_md),
                    "--no-ensure-default-artifacts",
                    "--format",
                    "json",
                ]
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = args.func(args)

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-live-readiness-gate/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["artifact_count"], 1)

    def test_process_ontology_schema_apply_owner_gated_live_plan_requires_owner_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            plan_json = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.json"
            plan_md = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            payload = write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
                REPO_ROOT,
                artifact_root,
                plan_json,
                plan_md,
                ensure_default_artifacts=False,
            )
            validation = validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
            json_exists = plan_json.is_file()
            markdown_exists = plan_md.is_file()

        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-owner-gated-live-plan/v0.1",
        )
        self.assertEqual(payload["status"], "READY_FOR_OWNER_APPROVAL")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["workspace_count"], 2)
        self.assertEqual(payload["summary"]["phase_count"], 8)
        self.assertEqual(payload["summary"]["planned_live_step_count"], 68)
        self.assertEqual(payload["summary"]["planned_preflight_count"], 68)
        self.assertEqual(payload["summary"]["planned_mutation_count"], 68)
        self.assertEqual(payload["summary"]["planned_readback_count"], 68)
        self.assertTrue(payload["summary"]["owner_gate_required_now"])
        self.assertTrue(payload["owner_gate"]["blocked_without_owner_approval"])
        self.assertIn("--owner-approved", payload["owner_gate"]["required_flags"])
        self.assertIn("--execute-live-schema-apply", payload["owner_gate"]["required_flags"])
        self.assertTrue(payload["future_runner_contract"]["command_exists_now"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["writes_sharepoint"])
        self.assertFalse(payload["summary"]["changes_sharepoint_schema"])
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)
        self.assertNotIn("funktion8.sharepoint.com", serialized)
        self.assertNotIn('"headers"', serialized)

    def test_cli_process_ontology_schema_apply_owner_gated_live_plan_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            plan_json = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.json"
            plan_md = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "process-ontology-schema-apply-owner-gated-live-plan",
                        "--artifact-root",
                        str(artifact_root),
                        "--output",
                        str(plan_json),
                        "--markdown-output",
                        str(plan_md),
                        "--no-ensure-default-artifacts",
                    ]
                )

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-owner-gated-live-plan/v0.1",
        )
        self.assertEqual(payload["status"], "READY_FOR_OWNER_APPROVAL")

    def test_nac_cli_process_ontology_schema_apply_owner_gated_live_plan_accepts_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            plan_json = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.json"
            plan_md = temp_root / "process-ontology-schema-apply-owner-gated-live-plan.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            parser = nac_cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "process-ontology-schema-apply-owner-gated-live-plan",
                    "--artifact-root",
                    str(artifact_root),
                    "--output",
                    str(plan_json),
                    "--markdown-output",
                    str(plan_md),
                    "--no-ensure-default-artifacts",
                    "--format",
                    "json",
                ]
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = args.func(args)

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-owner-gated-live-plan/v0.1",
        )
        self.assertEqual(payload["status"], "READY_FOR_OWNER_APPROVAL")
        self.assertEqual(payload["summary"]["planned_live_step_count"], 68)

    def test_process_ontology_schema_apply_owner_gated_runner_contract_exposes_step_sequence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            contract_json = temp_root / "process-ontology-schema-apply-owner-gated-runner-contract.redacted.json"
            contract_md = temp_root / "process-ontology-schema-apply-owner-gated-runner-contract.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            payload = write_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
                REPO_ROOT,
                artifact_root,
                contract_json,
                contract_md,
                ensure_default_artifacts=False,
            )
            validation = validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
            json_exists = contract_json.is_file()
            markdown_exists = contract_md.is_file()

        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-owner-gated-runner-contract/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["runner_step_count"], 68)
        self.assertEqual(payload["summary"]["preflight_count"], 68)
        self.assertEqual(payload["summary"]["mutation_count"], 68)
        self.assertEqual(payload["summary"]["readback_count"], 68)
        self.assertTrue(payload["runner_interface"]["command_implemented_now"])
        self.assertEqual(payload["runner_interface"]["command"], "nac kg process-ontology-schema-apply-live")
        self.assertIn("--owner-approved", payload["runner_interface"]["required_flags"])
        self.assertTrue(payload["stop_rules"]["stop_before_first_mutation_if_owner_approval_missing"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["writes_sharepoint"])
        self.assertFalse(payload["summary"]["changes_sharepoint_schema"])
        self.assertTrue(json_exists)
        self.assertTrue(markdown_exists)
        self.assertNotIn("funktion8.sharepoint.com", serialized)
        self.assertNotIn('"headers"', serialized)

    def test_cli_process_ontology_schema_apply_owner_gated_runner_contract_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            contract_json = temp_root / "process-ontology-schema-apply-owner-gated-runner-contract.redacted.json"
            contract_md = temp_root / "process-ontology-schema-apply-owner-gated-runner-contract.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "process-ontology-schema-apply-owner-gated-runner-contract",
                        "--artifact-root",
                        str(artifact_root),
                        "--output",
                        str(contract_json),
                        "--markdown-output",
                        str(contract_md),
                        "--no-ensure-default-artifacts",
                    ]
                )

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-owner-gated-runner-contract/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")

    def test_nac_cli_process_ontology_schema_apply_owner_gated_runner_contract_accepts_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            contract_json = temp_root / "process-ontology-schema-apply-owner-gated-runner-contract.redacted.json"
            contract_md = temp_root / "process-ontology-schema-apply-owner-gated-runner-contract.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            parser = nac_cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "process-ontology-schema-apply-owner-gated-runner-contract",
                    "--artifact-root",
                    str(artifact_root),
                    "--output",
                    str(contract_json),
                    "--markdown-output",
                    str(contract_md),
                    "--no-ensure-default-artifacts",
                    "--format",
                    "json",
                ]
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = args.func(args)

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            payload["schema_version"],
            "nac.process-ontology-sharepoint-schema-apply-owner-gated-runner-contract/v0.1",
        )
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["runner_step_count"], 68)

    def test_process_ontology_schema_apply_live_runner_blocks_without_owner_gate(self) -> None:
        payload = build_process_ontology_sharepoint_schema_apply_live_runner(
            REPO_ROOT,
            live_readiness_gate=Path("missing-live-readiness-gate.redacted.json"),
            ensure_default_artifacts=False,
        )
        validation = validate_process_ontology_sharepoint_schema_apply_live_runner(payload)

        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-live-runner/v0.1")
        self.assertEqual(payload["status"], "BLOCKED")
        self.assertEqual(validation.status, "PASSED")
        self.assertIn("missing --owner-approved", payload["owner_gate"]["missing_or_blocking"])
        self.assertIn("missing --execute-live-schema-apply", payload["owner_gate"]["missing_or_blocking"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["writes_sharepoint"])
        self.assertFalse(payload["summary"]["changes_sharepoint_schema"])

    def test_process_ontology_schema_apply_live_runner_blocks_non_pilot_workspace(self) -> None:
        payload = build_process_ontology_sharepoint_schema_apply_live_runner(
            REPO_ROOT,
            live_readiness_gate=Path("missing-live-readiness-gate.redacted.json"),
            workspace_id="notary_team_02",
            correlation_id="non-pilot-workspace",
            owner_approval_reference="owner-approval-non-pilot",
            reason="Negative workspace allowlist test",
            owner_approved=True,
            execute_live_schema_apply=True,
            write_redacted_evidence=True,
            ensure_default_artifacts=False,
        )

        self.assertEqual(payload["status"], "BLOCKED")
        self.assertIn(
            "unsupported --workspace-id; only notary_team_01 is enabled for live schema apply",
            payload["owner_gate"]["missing_or_blocking"],
        )

    def test_process_ontology_schema_apply_live_runner_accepts_full_owner_gate_surface(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            runner_json = temp_root / "process-ontology-schema-apply-live.redacted.json"
            runner_md = temp_root / "process-ontology-schema-apply-live.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_json,
                gate_md,
                workspace_ids=["notary_team_01"],
            )
            payload = write_process_ontology_sharepoint_schema_apply_live_runner(
                REPO_ROOT,
                artifact_root,
                runner_json,
                runner_md,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-live-runner-test",
                owner_approval_reference="approval-raw-marker-must-not-persist",
                reason="reason-raw-marker-must-not-persist",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                ensure_default_artifacts=False,
            )
            validation = validate_process_ontology_sharepoint_schema_apply_live_runner(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()
            runner_json_exists = runner_json.is_file()
            runner_md_exists = runner_md.is_file()

        self.assertEqual(payload["status"], "READY_FOR_GRAPH_REST_DISPATCH")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["runner_step_count"], 34)
        self.assertTrue(payload["summary"]["owner_gate_satisfied"])
        self.assertFalse(payload["summary"]["executes_graph_requests"])
        self.assertFalse(payload["summary"]["writes_sharepoint"])
        self.assertFalse(payload["summary"]["changes_sharepoint_schema"])
        self.assertTrue(payload["guardrails"]["requires_separate_graph_dispatcher"])
        self.assertTrue(runner_json_exists)
        self.assertTrue(runner_md_exists)
        self.assertNotIn("approval-raw-marker-must-not-persist", serialized)
        self.assertNotIn("reason-raw-marker-must-not-persist", serialized)
        self.assertNotIn("funktion8.sharepoint.com", serialized)
        self.assertNotIn('"headers"', serialized)

    def test_cli_process_ontology_schema_apply_live_writes_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            runner_json = temp_root / "process-ontology-schema-apply-live.redacted.json"
            runner_md = temp_root / "process-ontology-schema-apply-live.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_json,
                gate_md,
                workspace_ids=["notary_team_01"],
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "process-ontology-schema-apply-live",
                        "--workspace-id",
                        "notary_team_01",
                        "--artifact-root",
                        str(artifact_root),
                        "--live-readiness-gate",
                        str(gate_json),
                        "--correlation-id",
                        "nac-schema-apply-live-cli-test",
                        "--owner-approval-reference",
                        "owner-approval-cli-test",
                        "--reason",
                        "Safety rework CLI test",
                        "--owner-approved",
                        "--execute-live-schema-apply",
                        "--write-redacted-evidence",
                        "--output",
                        str(runner_json),
                        "--markdown-output",
                        str(runner_md),
                        "--no-ensure-default-artifacts",
                    ]
                )

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-live-runner/v0.1")
        self.assertEqual(payload["status"], "READY_FOR_GRAPH_REST_DISPATCH")
        self.assertEqual(payload["summary"]["runner_step_count"], 34)

    def test_nac_cli_process_ontology_schema_apply_live_accepts_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            runner_json = temp_root / "process-ontology-schema-apply-live.redacted.json"
            runner_md = temp_root / "process-ontology-schema-apply-live.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_json,
                gate_md,
                workspace_ids=["notary_team_01"],
            )
            parser = nac_cli.build_parser()
            args = parser.parse_args(
                [
                    "--repo-root",
                    str(REPO_ROOT),
                    "kg",
                    "process-ontology-schema-apply-live",
                    "--workspace-id",
                    "notary_team_01",
                    "--artifact-root",
                    str(artifact_root),
                    "--live-readiness-gate",
                    str(gate_json),
                    "--correlation-id",
                    "nac-schema-apply-live-nac-cli-test",
                    "--owner-approval-reference",
                    "owner-approval-nac-cli-test",
                    "--reason",
                    "Safety rework NaC CLI test",
                    "--owner-approved",
                    "--execute-live-schema-apply",
                    "--write-redacted-evidence",
                    "--output",
                    str(runner_json),
                    "--markdown-output",
                    str(runner_md),
                    "--no-ensure-default-artifacts",
                    "--format",
                    "json",
                ]
            )
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = args.func(args)

            payload = json.loads(buffer.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-live-runner/v0.1")
        self.assertEqual(payload["status"], "READY_FOR_GRAPH_REST_DISPATCH")
        self.assertEqual(payload["summary"]["runner_step_count"], 34)

    def test_cli_process_ontology_schema_apply_live_dispatch_forwards_owner_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            gate_json = temp_root / "gate.redacted.json"
            output_json = temp_root / "dispatch.redacted.json"
            output_md = temp_root / "dispatch.redacted.md"
            buffer = io.StringIO()
            with (
                patch("notary_kg.cli.runtime_token_provider_from_env", return_value=object()),
                patch("notary_kg.cli.GraphRestClient", return_value=object()),
                patch(
                    "notary_kg.cli.write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact",
                    return_value={"status": "PASSED"},
                ) as writer,
                redirect_stdout(buffer),
            ):
                exit_code = kg_main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--format",
                        "json",
                        "process-ontology-schema-apply-live-dispatch",
                        "--workspace-id",
                        "notary_team_01",
                        "--live-readiness-gate",
                        str(gate_json),
                        "--correlation-id",
                        "dispatch-cli-forwarding",
                        "--owner-approval-reference",
                        "approval-cli-forwarding",
                        "--reason",
                        "Dispatch CLI forwarding test",
                        "--owner-approved",
                        "--execute-live-schema-apply",
                        "--write-redacted-evidence",
                        "--output",
                        str(output_json),
                        "--markdown-output",
                        str(output_md),
                    ]
                )

        self.assertEqual(exit_code, 0)
        call = writer.call_args
        self.assertEqual(call.kwargs["workspace_id"], "notary_team_01")
        self.assertEqual(call.kwargs["owner_approval_reference"], "approval-cli-forwarding")
        self.assertEqual(call.kwargs["reason"], "Dispatch CLI forwarding test")
        self.assertEqual(call.kwargs["live_readiness_gate"], gate_json)

    def test_nac_cli_process_ontology_schema_apply_live_dispatch_forwards_owner_gate(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "process-ontology-schema-apply-live-dispatch",
                "--workspace-id",
                "notary_team_01",
                "--live-readiness-gate",
                "gate.redacted.json",
                "--correlation-id",
                "nac-dispatch-cli-forwarding",
                "--owner-approval-reference",
                "nac-approval-cli-forwarding",
                "--reason",
                "Central NaC dispatch forwarding test",
                "--owner-approved",
                "--execute-live-schema-apply",
                "--write-redacted-evidence",
                "--format",
                "json",
            ]
        )

        with patch.object(nac_cli, "notary_kg_main", return_value=0) as forwarded:
            exit_code = args.func(args)

        self.assertEqual(exit_code, 0)
        argv = forwarded.call_args.args[0]
        self.assertEqual(argv[argv.index("--workspace-id") + 1], "notary_team_01")
        self.assertEqual(argv[argv.index("--owner-approval-reference") + 1], "nac-approval-cli-forwarding")
        self.assertEqual(argv[argv.index("--reason") + 1], "Central NaC dispatch forwarding test")
        self.assertIn("--owner-approved", argv)
        self.assertIn("--execute-live-schema-apply", argv)
        self.assertIn("--write-redacted-evidence", argv)

    def test_process_ontology_schema_apply_graph_dispatcher_runs_with_fake_client(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            dispatch_json = temp_root / "process-ontology-schema-apply-graph-dispatcher.redacted.json"
            dispatch_md = temp_root / "process-ontology-schema-apply-graph-dispatcher.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_json,
                gate_md,
                workspace_ids=["notary_team_01"],
            )
            client = FakeProcessOntologySchemaApplyGraphClient(required_checkpoint_path=dispatch_json)
            payload = run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                client,
                REPO_ROOT,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-dispatcher-test",
                owner_approval_reference="owner-approval-dispatcher-test",
                reason="Safety rework dispatcher test",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                evidence_json_output=dispatch_json,
                evidence_markdown_output=dispatch_md,
            )
            validation = validate_process_ontology_sharepoint_schema_apply_graph_dispatcher(payload)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(payload["schema_version"], "nac.process-ontology-sharepoint-schema-apply-graph-dispatcher/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(payload["summary"]["dispatched_step_count"], 34)
        self.assertGreaterEqual(payload["summary"]["mutation_request_count"], 1)
        self.assertTrue(client.checkpoint_observed_before_first_request)
        self.assertEqual({step["workspaceId"] for step in payload["dispatch_steps"]}, {"notary_team_01"})
        self.assertTrue(all("LegacyCustom" in patch[1]["choice"]["choices"] for patch in client.patches))
        self.assertTrue(all(patch[1]["choice"]["allowTextEntry"] is False for patch in client.patches))
        self.assertTrue(all(patch[1]["choice"]["displayAs"] == "dropDownMenu" for patch in client.patches))
        self.assertTrue(payload["summary"]["executed_graph_requests"])
        self.assertTrue(payload["summary"]["executed_graph_writes"])
        self.assertTrue(payload["guardrails"]["graph_rest_only"])
        self.assertFalse(payload["privacy"]["storesRawGraphPath"])
        self.assertFalse(payload["privacy"]["storesRawGraphResponse"])
        self.assertNotIn("funktion8.sharepoint.com", serialized)
        self.assertNotIn('"authorization"', serialized)

    def test_process_ontology_schema_apply_graph_dispatcher_writes_redacted_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            artifact_json = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json"
            artifact_md = artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md"
            gate_json = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.json"
            gate_md = temp_root / "process-ontology-schema-apply-live-readiness-gate.redacted.md"
            dispatch_json = temp_root / "process-ontology-schema-apply-graph-dispatcher.redacted.json"
            dispatch_md = temp_root / "process-ontology-schema-apply-graph-dispatcher.redacted.md"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_json,
                artifact_md,
            )
            write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_json,
                gate_md,
                workspace_ids=["notary_team_01"],
            )
            payload = write_process_ontology_sharepoint_schema_apply_graph_dispatcher_artifact(
                FakeProcessOntologySchemaApplyGraphClient(),
                REPO_ROOT,
                dispatch_json,
                dispatch_md,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-dispatcher-artifact-test",
                owner_approval_reference="owner-approval-dispatcher-artifact-test",
                reason="Safety rework dispatcher artifact test",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                max_steps=2,
            )
            dispatch_json_exists = dispatch_json.is_file()
            dispatch_md_exists = dispatch_md.is_file()

        self.assertEqual(payload["status"], "PARTIAL")
        self.assertEqual(payload["summary"]["dispatched_step_count"], 2)
        self.assertTrue(dispatch_json_exists)
        self.assertTrue(dispatch_md_exists)

    def test_process_ontology_schema_apply_graph_dispatcher_rejects_max_steps_at_or_above_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            gate_json = _write_notary_team_01_schema_apply_gate(temp_root)
            client = FakeProcessOntologySchemaApplyGraphClient()

            with self.assertRaisesRegex(ValueError, "max_steps must be lower"):
                run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                    client,
                    REPO_ROOT,
                    live_readiness_gate=gate_json,
                    workspace_id="notary_team_01",
                    correlation_id="nac-schema-apply-invalid-max-steps",
                    owner_approval_reference="owner-approval-invalid-max-steps",
                    reason="Reject full apply through max steps",
                    owner_approved=True,
                    execute_live_schema_apply=True,
                    write_redacted_evidence=True,
                    evidence_json_output=temp_root / "invalid-max-steps.redacted.json",
                    evidence_markdown_output=temp_root / "invalid-max-steps.redacted.md",
                    max_steps=34,
                )

        self.assertEqual(client.requests, [])

    def test_process_ontology_schema_apply_graph_dispatcher_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gate_json = _write_notary_team_01_schema_apply_gate(Path(temp_dir))
            client = FakeProcessOntologySchemaApplyGraphClient()
            first = run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                client,
                REPO_ROOT,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-idempotence-first",
                owner_approval_reference="owner-approval-idempotence",
                reason="First idempotence pass",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                evidence_json_output=Path(temp_dir) / "dispatcher.redacted.json",
                evidence_markdown_output=Path(temp_dir) / "dispatcher.redacted.md",
            )
            write_count = len(client.posts) + len(client.patches)
            second = run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                client,
                REPO_ROOT,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-idempotence-second",
                owner_approval_reference="owner-approval-idempotence",
                reason="Second idempotence pass",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                evidence_json_output=Path(temp_dir) / "dispatcher.redacted.json",
                evidence_markdown_output=Path(temp_dir) / "dispatcher.redacted.md",
            )

        self.assertEqual(first["status"], "PASSED")
        self.assertEqual(second["status"], "PASSED")
        self.assertEqual(second["completion"], "NO_CHANGES")
        self.assertEqual(second["summary"]["mutation_request_count"], 0)
        self.assertEqual(second["summary"]["skipped_mutation_count"], 34)
        self.assertEqual(len(client.posts) + len(client.patches), write_count)

    def test_process_ontology_schema_apply_graph_dispatcher_tracks_post_write_readback_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gate_json = _write_notary_team_01_schema_apply_gate(Path(temp_dir))
            client = FakeProcessOntologySchemaApplyGraphClient(fail_readback_after_write=True)
            payload = run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                client,
                REPO_ROOT,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-readback-failure",
                owner_approval_reference="owner-approval-readback-failure",
                reason="Readback failure tracking test",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                evidence_json_output=Path(temp_dir) / "dispatcher.redacted.json",
                evidence_markdown_output=Path(temp_dir) / "dispatcher.redacted.md",
            )
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["summary"]["confirmed_mutation_count"], 1)
        self.assertTrue(payload["summary"]["writes_may_have_occurred"])
        self.assertEqual(payload["dispatch_steps"][0]["mutationOutcome"], "CONFIRMED")
        self.assertEqual(payload["dispatch_steps"][0]["error"]["httpStatus"], 503)
        self.assertNotIn("secret-response-body-must-not-be-stored", serialized)

    def test_process_ontology_schema_apply_graph_dispatcher_retains_possible_write_on_evidence_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            gate_json = _write_notary_team_01_schema_apply_gate(temp_root)
            dispatch_json = temp_root / "dispatcher.redacted.json"
            dispatch_md = temp_root / "dispatcher.redacted.md"
            client = FakeProcessOntologySchemaApplyGraphClient()
            original_write = graph_dispatcher_module._atomic_write_text
            write_count = 0

            def fail_after_first_graph_write(path: Path, content: str) -> None:
                nonlocal write_count
                write_count += 1
                if write_count == 5:
                    raise OSError("synthetic evidence writer failure")
                original_write(path, content)

            with (
                patch.object(
                    graph_dispatcher_module,
                    "_atomic_write_text",
                    side_effect=fail_after_first_graph_write,
                ),
                self.assertRaisesRegex(OSError, "synthetic evidence writer failure"),
            ):
                run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                    client,
                    REPO_ROOT,
                    live_readiness_gate=gate_json,
                    workspace_id="notary_team_01",
                    correlation_id="nac-schema-apply-evidence-failure",
                    owner_approval_reference="owner-approval-evidence-failure",
                    reason="Evidence failure tracking test",
                    owner_approved=True,
                    execute_live_schema_apply=True,
                    write_redacted_evidence=True,
                    evidence_json_output=dispatch_json,
                    evidence_markdown_output=dispatch_md,
                )
            persisted = json.loads(dispatch_json.read_text(encoding="utf-8"))

        self.assertEqual(len(client.posts) + len(client.patches), 1)
        self.assertEqual(persisted["status"], "RUNNING")
        self.assertEqual(persisted["summary"]["possible_mutation_count"], 1)
        self.assertTrue(persisted["summary"]["writes_may_have_occurred"])
        self.assertTrue(persisted["dispatch_steps"][0]["mutationIntentPersisted"])

    def test_process_ontology_schema_apply_graph_dispatcher_redacts_uncertain_mutation_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gate_json = _write_notary_team_01_schema_apply_gate(Path(temp_dir))
            payload = run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                FakeProcessOntologySchemaApplyGraphClient(fail_mutation=True),
                REPO_ROOT,
                live_readiness_gate=gate_json,
                workspace_id="notary_team_01",
                correlation_id="nac-schema-apply-mutation-failure",
                owner_approval_reference="owner-approval-mutation-failure",
                reason="Mutation failure redaction test",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                evidence_json_output=Path(temp_dir) / "dispatcher.redacted.json",
                evidence_markdown_output=Path(temp_dir) / "dispatcher.redacted.md",
            )
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertEqual(payload["status"], "FAILED")
        self.assertEqual(payload["summary"]["possible_mutation_count"], 1)
        self.assertTrue(payload["summary"]["writes_may_have_occurred"])
        self.assertEqual(payload["dispatch_steps"][0]["mutationOutcome"], "POSSIBLE")
        self.assertEqual(payload["dispatch_steps"][0]["error"]["httpStatus"], 502)
        self.assertNotIn("secret-mutation-body-must-not-be-stored", serialized)

    def test_process_ontology_schema_apply_graph_dispatcher_rejects_tampered_gate_before_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            gate_json = _write_notary_team_01_schema_apply_gate(Path(temp_dir))
            gate = json.loads(gate_json.read_text(encoding="utf-8"))
            gate["approval_binding"]["apply_plan_sha256"] = "0" * 64
            gate_json.write_text(json.dumps(gate), encoding="utf-8")
            client = FakeProcessOntologySchemaApplyGraphClient()

            with self.assertRaisesRegex(ValueError, "not ready for Graph REST dispatch"):
                run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                    client,
                    REPO_ROOT,
                    live_readiness_gate=gate_json,
                    workspace_id="notary_team_01",
                    correlation_id="nac-schema-apply-tampered-gate",
                    owner_approval_reference="owner-approval-tampered-gate",
                    reason="Tampered gate rejection test",
                    owner_approved=True,
                    execute_live_schema_apply=True,
                    write_redacted_evidence=True,
                evidence_json_output=Path(temp_dir) / "dispatcher.redacted.json",
                evidence_markdown_output=Path(temp_dir) / "dispatcher.redacted.md",
                )

        self.assertEqual(client.requests, [])

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

    def test_first_wave_process_deep_model_binds_phases_roles_and_projections(self) -> None:
        payload = build_first_wave_process_deep_model(REPO_ROOT)
        validation = validate_first_wave_process_deep_model(payload)
        case_models = {item["slug"]: item for item in payload["case_models"]}

        self.assertEqual(payload["schema_version"], "nac.first-wave-process-deep-model/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(validation.status, "PASSED")
        self.assertEqual(validation.errors, ())
        self.assertEqual(len(case_models), 4)
        self.assertEqual(payload["summary"]["phase_template_count"], 32)
        self.assertGreaterEqual(payload["summary"]["bpmn_flow_node_binding_count"], 40)
        self.assertGreaterEqual(payload["summary"]["sharepoint_projection_count"], 20)
        self.assertFalse(payload["guardrails"]["executes_graph_requests"])
        self.assertFalse(payload["guardrails"]["writes_sharepoint"])
        self.assertFalse(payload["guardrails"]["mutates_bpmn_sources"])
        self.assertTrue(payload["guardrails"]["bpmn_remains_process_model_not_runtime_engine"])
        for case_model in case_models.values():
            self.assertEqual(len(case_model["phase_plan"]), 8)
            self.assertEqual(len(case_model["role_binding_plan"]), 7)
            self.assertFalse(case_model["bpmn_binding_plan"]["is_executable"])
            self.assertFalse(case_model["kg_binding_plan"]["stores_matter_values"])
            self.assertFalse(case_model["sharepoint_projection_plan"]["writes_sharepoint"])
            self.assertTrue(case_model["gap_closure_plan"]["owner_gate_required_before_apply"])

    def test_cli_first_wave_process_deep_model_returns_safe_json(self) -> None:
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = kg_main(["--repo-root", str(REPO_ROOT), "--format", "json", "first-wave-process-deep-model"])

        payload = json.loads(buffer.getvalue())
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True).lower()

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-process-deep-model/v0.1")
        self.assertEqual(payload["status"], "PASSED")
        self.assertEqual(payload["summary"]["first_wave_count"], 4)
        for forbidden in ("client_secret", "private_key", "authorization", "bearer ", "raw_mandate", "mandatsdaten"):
            self.assertNotIn(forbidden, serialized)

    def test_nac_cli_first_wave_process_deep_model_accepts_tail_format_json(self) -> None:
        parser = nac_cli.build_parser()
        args = parser.parse_args(
            [
                "--repo-root",
                str(REPO_ROOT),
                "kg",
                "first-wave-process-deep-model",
                "--format",
                "json",
            ]
        )
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = args.func(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["schema_version"], "nac.first-wave-process-deep-model/v0.1")
        self.assertEqual(payload["status"], "PASSED")

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
