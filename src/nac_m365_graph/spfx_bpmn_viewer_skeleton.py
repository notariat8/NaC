from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPFX_BPMN_VIEWER_SKELETON = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-spfx-bpmn-viewer.skeleton.json"
)
DEFAULT_SPFX_BPMN_VIEWER_RENDER_FIXTURE = (
    REPO_ROOT / "tests" / "fixtures" / "m365" / "spfx-bpmn-viewer" / "render-contract.fixture.json"
)
APPROVED_WORKSPACE_ID = "notary_team_01"
SPFX_VERSION = "1.23.2"
PROCESS_SELECTION_FIXTURE_TOOLS = {
    "bpmn_model_get",
    "process_register_list",
    "bpmn_viewer_overlay_get",
}
REQUIRED_RENDER_STATES = {
    "approved_renderable",
    "approval_missing_or_review_required",
    "viewer_disabled",
    "contains_matter_data",
    "invalid_mime_or_hash_missing",
}
REQUIRED_PROCESS_SELECTION_CHECKS = {
    "single_process_register_match",
    "process_status_approved",
    "process_viewer_enabled",
    "overlay_policy_metadata_only",
    "linked_bpmn_model_found",
    "linked_bpmn_model_renderable",
}
REQUIRED_DOM_MARKERS = {
    "component": 'data-nac-component="test-workspace"',
    "synthetic_data": "Synthetische Testdaten",
    "no_matter_data": "Keine Mandatsdaten",
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
    "tenant_wide_deploy",
    "microsoft_graph_permission_request",
    "direct_graph_request",
    "aad_http_client_non_bff_resource",
    "additional_delegated_scope",
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
    ".gitignore",
    ".npmignore",
    ".yo-rc.json",
    "README.md",
    "package.json",
    "package-lock.json",
    "config/config.json",
    "config/package-solution.json",
    "src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.ts",
    "src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.manifest.json",
    "src/webparts/nacBpmnViewer/components/NacBpmnViewer.tsx",
    "src/webparts/nacBpmnViewer/fixtures/sampleBpmn.ts",
    "src/webparts/nacBpmnViewer/fixtures/syntheticWorkspace.ts",
    "src/webparts/nacBpmnViewer/services/NacBffClient.ts",
    "src/webparts/nacBpmnViewer/services/NacBffClient.test.ts",
    "teams/3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21_color.png",
    "teams/3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21_outline.png",
    "tsconfig.json",
}
SPFX_GENERATED_PATHS = {
    "node_modules",
    "dist",
    "lib",
    "lib-commonjs",
    "temp",
    "sharepoint/solution",
    "release",
    "jest-output",
}
SPFX_SKELETON_BLOCKED_PATHS = SPFX_GENERATED_PATHS
SPFX_SKELETON_BLOCKED_MARKERS = {
    "Graph" + "ServiceClient",
    "MS" + "GraphClient",
    "graph.microsoft" + ".com",
    "@" + "microsoft/microsoft-graph-client",
    "@" + "pnp",
    "_" + "api/",
    "/" + "_api",
    "graph" + "beta",
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
    del mcp_contract
    errors: list[str] = []
    if skeleton.get("schema_version") != "nac.m365-spfx-bpmn-viewer-skeleton/v0.3":
        errors.append("SPFx BPMN viewer skeleton schema_version is invalid")
    if skeleton.get("status") != "bff_read_site_scoped_package":
        errors.append("SPFx BPMN viewer skeleton status must be bff_read_site_scoped_package")

    spfx = skeleton.get("spfx")
    if not isinstance(spfx, dict):
        errors.append("SPFx BPMN viewer skeleton spfx must be an object")
    else:
        expected = {
            "framework": "SharePoint Framework",
            "framework_version": SPFX_VERSION,
            "build_tool": "Heft",
            "component_type": "clientSideWebPart",
            "library": "bpmn-js",
            "bpmn_js_import": "bpmn-js/lib/Viewer",
            "bpmn_js_mode": "viewer_only",
            "package_root": "spfx/nac-bpmn-viewer",
            "approved_workspace_id": APPROVED_WORKSPACE_ID,
            "data_source": "nac_bff_redacted_dto",
        }
        for key, value in expected.items():
            if spfx.get(key) != value:
                errors.append(f"SPFx BPMN viewer skeleton spfx.{key} must be {value}")
        for flag in (
            "source_package_included_now",
            "package_lock_required",
            "npm_ci_allowed_now",
            "build_allowed_now",
            "package_solution_enabled_now",
            "reproducible_build_required",
            "site_scoped_package",
            "teams_hosts_enabled",
            "app_catalog_deploy_owner_approved",
            "site_scoped_install_allowed_now",
            "aad_http_client_allowed",
        ):
            if spfx.get(flag) is not True:
                errors.append(f"SPFx BPMN viewer skeleton spfx.{flag} must be true")
        for flag in (
            "modeler_enabled",
            "workflow_execution_allowed",
            "requires_custom_script",
            "loose_html_embedding_allowed",
            "tenant_wide_deploy_allowed_now",
            "graph_permissions_requested",
            "direct_graph_access_allowed",
            "sharepoint_writes_allowed",
            "contains_real_matter_data",
        ):
            if spfx.get(flag) is not False:
                errors.append(f"SPFx BPMN viewer skeleton spfx.{flag} must be false")
        if spfx.get("delegated_api_resource") != "api://funktion8.de/nac-bff":
            errors.append("SPFx BPMN viewer delegated_api_resource must be the NaC BFF")
        if spfx.get("delegated_api_scope") != "Matter.Read":
            errors.append("SPFx BPMN viewer delegated_api_scope must be Matter.Read")
        if spfx.get("bff_endpoint") != "https://func-nac-bff-test-funktion8.azurewebsites.net":
            errors.append("SPFx BPMN viewer bff_endpoint is invalid")
        if spfx.get("package_root") == "spfx/nac-bpmn-viewer":
            errors.extend(_validate_spfx_source_root(REPO_ROOT / spfx["package_root"]))

    deployment = skeleton.get("deployment_scope")
    if not isinstance(deployment, dict):
        errors.append("SPFx BPMN viewer skeleton deployment_scope must be an object")
    else:
        if deployment.get("approved_workspace_id") != APPROVED_WORKSPACE_ID:
            errors.append("SPFx BPMN viewer skeleton deployment scope must be notary_team_01")
        if deployment.get("approval") != "owner_approved":
            errors.append("SPFx BPMN viewer skeleton deployment scope must be owner_approved")
        if deployment.get("site_scoped") is not True:
            errors.append("SPFx BPMN viewer skeleton deployment must be site-scoped")
        if deployment.get("tenant_wide") is not False:
            errors.append("SPFx BPMN viewer skeleton deployment must not be tenant-wide")

    render = skeleton.get("render_contract")
    if not isinstance(render, dict):
        errors.append("SPFx BPMN viewer skeleton render_contract must be an object")
    else:
        if render.get("workspace_id") != APPROVED_WORKSPACE_ID:
            errors.append("SPFx BPMN viewer skeleton render_contract.workspace_id is invalid")
        if render.get("content_source") != "nac_bff_redacted_dto":
            errors.append("SPFx BPMN viewer skeleton render content must come from nac_bff_redacted_dto")
        if render.get("synthetic_data_only") is not True:
            errors.append("SPFx BPMN viewer skeleton render content must be synthetic only")
        if render.get("viewer_only") is not True:
            errors.append("SPFx BPMN viewer skeleton render contract must be viewer-only")
        if render.get("live_tenant_access") is not True:
            errors.append("SPFx BPMN viewer skeleton render_contract.live_tenant_access must be true")
        for flag in ("graph_access", "writes_allowed", "real_matter_data_allowed"):
            if render.get(flag) is not False:
                errors.append(f"SPFx BPMN viewer skeleton render_contract.{flag} must be false")
        dom_markers = render.get("dom_markers")
        if not isinstance(dom_markers, dict):
            errors.append("SPFx BPMN viewer skeleton render_contract.dom_markers must be an object")
        else:
            for key, value in REQUIRED_DOM_MARKERS.items():
                if dom_markers.get(key) != value:
                    errors.append(f"SPFx BPMN viewer skeleton render_contract.dom_markers.{key} must be {value}")
        privacy = render.get("privacy_guards")
        if not isinstance(privacy, dict):
            errors.append("SPFx BPMN viewer skeleton render_contract.privacy_guards must be an object")
        else:
            for flag in (
                "matter_content_present",
                "private_payload_values_present",
                "credential_material_present",
                "raw_graph_paths_present",
            ):
                if privacy.get(flag) is not False:
                    errors.append(f"SPFx BPMN viewer skeleton privacy_guards.{flag} must be false")

    blocked = set(_strings(skeleton.get("blocked_operations")))
    for operation in sorted(REQUIRED_BLOCKED_OPERATIONS - blocked):
        errors.append(f"SPFx BPMN viewer skeleton blocked_operations missing {operation}")

    if render_fixture is not None:
        errors.extend(_validate_render_fixture(render_fixture, skeleton))
    return errors


def _validate_spfx_source_root(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"SPFx BPMN viewer package root missing: {root.relative_to(REPO_ROOT)}"]
    for required in sorted(SPFX_SKELETON_REQUIRED_FILES):
        if not (root / required).is_file():
            errors.append(f"SPFx BPMN viewer package source missing {required}")

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        ignored = {line.strip().strip("/") for line in gitignore.read_text(encoding="utf-8").splitlines()}
        for generated in sorted(SPFX_GENERATED_PATHS):
            ignored_names = {generated, generated.split("/", 1)[0], generated.rsplit("/", 1)[-1]}
            if ignored.isdisjoint(ignored_names):
                errors.append(f"SPFx BPMN viewer .gitignore must ignore {generated}")
    for tracked in _tracked_generated_paths(root):
        errors.append(f"SPFx BPMN viewer generated path must remain untracked: {tracked}")

    package_path = root / "package.json"
    lock_path = root / "package-lock.json"
    if package_path.is_file():
        package = json.loads(package_path.read_text(encoding="utf-8"))
        if package.get("private") is not True:
            errors.append("SPFx BPMN viewer package.json must be private")
        scripts = package.get("scripts")
        if not isinstance(scripts, dict):
            errors.append("SPFx BPMN viewer package.json scripts must be an object")
        else:
            build = str(scripts.get("build", ""))
            if "heft test --clean --production" not in build or "heft package-solution --production" not in build:
                errors.append("SPFx BPMN viewer build must use reproducible Heft production packaging")
        all_dependencies = {
            **(package.get("dependencies") if isinstance(package.get("dependencies"), dict) else {}),
            **(package.get("devDependencies") if isinstance(package.get("devDependencies"), dict) else {}),
        }
        spfx_dependencies = {
            name: version for name, version in all_dependencies.items() if name.startswith("@microsoft/sp")
        }
        if not spfx_dependencies or set(spfx_dependencies.values()) != {SPFX_VERSION}:
            errors.append(f"SPFx BPMN viewer Microsoft SPFx dependencies must be pinned to {SPFX_VERSION}")
        if all_dependencies.get("@rushstack/heft") != "1.2.17":
            errors.append("SPFx BPMN viewer Heft version must be pinned to 1.2.17")
        if all_dependencies.get("bpmn-js") != "17.11.1":
            errors.append("SPFx BPMN viewer bpmn-js must be pinned to 17.11.1")
        for dependency in all_dependencies:
            lowered = dependency.lower()
            if "graph-client" in lowered or "@pnp" in lowered:
                errors.append(f"SPFx BPMN viewer dependency {dependency} is forbidden")

        if lock_path.is_file():
            lock = json.loads(lock_path.read_text(encoding="utf-8"))
            if lock.get("lockfileVersion") != 3 or lock.get("requires") is not True:
                errors.append("SPFx BPMN viewer package-lock.json must use npm lockfileVersion 3")
            locked_root = lock.get("packages", {}).get("", {})
            for key in ("name", "version"):
                if locked_root.get(key) != package.get(key):
                    errors.append(f"SPFx BPMN viewer package-lock root {key} must match package.json")
            for key in ("dependencies", "devDependencies", "engines"):
                if locked_root.get(key) != package.get(key):
                    errors.append(f"SPFx BPMN viewer package-lock root {key} must match package.json")

    package_solution = root / "config" / "package-solution.json"
    if package_solution.is_file():
        payload = json.loads(package_solution.read_text(encoding="utf-8"))
        solution = payload.get("solution", {})
        if solution.get("skipFeatureDeployment") is not False:
            errors.append("SPFx BPMN viewer package must be site-scoped")
        if solution.get("webApiPermissionRequests") != [{"resource": "NaC M365 BFF", "scope": "Matter.Read"}]:
            errors.append("SPFx BPMN viewer package must request only NaC M365 BFF Matter.Read")
        if payload.get("paths", {}).get("zippedPackage") != "solution/nac-bpmn-viewer.sppkg":
            errors.append("SPFx BPMN viewer package-solution output path is invalid")

    manifest = root / "src" / "webparts" / "nacBpmnViewer" / "NacBpmnViewerWebPart.manifest.json"
    if manifest.is_file():
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        hosts = set(_strings(payload.get("supportedHosts")))
        if not {"SharePointWebPart", "TeamsTab"}.issubset(hosts):
            errors.append("SPFx BPMN viewer manifest must support SharePointWebPart and TeamsTab")
        if payload.get("requiresCustomScript") is not False:
            errors.append("SPFx BPMN viewer manifest must not require custom script")
        entries = _as_list(payload.get("preconfiguredEntries"))
        workspace = entries[0].get("properties", {}).get("workspaceId") if entries and isinstance(entries[0], dict) else None
        if workspace != APPROVED_WORKSPACE_ID:
            errors.append("SPFx BPMN viewer manifest workspaceId must be notary_team_01")

    for source_path in _iter_spfx_source_files(root):
        source_text = source_path.read_text(encoding="utf-8")
        for marker in sorted(SPFX_SKELETON_BLOCKED_MARKERS):
            if marker in source_text:
                rel = source_path.relative_to(REPO_ROOT)
                errors.append(f"SPFx BPMN viewer {rel} contains blocked marker {marker!r}")

    service = root / "src" / "webparts" / "nacBpmnViewer" / "services" / "NacBffClient.ts"
    if service.is_file():
        service_text = service.read_text(encoding="utf-8")
        for required in (
            "AadHttpClientFactory",
            "api://funktion8.de/nac-bff",
            "https://func-nac-bff-test-funktion8.azurewebsites.net",
            "Matter.Read",
            "NAC_BFF_WORKSPACE_ID = 'notary_team_01'",
            "NAC_BFF_MATTER_ID = 'NAC-SYN-MATTER-001'",
            "NAC_BFF_PURPOSE = 'view_synthetic_matter_workspace'",
            "MAX_RESPONSE_BYTES",
            "isWorkspace",
            "hasExactKeys",
            "verifyBpmnAsset",
            "crypto.subtle.digest",
        ):
            if required not in service_text:
                errors.append(f"SPFx BPMN viewer BFF client missing {required!r}")
        for blocked in ("graph.microsoft.com", "MSGraphClient", "@microsoft/microsoft-graph-client"):
            if blocked in service_text:
                errors.append(f"SPFx BPMN viewer BFF client contains blocked direct Graph marker {blocked!r}")

    service_test = root / "src" / "webparts" / "nacBpmnViewer" / "services" / "NacBffClient.test.ts"
    if service_test.is_file():
        test_text = service_test.read_text(encoding="utf-8")
        for required in (
            "parseWorkspaceResponse",
            "verifyBpmnAsset",
            "rejects extra %s fields",
            "cryptographically binds packaged BPMN XML",
        ):
            if required not in test_text:
                errors.append(f"SPFx BPMN viewer BFF client test missing {required!r}")

    component = root / "src" / "webparts" / "nacBpmnViewer" / "components" / "NacBpmnViewer.tsx"
    if component.is_file():
        source_text = component.read_text(encoding="utf-8")
        for required in (
            "bpmn-js/lib/Viewer",
            "syntheticWorkspaceFixture",
            "loadWorkspace",
            "verifyBpmnAsset",
            *REQUIRED_DOM_MARKERS.values(),
        ):
            if required not in source_text:
                errors.append(f"SPFx BPMN viewer component missing UI contract marker {required!r}")
        for blocked in ("Model" + "er", "save" + "XML", "start" + "Process", "execute" + "Workflow"):
            if blocked in source_text:
                errors.append(f"SPFx BPMN viewer component contains blocked viewer marker {blocked!r}")

    fixture = root / "src" / "webparts" / "nacBpmnViewer" / "fixtures" / "syntheticWorkspace.ts"
    if fixture.is_file():
        fixture_text = fixture.read_text(encoding="utf-8")
        for required in (
            "workspaceId: 'notary_team_01'",
            "containsMatterData: false",
            "source: 'package_bpmn_fixture'",
            "bpmnXml: sampleApprovedBpmnXml",
        ):
            if required not in fixture_text:
                errors.append(f"SPFx BPMN viewer synthetic fixture missing {required!r}")
    return errors


def _iter_spfx_source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for current, directories, names in os.walk(root):
        current_path = Path(current)
        kept_directories: list[str] = []
        for directory in directories:
            relative = (current_path / directory).relative_to(root).as_posix()
            if any(
                relative == generated or relative.startswith(f"{generated}/")
                for generated in SPFX_GENERATED_PATHS
            ):
                continue
            kept_directories.append(directory)
        directories[:] = kept_directories

        for name in names:
            path = current_path / name
            if name == "package-lock.json":
                continue
            if path.suffix.lower() in {".json", ".md", ".ts", ".tsx"}:
                files.append(path)
    return files

def _tracked_generated_paths(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", str(root.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ["git-ls-files-check-failed"]
    tracked: list[str] = []
    package_prefix = root.relative_to(REPO_ROOT).as_posix()
    for item in result.stdout.splitlines():
        relative = item.removeprefix(f"{package_prefix}/")
        if any(relative == generated or relative.startswith(f"{generated}/") for generated in SPFX_GENERATED_PATHS):
            tracked.append(item)
    return tracked


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


def evaluate_spfx_bpmn_viewer_process_selection(
    process_rows: list[dict[str, Any]],
    bpmn_models: list[dict[str, Any]],
    *,
    workspace_id: str,
    process_id: str | None = None,
    process_key: str | None = None,
    bpmn_model_id: str | None = None,
) -> dict[str, Any]:
    candidates = [
        row
        for row in process_rows
        if _process_row_matches(
            row,
            workspace_id=workspace_id,
            process_id=process_id,
            process_key=process_key,
            bpmn_model_id=bpmn_model_id,
        )
    ]
    checks = _process_selection_base_checks(candidates)
    if len(candidates) != 1:
        return _process_selection_blocked(
            "ambiguous_or_missing_process_register_match",
            checks,
            match_count=len(candidates),
        )

    selected = candidates[0]
    checks.extend(_process_selection_policy_checks(selected))
    model = _find_bpmn_model(bpmn_models, str(_field(selected, "nacBpmnModelId", "NacBpmnModelId") or ""))
    checks.append(
        {
            "id": "linked_bpmn_model_found",
            "passed": model is not None,
        }
    )
    if model is None:
        return _process_selection_blocked("linked_bpmn_model_missing", checks, match_count=1)

    render_decision = evaluate_spfx_bpmn_viewer_render_case(model)
    checks.append(
        {
            "id": "linked_bpmn_model_renderable",
            "passed": render_decision.get("renderAllowed") is True,
            "renderState": render_decision.get("renderState"),
        }
    )
    status = "PASSED" if all(bool(check.get("passed")) for check in checks) else "BLOCKED"
    return {
        "status": status,
        "selectionState": "approved_process_model_selected" if status == "PASSED" else "selection_policy_blocked",
        "summary": {
            "workspaceId": workspace_id,
            "matchCount": 1,
            "selectedProcessId": _field(selected, "nacProcessId", "NacProcessId"),
            "selectedProcessKey": _field(selected, "processKey", "ProcessKey"),
            "selectedBpmnModelId": _field(selected, "nacBpmnModelId", "NacBpmnModelId"),
            "renderState": render_decision.get("renderState"),
            "executesGraphRequestsNow": False,
            "readsSharePointFileContentNow": False,
            "appCatalogDeployAllowedNow": False,
        },
        "selectedProcess": _redact_selected_process(selected, model, render_decision),
        "checks": checks,
        "guardrails": _process_selection_guardrails(),
    }


def build_spfx_bpmn_viewer_process_selection_result(
    skeleton: dict[str, Any],
    *,
    render_fixture: dict[str, Any] | None = None,
    mcp_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del mcp_contract
    render_fixture = render_fixture or load_spfx_bpmn_viewer_render_fixture()
    validation_errors = validate_spfx_bpmn_viewer_skeleton(
        skeleton,
        render_fixture=render_fixture,
    )
    selection_errors = _validate_process_selection_fixture(render_fixture)
    errors = validation_errors + selection_errors
    if errors:
        return {"status": "FAILED", "errors": errors}

    props = render_fixture["component_props"]
    process_rows = [
        row
        for row in render_fixture["process_register_rows"]
        if isinstance(row, dict)
    ]
    bpmn_models = [
        model
        for model in render_fixture["bpmn_models"]
        if isinstance(model, dict)
    ]
    result = evaluate_spfx_bpmn_viewer_process_selection(
        process_rows,
        bpmn_models,
        workspace_id=str(props["workspaceId"]),
        process_id=str(props.get("processId", "")) or None,
        bpmn_model_id=str(props.get("bpmnModelId", "")) or None,
    )
    result["contract"] = {
        "schema_version": "nac.m365-spfx-bpmn-viewer-process-selection/v0.1",
        "status": "synthetic_fixture_selection_no_live_read",
        "fixture": "tests/fixtures/m365/spfx-bpmn-viewer/render-contract.fixture.json",
        "dataSource": "package_fixture",
        "requestPlanTools": [],
        "requiredChecks": sorted(REQUIRED_PROCESS_SELECTION_CHECKS),
    }
    return result


def build_spfx_bpmn_viewer_skeleton_result(
    skeleton: dict[str, Any],
    *,
    render_fixture: dict[str, Any] | None = None,
    mcp_contract: dict[str, Any] | None = None,
    provisioned_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del mcp_contract, provisioned_state
    render_fixture = render_fixture or load_spfx_bpmn_viewer_render_fixture()
    errors = validate_spfx_bpmn_viewer_skeleton(skeleton, render_fixture=render_fixture)
    if errors:
        return {"status": "FAILED", "errors": errors}

    render_case_results = _build_render_case_results(render_fixture)
    return {
        "status": "PASSED",
        "summary": {
            "component": skeleton["spfx"]["component_name"],
            "spfx_component_type": skeleton["spfx"]["component_type"],
            "spfx_version": skeleton["spfx"]["framework_version"],
            "build_tool": skeleton["spfx"]["build_tool"],
            "bpmn_js_mode": skeleton["spfx"]["bpmn_js_mode"],
            "data_source": skeleton["spfx"]["data_source"],
            "approved_workspace_id": skeleton["spfx"]["approved_workspace_id"],
            "package_solution_enabled_now": True,
            "app_catalog_deploy_owner_approved": True,
            "site_scoped_install_allowed_now": True,
            "tenant_wide_deploy_allowed_now": False,
            "executes_graph_requests_now": False,
            "request_plan_count": 1,
            "executes_bff_requests_now": True,
        },
        "skeleton": {
            "schema_version": skeleton["schema_version"],
            "status": skeleton["status"],
            "artifact": "deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json",
            "fixture": skeleton["test_fixtures"]["render_contract"],
        },
        "renderContract": {
            "workspaceId": skeleton["render_contract"]["workspace_id"],
            "componentProps": _redact_component_props(render_fixture["component_props"]),
            "request_plan_count": 1,
            "liveTenantAccess": True,
            "appCatalogDeployOwnerApproved": True,
            "domMarkers": skeleton["render_contract"]["dom_markers"],
            "privacyGuards": skeleton["render_contract"]["privacy_guards"],
            "expectedRenderState": render_fixture["expected_render_state"],
            "cases": render_case_results,
        },
        "requestPlans": [
            {
                "resource": "api://funktion8.de/nac-bff",
                "scope": "Matter.Read",
                "method": "GET",
                "endpoint": "https://func-nac-bff-test-funktion8.azurewebsites.net",
            }
        ],
        "guardrails": {
            "package_lock_required": True,
            "npm_ci_allowed_now": True,
            "build_allowed_now": True,
            "package_solution_enabled_now": True,
            "app_catalog_deploy_owner_approved": True,
            "site_scoped_install_allowed_now": True,
            "approved_workspace_only": True,
            "tenant_wide_deploy_allowed_now": False,
            "executes_graph_requests_now": False,
            "graph_permissions_requested": False,
            "aad_http_client_allowed": True,
            "delegated_api_resource": "api://funktion8.de/nac-bff",
            "delegated_api_scope": "Matter.Read",
            "legacy_sharepoint_api_allowed": False,
            "graph_sdk_allowed": False,
            "matter_document_content_reads_allowed": False,
            "sharepoint_writes_allowed": False,
            "workflow_execution_allowed": False,
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
        if props.get("workspaceId") != APPROVED_WORKSPACE_ID:
            errors.append("SPFx BPMN viewer render fixture workspaceId must be notary_team_01")
    render_contract = fixture.get("render_contract")
    if not isinstance(render_contract, dict):
        errors.append("SPFx BPMN viewer render fixture render_contract must be an object")
    else:
        if render_contract.get("liveTenantAccess") is not False:
            errors.append("SPFx BPMN viewer render fixture render_contract.liveTenantAccess must be false")
        if render_contract.get("appCatalogDeploy") is not False:
            errors.append("SPFx BPMN viewer render fixture render_contract.appCatalogDeploy must be false")
        if render_contract.get("request_plan_count") != len(PROCESS_SELECTION_FIXTURE_TOOLS):
            errors.append("SPFx BPMN viewer render fixture request_plan_count must be 3")
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
    if expected_tools != PROCESS_SELECTION_FIXTURE_TOOLS:
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


def _validate_process_selection_fixture(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rows = _as_list(fixture.get("process_register_rows"))
    models = _as_list(fixture.get("bpmn_models"))
    if not rows:
        errors.append("SPFx BPMN viewer process selection fixture requires process_register_rows")
    if not models:
        errors.append("SPFx BPMN viewer process selection fixture requires bpmn_models")
    props = fixture.get("component_props")
    if not isinstance(props, dict):
        return errors
    result = evaluate_spfx_bpmn_viewer_process_selection(
        [row for row in rows if isinstance(row, dict)],
        [model for model in models if isinstance(model, dict)],
        workspace_id=str(props.get("workspaceId", "")),
        process_id=str(props.get("processId", "")) or None,
        bpmn_model_id=str(props.get("bpmnModelId", "")) or None,
    )
    if result.get("status") != "PASSED":
        errors.append("SPFx BPMN viewer process selection fixture must select one approved renderable process")
    checks = {check.get("id") for check in _as_list(result.get("checks")) if isinstance(check, dict)}
    for missing in sorted(REQUIRED_PROCESS_SELECTION_CHECKS - checks):
        errors.append(f"SPFx BPMN viewer process selection fixture missing check {missing}")
    return errors


def _process_row_matches(
    row: dict[str, Any],
    *,
    workspace_id: str,
    process_id: str | None,
    process_key: str | None,
    bpmn_model_id: str | None,
) -> bool:
    row_workspace = _field(row, "workspaceId", "WorkspaceId")
    if row_workspace and row_workspace != workspace_id:
        return False
    if process_id and _field(row, "nacProcessId", "NacProcessId") != process_id:
        return False
    if process_key and _field(row, "processKey", "ProcessKey") != process_key:
        return False
    if bpmn_model_id and _field(row, "nacBpmnModelId", "NacBpmnModelId") != bpmn_model_id:
        return False
    return True


def _process_selection_base_checks(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": "single_process_register_match",
            "passed": len(candidates) == 1,
            "matchCount": len(candidates),
        }
    ]


def _process_selection_policy_checks(row: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": "process_status_approved",
            "passed": _field(row, "processStatus", "ProcessStatus") == "Approved",
        },
        {
            "id": "process_viewer_enabled",
            "passed": _field(row, "viewerEnabled", "ViewerEnabled") is True,
        },
        {
            "id": "overlay_policy_metadata_only",
            "passed": _field(row, "overlayPolicy", "OverlayPolicy") == "MetadataOnly",
        },
    ]


def _find_bpmn_model(models: list[dict[str, Any]], model_id: str) -> dict[str, Any] | None:
    for model in models:
        if _field(model, "nacBpmnModelId", "NacBpmnModelId") == model_id:
            return model
    return None


def _process_selection_blocked(reason: str, checks: list[dict[str, Any]], *, match_count: int) -> dict[str, Any]:
    return {
        "status": "BLOCKED",
        "selectionState": reason,
        "summary": {
            "matchCount": match_count,
            "executesGraphRequestsNow": False,
            "readsSharePointFileContentNow": False,
            "appCatalogDeployAllowedNow": False,
        },
        "selectedProcess": None,
        "checks": checks,
        "guardrails": _process_selection_guardrails(),
    }


def _redact_selected_process(
    process: dict[str, Any],
    model: dict[str, Any],
    render_decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "nacProcessId": _field(process, "nacProcessId", "NacProcessId"),
        "processKey": _field(process, "processKey", "ProcessKey"),
        "processName": _field(process, "processName", "ProcessName"),
        "processStatus": _field(process, "processStatus", "ProcessStatus"),
        "nacBpmnModelId": _field(process, "nacBpmnModelId", "NacBpmnModelId"),
        "nacBpmnVersion": _field(process, "nacBpmnVersion", "NacBpmnVersion"),
        "bpmnGitPath": _field(process, "bpmnGitPath", "BpmnGitPath"),
        "bpmnContentMode": _field(process, "bpmnContentMode", "BpmnContentMode"),
        "overlayPolicy": _field(process, "overlayPolicy", "OverlayPolicy"),
        "bpmnDriveItemIdPresent": bool(_field(model, "bpmnDriveItemId", "BpmnDriveItemId")),
        "bpmnXmlSha256Present": bool(_field(model, "bpmnXmlSha256", "BpmnXmlSha256")),
        "renderState": render_decision.get("renderState"),
        "metadataOverlay": render_decision.get("metadataOverlay"),
    }


def _process_selection_guardrails() -> dict[str, bool]:
    return {
        "metadataOnly": True,
        "executesGraphRequestsNow": False,
        "readsSharePointFileContentNow": False,
        "returnsMatterDocumentContent": False,
        "writesBpmnXml": False,
        "startsWorkflow": False,
        "appCatalogDeployAllowedNow": False,
    }


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


def _field(value: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in value:
            return value[name]
    return None
