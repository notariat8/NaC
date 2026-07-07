from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .mcp_runtime import RuntimeContext, load_mcp_contract, plan_tool_request, validate_mcp_contract
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPFX_BPMN_VIEWER_SKELETON = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-spfx-bpmn-viewer.skeleton.json"
)
DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "m365" / "spfx-bpmn-viewer" / "render-contract.fixture.json"
)
REQUIRED_MCP_TOOLS = {
    "bpmn_model_get",
    "process_register_list",
    "bpmn_viewer_overlay_get",
}
REQUIRED_BLOCKED_OPERATIONS = {
    "app_catalog_deploy",
    "tenant_wide_deploy",
    "npm_install",
    "live_tenant_apply",
    "write_bpmn_xml",
    "save_bpmn_model",
    "execute_workflow",
    "start_process_instance",
    "read_matter_document_content",
    "read_matter_payload",
    "store_tokens_or_secrets",
    "legacy_sharepoint_rest",
    "sharepoint_csom",
    "pnp",
    "microsoft_graph_sdk",
    "graph_beta",
}
SPFX_SKELETON_REQUIRED_FILES = {
    "README.md",
    "package.json",
    "config/package-solution.json",
    "src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts",
    "src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.manifest.json",
    "src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx",
    "src/webparts/nacBpmnViewer/services/BpmnViewerRequestPlan.ts",
    "src/webparts/nacBpmnViewer/fixtures/sampleBpmn.ts",
}
SPFX_SKELETON_BLOCKED_PATHS = {
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "node_modules",
    "dist",
    "lib",
    "temp",
    "sharepoint/solution",
}
SPFX_SKELETON_BLOCKED_MARKERS = {
    "Graph" + "ServiceClient",
    "MS" + "GraphClient",
    "@" + "pnp",
    "_" + "api/",
    "/" + "_api",
    "graph" + "beta",
    "gulp " + "bundle",
    "gulp " + "package-solution",
    "m365 " + "spo",
}


def load_spfx_bpmn_viewer_skeleton(
    path: Path = DEFAULT_SPFX_BPMN_VIEWER_SKELETON,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_spfx_bpmn_viewer_render_fixture(
    path: Path = DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_spfx_bpmn_viewer_skeleton(
    skeleton: dict[str, Any],
    *,
    render_fixture: dict[str, Any] | None = None,
    mcp_contract: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if skeleton.get("schema_version") != "nac.m365-spfx-bpmn-viewer-skeleton/v0.1":
        errors.append("SPFx BPMN viewer skeleton schema_version is invalid")
    if skeleton.get("status") != "offline_skeleton_no_package_deploy":
        errors.append("SPFx BPMN viewer skeleton status must be offline_skeleton_no_package_deploy")

    spfx = skeleton.get("spfx")
    if not isinstance(spfx, dict):
        errors.append("SPFx BPMN viewer skeleton spfx must be an object")
    else:
        expected = {
            "framework": "SharePoint Framework",
            "component_type": "clientSideWebPart",
            "library": "bpmn-js",
            "bpmn_js_import": "bpmn-js/lib/Viewer",
            "bpmn_js_mode": "viewer_only",
        }
        for key, value in expected.items():
            if spfx.get(key) != value:
                errors.append(f"SPFx BPMN viewer skeleton spfx.{key} must be {value}")
        if spfx.get("source_skeleton_included_now") is not True:
            errors.append("SPFx BPMN viewer skeleton spfx.source_skeleton_included_now must be true")
        package_root = spfx.get("package_root")
        if package_root != "spfx/nac-bpmn-viewer":
            errors.append("SPFx BPMN viewer skeleton spfx.package_root must be spfx/nac-bpmn-viewer")
        else:
            errors.extend(_validate_spfx_source_root(REPO_ROOT / package_root))
        for flag in (
            "modeler_enabled",
            "workflow_execution_allowed",
            "requires_custom_script",
            "loose_html_embedding_allowed",
            "actual_spfx_package_included_now",
            "package_solution_enabled_now",
            "app_catalog_deploy_allowed_now",
            "tenant_wide_deploy_allowed_now",
            "npm_install_required_now",
        ):
            if spfx.get(flag) is not False:
                errors.append(f"SPFx BPMN viewer skeleton spfx.{flag} must be false")

    render = skeleton.get("render_contract")
    if not isinstance(render, dict):
        errors.append("SPFx BPMN viewer skeleton render_contract must be an object")
    else:
        if render.get("container_id") != "nac-bpmn-viewer-container":
            errors.append("SPFx BPMN viewer skeleton render_contract.container_id is invalid")
        props = {
            item.get("name"): item
            for item in _as_list(render.get("component_props"))
            if isinstance(item, dict)
        }
        for prop in ("workspaceId", "bpmnModelId"):
            if props.get(prop, {}).get("required") is not True:
                errors.append(f"SPFx BPMN viewer skeleton render_contract must require {prop}")
        forbidden = set(_strings(render.get("forbidden_outputs")))
        for item in ("raw_matter_document_content", "tokens_or_secrets", "bpmn_model_write_payload"):
            if item not in forbidden:
                errors.append(f"SPFx BPMN viewer skeleton forbidden_outputs missing {item}")

    binding = skeleton.get("mcp_request_plan_binding")
    if not isinstance(binding, dict):
        errors.append("SPFx BPMN viewer skeleton mcp_request_plan_binding must be an object")
    else:
        if binding.get("server_id") != "teams-sharepoint-data-mcp":
            errors.append("SPFx BPMN viewer skeleton must bind teams-sharepoint-data-mcp")
        if binding.get("executes_graph_requests_now") is not False:
            errors.append("SPFx BPMN viewer skeleton must not execute Graph requests now")
        if binding.get("tools_request_plan_only_now") is not True:
            errors.append("SPFx BPMN viewer skeleton MCP tools must be request-plan-only now")
        if set(_strings(binding.get("tools"))) != REQUIRED_MCP_TOOLS:
            errors.append("SPFx BPMN viewer skeleton MCP tools must be the BPMN viewer request-plan tools")
        if set(_strings(binding.get("owner_gated_live_read_tools_enabled_now"))) != {"case_get", "document_list"}:
            errors.append("SPFx BPMN viewer skeleton live-read tools must stay case_get and document_list")

    graph = skeleton.get("graph_content_read_boundary")
    if not isinstance(graph, dict):
        errors.append("SPFx BPMN viewer skeleton graph_content_read_boundary must be an object")
    else:
        if graph.get("future_endpoint") != "GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/content":
            errors.append("SPFx BPMN viewer skeleton future content endpoint is invalid")
        if graph.get("live_content_read_enabled_now") is not False:
            errors.append("SPFx BPMN viewer skeleton live content read must be disabled now")
        if graph.get("fixture_content_allowed_now") is not True:
            errors.append("SPFx BPMN viewer skeleton fixture content must be allowed now")

    blocked = set(_strings(skeleton.get("blocked_operations")))
    for operation in sorted(REQUIRED_BLOCKED_OPERATIONS - blocked):
        errors.append(f"SPFx BPMN viewer skeleton blocked_operations missing {operation}")

    if render_fixture is not None:
        errors.extend(_validate_render_fixture(render_fixture, skeleton))
    if mcp_contract is not None:
        errors.extend(_validate_mcp_contract_binding(mcp_contract))
    return errors


def _validate_spfx_source_root(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"SPFx BPMN viewer skeleton source root missing: {root.relative_to(REPO_ROOT)}"]
    for required in sorted(SPFX_SKELETON_REQUIRED_FILES):
        if not (root / required).is_file():
            errors.append(f"SPFx BPMN viewer skeleton source missing {required}")
    for blocked in sorted(SPFX_SKELETON_BLOCKED_PATHS):
        if (root / blocked).exists():
            errors.append(f"SPFx BPMN viewer skeleton must not include {blocked}")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".json", ".md", ".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in sorted(SPFX_SKELETON_BLOCKED_MARKERS):
            if marker in text:
                rel = path.relative_to(REPO_ROOT)
                errors.append(f"SPFx BPMN viewer skeleton {rel} contains blocked marker {marker!r}")
    component = root / "src" / "webparts" / "nacBpmnViewer" / "components" / "NacBpmnViewer.tsx"
    if component.is_file():
        text = component.read_text(encoding="utf-8")
        if "bpmn-js/lib/Viewer" not in text:
            errors.append("SPFx BPMN viewer component must import bpmn-js/lib/Viewer")
        for blocked in ("Model" + "er", "save" + "XML", "start" + "Process", "execute" + "Workflow"):
            if blocked in text:
                errors.append(f"SPFx BPMN viewer component contains blocked viewer marker {blocked!r}")
    service = root / "src" / "webparts" / "nacBpmnViewer" / "services" / "BpmnViewerRequestPlan.ts"
    if service.is_file():
        text = service.read_text(encoding="utf-8")
        for tool in sorted(REQUIRED_MCP_TOOLS):
            if tool not in text:
                errors.append(f"SPFx BPMN viewer request plan service missing {tool}")
    return errors


def build_spfx_bpmn_viewer_skeleton_result(
    skeleton: dict[str, Any],
    *,
    render_fixture: dict[str, Any] | None = None,
    mcp_contract: dict[str, Any] | None = None,
    provisioned_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    render_fixture = render_fixture or load_spfx_bpmn_viewer_render_fixture()
    mcp_contract = mcp_contract or load_mcp_contract()
    provisioned_state = _state_with_optional_bpmn_viewer_lists(
        provisioned_state or load_provisioned_state(DEFAULT_PROVISIONED_STATE)
    )
    errors = validate_spfx_bpmn_viewer_skeleton(
        skeleton,
        render_fixture=render_fixture,
        mcp_contract=mcp_contract,
    )
    if errors:
        return {
            "status": "FAILED",
            "errors": errors,
        }

    context = RuntimeContext(
        actor_id="spfx-bpmn-viewer-skeleton",
        actor_role="runtime_service",
        workspace_id=str(render_fixture["workspace_id"]),
        purpose="spfx_bpmn_viewer_request_plan_fixture",
        correlation_id="spfx-bpmn-viewer-skeleton",
        case_id=str(render_fixture["component_props"].get("caseId", "")),
        role_case_gate="open",
        write_approved=False,
    )
    bpmn_model_id = str(render_fixture["component_props"]["bpmnModelId"])
    case_id = str(render_fixture["component_props"].get("caseId", ""))
    request_plans = [
        plan_tool_request(mcp_contract, provisioned_state, context, "bpmn_model_get", {"bpmn_model_id": bpmn_model_id}),
        plan_tool_request(mcp_contract, provisioned_state, context, "process_register_list", {}),
        plan_tool_request(mcp_contract, provisioned_state, context, "bpmn_viewer_overlay_get", {"case_id": case_id}),
    ]
    return {
        "status": "PASSED",
        "summary": {
            "component": skeleton["spfx"]["component_name"],
            "spfx_component_type": skeleton["spfx"]["component_type"],
            "bpmn_js_mode": skeleton["spfx"]["bpmn_js_mode"],
            "request_plan_count": len(request_plans),
            "app_catalog_deploy_allowed_now": False,
            "live_tenant_apply_allowed_now": False,
            "live_content_read_enabled_now": False,
        },
        "skeleton": {
            "schema_version": skeleton["schema_version"],
            "status": skeleton["status"],
            "artifact": "deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json",
            "fixture": skeleton["test_fixtures"]["render_contract"],
        },
        "renderContract": {
            "containerId": skeleton["render_contract"]["container_id"],
            "componentProps": render_fixture["component_props"],
            "expectedRenderState": render_fixture["expected_render_state"],
        },
        "requestPlans": [plan.to_dict() for plan in request_plans],
        "guardrails": {
            "executes_graph_requests_now": False,
            "mcp_tools_request_plan_only_now": True,
            "actual_spfx_package_included_now": False,
            "package_solution_enabled_now": False,
            "app_catalog_deploy_allowed_now": False,
            "tenant_wide_deploy_allowed_now": False,
            "npm_install_required_now": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
            "matter_document_content_reads_allowed": False,
        },
    }


def _validate_render_fixture(fixture: dict[str, Any], skeleton: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if fixture.get("schema_version") != "nac.m365-spfx-bpmn-viewer-render-fixture/v0.1":
        errors.append("SPFx BPMN viewer render fixture schema_version is invalid")
    if fixture.get("status") != "synthetic_metadata_only":
        errors.append("SPFx BPMN viewer render fixture status must be synthetic_metadata_only")
    props = fixture.get("component_props")
    if not isinstance(props, dict):
        errors.append("SPFx BPMN viewer render fixture component_props must be an object")
    else:
        for key in ("workspaceId", "bpmnModelId"):
            if not props.get(key):
                errors.append(f"SPFx BPMN viewer render fixture component_props.{key} is required")
    model = fixture.get("approved_bpmn_model")
    if not isinstance(model, dict):
        errors.append("SPFx BPMN viewer render fixture approved_bpmn_model must be an object")
    else:
        if model.get("approvalStatus") != "Approved":
            errors.append("SPFx BPMN viewer render fixture model must be approved")
        if model.get("viewerEnabled") is not True:
            errors.append("SPFx BPMN viewer render fixture model must be viewer-enabled")
        if model.get("containsMatterData") is not False:
            errors.append("SPFx BPMN viewer render fixture model must not contain matter data")
    expected_tools = set(_strings(fixture.get("expected_request_plan_tools")))
    if expected_tools != REQUIRED_MCP_TOOLS:
        errors.append("SPFx BPMN viewer render fixture expected_request_plan_tools is invalid")
    expected_state = fixture.get("expected_render_state")
    if not isinstance(expected_state, dict):
        errors.append("SPFx BPMN viewer render fixture expected_render_state must be an object")
    else:
        if expected_state.get("bpmnJsMode") != skeleton.get("spfx", {}).get("bpmn_js_mode"):
            errors.append("SPFx BPMN viewer render fixture bpmnJsMode must match skeleton")
        for flag in ("liveTenantAccess", "appCatalogDeploy"):
            if expected_state.get(flag) is not False:
                errors.append(f"SPFx BPMN viewer render fixture expected_render_state.{flag} must be false")
    return errors


def _validate_mcp_contract_binding(contract: dict[str, Any]) -> list[str]:
    errors = validate_mcp_contract(contract)
    if errors:
        return errors
    tools = {
        tool.get("id"): tool
        for tool in _as_list(contract.get("tools"))
        if isinstance(tool, dict)
    }
    for tool_id in REQUIRED_MCP_TOOLS:
        tool = tools.get(tool_id)
        if not isinstance(tool, dict):
            errors.append(f"SPFx BPMN viewer MCP binding missing tool {tool_id}")
            continue
        if tool.get("graph_method") != "GET":
            errors.append(f"SPFx BPMN viewer MCP binding {tool_id} must use GET")
        for flag in ("reads_files", "writes_items", "requires_write_approval"):
            if tool.get(flag) is not False:
                errors.append(f"SPFx BPMN viewer MCP binding {tool_id}.{flag} must be false")
    return errors


def _state_with_optional_bpmn_viewer_lists(state: dict[str, Any]) -> dict[str, Any]:
    cloned = json.loads(json.dumps(state))
    for workspace in cloned.get("workspaces", []):
        if not isinstance(workspace, dict):
            continue
        lists = workspace.setdefault("lists", {})
        if isinstance(lists, dict):
            lists.setdefault("BPMN Models", {"id": "list-bpmn-models"})
            lists.setdefault("Prozessregister", {"id": "list-process-register"})
    return cloned


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
