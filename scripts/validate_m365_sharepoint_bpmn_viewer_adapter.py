from __future__ import annotations

import hashlib
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
    REQUIRED_TASK_NAVIGATION,
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
SPFX_PACKAGE_JSON = REPO_ROOT / "spfx" / "nac-bpmn-viewer" / "package.json"
SPFX_SOURCE_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer" / "src"
CURRENT_STEP_AST_VALIDATOR = (
    REPO_ROOT / "spfx" / "nac-bpmn-viewer" / "scripts" / "validate-current-step-contract.cjs"
)
READ_ONLY_AST_VALIDATOR = (
    REPO_ROOT / "spfx" / "nac-bpmn-viewer" / "scripts" / "validate-read-only-boundary.cjs"
)
VISUAL_FIXTURE_GENERATOR = (
    REPO_ROOT / "spfx" / "nac-bpmn-viewer" / "scripts" / "generate-role-deadline-visual-fixture.cjs"
)
VISUAL_EVIDENCE_CAPTURE = (
    REPO_ROOT / "spfx" / "nac-bpmn-viewer" / "scripts" / "capture-role-deadline-visual-evidence.cjs"
)
VISUAL_EVIDENCE_ROOT = REPO_ROOT / "assets" / "docs" / "spfx-role-deadline-cockpit"
VISUAL_EVIDENCE_MANIFEST = VISUAL_EVIDENCE_ROOT / "VIS-710-manifest.json"
VISUAL_SOURCE_PATHS = (
    "bpmn/immobilienkaufvertrag.bpmn",
    "spfx/nac-bpmn-viewer/package.json",
    "spfx/nac-bpmn-viewer/package-lock.json",
    "spfx/nac-bpmn-viewer/scripts/capture-role-deadline-visual-evidence.cjs",
    "spfx/nac-bpmn-viewer/scripts/generate-role-deadline-visual-fixture.cjs",
    "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacBpmnViewer.styles.ts",
    "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx",
    "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/components/WorkspaceViewModel.ts",
)
VISUAL_EVIDENCE_CASES = {
    "VIS-710-01": {
        "file": "VIS-710-01-desktop-light.png",
        "viewport": {"width": 1440, "height": 1000},
        "containerWidth": None,
        "query": "?selected=deadline",
        "dark": False,
        "filter": "all",
        "current": ["Task_EntwurfAbstimmen"],
        "selected": ["Task_NachweiseNachhalten"],
        "selectedTasks": ["NAC-SYN-DEADLINE-001"],
        "detailTitle": "Abschlussfrist überwachen",
    },
    "VIS-710-02": {
        "file": "VIS-710-02-narrow-light.png",
        "viewport": {"width": 390, "height": 844},
        "containerWidth": None,
        "query": "?filter=deadline",
        "dark": False,
        "filter": "deadline",
        "current": ["Task_EntwurfAbstimmen"],
        "selected": ["Task_NachweiseNachhalten"],
        "selectedTasks": ["NAC-SYN-DEADLINE-001"],
        "detailTitle": "Abschlussfrist überwachen",
    },
    "VIS-710-03": {
        "file": "VIS-710-03-desktop-dark.png",
        "viewport": {"width": 1440, "height": 1000},
        "containerWidth": None,
        "query": "?theme=dark&filter=notary",
        "dark": True,
        "filter": "notary",
        "current": ["Task_EntwurfAbstimmen"],
        "selected": ["Task_EntwurfAbstimmen"],
        "selectedTasks": ["NAC-SYN-TASK-001"],
        "detailTitle": "Entwurf prüfen",
    },
    "VIS-710-04": {
        "file": "VIS-710-04-narrow-dark-empty.png",
        "viewport": {"width": 390, "height": 844},
        "containerWidth": None,
        "query": "?theme=dark&state=empty",
        "dark": True,
        "filter": "notary",
        "current": ["Task_EntwurfAbstimmen"],
        "selected": [],
        "selectedTasks": [],
        "detailTitle": None,
    },
    "VIS-710-05": {
        "file": "VIS-710-05-error-retry.png",
        "viewport": {"width": 390, "height": 320},
        "containerWidth": None,
        "query": "?state=error",
        "dark": False,
        "filter": None,
        "current": [],
        "selected": [],
        "selectedTasks": [],
        "detailTitle": None,
    },
    "VIS-710-06": {
        "file": "VIS-710-06-narrow-container-light.png",
        "viewport": {"width": 1440, "height": 1000},
        "containerWidth": 390,
        "query": "?selected=deadline",
        "dark": False,
        "filter": "all",
        "current": ["Task_EntwurfAbstimmen"],
        "selected": ["Task_NachweiseNachhalten"],
        "selectedTasks": ["NAC-SYN-DEADLINE-001"],
        "detailTitle": "Abschlussfrist überwachen",
    },
}
VISUAL_EMBEDDED_ASSETS = (
    "spfx/nac-bpmn-viewer/node_modules/bpmn-js/dist/assets/diagram-js.css",
    "spfx/nac-bpmn-viewer/node_modules/bpmn-js/dist/bpmn-viewer.production.min.js",
)
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
    errors.extend(_validate_spfx_ast_gate())
    errors.extend(_validate_spfx_source_boundary())
    errors.extend(_validate_visual_evidence_manifest())
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
        "schema_version": "nac.m365-sharepoint-bpmn-viewer-adapter/v0.6",
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
        for flag in ("git_remains_template_source_of_truth", "nac_bff_redacted_dto_is_runtime_source", "bff_canonical_bpmn_asset_is_model_source"):
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
            "current_step_ast_validator": "spfx/nac-bpmn-viewer/scripts/validate-current-step-contract.cjs",
            "package_output": "sharepoint/solution/nac-bpmn-viewer.sppkg",
        }
        for key, value in expected.items():
            if packaging.get(key) != value:
                errors.append(f"packaging_contract.{key} must be {value}")
        if packaging.get("current_step_ast_tamper_self_tests_required") is not True:
            errors.append("packaging_contract.current_step_ast_tamper_self_tests_required must be true")
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
            "workspace_contract_test": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.test.ts",
            "bpmn_source": "bpmn/immobilienkaufvertrag.bpmn",
            "bpmn_runtime_delivery": "nac_bff_embedded_dto",
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

    current_step = payload.get("current_step_binding")
    expected_current_step = {
        "source_exact": "matter.tasks[0].stepCode",
        "marker_class_exact": "nac-current-step",
        "dom_attribute_exact": "data-nac-current-step",
        "marker_count_exact": 1,
        "missing_task_behavior_exact": "render_failed",
        "missing_element_behavior_exact": "render_failed",
        "browser_mapping_table_allowed": False,
    }
    if current_step != expected_current_step:
        errors.append("current_step_binding must match the fail-closed package UI")

    expected_task_navigation = {
        "source_exact": "matter.tasks",
        "initial_selection_exact": "matter.tasks[0]",
        "selected_marker_class_exact": "nac-selected-step",
        "selected_dom_attribute_exact": "data-nac-selected-step",
        "task_dom_attribute_exact": "data-nac-task-id",
        "selected_marker_count_exact": 1,
        "current_marker_remains_fixed": True,
        "native_button_required": True,
        "pointer_enter_space_required": True,
        "aria_pressed_required": True,
        "unique_task_id_required": True,
        "unique_step_code_required": True,
        "all_step_codes_resolved_before_ready": True,
        "resolved_element_instance_of_exact": "bpmn:Task",
        "null_due_at_text_exact": "Keine eigene Frist",
        "nonnull_due_at_source_exact": "selectedTask.dueAt",
        "approval_source_exact": "selectedTask.requiresNotaryApproval",
        "approval_required_text_exact": "Notarielle Freigabe erforderlich",
        "approval_not_required_text_exact": "Keine notarielle Freigabe erforderlich",
        "binding_error_behavior_exact": "render_failed_before_matter_metadata",
        "marker_transition_error_behavior_exact": "render_failed_and_viewer_destroyed",
        "denied_metadata_visible": False,
        "deputy_grant_details_visible": False,
        "invented_assignees_allowed": False,
    }
    if payload.get("task_navigation") != expected_task_navigation:
        errors.append("task_navigation must match the fail-closed package UI")
    if payload.get("task_navigation_issue") != "https://github.com/notariat8/NaC/issues/684":
        errors.append("task_navigation_issue must reference issue 684")
    if (
        spfx_skeleton
        and spfx_skeleton.get("render_contract", {}).get("task_navigation")
        != REQUIRED_TASK_NAVIGATION
    ):
        errors.append("task_navigation must match the SPFx skeleton")

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
            "data-nac-current-step",
            "nac-current-step",
            "matter.tasks[0].stepCode",
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
            "data-nac-current-step",
            "nac-current-step",
            "matter.tasks[0].stepCode",
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


def _validate_spfx_ast_gate() -> list[str]:
    errors: list[str] = []
    package = _read_json(SPFX_PACKAGE_JSON, errors)
    if package:
        scripts = package.get("scripts")
        if not isinstance(scripts, dict):
            errors.append("SPFx package scripts must be an object")
        else:
            validator_command = "node scripts/validate-current-step-contract.cjs"
            if scripts.get("validate:current-step") != validator_command:
                errors.append("SPFx validate:current-step script must invoke the canonical AST validator")
            read_only_command = "node scripts/validate-read-only-boundary.cjs"
            if scripts.get("validate:read-only") != read_only_command:
                errors.append("SPFx validate:read-only script must invoke the read-only AST validator")
            visual_command = "node scripts/generate-role-deadline-visual-fixture.cjs"
            if scripts.get("visual:fixture") != visual_command:
                errors.append("SPFx visual:fixture script must invoke the canonical synthetic generator")
            capture_command = "node scripts/capture-role-deadline-visual-evidence.cjs"
            if scripts.get("visual:capture") != capture_command:
                errors.append("SPFx visual:capture script must invoke the canonical evidence harness")
            build = scripts.get("build")
            if not isinstance(build, str) or not build.startswith("npm run validate:current-step && "):
                errors.append("SPFx build must run validate:current-step first")
            elif "npm run validate:read-only && " not in build:
                errors.append("SPFx build must run validate:read-only")
            elif "npm run visual:fixture -- /tmp/nac-spfx-role-deadline-cockpit.html" not in build:
                errors.append("SPFx build must generate the synthetic visual fixture")
    if not CURRENT_STEP_AST_VALIDATOR.is_file():
        errors.append(
            f"missing AST validator: {CURRENT_STEP_AST_VALIDATOR.relative_to(REPO_ROOT)}"
        )
    if not READ_ONLY_AST_VALIDATOR.is_file():
        errors.append(
            f"missing read-only AST validator: {READ_ONLY_AST_VALIDATOR.relative_to(REPO_ROOT)}"
        )
    if not VISUAL_FIXTURE_GENERATOR.is_file():
        errors.append(
            f"missing visual fixture generator: {VISUAL_FIXTURE_GENERATOR.relative_to(REPO_ROOT)}"
        )
    if not VISUAL_EVIDENCE_CAPTURE.is_file():
        errors.append(
            f"missing visual evidence capture: {VISUAL_EVIDENCE_CAPTURE.relative_to(REPO_ROOT)}"
        )
    return errors


def _validate_spfx_source_boundary() -> list[str]:
    errors: list[str] = []
    forbidden = {
        "fetch(": "direct fetch",
        "XMLHttpRequest": "XMLHttpRequest",
        "/_api/": "legacy SharePoint REST",
        "graph.microsoft.com": "direct Microsoft Graph",
        "MSGraphClient": "Graph SDK client",
        "@pnp/": "PnP client",
        "bpmn-js/lib/Modeler": "BPMN modeler",
        "saveXML": "BPMN write",
        ".post(": "HTTP POST",
        ".put(": "HTTP PUT",
        ".patch(": "HTTP PATCH",
        ".delete(": "HTTP DELETE",
    }
    for path in sorted(SPFX_SOURCE_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in {".ts", ".tsx"}:
            continue
        source = path.read_text(encoding="utf-8")
        compact = "".join(source.split())
        for marker, label in forbidden.items():
            candidate = "".join(marker.split())
            if candidate in compact:
                errors.append(
                    f"{path.relative_to(REPO_ROOT)} contains forbidden {label} boundary"
                )
    return errors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_visual_evidence_manifest() -> list[str]:
    errors: list[str] = []
    manifest = _read_json(VISUAL_EVIDENCE_MANIFEST, errors)
    if not manifest:
        return errors

    expected_header = {
        "schemaVersion": "nac.spfx-role-deadline-visual-evidence/v0.2",
        "evaluationTimestamp": "2026-08-25T16:00:00Z",
        "containsOnlySyntheticData": True,
        "tenantAccess": False,
        "componentE2e": False,
        "evidenceKind": "offline_visual_contract",
    }
    for key, value in expected_header.items():
        if manifest.get(key) != value:
            errors.append(f"visual evidence {key} must be {value!r}")
    browser = manifest.get("browser")
    if not isinstance(browser, str) or not browser.startswith("Chromium "):
        errors.append("visual evidence browser must identify Chromium")
    if manifest.get("playwrightVersion") != "1.55.0":
        errors.append("visual evidence playwrightVersion must be 1.55.0")
    node_version = manifest.get("nodeVersion")
    if not isinstance(node_version, str) or not node_version.startswith("v22."):
        errors.append("visual evidence nodeVersion must identify pinned Node 22")

    embedded_assets = manifest.get("embeddedAssets")
    embedded_by_path: dict[str, Any] = {}
    if not isinstance(embedded_assets, list):
        errors.append("visual evidence embeddedAssets must be a list")
    else:
        for item in embedded_assets:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                errors.append("visual evidence embeddedAssets entries must have paths")
                continue
            embedded_by_path[item["path"]] = item
    if set(embedded_by_path) != set(VISUAL_EMBEDDED_ASSETS):
        errors.append("visual evidence embeddedAssets must match canonical bpmn-js inputs")
    for relative_path in VISUAL_EMBEDDED_ASSETS:
        item = embedded_by_path.get(relative_path)
        digest = item.get("sha256") if isinstance(item, dict) else None
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append(f"visual evidence embedded asset hash is invalid: {relative_path}")
        installed = REPO_ROOT / relative_path
        if installed.is_file() and digest != _sha256(installed):
            errors.append(f"visual evidence embedded asset hash mismatch: {relative_path}")

    source_inputs = manifest.get("sourceInputs")
    source_by_path: dict[str, Any] = {}
    if not isinstance(source_inputs, list):
        errors.append("visual evidence sourceInputs must be a list")
    else:
        for item in source_inputs:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                errors.append("visual evidence sourceInputs entries must be objects with paths")
                continue
            source_path = item["path"]
            if source_path in source_by_path:
                errors.append(f"visual evidence sourceInputs duplicates {source_path}")
            source_by_path[source_path] = item

    if set(source_by_path) != set(VISUAL_SOURCE_PATHS):
        errors.append("visual evidence sourceInputs must match the canonical source set")
    source_lines: list[str] = []
    for relative_path in VISUAL_SOURCE_PATHS:
        source_path = REPO_ROOT / relative_path
        item = source_by_path.get(relative_path)
        if not source_path.is_file():
            errors.append(f"visual evidence source is missing: {relative_path}")
            continue
        actual = _sha256(source_path)
        if not isinstance(item, dict) or item.get("sha256") != actual:
            errors.append(f"visual evidence source hash mismatch: {relative_path}")
        source_lines.append(f"{relative_path}:{actual}")
    aggregate = hashlib.sha256("\n".join(source_lines).encode("utf-8")).hexdigest()
    if manifest.get("aggregateSourceSha256") != aggregate:
        errors.append("visual evidence aggregateSourceSha256 does not match current sources")

    evidence = manifest.get("evidence")
    evidence_by_id: dict[str, Any] = {}
    if not isinstance(evidence, list):
        errors.append("visual evidence evidence must be a list")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                errors.append("visual evidence entries must be objects with ids")
                continue
            evidence_id = item["id"]
            if evidence_id in evidence_by_id:
                errors.append(f"visual evidence duplicates {evidence_id}")
            evidence_by_id[evidence_id] = item
    if set(evidence_by_id) != set(VISUAL_EVIDENCE_CASES):
        errors.append("visual evidence IDs must match VIS-710-01 through VIS-710-06")

    for evidence_id, expected_case in VISUAL_EVIDENCE_CASES.items():
        item = evidence_by_id.get(evidence_id)
        if not isinstance(item, dict):
            continue
        filename = expected_case["file"]
        if item.get("file") != filename:
            errors.append(f"{evidence_id} must use canonical filename {filename}")
        for field in ("viewport", "containerWidth", "query"):
            if item.get(field) != expected_case[field]:
                errors.append(f"{evidence_id}.{field} does not match the evidence matrix")
        screenshot = VISUAL_EVIDENCE_ROOT / filename
        if not screenshot.is_file():
            errors.append(f"missing visual evidence screenshot: {filename}")
        elif item.get("sha256") != _sha256(screenshot):
            errors.append(f"visual evidence screenshot hash mismatch: {filename}")
        if item.get("elementCrop") is not True:
            errors.append(f"{evidence_id} must declare elementCrop=true")
        checks = item.get("checks")
        if not isinstance(checks, dict):
            errors.append(f"{evidence_id}.checks must be an object")
            continue
        if (
            checks.get("documentOverflow") is not False
            or checks.get("containerOverflow") is not False
            or checks.get("containerOverflowElements") != []
            or checks.get("clippedText") != []
        ):
            errors.append(f"{evidence_id} must prove no document, container, or text overflow")
        exact_checks = {
            "dark": expected_case["dark"],
            "activeFilter": expected_case["filter"],
            "currentStepCodes": expected_case["current"],
            "selectedStepCodes": expected_case["selected"],
            "selectedTaskIds": expected_case["selectedTasks"],
            "detailTitle": expected_case["detailTitle"],
        }
        for field, expected in exact_checks.items():
            if checks.get(field) != expected:
                errors.append(f"{evidence_id}.checks.{field} does not match the evidence matrix")
        if checks.get("forbiddenTextMatches") != []:
            errors.append(f"{evidence_id} contains forbidden non-synthetic text markers")
        if evidence_id == "VIS-710-05":
            if checks.get("retryButtons") != 1 or item.get("recoveryVerified") is not True:
                errors.append("VIS-710-05 must prove exactly one functional retry")
            if checks.get("syntheticMarkers") != {"fixture": False, "noMatterData": False}:
                errors.append("VIS-710-05 must not infer visible markers from embedded scripts")
        else:
            synthetic = checks.get("syntheticMarkers")
            if synthetic != {"fixture": True, "noMatterData": True}:
                errors.append(f"{evidence_id} must prove the synthetic-data markers")
            if checks.get("svgElements", 0) < 1 or checks.get("currentStepCodes") != ["Task_EntwurfAbstimmen"]:
                errors.append(f"{evidence_id} must prove the canonical BPMN current step")
            selection = expected_case["detailTitle"] or "Keine ausgewählte Aufgabe"
            expected_status = (
                "Aktueller Prozessschritt: Entwurf prüfen. Ausgewählte Aufgabe: "
                f"{selection}."
            )
            if checks.get("diagramStatus") != expected_status:
                errors.append(f"{evidence_id} diagramStatus is not selection-consistent")
        if evidence_id == "VIS-710-01" and expected_case["current"] == expected_case["selected"]:
            errors.append("VIS-710-01 must prove distinct Current and Selected steps")
        if evidence_id == "VIS-710-04" and item.get("recoveryVerified") is not True:
            errors.append("VIS-710-04 must prove empty-state recovery")
        if evidence_id == "VIS-710-06":
            if expected_case["viewport"]["width"] <= 760:
                errors.append("VIS-710-06 must prove a narrow container in a wide viewport")
            if checks.get("maximumTextLayoutVerified") is not True:
                errors.append("VIS-710-06 must prove bounded maximum-length text layout")
        elif checks.get("maximumTextLayoutVerified") is not False:
            errors.append(f"{evidence_id} must not claim the maximum-text layout check")
    return errors


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


if __name__ == "__main__":
    raise SystemExit(main())
