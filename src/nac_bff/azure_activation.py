from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from nac_bff.azure_readiness import build_azure_bff_readiness


SCHEMA_VERSION = "nac.m365-azure-bff-activation-plan/v1"
CONTRACT_ID = "m365.azure_bff_activation_plan"
COMMAND = "nac m365 teams-sharepoint bff-azure-activation-plan --format json"

SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
LOCATION = "germanywestcentral"
RESOURCE_GROUP = "rg-nac-bff-test"
FUNCTION_APP = "func-nac-bff-test-funktion8"
API_APP_DISPLAY_NAME = "NaC M365 BFF"
API_APP_URI = "api://funktion8.de/nac-bff"
DELEGATED_SCOPE = "Matter.Read"
WORKSPACE_ID = "notary_team_01"
MATTER_ID = "NAC-SYN-MATTER-001"
SITE_ID = (
    "funktion8.sharepoint.com,31324d31-3074-4f1c-ba45-3b3fd5f5ce97,"
    "56fc9349-e123-4252-ae2a-05d5d61c9b38"
)
API_CLIENT_ID_BINDING = {
    "resolution": "unique_by_app_id_uri",
    "source": "entra_application.appId",
    "app_id_uri": API_APP_URI,
    "bicep_parameter": "bffApiAudience",
    "must_be_uuid": True,
    "must_equal_token_audience": True,
    "bind_before_azure_deploy": True,
    "evidence_name": "entra_api_client_id_binding_redacted",
}

_SPFX_ROOT = "spfx/nac-bpmn-viewer"
_SPFX_GENERATED_DIRECTORIES = {
    "dist",
    "jest-output",
    "lib",
    "lib-commonjs",
    "node_modules",
    "release",
    "sharepoint",
    "temp",
}

_ARTIFACT_PATHS = (
    "workflows/contracts/m365-azure-bff-activation-plan.contract.json",
    "deploy/runtime/azure/nac-bff/infra/main.bicep",
    "deploy/runtime/azure/nac-bff/infra/compiled/main.json",
    "deploy/runtime/azure/nac-bff/build_package.py",
    "deploy/runtime/azure/nac-bff/requirements.txt",
    "spfx/nac-bpmn-viewer/config/package-solution.json",
    "spfx/nac-bpmn-viewer/package-lock.json",
    "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/services/NacBffClient.ts",
    "spfx/nac-bpmn-viewer/src/webparts/nacBpmnViewer/fixtures/syntheticWorkspace.ts",
)


def build_azure_bff_activation_plan(repo_root: Path) -> dict[str, Any]:
    root = repo_root.expanduser().resolve()
    readiness = build_azure_bff_readiness(root)
    artifacts, missing = _artifact_bindings(root)
    package_binding, package_error = _function_package_binding(root)
    if package_error:
        missing.append(package_error)
    elif package_binding is not None:
        artifacts.append(package_binding)
    spfx_binding, spfx_error = _spfx_source_manifest_binding(root)
    if spfx_error:
        missing.append(spfx_error)
    elif spfx_binding is not None:
        artifacts.append(spfx_binding)
    gates = {
        "offline_readiness_ready": readiness.get("status") == "READY",
        "activation_contract_valid": _activation_contract_valid(root),
        "all_activation_inputs_present": not missing,
        "single_subscription_bound": True,
        "single_tenant_bound": True,
        "single_workspace_bound": True,
        "fixed_function_hostname_bound": True,
        "graph_v1_only": True,
        "direct_browser_graph_forbidden": True,
        "synthetic_data_only": True,
        "stop_on_first_error": True,
    }
    status = "READY" if all(gates.values()) else "BLOCKED"
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "command": COMMAND,
        "status": status,
        "mode": "offline_plan",
        "bindings": {
            "subscription_id": SUBSCRIPTION_ID,
            "tenant_id": TENANT_ID,
            "location": LOCATION,
            "resource_group": RESOURCE_GROUP,
            "function_app": FUNCTION_APP,
            "function_base_url": f"https://{FUNCTION_APP}.azurewebsites.net",
            "api_app_display_name": API_APP_DISPLAY_NAME,
            "api_app_uri": API_APP_URI,
            "api_client_id_binding": dict(API_CLIENT_ID_BINDING),
            "delegated_scope": DELEGATED_SCOPE,
            "workspace_id": WORKSPACE_ID,
            "matter_id": MATTER_ID,
            "site_id": SITE_ID,
            "site_grant_role": "read",
            "managed_identity_graph_role": "Sites.Selected",
        },
        "gate_results": gates,
        "missing_artifacts": missing,
        "artifact_bindings": artifacts,
        "steps": _activation_steps(),
        "boundaries": {
            "live_actions_executed": 0,
            "network_accessed": False,
            "credentials_read": False,
            "secrets_written": False,
            "production_data_allowed": False,
            "other_workspaces_allowed": False,
            "credential_changes_allowed": False,
            "automatic_deletion_allowed": False,
            "automatic_rollback_allowed": False,
        },
        "required_evidence": [
            "azure_deployment_outputs_redacted",
            "entra_api_scope_binding_redacted",
            "entra_api_client_id_binding_redacted",
            "managed_identity_sites_selected_binding_redacted",
            "site_read_grant_redacted",
            "function_health_and_authorization_smoke_redacted",
            "spfx_package_and_api_approval_redacted",
            "spfx_source_manifest_and_package_sha256_redacted",
            "synthetic_workspace_readback_redacted",
            "assigned_deputy_and_denied_access_smoke_redacted",
            "idempotency_readback_redacted",
        ],
    }
    payload["activation_hash"] = _payload_hash(payload)
    return payload


def format_azure_bff_activation_plan(plan: dict[str, Any]) -> str:
    lines = [
        f"STATUS: {plan['status']}",
        f"Activation hash: {plan['activation_hash']}",
        f"Subscription: {plan['bindings']['subscription_id']}",
        f"Tenant: {plan['bindings']['tenant_id']}",
        f"Workspace: {plan['bindings']['workspace_id']}",
        f"Function: {plan['bindings']['function_base_url']}",
        f"API scope: {plan['bindings']['api_app_uri']}/{plan['bindings']['delegated_scope']}",
        "Steps:",
    ]
    lines.extend(
        f"  {step['order']:02d}. {step['id']} [{step['mode']}]"
        for step in plan["steps"]
    )
    if plan["missing_artifacts"]:
        lines.append("Missing artifacts: " + ", ".join(plan["missing_artifacts"]))
    return "\n".join(lines) + "\n"


def _artifact_bindings(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    bindings: list[dict[str, Any]] = []
    missing: list[str] = []
    for relative in _ARTIFACT_PATHS:
        path = root / relative
        if not path.is_file():
            missing.append(relative)
            continue
        bindings.append(
            {
                "path": relative,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    return bindings, missing


def _spfx_source_manifest_binding(
    root: Path,
) -> tuple[dict[str, Any] | None, str | None]:
    package_root = root / _SPFX_ROOT
    if not package_root.is_dir():
        return None, "generated:spfx-source-manifest"

    entries: list[dict[str, str]] = []
    for path in sorted(package_root.rglob("*")):
        relative_to_package = path.relative_to(package_root)
        if any(
            part in _SPFX_GENERATED_DIRECTORIES
            for part in relative_to_package.parts
        ):
            continue
        if path.is_symlink():
            return None, f"symlink:{path.relative_to(root).as_posix()}"
        if not path.is_file():
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    if not entries:
        return None, "generated:spfx-source-manifest"
    canonical = json.dumps(
        entries,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return {
        "path": "generated:spfx-source-manifest",
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "file_count": len(entries),
        "entries": entries,
    }, None


def _function_package_binding(
    root: Path,
) -> tuple[dict[str, str] | None, str | None]:
    builder_path = root / "deploy/runtime/azure/nac-bff/build_package.py"
    try:
        spec = importlib.util.spec_from_file_location(
            "nac_bff_activation_package_builder",
            builder_path,
        )
        if spec is None or spec.loader is None:
            return None, "generated:nac-bff-function.zip"
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        package = module.build_package_bytes()
        if module.validate_package(package):
            return None, "generated:nac-bff-function.zip"
    except (OSError, ValueError, ImportError, AttributeError):
        return None, "generated:nac-bff-function.zip"
    return {
        "path": "generated:nac-bff-function.zip",
        "sha256": hashlib.sha256(package).hexdigest(),
    }, None


def _activation_contract_valid(root: Path) -> bool:
    try:
        contract = json.loads(
            (
                root
                / "workflows/contracts/m365-azure-bff-activation-plan.contract.json"
            ).read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return False
    expected_bindings = {
        "subscription_id": SUBSCRIPTION_ID,
        "tenant_id": TENANT_ID,
        "location": LOCATION,
        "resource_group": RESOURCE_GROUP,
        "function_app": FUNCTION_APP,
        "api_app_display_name": API_APP_DISPLAY_NAME,
        "api_app_uri": API_APP_URI,
        "api_client_id_binding": API_CLIENT_ID_BINDING,
        "delegated_scope": DELEGATED_SCOPE,
        "workspace_id": WORKSPACE_ID,
        "matter_id": MATTER_ID,
        "site_id": SITE_ID,
        "site_grant_role": "read",
        "managed_identity_graph_role": "Sites.Selected",
    }
    expected_execution = {
        "offline_plan_live_actions_exact": 0,
        "stop_on_first_error": True,
        "steps_hash_bound": True,
        "artifact_inputs_hash_bound": True,
        "single_consolidated_owner_gate_required": True,
        "idempotency_run_required": True,
        "redacted_evidence_required": True,
    }
    expected_boundaries = {
        "production_data_allowed": False,
        "other_workspaces_allowed": False,
        "direct_browser_graph_allowed": False,
        "graph_beta_allowed": False,
        "graph_sdk_allowed": False,
        "sharepoint_legacy_api_allowed": False,
        "credential_changes_allowed": False,
        "automatic_deletion_allowed": False,
        "automatic_rollback_allowed": False,
        "synthetic_data_only": True,
    }
    expected_steps = [step["id"] for step in _activation_steps()]
    return all(
        (
            contract.get("schema_version") == SCHEMA_VERSION,
            contract.get("contract_id") == CONTRACT_ID,
            contract.get("command") == COMMAND,
            contract.get("bindings") == expected_bindings,
            contract.get("execution") == expected_execution,
            contract.get("boundaries") == expected_boundaries,
            contract.get("required_live_sequence") == expected_steps,
            contract.get("status") == "OFFLINE_READY_LIVE_DEFERRED",
        )
    )


def _activation_steps() -> list[dict[str, Any]]:
    definitions = (
        ("register_azure_providers", "azure_write", "Register only Microsoft.Web, Microsoft.Storage and Microsoft.OperationalInsights."),
        ("ensure_resource_group", "azure_write", "Create or reuse the bound test resource group in Germany West Central."),
        ("ensure_entra_api_application", "entra_write", "Create or reuse exactly one single-tenant API by app ID URI, capture its UUID appId and bind it into a redacted runtime manifest for Matter.Read."),
        ("deploy_bicep_baseline", "azure_write", "Verify the captured API appId binding, then deploy the hash-bound Function, UAMI, storage and observability baseline with that exact bffApiAudience."),
        ("assign_sites_selected", "graph_write", "Assign Graph application role Sites.Selected to the deployed UAMI."),
        ("grant_target_site_read", "graph_write", "Grant read only on the exact notary_team_01 SharePoint site."),
        ("deploy_function_package", "azure_write", "Deploy the deterministic Python package through OneDeploy remote build."),
        ("build_and_deploy_spfx", "m365_write", "Verify the bound SPFx source manifest, build and hash the generated .sppkg, then upgrade the site-scoped package with the exact BFF web API request."),
        ("approve_spfx_bff_scope", "m365_write", "Approve only NaC M365 BFF / Matter.Read for the SPFx principal."),
        ("seed_synthetic_workspace", "graph_write", "Create or reuse only the canonical synthetic matter, tasks, deadline and role assignment."),
        ("run_access_and_readback_smokes", "live_verify", "Verify assigned, deputy, denied and tamper-resistant BFF reads."),
        ("run_idempotency_and_evidence", "live_verify", "Repeat deployment/readback without duplicate data and write redacted evidence."),
    )
    return [
        {
            "order": index,
            "id": step_id,
            "mode": mode,
            "description": description,
            "stop_on_error": True,
        }
        for index, (step_id, mode, description) in enumerate(definitions, start=1)
    ]


def _payload_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("ascii")).hexdigest()
