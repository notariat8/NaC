from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .spfx_bpmn_viewer_skeleton import (
    APPROVED_WORKSPACE_ID,
    DEFAULT_SPFX_BPMN_VIEWER_SKELETON,
    SPFX_VERSION,
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
    "spfx_skeleton": "deploy/m365/teams-sharepoint/nac-spfx-bpmn-viewer.skeleton.json",
    "package_root": "spfx/nac-bpmn-viewer",
    "package_json": "spfx/nac-bpmn-viewer/package.json",
    "package_lock": "spfx/nac-bpmn-viewer/package-lock.json",
    "package_solution": "spfx/nac-bpmn-viewer/config/package-solution.json",
    "manifest": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/NacBpmnViewerWebPart.manifest.json",
    "synthetic_fixture": "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/fixtures/syntheticWorkspace.ts",
}
REQUIRED_BLOCKED_OPERATIONS = {
    "tenant_wide_deploy",
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
    "read_matter_document_content",
    "read_matter_payload",
    "store_tokens_or_secrets",
    "store_real_matter_data",
}
REQUIRED_EVIDENCE_KEYS = {
    "spfx_packaging_boundary",
    "app_catalog_deployment",
    "synthetic_data_boundary",
    "guardrails",
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
    del provisioning, mcp_contract
    errors: list[str] = []
    if readiness.get("schema_version") != "nac.m365-bpmn-viewer-runtime-readiness/v0.3":
        errors.append("SPFx BPMN viewer runtime readiness schema_version is invalid")
    if readiness.get("status") != "bff_read_site_scoped_runtime_ready":
        errors.append("SPFx BPMN viewer runtime readiness status must be bff_read_site_scoped_runtime_ready")

    source_artifacts = readiness.get("source_artifacts")
    if not isinstance(source_artifacts, dict):
        errors.append("SPFx BPMN viewer runtime readiness source_artifacts must be an object")
    else:
        for key, value in sorted(REQUIRED_SOURCE_ARTIFACTS.items()):
            if source_artifacts.get(key) != value:
                errors.append(f"SPFx BPMN viewer runtime readiness source_artifacts.{key} must be {value}")
            elif not (REPO_ROOT / value).exists():
                errors.append(f"SPFx BPMN viewer runtime readiness source_artifacts.{key} target is missing")

    skeleton = skeleton or load_spfx_bpmn_viewer_skeleton(DEFAULT_SPFX_BPMN_VIEWER_SKELETON)
    errors.extend(_prefixed("skeleton", validate_spfx_bpmn_viewer_skeleton(skeleton)))
    errors.extend(_validate_packaging_boundary(readiness.get("spfx_packaging_boundary"), skeleton))
    errors.extend(_validate_app_catalog_deployment(readiness.get("app_catalog_deployment")))
    errors.extend(_validate_synthetic_data_boundary(readiness.get("synthetic_data_boundary")))
    errors.extend(_validate_evidence_expectations(readiness.get("evidence_expectations")))

    blocked = set(_strings(readiness.get("blocked_operations")))
    for operation in sorted(REQUIRED_BLOCKED_OPERATIONS - blocked):
        errors.append(f"SPFx BPMN viewer runtime readiness blocked_operations missing {operation}")
    return errors


def build_bpmn_viewer_runtime_readiness_result(
    readiness: dict[str, Any],
    *,
    skeleton: dict[str, Any] | None = None,
    provisioning: dict[str, Any] | None = None,
    mcp_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    del provisioning, mcp_contract
    skeleton = skeleton or load_spfx_bpmn_viewer_skeleton(DEFAULT_SPFX_BPMN_VIEWER_SKELETON)
    errors = validate_bpmn_viewer_runtime_readiness(readiness, skeleton=skeleton)
    if errors:
        return {"status": "FAILED", "errors": errors}

    packaging = readiness["spfx_packaging_boundary"]
    deployment = readiness["app_catalog_deployment"]
    data_boundary = readiness["synthetic_data_boundary"]
    return {
        "status": "PASSED",
        "summary": {
            "component": skeleton["spfx"]["component_name"],
            "package_root": packaging["package_root"],
            "readiness_gate_count": 3,
            "package_build_allowed_now": True,
            "package_solution_allowed_now": True,
            "app_catalog_deploy_owner_approved": True,
            "site_scoped_install_allowed_now": True,
            "approved_workspace_id": APPROVED_WORKSPACE_ID,
            "tenant_wide_deploy_allowed_now": False,
            "graph_access_allowed": False,
            "bff_read_allowed": True,
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
                "status": "READY",
                "allowed_now": True,
                "spfx_version": packaging["spfx_version"],
                "build_tool": packaging["build_tool"],
                "reproducible_commands": packaging["reproducible_commands"],
            },
            {
                "id": "app_catalog_deployment",
                "status": "OWNER_APPROVED",
                "allowed_now": True,
                "approved_workspace_id": deployment["approved_workspace_id"],
                "site_scoped": deployment["site_scoped"],
                "tenant_wide": deployment["tenant_wide"],
            },
            {
                "id": "synthetic_data_boundary",
                "status": "ENFORCED",
                "allowed_now": True,
                "source": data_boundary["source"],
                "graph_access_allowed": data_boundary["graph_access_allowed"],
                "writes_allowed": data_boundary["writes_allowed"],
            },
        ],
        "guardrails": {
            "package_lock_required": True,
            "npm_ci_allowed_now": True,
            "build_allowed_now": True,
            "package_solution_allowed_now": True,
            "generated_outputs_must_remain_ignored_and_untracked": True,
            "app_catalog_deploy_owner_approved": True,
            "site_scoped_install_allowed_now": True,
            "approved_workspace_only": True,
            "tenant_wide_deploy_allowed_now": False,
            "graph_permissions_requested": False,
            "direct_graph_access_allowed": False,
            "ms_graph_client_allowed": False,
            "aad_http_client_allowed": True,
            "delegated_api_resource": "api://funktion8.de/nac-bff",
            "delegated_scope": "Matter.Read",
            "graph_sdk_allowed": False,
            "legacy_sharepoint_api_allowed": False,
            "matter_document_content_reads_allowed": False,
            "sharepoint_writes_allowed": False,
            "workflow_execution_allowed": False,
            "real_matter_data_allowed": False,
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
    expected = {
        "package_root": skeleton.get("spfx", {}).get("package_root"),
        "spfx_version": SPFX_VERSION,
        "build_tool": "Heft",
        "lockfile": "package-lock.json",
        "lockfile_version": 3,
        "package_output": "sharepoint/solution/nac-bpmn-viewer.sppkg",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            errors.append(f"SPFx BPMN viewer runtime readiness spfx_packaging_boundary.{key} is invalid")
    for flag in (
        "package_json_required",
        "package_lock_required",
        "package_solution_json_required",
        "manifest_required",
        "npm_ci_allowed_now",
        "build_allowed_now",
        "bundle_allowed_now",
        "package_solution_allowed_now",
        "reproducible_build_required",
        "generated_outputs_ignored",
        "generated_outputs_untracked",
        "generated_outputs_excluded_from_source_scans",
    ):
        if value.get(flag) is not True:
            errors.append(f"SPFx BPMN viewer runtime readiness spfx_packaging_boundary.{flag} must be true")
    commands = value.get("reproducible_commands")
    if commands != ["npm ci", "npm run build"]:
        errors.append("SPFx BPMN viewer reproducible commands must be npm ci and npm run build")
    ignored = set(_strings(value.get("ignored_generated_paths")))
    for item in ("node_modules", "lib", "dist", "temp", "sharepoint/solution"):
        if item not in ignored:
            errors.append(f"SPFx BPMN viewer ignored_generated_paths missing {item}")
    return errors


def _validate_app_catalog_deployment(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["SPFx BPMN viewer runtime readiness app_catalog_deployment must be an object"]
    expected = {
        "approval": "owner_approved",
        "approved_workspace_id": APPROVED_WORKSPACE_ID,
        "deployment_scope": "site_scoped",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            errors.append(f"SPFx BPMN viewer runtime readiness app_catalog_deployment.{key} must be {expected_value}")
    for flag in (
        "app_catalog_upload_allowed_now",
        "site_scoped_install_allowed_now",
        "requires_sharepoint_admin_role",
        "requires_app_catalog_site",
        "requires_rollback_plan",
        "requires_post_deploy_read_only_smoke",
    ):
        if value.get(flag) is not True:
            errors.append(f"SPFx BPMN viewer runtime readiness app_catalog_deployment.{flag} must be true")
    if value.get("site_scoped") is not True:
        errors.append("SPFx BPMN viewer runtime readiness app_catalog_deployment.site_scoped must be true")
    if value.get("tenant_wide") is not False:
        errors.append("SPFx BPMN viewer runtime readiness app_catalog_deployment.tenant_wide must be false")
    return errors


def _validate_synthetic_data_boundary(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["SPFx BPMN viewer runtime readiness synthetic_data_boundary must be an object"]
    expected = {
        "source": "nac_bff_redacted_dto",
        "workspace_id": APPROVED_WORKSPACE_ID,
        "allowed_content_class": "synthetic_notarial_test_data_only",
    }
    for key, expected_value in expected.items():
        if value.get(key) != expected_value:
            errors.append(f"SPFx BPMN viewer runtime readiness synthetic_data_boundary.{key} must be {expected_value}")
    if value.get("viewer_only") is not True:
        errors.append("SPFx BPMN viewer runtime readiness synthetic_data_boundary.viewer_only must be true")
    for flag in (
        "graph_permission_requested",
        "graph_access_allowed",
        "ms_graph_client_allowed",
        "graph_sdk_allowed",
        "legacy_sharepoint_api_allowed",
        "pnp_allowed",
        "writes_allowed",
        "real_matter_data_allowed",
    ):
        if value.get(flag) is not False:
            errors.append(f"SPFx BPMN viewer runtime readiness synthetic_data_boundary.{flag} must be false")
    if value.get("aad_http_client_allowed") is not True:
        errors.append("SPFx BPMN viewer runtime readiness synthetic_data_boundary.aad_http_client_allowed must be true")
    if value.get("delegated_api_resource") != "api://funktion8.de/nac-bff":
        errors.append("SPFx BPMN viewer runtime readiness delegated_api_resource is invalid")
    if value.get("delegated_scope") != "Matter.Read":
        errors.append("SPFx BPMN viewer runtime readiness delegated_scope must be Matter.Read")
    if value.get("bff_endpoint") != "https://func-nac-bff-test-funktion8.azurewebsites.net":
        errors.append("SPFx BPMN viewer runtime readiness bff_endpoint is invalid")
    forbidden = set(_strings(value.get("forbidden_content_classes")))
    for item in ("matter_document_content", "mandate_payload", "credentials", "tokens_or_secrets"):
        if item not in forbidden:
            errors.append(f"SPFx BPMN viewer synthetic data boundary forbidden content missing {item}")
    return errors


def _validate_evidence_expectations(value: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return ["SPFx BPMN viewer runtime readiness evidence_expectations must be an object"]
    if value.get("command") != "nac m365 teams-sharepoint bpmn-viewer-runtime-readiness --format json":
        errors.append("SPFx BPMN viewer runtime readiness evidence command is invalid")
    if value.get("output_kind") != "redacted_bff_read_site_scoped_readiness_json":
        errors.append("SPFx BPMN viewer runtime readiness evidence output_kind is invalid")
    includes = set(_strings(value.get("must_include")))
    for key in sorted(REQUIRED_EVIDENCE_KEYS - includes):
        errors.append(f"SPFx BPMN viewer runtime readiness evidence must_include missing {key}")
    excludes = set(_strings(value.get("must_not_include")))
    for key in ("secrets", "tokens", "raw_matter_document_content", "real_matter_data", "graph_response"):
        if key not in excludes:
            errors.append(f"SPFx BPMN viewer runtime readiness evidence must_not_include missing {key}")
    return errors


def _prefixed(prefix: str, errors: list[str]) -> list[str]:
    return [f"{prefix}: {error}" for error in errors]


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []
