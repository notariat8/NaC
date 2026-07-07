from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.bpmn_viewer_provisioning import (  # noqa: E402
    build_bpmn_viewer_provisioning_plan,
    summarize_bpmn_viewer_provisioning_plan,
    validate_bpmn_viewer_provisioning_config,
)
from nac_m365_graph.spfx_bpmn_viewer_skeleton import (  # noqa: E402
    build_spfx_bpmn_viewer_skeleton_result,
    load_spfx_bpmn_viewer_render_fixture,
    validate_spfx_bpmn_viewer_skeleton,
)

CONTRACT = REPO_ROOT / "workflows" / "contracts" / "m365-sharepoint-bpmn-viewer-adapter.contract.json"
BPMN_VIEWER_PROVISIONING = REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-bpmn-viewer.provisioning.json"
SPFX_BPMN_VIEWER_SKELETON = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-spfx-bpmn-viewer.skeleton.json"
)
DATA_MCP_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "teams-sharepoint-data-mcp.contract.json"
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
    "app_catalog_deploy",
    "tenant_wide_deploy",
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
    bpmn_viewer_provisioning = _read_json(BPMN_VIEWER_PROVISIONING, errors)
    spfx_bpmn_viewer_skeleton = _read_json(SPFX_BPMN_VIEWER_SKELETON, errors)
    data_mcp_contract = _read_json(DATA_MCP_CONTRACT, errors)
    if contract:
        errors.extend(
            _validate_contract(
                contract,
                bpmn_viewer_provisioning,
                spfx_bpmn_viewer_skeleton,
                data_mcp_contract,
            )
        )
    if bpmn_viewer_provisioning:
        errors.extend(_validate_bpmn_viewer_provisioning(bpmn_viewer_provisioning))
    if spfx_bpmn_viewer_skeleton:
        errors.extend(_validate_spfx_bpmn_viewer_skeleton(spfx_bpmn_viewer_skeleton, data_mcp_contract))
    if data_mcp_contract:
        errors.extend(_validate_data_mcp_contract(data_mcp_contract))
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


def _validate_contract(
    payload: dict[str, Any],
    provisioning: dict[str, Any],
    spfx_skeleton: dict[str, Any],
    data_mcp_contract: dict[str, Any],
) -> list[str]:
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
        expected = {
            "included_in_nac_repo_now": True,
            "source_skeleton_included_now": True,
            "uses_mock_or_fixture_bpmn_now": True,
            "uses_bpmn_js_viewer_only": True,
        }
        for key, value in expected.items():
            if spfx.get(key) is not value:
                errors.append(f"spfx_surface.{key} must be {value}")
        if spfx.get("package_root") != "spfx/nac-bpmn-viewer":
            errors.append("spfx_surface.package_root must be spfx/nac-bpmn-viewer")
        if spfx.get("status") != "offline_source_only":
            errors.append("spfx_surface.status must be offline_source_only")
        for flag in (
            "npm_install_required_now",
            "build_required_now",
            "app_catalog_deploy_allowed_now",
            "tenant_apply_allowed_now",
            "executes_graph_requests_now",
            "uses_bpmn_js_modeler",
            "writes_sharepoint_or_bpmn",
            "modeler_enabled",
            "workflow_execution_allowed",
            "custom_script_dependency_allowed",
            "requires_custom_script",
            "modern_page_loose_html_embedding_allowed",
        ):
            if spfx.get(flag) is not False:
                errors.append(f"spfx_surface.{flag} must be false")

    optional_plan = payload.get("optional_provisioning_plan")
    if not isinstance(optional_plan, dict):
        errors.append("optional_provisioning_plan must be an object")
    else:
        expected = {
            "artifact": "deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json",
            "command": "nac m365 teams-sharepoint bpmn-viewer-plan --format json",
            "status": "optional_plan_only_no_live_apply",
        }
        for key, value in expected.items():
            if optional_plan.get(key) != value:
                errors.append(f"optional_provisioning_plan.{key} must be {value}")
        for flag in (
            "adds_to_required_mvp_schema_now",
            "live_apply_implemented",
            "mutates_tenant_now",
        ):
            if optional_plan.get(flag) is not False:
                errors.append(f"optional_provisioning_plan.{flag} must be false")
        if optional_plan.get("owner_gate_required_before_future_apply") is not True:
            errors.append("optional_provisioning_plan.owner_gate_required_before_future_apply must be true")
        if set(_as_list(optional_plan.get("planned_document_libraries"))) != {"BPMN Models"}:
            errors.append("optional_provisioning_plan.planned_document_libraries must be BPMN Models")
        if set(_as_list(optional_plan.get("planned_lists"))) != {"Prozessregister"}:
            errors.append("optional_provisioning_plan.planned_lists must be Prozessregister")
        if provisioning:
            live_apply = provisioning.get("live_apply", {})
            if live_apply.get("implemented") != optional_plan.get("live_apply_implemented"):
                errors.append("optional_provisioning_plan live_apply flag must match provisioning artifact")
            if live_apply.get("mutates_tenant_now") != optional_plan.get("mutates_tenant_now"):
                errors.append("optional_provisioning_plan tenant mutation flag must match provisioning artifact")

    offline_skeleton = payload.get("offline_spfx_skeleton")
    if not isinstance(offline_skeleton, dict):
        errors.append("offline_spfx_skeleton must be an object")
    else:
        expected = {
            "artifact": "deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json",
            "package_root": "spfx/nac-bpmn-viewer",
            "command": "nac m365 teams-sharepoint spfx-bpmn-viewer-skeleton --format json",
            "status": "offline_skeleton_no_package_deploy",
        }
        for key, value in expected.items():
            if offline_skeleton.get(key) != value:
                errors.append(f"offline_spfx_skeleton.{key} must be {value}")
        if offline_skeleton.get("source_skeleton_included_now") is not True:
            errors.append("offline_spfx_skeleton.source_skeleton_included_now must be true")
        for flag in (
            "actual_spfx_package_included_now",
            "package_solution_enabled_now",
            "app_catalog_deploy_allowed_now",
            "tenant_apply_allowed_now",
            "executes_graph_requests_now",
        ):
            if offline_skeleton.get(flag) is not False:
                errors.append(f"offline_spfx_skeleton.{flag} must be false")
        if spfx_skeleton:
            if spfx_skeleton.get("status") != offline_skeleton.get("status"):
                errors.append("offline_spfx_skeleton status must match skeleton artifact")

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
        request_plan_tools = set(_as_list(mcp.get("request_plan_tools_enabled_now")))
        if request_plan_tools != {"bpmn_model_get", "process_register_list", "bpmn_viewer_overlay_get"}:
            errors.append("mcp_boundary.request_plan_tools_enabled_now must contain only BPMN viewer metadata tools")
        live_read_tools = set(_as_list(mcp.get("owner_gated_live_read_tools_enabled_now")))
        if live_read_tools != {"case_get", "document_list"}:
            errors.append("mcp_boundary.owner_gated_live_read_tools_enabled_now must stay case_get/document_list")
        if data_mcp_contract:
            data_tools = {
                tool.get("id")
                for tool in _as_list(data_mcp_contract.get("tools"))
                if isinstance(tool, dict)
            }
            for tool in request_plan_tools:
                if tool not in data_tools:
                    errors.append(f"teams-sharepoint-data-mcp missing request-plan tool {tool}")

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


def _validate_bpmn_viewer_provisioning(payload: dict[str, Any]) -> list[str]:
    errors = validate_bpmn_viewer_provisioning_config(payload)
    if errors:
        return errors
    operations = build_bpmn_viewer_provisioning_plan(payload)
    summary = summarize_bpmn_viewer_provisioning_plan(operations)
    if summary.get("operation_count", 0) < 1:
        errors.append("bpmn viewer provisioning plan must emit operations")
    if summary.get("owner_gated_operations") != summary.get("operation_count"):
        errors.append("bpmn viewer provisioning operations must all be owner-gated")
    if summary.get("mutates_tenant_now") is not False:
        errors.append("bpmn viewer provisioning plan must not mutate the tenant now")
    if summary.get("live_apply_implemented") is not False:
        errors.append("bpmn viewer provisioning live apply must not be implemented in this slice")
    sharepoint = payload.get("sharepoint", {})
    library_names = {
        item.get("display_name")
        for item in _as_list(sharepoint.get("document_libraries"))
        if isinstance(item, dict)
    }
    list_names = {
        item.get("display_name")
        for item in _as_list(sharepoint.get("lists"))
        if isinstance(item, dict)
    }
    if library_names != {"BPMN Models"}:
        errors.append("bpmn viewer provisioning document libraries must only add BPMN Models")
    if list_names != {"Prozessregister"}:
        errors.append("bpmn viewer provisioning lists must only add Prozessregister")
    return errors


def _validate_spfx_bpmn_viewer_skeleton(
    payload: dict[str, Any],
    data_mcp_contract: dict[str, Any],
) -> list[str]:
    render_fixture = load_spfx_bpmn_viewer_render_fixture()
    errors = validate_spfx_bpmn_viewer_skeleton(
        payload,
        render_fixture=render_fixture,
        mcp_contract=data_mcp_contract if data_mcp_contract else None,
    )
    if errors:
        return errors
    result = build_spfx_bpmn_viewer_skeleton_result(
        payload,
        render_fixture=render_fixture,
        mcp_contract=data_mcp_contract if data_mcp_contract else None,
    )
    if result.get("status") != "PASSED":
        errors.append("SPFx BPMN viewer skeleton result must pass")
        return errors
    summary = result.get("summary", {})
    if summary.get("request_plan_count") != 3:
        errors.append("SPFx BPMN viewer skeleton must expose three MCP request plans")
    for flag in (
        "app_catalog_deploy_allowed_now",
        "live_tenant_apply_allowed_now",
        "live_content_read_enabled_now",
    ):
        if summary.get(flag) is not False:
            errors.append(f"SPFx BPMN viewer skeleton summary.{flag} must be false")
    return errors


def _validate_data_mcp_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("server_id") != "teams-sharepoint-data-mcp":
        errors.append("teams-sharepoint-data-mcp server_id is invalid")
    if payload.get("graph", {}).get("rest_only") is not True:
        errors.append("teams-sharepoint-data-mcp graph.rest_only must be true")
    live_read = payload.get("runtime_boundary", {}).get("owner_gated_live_read_mode", {})
    if set(_as_list(live_read.get("allowed_tools"))) != {"case_get", "document_list"}:
        errors.append("teams-sharepoint-data-mcp live-read tools must remain case_get and document_list")
    tools = {
        tool.get("id"): tool
        for tool in _as_list(payload.get("tools"))
        if isinstance(tool, dict)
    }
    expected = {
        "bpmn_model_get": "BPMN Models",
        "process_register_list": "Prozessregister",
        "bpmn_viewer_overlay_get": "AufgabenFristen",
    }
    for tool_id, list_name in expected.items():
        tool = tools.get(tool_id)
        if not isinstance(tool, dict):
            errors.append(f"teams-sharepoint-data-mcp missing {tool_id}")
            continue
        if tool.get("graph_method") != "GET":
            errors.append(f"teams-sharepoint-data-mcp {tool_id} must use GET")
        if tool.get("list_name") != list_name:
            errors.append(f"teams-sharepoint-data-mcp {tool_id} must target {list_name}")
        for flag in ("reads_items", "requires_role_case_purpose_gate"):
            if tool.get(flag) is not True:
                errors.append(f"teams-sharepoint-data-mcp {tool_id}.{flag} must be true")
        for flag in ("reads_files", "writes_items", "requires_write_approval"):
            if tool.get(flag) is not False:
                errors.append(f"teams-sharepoint-data-mcp {tool_id}.{flag} must be false")
    blocked = set(_as_list(payload.get("blocked_operations")))
    for operation in ("bpmn_model_write", "bpmn_modeler_save", "workflow_execution"):
        if operation not in blocked:
            errors.append(f"teams-sharepoint-data-mcp blocked_operations missing {operation}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_docs = {
        DOC_DE: [
            "SPFx",
            "bpmn-js",
            "viewer-only",
            "spfx-bpmn-viewer-skeleton",
            "bpmn-viewer-plan",
            "optional_plan_only_no_live_apply",
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
            "spfx-bpmn-viewer-skeleton",
            "bpmn-viewer-plan",
            "optional_plan_only_no_live_apply",
            "Microsoft Graph REST",
            "does not build a SharePoint plugin",
            "not the source, editor or execution engine",
            "teams-sharepoint-data-mcp",
        ],
        DATA_PLANE_DE: [
            "M365 SharePoint BPMN Viewer Adapter",
            "Microsoft Graph REST",
            "SPFx",
            "nac-bpmn-viewer.provisioning.json",
        ],
        DATA_PLANE_EN: [
            "M365 SharePoint BPMN Viewer Adapter",
            "Microsoft Graph REST",
            "SPFx",
            "nac-bpmn-viewer.provisioning.json",
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
            "spfx/nac-bpmn-viewer",
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
