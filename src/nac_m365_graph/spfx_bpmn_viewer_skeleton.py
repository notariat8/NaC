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
REQUIRED_GRAPH_CONTENT_METADATA_GATES = {
    "ApprovalStatus=Approved",
    "ViewerEnabled=true",
    "ContainsMatterData=false",
    "NacDataClass in Template,Demo,Reference",
    "BpmnXmlSha256 matches downloaded XML",
}
REQUIRED_RENDER_STATES = {
    "approved_renderable",
    "approval_missing_or_review_required",
    "viewer_disabled",
    "contains_matter_data",
    "invalid_mime_or_hash_missing",
}
REQUIRED_DOM_MARKERS = {
    "render_state": "data-nac-render-state",
    "content_source": "data-nac-content-source",
    "metadata_overlay": "data-nac-metadata-overlay",
}
ALLOWED_BPMN_XML_MIME_TYPES = {"application/xml", "text/xml"}
REDACTED_OVERLAY_FORBIDDEN_MARKERS = {
    "NAC-FIXTURE-CASE",
    "/sites/",
    "/drives/",
    "/lists/",
    "fields/",
    "token",
    "secret",
    "Akteninhalt",
    "Mandatswert",
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
        if set(_strings(render.get("render_states"))) != REQUIRED_RENDER_STATES:
            errors.append("SPFx BPMN viewer skeleton render_contract.render_states is invalid")
        dom_markers = render.get("dom_markers")
        if not isinstance(dom_markers, dict):
            errors.append("SPFx BPMN viewer skeleton render_contract.dom_markers must be an object")
        else:
            for key, value in REQUIRED_DOM_MARKERS.items():
                if dom_markers.get(key) != value:
                    errors.append(f"SPFx BPMN viewer skeleton render_contract.dom_markers.{key} must be {value}")
        overlay = render.get("metadata_overlay")
        if not isinstance(overlay, dict):
            errors.append("SPFx BPMN viewer skeleton render_contract.metadata_overlay must be an object")
        else:
            if overlay.get("kind") != "redacted_metadata_only":
                errors.append("SPFx BPMN viewer skeleton metadata overlay kind must be redacted_metadata_only")
            for flag in (
                "matter_content_present",
                "private_payload_values_present",
                "credential_material_present",
                "raw_graph_paths_present",
            ):
                if overlay.get(flag) is not False:
                    errors.append(f"SPFx BPMN viewer skeleton metadata_overlay.{flag} must be false")

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
        metadata_gates = set(_strings(graph.get("required_metadata_gates")))
        for gate in sorted(REQUIRED_GRAPH_CONTENT_METADATA_GATES - metadata_gates):
            errors.append(f"SPFx BPMN viewer skeleton metadata gate missing {gate}")

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
        for marker in REQUIRED_DOM_MARKERS.values():
            if marker not in text:
                errors.append(f"SPFx BPMN viewer component missing DOM marker {marker}")
        if "data-case-id" in text:
            errors.append("SPFx BPMN viewer component must not render raw case IDs into DOM attributes")
    service = root / "src" / "webparts" / "nacBpmnViewer" / "services" / "BpmnViewerRequestPlan.ts"
    if service.is_file():
        text = service.read_text(encoding="utf-8")
        for tool in sorted(REQUIRED_MCP_TOOLS):
            if tool not in text:
                errors.append(f"SPFx BPMN viewer request plan service missing {tool}")
        for render_state in sorted(REQUIRED_RENDER_STATES):
            if render_state not in text:
                errors.append(f"SPFx BPMN viewer request plan service missing render state {render_state}")
    return errors


def evaluate_spfx_bpmn_viewer_render_case(model: dict[str, Any]) -> dict[str, Any]:
    if model.get("approvalStatus") != "Approved":
        render_state = "approval_missing_or_review_required"
    elif model.get("viewerEnabled") is not True:
        render_state = "viewer_disabled"
    elif model.get("containsMatterData") is not False:
        render_state = "contains_matter_data"
    elif not _has_valid_bpmn_xml_reference(model):
        render_state = "invalid_mime_or_hash_missing"
    else:
        render_state = "approved_renderable"

    render_allowed = render_state == "approved_renderable"
    return {
        "renderState": render_state,
        "bpmnJsMode": "viewer_only",
        "contentSource": "approved_bpmn_xml_fixture" if render_allowed else "blocked_metadata_only",
        "metadataOverlay": "redacted_metadata_only",
        "renderAllowed": render_allowed,
        "liveTenantAccess": False,
        "appCatalogDeploy": False,
    }


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
    render_case_results = _build_render_case_results(render_fixture)
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
            "componentProps": _redact_component_props(render_fixture["component_props"]),
            "request_plan_count": len(request_plans),
            "liveTenantAccess": False,
            "appCatalogDeploy": False,
            "domMarkers": skeleton["render_contract"]["dom_markers"],
            "metadataOverlay": skeleton["render_contract"]["metadata_overlay"],
            "expectedRenderState": render_fixture["expected_render_state"],
            "cases": render_case_results,
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
    render_contract = fixture.get("render_contract")
    if not isinstance(render_contract, dict):
        errors.append("SPFx BPMN viewer render fixture render_contract must be an object")
    else:
        if render_contract.get("liveTenantAccess") is not False:
            errors.append("SPFx BPMN viewer render fixture render_contract.liveTenantAccess must be false")
        if render_contract.get("appCatalogDeploy") is not False:
            errors.append("SPFx BPMN viewer render fixture render_contract.appCatalogDeploy must be false")
        if render_contract.get("request_plan_count") != len(REQUIRED_MCP_TOOLS):
            errors.append("SPFx BPMN viewer render fixture request_plan_count must be 3")
        dom_markers = render_contract.get("dom_markers")
        if not isinstance(dom_markers, dict):
            errors.append("SPFx BPMN viewer render fixture dom_markers must be an object")
        else:
            for key, value in REQUIRED_DOM_MARKERS.items():
                if dom_markers.get(key) != value:
                    errors.append(f"SPFx BPMN viewer render fixture dom_markers.{key} must be {value}")
        if render_contract.get("metadata_overlay") != "redacted_metadata_only":
            errors.append("SPFx BPMN viewer render fixture metadata_overlay must be redacted_metadata_only")
        redaction = render_contract.get("redaction_policy")
        if not isinstance(redaction, dict):
            errors.append("SPFx BPMN viewer render fixture redaction_policy must be an object")
        else:
            for flag in (
                "matter_content_present",
                "private_payload_values_present",
                "credential_material_present",
                "raw_graph_paths_present",
            ):
                if redaction.get(flag) is not False:
                    errors.append(f"SPFx BPMN viewer render fixture redaction_policy.{flag} must be false")
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
        if model.get("bpmnContentMode") != "ApprovedCopy":
            errors.append("SPFx BPMN viewer render fixture model must be an approved BPMN copy")
        if model.get("bpmnXmlMimeType") not in {"application/xml", "text/xml"}:
            errors.append("SPFx BPMN viewer render fixture model must use an allowed BPMN XML mime type")
        if not model.get("bpmnDriveItemId"):
            errors.append("SPFx BPMN viewer render fixture model must include bpmnDriveItemId")
        if evaluate_spfx_bpmn_viewer_render_case(model).get("renderState") != "approved_renderable":
            errors.append("SPFx BPMN viewer render fixture approved_bpmn_model must evaluate as approved_renderable")
    cases = _as_list(fixture.get("render_cases"))
    case_names = {item.get("name") for item in cases if isinstance(item, dict)}
    if case_names != REQUIRED_RENDER_STATES:
        errors.append("SPFx BPMN viewer render fixture render_cases must cover all required states")
    for item in cases:
        if not isinstance(item, dict):
            errors.append("SPFx BPMN viewer render fixture render_cases entries must be objects")
            continue
        name = item.get("name")
        case_model = item.get("bpmn_model")
        if not isinstance(case_model, dict):
            errors.append(f"SPFx BPMN viewer render case {name!r} bpmn_model must be an object")
            continue
        decision = evaluate_spfx_bpmn_viewer_render_case(case_model)
        if decision.get("renderState") != name:
            errors.append(f"SPFx BPMN viewer render case {name!r} does not evaluate to its name")
        expected = item.get("expected_render_state")
        if not isinstance(expected, dict):
            errors.append(f"SPFx BPMN viewer render case {name!r} expected_render_state must be an object")
        else:
            for key, value in decision.items():
                if expected.get(key) != value:
                    errors.append(f"SPFx BPMN viewer render case {name!r} expected_render_state.{key} is invalid")
        overlay = item.get("redacted_overlay")
        if not isinstance(overlay, dict):
            errors.append(f"SPFx BPMN viewer render case {name!r} redacted_overlay must be an object")
        else:
            errors.extend(_validate_redacted_overlay(overlay, f"render case {name!r}"))
    expected_tools = set(_strings(fixture.get("expected_request_plan_tools")))
    if expected_tools != REQUIRED_MCP_TOOLS:
        errors.append("SPFx BPMN viewer render fixture expected_request_plan_tools is invalid")
    expected_state = fixture.get("expected_render_state")
    if not isinstance(expected_state, dict):
        errors.append("SPFx BPMN viewer render fixture expected_render_state must be an object")
    else:
        if expected_state.get("bpmnJsMode") != skeleton.get("spfx", {}).get("bpmn_js_mode"):
            errors.append("SPFx BPMN viewer render fixture bpmnJsMode must match skeleton")
        approved_decision = evaluate_spfx_bpmn_viewer_render_case(model if isinstance(model, dict) else {})
        for key, value in approved_decision.items():
            if expected_state.get(key) != value:
                errors.append(f"SPFx BPMN viewer render fixture expected_render_state.{key} is invalid")
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


def _has_valid_bpmn_xml_reference(model: dict[str, Any]) -> bool:
    return bool(model.get("bpmnXmlSha256")) and model.get("bpmnXmlMimeType") in ALLOWED_BPMN_XML_MIME_TYPES


def _build_render_case_results(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for item in _as_list(fixture.get("render_cases")):
        if not isinstance(item, dict) or not isinstance(item.get("bpmn_model"), dict):
            continue
        decision = evaluate_spfx_bpmn_viewer_render_case(item["bpmn_model"])
        results.append(
            {
                "name": item.get("name"),
                "renderState": decision["renderState"],
                "contentSource": decision["contentSource"],
                "metadataOverlay": decision["metadataOverlay"],
                "renderAllowed": decision["renderAllowed"],
                "redactedOverlay": _redacted_overlay(decision),
            }
        )
    return results


def _redact_component_props(props: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(props)
    if redacted.get("caseId"):
        redacted["caseId"] = "redacted"
    return redacted


def _redacted_overlay(decision: dict[str, Any]) -> dict[str, str]:
    return {
        "state": str(decision["renderState"]),
        "content_source": str(decision["contentSource"]),
        "case_context": "redacted",
        "data_boundary": "metadata_only",
    }


def _validate_redacted_overlay(overlay: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    overlay_text = json.dumps(overlay, sort_keys=True)
    for marker in sorted(REDACTED_OVERLAY_FORBIDDEN_MARKERS):
        if marker in overlay_text:
            errors.append(f"SPFx BPMN viewer {label} redacted overlay contains forbidden marker {marker!r}")
    expected_values = {
        "case_context": "redacted",
        "data_boundary": "metadata_only",
    }
    for key, value in expected_values.items():
        if overlay.get(key) != value:
            errors.append(f"SPFx BPMN viewer {label} redacted overlay {key} must be {value}")
    if overlay.get("state") not in REQUIRED_RENDER_STATES:
        errors.append(f"SPFx BPMN viewer {label} redacted overlay state is invalid")
    if overlay.get("content_source") not in {"approved_bpmn_xml_fixture", "blocked_metadata_only"}:
        errors.append(f"SPFx BPMN viewer {label} redacted overlay content_source is invalid")
    return errors


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
