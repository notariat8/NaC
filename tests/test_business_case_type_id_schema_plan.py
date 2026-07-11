from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from notary_kg.process_ontology_schema_apply_execution_contract import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_execution_contract,
    validate_process_ontology_sharepoint_schema_apply_execution_contract,
)
from notary_kg.process_ontology_schema_apply_graph_dispatcher import (  # noqa: E402
    run_process_ontology_sharepoint_schema_apply_graph_dispatcher,
)
from notary_kg.process_ontology_schema_apply_live_runner import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_live_runner,
    validate_process_ontology_sharepoint_schema_apply_live_runner,
)
from notary_kg.process_ontology_schema_apply_readiness import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_readiness,
    validate_process_ontology_sharepoint_schema_apply_readiness,
)
from notary_kg.process_ontology_schema_apply_owner_gated_live_plan import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
    validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
)
from notary_kg.process_ontology_schema_apply_owner_gated_runner_contract import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract,
    validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract,
)
from notary_kg.process_ontology_schema_apply_plan import (  # noqa: E402
    build_process_ontology_sharepoint_schema_apply_plan,
    validate_process_ontology_sharepoint_schema_apply_plan,
)
from notary_kg.process_ontology_schema_apply_runner_dry_run import (  # noqa: E402
    ARTIFACT_SCHEMA_VERSION,
    LEGACY_ARTIFACT_SCHEMA_VERSION,
    build_process_ontology_sharepoint_schema_apply_artifact_index,
    build_process_ontology_sharepoint_schema_apply_runner_dry_run,
    validate_process_ontology_sharepoint_schema_apply_artifact_index,
    validate_process_ontology_sharepoint_schema_apply_live_readiness_gate,
    validate_process_ontology_sharepoint_schema_apply_runner_dry_run,
    validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
    write_process_ontology_sharepoint_schema_apply_live_readiness_gate,
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
)
from notary_kg.process_ontology_schema_gap import (  # noqa: E402
    build_process_ontology_sharepoint_schema_gap,
    validate_process_ontology_sharepoint_schema_gap,
)


class ZeroCallGraphClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def get(self, path: str) -> dict:
        self.calls.append(("GET", path))
        return {}

    def post(self, path: str, payload: dict) -> dict:
        self.calls.append(("POST", path))
        return {}

    def patch(self, path: str, payload: dict) -> dict:
        self.calls.append(("PATCH", path))
        return {}


class BusinessCaseTypeIdSchemaPlanTests(unittest.TestCase):
    def test_s2_plan_has_exact_registry_shapes_and_preserves_legacy_choice(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json").read_text(
                encoding="utf-8"
            )
        )
        akten = next(item for item in schema["sharepoint"]["lists"] if item["display_name"] == "Akten")
        legacy = next(column for column in akten["columns"] if column["name"] == "Vorgangstyp")
        fingerprint = hashlib.sha256(
            json.dumps(legacy, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()

        gap = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)
        plan = build_process_ontology_sharepoint_schema_apply_plan(REPO_ROOT)
        register_step = next(step for step in plan["steps"] if step["target"] == "Vorgangsartenregister")
        register_columns = {
            column["name"]: column for column in register_step["request"]["body"]["columns"]
        }
        matter_type_step = next(
            step
            for step in plan["steps"]
            if step["target"] == "Akten" and step["request"]["body"].get("name") == "VorgangstypId"
        )

        self.assertEqual(plan["summary"]["total_step_count"], 33)
        self.assertEqual(gap["legacy_column_contract"]["baseline_fingerprint_sha256"], fingerprint)
        self.assertEqual(legacy["type"], "choice")
        business_case_id = register_columns["BusinessCaseTypeId"]
        self.assertEqual(business_case_id["text"]["maxLength"], 128)
        self.assertTrue(business_case_id["indexed"])
        self.assertTrue(business_case_id["enforceUniqueValues"])
        self.assertFalse(register_columns["LifecycleStatus"]["choice"]["allowTextEntry"])
        self.assertIn("boolean", register_columns["Selectable"])
        self.assertIn("text", register_columns["CatalogVersion"])
        self.assertFalse(any(step["target"] == "Prozessregister" for step in plan["steps"]))
        self.assertFalse(any(step["target"] == "BPMN Models" for step in plan["steps"]))
        self.assertEqual(plan["optional_projection_plan"]["gap_count"], 2)
        self.assertFalse(plan["optional_projection_plan"]["included_in_default_s2_plan"])
        self.assertEqual(matter_type_step["request"]["body"]["text"]["maxLength"], 128)
        self.assertTrue(matter_type_step["request"]["body"]["indexed"])
        self.assertFalse(
            any(
                step["target"] == "Akten"
                and step["request"]["method"] == "PATCH"
                and step["request"]["body"].get("name") == "Vorgangstyp"
                for step in plan["steps"]
            )
        )

    def test_optional_viewer_shapes_derive_from_provisioning_and_remain_nonblocking(self) -> None:
        gap = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)
        optional = {item["target"]: item for item in gap["optional_projection_gaps"]}
        viewer = json.loads(
            (REPO_ROOT / "deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json").read_text(
                encoding="utf-8"
            )
        )
        process_source = next(item for item in viewer["sharepoint"]["lists"] if item["display_name"] == "Prozessregister")
        library_source = next(
            item for item in viewer["sharepoint"]["document_libraries"] if item["display_name"] == "BPMN Models"
        )
        process_columns = {item["name"]: item for item in optional["Prozessregister"]["planned_columns"]}
        library_columns = {item["name"]: item for item in optional["BPMN Models"]["planned_columns"]}

        self.assertEqual(set(process_columns), {item["name"] for item in process_source["columns"]})
        self.assertEqual(set(library_columns), {item["name"] for item in library_source["columns"]})
        self.assertTrue(process_columns["ProcessKey"]["indexed"])
        self.assertTrue(process_columns["ProcessKey"]["enforceUniqueValues"])
        self.assertEqual(process_columns["ProcessKey"]["maxLength"], 128)
        for name in (
            "NacBpmnModelId",
            "BpmnDriveItemId",
            "BpmnXmlSha256",
            "BpmnGitPath",
            "BpmnGitCommitSha",
            "NacBpmnVersion",
            "BpmnContentMode",
        ):
            self.assertFalse(process_columns[name]["required"])
        self.assertTrue(library_columns["NacBpmnModelId"]["required"])
        self.assertTrue(library_columns["BpmnDriveItemId"]["required"])

        schema = json.loads(
            (REPO_ROOT / "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json").read_text(
                encoding="utf-8"
            )
        )
        schema["sharepoint"]["lists"].extend(viewer["sharepoint"]["lists"])
        schema["sharepoint"]["document_libraries"].extend(viewer["sharepoint"]["document_libraries"])
        with tempfile.TemporaryDirectory() as temp_dir:
            mutated_path = Path(temp_dir) / "schema.json"
            mutated_path.write_text(json.dumps(schema), encoding="utf-8")
            with patch("notary_kg.process_ontology_schema_gap.SHAREPOINT_SCHEMA_PATH", mutated_path):
                applied_gap = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)

        self.assertEqual(applied_gap["status"], "PASSED")
        self.assertEqual(applied_gap["summary"]["blocking_shape_mismatch_count"], 0)
        self.assertEqual(applied_gap["summary"]["optional_shape_mismatch_count"], 0)

    def test_generic_validators_accept_consistent_zero_change_state(self) -> None:
        gap = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)
        for key in (
            "missing_required_lists",
            "required_projection_gaps",
            "optional_projection_gaps",
            "field_gaps",
            "choice_gaps",
        ):
            gap[key] = []
        for key in (
            "missing_required_list_count",
            "required_projection_gap_count",
            "optional_projection_gap_count",
            "field_gap_count",
            "choice_gap_count",
            "blocking_shape_mismatch_count",
            "optional_shape_mismatch_count",
            "total_gap_count",
        ):
            gap["summary"][key] = 0
        self.assertEqual(validate_process_ontology_sharepoint_schema_gap(gap).errors, ())

        plan = build_process_ontology_sharepoint_schema_apply_plan(REPO_ROOT)
        plan["steps"] = []
        plan["optional_projection_plan"]["gaps"] = []
        plan["optional_projection_plan"]["gap_count"] = 0
        for key in (
            "source_total_gap_count",
            "source_required_gap_count",
            "excluded_optional_projection_gap_count",
            "create_list_step_count",
            "create_document_library_step_count",
            "create_column_step_count",
            "extend_choice_step_count",
            "total_step_count",
        ):
            plan["summary"][key] = 0
        self.assertEqual(validate_process_ontology_sharepoint_schema_apply_plan(plan).errors, ())

        readiness = build_process_ontology_sharepoint_schema_apply_readiness(REPO_ROOT)
        readiness["source"]["apply_plan_step_count"] = 0
        readiness["summary"]["apply_plan_step_count"] = 0
        readiness["summary"]["workspace_apply_unit_count"] = 0
        readiness["summary"]["known_required_list_id_count"] = 0
        readiness["summary"]["dynamic_resource_resolution_count"] = 0
        for workspace in readiness["workspaces"]:
            workspace["apply_units"] = []
            workspace["summary"]["workspace_apply_unit_count"] = 0
            workspace["summary"]["known_required_list_id_count"] = 0
            workspace["summary"]["dynamic_resource_resolution_count"] = 0
        self.assertEqual(validate_process_ontology_sharepoint_schema_apply_readiness(readiness).errors, ())

        dry_run = build_process_ontology_sharepoint_schema_apply_runner_dry_run(REPO_ROOT)
        dry_run["dry_run_steps"] = []
        for key in (
            "dry_run_step_count",
            "preflight_request_count",
            "future_mutation_request_count",
            "readback_request_count",
        ):
            dry_run["summary"][key] = 0
        self.assertEqual(validate_process_ontology_sharepoint_schema_apply_runner_dry_run(dry_run).errors, ())

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact = write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.json",
                temp_root / "process-ontology-schema-apply-runner-dry-run.redacted.md",
            )
            artifact["dry_run_step_index"] = []
            for key in (
                "dry_run_step_count",
                "preflight_request_count",
                "future_mutation_request_count",
                "readback_request_count",
            ):
                artifact["summary"][key] = 0
            self.assertEqual(
                validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(artifact).errors,
                (),
            )

            artifact_index = build_process_ontology_sharepoint_schema_apply_artifact_index(
                REPO_ROOT,
                temp_root,
                ensure_default_artifact=False,
            )
            artifact_index["source"]["current_dry_run_step_count"] = 0
            artifact_index["summary"]["total_dry_run_step_count"] = 0
            for row in artifact_index["artifacts"]:
                row["dry_run_step_count"] = 0
            self.assertEqual(
                validate_process_ontology_sharepoint_schema_apply_artifact_index(artifact_index).errors,
                (),
            )

        execution = build_process_ontology_sharepoint_schema_apply_execution_contract(REPO_ROOT)
        execution["summary"]["workspace_apply_unit_count"] = 0
        execution["summary"]["mutating_operation_count"] = 0
        execution["summary"]["dynamic_resolution_count"] = 0
        for workspace in execution["workspace_contracts"]:
            workspace["summary"]["workspace_apply_unit_count"] = 0
            workspace["summary"]["mutating_operation_count"] = 0
            workspace["summary"]["dynamic_resolution_count"] = 0
        self.assertEqual(
            validate_process_ontology_sharepoint_schema_apply_execution_contract(execution).errors,
            (),
        )

        live_plan = build_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(REPO_ROOT)
        for key in (
            "planned_live_step_count",
            "planned_preflight_count",
            "planned_mutation_count",
            "planned_readback_count",
        ):
            live_plan["summary"][key] = 0
        live_plan["source"]["live_readiness_gate_status"] = "PASSED"
        live_plan["status"] = "BLOCKED"
        live_plan["blockers"] = [
            blocker
            for blocker in live_plan["blockers"]
            if blocker["id"] == "s2_pending_s6_s7_approval"
        ]
        for phase in live_plan["execution_plan"]["phase_order"]:
            phase["planned_unit_count"] = 0
        self.assertEqual(
            validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(live_plan).errors,
            (),
        )

        runner_contract = build_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(REPO_ROOT)
        runner_contract["runner_steps"] = []
        for key in ("runner_step_count", "preflight_count", "mutation_count", "readback_count"):
            runner_contract["summary"][key] = 0
        self.assertEqual(
            validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
                runner_contract
            ).errors,
            (),
        )

        live_runner = build_process_ontology_sharepoint_schema_apply_live_runner(REPO_ROOT)
        live_runner["runner_steps"] = []
        for key in ("runner_step_count", "preflight_count", "mutation_count", "readback_count"):
            live_runner["summary"][key] = 0
        self.assertEqual(
            validate_process_ontology_sharepoint_schema_apply_live_runner(live_runner).errors,
            (),
        )

    def test_live_runner_rejects_consistently_tampered_gate_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json",
                artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md",
            )
            gate_path = temp_root / "gate.redacted.json"
            write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_path,
                temp_root / "gate.redacted.md",
                workspace_ids=["notary_team_01"],
            )
            gate = json.loads(gate_path.read_text(encoding="utf-8"))
            fake = "f" * 64
            binding = gate["approval_binding"]
            binding["apply_plan_sha256"] = fake
            binding["workspace_readiness_sha256"] = fake
            gate["source"]["apply_plan_sha256"] = fake
            gate["source"]["workspace_readiness_sha256"] = fake
            gate["source"]["artifact_index_apply_plan_sha256"] = fake
            gate["source"]["artifact_index_workspace_readiness_sha256"] = fake
            for artifact in gate["evidence"]["indexed_artifacts"]:
                artifact["apply_plan_sha256"] = fake
                artifact["workspace_readiness_sha256"] = fake
            self.assertIn(
                "live readiness gate approval_binding hash does not match canonical binding",
                validate_process_ontology_sharepoint_schema_apply_live_readiness_gate(gate).errors,
            )
            gate_path.write_text(json.dumps(gate), encoding="utf-8")

            runner = build_process_ontology_sharepoint_schema_apply_live_runner(
                REPO_ROOT,
                live_readiness_gate=gate_path,
                workspace_id="notary_team_01",
                correlation_id="consistent-tamper",
                owner_approval_reference="owner-approved-reference",
                reason="Verify fresh recomputation",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                ensure_default_artifacts=False,
            )
            self.assertIn(
                "live readiness gate did not pass validation",
                runner["owner_gate"]["missing_or_blocking"],
            )
            self.assertIn(
                "S2 schema plan live execution is blocked pending S6/S7 approval",
                runner["owner_gate"]["missing_or_blocking"],
            )

    def test_existing_projection_shape_drift_fails_closed(self) -> None:
        schema_path = REPO_ROOT / "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        akten = next(item for item in schema["sharepoint"]["lists"] if item["display_name"] == "Akten")
        akten["columns"].append(
            {
                "name": "VorgangstypId",
                "type": "text",
                "required": True,
                "indexed": False,
                "text": {"maxLength": 64},
            }
        )
        schema["sharepoint"]["lists"].append(
            {
                "display_name": "Vorgangsartenregister",
                "template": "genericList",
                "columns": [
                    {
                        "name": "BusinessCaseTypeId",
                        "type": "text",
                        "required": True,
                        "indexed": False,
                        "enforceUniqueValues": False,
                        "text": {"maxLength": 64},
                    }
                ],
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            mutated_path = Path(temp_dir) / "schema.json"
            mutated_path.write_text(json.dumps(schema), encoding="utf-8")
            with patch("notary_kg.process_ontology_schema_gap.SHAREPOINT_SCHEMA_PATH", mutated_path):
                gap = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)

        self.assertEqual(gap["status"], "FAILED")
        self.assertEqual(gap["summary"]["blocking_shape_mismatch_count"], 2)
        mismatch = gap["required_projection_gaps"][0]["shape_mismatches"]["BusinessCaseTypeId"]
        self.assertEqual(mismatch["indexed"]["expected"], True)
        self.assertEqual(mismatch["maxLength"]["expected"], 128)
        matter_gap = next(item for item in gap["field_gaps"] if item["id"] == "Akten.VorgangstypId.shape")
        self.assertEqual(matter_gap["shape_mismatches"]["required"]["expected"], False)
        self.assertEqual(matter_gap["shape_mismatches"]["indexed"]["expected"], True)

    def test_legacy_choice_missing_or_drifted_fails_closed(self) -> None:
        schema_path = REPO_ROOT / "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json"
        for mode in ("missing", "drifted"):
            with self.subTest(mode=mode):
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                akten = next(item for item in schema["sharepoint"]["lists"] if item["display_name"] == "Akten")
                if mode == "missing":
                    akten["columns"] = [column for column in akten["columns"] if column["name"] != "Vorgangstyp"]
                else:
                    legacy = next(column for column in akten["columns"] if column["name"] == "Vorgangstyp")
                    legacy["choices"].append("unapproved-drift")
                with tempfile.TemporaryDirectory() as temp_dir:
                    mutated_path = Path(temp_dir) / "schema.json"
                    mutated_path.write_text(json.dumps(schema), encoding="utf-8")
                    with patch("notary_kg.process_ontology_schema_gap.SHAREPOINT_SCHEMA_PATH", mutated_path):
                        gap = build_process_ontology_sharepoint_schema_gap(REPO_ROOT)
                self.assertEqual(gap["status"], "FAILED")
                self.assertFalse(gap["legacy_column_contract"]["matches_pinned_baseline"])
                self.assertIn(
                    "legacy Akten.Vorgangstyp is missing or drifted from the pinned baseline",
                    gap["errors"],
                )

    def test_stale_v01_artifact_is_rejected(self) -> None:
        artifact = {
            "schema_version": LEGACY_ARTIFACT_SCHEMA_VERSION,
            "contract_id": "notarial.process_ontology_sharepoint_schema_apply_runner_dry_run.artifact",
            "mode": "redacted_offline_artifact",
        }
        validation = validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(artifact)
        self.assertEqual(ARTIFACT_SCHEMA_VERSION.endswith("/v0.2"), True)
        self.assertIn("stale or unexpected artifact schema_version", validation.errors)

    def test_s2_stale_gate_and_dispatch_are_blocked_before_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            artifact_root = temp_root / "artifacts"
            write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
                REPO_ROOT,
                artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.json",
                artifact_root / "process-ontology-schema-apply-runner-dry-run.redacted.md",
            )
            gate_path = temp_root / "live-readiness-gate.redacted.json"
            write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
                REPO_ROOT,
                artifact_root,
                gate_path,
                temp_root / "live-readiness-gate.redacted.md",
                workspace_ids=["notary_team_01"],
            )
            stale = json.loads(gate_path.read_text(encoding="utf-8"))
            stale["approval_binding"]["apply_plan_sha256"] = "0" * 64
            stale_path = temp_root / "stale-live-readiness-gate.redacted.json"
            stale_path.write_text(json.dumps(stale), encoding="utf-8")

            runner = build_process_ontology_sharepoint_schema_apply_live_runner(
                REPO_ROOT,
                live_readiness_gate=stale_path,
                workspace_id="notary_team_01",
                correlation_id="s2-stale-contract",
                owner_approval_reference="s2-owner-reference",
                reason="Verify stale S2 contract rejection",
                owner_approved=True,
                execute_live_schema_apply=True,
                write_redacted_evidence=True,
                ensure_default_artifacts=False,
            )
            self.assertEqual(runner["status"], "BLOCKED")
            self.assertTrue(
                any(
                    blocker in runner["owner_gate"]["missing_or_blocking"]
                    for blocker in (
                        "live readiness gate does not match selected workspace and freshly recomputed current plan/readiness",
                        "live readiness gate did not pass validation",
                    )
                )
            )

            client = ZeroCallGraphClient()
            with self.assertRaisesRegex(ValueError, "blocked pending S6/S7 approval"):
                run_process_ontology_sharepoint_schema_apply_graph_dispatcher(
                    client,
                    REPO_ROOT,
                    live_readiness_gate=gate_path,
                    workspace_id="notary_team_01",
                    correlation_id="s2-zero-graph-calls",
                    owner_approval_reference="s2-owner-reference",
                    reason="Verify S2 pre-dispatch block",
                    owner_approved=True,
                    execute_live_schema_apply=True,
                    write_redacted_evidence=True,
                    evidence_json_output=temp_root / "dispatcher.redacted.json",
                    evidence_markdown_output=temp_root / "dispatcher.redacted.md",
                )
            self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
