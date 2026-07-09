from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .process_ontology_schema_apply_execution_contract import (
    build_process_ontology_sharepoint_schema_apply_execution_contract,
)
from .process_ontology_schema_apply_plan import build_process_ontology_sharepoint_schema_apply_plan
from .process_ontology_schema_apply_readiness import (
    build_process_ontology_sharepoint_schema_apply_readiness,
)


SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-runner-dry-run/v0.1"
ARTIFACT_SCHEMA_VERSION = "nac.process-ontology-sharepoint-schema-apply-runner-dry-run-artifact/v0.1"
CONTRACT_ID = "notarial.process_ontology_sharepoint_schema_apply_runner_dry_run"
DEFAULT_DRY_RUN_ARTIFACT_JSON = Path("out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.json")
DEFAULT_DRY_RUN_ARTIFACT_MARKDOWN = Path("out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.md")


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyRunnerDryRunValidation:
    status: str
    errors: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProcessOntologySchemaApplyRunnerDryRunArtifactValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_sharepoint_schema_apply_runner_dry_run(repo_root: Path) -> dict[str, Any]:
    execution_contract = build_process_ontology_sharepoint_schema_apply_execution_contract(repo_root)
    readiness = build_process_ontology_sharepoint_schema_apply_readiness(repo_root)
    apply_plan = build_process_ontology_sharepoint_schema_apply_plan(repo_root)
    steps_by_id = {step["id"]: step for step in apply_plan["steps"]}
    dry_run_steps = [
        _dry_run_step(workspace, unit, steps_by_id[unit["source_step_id"]])
        for workspace in readiness["workspaces"]
        for unit in workspace["apply_units"]
    ]
    payload = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED",
        "mode": "offline_runner_dry_run",
        "source": {
            "execution_contract_schema": execution_contract["schema_version"],
            "execution_contract_status": execution_contract["status"],
            "apply_readiness_schema": readiness["schema_version"],
            "apply_readiness_status": readiness["status"],
            "apply_plan_schema": apply_plan["schema_version"],
            "apply_plan_status": apply_plan["status"],
            "graph_base_url": apply_plan["source"]["graph_base_url"],
            "graph_rest_only": apply_plan["source"]["graph_rest_only"],
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "summary": {
            "workspace_count": readiness["summary"]["workspace_count"],
            "dry_run_step_count": len(dry_run_steps),
            "preflight_request_count": len(dry_run_steps),
            "future_mutation_request_count": len(dry_run_steps),
            "readback_request_count": len(dry_run_steps),
            "owner_gate_required_now": False,
            "owner_gate_required_before_live_apply": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
        },
        "dry_run_steps": dry_run_steps,
        "evidence_plan": {
            "mode": "redacted_plan_only",
            "artifact_recommended": "out/notary-kg/process-ontology-schema-apply-runner-dry-run.redacted.json",
            "minimum_sections": [
                "source_contracts",
                "workspace_summary",
                "preflight_plan",
                "mutation_plan",
                "readback_plan",
                "stop_rule_plan",
            ],
            "raw_graph_response_allowed": False,
            "tokens_or_auth_headers_allowed": False,
        },
        "guardrails": {
            "offline_only": True,
            "dry_run_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
            "stores_tokens_or_secrets": False,
            "creates_central_knowledge_graph_folder": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
        },
        "next_batch": {
            "recommended_slice": "process_ontology_sharepoint_schema_apply_runner_artifact",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "graph_live_write",
                "sharepoint_schema_apply",
                "runner_live_execution",
            ],
        },
        "errors": [],
    }
    validation = validate_process_ontology_sharepoint_schema_apply_runner_dry_run(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)
    return payload


def write_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
    repo_root: Path,
    json_output: Path | None = None,
    markdown_output: Path | None = None,
) -> dict[str, Any]:
    dry_run = build_process_ontology_sharepoint_schema_apply_runner_dry_run(repo_root)
    json_path = _resolve_output_path(repo_root, json_output or DEFAULT_DRY_RUN_ARTIFACT_JSON)
    markdown_path = _resolve_output_path(repo_root, markdown_output or DEFAULT_DRY_RUN_ARTIFACT_MARKDOWN)
    payload = _artifact_payload(repo_root, dry_run, json_path, markdown_path)
    validation = validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(payload)
    if validation.errors:
        payload["status"] = "FAILED"
        payload["errors"] = list(validation.errors)

    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(_artifact_markdown(payload), encoding="utf-8")
    return payload


def validate_process_ontology_sharepoint_schema_apply_runner_dry_run(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyRunnerDryRunValidation:
    errors: list[str] = []
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("mode") != "offline_runner_dry_run":
        errors.append("runner dry-run must remain offline")

    source = payload.get("source", {})
    for key in ("execution_contract_status", "apply_readiness_status", "apply_plan_status"):
        if source.get(key) != "PASSED":
            errors.append(f"required upstream source did not pass: {key}")
    if source.get("graph_rest_only") is not True:
        errors.append("Graph REST must remain the only API surface")
    if source.get("legacy_sharepoint_api_allowed") is not False:
        errors.append("legacy SharePoint API must remain blocked")
    if source.get("graph_sdk_allowed") is not False:
        errors.append("Graph SDK must remain blocked")

    summary = payload.get("summary", {})
    if summary.get("workspace_count") != 2:
        errors.append("dry-run must cover both workspaces")
    if summary.get("dry_run_step_count") != 68:
        errors.append("dry-run must expose all workspace apply units")
    for key in (
        "preflight_request_count",
        "future_mutation_request_count",
        "readback_request_count",
    ):
        if summary.get(key) != summary.get("dry_run_step_count"):
            errors.append(f"{key} must match dry-run step count")
    for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
        if summary.get(key) is not False:
            errors.append(f"summary must keep {key} false")
    if summary.get("owner_gate_required_before_live_apply") is not True:
        errors.append("live apply must require owner gate")

    dry_run_steps = payload.get("dry_run_steps", [])
    if len(dry_run_steps) != 68:
        errors.append("expected 68 dry-run steps")
    for step in dry_run_steps:
        step_id = step.get("id", "<unknown>")
        if step.get("mode") != "dry_run_only":
            errors.append(f"{step_id}: step must be dry_run_only")
        for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
            if step.get(key) is not False:
                errors.append(f"{step_id}: step must keep {key} false")
        if step.get("owner_gate_required_before_live_apply") is not True:
            errors.append(f"{step_id}: owner gate must be required before live apply")
        if not step.get("preflight_request", {}).get("path_template"):
            errors.append(f"{step_id}: missing preflight request")
        if not step.get("future_mutation_request", {}).get("path_template"):
            errors.append(f"{step_id}: missing future mutation request")
        if not step.get("readback_request", {}).get("path_template"):
            errors.append(f"{step_id}: missing readback request")
        if "headers" in step.get("future_mutation_request", {}):
            errors.append(f"{step_id}: dry-run must not include request headers")

    evidence = payload.get("evidence_plan", {})
    if evidence.get("mode") != "redacted_plan_only":
        errors.append("evidence plan must be redacted_plan_only")
    for key in ("raw_graph_response_allowed", "tokens_or_auth_headers_allowed"):
        if evidence.get(key) is not False:
            errors.append(f"evidence plan must keep {key} false")

    guardrails = payload.get("guardrails", {})
    for key in ("offline_only", "dry_run_only"):
        if guardrails.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    for key in (
        "executes_graph_requests",
        "writes_sharepoint",
        "changes_sharepoint_schema",
        "stores_matter_instance_values",
        "stores_document_full_text",
        "stores_tokens_or_secrets",
        "creates_central_knowledge_graph_folder",
        "legacy_sharepoint_api_allowed",
        "graph_sdk_allowed",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")
    return ProcessOntologySchemaApplyRunnerDryRunValidation(
        status="PASSED" if not errors else "FAILED",
        errors=tuple(errors),
    )


def validate_process_ontology_sharepoint_schema_apply_runner_dry_run_artifact(
    payload: dict[str, Any],
) -> ProcessOntologySchemaApplyRunnerDryRunArtifactValidation:
    errors: list[str] = []
    if payload.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        errors.append("unexpected artifact schema_version")
    if payload.get("contract_id") != f"{CONTRACT_ID}.artifact":
        errors.append("unexpected artifact contract_id")
    if payload.get("mode") != "redacted_offline_artifact":
        errors.append("artifact must remain redacted_offline_artifact")

    source = payload.get("source", {})
    if source.get("dry_run_schema") != SCHEMA_VERSION:
        errors.append("artifact must reference the dry-run schema")
    if source.get("dry_run_status") != "PASSED":
        errors.append("dry-run source must pass before artifact creation")

    summary = payload.get("summary", {})
    if summary.get("dry_run_step_count") != 68:
        errors.append("artifact must include all 68 dry-run steps")
    for key in ("preflight_request_count", "future_mutation_request_count", "readback_request_count"):
        if summary.get(key) != summary.get("dry_run_step_count"):
            errors.append(f"{key} must match dry-run step count")

    artifact_paths = payload.get("artifact_paths", {})
    for key, suffix in (("json", ".redacted.json"), ("markdown", ".redacted.md")):
        path = artifact_paths.get(key, "")
        if not str(path).endswith(suffix):
            errors.append(f"{key} artifact path must end with {suffix}")

    redaction = payload.get("redaction", {})
    expected_flags = {
        "redacted": True,
        "contains_site_ids": False,
        "contains_tokens_or_secrets": False,
        "contains_request_headers": False,
        "contains_raw_graph_response": False,
        "contains_matter_values": False,
    }
    for key, expected in expected_flags.items():
        if redaction.get(key) is not expected:
            errors.append(f"redaction flag mismatch: {key}")

    steps = payload.get("dry_run_step_index", [])
    if len(steps) != 68:
        errors.append("artifact dry-run step index must include 68 entries")
    for step in steps:
        step_id = step.get("id", "<unknown>")
        if step.get("mode") != "redacted_step_index":
            errors.append(f"{step_id}: step index must be redacted")
        for key in ("executes_graph_requests", "writes_sharepoint", "changes_sharepoint_schema"):
            if step.get(key) is not False:
                errors.append(f"{step_id}: step must keep {key} false")
        for request_key in ("preflight_request", "future_mutation_request", "readback_request"):
            request = step.get(request_key, {})
            if "headers" in request:
                errors.append(f"{step_id}: {request_key} must not include headers")
            if "funktion8.sharepoint.com" in str(request.get("path_template", "")):
                errors.append(f"{step_id}: {request_key} must redact site id")

    guardrails = payload.get("guardrails", {})
    for key in ("offline_only", "redacted_artifact", "dry_run_only"):
        if guardrails.get(key) is not True:
            errors.append(f"guardrail must be true: {key}")
    for key in (
        "executes_graph_requests",
        "writes_sharepoint",
        "changes_sharepoint_schema",
        "stores_tokens_or_secrets",
        "stores_matter_instance_values",
        "stores_document_full_text",
    ):
        if guardrails.get(key) is not False:
            errors.append(f"guardrail must be false: {key}")

    return ProcessOntologySchemaApplyRunnerDryRunArtifactValidation(
        status="PASSED" if not errors else "FAILED",
        errors=tuple(errors),
    )


def _dry_run_step(workspace: dict[str, Any], unit: dict[str, Any], source_step: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": unit["id"],
        "workspace_id": workspace["workspace_id"],
        "source_step_id": unit["source_step_id"],
        "operation": unit["operation"],
        "target": unit["target"],
        "mode": "dry_run_only",
        "owner_gate_required_before_live_apply": True,
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
        "preflight_request": {
            "method": unit["preflight_idempotency_check"]["method"],
            "path_template": _workspace_path(unit["preflight_idempotency_check"]["path_template"], workspace),
            "match": unit["preflight_idempotency_check"].get("match", {}),
        },
        "future_mutation_request": {
            "method": source_step["request"]["method"],
            "path_template": _workspace_path(source_step["request"]["path_template"], workspace),
            "body_shape": source_step["request"]["body"],
            "expected_success_status": source_step["expected_success_status"],
        },
        "readback_request": {
            "method": "GET",
            "path_template": _readback_path_template(unit, workspace),
            "expected_success_status": 200,
        },
        "stop_rule_plan": [
            "stop_on_failed_preflight",
            "stop_on_unexpected_status",
            "stop_on_ambiguous_readback",
        ],
    }


def _workspace_path(path_template: str, workspace: dict[str, Any]) -> str:
    return path_template.replace("{site-id}", str(workspace.get("site_id", "{site-id}")))


def _readback_path_template(unit: dict[str, Any], workspace: dict[str, Any]) -> str:
    for dynamic in unit.get("dynamic_resolution_required", []):
        if dynamic.get("path_template"):
            return _workspace_path(dynamic["path_template"], workspace)
    return _workspace_path(unit["preflight_idempotency_check"]["path_template"], workspace)


def _artifact_payload(repo_root: Path, dry_run: dict[str, Any], json_path: Path, markdown_path: Path) -> dict[str, Any]:
    dry_run_step_index = [_redacted_step_index(step) for step in dry_run["dry_run_steps"]]
    payload = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "contract_id": f"{CONTRACT_ID}.artifact",
        "status": "PASSED",
        "mode": "redacted_offline_artifact",
        "source": {
            "dry_run_schema": dry_run["schema_version"],
            "dry_run_status": dry_run["status"],
            "dry_run_contract_id": dry_run["contract_id"],
        },
        "artifact_paths": {
            "json": str(json_path.relative_to(repo_root) if json_path.is_relative_to(repo_root) else json_path),
            "markdown": str(markdown_path.relative_to(repo_root) if markdown_path.is_relative_to(repo_root) else markdown_path),
        },
        "summary": dict(dry_run["summary"]),
        "workspace_summary": _workspace_summary(dry_run_step_index),
        "operation_summary": _operation_summary(dry_run_step_index),
        "dry_run_step_index": dry_run_step_index,
        "redaction": {
            "redacted": True,
            "contains_site_ids": False,
            "contains_tokens_or_secrets": False,
            "contains_request_headers": False,
            "contains_raw_graph_response": False,
            "contains_matter_values": False,
        },
        "evidence_attachments": [
            {
                "id": "process_ontology_schema_apply_runner_dry_run_json",
                "path": str(json_path.relative_to(repo_root) if json_path.is_relative_to(repo_root) else json_path),
                "media_type": "application/json",
                "redacted": True,
                "required_for_live_apply_readiness": True,
            },
            {
                "id": "process_ontology_schema_apply_runner_dry_run_markdown",
                "path": str(markdown_path.relative_to(repo_root) if markdown_path.is_relative_to(repo_root) else markdown_path),
                "media_type": "text/markdown",
                "redacted": True,
                "required_for_live_apply_readiness": True,
            },
        ],
        "guardrails": {
            "offline_only": True,
            "redacted_artifact": True,
            "dry_run_only": True,
            "executes_graph_requests": False,
            "writes_sharepoint": False,
            "changes_sharepoint_schema": False,
            "stores_tokens_or_secrets": False,
            "stores_matter_instance_values": False,
            "stores_document_full_text": False,
        },
        "next_batch": {
            "recommended_slice": "process_ontology_sharepoint_schema_apply_artifact_index",
            "owner_gate_required_now": False,
            "owner_gate_required_before": [
                "graph_live_write",
                "sharepoint_schema_apply",
                "runner_live_execution",
            ],
        },
        "errors": [],
    }
    return payload


def _redacted_step_index(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": step["id"],
        "workspace_id": step["workspace_id"],
        "source_step_id": step["source_step_id"],
        "operation": step["operation"],
        "target": step["target"],
        "mode": "redacted_step_index",
        "owner_gate_required_before_live_apply": step["owner_gate_required_before_live_apply"],
        "executes_graph_requests": False,
        "writes_sharepoint": False,
        "changes_sharepoint_schema": False,
        "preflight_request": _redacted_request(step["preflight_request"], include_body=False),
        "future_mutation_request": _redacted_request(step["future_mutation_request"], include_body=True),
        "readback_request": _redacted_request(step["readback_request"], include_body=False),
        "stop_rule_plan": list(step["stop_rule_plan"]),
    }


def _redacted_request(request: dict[str, Any], *, include_body: bool) -> dict[str, Any]:
    redacted: dict[str, Any] = {
        "method": request["method"],
        "path_template": _redact_path_template(str(request["path_template"])),
    }
    if request.get("expected_success_status") is not None:
        redacted["expected_success_status"] = request["expected_success_status"]
    if include_body:
        redacted["body_shape_keys"] = sorted(_body_shape_keys(request.get("body_shape", {})))
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


def _body_shape_keys(value: Any, prefix: str = "") -> list[str]:
    if isinstance(value, dict):
        keys: list[str] = []
        for key, item in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            keys.extend(_body_shape_keys(item, child_prefix))
        return keys or ([prefix] if prefix else [])
    if isinstance(value, list):
        return [f"{prefix}[]" if prefix else "[]"]
    return [prefix] if prefix else []


def _workspace_summary(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_workspace: dict[str, dict[str, Any]] = {}
    for step in steps:
        workspace = by_workspace.setdefault(
            step["workspace_id"],
            {
                "workspace_id": step["workspace_id"],
                "dry_run_step_count": 0,
                "operation_counts": {},
            },
        )
        workspace["dry_run_step_count"] += 1
        operation_counts = workspace["operation_counts"]
        operation_counts[step["operation"]] = operation_counts.get(step["operation"], 0) + 1
    return [by_workspace[key] for key in sorted(by_workspace)]


def _operation_summary(steps: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for step in steps:
        counts[step["operation"]] = counts.get(step["operation"], 0) + 1
    return dict(sorted(counts.items()))


def _artifact_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Process Ontology SharePoint Schema Apply Runner Dry-Run Artifact",
        "",
        f"- Status: `{payload['status']}`",
        f"- Schema: `{payload['schema_version']}`",
        f"- Dry-run steps: `{payload['summary']['dry_run_step_count']}`",
        f"- Future mutation plans: `{payload['summary']['future_mutation_request_count']}`",
        f"- Executes Graph requests: `{payload['summary']['executes_graph_requests']}`",
        f"- Writes SharePoint: `{payload['summary']['writes_sharepoint']}`",
        f"- Changes SharePoint schema: `{payload['summary']['changes_sharepoint_schema']}`",
        "",
        "## Workspaces",
        "",
    ]
    for workspace in payload["workspace_summary"]:
        lines.append(f"- `{workspace['workspace_id']}`: `{workspace['dry_run_step_count']}` dry-run steps")
    lines.extend(["", "## Operations", ""])
    for operation, count in payload["operation_summary"].items():
        lines.append(f"- `{operation}`: `{count}`")
    lines.extend(["", "## Redaction", ""])
    for key, value in payload["redaction"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Attachments", ""])
    for attachment in payload["evidence_attachments"]:
        lines.append(f"- `{attachment['id']}`: `{attachment['path']}`")
    return "\n".join(lines).rstrip() + "\n"


def _resolve_output_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path
