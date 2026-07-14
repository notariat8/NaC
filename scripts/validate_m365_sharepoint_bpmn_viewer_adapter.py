from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_m365_graph.spfx_bpmn_viewer_skeleton import (  # noqa: E402
    APPROVED_WORKSPACE_ID,
    REQUIRED_DOM_MARKERS,
    build_spfx_bpmn_viewer_skeleton_result,
    load_spfx_bpmn_viewer_render_fixture,
    validate_spfx_bpmn_viewer_skeleton,
)
from nac_m365_graph.spfx_bpmn_viewer_runtime_readiness import (  # noqa: E402
    build_bpmn_viewer_runtime_readiness_result,
    validate_bpmn_viewer_runtime_readiness,
)


CONTRACT = REPO_ROOT / "workflows" / "contracts" / "m365-sharepoint-bpmn-viewer-adapter.contract.json"
SPFX_BPMN_VIEWER_SKELETON = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-spfx-bpmn-viewer.skeleton.json"
)
BPMN_VIEWER_RUNTIME_READINESS = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-bpmn-viewer.runtime-readiness.json"
)
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "m365-sharepoint-bpmn-viewer-adapter.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "m365-sharepoint-bpmn-viewer-adapter.md"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"
GENERATED_PATHS = {
    "node_modules",
    "lib",
    "lib-commonjs",
    "dist",
    "temp",
    "sharepoint/solution",
    "release",
    "jest-output",
}
REQUIRED_BLOCKED_OPERATIONS = {
    "tenant_wide_deploy",
    "deploy_other_workspace",
    "microsoft_graph_permission_request",
    "direct_graph_request",
    "ms_graph_client",
    "aad_http_client_non_bff_resource",
    "additional_delegated_scope",
    "graph_sdk",
    "legacy_sharepoint_api",
    "pnp",
    "write_bpmn_xml",
    "save_bpmn_model",
    "execute_workflow",
    "start_process_instance",
    "write_sharepoint_data",
    "read_sharepoint_content",
    "read_matter_document_content",
    "read_matter_payload",
    "store_secrets",
    "store_mandate_data",
    "store_real_matter_data",
    "app_catalog_upload",
    "site_scoped_install",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: M365 SharePoint BPMN viewer package contract and docs are aligned.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    contract = _read_json(CONTRACT, errors)
    skeleton = _read_json(SPFX_BPMN_VIEWER_SKELETON, errors)
    readiness = _read_json(BPMN_VIEWER_RUNTIME_READINESS, errors)
    if contract:
        errors.extend(_validate_contract(contract, {}, skeleton, readiness, {}))
    if skeleton:
        errors.extend(_validate_spfx_bpmn_viewer_skeleton(skeleton))
    if readiness:
        errors.extend(_validate_bpmn_viewer_runtime_readiness(readiness, skeleton))
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
    runtime_readiness_artifact: dict[str, Any],
    data_mcp_contract: dict[str, Any],
) -> list[str]:
    del provisioning, data_mcp_contract
    errors: list[str] = []
    expected = {
        "schema_version": "nac.m365-sharepoint-bpmn-viewer-adapter/v0.4",
        "contract_id": "m365.sharepoint_bpmn_viewer_adapter",
        "status": "bff_read_site_scoped_package_ready_activation_deferred",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key} must be {value}")

    source = payload.get("source_of_truth")
    if not isinstance(source, dict):
        errors.append("source_of_truth must be an object")
    else:
        for flag in ("git_remains_template_source_of_truth", "nac_bff_redacted_dto_is_runtime_source", "package_bpmn_asset_is_model_source"):
            if source.get(flag) is not True:
                errors.append(f"source_of_truth.{flag} must be true")
        for flag in ("sharepoint_content_reads_allowed", "real_matter_data_allowed"):
            if source.get(flag) is not False:
                errors.append(f"source_of_truth.{flag} must be false")

    spfx = payload.get("spfx_surface")
    if not isinstance(spfx, dict):
        errors.append("spfx_surface must be an object")
    else:
        expected = {
            "delivery": "SharePoint Framework Web Part",
            "package_root": "spfx/nac-bpmn-viewer",
            "status": "package_ready_bff_read_site_scoped",
            "framework_version": "1.23.2",
            "build_tool": "Heft",
            "library": "bpmn-js",
            "bpmn_js_mode": "viewer_only",
        }
        for key, value in expected.items():
            if spfx.get(key) != value:
                errors.append(f"spfx_surface.{key} must be {value}")
        for flag in (
            "package_lock_required",
            "reproducible_build_required",
            "package_solution_enabled_now",
            "site_scoped",
        ):
            if spfx.get(flag) is not True:
                errors.append(f"spfx_surface.{flag} must be true")
        for flag in (
            "tenant_wide",
            "requires_custom_script",
            "modeler_enabled",
            "workflow_execution_allowed",
            "writes_sharepoint_or_bpmn",
        ):
            if spfx.get(flag) is not False:
                errors.append(f"spfx_surface.{flag} must be false")
        hosts = set(_as_list(spfx.get("supported_hosts")))
        if not {"SharePointWebPart", "TeamsTab"}.issubset(hosts):
            errors.append("spfx_surface.supported_hosts must include SharePointWebPart and TeamsTab")

    deployment = payload.get("deployment_scope")
    if not isinstance(deployment, dict):
        errors.append("deployment_scope must be an object")
    else:
        if deployment.get("approval") != "deferred_until_bff_activation":
            errors.append("deployment_scope.approval must be deferred_until_bff_activation")
        if deployment.get("activation_gate_required") is not True:
            errors.append("deployment_scope.activation_gate_required must be true")
        if deployment.get("approved_workspace_ids") != [APPROVED_WORKSPACE_ID]:
            errors.append("deployment_scope.approved_workspace_ids must contain only notary_team_01")
        for flag in (
            "app_catalog_upload_allowed_now",
            "site_scoped_install_allowed_now",
            "tenant_wide_deploy_allowed_now",
            "other_workspace_deploy_allowed_now",
        ):
            if deployment.get(flag) is not False:
                errors.append(f"deployment_scope.{flag} must be false")

    packaging = payload.get("packaging_contract")
    if not isinstance(packaging, dict):
        errors.append("packaging_contract must be an object")
    else:
        expected = {
            "package_json": "spfx/nac-bpmn-viewer/package.json",
            "package_lock": "spfx/nac-bpmn-viewer/package-lock.json",
            "package_solution": "spfx/nac-bpmn-viewer/config/package-solution.json",
            "install_command": "npm ci",
            "build_command": "npm run build",
            "package_output": "sharepoint/solution/nac-bpmn-viewer.sppkg",
        }
        for key, value in expected.items():
            if packaging.get(key) != value:
                errors.append(f"packaging_contract.{key} must be {value}")
        if set(_as_list(packaging.get("generated_paths_ignored_untracked"))) != GENERATED_PATHS:
            errors.append("packaging_contract.generated_paths_ignored_untracked is invalid")
        if packaging.get("generated_paths_excluded_from_recursive_source_scans") is not True:
            errors.append("packaging_contract.generated paths must be excluded from recursive source scans")

    synthetic = payload.get("synthetic_data_boundary")
    if not isinstance(synthetic, dict):
        errors.append("synthetic_data_boundary must be an object")
    else:
        expected = {
            "workspace_id": APPROVED_WORKSPACE_ID,
            "source": "nac_bff_redacted_dto",
            "fixture": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/fixtures/syntheticWorkspace.ts",
            "bpmn_fixture": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/fixtures/sampleBpmn.ts",
        }
        for key, value in expected.items():
            if synthetic.get(key) != value:
                errors.append(f"synthetic_data_boundary.{key} must be {value}")
        if synthetic.get("synthetic_data_only") is not True:
            errors.append("synthetic_data_boundary.synthetic_data_only must be true")
        for flag in (
            "contains_real_matter_data",
            "reads_sharepoint_content",
            "reads_matter_document_content",
            "writes_allowed",
        ):
            if synthetic.get(flag) is not False:
                errors.append(f"synthetic_data_boundary.{flag} must be false")

    graph_free = payload.get("graph_free_boundary")
    if not isinstance(graph_free, dict):
        errors.append("graph_free_boundary must be an object")
    else:
        for flag in (
            "graph_permissions_requested",
            "direct_graph_access_allowed",
            "ms_graph_client_allowed",
            "graph_sdk_allowed",
            "legacy_sharepoint_api_allowed",
            "pnp_allowed",
        ):
            if graph_free.get(flag) is not False:
                errors.append(f"graph_free_boundary.{flag} must be false")
        for flag in ("aad_http_client_allowed", "web_api_permission_requests_allowed"):
            if graph_free.get(flag) is not True:
                errors.append(f"graph_free_boundary.{flag} must be true")
        if graph_free.get("delegated_api_resource") != "api://funktion8.de/nac-bff":
            errors.append("graph_free_boundary.delegated_api_resource is invalid")
        if graph_free.get("delegated_scope") != "Matter.Read":
            errors.append("graph_free_boundary.delegated_scope must be Matter.Read")
        if graph_free.get("bff_endpoint") != "https://func-nac-bff-test-funktion8.azurewebsites.net":
            errors.append("graph_free_boundary.bff_endpoint is invalid")

    render = payload.get("package_render_contract")
    if not isinstance(render, dict):
        errors.append("package_render_contract must be an object")
    else:
        expected = {
            "slice": "spfx-bpmn-viewer-package-render-contract",
            "workspace_id": APPROVED_WORKSPACE_ID,
            "content_source": "nac_bff_redacted_dto",
            "request_plan_count": 1,
        }
        for key, value in expected.items():
            if render.get(key) != value:
                errors.append(f"package_render_contract.{key} must be {value}")
        if render.get("viewer_only") is not True:
            errors.append("package_render_contract.viewer_only must be true")
        if render.get("liveTenantAccess") is not False:
            errors.append("package_render_contract.liveTenantAccess must be false until BFF activation")
        if render.get("dom_markers") != REQUIRED_DOM_MARKERS:
            errors.append("package_render_contract.dom_markers must match the package UI")
        privacy = render.get("privacy_guards")
        if not isinstance(privacy, dict) or any(value is not False for value in privacy.values()):
            errors.append("package_render_contract.privacy_guards must all be false")

    package_link = payload.get("spfx_package")
    if not isinstance(package_link, dict):
        errors.append("spfx_package must be an object")
    else:
        expected = {
            "artifact": "deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json",
            "command": "nac m365 teams-sharepoint spfx-bpmn-viewer-skeleton --format json",
            "status": "bff_read_site_scoped_package",
        }
        for key, value in expected.items():
            if package_link.get(key) != value:
                errors.append(f"spfx_package.{key} must be {value}")
        if package_link.get("package_solution_enabled_now") is not True:
            errors.append("spfx_package.package_solution_enabled_now must be true")
        for flag in ("app_catalog_deploy_owner_approved", "site_scoped_install_allowed_now"):
            if package_link.get(flag) is not False:
                errors.append(f"spfx_package.{flag} must be false until BFF activation")
        if package_link.get("executes_bff_requests_now") is not False:
            errors.append("spfx_package.executes_bff_requests_now must be false until BFF activation")
        if package_link.get("bff_activation_status") != "DEFERRED":
            errors.append("spfx_package.bff_activation_status must be DEFERRED")
        for flag in ("tenant_wide_deploy_allowed_now", "executes_graph_requests_now"):
            if package_link.get(flag) is not False:
                errors.append(f"spfx_package.{flag} must be false")
        if spfx_skeleton and spfx_skeleton.get("status") != package_link.get("status"):
            errors.append("spfx_package status must match skeleton artifact")

    readiness = payload.get("runtime_readiness")
    if not isinstance(readiness, dict):
        errors.append("runtime_readiness must be an object")
    else:
        expected = {
            "artifact": "deploy/m365/teams-sharepoint/nac-bpmn-viewer.runtime-readiness.json",
            "command": "nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json",
            "status": "bff_read_site_scoped_package_ready_activation_deferred",
            "redacted_artifact_kind": "redacted_bff_read_site_scoped_readiness_json",
        }
        for key, value in expected.items():
            if readiness.get(key) != value:
                errors.append(f"runtime_readiness.{key} must be {value}")
        if readiness.get("spfx_package_allowed_now") is not True:
            errors.append("runtime_readiness.spfx_package_allowed_now must be true")
        for flag in (
            "app_catalog_upload_allowed_now",
            "site_scoped_install_allowed_now",
            "tenant_wide_deploy_allowed_now",
            "graph_access_allowed",
            "writes_allowed",
        ):
            if readiness.get(flag) is not False:
                errors.append(f"runtime_readiness.{flag} must be false")
        if runtime_readiness_artifact and runtime_readiness_artifact.get("status") != readiness.get("status"):
            errors.append("runtime_readiness status must match runtime-readiness artifact")

    blocked = set(_as_list(payload.get("blocked_operations")))
    for operation in sorted(REQUIRED_BLOCKED_OPERATIONS - blocked):
        errors.append(f"blocked_operations missing {operation}")

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


def _validate_spfx_bpmn_viewer_skeleton(payload: dict[str, Any]) -> list[str]:
    fixture = load_spfx_bpmn_viewer_render_fixture()
    errors = validate_spfx_bpmn_viewer_skeleton(payload, render_fixture=fixture)
    if errors:
        return errors
    result = build_spfx_bpmn_viewer_skeleton_result(payload, render_fixture=fixture)
    if result.get("status") != "READY":
        return ["SPFx BPMN viewer package result must be READY"]
    summary = result.get("summary", {})
    if summary.get("package_solution_enabled_now") is not True:
        errors.append("SPFx BPMN viewer package summary.package_solution_enabled_now must be true")
    for flag in ("app_catalog_deploy_owner_approved", "site_scoped_install_allowed_now"):
        if summary.get(flag) is not False:
            errors.append(f"SPFx BPMN viewer package summary.{flag} must be false until activation")
    for flag in ("tenant_wide_deploy_allowed_now", "executes_graph_requests_now"):
        if summary.get(flag) is not False:
            errors.append(f"SPFx BPMN viewer package summary.{flag} must be false")
    if summary.get("request_plan_count") != 1:
        errors.append("SPFx BPMN viewer package must expose exactly one NaC BFF request plan")
    if summary.get("executes_bff_requests_now") is not False:
        errors.append("SPFx BPMN viewer package summary must defer BFF reads")
    if summary.get("bff_activation_status") != "DEFERRED":
        errors.append("SPFx BPMN viewer package summary must expose deferred activation")
    return errors


def _validate_bpmn_viewer_runtime_readiness(
    payload: dict[str, Any],
    spfx_skeleton: dict[str, Any],
) -> list[str]:
    errors = validate_bpmn_viewer_runtime_readiness(payload, skeleton=spfx_skeleton or None)
    if errors:
        return errors
    result = build_bpmn_viewer_runtime_readiness_result(payload, skeleton=spfx_skeleton or None)
    if result.get("status") != "READY":
        return ["BPMN viewer runtime readiness result must be READY"]
    summary = result.get("summary", {})
    if summary.get("readiness_gate_count") != 3:
        errors.append("BPMN viewer runtime readiness must expose three readiness gates")
    for flag in ("package_build_allowed_now", "package_solution_allowed_now"):
        if summary.get(flag) is not True:
            errors.append(f"BPMN viewer runtime readiness summary.{flag} must be true")
    for flag in (
        "app_catalog_deploy_owner_approved",
        "site_scoped_install_allowed_now",
        "tenant_wide_deploy_allowed_now",
        "graph_access_allowed",
    ):
        if summary.get(flag) is not False:
            errors.append(f"BPMN viewer runtime readiness summary.{flag} must be false")
    return errors


def _validate_docs() -> list[str]:
    required_docs = {
        DOC_DE: [
            "SPFx 1.23.2",
            "Heft",
            "package-lock.json",
            "npm ci",
            "npm run build",
            "notary_team_01",
            "site-scoped",
            "DEFERRED",
            "Aktivierungs-Gate",
            "TeamsTab",
            "api://funktion8.de/nac-bff",
            "Matter.Read",
            "MSGraphClient",
            "AadHttpClient",
            "Keine Mandatsdaten",
        ],
        DOC_EN: [
            "SPFx 1.23.2",
            "Heft",
            "package-lock.json",
            "npm ci",
            "npm run build",
            "notary_team_01",
            "site-scoped",
            "DEFERRED",
            "activation gate",
            "TeamsTab",
            "api://funktion8.de/nac-bff",
            "Matter.Read",
            "MSGraphClient",
            "AadHttpClient",
            "No real matter data",
        ],
    }
    errors: list[str] = []
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
