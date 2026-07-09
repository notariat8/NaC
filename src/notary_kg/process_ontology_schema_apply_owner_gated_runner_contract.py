from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process_ontology_schema_apply_owner_gated_live_plan import (
    build_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
    write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan,
)
from .process_ontology_schema_apply_runner_dry_run import (
    build_process_ontology_sharepoint_schema_apply_runner_dry_run,
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact,
)


SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-owner-gated-runner-contract/v0.1"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_owner_gated_runner_contract"
DEFAULT_OWNER_GATED_RUNNER_CONTRACT_JSON = Path(
    "out/notary-kg/process-ontology-schema-apply-owner-gated-runner-contract.redacted.json"
)
DEFAULT_OWNER_GATED_RUNNER_CONTRACT_MARKDOWN = Path(
    "out/notary-kg/process-ontology-schema-apply-owner-gated-runner-contract.redacted.md"
)


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyOwnerGatedRunnerContractValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
    repo_root: Path,
    artifact_root: Path | None = None,
    *,
    ensure_default_artifacts: bool = True,
) -> dict[str, Any]:
    live_plan = build_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
        repo_root,
        artifact_root,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    dry_run = build_process_ontology_sharepoint_schema_apply_runner_dry_run(repo_root)
    steps = [_runner_step(step, index + 1) for index, step in enumerate(dry_run["dry_run_steps"])]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED",
        "mode": "offline_owner_gated_runner_contract",
        "source": {
            "owner_gated_live_plan_schema": live_plan["schema_version"],
            "owner_gated_live_plan_status": live_plan["status"],
            "dry_run_schema": dry_run["schema_version"],
            "dry_run_status": dry_run["status"],
            "graph_rest_only": live_plan["source"]["graph_rest_only"],
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "summary": {
            "workspace_count": live_plan["summary"]["workspace_count"],
            "runner_step_count": len(steps),
            "preflight_count": len(steps),
            "mutation_count": len(steps),
            "readback_count": len(steps),
            "owner_gate_required_now": False,
            "owner_gate_required_before_execution": True,
            "runner_implementation_ready_for_next_slice": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
        },
        "runner_interface": {
            "command": "nac kg process-ontology-schema-apply-live",
            "command_implemented_now": False,
            "required_flags": live_plan["owner_gate"]["required_flags"],
            "required_inputs": live_plan["owner_gate"]["required_fields"],
            "required_permission": live_plan["future_runner_contract"]["runtime_permission_required"],
            "application_owner_path_required": True,
            "delegated_user_context_allowed": False,
            "graph_rest_only": True,
            "forbidden_flags": live_plan["future_runner_contract"]["forbidden_flags"],
        },
        "stop_rules": {
            "stop_before_first_mutation_if_owner_approval_missing": True,
            "stop_before_first_mutation_if_live_readiness_gate_blocked": True,
            "stop_before_first_mutation_if_runtime_permission_missing": True,
            "stop_on_first_failed_preflight": True,
            "stop_on_first_unexpected_mutation_status": True,
            "stop_on_first_ambiguous_readback": True,
            "automatic_rollback_allowed": False,
            "manual_owner_review_required_after_failure": True,
        },
        "runner_steps": steps,
        "evidence_contract": {
            "redacted_evidence_required": True,
            "write_evidence_before_first_mutation": True,
            "write_evidence_after_each_phase": True,
            "write_evidence_after_stop": True,
            "minimum_evidence_items": live_plan["evidence_contract"]["minimum_evidence_items"],
            "raw_graph_response_allowed": False,
            "tokens_or_auth_headers_allowed": False,
            "matter_instance_values_allowed": False,
        },
        "guardrails": {
            "offline_only": True,
            "runner_contract_only": True,
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
        "next_batch": {
            "recommended_slice": "process_ontology_sharepoint_schema_apply_owner_gated_runner_dry_execute",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "graph_live_write",
                "sharepoint_schema_apply",
                "runner_live_execution",
            ],
        },
        "errors": [],
    }
    validation = validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def write_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
    repo_root: Path,
    artifact_root: Path | None = None,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
    *,
    ensure_default_artifacts: bool = True,
) -> dict[str, Any]:
    write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(repo_root)
    write_process_ontology_sharepoint_schema_apply_owner_gated_live_plan(
        repo_root,
        artifact_root,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    payload = build_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
        repo_root,
        artifact_root,
        ensure_default_artifacts=ensure_default_artifacts,
    )
    json_path = _resolve_output_path(repo_root, json_output or DEFAULT_OWNER_GATED_RUNNER_CONTRACT_JSON)
    markdown_path = _resolve_output_path(repo_root, markdown_output or DEFAULT_OWNER_GATED_RUNNER_CONTRACT_MARKDOWN)
    payload["artifact_paths"] = {
        "json": _relative_path(repo_root, json_path),
        "markdown": _relative_path(repo_root, markdown_path),
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_runner_contract_markdown(payload), encoding="utf-8")
    return payload


def validate_process_ontology_sharepoint_schema_apply_owner_gated_runner_contract(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyOwnerGatedRunnerContractValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected runner contract schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected runner contract contract_id")
    if payload.get("mode") != "offline_owner_gated_runner_contract":
        errors.append("runner contract must remain offline")

    summary = payload.get("summary", {})
    for key in ("runner_step_count", "preflight_count", "mutation_count", "readback_count"):
        if summary.get(key) != 68:
            errors.append(f"{key} must cover 68 steps")
    if summary.get("owner_gate_required_before_execution") is not True:
        errors.append("runner execution must require owner gate")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if summary.get(key) is not False:
            errors.append(f"summary must keep {key} false")

    interface = payload.get("runner_interface", {})
    if interface.get("command") != "nac kg process-ontology-schema-apply-live":
        errors.append("unexpected runner command")
    if interface.get("command_implemented_now") is not False:
        errors.append("runner command must not be claimed as implemented in this contract")
    for flag in ("--owner-approved", "--execute-live-schema-apply", "--live-readiness-gate", "--correlation-id"):
        if flag not in interface.get("required_flags", []):
            errors.append(f"missing required runner flag: {flag}")
    if interface.get("delegated_user_context_allowed") is not False:
        errors.append("delegated user context must remain blocked")
    if interface.get("graph_rest_only") is not True:
        errors.append("runner must be Graph REST only")

    stop_rules = payload.get("stop_rules", {})
    for key in (
        "stop_before_first_mutation_if_owner_approval_missing",
        "stop_before_first_mutation_if_live_readiness_gate_blocked",
        "stop_before_first_mutation_if_runtime_permission_missing",
        "stop_on_first_failed_preflight",
        "stop_on_first_unexpected_mutation_status",
        "stop_on_first_ambiguous_readback",
        "manual_owner_review_required_after_failure",
    ):
        if stop_rules.get(key) is not True:
            errors.append(f"stop rule must be true: {key}")
    if stop_rules.get("automatic_rollback_allowed") is not False:
        errors.append("automatic rollback must remain blocked")

    steps = payload.get("runner_steps", [])
    if len(steps) != 68:
        errors.append("runner contract must expose 68 steps")
    for step in steps:
        if step.get("mode") != "future_owner_gated_step_contract":
            errors.append(f"{step.get('id', '<unknown>')}: unexpected step mode")
        if step.get("owner_gate_required_before_execution") is not True:
            errors.append(f"{step.get('id', '<unknown>')}: missing owner gate")
        for key in ("executes_graph_requests_now", "writes_sharepoint_now", "changes_sharepoint_schema_now"):
            if step.get(key) is not False:
                errors.append(f"{step.get('id', '<unknown>')}: {key} must be false")

    evidence = payload.get("evidence_contract", {})
    if evidence.get("redacted_evidence_required") is not True:
        errors.append("redacted evidence must be required")
    for key in ("raw_graph_response_allowed", "tokens_or_auth_headers_allowed", "matter_instance_values_allowed"):
        if evidence.get(key) is not False:
            errors.append(f"evidence contract must keep {key} false")

    guardrails = payload.get("guardrails", {})
    for key in ("offline_only", "runner_contract_only", "owner_gated"):
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

    return ProcessOntologySchemaApplyOwnerGatedRunnerContractValidation(
        status="PASSED" if not errors else "FAILED",
        errors=tuple(errors),
    )


def _runner_step(step: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "id": step["id"],
        "workspace_id": step["workspace_id"],
        "operation": step["operation"],
        "target": step["target"],
        "mode": "future_owner_gated_step_contract",
        "owner_gate_required_before_execution": True,
        "executes_graph_requests_now": False,
        "writes_sharepoint_now": False,
        "changes_sharepoint_schema_now": False,
        "preflight": _redacted_request(step["preflight_request"]),
        "mutation": {
            "method": step["future_mutation_request"]["method"],
            "path_template": _redact_path_template(step["future_mutation_request"]["path_template"]),
            "expected_success_status": step["future_mutation_request"]["expected_success_status"],
        },
        "readback": _redacted_request(step["readback_request"]),
        "stop_rule_plan": step["stop_rule_plan"],
    }


def _redacted_request(request: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(request)
    if "path_template" in redacted:
        redacted["path_template"] = _redact_path_template(str(redacted["path_template"]))
    return redacted


def _redact_path_template(path_template: str) -> str:
    marker = "/sites/"
    if marker not in path_template:
        return path_template
    prefix, rest = path_template.split(marker, 1)
    if "/lists" not in rest:
        return f"{prefix}{marker}{{site-id}}"
    _, suffix = rest.split("/lists", 1)
    return f"{prefix}{marker}{{site-id}}/lists{suffix}"


def _runner_contract_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Process Ontology SharePoint Schema Apply Owner-Gated Runner Contract",
        "",
        f"- Status: `{payload['status']}`",
        f"- Schema: `{payload['schema_version']}`",
        f"- Runner command: `{payload['runner_interface']['command']}`",
        f"- Runner command implemented now: `{payload['runner_interface']['command_implemented_now']}`",
        f"- Runner steps: `{payload['summary']['runner_step_count']}`",
        f"- Owner gate before execution: `{payload['summary']['owner_gate_required_before_execution']}`",
        f"- Executes Graph requests now: `{payload['summary']['executes_graph_requests']}`",
        "",
        "## Required Flags",
        "",
    ]
    for flag in payload["runner_interface"]["required_flags"]:
        lines.append(f"- `{flag}`")
    lines.extend(["", "## Stop Rules", ""])
    for key, value in payload["stop_rules"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Guardrails", ""])
    for key, value in payload["guardrails"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines).rstrip() + "\n"


def _resolve_output_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _relative_path(repo_root: Path, path: Path) -> str:
    return str(path.relative_to(repo_root) if path.is_relative_to(repo_root) else path)
