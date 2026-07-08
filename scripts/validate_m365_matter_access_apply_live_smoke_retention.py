from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.matter_access_apply_live_smoke_retention import (  # noqa: E402
    build_matter_access_apply_live_smoke_retention_index,
    build_matter_access_apply_live_smoke_retention_readiness,
    build_matter_access_apply_live_smoke_retention_upgrade_plan,
    format_matter_access_apply_live_smoke_retention_index,
    format_matter_access_apply_live_smoke_retention_readiness,
    format_matter_access_apply_live_smoke_retention_upgrade_plan,
    retain_matter_access_apply_live_smoke_artifact,
)


CONTRACT_ID = "verification.m365_matter_access_apply_live_smoke_retention"
CHECK_ID = "m365_matter_access_apply_live_smoke_retention"

REQUIRED_FILES = {
    "module": REPO_ROOT / "src/nac_m365_graph/matter_access_apply_live_smoke_retention.py",
    "cli": REPO_ROOT / "src/nac_cli/cli.py",
    "provision_script": REPO_ROOT / "scripts/provision_teams_sharepoint_graph.py",
    "validator": REPO_ROOT / "scripts/validate_m365_matter_access_apply_live_smoke_retention.py",
    "tests": REPO_ROOT / "tests/test_m365_matter_access_apply_live_smoke_retention.py",
    "de_doc": REPO_ROOT / "docs/de/operations/m365-matter-access-apply-live-smoke-release-lane.md",
    "en_doc": REPO_ROOT / "docs/en/operations/m365-matter-access-apply-live-smoke-release-lane.md",
    "de_cli": REPO_ROOT / "docs/de/cli.md",
    "en_cli": REPO_ROOT / "docs/en/cli.md",
    "de_quality": REPO_ROOT / "docs/de/quality-gate.md",
    "en_quality": REPO_ROOT / "docs/en/quality-gate.md",
    "quality_gate": REPO_ROOT / "scripts/quality_gate.py",
    "verification_contract": REPO_ROOT
    / "workflows/verification-contracts/m365-matter-access-apply-live-smoke-retention.verification.json",
    "verification_readme": REPO_ROOT / "workflows/verification-contracts/README.md",
    "agent_context_index": REPO_ROOT / "agent-context/index.json",
    "decision_index": REPO_ROOT / "agent-context/decision-index.json",
    "invariant_index": REPO_ROOT / "agent-context/invariant-index.json",
}

PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "client_secret",
    "password=",
    "ghp_",
    "real_mandate_data_sample",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: M365 matter-access apply live-smoke retention is documented, indexed and gated.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    errors.extend(_validate_files())
    errors.extend(_validate_code())
    errors.extend(_validate_docs())
    errors.extend(_validate_quality_gate())
    errors.extend(_validate_contract_and_indexes())
    errors.extend(_validate_synthetic_retention_roundtrip())
    errors.extend(_validate_synthetic_upgrade_advice_smoke())
    errors.extend(_validate_synthetic_upgrade_plan_dry_run_smoke())
    return errors


def _validate_files() -> list[str]:
    errors: list[str] = []
    for label, path in REQUIRED_FILES.items():
        if not path.is_file():
            errors.append(f"required file missing ({label}): {path.relative_to(REPO_ROOT)}")
    return errors


def _validate_code() -> list[str]:
    errors: list[str] = []
    module = _read("module")
    cli = _read("cli")
    provision_script = _read("provision_script")
    tests = _read("tests")

    for marker in (
        "DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT",
        "SCHEMA_VERSION = \"nac.m365-matter-access-apply-live-smoke-retention/v0.1\"",
        "INDEX_SCHEMA_VERSION = \"nac.m365-matter-access-apply-live-smoke-retention-index/v0.1\"",
        "READINESS_SCHEMA_VERSION = \"nac.m365-matter-access-apply-live-smoke-retention-readiness/v0.1\"",
        "REDACTION_SHAPE_SCHEMA_VERSION = \"nac.m365-matter-access-apply-live-smoke-redaction-shape/v0.1\"",
        "UPGRADE_ADVICE_SCHEMA_VERSION = \"nac.m365-matter-access-apply-live-smoke-retention-upgrade-advice/v0.1\"",
        "UPGRADE_PLAN_SCHEMA_VERSION = \"nac.m365-matter-access-apply-live-smoke-retention-upgrade-plan/v0.1\"",
        "retain_matter_access_apply_live_smoke_artifact",
        "validate_matter_access_apply_live_smoke_artifact",
        "validate_matter_access_apply_live_smoke_redaction_shape",
        "build_matter_access_apply_live_smoke_retention_index",
        "build_matter_access_apply_live_smoke_retention_readiness",
        "build_matter_access_apply_live_smoke_retention_upgrade_plan",
        "format_matter_access_apply_live_smoke_retention_readiness",
        "format_matter_access_apply_live_smoke_retention_upgrade_plan",
        "_readiness_checks",
        "redaction_shape_status",
        "redaction_shape_violation_count",
        "redaction_shape_status_counts",
        "redaction_shape_legacy_missing_count",
        "redaction_shape_upgrade_required",
        "redaction_shape_upgrade_item_count",
        "redaction_shape_evidence_present",
        "latest_redaction_shape_status",
        "upgrade_advice",
        "_retention_upgrade_advice",
        "_row_upgrade_advice",
        "_format_upgrade_advice",
        "_upgrade_plan_command",
        "rerun_offline_retention_from_existing_redacted_live_smoke_artifact",
        "would_execute_commands",
        "mutates_artifacts",
        "sourceArtifactRedactionShapeChecked",
        "all_runs_have_valid_redaction_shape",
        "all_runs_have_redaction_shape_evidence",
        "_retention_redaction_shape_summary",
        "_redaction_shape_status_counts",
        "retention_executes_graph_requests\": False",
        "retentionExecutesGraphRequests\": False",
        "retentionTenantWritesExecuted\": False",
        "storesTokensOrSecrets\": False",
        "shutil.copyfile",
    ):
        _require(marker, module, "module", errors)

    for marker in (
        "matter-access-apply-live-smoke-retain",
        "matter-access-apply-live-smoke-retention-index",
        "matter-access-apply-live-smoke-retention-readiness",
        "matter-access-apply-live-smoke-retention-upgrade-plan",
        "--matter-access-apply-live-smoke-retention-root",
        "--matter-access-apply-live-smoke-artifact",
        "--matter-access-apply-live-smoke-correlation-id",
        "--matter-access-apply-live-smoke-write-readiness",
        "retain_matter_access_apply_live_smoke_artifact",
        "build_matter_access_apply_live_smoke_retention_index",
        "build_matter_access_apply_live_smoke_retention_readiness",
        "build_matter_access_apply_live_smoke_retention_upgrade_plan",
    ):
        _require(marker, cli, "cli", errors)

    for marker in (
        "DEFAULT_MATTER_ACCESS_APPLY_LIVE_SMOKE_RETENTION_ROOT",
        "retain_matter_access_apply_live_smoke_artifact",
        "--matter-access-apply-live-smoke-retention-root",
        "retention_status",
        "retention_artifact_dir",
        "retention_json_path",
        "retention_root_index_path",
        "command_status = \"PASSED\" if result[\"status\"] == \"PASSED\" and retention[\"status\"] == \"PASSED\" else \"FAILED\"",
    ):
        _require(marker, provision_script, "provision_script", errors)

    for marker in (
        "test_retains_redacted_live_smoke_and_updates_index",
        "test_index_filters_by_correlation_workspace_status_and_query",
        "test_retention_blocks_invalid_source_without_copying",
        "test_index_surfaces_legacy_missing_redaction_shape_evidence",
        "test_redaction_shape_blocks_forbidden_raw_graph_path_key_without_copying",
        "test_redaction_shape_blocks_secret_like_value_marker",
        "test_cli_retains_and_indexes_without_graph",
        "test_readiness_reports_ready_for_retained_live_smoke",
        "test_readiness_blocks_when_no_retained_live_smoke_matches",
        "test_cli_reports_live_smoke_retention_readiness_without_graph",
        "test_cli_upgrade_advice_smoke_uses_legacy_fixture_and_reports_upgrade_required",
        "test_cli_upgrade_plan_dry_run_reports_commands_without_mutating_artifacts",
        "test_upgrade_plan_reports_current_when_no_upgrade_is_required",
        "_write_legacy_retention_fixture",
        "test_retention_validator_passes",
    ):
        _require(marker, tests, "tests", errors)

    for key in ("module", "cli", "provision_script", "tests"):
        _reject_prohibited_text(REQUIRED_FILES[key], errors)
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_doc_markers = (
        "matter-access-apply-live-smokes/<correlation-id>/",
        "matter-access-apply-live-smoke-retain",
        "matter-access-apply-live-smoke-retention-index",
        "matter-access-apply-live-smoke-retention-readiness",
        "matter-access-apply-live-smoke-retention-upgrade-plan",
        "matter-access-apply-live-smoke-retention-readiness.redacted.json",
        "matter-access-apply-live-smoke-retention-readiness.redacted.md",
        "--matter-access-apply-live-smoke-write-readiness",
        "READY",
        "NOT_READY",
        "redaction_shape_status=PASSED",
        "redaction_shape_status_counts",
        "redaction_shape_legacy_missing_count",
        "redaction_shape_upgrade_required",
        "UPGRADE_REQUIRED",
        "upgrade_advice.status=UPGRADE_REQUIRED",
        "dry_run=true",
        "mutates_artifacts=false",
        "upgrade advice",
        "sourceArtifactRedactionShapeChecked=true",
        "retention_executes_graph_requests=false",
        "retention_tenant_writes_executed=false",
    )
    for key in ("de_doc", "en_doc", "de_cli", "en_cli"):
        text = _read(key)
        for marker in required_doc_markers:
            _require(marker, text, key, errors)
        _reject_prohibited_text(REQUIRED_FILES[key], errors)

    for key in ("de_quality", "en_quality"):
        text = _read(key)
        for marker in (
            CHECK_ID,
            "matter-access-apply-live-smokes/",
            "keine Graph- oder Tenant-Aktion" if key == "de_quality" else "no Graph or tenant action",
        ):
            _require(marker, text, key, errors)
    return errors


def _validate_quality_gate() -> list[str]:
    errors: list[str] = []
    text = _read("quality_gate")
    for marker in (
        CHECK_ID,
        "M365 Matter Access Apply Live-Smoke Retention",
        "scripts/validate_m365_matter_access_apply_live_smoke_retention.py",
    ):
        _require(marker, text, "quality_gate", errors)
    return errors


def _validate_contract_and_indexes() -> list[str]:
    errors: list[str] = []
    contract = _read_json("verification_contract", errors)
    if contract:
        if contract.get("contract_id") != CONTRACT_ID:
            errors.append("verification contract has wrong contract_id")
        for marker in (
            "src/nac_m365_graph/matter_access_apply_live_smoke_retention.py",
            "scripts/validate_m365_matter_access_apply_live_smoke_retention.py",
            "tests/test_m365_matter_access_apply_live_smoke_retention.py",
            "matter-access-apply-live-smoke-retention-readiness",
            "matter-access-apply-live-smoke-retention-upgrade-plan",
        ):
            if marker not in json.dumps(contract, ensure_ascii=False):
                errors.append(f"verification contract missing marker: {marker}")
        if "quality_gate_failure" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing quality_gate_failure behavior")
        if "redaction_shape_fail_closed" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing redaction_shape_fail_closed pass condition")
        if "redaction_shape_indexed" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing redaction_shape_indexed pass condition")
        if "legacy_missing_redaction_shape_visible" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing legacy_missing_redaction_shape_visible pass condition")
        if "legacy_redaction_shape_upgrade_advice_visible" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing legacy_redaction_shape_upgrade_advice_visible pass condition")
        if "legacy_upgrade_advice_smoke_passes" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing legacy_upgrade_advice_smoke_passes pass condition")
        if "retention_upgrade_advice_smoke" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing retention_upgrade_advice_smoke evidence")
        if "retention_upgrade_command_dry_run" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing retention_upgrade_command_dry_run evidence")
        if "retention_upgrade_command_dry_run_noop" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing retention_upgrade_command_dry_run_noop pass condition")
        if "recursive redaction-shape check" not in json.dumps(contract, ensure_ascii=False):
            errors.append("verification contract missing recursive redaction-shape invariant")

    readme = _read("verification_readme")
    _require("m365-matter-access-apply-live-smoke-retention.verification.json", readme, "verification_readme", errors)

    agent_index = _read_json("agent_context_index", errors)
    if agent_index:
        categories = {
            category.get("id"): set(category.get("paths", []))
            for layer in agent_index.get("layers", [])
            if layer.get("id") == "on_demand"
            for category in layer.get("categories", [])
            if isinstance(category, dict)
        }
        required_paths = {
            "src/nac_m365_graph/matter_access_apply_live_smoke_retention.py",
            "scripts/validate_m365_matter_access_apply_live_smoke_retention.py",
            "tests/test_m365_matter_access_apply_live_smoke_retention.py",
            "workflows/verification-contracts/m365-matter-access-apply-live-smoke-retention.verification.json",
        }
        paths = categories.get("m365_matter_access_apply_live_smoke_retention")
        if paths is None:
            errors.append("agent-context/index.json missing m365_matter_access_apply_live_smoke_retention category")
        else:
            for path in sorted(required_paths - paths):
                errors.append(f"agent-context/index.json retention category missing path: {path}")
        if f"workflows/verification-contracts/{Path(REQUIRED_FILES['verification_contract']).name}" not in agent_index.get(
            "verification_contracts", []
        ):
            errors.append("agent-context/index.json missing retention verification contract")

    decision_index = _read_json("decision_index", errors)
    if decision_index and not _contains_id(decision_index.get("decisions"), "ADR-M365-MATTER-ACCESS-005"):
        errors.append("agent-context/decision-index.json missing ADR-M365-MATTER-ACCESS-005")

    invariant_index = _read_json("invariant_index", errors)
    if invariant_index and not _contains_id(
        invariant_index.get("invariants"), "invariant.m365_matter_access.apply_live_smoke_retention_required"
    ):
        errors.append("agent-context/invariant-index.json missing apply_live_smoke_retention_required")
    return errors


def _validate_synthetic_retention_roundtrip() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact_path = tmp_path / "matter-access-apply-smoke.redacted.json"
        artifact_path.write_text(json.dumps(_synthetic_apply_smoke_payload()), encoding="utf-8")
        retention_root = tmp_path / "retention"
        retention = retain_matter_access_apply_live_smoke_artifact(
            artifact_path,
            retention_root=retention_root,
            now_utc="2026-07-08T15:30:00Z",
        )
        if retention.get("status") != "PASSED":
            errors.append(f"synthetic retention roundtrip failed: {retention.get('errors')}")
        summary = retention.get("summary") if isinstance(retention.get("summary"), dict) else {}
        for key in ("retained_artifact_path", "retention_json_path", "retention_report_path", "retention_index_json_path"):
            value = summary.get(key)
            if not value or not Path(value).is_file():
                errors.append(f"synthetic retention missing file for summary.{key}")
        index = build_matter_access_apply_live_smoke_retention_index(retention_root=retention_root)
        if index.get("status") != "PASSED" or index.get("summary", {}).get("run_count") != 1:
            errors.append("synthetic retention index must pass with one retained live smoke")
        readiness = build_matter_access_apply_live_smoke_retention_readiness(
            retention_root=retention_root,
            correlation_id="validator-correlation",
            workspace_id="notary_team_01",
            now_utc="2026-07-08T15:31:00Z",
            write_artifact=True,
        )
        if readiness.get("status") != "READY":
            errors.append(f"synthetic retention readiness must be READY: {readiness.get('errors')}")
        summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
        for key in ("readiness_json_path", "readiness_report_path"):
            value = summary.get(key)
            if not value or not Path(value).is_file():
                errors.append(f"synthetic retention readiness missing file for summary.{key}")
    return errors


def _validate_synthetic_upgrade_advice_smoke() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact_path = tmp_path / "legacy-upgrade-smoke.redacted.json"
        payload = _synthetic_apply_smoke_payload()
        payload["summary"]["correlation_id"] = "validator-legacy-upgrade-correlation"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        retention_root = tmp_path / "retention"
        retention = retain_matter_access_apply_live_smoke_artifact(
            artifact_path,
            retention_root=retention_root,
            now_utc="2026-07-08T15:40:00Z",
        )
        retention_json = Path(str(retention.get("summary", {}).get("retention_json_path") or ""))
        if not retention_json.is_file():
            errors.append("synthetic upgrade advice smoke missing retention JSON")
            return errors
        legacy_payload = json.loads(retention_json.read_text(encoding="utf-8"))
        legacy_payload.pop("redaction_shape", None)
        legacy_summary = legacy_payload.get("summary") if isinstance(legacy_payload.get("summary"), dict) else {}
        for key in ("redaction_shape_status", "redaction_shape_violation_count", "redaction_shape_checked_node_count"):
            legacy_summary.pop(key, None)
        retention_json.write_text(json.dumps(legacy_payload), encoding="utf-8")

        index = build_matter_access_apply_live_smoke_retention_index(
            retention_root=retention_root,
            correlation_id="validator-legacy-upgrade-correlation",
        )
        readiness = build_matter_access_apply_live_smoke_retention_readiness(
            retention_root=retention_root,
            correlation_id="validator-legacy-upgrade-correlation",
            write_artifact=True,
        )
        index_report = format_matter_access_apply_live_smoke_retention_index(index)
        readiness_report = format_matter_access_apply_live_smoke_retention_readiness(readiness)
        if index.get("upgrade_advice", {}).get("status") != "UPGRADE_REQUIRED":
            errors.append("synthetic upgrade advice smoke index must report UPGRADE_REQUIRED")
        if readiness.get("status") != "NOT_READY":
            errors.append("synthetic upgrade advice smoke readiness must be NOT_READY")
        if readiness.get("upgrade_advice", {}).get("status") != "UPGRADE_REQUIRED":
            errors.append("synthetic upgrade advice smoke readiness must report UPGRADE_REQUIRED")
        if "matter-access-apply-live-smoke-retain" not in index_report:
            errors.append("synthetic upgrade advice smoke index report missing retain command")
        if "Upgrade Advice" not in readiness_report:
            errors.append("synthetic upgrade advice smoke readiness report missing Upgrade Advice section")
        summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
        for key in ("readiness_json_path", "readiness_report_path"):
            value = summary.get(key)
            if not value or not Path(value).is_file():
                errors.append(f"synthetic upgrade advice smoke missing file for summary.{key}")
    return errors


def _validate_synthetic_upgrade_plan_dry_run_smoke() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        artifact_path = tmp_path / "legacy-upgrade-plan.redacted.json"
        payload = _synthetic_apply_smoke_payload()
        payload["summary"]["correlation_id"] = "validator-legacy-upgrade-plan"
        artifact_path.write_text(json.dumps(payload), encoding="utf-8")
        retention_root = tmp_path / "retention"
        retention = retain_matter_access_apply_live_smoke_artifact(
            artifact_path,
            retention_root=retention_root,
            now_utc="2026-07-08T15:50:00Z",
        )
        retention_json = Path(str(retention.get("summary", {}).get("retention_json_path") or ""))
        if not retention_json.is_file():
            errors.append("synthetic upgrade plan dry-run smoke missing retention JSON")
            return errors
        legacy_payload = json.loads(retention_json.read_text(encoding="utf-8"))
        legacy_payload.pop("redaction_shape", None)
        legacy_summary = legacy_payload.get("summary") if isinstance(legacy_payload.get("summary"), dict) else {}
        for key in ("redaction_shape_status", "redaction_shape_violation_count", "redaction_shape_checked_node_count"):
            legacy_summary.pop(key, None)
        retention_json.write_text(json.dumps(legacy_payload), encoding="utf-8")
        before = retention_json.read_text(encoding="utf-8")

        plan = build_matter_access_apply_live_smoke_retention_upgrade_plan(
            retention_root=retention_root,
            correlation_id="validator-legacy-upgrade-plan",
            now_utc="2026-07-08T15:51:00Z",
        )
        report = format_matter_access_apply_live_smoke_retention_upgrade_plan(plan)
        if plan.get("status") != "UPGRADE_REQUIRED":
            errors.append("synthetic upgrade plan dry-run smoke must report UPGRADE_REQUIRED")
        summary = plan.get("summary") if isinstance(plan.get("summary"), dict) else {}
        if summary.get("dry_run") is not True or summary.get("mutates_artifacts") is not False:
            errors.append("synthetic upgrade plan dry-run smoke must be dry_run and non-mutating")
        commands = plan.get("commands") if isinstance(plan.get("commands"), list) else []
        if len(commands) != 1:
            errors.append("synthetic upgrade plan dry-run smoke must render one command")
        else:
            command = commands[0]
            if command.get("would_execute") is not False:
                errors.append("synthetic upgrade plan dry-run smoke command must not execute")
            if command.get("mutates_artifacts") is not False:
                errors.append("synthetic upgrade plan dry-run smoke command must not mutate artifacts")
            if "matter-access-apply-live-smoke-retain" not in str(command.get("command")):
                errors.append("synthetic upgrade plan dry-run smoke missing retain command")
        if "Dry run: `True`" not in report:
            errors.append("synthetic upgrade plan dry-run report missing dry-run marker")
        if before != retention_json.read_text(encoding="utf-8"):
            errors.append("synthetic upgrade plan dry-run smoke mutated retention JSON")
    return errors


def _synthetic_apply_smoke_payload() -> dict:
    return {
        "schema_version": "nac.m365-matter-access-apply-smoke/v0.1",
        "status": "PASSED",
        "generated_at": "2026-07-08T15:30:00Z",
        "summary": {
            "workspace_id": "notary_team_01",
            "correlation_id": "validator-correlation",
            "write_tools": ["grant_request", "audit_append"],
            "write_lists": ["Vertretungsfreigaben", "AuditJournalLite"],
            "planned_write_count": 2,
            "executed_graph_requests": True,
            "executed_graph_writes": True,
            "sharepoint_item_writes_executed": True,
            "tenant_mutation_allowed": False,
            "team_membership_mutation_allowed": False,
            "sharepoint_item_permission_mutation_allowed": False,
            "grant_read_value_count": 1,
            "audit_read_value_count": 1,
            "cleanup_requested": True,
            "grant_cleanup_read_after_value_count": 0,
            "audit_cleanup_read_after_value_count": 0,
            "graph_rest_only": True,
            "raw_graph_path_stored": False,
            "raw_graph_response_stored": False,
            "raw_write_payload_stored": False,
            "stores_tokens_or_secrets": False,
            "reads_sharepoint_file_content": False,
        },
        "privacy": {
            "storesTokensOrSecrets": False,
            "storesMatterPayloads": False,
            "storesRawGraphPath": False,
            "storesRawGraphResponse": False,
            "readsSharePointFileContent": False,
        },
    }


def _contains_id(items: object, item_id: str) -> bool:
    return isinstance(items, list) and any(isinstance(item, dict) and item.get("id") == item_id for item in items)


def _read(label: str) -> str:
    path = REQUIRED_FILES[label]
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _read_json(label: str, errors: list[str]) -> dict:
    path = REQUIRED_FILES[label]
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} invalid JSON: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must contain a JSON object")
        return {}
    return payload


def _require(marker: str, text: str, label: str, errors: list[str]) -> None:
    if marker not in text:
        errors.append(f"{REQUIRED_FILES[label].relative_to(REPO_ROOT)} missing marker: {marker}")


def _reject_prohibited_text(path: Path, errors: list[str]) -> None:
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker: {marker}")


if __name__ == "__main__":
    raise SystemExit(main())
