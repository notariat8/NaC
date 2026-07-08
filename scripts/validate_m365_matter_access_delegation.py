from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.matter_access_delegation import (  # noqa: E402
    DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT,
    build_matter_access_plan,
    summarize_matter_access_plan,
    validate_matter_access_delegation_contract,
)
from nac_m365_graph.matter_access_delegation_smoke import run_matter_access_delegation_smoke  # noqa: E402
from nac_m365_graph.matter_access_apply_readiness import build_matter_access_apply_readiness  # noqa: E402
from nac_m365_graph.matter_access_apply_request import build_matter_access_apply_request_plan  # noqa: E402
from nac_m365_graph.mcp_runtime import DEFAULT_MCP_CONTRACT, load_mcp_contract, validate_mcp_contract  # noqa: E402
from nac_m365_graph.privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state  # noqa: E402
from nac_m365_graph.schema import DEFAULT_SCHEMA, load_schema  # noqa: E402


CONTRACT = DEFAULT_MATTER_ACCESS_DELEGATION_CONTRACT
DATA_MCP_CONTRACT = DEFAULT_MCP_CONTRACT
CONTRACTS_README = REPO_ROOT / "workflows" / "contracts" / "README.md"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "m365-matter-access-delegation.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "m365-matter-access-delegation.md"
DATA_PLANE_DE = REPO_ROOT / "docs" / "de" / "architecture" / "teams-sharepoint-graph-data-plane.md"
DATA_PLANE_EN = REPO_ROOT / "docs" / "en" / "architecture" / "teams-sharepoint-graph-data-plane.md"
CLI_DE = REPO_ROOT / "docs" / "de" / "cli.md"
CLI_EN = REPO_ROOT / "docs" / "en" / "cli.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"
NAC_CLI = REPO_ROOT / "src" / "nac_cli" / "cli.py"
PROVISIONER_CLI = REPO_ROOT / "scripts" / "provision_teams_sharepoint_graph.py"

REQUIRED_MCP_TOOLS = {"case_get", "grant_request", "audit_append", "document_list"}
REQUIRED_DOC_MARKERS = {
    DOC_DE: [
        "M365-Mandatszugriffsdelegation",
        "Vertretungsfreigaben",
        "matter-access-plan",
        "matter-access-apply-readiness",
        "matter-access-apply-request-plan",
        "matter-access-smoke",
        "Microsoft Graph REST",
        "keine Live-Tenant-Aktion",
    ],
    DOC_EN: [
        "M365 Matter Access Delegation",
        "Vertretungsfreigaben",
        "matter-access-plan",
        "matter-access-apply-readiness",
        "matter-access-apply-request-plan",
        "matter-access-smoke",
        "Microsoft Graph REST",
        "no live tenant action",
    ],
    DATA_PLANE_DE: [
        "m365-matter-access-delegation.md",
        "matter-access-plan",
        "matter-access-apply-readiness",
        "matter-access-apply-request-plan",
        "matter-access-smoke",
    ],
    DATA_PLANE_EN: [
        "m365-matter-access-delegation.md",
        "matter-access-plan",
        "matter-access-apply-readiness",
        "matter-access-apply-request-plan",
        "matter-access-smoke",
    ],
    CLI_DE: [
        "matter-access-plan",
        "matter-access-apply-readiness",
        "matter-access-apply-request-plan",
        "matter-access-smoke",
    ],
    CLI_EN: [
        "matter-access-plan",
        "matter-access-apply-readiness",
        "matter-access-apply-request-plan",
        "matter-access-smoke",
    ],
    CONTRACTS_README: ["m365-matter-access-delegation.contract.json", "matter-access-apply-request-plan"],
    QUALITY_DE: ["m365_matter_access_delegation"],
    QUALITY_EN: ["m365_matter_access_delegation"],
}
PROHIBITED_TEXT_MARKERS = {
    "BEGIN PRIVATE KEY",
    "client_secret",
    "password=",
    "ghp_",
    "oci_session_token",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: M365 matter access delegation contract, CLI, docs and quality gate are aligned.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    contract = _read_json(CONTRACT, errors)
    schema = _read_json(DEFAULT_SCHEMA, errors)
    mcp_contract = _read_json(DATA_MCP_CONTRACT, errors)
    if contract:
        _reject_prohibited_text(CONTRACT, errors)
    if mcp_contract:
        _reject_prohibited_text(DATA_MCP_CONTRACT, errors)

    if contract and schema:
        errors.extend(validate_matter_access_delegation_contract(contract, schema))
        try:
            operations = build_matter_access_plan(contract, schema)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            summary = summarize_matter_access_plan(operations, contract)
            if summary["operation_count"] != len(schema["workspaces"]) * 6:
                errors.append("matter-access-plan must create six request-plan operations per workspace")
            if summary["executes_graph_requests_now"] is not False:
                errors.append("matter-access-plan must not execute Graph requests now")
            if summary["team_membership_mutation_allowed_now"] is not False:
                errors.append("matter-access-plan must not mutate Teams membership now")
            if any(operation.reads_files for operation in operations):
                errors.append("matter-access-plan operations must not read SharePoint file content")
            if any(not operation.graph_path.startswith("/sites/{site-id}/") for operation in operations):
                errors.append("matter-access-plan operations must stay within /sites/{site-id}")
            smoke = run_matter_access_delegation_smoke(
                contract,
                schema,
                workspace_id=schema["workspaces"][0]["id"],
                correlation_id="validator-smoke",
                timestamp="2026-07-07T00:00:00Z",
            )
            if smoke["status"] != "PASSED":
                errors.append("matter-access-smoke must pass for the first workspace")
            smoke_summary = smoke["summary"]
            if smoke_summary["workspace_operation_count"] != 6:
                errors.append("matter-access-smoke must report six operations for the target workspace")
            if smoke_summary["owner_gated_workspace_operations"] != 3:
                errors.append("matter-access-smoke must report three owner-gated write plans")
            if smoke_summary["executes_graph_requests"] is not False:
                errors.append("matter-access-smoke must not execute Graph requests")
            if mcp_contract:
                apply_readiness = build_matter_access_apply_readiness(
                    contract,
                    schema,
                    mcp_contract,
                    workspace_id=schema["workspaces"][0]["id"],
                    correlation_id="validator-apply-readiness",
                    timestamp="2026-07-07T00:00:00Z",
                )
                if apply_readiness["status"] != "PASSED":
                    errors.append("matter-access-apply-readiness must pass for the first workspace")
                apply_summary = apply_readiness["summary"]
                if apply_summary["planned_apply_operation_count"] != 2:
                    errors.append("matter-access-apply-readiness must report two future apply operations")
                for flag in (
                    "grant_request_ready",
                    "audit_append_ready",
                    "required_write_approval",
                    "owner_gate_required",
                    "reason_required",
                    "valid_until_required",
                    "valid_until_after_valid_from_required",
                    "approver_required",
                    "audit_correlation_required",
                ):
                    if apply_summary.get(flag) is not True:
                        errors.append(f"matter-access-apply-readiness summary.{flag} must be true")
                for flag in (
                    "executes_graph_requests",
                    "executes_graph_writes",
                    "tenant_mutation_allowed",
                    "team_membership_mutation_allowed",
                    "sharepoint_item_permission_mutation_allowed",
                    "stores_tokens_or_secrets",
                    "stores_matter_payloads",
                ):
                    if apply_summary.get(flag) is not False:
                        errors.append(f"matter-access-apply-readiness summary.{flag} must be false")
                apply_request = build_matter_access_apply_request_plan(
                    mcp_contract,
                    load_provisioned_state(DEFAULT_PROVISIONED_STATE),
                    apply_readiness,
                    workspace_id=schema["workspaces"][0]["id"],
                    correlation_id="validator-apply-request",
                    grant_id="validator-grant",
                    case_id="validator-case",
                    from_user="validator-from-user",
                    to_user="validator-to-user",
                    reason="Validator-Vertretung",
                    approved_by="validator-approver",
                    timestamp="2026-07-07T00:00:00Z",
                )
                if apply_request["status"] != "PASSED":
                    errors.append("matter-access-apply-request-plan must pass for the first workspace")
                apply_request_summary = apply_request["summary"]
                if apply_request_summary["planned_write_count"] != 2:
                    errors.append("matter-access-apply-request-plan must report two planned writes")
                if apply_request_summary["planned_tools"] != ["grant_request", "audit_append"]:
                    errors.append("matter-access-apply-request-plan must bundle grant_request and audit_append")
                for flag in (
                    "required_write_approval",
                    "owner_gate_required",
                    "role_case_purpose_gate_required",
                    "graph_rest_only",
                ):
                    if apply_request_summary.get(flag) is not True:
                        errors.append(f"matter-access-apply-request-plan summary.{flag} must be true")
                for flag in (
                    "executes_graph_requests",
                    "executes_graph_writes",
                    "tenant_mutation_allowed",
                    "team_membership_mutation_allowed",
                    "sharepoint_item_permission_mutation_allowed",
                    "raw_graph_path_stored",
                    "raw_graph_response_stored",
                    "stores_tokens_or_secrets",
                    "stores_matter_payloads",
                    "reads_sharepoint_file_content",
                ):
                    if apply_request_summary.get(flag) is not False:
                        errors.append(f"matter-access-apply-request-plan summary.{flag} must be false")
                apply_request_text = json.dumps(apply_request, ensure_ascii=False)
                for raw_value in (
                    "validator-grant",
                    "validator-case",
                    "validator-from-user",
                    "validator-to-user",
                    "validator-approver",
                    "Validator-Vertretung",
                    "funktion8.sharepoint.com",
                ):
                    if raw_value in apply_request_text:
                        errors.append(f"matter-access-apply-request-plan stores raw value {raw_value!r}")

    if mcp_contract:
        errors.extend(validate_mcp_contract(mcp_contract))
        errors.extend(_validate_data_mcp_contract(mcp_contract))

    errors.extend(_validate_docs_and_wiring())
    return errors


def _validate_data_mcp_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    tools = {
        str(tool.get("id")): tool
        for tool in payload.get("tools", [])
        if isinstance(tool, dict) and isinstance(tool.get("id"), str)
    }
    for missing in sorted(REQUIRED_MCP_TOOLS - set(tools)):
        errors.append(f"teams-sharepoint-data-mcp missing required access tool {missing}")
    grant = tools.get("grant_request")
    if isinstance(grant, dict):
        if grant.get("list_name") != "Vertretungsfreigaben":
            errors.append("grant_request must write Vertretungsfreigaben")
        if grant.get("graph_method") != "POST":
            errors.append("grant_request must use POST")
        if grant.get("requires_role_case_purpose_gate") is not True:
            errors.append("grant_request must require role/case/purpose gate")
        if grant.get("requires_write_approval") is not True:
            errors.append("grant_request must require explicit write approval")
        if grant.get("reads_files") is not False:
            errors.append("grant_request must not read files")
        for field in (
            "grant_id",
            "case_id",
            "from_user",
            "to_user",
            "granted_role",
            "reason",
            "valid_from",
            "valid_until",
            "approved_by",
            "status",
        ):
            if field not in _strings(grant.get("required_inputs")):
                errors.append(f"grant_request required_inputs missing {field}")
    audit = tools.get("audit_append")
    if isinstance(audit, dict) and audit.get("list_name") != "AuditJournalLite":
        errors.append("audit_append must write AuditJournalLite")
    case_get = tools.get("case_get")
    if isinstance(case_get, dict) and case_get.get("list_name") != "Akten":
        errors.append("case_get must read Akten")
    return errors


def _validate_docs_and_wiring() -> list[str]:
    errors: list[str] = []
    for path, markers in REQUIRED_DOC_MARKERS.items():
        if not path.is_file():
            errors.append(f"missing file: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {marker!r}")

    for path in (QUALITY_GATE, NAC_CLI, PROVISIONER_CLI):
        if not path.is_file():
            errors.append(f"missing file: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if path == QUALITY_GATE and "m365_matter_access_delegation" not in text:
            errors.append("quality_gate.py missing m365_matter_access_delegation")
        if path in {NAC_CLI, PROVISIONER_CLI} and "matter-access-plan" not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing marker 'matter-access-plan'")
        if path in {NAC_CLI, PROVISIONER_CLI} and "matter-access-smoke" not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing marker 'matter-access-smoke'")
        if path in {NAC_CLI, PROVISIONER_CLI} and "matter-access-apply-readiness" not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing marker 'matter-access-apply-readiness'")
        if path in {NAC_CLI, PROVISIONER_CLI} and "matter-access-apply-request-plan" not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing marker 'matter-access-apply-request-plan'")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing JSON file: {path.relative_to(REPO_ROOT)}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path.relative_to(REPO_ROOT)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
        return {}
    return payload


def _reject_prohibited_text(path: Path, errors: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    for marker in sorted(PROHIBITED_TEXT_MARKERS):
        if marker in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker {marker}")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


if __name__ == "__main__":
    raise SystemExit(main())
