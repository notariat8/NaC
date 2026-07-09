from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process_ontology_schema_apply_execution_contract import (
    REQUIRED_PERMISSION,
    build_process_ontology_sharepoint_schema_apply_execution_contract,
)
from .process_ontology_schema_apply_runner_dry_run import (
    build_process_ontology_sharepoint_schema_apply_live_readiness_gate,
    write_process_ontology_sharepoint_schema_apply_live_readiness_gate,
)


SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-owner-gated-live-plan/v0.1"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_owner_gated_live_plan"
DEFAULT_OWNER_GATED_LIVE_PLAN_JSON = Path(
    "out/notary-kg/process-ontology-schema-apply-owner-gated-live-plan.redacted.json"
)
DEFAULT_OWNER_GATED_LIVE_PLAN_MARKDOWN = Path(
    "out/notary-kg/process-ontology-schema-apply-owner-gated-live-plan.redacted.md"
)


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyOwnerGatedLivePlanValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
    repo_root: Path,
    artifact_root: Path | None = None,
    live_readiness_gate: dict[str, Any] | None = None,
    *,
    ensure_default_artifacts: bool = True,
) -> dict[str, Any]:
    execution_contract = build_process_ontology_sharepoint_schema_apply_execution_contract(repo_root)
    if live_readiness_gate is None:
        live_readiness_gate = build_process_ontology_sharepoint_schema_apply_live_readiness_gate(
            repo_root,
            artifact_root,
            ensure_default_artifacts=ensure_default_artifacts,
        )
    phase_plans = [_phase_plan(phase) for phase in execution_contract["execution_phases"]]
    workspace_plans = [_workspace_plan(workspace) for workspace in execution_contract["workspace_contracts"]]
    planned_live_step_count = execution_contract["summary"]["workspace_apply_unit_count"]
    blockers = _blockers(execution_contract, live_readiness_gate)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "READY_FOR_OWNER_APPROVAL" if not blockers else "BLOCKED",
        "mode": "offline_owner_gated_live_plan",
        "source": {
            "execution_contract_schema": execution_contract["schema_version"],
            "execution_contract_status": execution_contract["status"],
            "live_readiness_gate_schema": live_readiness_gate["schema_version"],
            "live_readiness_gate_status": live_readiness_gate["status"],
            "artifact_root": live_readiness_gate["source"]["artifact_root"],
            "graph_rest_only": execution_contract["source"]["graph_rest_only"],
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "summary": {
            "workspace_count": execution_contract["summary"]["workspace_count"],
            "phase_count": execution_contract["summary"]["execution_phase_count"],
            "planned_live_step_count": planned_live_step_count,
            "planned_preflight_count": planned_live_step_count,
            "planned_mutation_count": planned_live_step_count,
            "planned_readback_count": planned_live_step_count,
            "owner_gate_required_now": True,
            "owner_approval_required_before_execution": True,
            "owner_approval_text_required": True,
            "live_readiness_gate_required": True,
            "redacted_evidence_required": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
        },
        "owner_gate": {
            "required": True,
            "approval_text": (
                "Freigabe: Process-Ontology SharePoint Schema Apply live owner-approved "
                "ausführen; Graph REST only; workspaces=notary_team_01,notary_team_02; "
                "correlation_id=<correlation-id>; redigierte Evidence schreiben."
            ),
            "required_fields": [
                "owner_approval_reference",
                "correlation_id",
                "reason",
                "workspace_ids",
                "live_readiness_gate_artifact",
                "dry_run_artifact_index",
            ],
            "required_flags": [
                "--owner-approved",
                "--execute-live-schema-apply",
                "--live-readiness-gate",
                "--correlation-id",
                "--write-redacted-evidence",
            ],
            "blocked_without_owner_approval": True,
            "delegated_user_context_allowed": False,
            "technical_owner_user": "funktion8@funktion8.de",
        },
        "future_runner_contract": {
            "command_template": (
                "nac kg process-ontology-schema-apply-live "
                "--owner-approved --execute-live-schema-apply "
                "--live-readiness-gate <redacted-live-readiness-gate.json> "
                "--correlation-id <correlation-id> --write-redacted-evidence"
            ),
            "command_exists_now": True,
            "runtime_permission_required": REQUIRED_PERMISSION,
            "application_owner_path_required": True,
            "graph_rest_only": True,
            "forbidden_flags": [
                "--delegated-user-context",
                "--allow-legacy-sharepoint-api",
                "--allow-graph-sdk",
                "--skip-preflight",
                "--skip-readback",
                "--skip-redaction",
            ],
            "must_stop_before_first_mutation_if": [
                "owner_approval_missing",
                "live_readiness_gate_missing_or_blocked",
                "runtime_permission_missing",
                "unexpected_graph_endpoint_family",
                "redacted_evidence_output_missing",
            ],
        },
        "execution_plan": {
            "phase_order": phase_plans,
            "workspace_plans": workspace_plans,
            "preflight_before_every_mutation": True,
            "readback_after_every_mutation": True,
            "manual_owner_review_after_failure": True,
            "automatic_rollback_allowed": False,
        },
        "evidence_contract": {
            "redacted_evidence_required": True,
            "live_readiness_gate": live_readiness_gate.get("artifact_paths", {}),
            "dry_run_artifact_index": live_readiness_gate.get("evidence", {}).get("dry_run_artifact_index", {}),
            "minimum_evidence_items": [
                "owner_approval_reference",
                "correlation_id",
                "live_readiness_gate_reference",
                "workspace_execution_summary",
                "per_step_preflight_result",
                "per_mutation_expected_status",
                "per_mutation_readback_result",
                "stop_rule_evaluation",
                "post_apply_schema_snapshot_metadata",
            ],
            "raw_graph_response_allowed": False,
            "tokens_or_auth_headers_allowed": False,
            "matter_instance_values_allowed": False,
        },
        "guardrails": {
            "offline_only": True,
            "live_plan_only": True,
            "owner_gated": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "blockers": blockers,
        "next_batch": {
            "recommended_slice": "process_ontology_sharepoint_schema_apply_owner_gated_runner_contract",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "graph_live_write",
                "sharepoint_schema_apply",
                "runner_live_execution",
            ],
        },
        "errors": [],
    }
    validation = validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
    repo_root: Path,
    artifact_root: Path | None = None,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
    *,
    ensure_default_artifacts: bool = True,
) -> dict[str, Any]:
    live_readiness_gate = write_process_ontology_sharepoint_schema_apply_live_readiness_gate(
        repo_root,
        artifact_root,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    payload = build_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
        repo_root,
        artifact_root,
        live_readiness_gate,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    json_path = _resolve_output_path(repo_root, json_output or DEFAULT_OWNER_GATED_LIVE_PLAN_JSON)
    markdown_path = _resolve_output_path(repo_root, markdown_output or DEFAULT_OWNER_GATED_LIVE_PLAN_MARKDOWN)
    payload["artifact_paths"] = {
        "json": _relative_path(repo_root, json_path),
        "markdown": _relative_path(repo_root, markdown_path),
    }

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_owner_gated_live_plan_markdown(payload), encoding="utf-8")
    return payload


def validate_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyOwnerGatedLivePlanValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected owner-gated live plan schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected owner-gated live plan contract_id")
    if payload.get("mode") != "offline_owner_gated_live_plan":
        errors.append("owner-gated live plan must remain offline_owner_gated_live_plan")

    source = payload.get("source", {})
    if source.get("execution_contract_status") != "PASSED":
        errors.append("execution contract must pass before live plan")
    if source.get("live_readiness_gate_status") != "PASSED":
        errors.append("live readiness gate must pass before live plan")
    if source.get("graph_rest_only") is not True:
        errors.append("Graph REST must remain the only API surface")
    for key in ("legacy_sharepoint_api_allowed", "graph_sdk_allowed"):
        if source.get(key) is not False:
            errors.append(f"source must keep {key} false")

    summary = payload.get("summary", {})
    if summary.get("workspace_count") != 2:
        errors.append("live plan must cover both notary workspaces")
    if summary.get("phase_count") != 8:
        errors.append("live plan must preserve eight execution phases")
    for key in ("planned_live_step_count", "planned_preflight_count", "planned_mutation_count", "planned_readback_count"):
        if summary.get(key) != 68:
            errors.append(f"{key} must cover 68 planned steps")
    for key in (
        "owner_gate_required_now",
        "owner_approval_required_before_execution",
        "owner_approval_text_required",
        "live_readiness_gate_required",
        "redacted_evidence_required",
    ):
        if summary.get(key) is not True:
            errors.append(f"summary must require {key}")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if summary.get(key) is not False:
            errors.append(f"summary must keep {key} false")

    owner_gate = payload.get("owner_gate", {})
    if owner_gate.get("required") is not True:
        errors.append("owner gate must be required")
    for required_flag in (
        "--owner-approved",
        "--execute-live-schema-apply",
        "--live-readiness-gate",
        "--correlation-id",
        "--write-redacted-evidence",
    ):
        if required_flag not in owner_gate.get("required_flags", []):
            errors.append(f"missing owner-gate flag: {required_flag}")
    if owner_gate.get("blocked_without_owner_approval") is not True:
        errors.append("live plan must block without owner approval")
    if owner_gate.get("delegated_user_context_allowed") is not False:
        errors.append("delegated user context must remain blocked")

    runner = payload.get("future_runner_contract", {})
    if runner.get("command_exists_now") is not True:
        errors.append("live runner command must exist once the owner-gated live surface is implemented")
    if runner.get("runtime_permission_required") != REQUIRED_PERMISSION:
        errors.append("unexpected runtime permission")
    if runner.get("application_owner_path_required") is not True:
        errors.append("application owner path must be required")
    if runner.get("graph_rest_only") is not True:
        errors.append("future runner must remain Graph REST only")
    for forbidden in ("--allow-legacy-sharepoint-api", "--allow-graph-sdk", "--skip-redaction"):
        if forbidden not in runner.get("forbidden_flags", []):
            errors.append(f"missing forbidden future runner flag: {forbidden}")

    execution_plan = payload.get("execution_plan", {})
    phase_order = execution_plan.get("phase_order", [])
    workspace_plans = execution_plan.get("workspace_plans", [])
    if len(phase_order) != 8:
        errors.append("execution plan must include eight phases")
    if len(workspace_plans) != 2:
        errors.append("execution plan must include two workspace plans")
    if sum(int(phase.get("planned_unit_count", 0)) for phase in phase_order) != 68:
        errors.append("phase plan must sum to 68 planned units")
    for key in ("preflight_before_every_mutation", "readback_after_every_mutation", "manual_owner_review_after_failure"):
        if execution_plan.get(key) is not True:
            errors.append(f"execution plan must require {key}")
    if execution_plan.get("automatic_rollback_allowed") is not False:
        errors.append("automatic rollback must remain blocked")

    evidence = payload.get("evidence_contract", {})
    if evidence.get("redacted_evidence_required") is not True:
        errors.append("redacted evidence must be required")
    for key in ("raw_graph_response_allowed", "tokens_or_auth_headers_allowed", "matter_instance_values_allowed"):
        if evidence.get(key) is not False:
            errors.append(f"evidence contract must keep {key} false")
    if not evidence.get("minimum_evidence_items"):
        errors.append("minimum evidence items must be listed")

    guardrails = payload.get("guardrails", {})
    for key in ("offline_only", "live_plan_only", "owner_gated"):
        if guardrails.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    for key in (
        "executes_graph_requests",
        "writes_sharepoint",
        "changes_sharepoint_schema",
        "stores_tokens_or_secrets",
        "stores_matter_instance_values",
        "stores_document_full_text",
        "legacy_sharepoint_api_allowed",
        "graph_sdk_allowed",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")

    return ProcessOntologySchemaApplyOwnerGatedLivePlanValidation(
        status="PASSED" if not errors else "FAILED",
        errors=tuple(errors),
    )


def _blockers(execution_contract: dict[str, Any], live_readiness_gate: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    if execution_contract.get("status") != "PASSED":
        blockers.append({"id": "execution_contract", "detail": "execution contract must pass"})
    if live_readiness_gate.get("status") != "PASSED":
        blockers.append({"id": "live_readiness_gate", "detail": "live readiness gate must pass"})
    return blockers


def _phase_plan(phase: dict[str, Any]) -> dict[str, Any]:
    planned_unit_count = int(phase.get("unit_count", 0))
    return {
        "phase": phase["phase"],
        "mode": "future_owner_gated_live_phase",
        "workspace_phase_count": phase["workspace_phase_count"],
        "planned_unit_count": planned_unit_count,
        "preflight_required_before_mutation": planned_unit_count > 0,
        "readback_required_after_mutation": planned_unit_count > 0,
        "owner_gate_required_before_execution": True,
        "executes_graph_requests_now": False,
        "writes_sharepoint_now": False,
        "changes_sharepoint_schema_now": False,
    }


def _workspace_plan(workspace: dict[str, Any]) -> dict[str, Any]:
    return {
        "workspace_id": workspace["workspace_id"],
        "site_id_status": workspace["site_id_status"],
        "planned_unit_count": workspace["summary"]["workspace_apply_unit_count"],
        "dynamic_resolution_count": workspace["summary"]["dynamic_resolution_count"],
        "missing_required_list_id_count": workspace["summary"]["missing_required_list_id_count"],
        "owner_gate_required_before_execution": True,
    }


def _owner_gated_live_plan_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Process Ontology SharePoint Schema Apply Owner-Gated Live Plan",
        "",
        f"- Status: `{payload['status']}`",
        f"- Schema: `{payload['schema_version']}`",
        f"- Workspaces: `{payload['summary']['workspace_count']}`",
        f"- Planned live steps: `{payload['summary']['planned_live_step_count']}`",
        f"- Owner gate required now: `{payload['summary']['owner_gate_required_now']}`",
        f"- Executes Graph requests now: `{payload['summary']['executes_graph_requests']}`",
        f"- Writes SharePoint now: `{payload['summary']['writes_sharepoint']}`",
        "",
        "## Owner Gate",
        "",
        f"- Approval text: `{payload['owner_gate']['approval_text']}`",
        "- Required flags:",
    ]
    for flag in payload["owner_gate"]["required_flags"]:
        lines.append(f"  - `{flag}`")
    lines.extend(["", "## Phase Plan", "", "| Phase | Planned units |", "| --- | ---: |"])
    for phase in payload["execution_plan"]["phase_order"]:
        lines.append(f"| `{phase['phase']}` | `{phase['planned_unit_count']}` |")
    lines.extend(["", "## Evidence", ""])
    for item in payload["evidence_contract"]["minimum_evidence_items"]:
        lines.append(f"- `{item}`")
    lines.extend(["", "## Guardrails", ""])
    for key, value in payload["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def _resolve_output_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _relative_path(repo_root: Path, path: Path) -> str:
    return str(path.relative_to(repo_root) if path.is_relative_to(repo_root) else path)
