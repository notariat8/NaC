from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process_ontology_schema_apply_owner_gated_runner_contract import (
    build_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract,
)


SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-live-runner/v0.1"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_live_runner"
DEFAULT_LIVE_RUNNER_JSON = Path("out/notary-kg/process-ontology-schema-apply-live.redacted.json")
DEFAULT_LIVE_RUNNER_MARKDOWN = Path("out/notary-kg/process-ontology-schema-apply-live.redacted.md")


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyLiveRunnerValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_apply_live_runner(
    repo_root: Path,
    artifact_root: Path | None = None,
    *,
    live_readiness_gate: Path | None = None,
    correlation_id: str | None = None,
    owner_approved: bool = False,
    execute_live_schema_apply: bool = False,
    write_redacted_evidence: bool = False,
    ensure_default_artifacts: bool = True,
) -> dict[str, Any]:
    contract = build_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
        repo_root,
        artifact_root,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    gate_payload, gate_path, gate_errors = _load_or_build_live_readiness_gate(
        repo_root,
        artifact_root,
        live_readiness_gate,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    blocked_reasons = _blocked_reasons(
        owner_approved=owner_approved,
        execute_live_schema_apply=execute_live_schema_apply,
        write_redacted_evidence=write_redacted_evidence,
        correlation_id=correlation_id,
        gate_payload=gate_payload,
        gate_errors=gate_errors,
    )
    ready = not blocked_reasons
    runner_steps = [_live_runner_step(step) for step in contract["runner_steps"]]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "READY_FOR_GRAPH_REST_DISPATCH" if ready else "BLOCKED",
        "mode": "owner_gated_live_runner_surface",
        "source": {
            "runner_contract_schema": contract["schema_version"],
            "runner_contract_status": contract["status"],
            "live_readiness_gate_schema": gate_payload.get("schema_version") if gate_payload else None,
            "live_readiness_gate_status": gate_payload.get("status") if gate_payload else "MISSING",
            "live_readiness_gate_path": _relative_path(repo_root, gate_path) if gate_path else None,
            "graph_rest_only": True,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "owner_gate": {
            "owner_approved": owner_approved,
            "execute_live_schema_apply": execute_live_schema_apply,
            "write_redacted_evidence": write_redacted_evidence,
            "correlation_id": correlation_id or "",
            "live_readiness_gate_required": True,
            "required_flags": [
                "--owner-approved",
                "--execute-live-schema-apply",
                "--live-readiness-gate",
                "--correlation-id",
                "--write-redacted-evidence",
            ],
            "missing_or_blocking": blocked_reasons,
        },
        "summary": {
            "runner_step_count": len(runner_steps),
            "preflight_count": len(runner_steps),
            "mutation_count": len(runner_steps),
            "readback_count": len(runner_steps),
            "owner_gate_satisfied": ready,
            "ready_for_graph_rest_dispatch": ready,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "graph_dispatcher_implemented": False,
            "live_schema_apply_started": False,
        },
        "runner_phases": [
            {
                "id": "owner_gate",
                "status": "PASSED" if ready else "BLOCKED",
                "executes_graph_requests": False,
                "writes_sharepoint": False,
            },
            {
                "id": "graph_rest_dispatch",
                "status": "READY_NEXT_SLICE" if ready else "BLOCKED",
                "executes_graph_requests": False,
                "writes_sharepoint": False,
            },
        ],
        "runner_steps": runner_steps,
        "stop_rules": contract["stop_rules"],
        "evidence_contract": {
            "redacted_evidence_required": True,
            "write_evidence_before_first_mutation": True,
            "raw_graph_response_allowed": False,
            "tokens_or_auth_headers_allowed": False,
            "matter_instance_values_allowed": False,
            "correlation_id_required": True,
        },
        "guardrails": {
            "owner_gated": True,
            "live_runner_surface_only": True,
            "requires_separate_graph_dispatcher": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "next_batch": {
            "recommended_slice": "process_ontology_sharepoint_schema_apply_live_graph_dispatcher",
            "owner_gate_required_now": ready,
            "owner_gate_required_before": [
                "graph_live_write",
                "sharepoint_schema_apply",
                "runner_live_execution",
            ],
        },
        "errors": [],
    }
    validation = validate_process_ontology_sharepoint_schema_apply_live_runner(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def write_process_ontology_sharepoint_schema_apply_live_runner(
    repo_root: Path,
    artifact_root: Path | None = None,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
    *,
    live_readiness_gate: Path | None = None,
    correlation_id: str | None = None,
    owner_approved: bool = False,
    execute_live_schema_apply: bool = False,
    write_redacted_evidence: bool = False,
    ensure_default_artifacts: bool = True,
) -> dict[str, Any]:
    payload = build_process_ontology_sharepoint_schema_apply_live_runner(
        repo_root,
        artifact_root,
        live_readiness_gate=live_readiness_gate,
        correlation_id=correlation_id,
        owner_approved=owner_approved,
        execute_live_schema_apply=execute_live_schema_apply,
        write_redacted_evidence=write_redacted_evidence,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    json_path = _resolve_output_path(repo_root, json_output or DEFAULT_LIVE_RUNNER_JSON)
    markdown_path = _resolve_output_path(repo_root, markdown_output or DEFAULT_LIVE_RUNNER_MARKDOWN)
    payload["artifact_paths"] = {
        "json": _relative_path(repo_root, json_path),
        "markdown": _relative_path(repo_root, markdown_path),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_live_runner_markdown(payload), encoding="utf-8")
    return payload


def validate_process_ontology_sharepoint_schema_apply_live_runner(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyLiveRunnerValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected live runner schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected live runner contract_id")
    if payload.get("mode") != "owner_gated_live_runner_surface":
        errors.append("live runner must expose the owner-gated runner surface")

    summary = payload.get("summary", {})
    for key in ("runner_step_count", "preflight_count", "mutation_count", "readback_count"):
        if summary.get(key) != 68:
            errors.append(f"{key} must cover 68 steps")
    if payload.get("status") == "READY_FOR_GRAPH_REST_DISPATCH" and summary.get("owner_gate_satisfied") is not True:
        errors.append("ready live runner must satisfy the owner gate")
    if payload.get("status") == "BLOCKED" and not payload.get("owner_gate", {}).get("missing_or_blocking"):
        errors.append("blocked live runner must explain missing or blocking inputs")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if summary.get(key) is not False:
            errors.append(f"summary must keep {key} false until Graph dispatcher is implemented")
    if summary.get("graph_dispatcher_implemented") is not False:
        errors.append("this runner slice must not claim the Graph dispatcher is implemented")

    owner_gate = payload.get("owner_gate", {})
    required_flags = owner_gate.get("required_flags", [])
    for flag in (
        "--owner-approved",
        "--execute-live-schema-apply",
        "--live-readiness-gate",
        "--correlation-id",
        "--write-redacted-evidence",
    ):
        if flag not in required_flags:
            errors.append(f"missing required owner-gate flag: {flag}")

    steps = payload.get("runner_steps", [])
    if len(steps) != 68:
        errors.append("live runner must expose 68 steps")
    for step in steps:
        step_id = step.get("id", "<unknown>")
        if step.get("mode") != "owner_gated_live_step_surface":
            errors.append(f"{step_id}: unexpected live runner step mode")
        if step.get("owner_gate_required_before_execution") is not True:
            errors.append(f"{step_id}: missing owner gate")
        for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
            if step.get(key) is not False:
                errors.append(f"{step_id}: {key} must be false in this slice")

    guardrails = payload.get("guardrails", {})
    for key in ("owner_gated", "live_runner_surface_only", "requires_separate_graph_dispatcher"):
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

    return ProcessOntologySchemaApplyLiveRunnerValidation(
        status="PASSED" if not errors else "FAILED",
        errors=tuple(errors),
    )


def _load_or_build_live_readiness_gate(
    repo_root: Path,
    artifact_root: Path | None,
    live_readiness_gate: Path | None,
    *,
    ensure_default_artifacts: bool,
) -> tuple[dict[str, Any], Path | None, list[str]]:
    errors: list[str] = []
    if live_readiness_gate is None:
        return {}, None, ["missing --live-readiness-gate"]

    gate_path = _resolve_output_path(repo_root, live_readiness_gate)
    if not gate_path.is_file():
        return {}, gate_path, [f"live readiness gate not found: {_relative_path(repo_root, gate_path)}"]
    try:
        payload = json.loads(gate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, gate_path, [f"live readiness gate is not valid JSON: {exc}"]
    return payload, gate_path, errors


def _blocked_reasons(
    *,
    owner_approved: bool,
    execute_live_schema_apply: bool,
    write_redacted_evidence: bool,
    correlation_id: str | None,
    gate_payload: dict[str, Any],
    gate_errors: list[str],
) -> list[str]:
    reasons: list[str] = []
    if not owner_approved:
        reasons.append("missing --owner-approved")
    if not execute_live_schema_apply:
        reasons.append("missing --execute-live-schema-apply")
    if not write_redacted_evidence:
        reasons.append("missing --write-redacted-evidence")
    if not correlation_id:
        reasons.append("missing --correlation-id")
    reasons.extend(gate_errors)
    if gate_payload and gate_payload.get("status") != "PASSED":
        reasons.append("live readiness gate did not pass")
    return reasons


def _live_runner_step(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": step["sequence"],
        "id": step["id"],
        "workspace_id": step["workspace_id"],
        "operation": step["operation"],
        "target": step["target"],
        "mode": "owner_gated_live_step_surface",
        "owner_gate_required_before_execution": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
        "preflight": step["preflight"],
        "mutation": step["mutation"],
        "readback": step["readback"],
        "stop_rule_plan": step["stop_rule_plan"],
    }


def _live_runner_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Process Ontology SharePoint Schema Apply Live Runner",
        "",
        f"- Status: `{payload['status']}`",
        f"- Schema: `{payload['schema_version']}`",
        f"- Correlation ID: `{payload['owner_gate']['correlation_id']}`",
        f"- Runner steps: `{payload['summary']['runner_step_count']}`",
        f"- Owner gate satisfied: `{payload['summary']['owner_gate_satisfied']}`",
        f"- Ready for Graph REST dispatch: `{payload['summary']['ready_for_graph_rest_dispatch']}`",
        f"- Executes Graph requests now: `{payload['summary']['executes_graph_requests']}`",
        f"- Writes SharePoint now: `{payload['summary']['writes_sharepoint']}`",
        "",
        "## Blocking Reasons",
        "",
    ]
    if payload["owner_gate"]["missing_or_blocking"]:
        for reason in payload["owner_gate"]["missing_or_blocking"]:
            lines.append(f"- `{reason}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Guardrails", ""])
    for key, value in payload["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def _resolve_output_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _relative_path(repo_root: Path, path: Path) -> str:
    return str(path.relative_to(repo_root) if path.is_relative_to(repo_root) else path)
