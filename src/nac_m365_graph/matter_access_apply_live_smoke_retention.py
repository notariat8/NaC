from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT = (
    REPO_ROOT / "out" / "m365" / "teams-sharepoint" / "matter-access-apply-live-smokes"
)
RETENTION_JSON_NAME = "matter-access-apply-live-smoke-retention.redacted.json"
RETENTION_REPORT_NAME = "matter-access-apply-live-smoke-retention.redacted.md"
RETENTION_INDEX_JSON_NAME = "matter-access-apply-live-smoke-retention-index.redacted.json"
RETENTION_INDEX_REPORT_NAME = "matter-access-apply-live-smoke-retention-index.redacted.md"
RETENTION_READINESS_JSON_NAME = "matter-access-apply-live-smoke-retention-readiness.redacted.json"
RETENTION_READINESS_REPORT_NAME = "matter-access-apply-live-smoke-retention-readiness.redacted.md"
RETAINED_SMOKE_ARTIFACT_NAME = "matter-access-apply-smoke.redacted.json"

SCHEMA_VERSION = "nac.m365-matter-access-apply-live-smoke-retention/v0.1"
INDEX_SCHEMA_VERSION = "nac.m365-matter-access-apply-live-smoke-retention-index/v0.1"
READINESS_SCHEMA_VERSION = "nac.m365-matter-access-apply-live-smoke-retention-readiness/v0.1"
REDACTION_SHAPE_SCHEMA_VERSION = "nac.m365-matter-access-apply-live-smoke-redaction-shape/v0.1"
UPGRADE_ADVICE_SCHEMA_VERSION = "nac.m365-matter-access-apply-live-smoke-retention-upgrade-advice/v0.1"
UPGRADE_PLAN_SCHEMA_VERSION = "nac.m365-matter-access-apply-live-smoke-retention-upgrade-plan/v0.1"

ALLOWED_FALSE_PRIVACY_FLAG_KEYS = {
    "storesrawgraphpath",
    "storesrawgraphresponse",
    "storesrawwritepayload",
    "storestokensorsecrets",
    "storesmatterpayloads",
    "readsSharePointFileContent".lower(),
    "raw_graph_path_stored",
    "raw_graph_response_stored",
    "raw_write_payload_stored",
    "stores_tokens_or_secrets",
    "stores_matter_payloads",
    "reads_sharepoint_file_content",
}
FORBIDDEN_REDACTION_SHAPE_KEYS = {
    "accesstoken",
    "authorization",
    "bearertoken",
    "certificatesecret",
    "clientsecret",
    "documentcontent",
    "graphpath",
    "graphresponse",
    "mandatepayload",
    "matterpayload",
    "password",
    "privatekey",
    "privatedocumentcontent",
    "privatepayload",
    "rawgraphpath",
    "rawgraphresponse",
    "rawwritepayload",
    "refreshtoken",
    "requestbody",
    "responsebody",
    "secret",
    "token",
    "writepayload",
}
FORBIDDEN_REDACTION_SHAPE_VALUE_MARKERS = (
    "BEGIN " + "PRIVATE KEY",
    "PRIVATE " + "KEY",
    "Authorization:",
    "Bearer ",
    "access_token",
    "client" + "_secret",
    "refresh_token",
    "password" + "=",
    "https://graph.microsoft.com/",
    "/sites/",
    "/drives/",
    "/lists/",
    "fields/",
    "Akteninhalt",
    "Mandatswert",
)


def retain_matter_access_apply_live_smoke_artifact(
    artifact_path: Path,
    *,
    retention_root: Path = DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT,
    now_utc: str | None = None,
) -> dict[str, Any]:
    generated_at = now_utc or _now()
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _blocked_retention(generated_at, artifact_path, retention_root, [str(exc)])

    redaction_shape = validate_matter_access_apply_live_smoke_redaction_shape(artifact)
    errors = validate_matter_access_apply_live_smoke_artifact(artifact)
    errors.extend(redaction_shape.get("errors", []))
    summary = _artifact_summary(artifact)
    correlation_id = str(summary.get("correlation_id") or "")
    workspace_id = str(summary.get("workspace_id") or "")
    artifact_dir = retention_root / _safe_segment(correlation_id or "missing-correlation-id")
    retained_artifact_path = artifact_dir / RETAINED_SMOKE_ARTIFACT_NAME
    retention_json_path = artifact_dir / RETENTION_JSON_NAME
    retention_report_path = artifact_dir / RETENTION_REPORT_NAME
    index_json_path = retention_root / RETENTION_INDEX_JSON_NAME
    index_report_path = retention_root / RETENTION_INDEX_REPORT_NAME

    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED" if errors else "PASSED",
        "generated_at": generated_at,
        "summary": {
            "workspace_id": workspace_id or None,
            "correlation_id": correlation_id or None,
            "source_artifact_path": str(artifact_path),
            "artifact_dir": str(artifact_dir),
            "retained_artifact_path": str(retained_artifact_path),
            "retention_json_path": str(retention_json_path),
            "retention_report_path": str(retention_report_path),
            "retention_index_json_path": str(index_json_path),
            "retention_index_report_path": str(index_report_path),
            "source_artifact_sha256": _sha256_file(artifact_path) if artifact_path.is_file() else None,
            "retained_artifact_sha256": None,
            "live_smoke_status": artifact.get("status"),
            "write_tools": summary.get("write_tools"),
            "write_lists": summary.get("write_lists"),
            "planned_write_count": summary.get("planned_write_count"),
            "grant_read_value_count": summary.get("grant_read_value_count"),
            "audit_read_value_count": summary.get("audit_read_value_count"),
            "cleanup_requested": summary.get("cleanup_requested"),
            "grant_cleanup_read_after_value_count": summary.get("grant_cleanup_read_after_value_count"),
            "audit_cleanup_read_after_value_count": summary.get("audit_cleanup_read_after_value_count"),
            "source_executed_graph_requests": summary.get("executed_graph_requests"),
            "source_executed_graph_writes": summary.get("executed_graph_writes"),
            "source_sharepoint_item_writes_executed": summary.get("sharepoint_item_writes_executed"),
            "retention_executes_graph_requests": False,
            "retention_executes_graph_writes": False,
            "retention_tenant_writes_executed": False,
            "retention_tenant_deletes_executed": False,
            "graph_rest_only": summary.get("graph_rest_only"),
            "stores_tokens_or_secrets": summary.get("stores_tokens_or_secrets"),
            "stores_matter_payloads": _privacy_flag(artifact, "storesMatterPayloads"),
            "raw_graph_path_stored": summary.get("raw_graph_path_stored"),
            "raw_graph_response_stored": summary.get("raw_graph_response_stored"),
            "raw_write_payload_stored": summary.get("raw_write_payload_stored"),
            "reads_sharepoint_file_content": summary.get("reads_sharepoint_file_content"),
            "redaction_shape_status": redaction_shape.get("status"),
            "redaction_shape_violation_count": _dict(redaction_shape.get("summary")).get("violation_count"),
            "redaction_shape_checked_node_count": _dict(redaction_shape.get("summary")).get("checked_node_count"),
        },
        "checks": _retention_checks(errors),
        "errors": errors,
        "redaction_shape": redaction_shape,
        "privacy": {
            "source_artifact_must_be_redacted": True,
            "sourceArtifactRedactionShapeChecked": True,
            "retentionReadsLocalRedactedArtifactOnly": True,
            "retentionExecutesGraphRequests": False,
            "retentionExecutesGraphWrites": False,
            "retentionTenantWritesExecuted": False,
            "retentionTenantDeletesExecuted": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "storesRawWritePayload": False,
            "readsSharePointFileContent": False,
        },
    }
    if errors:
        return payload

    artifact_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(artifact_path, retained_artifact_path)
    payload["summary"]["retained_artifact_sha256"] = _sha256_file(retained_artifact_path)
    _write_json(payload, retention_json_path)
    _write_text(format_matter_access_apply_live_smoke_retention(payload), retention_report_path)
    index = build_matter_access_apply_live_smoke_retention_index(retention_root=retention_root)
    _write_json(index, index_json_path)
    _write_text(format_matter_access_apply_live_smoke_retention_index(index), index_report_path)
    return payload


def validate_matter_access_apply_live_smoke_artifact(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = _artifact_summary(artifact)
    privacy = _dict(artifact.get("privacy"))
    if artifact.get("schema_version") != "nac.m365-matter-access-apply-smoke/v0.1":
        errors.append("artifact schema_version must be nac.m365-matter-access-apply-smoke/v0.1")
    if artifact.get("status") != "PASSED":
        errors.append("artifact status must be PASSED")
    if not summary.get("workspace_id"):
        errors.append("artifact summary.workspace_id is required")
    if not summary.get("correlation_id"):
        errors.append("artifact summary.correlation_id is required")
    _expect(summary, "write_tools", ["grant_request", "audit_append"], errors)
    _expect(summary, "write_lists", ["Vertretungsfreigaben", "AuditJournalLite"], errors)
    _expect(summary, "planned_write_count", 2, errors)
    _expect(summary, "grant_read_value_count", 1, errors)
    _expect(summary, "audit_read_value_count", 1, errors)
    _expect(summary, "cleanup_requested", True, errors)
    _expect(summary, "grant_cleanup_read_after_value_count", 0, errors)
    _expect(summary, "audit_cleanup_read_after_value_count", 0, errors)
    for key in (
        "executed_graph_requests",
        "executed_graph_writes",
        "sharepoint_item_writes_executed",
        "graph_rest_only",
    ):
        _expect(summary, key, True, errors)
    for key in (
        "tenant_mutation_allowed",
        "team_membership_mutation_allowed",
        "sharepoint_item_permission_mutation_allowed",
        "raw_graph_path_stored",
        "raw_graph_response_stored",
        "raw_write_payload_stored",
        "stores_tokens_or_secrets",
        "reads_sharepoint_file_content",
    ):
        _expect(summary, key, False, errors)
    for key in ("storesTokensOrSecrets", "storesMatterPayloads", "storesRawGraphPath", "storesRawGraphResponse"):
        if privacy.get(key) is not False:
            errors.append(f"artifact privacy.{key} must be false")
    return errors


def validate_matter_access_apply_live_smoke_redaction_shape(artifact: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, str]] = []
    checked_node_count = 0
    for path, value in _walk_json(artifact):
        checked_node_count += 1
        if path:
            key = path[-1]
            if isinstance(key, str) and _is_forbidden_redaction_shape_key(key, value):
                violations.append(
                    {
                        "path": _format_json_path(path),
                        "reason": "forbidden_key",
                        "marker": key,
                    }
                )
        if isinstance(value, str):
            marker = _forbidden_value_marker(value)
            if marker is not None:
                violations.append(
                    {
                        "path": _format_json_path(path),
                        "reason": "forbidden_value_marker",
                        "marker": marker,
                    }
                )
    return {
        "schema_version": REDACTION_SHAPE_SCHEMA_VERSION,
        "status": "PASSED" if not violations else "BLOCKED",
        "summary": {
            "checked_node_count": checked_node_count,
            "violation_count": len(violations),
            "executes_graph_requests": False,
            "tenant_writes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "violations": violations,
        "errors": [
            f"artifact redaction shape violation at {item['path']}: {item['reason']} {item['marker']!r}"
            for item in violations
        ],
        "privacy": {
            "checksLocalArtifactOnly": True,
            "executesGraphRequests": False,
            "tenantWritesExecuted": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def build_matter_access_apply_live_smoke_retention_index(
    *,
    retention_root: Path = DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT,
    correlation_id: str | None = None,
    workspace_id: str | None = None,
    status: str | None = None,
    query: str | None = None,
    now_utc: str | None = None,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    if retention_root.exists():
        for path in sorted(retention_root.glob(f"*/{RETENTION_JSON_NAME}")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"invalid retention JSON {path}: {exc}")
                continue
            if not isinstance(payload, dict):
                errors.append(f"invalid retention JSON {path}: expected object")
                continue
            row = _retention_row(payload, path)
            if _matches(row, correlation_id=correlation_id, workspace_id=workspace_id, status=status, query=query):
                rows.append(row)
    rows.sort(key=lambda item: (str(item.get("generated_at") or ""), str(item.get("correlation_id") or "")))
    redaction_shape_status_counts = _redaction_shape_status_counts(rows)
    upgrade_advice = _retention_upgrade_advice(rows)
    return {
        "schema_version": INDEX_SCHEMA_VERSION,
        "status": "PASSED" if not errors else "BLOCKED",
        "generated_at": now_utc or _now(),
        "summary": {
            "retention_root": str(retention_root),
            "run_count": len(rows),
            "filter_correlation_id": correlation_id,
            "filter_workspace_id": workspace_id,
            "filter_status": status,
            "filter_query": query,
            "redaction_shape_status_counts": redaction_shape_status_counts,
            "redaction_shape_passed_count": redaction_shape_status_counts.get("PASSED", 0),
            "redaction_shape_blocked_count": redaction_shape_status_counts.get("BLOCKED", 0),
            "redaction_shape_not_evaluated_count": redaction_shape_status_counts.get("NOT_EVALUATED", 0),
            "redaction_shape_legacy_missing_count": sum(
                1 for row in rows if row.get("redaction_shape_legacy_missing") is True
            ),
            "redaction_shape_upgrade_required": _dict(upgrade_advice.get("summary")).get("upgrade_required"),
            "redaction_shape_upgrade_item_count": _dict(upgrade_advice.get("summary")).get("upgrade_item_count"),
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "live_smokes": rows,
        "upgrade_advice": upgrade_advice,
        "errors": errors,
        "privacy": {
            "readsLocalRedactedArtifactsOnly": True,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "tenantDeletesExecuted": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
        },
    }


def build_matter_access_apply_live_smoke_retention_readiness(
    *,
    retention_root: Path = DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT,
    correlation_id: str | None = None,
    workspace_id: str | None = None,
    now_utc: str | None = None,
    write_artifact: bool = False,
) -> dict[str, Any]:
    generated_at = now_utc or _now()
    index = build_matter_access_apply_live_smoke_retention_index(
        retention_root=retention_root,
        correlation_id=correlation_id,
        workspace_id=workspace_id,
        status="PASSED",
        now_utc=generated_at,
    )
    rows = [row for row in index.get("live_smokes", []) if isinstance(row, dict)]
    checks = _readiness_checks(index, rows)
    errors = [check["message"] for check in checks if check.get("status") != "PASSED"]
    latest_row = rows[-1] if rows else {}
    index_summary = _dict(index.get("summary"))
    upgrade_advice = _retention_upgrade_advice(rows)
    payload = {
        "schema_version": READINESS_SCHEMA_VERSION,
        "status": "READY" if not errors else "NOT_READY",
        "generated_at": generated_at,
        "summary": {
            "retention_root": str(retention_root),
            "filter_correlation_id": correlation_id,
            "filter_workspace_id": workspace_id,
            "ready_run_count": len(rows),
            "latest_correlation_id": latest_row.get("correlation_id"),
            "latest_workspace_id": latest_row.get("workspace_id"),
            "latest_retention_json_path": latest_row.get("retention_json_path"),
            "latest_retained_artifact_path": latest_row.get("retained_artifact_path"),
            "latest_retention_report_path": latest_row.get("retention_report_path"),
            "latest_redaction_shape_status": latest_row.get("redaction_shape_status"),
            "latest_redaction_shape_violation_count": latest_row.get("redaction_shape_violation_count"),
            "redaction_shape_status_counts": index_summary.get("redaction_shape_status_counts"),
            "redaction_shape_passed_count": index_summary.get("redaction_shape_passed_count"),
            "redaction_shape_blocked_count": index_summary.get("redaction_shape_blocked_count"),
            "redaction_shape_not_evaluated_count": index_summary.get("redaction_shape_not_evaluated_count"),
            "redaction_shape_legacy_missing_count": index_summary.get("redaction_shape_legacy_missing_count"),
            "redaction_shape_upgrade_required": _dict(upgrade_advice.get("summary")).get("upgrade_required"),
            "redaction_shape_upgrade_item_count": _dict(upgrade_advice.get("summary")).get("upgrade_item_count"),
            "readiness_json_path": str(retention_root / RETENTION_READINESS_JSON_NAME),
            "readiness_report_path": str(retention_root / RETENTION_READINESS_REPORT_NAME),
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "checks": checks,
        "errors": errors,
        "retention_index": {
            "status": index.get("status"),
            "generated_at": index.get("generated_at"),
            "run_count": index_summary.get("run_count"),
            "redaction_shape_status_counts": index_summary.get("redaction_shape_status_counts"),
            "live_smokes": rows,
        },
        "upgrade_advice": upgrade_advice,
        "privacy": {
            "readsLocalRedactedArtifactsOnly": True,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "tenantDeletesExecuted": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
        },
    }
    if write_artifact:
        _write_json(payload, retention_root / RETENTION_READINESS_JSON_NAME)
        _write_text(
            format_matter_access_apply_live_smoke_retention_readiness(payload),
            retention_root / RETENTION_READINESS_REPORT_NAME,
        )
    return payload


def build_matter_access_apply_live_smoke_retention_upgrade_plan(
    *,
    retention_root: Path = DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT,
    correlation_id: str | None = None,
    workspace_id: str | None = None,
    status: str | None = None,
    query: str | None = None,
    now_utc: str | None = None,
) -> dict[str, Any]:
    generated_at = now_utc or _now()
    index = build_matter_access_apply_live_smoke_retention_index(
        retention_root=retention_root,
        correlation_id=correlation_id,
        workspace_id=workspace_id,
        status=status,
        query=query,
        now_utc=generated_at,
    )
    advice = _dict(index.get("upgrade_advice"))
    items = [item for item in advice.get("items", []) if isinstance(item, dict)]
    commands = [_upgrade_plan_command(item) for item in items]
    errors = index.get("errors") if isinstance(index.get("errors"), list) else []
    plan_status = "BLOCKED" if index.get("status") != "PASSED" else "UPGRADE_REQUIRED" if commands else "CURRENT"
    return {
        "schema_version": UPGRADE_PLAN_SCHEMA_VERSION,
        "status": plan_status,
        "generated_at": generated_at,
        "summary": {
            "retention_root": str(retention_root),
            "filter_correlation_id": correlation_id,
            "filter_workspace_id": workspace_id,
            "filter_status": status,
            "filter_query": query,
            "upgrade_command_count": len(commands),
            "dry_run": True,
            "mutates_artifacts": False,
            "would_execute_commands": False,
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "changes_credentials": False,
        },
        "commands": commands,
        "retention_index": {
            "schema_version": index.get("schema_version"),
            "status": index.get("status"),
            "generated_at": index.get("generated_at"),
            "run_count": _dict(index.get("summary")).get("run_count"),
            "redaction_shape_status_counts": _dict(index.get("summary")).get("redaction_shape_status_counts"),
            "upgrade_advice": advice,
        },
        "errors": errors,
        "privacy": {
            "readsLocalRedactedArtifactsOnly": True,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "tenantDeletesExecuted": False,
            "storesTokensOrSecrets": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
            "mutatesArtifacts": False,
            "dryRunOnly": True,
        },
    }


def format_matter_access_apply_live_smoke_retention(payload: dict[str, Any]) -> str:
    summary = _dict(payload.get("summary"))
    lines = [
        "# Matter-Access Apply Live-Smoke Retention",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Workspace: `{summary.get('workspace_id')}`",
        f"- Correlation-ID: `{summary.get('correlation_id')}`",
        f"- Retained artifact: `{summary.get('retained_artifact_path')}`",
        f"- Retention index: `{summary.get('retention_json_path')}`",
        f"- Root index: `{summary.get('retention_index_json_path')}`",
        f"- Source Graph writes executed: `{summary.get('source_executed_graph_writes')}`",
        f"- Cleanup after readback: `grant={summary.get('grant_cleanup_read_after_value_count')}`, `audit={summary.get('audit_cleanup_read_after_value_count')}`",
        f"- Retention Graph requests executed: `{summary.get('retention_executes_graph_requests')}`",
        f"- Redaction shape status: `{summary.get('redaction_shape_status')}`",
        f"- Redaction shape violations: `{summary.get('redaction_shape_violation_count')}`",
        "",
    ]
    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    if errors:
        lines.append("## Errors")
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    return "\n".join(lines)


def format_matter_access_apply_live_smoke_retention_index(payload: dict[str, Any]) -> str:
    summary = _dict(payload.get("summary"))
    lines = [
        "# Matter-Access Apply Live-Smoke Retention Index",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Retention root: `{summary.get('retention_root')}`",
        f"- Run count: `{summary.get('run_count')}`",
        f"- Redaction shape status counts: `{summary.get('redaction_shape_status_counts')}`",
        "",
        "| Correlation ID | Workspace | Status | Redaction Shape | Violations | Artifact |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload.get("live_smokes", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| `{row.get('correlation_id')}` | `{row.get('workspace_id')}` | `{row.get('status')}` | `{row.get('redaction_shape_status')}` | `{row.get('redaction_shape_violation_count')}` | `{row.get('retained_artifact_path')}` |"
        )
    lines.extend(_format_upgrade_advice(payload.get("upgrade_advice")))
    lines.append("")
    return "\n".join(lines)


def format_matter_access_apply_live_smoke_retention_readiness(payload: dict[str, Any]) -> str:
    summary = _dict(payload.get("summary"))
    lines = [
        "# Matter-Access Apply Live-Smoke Retention Readiness",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Retention root: `{summary.get('retention_root')}`",
        f"- Ready run count: `{summary.get('ready_run_count')}`",
        f"- Latest correlation ID: `{summary.get('latest_correlation_id')}`",
        f"- Latest retained artifact: `{summary.get('latest_retained_artifact_path')}`",
        f"- Latest redaction shape status: `{summary.get('latest_redaction_shape_status')}`",
        f"- Redaction shape status counts: `{summary.get('redaction_shape_status_counts')}`",
        f"- Redaction shape upgrade required: `{summary.get('redaction_shape_upgrade_required')}`",
        f"- Executes Graph requests: `{summary.get('executes_graph_requests')}`",
        f"- Tenant writes executed: `{summary.get('tenant_writes_executed')}`",
        "",
        "## Checks",
        "",
    ]
    for check in payload.get("checks", []):
        if not isinstance(check, dict):
            continue
        lines.append(f"- `{check.get('id')}`: `{check.get('status')}` - {check.get('message')}")
    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    if errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
    lines.extend(_format_upgrade_advice(payload.get("upgrade_advice")))
    lines.append("")
    return "\n".join(lines)


def format_matter_access_apply_live_smoke_retention_upgrade_plan(payload: dict[str, Any]) -> str:
    summary = _dict(payload.get("summary"))
    commands = [item for item in payload.get("commands", []) if isinstance(item, dict)]
    lines = [
        "# Matter-Access Apply Live-Smoke Retention Upgrade Plan",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Retention root: `{summary.get('retention_root')}`",
        f"- Upgrade command count: `{summary.get('upgrade_command_count')}`",
        f"- Dry run: `{summary.get('dry_run')}`",
        f"- Mutates artifacts: `{summary.get('mutates_artifacts')}`",
        f"- Would execute commands: `{summary.get('would_execute_commands')}`",
        f"- Executes Graph requests: `{summary.get('executes_graph_requests')}`",
        f"- Tenant writes executed: `{summary.get('tenant_writes_executed')}`",
        "",
    ]
    if commands:
        lines.extend(
            [
                "## Upgrade Commands",
                "",
                "| Correlation ID | Workspace | Retained Artifact Available | Dry Run | Command |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for command in commands:
            lines.append(
                f"| `{command.get('correlation_id')}` | `{command.get('workspace_id')}` | `{command.get('retained_artifact_available')}` | `{command.get('dry_run')}` | `{command.get('command')}` |"
            )
        lines.append("")
    else:
        lines.extend(["No retention upgrade commands are required for the selected filters.", ""])
    errors = payload.get("errors") if isinstance(payload.get("errors"), list) else []
    if errors:
        lines.extend(["## Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")
    return "\n".join(lines)


def _retention_row(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    summary = _dict(payload.get("summary"))
    redaction_shape_summary = _retention_redaction_shape_summary(payload)
    row = {
        "correlation_id": summary.get("correlation_id"),
        "workspace_id": summary.get("workspace_id"),
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
        "retention_root_path": str(path.parent.parent),
        "retention_json_path": str(path),
        "retention_report_path": summary.get("retention_report_path"),
        "retained_artifact_path": summary.get("retained_artifact_path"),
        "retained_artifact_sha256": summary.get("retained_artifact_sha256"),
        "redaction_shape_status": redaction_shape_summary.get("status"),
        "redaction_shape_violation_count": redaction_shape_summary.get("violation_count"),
        "redaction_shape_checked_node_count": redaction_shape_summary.get("checked_node_count"),
        "redaction_shape_evidence_present": redaction_shape_summary.get("evidence_present"),
        "redaction_shape_legacy_missing": redaction_shape_summary.get("legacy_missing"),
        "redaction_shape_schema_version": redaction_shape_summary.get("schema_version"),
        "source_executed_graph_writes": summary.get("source_executed_graph_writes"),
        "grant_read_value_count": summary.get("grant_read_value_count"),
        "audit_read_value_count": summary.get("audit_read_value_count"),
        "grant_cleanup_read_after_value_count": summary.get("grant_cleanup_read_after_value_count"),
        "audit_cleanup_read_after_value_count": summary.get("audit_cleanup_read_after_value_count"),
    }
    row["upgrade_advice"] = _row_upgrade_advice(row)
    return row


def _readiness_checks(index: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        _check(
            "retention_index_passed",
            index.get("status") == "PASSED",
            "Retention index is readable and PASSED.",
        ),
        _check(
            "retained_live_smoke_present",
            bool(rows),
            "At least one PASSED retained owner-gated live-smoke artifact is present for the selected filters.",
        ),
        _check(
            "readiness_offline_only",
            True,
            "Readiness uses only local redacted retention artifacts and performs no Graph request.",
        ),
    ]
    if rows:
        checks.extend(
            [
                _check(
                    "all_runs_executed_graph_writes",
                    all(row.get("source_executed_graph_writes") is True for row in rows),
                    "Every retained live-smoke proves synthetic Graph writes were executed in the source smoke.",
                ),
                _check(
                    "all_runs_have_readback",
                    all(
                        row.get("grant_read_value_count") == 1
                        and row.get("audit_read_value_count") == 1
                        for row in rows
                    ),
                    "Every retained live-smoke has grant and audit readback evidence.",
                ),
                _check(
                    "all_runs_have_cleanup_readback",
                    all(
                        row.get("grant_cleanup_read_after_value_count") == 0
                        and row.get("audit_cleanup_read_after_value_count") == 0
                        for row in rows
                    ),
                    "Every retained live-smoke proves cleanup by zero-value readback.",
                ),
                _check(
                    "all_runs_have_redaction_shape_evidence",
                    all(row.get("redaction_shape_evidence_present") is True for row in rows),
                    "Every retained live-smoke exposes redaction-shape evidence in the retention index.",
                ),
                _check(
                    "all_runs_have_valid_redaction_shape",
                    all(row.get("redaction_shape_status") == "PASSED" for row in rows),
                    "Every retained live-smoke has passed the recursive redaction-shape check.",
                ),
                _check(
                    "all_retained_artifacts_exist",
                    all(Path(str(row.get("retained_artifact_path") or "")).is_file() for row in rows),
                    "Every retained live-smoke row points to an existing redacted retained artifact.",
                ),
            ]
        )
    return checks


def _matches(
    row: dict[str, Any],
    *,
    correlation_id: str | None,
    workspace_id: str | None,
    status: str | None,
    query: str | None,
) -> bool:
    if correlation_id and row.get("correlation_id") != correlation_id:
        return False
    if workspace_id and row.get("workspace_id") != workspace_id:
        return False
    if status and row.get("status") != status:
        return False
    if query:
        text = json.dumps(row, ensure_ascii=False).lower()
        if query.lower() not in text:
            return False
    return True


def _blocked_retention(generated_at: str, artifact_path: Path, retention_root: Path, errors: list[str]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "BLOCKED",
        "generated_at": generated_at,
        "summary": {
            "source_artifact_path": str(artifact_path),
            "retention_root": str(retention_root),
            "retention_executes_graph_requests": False,
            "retention_executes_graph_writes": False,
            "retention_tenant_writes_executed": False,
            "retention_tenant_deletes_executed": False,
            "redaction_shape_status": "NOT_EVALUATED",
            "redaction_shape_violation_count": None,
        },
        "checks": _retention_checks(errors),
        "errors": errors,
        "redaction_shape": {
            "schema_version": REDACTION_SHAPE_SCHEMA_VERSION,
            "status": "NOT_EVALUATED",
            "summary": {
                "checked_node_count": 0,
                "violation_count": None,
                "executes_graph_requests": False,
                "tenant_writes_executed": False,
            },
            "violations": [],
            "errors": [],
        },
        "privacy": {
            "readsLocalRedactedArtifactsOnly": True,
            "executesGraphRequests": False,
            "executesGraphWrites": False,
            "tenantWritesExecuted": False,
            "tenantDeletesExecuted": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def _retention_upgrade_advice(rows: list[dict[str, Any]]) -> dict[str, Any]:
    items = [
        _dict(row.get("upgrade_advice"))
        for row in rows
        if _dict(row.get("upgrade_advice")).get("required") is True
    ]
    return {
        "schema_version": UPGRADE_ADVICE_SCHEMA_VERSION,
        "status": "UPGRADE_REQUIRED" if items else "CURRENT",
        "summary": {
            "upgrade_required": bool(items),
            "upgrade_item_count": len(items),
            "legacy_missing_redaction_shape_count": sum(
                1 for item in items if item.get("reason") == "legacy_missing_redaction_shape_evidence"
            ),
            "executes_graph_requests": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "changes_credentials": False,
        },
        "items": items,
        "privacy": {
            "readsLocalRedactedArtifactsOnly": True,
            "executesGraphRequests": False,
            "tenantWritesExecuted": False,
            "tenantDeletesExecuted": False,
            "storesTokensOrSecrets": False,
            "readsSharePointFileContent": False,
        },
    }


def _row_upgrade_advice(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("redaction_shape_legacy_missing") is not True:
        return {
            "required": False,
            "reason": None,
            "executes_graph_requests": False,
            "tenant_writes_executed": False,
        }
    retained_artifact_path = str(row.get("retained_artifact_path") or "")
    retention_root_path = str(row.get("retention_root_path") or "")
    command_argv = [
        "python3",
        "scripts/nac.py",
        "m365",
        "teams-sharepoint",
        "matter-access-apply-live-smoke-retain",
        "--matter-access-apply-live-smoke-artifact",
        retained_artifact_path or "<redacted-live-smoke-artifact>",
        "--matter-access-apply-live-smoke-retention-root",
        retention_root_path or "<retention-root>",
        "--format",
        "json",
    ]
    return {
        "required": True,
        "reason": "legacy_missing_redaction_shape_evidence",
        "correlation_id": row.get("correlation_id"),
        "workspace_id": row.get("workspace_id"),
        "retention_json_path": row.get("retention_json_path"),
        "retained_artifact_path": retained_artifact_path or None,
        "retained_artifact_available": Path(retained_artifact_path).is_file() if retained_artifact_path else False,
        "recommended_action": "rerun_offline_retention_from_existing_redacted_live_smoke_artifact",
        "command_argv": command_argv,
        "command": " ".join(command_argv),
        "executes_graph_requests": False,
        "tenant_writes_executed": False,
        "tenant_deletes_executed": False,
        "changes_credentials": False,
    }


def _format_upgrade_advice(value: Any) -> list[str]:
    upgrade_advice = _dict(value)
    items = [item for item in upgrade_advice.get("items", []) if isinstance(item, dict)]
    if not items:
        return []
    lines = [
        "",
        "## Upgrade Advice",
        "",
        "Legacy or missing redaction-shape evidence was found. Re-run offline retention from the existing redacted live-smoke artifact; this performs no Graph request and no tenant write.",
        "",
    ]
    for item in items:
        lines.append(
            f"- `{item.get('correlation_id')}`: `{item.get('recommended_action')}` via `{item.get('command')}`"
        )
    return lines


def _upgrade_plan_command(item: dict[str, Any]) -> dict[str, Any]:
    command_argv = item.get("command_argv") if isinstance(item.get("command_argv"), list) else []
    return {
        "correlation_id": item.get("correlation_id"),
        "workspace_id": item.get("workspace_id"),
        "reason": item.get("reason"),
        "recommended_action": item.get("recommended_action"),
        "retention_json_path": item.get("retention_json_path"),
        "retained_artifact_path": item.get("retained_artifact_path"),
        "retained_artifact_available": item.get("retained_artifact_available"),
        "command_argv": command_argv,
        "command": item.get("command") or " ".join(str(part) for part in command_argv),
        "dry_run": True,
        "would_execute": False,
        "mutates_artifacts": False,
        "executes_graph_requests": False,
        "tenant_writes_executed": False,
        "tenant_deletes_executed": False,
        "changes_credentials": False,
    }


def _retention_redaction_shape_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(payload.get("summary"))
    redaction_shape = _dict(payload.get("redaction_shape"))
    redaction_shape_summary = _dict(redaction_shape.get("summary"))
    status = summary.get("redaction_shape_status") or redaction_shape.get("status")
    evidence_present = bool(status) and status != "NOT_EVALUATED" and bool(redaction_shape)
    normalized_status = str(status or "NOT_EVALUATED")
    return {
        "schema_version": redaction_shape.get("schema_version"),
        "status": normalized_status,
        "violation_count": _first_present(
            summary.get("redaction_shape_violation_count"),
            redaction_shape_summary.get("violation_count"),
        ),
        "checked_node_count": _first_present(
            summary.get("redaction_shape_checked_node_count"),
            redaction_shape_summary.get("checked_node_count"),
        ),
        "evidence_present": evidence_present,
        "legacy_missing": not evidence_present,
    }


def _redaction_shape_status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("redaction_shape_status") or "NOT_EVALUATED")
        counts[status] = counts.get(status, 0) + 1
    for status in ("PASSED", "BLOCKED", "NOT_EVALUATED"):
        counts.setdefault(status, 0)
    return counts


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _retention_checks(errors: list[str]) -> list[dict[str, Any]]:
    return [
        _check("source_artifact_valid", not errors, "Source live-smoke artifact is PASSED and redacted."),
        _check("redaction_shape_valid", not errors, "Source live-smoke artifact has no forbidden raw fields or sensitive markers."),
        _check("offline_retention", True, "Retention reads and writes local redacted artifacts only."),
        _check("no_graph_or_tenant_action", True, "Retention performs no Graph request, tenant write or delete."),
    ]


def _check(check_id: str, passed: bool, message: str) -> dict[str, Any]:
    return {"id": check_id, "status": "PASSED" if passed else "BLOCKED", "message": message}


def _artifact_summary(artifact: dict[str, Any]) -> dict[str, Any]:
    return _dict(artifact.get("summary"))


def _privacy_flag(artifact: dict[str, Any], key: str) -> Any:
    return _dict(artifact.get("privacy")).get(key)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _expect(summary: dict[str, Any], key: str, expected: Any, errors: list[str]) -> None:
    if summary.get(key) != expected:
        errors.append(f"artifact summary.{key} expected {expected!r}, got {summary.get(key)!r}")


def _safe_segment(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "._-" else "-" for ch in value).strip(".-_")
    return safe or "unknown"


def _walk_json(value: Any, path: tuple[str, ...] = ()) -> list[tuple[tuple[str, ...], Any]]:
    rows: list[tuple[tuple[str, ...], Any]] = [(path, value)]
    if isinstance(value, dict):
        for key, child in value.items():
            rows.extend(_walk_json(child, (*path, str(key))))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            rows.extend(_walk_json(child, (*path, str(index))))
    return rows


def _is_forbidden_redaction_shape_key(key: str, value: Any) -> bool:
    normalized = _normalize_key(key)
    if normalized in ALLOWED_FALSE_PRIVACY_FLAG_KEYS and value is False:
        return False
    if normalized in FORBIDDEN_REDACTION_SHAPE_KEYS:
        return True
    return False


def _normalize_key(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum() or ch == "_")


def _forbidden_value_marker(value: str) -> str | None:
    for marker in FORBIDDEN_REDACTION_SHAPE_VALUE_MARKERS:
        if marker in value:
            return marker
    return None


def _format_json_path(path: tuple[str, ...]) -> str:
    if not path:
        return "$"
    return "$." + ".".join(path)


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
