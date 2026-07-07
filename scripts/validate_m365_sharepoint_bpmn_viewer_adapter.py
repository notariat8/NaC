from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "m365-sharepoint-bpmn-viewer-adapter.contract.json"
CONTRACTS_README = REPO_ROOT / "workflows" / "contracts" / "README.md"
DATA_PLANE_DE = REPO_ROOT / "docs" / "de" / "architecture" / "teams-sharepoint-graph-data-plane.md"
DATA_PLANE_EN = REPO_ROOT / "docs" / "en" / "architecture" / "teams-sharepoint-graph-data-plane.md"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "m365-sharepoint-bpmn-viewer-adapter.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "m365-sharepoint-bpmn-viewer-adapter.md"
BPMN_DE = REPO_ROOT / "docs" / "de" / "bpmn-js-business-layer.md"
BPMN_EN = REPO_ROOT / "docs" / "en" / "bpmn-js-business-layer.md"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"

REQUIRED_BLOCKED_OPERATIONS = {
    "write_bpmn_xml",
    "save_bpmn_model",
    "execute_workflow",
    "start_process_instance",
    "mutate_sharepoint_schema",
    "mutate_team_or_site_membership",
    "read_matter_document_content",
    "read_matter_payload",
    "legacy_sharepoint_rest",
    "sharepoint_csom",
    "pnp",
    "microsoft_graph_sdk",
    "custom_script_page_embedding",
    "store_secrets",
    "store_mandate_data",
}
REQUIRED_ALLOWED_READS = {
    "approved_bpmn_xml",
    "process_register_metadata",
    "task_status_metadata",
    "audit_status_metadata",
    "document_register_metadata",
}
REQUIRED_ENDPOINTS = {
    "GET /sites/{site-id}/drives",
    "GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/content",
    "GET /sites/{site-id}/lists/{list-id}/items",
    "GET /sites/{site-id}/lists/{list-id}/items/{item-id}",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: M365 SharePoint BPMN viewer adapter contract, docs and quality gate are aligned.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    contract = _read_json(CONTRACT, errors)
    if contract:
        errors.extend(_validate_contract(contract))
    errors.extend(_validate_docs())
    errors.extend(_validate_quality_gate())
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing JSON artifact: {path.relative_to(REPO_ROOT)}")
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


def _validate_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version": "nac.m365-sharepoint-bpmn-viewer-adapter/v0.1",
        "contract_id": "m365.sharepoint_bpmn_viewer_adapter",
        "status": "contract_first",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key} must be {value}")

    source = payload.get("source_of_truth")
    if not isinstance(source, dict):
        errors.append("source_of_truth must be an object")
    else:
        for flag in (
            "git_remains_template_source_of_truth",
            "sharepoint_stores_viewable_copies_or_pointers",
            "python_validation_required_before_publish",
            "pull_request_required_before_publish",
        ):
            if source.get(flag) is not True:
                errors.append(f"source_of_truth.{flag} must be true")
        models = set(_as_list(source.get("approved_bpmn_templates")))
        for model_pattern in ("bpmn/*.bpmn", "bpmn/usecases/*.bpmn"):
            if model_pattern not in models:
                errors.append(f"source_of_truth.approved_bpmn_templates missing {model_pattern}")

    sharepoint = payload.get("sharepoint_surface")
    if not isinstance(sharepoint, dict):
        errors.append("sharepoint_surface must be an object")
    else:
        if sharepoint.get("site_model") != "team_connected_sharepoint_site":
            errors.append("sharepoint_surface.site_model must be team_connected_sharepoint_site")
        if sharepoint.get("approved_bpmn_xml_content_read_allowed") is not True:
            errors.append("sharepoint_surface.approved_bpmn_xml_content_read_allowed must be true")
        for flag in ("matter_document_content_reads_allowed", "matter_payload_storage_allowed"):
            if sharepoint.get(flag) is not False:
                errors.append(f"sharepoint_surface.{flag} must be false")
        libraries = {
            item.get("name")
            for item in _as_list(sharepoint.get("document_libraries"))
            if isinstance(item, dict)
        }
        if "BPMN Models" not in libraries:
            errors.append("sharepoint_surface.document_libraries must include BPMN Models")
        lists = {item.get("name") for item in _as_list(sharepoint.get("lists")) if isinstance(item, dict)}
        if "Prozessregister" not in lists:
            errors.append("sharepoint_surface.lists must include Prozessregister")

    spfx = payload.get("spfx_surface")
    if not isinstance(spfx, dict):
        errors.append("spfx_surface must be an object")
    else:
        if spfx.get("delivery") != "SharePoint Framework Web Part":
            errors.append("spfx_surface.delivery must be SharePoint Framework Web Part")
        if spfx.get("library") != "bpmn-js":
            errors.append("spfx_surface.library must be bpmn-js")
        if spfx.get("bpmn_js_mode") != "viewer_only":
            errors.append("spfx_surface.bpmn_js_mode must be viewer_only")
        for flag in (
            "modeler_enabled",
            "workflow_execution_allowed",
            "custom_script_dependency_allowed",
            "requires_custom_script",
            "modern_page_loose_html_embedding_allowed",
        ):
            if spfx.get(flag) is not False:
                errors.append(f"spfx_surface.{flag} must be false")

    graph = payload.get("graph_policy")
    if not isinstance(graph, dict):
        errors.append("graph_policy must be an object")
    else:
        if graph.get("base_url") != "https://graph.microsoft.com/v1.0":
            errors.append("graph_policy.base_url must be https://graph.microsoft.com/v1.0")
        for flag in ("graph_rest_only", "raw_http_required", "mcp_allowed_only_when_backed_by_graph_rest"):
            if graph.get(flag) is not True:
                errors.append(f"graph_policy.{flag} must be true")
        for flag in ("legacy_sharepoint_api_allowed", "csom_allowed", "pnp_allowed", "graph_sdk_allowed"):
            if graph.get(flag) is not False:
                errors.append(f"graph_policy.{flag} must be false")
        endpoints = set(_as_list(graph.get("allowed_endpoint_patterns")))
        for endpoint in sorted(REQUIRED_ENDPOINTS - endpoints):
            errors.append(f"graph_policy.allowed_endpoint_patterns missing {endpoint}")

    allowed_reads = set(_as_list(payload.get("allowed_reads")))
    for item in sorted(REQUIRED_ALLOWED_READS - allowed_reads):
        errors.append(f"allowed_reads missing {item}")

    blocked_operations = set(_as_list(payload.get("blocked_operations")))
    for item in sorted(REQUIRED_BLOCKED_OPERATIONS - blocked_operations):
        errors.append(f"blocked_operations missing {item}")

    mcp = payload.get("mcp_boundary")
    if not isinstance(mcp, dict):
        errors.append("mcp_boundary must be an object")
    else:
        if mcp.get("server_id") != "teams-sharepoint-data-mcp":
            errors.append("mcp_boundary.server_id must be teams-sharepoint-data-mcp")
        if mcp.get("new_mcp_server_required_now") is not False:
            errors.append("mcp_boundary.new_mcp_server_required_now must be false")
        for flag in (
            "tools_read_only",
            "tools_must_return_redacted_metadata",
            "tools_must_not_return_matter_document_content",
        ):
            if mcp.get(flag) is not True:
                errors.append(f"mcp_boundary.{flag} must be true")
        future_tools = set(_as_list(mcp.get("future_tools")))
        for tool in ("bpmn_model_get", "process_register_list", "bpmn_viewer_overlay_get"):
            if tool not in future_tools:
                errors.append(f"mcp_boundary.future_tools missing {tool}")

    relationship = payload.get("relationship_to_bpmn_js_editor")
    if not isinstance(relationship, dict):
        errors.append("relationship_to_bpmn_js_editor must be an object")
    else:
        for flag in (
            "sharepoint_adapter_is_viewer_only",
            "sharepoint_adapter_must_not_replace_pr_review",
            "sharepoint_adapter_must_not_write_template_models",
        ):
            if relationship.get(flag) is not True:
                errors.append(f"relationship_to_bpmn_js_editor.{flag} must be true")

    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_docs = {
        DOC_DE: [
            "SPFx",
            "bpmn-js",
            "viewer-only",
            "Microsoft Graph REST",
            "kein SharePoint-Plugin",
            "keinen BPMN-Modeler",
            "nicht die Ausführungsengine",
            "teams-sharepoint-data-mcp",
        ],
        DOC_EN: [
            "SPFx",
            "bpmn-js",
            "viewer-only",
            "Microsoft Graph REST",
            "does not build a SharePoint plugin",
            "not the source, editor or execution engine",
            "teams-sharepoint-data-mcp",
        ],
        DATA_PLANE_DE: [
            "M365 SharePoint BPMN Viewer Adapter",
            "Microsoft Graph REST",
            "SPFx",
        ],
        DATA_PLANE_EN: [
            "M365 SharePoint BPMN Viewer Adapter",
            "Microsoft Graph REST",
            "SPFx",
        ],
        BPMN_DE: [
            "M365 SharePoint BPMN Viewer Adapter",
            "Anzeigeprojektion",
        ],
        BPMN_EN: [
            "M365 SharePoint BPMN Viewer Adapter",
            "display projection",
        ],
        CONTRACTS_README: [
            "m365-sharepoint-bpmn-viewer-adapter.contract.json",
            "SPFx",
            "BPMN",
        ],
    }
    for path, markers in required_docs.items():
        if not path.is_file():
            errors.append(f"missing documentation: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {marker!r}")
    return errors


def _validate_quality_gate() -> list[str]:
    if not QUALITY_GATE.is_file():
        return [f"missing quality gate: {QUALITY_GATE.relative_to(REPO_ROOT)}"]
    text = QUALITY_GATE.read_text(encoding="utf-8")
    required = (
        "m365_sharepoint_bpmn_viewer_adapter",
        "M365 SharePoint BPMN Viewer Adapter",
        "scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py",
    )
    return [f"quality gate missing marker {marker!r}" for marker in required if marker not in text]


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
