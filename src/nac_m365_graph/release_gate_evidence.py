from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


DEFAULT_EVIDENCE_OUTPUT = Path("out/m365/teams-sharepoint/release-gate-evidence.redacted.md")
DEFAULT_EVIDENCE_JSON_OUTPUT = Path("out/m365/teams-sharepoint/release-gate-evidence.redacted.json")
DEFAULT_ARTIFACT_INDEX_OUTPUT = Path("out/m365/teams-sharepoint/release-gate-artifact-index.redacted.json")
DEFAULT_RUNTIME_ENV_BOOTSTRAP_ARTIFACT = Path("out/m365/teams-sharepoint/runtime-env-bootstrap.redacted.json")
DEFAULT_MCP_INVENTORY_ARTIFACT = Path("out/m365/teams-sharepoint/mcp-inventory-smoke.redacted.json")
DEFAULT_MATTER_ACCESS_ARTIFACT = Path("out/m365/teams-sharepoint/matter-access-delegation-smoke.redacted.json")
DEFAULT_MATTER_ACCESS_APPLY_READINESS_ARTIFACT = Path(
    "out/m365/teams-sharepoint/matter-access-apply-readiness.redacted.json"
)
DEFAULT_MCP_SMOKE_SUITE_ARTIFACT = Path("out/m365/teams-sharepoint/mcp-smoke-suite.redacted.json")
DEFAULT_MCP_LEFTOVER_ARTIFACT = Path("out/m365/teams-sharepoint/mcp-smoke-leftover-cleanup.redacted.json")
DEFAULT_RUNTIME_CERTIFICATE_EXPIRY_ARTIFACT = Path(
    "out/m365/teams-sharepoint/runtime-certificate-expiry-monitor.redacted.json"
)
DEFAULT_RUNTIME_SMOKE_ARTIFACT = Path("out/m365/teams-sharepoint/runtime-smoke.redacted.json")
DEFAULT_RUNTIME_METADATA_ARTIFACT = Path("out/m365/teams-sharepoint/runtime-metadata.redacted.json")

_RUNTIME_ENV_BOOTSTRAP_ALLOWED_ENV_KEYS = {
    "M365_TENANT_ID",
    "M365_RUNTIME_CLIENT_ID",
    "M365_RUNTIME_CLIENT_CERTIFICATE_PATH",
    "M365_RUNTIME_CLIENT_KEY_PATH",
}
_RUNTIME_ENV_BOOTSTRAP_SECRET_KEYS = {
    "M365_RUNTIME_GRAPH_ACCESS_TOKEN",
    "M365_RUNTIME_GRAPH_ACCESS_TOKEN_FILE",
    "M365_RUNTIME_CLIENT_SECRET",
    "M365_RUNTIME_CLIENT_KEY_PASSWORD",
}


def build_release_gate_evidence(
    *,
    repo_root: Path,
    mcp_inventory_artifact: Path | None = None,
    matter_access_artifact: Path | None = None,
    matter_access_apply_readiness_artifact: Path | None = None,
    mcp_suite_artifact: Path | None = None,
    mcp_leftover_artifact: Path | None = None,
    runtime_env_bootstrap_artifact: Path | None = None,
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
        "runtime_env_bootstrap": _resolve(
            repo_root,
            runtime_env_bootstrap_artifact,
            DEFAULT_RUNTIME_ENV_BOOTSTRAP_ARTIFACT,
        ),
        "runtime_smoke": _resolve(repo_root, runtime_smoke_artifact, DEFAULT_RUNTIME_SMOKE_ARTIFACT),
        "runtime_metadata": _resolve(repo_root, runtime_metadata_artifact, DEFAULT_RUNTIME_METADATA_ARTIFACT),
        "mcp_inventory_smoke": _resolve(repo_root, mcp_inventory_artifact, DEFAULT_MCP_INVENTORY_ARTIFACT),
        "matter_access_delegation_smoke": _resolve(
            repo_root,
            matter_access_artifact,
            DEFAULT_MATTER_ACCESS_ARTIFACT,
        ),
        "matter_access_apply_readiness": _resolve(
            repo_root,
            matter_access_apply_readiness_artifact,
            DEFAULT_MATTER_ACCESS_APPLY_READINESS_ARTIFACT,
        ),
        "mcp_smoke_suite": _resolve(repo_root, mcp_suite_artifact, DEFAULT_MCP_SMOKE_SUITE_ARTIFACT),
        "mcp_leftover_dry_run": _resolve(repo_root, mcp_leftover_artifact, DEFAULT_MCP_LEFTOVER_ARTIFACT),
    }

    steps = [
        _runtime_certificate_expiry_step(paths["runtime_certificate_expiry"], required=require_runtime_artifacts),
        _runtime_env_bootstrap_step(paths["runtime_env_bootstrap"]),
        _runtime_smoke_step(paths["runtime_smoke"], required=require_runtime_artifacts),
        _runtime_metadata_step(paths["runtime_metadata"], required=require_runtime_artifacts),
        _mcp_inventory_step(paths["mcp_inventory_smoke"]),
        _matter_access_step(paths["matter_access_delegation_smoke"]),
        _matter_access_apply_readiness_step(paths["matter_access_apply_readiness"]),
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
        "runtime_env_bootstrap_status": steps[1]["status"],
        "runtime_smoke_status": steps[2]["status"],
        "runtime_metadata_status": steps[3]["status"],
        "mcp_inventory_smoke_status": steps[4]["status"],
        "matter_access_delegation_smoke_status": steps[5]["status"],
        "matter_access_apply_readiness_status": steps[6]["status"],
        "mcp_smoke_suite_status": steps[7]["status"],
        "mcp_leftover_dry_run_status": steps[8]["status"],
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


def attach_release_gate_retention_reference(
    evidence: dict[str, Any],
    *,
    artifact_dir: str,
    retention_index_path: str,
    copied_artifact_count: int,
) -> dict[str, Any]:
    summary = evidence.setdefault("summary", {})
    if not isinstance(summary, dict):
        summary = {}
        evidence["summary"] = summary
    summary["release_gate_run_artifact_dir"] = artifact_dir
    summary["release_gate_retention_index_path"] = retention_index_path
    summary["retained_artifact_count"] = copied_artifact_count
    summary["retention_index_attached"] = True
    attach_release_gate_artifact_index(evidence)
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
        "retention": _retention_summary(summary),
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
    ]
    retention = _retention_summary(summary)
    if retention["attached"]:
        lines.extend(
            [
                "## Artifact Retention",
                "",
                f"- Run artifact directory: `{retention['artifact_dir']}`",
                f"- Retention index: `{retention['retention_index_path']}`",
                f"- Retained artifacts: `{retention['copied_artifact_count']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Steps",
            "",
            "| Step | Status | Artifact | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
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


def _runtime_env_bootstrap_step(path: Path) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="runtime_env_bootstrap",
        label="runtime-env-bootstrap",
        artifact_path=path,
        required=False,
        artifact=artifact,
        load_error=error,
    )
    if artifact is None:
        return step
    summary = _dict(artifact.get("summary"))
    env_overlay_variable_names = _string_list(summary.get("env_overlay_variable_names"))
    step["summary"] = {
        "runtime_state_attached": summary.get("runtime_state_attached"),
        "preferred_authentication_mode": summary.get("preferred_authentication_mode"),
        "runtime_authentication_mode": summary.get("runtime_authentication_mode"),
        "explicit_runtime_credential_mode": summary.get("explicit_runtime_credential_mode"),
        "env_overlay_variable_count": summary.get("env_overlay_variable_count"),
        "env_overlay_variable_names": env_overlay_variable_names,
        "tenant_id_resolved_from_state": summary.get("tenant_id_resolved_from_state"),
        "client_id_resolved_from_state": summary.get("client_id_resolved_from_state"),
        "tenant_id_emitted": summary.get("tenant_id_emitted"),
        "client_id_emitted": summary.get("client_id_emitted"),
        "certificate_thumbprint_emitted": summary.get("certificate_thumbprint_emitted"),
        "credential_files_read": summary.get("credential_files_read"),
        "secret_env_values_read": summary.get("secret_env_values_read"),
        "executes_graph_requests": summary.get("executes_graph_requests"),
        "executes_graph_writes": summary.get("executes_graph_writes"),
        "owner_gate_required_for_live_use": summary.get("owner_gate_required_for_live_use"),
        "graph_rest_only": True,
        "raw_graph_response_stored": False,
        "stores_tokens_or_secrets": summary.get("stores_tokens_or_secrets"),
        "reads_sharepoint_file_content": False,
    }
    _expect_status_passed(step, artifact)
    if artifact.get("schema_version") != "nac.m365-runtime-env-bootstrap/v0.1":
        _fail(step, f"{step['label']} schema_version is not nac.m365-runtime-env-bootstrap/v0.1")
    _expect_summary_value(step, summary, "runtime_state_attached", True)
    _expect_summary_value(step, summary, "preferred_authentication_mode", "client_credentials_with_certificate")
    _expect_summary_value(step, summary, "runtime_authentication_mode", "client_credentials_with_certificate")
    _expect_summary_value(step, summary, "tenant_id_emitted", False)
    _expect_summary_value(step, summary, "client_id_emitted", False)
    _expect_summary_value(step, summary, "certificate_thumbprint_emitted", False)
    _expect_summary_value(step, summary, "credential_files_read", False)
    _expect_summary_value(step, summary, "secret_env_values_read", False)
    _expect_summary_value(step, summary, "executes_graph_requests", False)
    _expect_summary_value(step, summary, "executes_graph_writes", False)
    _expect_summary_value(step, summary, "stores_tokens_or_secrets", False)
    _expect_summary_value(step, summary, "owner_gate_required_for_live_use", True)
    _expect_runtime_env_overlay_names(step, summary, env_overlay_variable_names)
    _expect_privacy_flags(step, step["summary"])
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


def _matter_access_step(path: Path) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="matter_access_delegation_smoke",
        label="matter-access-smoke",
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
        "contract_id": summary.get("contract_id"),
        "workspace_operation_count": summary.get("workspace_operation_count"),
        "operation_count": summary.get("operation_count"),
        "mcp_tool_contract_count": summary.get("mcp_tool_contract_count"),
        "owner_gated_workspace_operations": summary.get("owner_gated_workspace_operations"),
        "graph_rest_only": summary.get("graph_rest_only"),
        "legacy_sharepoint_api_allowed": summary.get("legacy_sharepoint_api_allowed"),
        "executes_graph_requests": summary.get("executes_graph_requests"),
        "executes_graph_writes": summary.get("executes_graph_writes"),
        "tenant_mutation_allowed": summary.get("tenant_mutation_allowed"),
        "team_membership_mutation_allowed": summary.get("team_membership_mutation_allowed"),
        "raw_graph_path_stored": summary.get("raw_graph_path_stored"),
        "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
        "stores_tokens_or_secrets": privacy.get("storesTokensOrSecrets"),
        "reads_sharepoint_file_content": privacy.get("readsSharePointFileContent"),
        "stores_matter_payloads": privacy.get("storesMatterPayloads"),
    }
    _expect_status_passed(step, artifact)
    if artifact.get("schema_version") != "nac.m365-matter-access-delegation-smoke/v0.1":
        _fail(step, f"{step['label']} schema_version is not nac.m365-matter-access-delegation-smoke/v0.1")
    _expect_summary_value(step, summary, "contract_id", "m365.matter_access_delegation")
    _expect_summary_value(step, summary, "workspace_operation_count", 6)
    _expect_summary_value(step, summary, "mcp_tool_contract_count", 4)
    _expect_summary_value(step, summary, "owner_gated_workspace_operations", 3)
    _expect_summary_value(step, summary, "graph_rest_only", True)
    _expect_summary_value(step, summary, "legacy_sharepoint_api_allowed", False)
    _expect_summary_value(step, summary, "executes_graph_requests", False)
    _expect_summary_value(step, summary, "executes_graph_writes", False)
    _expect_summary_value(step, summary, "tenant_mutation_allowed", False)
    _expect_summary_value(step, summary, "team_membership_mutation_allowed", False)
    _expect_summary_value(step, summary, "raw_graph_path_stored", False)
    _expect_summary_value(step, summary, "raw_graph_response_stored", False)
    _expect_matter_access_privacy_flags(step, privacy)
    return step


def _matter_access_apply_readiness_step(path: Path) -> dict[str, Any]:
    artifact, error = _load_optional_json(path)
    step = _base_step(
        step_id="matter_access_apply_readiness",
        label="matter-access-apply-readiness",
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
        "contract_id": summary.get("contract_id"),
        "future_apply_mode": summary.get("future_apply_mode"),
        "workspace_operation_count": summary.get("workspace_operation_count"),
        "planned_apply_operation_count": summary.get("planned_apply_operation_count"),
        "grant_request_ready": summary.get("grant_request_ready"),
        "audit_append_ready": summary.get("audit_append_ready"),
        "required_write_approval": summary.get("required_write_approval"),
        "owner_gate_required": summary.get("owner_gate_required"),
        "role_case_purpose_gate_required": summary.get("role_case_purpose_gate_required"),
        "reason_required": summary.get("reason_required"),
        "valid_from_required": summary.get("valid_from_required"),
        "valid_until_required": summary.get("valid_until_required"),
        "valid_until_after_valid_from_required": summary.get("valid_until_after_valid_from_required"),
        "approver_required": summary.get("approver_required"),
        "audit_correlation_required": summary.get("audit_correlation_required"),
        "graph_rest_only": summary.get("graph_rest_only"),
        "executes_graph_requests": summary.get("executes_graph_requests"),
        "executes_graph_writes": summary.get("executes_graph_writes"),
        "tenant_mutation_allowed": summary.get("tenant_mutation_allowed"),
        "team_membership_mutation_allowed": summary.get("team_membership_mutation_allowed"),
        "sharepoint_item_permission_mutation_allowed": summary.get("sharepoint_item_permission_mutation_allowed"),
        "raw_graph_path_stored": summary.get("raw_graph_path_stored"),
        "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
        "stores_tokens_or_secrets": privacy.get("storesTokensOrSecrets"),
        "reads_sharepoint_file_content": privacy.get("readsSharePointFileContent"),
        "stores_matter_payloads": privacy.get("storesMatterPayloads"),
    }
    _expect_status_passed(step, artifact)
    if artifact.get("schema_version") != "nac.m365-matter-access-apply-readiness/v0.1":
        _fail(step, f"{step['label']} schema_version is not nac.m365-matter-access-apply-readiness/v0.1")
    _expect_summary_value(step, summary, "contract_id", "m365.matter_access_delegation")
    _expect_summary_value(step, summary, "future_apply_mode", "owner_gated_graph_rest_item_writes")
    _expect_summary_value(step, summary, "workspace_operation_count", 6)
    _expect_summary_value(step, summary, "planned_apply_operation_count", 2)
    for flag in (
        "grant_request_ready",
        "audit_append_ready",
        "required_write_approval",
        "owner_gate_required",
        "role_case_purpose_gate_required",
        "reason_required",
        "valid_from_required",
        "valid_until_required",
        "valid_until_after_valid_from_required",
        "approver_required",
        "audit_correlation_required",
        "graph_rest_only",
    ):
        _expect_summary_value(step, summary, flag, True)
    for flag in (
        "automation_may_approve_grant",
        "legacy_sharepoint_api_allowed",
        "executes_graph_requests",
        "executes_graph_writes",
        "tenant_mutation_allowed",
        "team_membership_mutation_allowed",
        "sharepoint_item_permission_mutation_allowed",
        "raw_graph_path_stored",
        "raw_graph_response_stored",
    ):
        _expect_summary_value(step, summary, flag, False)
    _expect_matter_access_privacy_flags(step, privacy)
    if privacy.get("sharePointItemPermissionMutationAllowed") is not False:
        _fail(step, f"{step['label']} privacy flag sharePointItemPermissionMutationAllowed must be false")
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


def _expect_runtime_env_overlay_names(
    step: dict[str, Any],
    summary: dict[str, Any],
    env_overlay_variable_names: list[str],
) -> None:
    count = summary.get("env_overlay_variable_count")
    if not isinstance(count, int) or count != len(env_overlay_variable_names):
        _fail(
            step,
            f"{step['label']} summary.env_overlay_variable_count expected {len(env_overlay_variable_names)!r}, got {count!r}",
        )
    for name in env_overlay_variable_names:
        if name in _RUNTIME_ENV_BOOTSTRAP_SECRET_KEYS:
            _fail(step, f"{step['label']} env overlay must not expose secret variable {name}")
        if name not in _RUNTIME_ENV_BOOTSTRAP_ALLOWED_ENV_KEYS:
            _fail(step, f"{step['label']} env overlay contains unexpected variable {name}")


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


def _expect_matter_access_privacy_flags(step: dict[str, Any], privacy: dict[str, Any]) -> None:
    if privacy.get("metadataOnly") is not True:
        _fail(step, f"{step['label']} privacy flag metadataOnly must be true")
    for flag in (
        "storesSourceFullText",
        "storesRawXsd",
        "storesCredentials",
        "storesTokensOrSecrets",
        "storesMatterData",
        "storesMatterPayloads",
        "storesMessagePayloads",
        "storesRawGraphPath",
        "storesRawGraphResponse",
        "readsSharePointFileContent",
        "executesGraphRequests",
        "executesGraphWrites",
        "tenantWritesExecuted",
        "teamMembershipMutationAllowed",
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
        step
        for step in steps
        if step.get("id")
        not in {
            "runtime_env_bootstrap",
            "mcp_inventory_smoke",
            "matter_access_delegation_smoke",
            "matter_access_apply_readiness",
        }
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


def _retention_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "attached": summary.get("retention_index_attached") is True,
        "artifact_dir": summary.get("release_gate_run_artifact_dir"),
        "retention_index_path": summary.get("release_gate_retention_index_path"),
        "copied_artifact_count": summary.get("retained_artifact_count"),
    }


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
        "env_overlay_variable_count",
        "runtime_authentication_mode",
        "interface_count",
        "metadata_boundary_status",
        "owner_gated_boundary_status",
        "closed_gate_blocks",
        "workspace_operation_count",
        "owner_gated_workspace_operations",
        "future_apply_mode",
        "planned_apply_operation_count",
        "grant_request_ready",
        "audit_append_ready",
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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _md(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
