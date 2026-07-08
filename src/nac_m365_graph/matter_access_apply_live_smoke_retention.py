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

    errors = validate_matter_access_apply_live_smoke_artifact(artifact)
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
        },
        "checks": _retention_checks(errors),
        "errors": errors,
        "privacy": {
            "source_artifact_must_be_redacted": True,
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
            "executes_graph_requests": False,
            "executes_graph_writes": False,
            "tenant_writes_executed": False,
            "tenant_deletes_executed": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "live_smokes": rows,
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
            "run_count": _dict(index.get("summary")).get("run_count"),
            "live_smokes": rows,
        },
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
        "",
        "| Correlation ID | Workspace | Status | Artifact |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload.get("live_smokes", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| `{row.get('correlation_id')}` | `{row.get('workspace_id')}` | `{row.get('status')}` | `{row.get('retained_artifact_path')}` |"
        )
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
    lines.append("")
    return "\n".join(lines)


def _retention_row(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    summary = _dict(payload.get("summary"))
    return {
        "correlation_id": summary.get("correlation_id"),
        "workspace_id": summary.get("workspace_id"),
        "status": payload.get("status"),
        "generated_at": payload.get("generated_at"),
        "retention_json_path": str(path),
        "retention_report_path": summary.get("retention_report_path"),
        "retained_artifact_path": summary.get("retained_artifact_path"),
        "retained_artifact_sha256": summary.get("retained_artifact_sha256"),
        "source_executed_graph_writes": summary.get("source_executed_graph_writes"),
        "grant_read_value_count": summary.get("grant_read_value_count"),
        "audit_read_value_count": summary.get("audit_read_value_count"),
        "grant_cleanup_read_after_value_count": summary.get("grant_cleanup_read_after_value_count"),
        "audit_cleanup_read_after_value_count": summary.get("audit_cleanup_read_after_value_count"),
    }


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
        },
        "checks": _retention_checks(errors),
        "errors": errors,
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


def _retention_checks(errors: list[str]) -> list[dict[str, Any]]:
    return [
        _check("source_artifact_valid", not errors, "Source live-smoke artifact is PASSED and redacted."),
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
