from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bpmn_viewer_provisioning import (
    DEFAULT_BPMN_VIEWER_PROVISIONING,
    load_bpmn_viewer_provisioning_config,
    validate_bpmn_viewer_provisioning_config,
)
from .mcp_runtime import load_mcp_contract
from .spfx_bpmn_viewer_skeleton import (
    DEFAULT_SPFX_BPMN_VIEWER_SKELETON,
    SPFX_SKELETON_BLOCKED_MARKERS,
    SPFX_SKELETON_BLOCKED_PATHS,
    load_spfx_bpmn_viewer_skeleton,
    validate_spfx_bpmn_viewer_skeleton,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BPMN_VIEWER_RUNTIME_READINESS = (
    REPO_ROOT / "deploy" / "m365" / "teams-sharepoint" / "nac-bpmn-viewer.runtime-readiness.json"
)
SPFX_PACKAGE_ROOT = REPO_ROOT / "spfx" / "nac-bpmn-viewer"
REQUIRED_SOURCE_ARTIFACTS = {
    "viewer_contract": "workflows/contracts/m365-sharepoint-bpmn-viewer-adapter.contract.json",
    "provisioning_plan": "deploy/m365/teams-sharepoint/nac-bpmn-viewer.provisioning.json",
    "spfx_skeleton": "deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json",
    "package_root": "spfx/nac-bpmn-viewer",
    "render_fixture": "tests/fixtures/m365/spfx-bpmn-viewer/render-contract.fixture.json",
}
REQUIRED_BLOCKED_OPERATIONS = {
    "npm_install",
    "spfx_bundle",
    "spfx_package_solution",
    "create_sppkg",
    "app_catalog_upload",
    "site_app_install",
    "tenant_wide_deploy",
    "live_tenant_apply",
    "live_bpmn_content_read",
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
REQUIRED_METADATA_GATES = {
    "ApprovalStatus=Approved",
    "ViewerEnabled=true",
    "ContainsMatterData=false",
    "BpmnXmlSha256 matches downloaded XML",
    "NacDataClass in Template,Demo,Reference",
}
REQUIRED_EVIDENCE_KEYS = {
    "spfx_packaging_boundary",
    "app_catalog_deploy_gate",
    "graph_bpmn_content_read_gate",
    "guardrails",
}
SPFX_RUNTIME_BLOCKED_SCRIPT_MARKERS = {
    "install",
    "postinstall",
    "build",
    "bundle",
    "package-solution",
    "deploy",
    "serve",
    "upload",
    "app-catalog",
    "app catalog",
}
SPFX_RUNTIME_BLOCKED_MARKERS = {
    "npm " + "install",
    "npm " + "ci",
    "npx " + "gulp",
    "gulp " + "bundle",
    "gulp " + "package-solution",
    "package-solution " + "--ship",
    "deploy-" + "azure-storage",
    "m365 " + "spo",
    "Add-" + "PnPApp",
    "Publish-" + "PnPApp",
    "tenant " + "apply",
    "app" + "catalogurl",
    "Graph" + "ServiceClient",
    "MS" + "GraphClient",
    "MS" + "GraphClientV3",
    "@" + "microsoft/microsoft-graph-client",
    "@" + "microsoft/microsoft-graph-types",
    "@" + "pnp",
    "sp-" + "pnp-js",
    "PnP" + "js",
    "Client" + "Context(",
    "SP." + "ClientContext",
    "/" + "_api",
    "_" + "api/",
    "office365." + "sharepoint",
    "share" + "plum",
    "writesItems" + ": true",
    "executesGraphRequestsNow" + ": true",
    "POST ",
    "PATCH ",
    "PUT ",
    "DELETE ",
    ".post(",
    ".patch(",
    ".put(",
    ".delete(",
    "bpmn-js/lib/" + "Modeler",
    "Model" + "er",
    "save" + "XML",
    "save" + "SVG",
    "start" + "Process",
    "execute" + "Workflow",
}


def load_bpmn_viewer_runtime_readiness(
    path: Path = DEFAULT_BPMN_VIEWER_RUNTIME_READINESS,
) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_bpmn_viewer_runtime_readiness(
    readiness: dict[str, Any],
    *,
    skeleton: dict[str, Any] | None = None,
    provisioning: dict[str, Any] | None = None,
    mcp_contract: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    if readiness.get("schema_version") != "nac.m365-bpmn-viewer-runtime-readiness/v0.1":
        errors.append("SPFx BPMN viewer runtime readiness schema_version is invalid")
    if readiness.get("status") != "offline_runtime_readiness_no_live_deploy":
        errors.append("SPFx BPMN viewer runtime readiness status must be offline_runtime_readiness_no_live_deploy")

    source_artifacts = readiness.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        errors.append("SPFx BPMN viewer runtime readiness source_artifacts must be an object")
    else:
        for key, value in sorted(REQUIRED_SOURCE_ARTIFACTS.items()):
            if source_artifacts.get(key) != value:
                errors.append(f"SPFx BPMN viewer runtime readiness source_artifacts.{key} must be {value}")
            elif not (REPO_ROOT / value).exists() and key != "package_root":
                errors.append(f"SPFx BPMN viewer runtime readiness source_artifacts.{key} target is missing")
        if source_artifacts.get("package_root") == "spfx/nac-bpmn-viewer" and not SPFX_PACKAGE_ROOT.is_dir():
            errors.append("SPFx BPMN viewer runtime readiness package_root is missing")

    skeleton = skeleton or load_spfx_bpmn_viewer_skeleton(DEFAULT_SPFX_BPMN_VIEWER_SKELETON)
    provisioning = provisioning or load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
    mcp_contract = mcp_contract or load_mcp_contract()
    errors.extend(_prefixed("skeleton", validate_spfx_bpmn_viewer_skeleton(skeleton, mcp_contract=mcp_contract)))
    errors.extend(_prefixed("provisioning", validate_bpmn_viewer_provisioning_config(provisioning)))

    errors.extend(_validate_packaging_boundary(readiness.get("spfx_packaging_boundary"), skeleton))
    errors.extend(_validate_app_catalog_gate(readiness.get("app_catalog_deploy_gate")))
    errors.extend(_validate_graph_content_read_gate(readiness.get("graph_bpmn_content_read_gate")))
    errors.extend(_validate_evidence_expectations(readiness.get("evidence_expectations")))

    blocked = set(_strings(readiness.get("blocked_operations")))
    for operation in sorted(REQUIRED_BLOCKED_OPERATIONS - blocked):
        errors.append(f"SPFx BPMN viewer runtime readiness blocked_operations missing {operation}")

    errors.extend(_validate_spfx_source_runtime_boundaries(SPFX_PACKAGE_ROOT))
    return errors


def build_bpmn_viewer_runtime_readiness_result(
    readiness: dict[str, Any],
    *,
    skeleton: dict[str, Any] | None = None,
    provisioning: dict[str, Any] | None = None,
    mcp_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    skeleton = skeleton or load_spfx_bpmn_viewer_skeleton(DEFAULT_SPFX_BPMN_VIEWER_SKELETON)
    provisioning = provisioning or load_bpmn_viewer_provisioning_config(DEFAULT_BPMN_VIEWER_PROVISIONING)
    mcp_contract = mcp_contract or load_mcp_contract()
    errors = validate_bpmn_viewer_runtime_readiness(
        readiness,
        skeleton=skeleton,
        provisioning=provisioning,
        mcp_contract=mcp_contract,
    )
    if errors:
        return {
            "status": "FAILED",
            "errors": errors,
        }

    package_boundary = readiness["spfx_packaging_boundary"]
    deploy_gate = readiness["app_catalog_deploy_gate"]
    content_gate = readiness["graph_bpmn_content_read_gate"]
    return {
        "status": "PASSED",
        "summary": {
            "component": skeleton["spfx"]["component_name"],
            "package_root": package_boundary["package_root"],
            "readiness_gate_count": 3,
            "live_deploy_allowed_now": False,
            "live_content_read_enabled_now": False,
            "app_catalog_upload_allowed_now": False,
        },
        "readiness": {
            "schema_version": readiness["schema_version"],
            "status": readiness["status"],
            "artifact": "deploy/m365/teams-sharepoint/nac-bpmn-viewer.runtime-readiness.json",
            "source_artifacts": readiness["source_artifacts"],
        },
        "readinessGates": [
            {
                "id": "spfx_packaging_boundary",
                "status": "BLOCKED_UNTIL_OWNER_GATE",
                "owner_gate_required": package_boundary["future_owner_gate_required_before_package"],
                "allowed_now": False,
                "future_validation": package_boundary["future_validation_before_package"],
            },
            {
                "id": "app_catalog_deploy_gate",
                "status": "BLOCKED_UNTIL_OWNER_GATE",
                "owner_gate_required": deploy_gate["requires_owner_gate"],
                "allowed_now": False,
                "requires_sharepoint_admin_role": deploy_gate["requires_sharepoint_admin_role"],
            },
            {
                "id": "graph_bpmn_content_read_gate",
                "status": "BLOCKED_UNTIL_OWNER_GATE",
                "owner_gate_required": True,
                "allowed_now": content_gate["live_content_read_enabled_now"],
                "future_endpoint": content_gate["future_endpoint"],
                "required_metadata_gates": content_gate["required_metadata_gates"],
            },
        ],
        "guardrails": {
            "npm_install_allowed_now": False,
            "build_allowed_now": False,
            "package_solution_allowed_now": False,
            "sppkg_included_now": False,
            "app_catalog_upload_allowed_now": False,
            "tenant_wide_deploy_allowed_now": False,
            "site_scoped_install_allowed_now": False,
            "live_tenant_apply_allowed_now": False,
            "live_content_read_enabled_now": False,
            "graph_rest_only": True,
            "graph_sdk_allowed": False,
            "legacy_sharepoint_api_allowed": False,
            "matter_document_content_reads_allowed": False,
            "workflow_execution_allowed": False,
        },
        "evidence": {
            "command": readiness["evidence_expectations"]["command"],
            "output_kind": readiness["evidence_expectations"]["output_kind"],
            "must_include": readiness["evidence_expectations"]["must_include"],
            "must_not_include": readiness["evidence_expectations"]["must_not_include"],
        },
    }


def _validate_packaging_boundary(value: object, skeleton: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["SPFx BPMN viewer runtime readiness spfx_packaging_boundary must be an object"]
    expected_true = {
        "package_json_required",
        "package_solution_json_required",
        "manifest_required",
        "future_owner_gate_required_before_package",
    }
    for flag in sorted(expected_true):
        if value.get(flag) is not True:
            errors.append(f"SPFx BPMN viewer runtime readiness spfx_packaging_boundary.{flag} must be true")
    expected_false = {
        "npm_install_allowed_now",
        "build_allowed_now",
        "bundle_allowed_now",
        "package_solution_allowed_now",
        "sppkg_included_now",
        "lockfile_allowed_now",
        "node_modules_allowed_now",
    }
    for flag in sorted(expected_false):
        if value.get(flag) is not False:
            errors.append(f"SPFx BPMN viewer runtime readiness spfx_packaging_boundary.{flag} must be false")
    if value.get("package_root") != skeleton.get("spfx", {}).get("package_root"):
        errors.append("SPFx BPMN viewer runtime readiness package_root must match skeleton package_root")
    future_validation = set(_strings(value.get("future_validation_before_package")))
    for marker in (
        "npm install in an isolated SPFx package workspace",
        "SPFx bundle validation",
        "SPFx package-solution validation",
        "license and SBOM delta review",
    ):
        if marker not in future_validation:
            errors.append(f"SPFx BPMN viewer runtime readiness future validation missing {marker}")
    return errors


def _validate_app_catalog_gate(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["SPFx BPMN viewer runtime readiness app_catalog_deploy_gate must be an object"]
    expected_false = {
        "app_catalog_upload_allowed_now",
        "tenant_wide_deploy_allowed_now",
        "site_scoped_install_allowed_now",
    }
    for flag in sorted(expected_false):
        if value.get(flag) is not False:
            errors.append(f"SPFx BPMN viewer runtime readiness app_catalog_deploy_gate.{flag} must be false")
    expected_true = {
        "requires_owner_gate",
        "requires_sharepoint_admin_role",
        "requires_app_catalog_site",
        "requires_separate_pr_with_package_artifact",
        "requires_rollback_plan",
        "requires_post_deploy_read_only_smoke",
    }
    for flag in sorted(expected_true):
        if value.get(flag) is not True:
            errors.append(f"SPFx BPMN viewer runtime readiness app_catalog_deploy_gate.{flag} must be true")
    return errors


def _validate_graph_content_read_gate(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["SPFx BPMN viewer runtime readiness graph_bpmn_content_read_gate must be an object"]
    expected = {
        "graph_base_url": "https://graph.microsoft.com/v1.0",
        "future_endpoint": "GET /sites/{site-id}/drives/{drive-id}/items/{item-id}/content",
        "permission_model": "future_owner_gated_sites_selected_read",
        "allowed_content_class": "approved_bpmn_xml_only",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            errors.append(f"SPFx BPMN viewer runtime readiness graph_bpmn_content_read_gate.{key} is invalid")
    if value.get("graph_rest_only") is not True:
        errors.append("SPFx BPMN viewer runtime readiness graph_bpmn_content_read_gate.graph_rest_only must be true")
    for flag in (
        "graph_sdk_allowed",
        "legacy_sharepoint_api_allowed",
        "pnp_allowed",
        "csom_allowed",
        "live_content_read_enabled_now",
    ):
        if value.get(flag) is not False:
            errors.append(f"SPFx BPMN viewer runtime readiness graph_bpmn_content_read_gate.{flag} must be false")
    if set(_strings(value.get("allowed_file_extensions"))) != {".bpmn"}:
        errors.append("SPFx BPMN viewer runtime readiness allowed_file_extensions must be only .bpmn")
    metadata_gates = set(_strings(value.get("required_metadata_gates")))
    for gate in sorted(REQUIRED_METADATA_GATES - metadata_gates):
        errors.append(f"SPFx BPMN viewer runtime readiness metadata gate missing {gate}")
    forbidden = set(_strings(value.get("forbidden_content_classes")))
    for content_class in ("matter_document_content", "mandate_payload", "tokens_or_secrets"):
        if content_class not in forbidden:
            errors.append(f"SPFx BPMN viewer runtime readiness forbidden content missing {content_class}")
    return errors


def _validate_evidence_expectations(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["SPFx BPMN viewer runtime readiness evidence_expectations must be an object"]
    if value.get("command") != "nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json":
        errors.append("SPFx BPMN viewer runtime readiness evidence command is invalid")
    if value.get("output_kind") != "redacted_offline_readiness_json":
        errors.append("SPFx BPMN viewer runtime readiness evidence output_kind is invalid")
    includes = set(_strings(value.get("must_include")))
    for key in sorted(REQUIRED_EVIDENCE_KEYS - includes):
        errors.append(f"SPFx BPMN viewer runtime readiness evidence must_include missing {key}")
    excludes = set(_strings(value.get("must_not_include")))
    for key in ("secrets", "tokens", "raw_matter_document_content", "live_bpmn_xml_content"):
        if key not in excludes:
            errors.append(f"SPFx BPMN viewer runtime readiness evidence must_not_include missing {key}")
    return errors


def _validate_spfx_source_runtime_boundaries(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"SPFx BPMN viewer runtime readiness source root missing: {root.relative_to(REPO_ROOT)}"]
    for blocked in sorted(SPFX_SKELETON_BLOCKED_PATHS):
        if (root / blocked).exists():
            errors.append(f"SPFx BPMN viewer runtime readiness must not include {blocked}")
    package = root / "package.json"
    if package.is_file():
        package_json = json.loads(package.read_text(encoding="utf-8"))
        scripts = package_json.get("scripts", {})
        if not isinstance(scripts, dict) or not scripts:
            errors.append("SPFx BPMN viewer runtime readiness package.json must keep validate-only scripts")
        elif set(scripts) != {"validate:skeleton"}:
            errors.append("SPFx BPMN viewer runtime readiness package.json scripts must only contain validate:skeleton")
        script_items = scripts.items() if isinstance(scripts, dict) else []
        for script_name, script_command in script_items:
            if not isinstance(script_name, str) or not isinstance(script_command, str):
                errors.append("SPFx BPMN viewer runtime readiness package.json scripts must be string commands")
                continue
            lowered = f"{script_name} {script_command}".lower()
            for marker in sorted(SPFX_RUNTIME_BLOCKED_SCRIPT_MARKERS):
                if marker in lowered:
                    errors.append(
                        f"SPFx BPMN viewer runtime readiness package.json script {script_name!r} contains blocked marker {marker!r}"
                    )
        skeleton_flags = package_json.get("nacSkeleton", {})
        for flag in (
            "npmInstallRequiredNow",
            "buildRequiredNow",
            "appCatalogDeployAllowedNow",
            "tenantApplyAllowedNow",
            "executesGraphRequestsNow",
        ):
            if skeleton_flags.get(flag) is not False:
                errors.append(f"SPFx BPMN viewer runtime readiness package.json nacSkeleton.{flag} must be false")
    package_solution = root / "config" / "package-solution.json"
    if package_solution.is_file():
        payload = json.loads(package_solution.read_text(encoding="utf-8"))
        guardrails = payload.get("nacGuardrails", {})
        for flag in ("packageSolutionEnabledNow", "appCatalogDeployAllowedNow", "tenantApplyAllowedNow"):
            if guardrails.get(flag) is not False:
                errors.append(f"SPFx BPMN viewer runtime readiness package-solution nacGuardrails.{flag} must be false")
        if payload.get("solution", {}).get("skipFeatureDeployment") is True:
            errors.append("SPFx BPMN viewer runtime readiness package-solution must not enable tenant-wide deployment")
        web_api_permissions = payload.get("solution", {}).get("webApiPermissionRequests")
        if web_api_permissions:
            errors.append("SPFx BPMN viewer runtime readiness package-solution must not request Web API permissions now")
        zipped = payload.get("paths", {}).get("zippedPackage")
        if isinstance(zipped, str) and (root / zipped).exists():
            errors.append("SPFx BPMN viewer runtime readiness must not include an .sppkg artifact now")
    for sppkg in root.rglob("*.sppkg"):
        errors.append(f"SPFx BPMN viewer runtime readiness must not include package artifact {sppkg.relative_to(REPO_ROOT)}")
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".md", ".ts", ".tsx"}:
            continue
        text = path.read_text(encoding="utf-8")
        for marker in sorted(SPFX_SKELETON_BLOCKED_MARKERS | SPFX_RUNTIME_BLOCKED_MARKERS):
            if marker in text:
                errors.append(
                    f"SPFx BPMN viewer runtime readiness {path.relative_to(REPO_ROOT)} contains blocked marker {marker!r}"
                )
    return errors


def _prefixed(prefix: str, errors: list[str]) -> list[str]:
    return [f"{prefix}: {error}" for error in errors]


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
