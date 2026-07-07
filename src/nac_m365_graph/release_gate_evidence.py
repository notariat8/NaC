from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


DEFAULT_EVIDENCE_OUTPUT = Path("out/m365/teams-sharepoint/release-gate-evidence.redacted.md")
DEFAULT_EVIDENCE_JSON_OUTPUT = Path("out/m365/teams-sharepoint/release-gate-evidence.redacted.json")
DEFAULT_ARTIFACT_INDEX_OUTPUT = Path("out/m365/teams-sharepoint/release-gate-artifact-index.redacted.json")
DEFAULT_MCP_INVENTORY_ARTIFACT = Path("out/m365/teams-sharepoint/mcp-inventory-smoke.redacted.json")
DEFAULT_MCP_SMOKE_SUITE_ARTIFACT = Path("out/m365/teams-sharepoint/mcp-smoke-suite.redacted.json")
DEFAULT_MCP_LEFTOVER_ARTIFACT = Path("out/m365/teams-sharepoint/mcp-smoke-leftover-cleanup.redacted.json")
DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_ARTIFACT = Path(
    "out/m365/teams-sharepoint/runtime-certificate-expiry-monitor.redacted.json"
)
DEFAULT_RUNTIME_SMOKE_ARTIFACT = Path("out/m365/teams-sharepoint/runtime-smoke.redacted.json")
DEFAULT_RUNTIME_METADATA_ARTIFACT = Path("out/m365/teams-sharepoint/runtime-metadata.redacted.json")


def build_release_gate_evidence(
    *,
    repo_root: Path,
    mcp_inventory_artifact: Path | None = None,
    mcp_suite_artifact: Path | None = None,
    mcp_leftover_artifact: Path | None = None,
    runtime_certificate_expiry_artifact: Path | None = None,
    runtime_smoke_artifact: Path | None = None,
    runtime_metadata_artifact: Path | None = None,
    expected_workspace_id: str | None = None,
    expected_correlation_id: str | None = None,
    require_runtime_artifacts: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at = generated_at or _now()
    paths = {
        "runtime_certificate_expiry": _resolve(
            repo_root,
            runtime_certificate_expiry_artifact,
            DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_ARTIFACT,
        ),
        "runtime_smoke": _resolve(repo_root, runtime_smoke_artifact, DEFAULT_RUNTIME_SMOKE_ARTIFACT),
        "runtime_metadata": _resolve(repo_root, runtime_metadata_artifact, DEFAULT_RUNTIME_METADATA_ARTIFACT),
        "mcp_inventory_smoke": _resolve(repo_root, mcp_inventory_artifact, DEFAULT_MCP_INVENTORY_ARTIFACT),
        "mcp_smoke_suite": _resolve(repo_root, mcp_suite_artifact, DEFAULT_MCP_SMOKE_SUITE_ARTIFACT),
        "mcp_leftover_dry_run": _resolve(repo_root, mcp_leftover_artifact, DEFAULT_MCP_LEFTOVER_ARTIFACT),
    }

    steps = [
        _runtime_certificate_expiry_step(paths["runtime_certificate_expiry"], required=require_runtime_artifacts),
        _runtime_smoke_step(paths["runtime_smoke"], required=require_runtime_artifacts),
        _runtime_metadata_step(paths["runtime_metadata"], required=require_runtime_artifacts),
        _mcp_inventory_step(paths["mcp_inventory_smoke"]),
        _mcp_suite_step(paths["mcp_smoke_suite"]),
        _mcp_leftover_step(paths["mcp_leftover_dry_run"]),
    ]
    errors: list[str] = []
    for step in steps:
        errors.extend(step["errors"])

    _validate_expected_value(
        steps,
        field="workspace_id",
        expected=expected_workspace_id,
        errors=errors,
    )
    _validate_expected_value(
        steps,
        field="correlation_id",
        expected=expected_correlation_id,
        errors=errors,
    )

    status = _overall_status(steps, errors)
    completeness = _evidence_completeness(steps)
    summary = {
        "workspace_id": _first_summary_value(steps, "workspace_id"),
        "correlation_id": _first_summary_value(steps, "correlation_id"),
        "evidence_completeness": completeness,
        "runtime_artifacts_required": require_runtime_artifacts,
        "runtime_certificate_expiry_status": steps[0]["status"],
        "runtime_smoke_status": steps[1]["status"],
        "runtime_metadata_status": steps[2]["status"],
        "mcp_inventory_smoke_status": steps[3]["status"],
        "mcp_smoke_suite_status": steps[4]["status"],
        "mcp_leftover_dry_run_status": steps[5]["status"],
        "graph_rest_only": _all_privacy_flag(steps, "graph_rest_only", default=True),
        "stores_tokens_or_secrets": _any_privacy_flag(steps, "stores_tokens_or_secrets"),
        "stores_raw_graph_response": _any_privacy_flag(steps, "raw_graph_response_stored"),
        "stores_raw_case_id": _any_privacy_flag(steps, "raw_case_id_stored"),
        "reads_sharepoint_file_content": _any_privacy_flag(steps, "reads_sharepoint_file_content"),
    }
    evidence = {
        "schema_version": "nac.m365-release-gate-evidence/v0.1",
        "status": status,
        "generated_at": generated_at,
        "summary": summary,
        "steps": steps,
        "errors": errors,
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }
    attach_release_gate_artifact_index(evidence)
    return evidence


def write_release_gate_evidence_report(evidence: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_release_gate_evidence_markdown(evidence), encoding="utf-8")


def write_release_gate_evidence_json(evidence: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_release_gate_artifact_index(index: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def attach_release_gate_artifact_index(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence["artifact_index"] = build_release_gate_artifact_index(evidence)
    return evidence


def build_release_gate_artifact_index(evidence: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(evidence.get("summary"))
    artifacts = []
    for step in evidence.get("steps", []):
        if not isinstance(step, dict):
            continue
        errors = step.get("errors")
        artifact_path = Path(str(step.get("artifact_path", "")))
        artifact_exists = artifact_path.exists()
        artifacts.append(
            {
                "id": step.get("id"),
                "label": step.get("label"),
                "status": step.get("status"),
                "required": step.get("required") is True,
                "attached": artifact_exists,
                "artifact_path": str(artifact_path),
                "artifact_sha256": _file_sha256(artifact_path) if artifact_exists else None,
                "error_count": len(errors) if isinstance(errors, list) else 0,
            }
        )
    return {
        "schema_version": "nac.m365-release-gate-evidence-index/v0.1",
        "status": evidence.get("status"),
        "generated_at": evidence.get("generated_at"),
        "workspace_id": summary.get("workspace_id"),
        "correlation_id": summary.get("correlation_id"),
        "evidence_completeness": summary.get("evidence_completeness"),
        "report_path": summary.get("report_path"),
        "json_path": summary.get("json_path"),
        "artifact_index_path": summary.get("artifact_index_path"),
        "artifacts": artifacts,
        "privacy": {
            "source_artifacts_must_be_redacted": True,
            "graph_requests_executed": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "storesRawCaseId": False,
            "readsSharePointFileContent": False,
        },
    }


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_release_gate_evidence_markdown(evidence: dict[str, Any]) -> str:
    summary = _dict(evidence.get("summary"))
    lines = [
        "# M365 Runtime Release Gate Evidence",
        "",
        f"- Status: `{evidence.get('status', 'UNKNOWN')}`",
        f"- Generated at: `{evidence.get('generated_at', '')}`",
        f"- Workspace: `{summary.get('workspace_id') or 'unknown'}`",
        f"- Correlation ID: `{summary.get('correlation_id') or 'unknown'}`",
        f"- Evidence completeness: `{summary.get('evidence_completeness', 'unknown')}`",
        f"- Graph requests executed by exporter: `{str(False).lower()}`",
        f"- Tenant writes/deletes executed by exporter: `{str(False).lower()}`",
        "",
        "## Steps",
        "",
        "| Step | Status | Artifact | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for step in evidence.get("steps", []):
        if not isinstance(step, dict):
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    _md(str(step.get("label", step.get("id", "unknown")))),
                    f"`{step.get('status', 'UNKNOWN')}`",
                    _md(str(step.get("artifact_path", ""))),
                    _md(_step_summary_text(step)),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Privacy Boundary",
            "",
            "- The exporter reads local redacted JSON artifacts only.",
            "- It does not call Microsoft Graph.",
            "- It does not write to or delete from the tenant.",
            "- It does not include raw case IDs, raw Graph paths, tokens, secrets or SharePoint file content.",
        ]
    )
    errors = evidence.get("errors")
    if isinstance(errors, list) and errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {_md(str(error))}" for error in errors)
    lines.append("")
    return "\n".join(lines)


def _runtime_smoke_step(path: Path, *, required: bool) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="runtime_smoke",
        label="runtime-smoke",
        artifact_path=path,
        required=required,
        artifact=artifact,
        load_error=error,
    )
    if artifact is None:
        return step
    summary = _dict(artifact.get("summary"))
    step["summary"] = {
        "workspaces": summary.get("workspaces"),
        "sites_read": summary.get("sites_read"),
        "missing_lists": summary.get("missing_lists"),
        "graph_rest_only": summary.get("graph_rest_only"),
        "raw_site_id_stored": summary.get("raw_site_id_stored"),
        "raw_site_url_stored": summary.get("raw_site_url_stored"),
        "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
        "stores_tokens_or_secrets": summary.get("stores_tokens_or_secrets"),
        "reads_sharepoint_file_content": summary.get("reads_sharepoint_file_content"),
        "list_items_read": summary.get("list_items_read"),
    }
    _expect_status_passed(step, artifact)
    _expect_summary_value(step, summary, "missing_lists", 0)
    _expect_summary_value(step, summary, "list_items_read", 0)
    _expect_privacy_flags(step, summary)
    return step


def _runtime_certificate_expiry_step(path: Path, *, required: bool) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="runtime_certificate_expiry",
        label="runtime-certificate-expiry-monitor",
        artifact_path=path,
        required=required,
        artifact=artifact,
        load_error=error,
    )
    if artifact is None:
        return step
    summary = _dict(artifact.get("summary"))
    step["summary"] = {
        "certificate_expires_at_utc": summary.get("certificate_expires_at_utc"),
        "certificate_days_until_expiry": summary.get("certificate_days_until_expiry"),
        "certificate_expiry_level": summary.get("certificate_expiry_level"),
        "certificate_expiry_warning_days": summary.get("certificate_expiry_warning_days"),
        "certificate_expiry_critical_days": summary.get("certificate_expiry_critical_days"),
        "certificate_rotation_required": summary.get("certificate_rotation_required"),
        "certificate_thumbprint_emitted": summary.get("certificate_thumbprint_emitted"),
        "runtime_metadata_thumbprint_matches_smoke": summary.get("runtime_metadata_thumbprint_matches_smoke"),
        "graph_rest_only": summary.get("graph_rest_only"),
        "raw_site_id_stored": summary.get("raw_site_id_stored"),
        "raw_site_url_stored": summary.get("raw_site_url_stored"),
        "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
        "stores_tokens_or_secrets": summary.get("stores_tokens_or_secrets"),
        "reads_sharepoint_file_content": summary.get("reads_sharepoint_file_content"),
        "credential_files_read": summary.get("credential_files_read"),
        "executes_graph_requests": summary.get("executes_graph_requests"),
    }
    _expect_status_passed(step, artifact)
    _expect_summary_value(step, summary, "certificate_expiry_level", "OK")
    _expect_summary_value(step, summary, "certificate_rotation_required", False)
    _expect_summary_value(step, summary, "certificate_thumbprint_emitted", False)
    _expect_summary_value(step, summary, "runtime_metadata_thumbprint_matches_smoke", True)
    _expect_summary_value(step, summary, "credential_files_read", False)
    _expect_summary_value(step, summary, "executes_graph_requests", False)
    _expect_privacy_flags(step, summary)
    return step


def _runtime_metadata_step(path: Path, *, required: bool) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="runtime_metadata",
        label="runtime-metadata",
        artifact_path=path,
        required=required,
        artifact=artifact,
        load_error=error,
    )
    if artifact is None:
        return step
    summary = _dict(artifact.get("summary"))
    step["summary"] = {
        "workspaces": summary.get("workspaces"),
        "sites_read": summary.get("sites_read"),
        "expected_lists": summary.get("expected_lists"),
        "expected_document_libraries": summary.get("expected_document_libraries"),
        "missing_lists": summary.get("missing_lists"),
        "missing_document_libraries": summary.get("missing_document_libraries"),
        "list_items_read": summary.get("list_items_read"),
        "graph_rest_only": summary.get("graph_rest_only"),
        "raw_site_id_stored": summary.get("raw_site_id_stored"),
        "raw_site_url_stored": summary.get("raw_site_url_stored"),
        "raw_list_id_stored": summary.get("raw_list_id_stored"),
        "raw_drive_id_stored": summary.get("raw_drive_id_stored"),
        "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
        "stores_tokens_or_secrets": summary.get("stores_tokens_or_secrets"),
        "reads_sharepoint_file_content": summary.get("reads_sharepoint_file_content"),
    }
    _expect_status_passed(step, artifact)
    _expect_summary_value(step, summary, "missing_lists", 0)
    _expect_summary_value(step, summary, "missing_document_libraries", 0)
    _expect_summary_value(step, summary, "list_items_read", 0)
    _expect_privacy_flags(step, summary)
    return step


def _mcp_suite_step(path: Path) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="mcp_smoke_suite",
        label="mcp-smoke-suite --mcp-suite-cleanup",
        artifact_path=path,
        required=True,
        artifact=artifact,
        load_error=error,
    )
    if artifact is None:
        return step
    summary = _dict(artifact.get("summary"))
    step["summary"] = {
        "workspace_id": summary.get("workspace_id"),
        "correlation_id": summary.get("correlation_id"),
        "positive_write_read_status": summary.get("positive_write_read_status"),
        "write_status": summary.get("write_status"),
        "read_status": summary.get("read_status"),
        "read_value_count": summary.get("read_value_count"),
        "cleanup_requested": summary.get("cleanup_requested"),
        "cleanup_status": summary.get("cleanup_status"),
        "cleanup_read_after_value_count": summary.get("cleanup_read_after_value_count"),
        "graph_rest_only": summary.get("graph_rest_only"),
        "raw_case_id_stored": summary.get("raw_case_id_stored"),
        "raw_write_payload_stored": summary.get("raw_write_payload_stored"),
        "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
        "stores_tokens_or_secrets": summary.get("stores_tokens_or_secrets"),
        "reads_sharepoint_file_content": summary.get("reads_sharepoint_file_content"),
    }
    _expect_status_passed(step, artifact)
    _expect_summary_value(step, summary, "positive_write_read_status", "PASSED")
    _expect_summary_value(step, summary, "write_status", "PASSED")
    _expect_summary_value(step, summary, "read_status", "PASSED")
    _expect_summary_value(step, summary, "cleanup_requested", True)
    _expect_summary_value(step, summary, "cleanup_status", "PASSED")
    _expect_summary_value(step, summary, "cleanup_read_after_value_count", 0)
    _expect_privacy_flags(step, summary)
    return step


def _mcp_inventory_step(path: Path) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="mcp_inventory_smoke",
        label="mcp-inventory-smoke",
        artifact_path=path,
        required=False,
        artifact=artifact,
        load_error=error,
    )
    if artifact is None:
        return step
    summary = _dict(artifact.get("summary"))
    privacy = _dict(artifact.get("privacy"))
    step["summary"] = {
        "workspace_id": summary.get("workspace_id"),
        "correlation_id": summary.get("correlation_id"),
        "tool_call_count": summary.get("tool_call_count"),
        "inventory_tool_count": summary.get("inventory_tool_count"),
        "interface_count": summary.get("interface_count"),
        "metadata_boundary_status": summary.get("metadata_boundary_status"),
        "owner_gated_boundary_status": summary.get("owner_gated_boundary_status"),
        "closed_gate_blocks": summary.get("closed_gate_blocks"),
        "graph_requests_executed": summary.get("graph_requests_executed"),
        "external_bnotk_calls_executed": summary.get("external_bnotk_calls_executed"),
        "raw_source_content_stored": summary.get("raw_source_content_stored"),
        "stores_tokens_or_secrets": privacy.get("storesTokensOrSecrets"),
        "reads_sharepoint_file_content": False,
    }
    _expect_status_passed(step, artifact)
    _expect_summary_value(step, summary, "tool_call_count", 4)
    _expect_summary_value(step, summary, "inventory_tool_count", 2)
    _expect_summary_minimum(step, summary, "interface_count", 1)
    _expect_summary_value(step, summary, "metadata_boundary_status", "allowed_metadata_only")
    _expect_summary_value(step, summary, "owner_gated_boundary_status", "owner_gate_required")
    _expect_summary_value(step, summary, "closed_gate_blocks", True)
    _expect_summary_value(step, summary, "graph_requests_executed", False)
    _expect_summary_value(step, summary, "external_bnotk_calls_executed", False)
    _expect_summary_value(step, summary, "raw_source_content_stored", False)
    _expect_inventory_privacy_flags(step, privacy)
    return step


def _mcp_leftover_step(path: Path) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="mcp_leftover_dry_run",
        label="mcp-smoke-leftover-cleanup --mcp-leftover-dry-run",
        artifact_path=path,
        required=True,
        artifact=artifact,
        load_error=error,
    )
    if artifact is None:
        return step
    summary = _dict(artifact.get("summary"))
    step["summary"] = {
        "workspace_id": summary.get("workspace_id"),
        "correlation_id": summary.get("correlation_id"),
        "cleanup_target": summary.get("cleanup_target"),
        "read_before_value_count": summary.get("read_before_value_count"),
        "delete_requested": summary.get("delete_requested"),
        "deleted_value_count": summary.get("deleted_value_count"),
        "read_after_value_count": summary.get("read_after_value_count"),
        "graph_rest_only": summary.get("graph_rest_only"),
        "raw_case_id_stored": summary.get("raw_case_id_stored"),
        "raw_item_id_stored": summary.get("raw_item_id_stored"),
        "raw_graph_path_stored": summary.get("raw_graph_path_stored"),
        "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
        "stores_tokens_or_secrets": summary.get("stores_tokens_or_secrets"),
        "reads_sharepoint_file_content": summary.get("reads_sharepoint_file_content"),
    }
    _expect_status_passed(step, artifact)
    _expect_summary_value(step, summary, "delete_requested", False)
    _expect_summary_value(step, summary, "read_after_value_count", 0)
    _expect_privacy_flags(step, summary)
    return step


def _base_step(
    *,
    step_id: str,
    label: str,
    artifact_path: Path,
    required: bool,
    artifact: dict[str, Any] | None,
    load_error: str | None,
) -> dict[str, Any]:
    if artifact is not None:
        status = "PASSED"
        errors: list[str] = []
    elif required:
        status = "BLOCKED"
        errors = [load_error] if load_error else []
    elif load_error and not load_error.startswith("missing evidence artifact:"):
        status = "FAILED"
        errors = [load_error]
    else:
        status = "NOT_ATTACHED"
        errors = []
    return {
        "id": step_id,
        "label": label,
        "status": status,
        "required": required,
        "artifact_path": str(artifact_path),
        "summary": {},
        "errors": errors,
    }


def _load_optional_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.exists():
        return None, f"missing evidence artifact: {path}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"invalid evidence artifact {path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"invalid evidence artifact {path}: root must be an object"
    return payload, None


def _expect_status_passed(step: dict[str, Any], artifact: dict[str, Any]) -> None:
    if artifact.get("status") != "PASSED":
        _fail(step, f"{step['label']} artifact status is not PASSED")


def _expect_summary_value(step: dict[str, Any], summary: dict[str, Any], key: str, expected: Any) -> None:
    if summary.get(key) != expected:
        _fail(step, f"{step['label']} summary.{key} expected {expected!r}, got {summary.get(key)!r}")


def _expect_summary_minimum(step: dict[str, Any], summary: dict[str, Any], key: str, minimum: int) -> None:
    value = summary.get(key)
    if not isinstance(value, int) or value < minimum:
        _fail(step, f"{step['label']} summary.{key} expected at least {minimum}, got {value!r}")


def _expect_privacy_flags(step: dict[str, Any], summary: dict[str, Any]) -> None:
    true_flags = ["graph_rest_only"]
    false_flags = [
        "raw_case_id_stored",
        "raw_write_payload_stored",
        "raw_site_id_stored",
        "raw_site_url_stored",
        "raw_list_id_stored",
        "raw_drive_id_stored",
        "raw_item_id_stored",
        "raw_graph_path_stored",
        "raw_graph_response_stored",
        "stores_tokens_or_secrets",
        "reads_sharepoint_file_content",
    ]
    for flag in true_flags:
        if flag in summary and summary.get(flag) is not True:
            _fail(step, f"{step['label']} privacy flag {flag} must be true")
    for flag in false_flags:
        if flag in summary and summary.get(flag) is not False:
            _fail(step, f"{step['label']} privacy flag {flag} must be false")


def _expect_inventory_privacy_flags(step: dict[str, Any], privacy: dict[str, Any]) -> None:
    if privacy.get("metadataOnly") is not True:
        _fail(step, f"{step['label']} privacy flag metadataOnly must be true")
    for flag in (
        "storesSourceFullText",
        "storesRawXsd",
        "storesCredentials",
        "storesTokensOrSecrets",
        "storesMatterData",
        "storesMessagePayloads",
        "executesGraphRequests",
        "callsExternalBnotkSystems",
    ):
        if privacy.get(flag) is not False:
            _fail(step, f"{step['label']} privacy flag {flag} must be false")


def _fail(step: dict[str, Any], message: str) -> None:
    step["status"] = "FAILED"
    step["errors"].append(message)


def _overall_status(steps: list[dict[str, Any]], errors: list[str]) -> str:
    if any(step["status"] == "BLOCKED" for step in steps):
        return "BLOCKED"
    if errors or any(step["status"] == "FAILED" for step in steps):
        return "FAILED"
    return "PASSED"


def _evidence_completeness(steps: list[dict[str, Any]]) -> str:
    if any(step["status"] in {"BLOCKED", "FAILED"} for step in steps):
        return "incomplete"
    required_for_completeness = [
        step for step in steps if step.get("id") != "mcp_inventory_smoke"
    ]
    if all(step["status"] == "PASSED" for step in required_for_completeness):
        return "complete_release_gate_artifacts"
    if all(step["status"] == "PASSED" for step in required_for_completeness if step["required"]):
        return "mcp_artifacts_only"
    return "incomplete"


def _validate_expected_value(
    steps: list[dict[str, Any]],
    *,
    field: str,
    expected: str | None,
    errors: list[str],
) -> None:
    if not expected:
        return
    for step in steps:
        summary = _dict(step.get("summary"))
        observed = summary.get(field)
        if observed is None:
            continue
        if observed != expected:
            step["status"] = "FAILED"
            message = f"{step['label']} summary.{field} expected {expected!r}, got {observed!r}"
            step["errors"].append(message)
            errors.append(message)


def _first_summary_value(steps: list[dict[str, Any]], key: str) -> Any:
    for step in steps:
        value = _dict(step.get("summary")).get(key)
        if value is not None:
            return value
    return None


def _all_privacy_flag(steps: list[dict[str, Any]], key: str, *, default: bool) -> bool:
    values = [_dict(step.get("summary")).get(key) for step in steps]
    observed = [value for value in values if isinstance(value, bool)]
    if not observed:
        return default
    return all(observed)


def _any_privacy_flag(steps: list[dict[str, Any]], key: str) -> bool:
    return any(_dict(step.get("summary")).get(key) is True for step in steps)


def _step_summary_text(step: dict[str, Any]) -> str:
    summary = _dict(step.get("summary"))
    parts = []
    for key in (
        "workspaces",
        "sites_read",
        "workspace_id",
        "correlation_id",
        "certificate_expiry_level",
        "certificate_days_until_expiry",
        "interface_count",
        "metadata_boundary_status",
        "owner_gated_boundary_status",
        "closed_gate_blocks",
        "positive_write_read_status",
        "cleanup_status",
        "read_after_value_count",
    ):
        value = summary.get(key)
        if value is not None:
            parts.append(f"{key}={value}")
    if parts:
        return "; ".join(parts)
    if step.get("status") == "NOT_ATTACHED":
        return "optional runtime artifact not attached"
    if step.get("errors"):
        return "; ".join(str(error) for error in step["errors"])
    return "redacted artifact attached"


def _resolve(repo_root: Path, path: Path | None, default: Path) -> Path:
    raw = path or default
    return raw if raw.is_absolute() else repo_root / raw


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
