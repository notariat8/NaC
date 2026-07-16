from __future__ import annotations

import ast
import hashlib
import io
import json
from pathlib import Path
import stat
import subprocess
from typing import Any
import zipfile

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
REQUESTED_ACCESS_TOKEN_VERSION = 2
ENTRA_API_CONTRACT = {
    "sign_in_audience": "AzureADMyOrg",
    "requested_access_token_version": REQUESTED_ACCESS_TOKEN_VERSION,
    "delegated_scope": DELEGATED_SCOPE,
    "readback_required_before_azure_deploy": True,
    "readback_fields": [
        "appId",
        "identifierUris",
        "signInAudience",
        "api.requestedAccessTokenVersion",
        "api.oauth2PermissionScopes",
    ],
}
WORKSPACE_ID = "notary_team_01"
MATTER_ID = "NAC-SYN-MATTER-001"
SITE_ID = (
    "funktion8.sharepoint.com,31324d31-3074-4f1c-ba45-3b3fd5f5ce97,"
    "56fc9349-e123-4252-ae2a-05d5d61c9b38"
)
SITE_URL = "https://funktion8.sharepoint.com/sites/NaC-Notar-01"
TEAM_ID = "124f1b11-207d-4307-bfd1-ac0fd73aa90a"
LIST_IDS = {
    "Akten": "588d4a41-f538-4f37-acfb-63ff283e0910",
    "AufgabenFristen": "720ef1d4-8496-4ecb-aa1f-5fa4568343f2",
    "Vertretungsfreigaben": "ec12d339-d9b7-45e9-be45-38dadd917746",
    "AuditJournalLite": "327181c2-e402-48e9-bcfa-1f5081b45d9c",
}
APP_CATALOG_SCOPE = "tenant"
SPFX_SOLUTION_ID = "b7a5417c-0dd3-4e69-87c7-95adfd7e8a58"
SPFX_WEB_PART_ID = "3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21"
SPFX_PAGE_NAME = "NaC-Testumgebung.aspx"
CLI_TEST_CLIENT_ID = "c86dded6-9723-4b8d-91f2-e0fd70e25839"
PROVISIONER_CLIENT_ID = "6845f6c3-896c-4e44-a50f-2a5086a13fac"
M365_CLI_OWNER_UPN = "ofunk@funktion8.de"
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
_GIT_EXECUTABLE = Path("/usr/bin/git")
_PACKAGE_BUILDER_SHA256 = (
    "96a55638359f3e89d16ed577ccdc425754d3ecf0aed1d5c03f1282833a630f36"
)
_PACKAGE_HOST_FILES = ("function_app.py", "host.json", "requirements.txt")
_PACKAGE_SOURCE_PACKAGES = ("nac_bff", "nac_m365_graph")
_PACKAGE_SOURCE_MODULES = ("nac_mvp_test_environment.py",)
_PACKAGE_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_ARTIFACT_PATHS = (
    "workflows/contracts/m365-azure-bff-activation-plan.contract.json",
    "workflows/contracts/m365-azure-bff-live-activation.contract.json",
    "src/nac_bff/azure_activation_runner.py",
    "src/nac_bff/azure_activation_composition.py",
    "src/nac_bff/approved_git_tree.py",
    "src/nac_bff/azure_live_commands.py",
    "src/nac_bff/graph_activation.py",
    "src/nac_bff/live_synthetic_workspace.py",
    "src/nac_cli/cli.py",
    "deploy/runtime/azure/nac-bff/infra/main.bicep",
    "deploy/runtime/azure/nac-bff/infra/compiled/main.json",
    "deploy/runtime/azure/nac-bff/build_package.py",
    "deploy/runtime/azure/nac-bff/requirements.txt",
    "deploy/runtime/azure/nac-bff/apparmor/nac-azure-cli-sealed-runtime",
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
        "source_commit_bound": bool(_source_commit(root)),
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
            "entra_api_contract": dict(ENTRA_API_CONTRACT),
            "delegated_scope": DELEGATED_SCOPE,
            "workspace_id": WORKSPACE_ID,
            "matter_id": MATTER_ID,
            "site_id": SITE_ID,
            "site_url": SITE_URL,
            "team_id": TEAM_ID,
            "list_ids": dict(LIST_IDS),
            "app_catalog_scope": APP_CATALOG_SCOPE,
            "spfx_solution_id": SPFX_SOLUTION_ID,
            "spfx_web_part_id": SPFX_WEB_PART_ID,
            "spfx_page_name": SPFX_PAGE_NAME,
            "cli_test_client_id": CLI_TEST_CLIENT_ID,
            "provisioner_client_id": PROVISIONER_CLIENT_ID,
            "m365_cli_owner_upn": M365_CLI_OWNER_UPN,
            "site_grant_role": "read",
            "managed_identity_graph_role": "Sites.Selected",
        },
        "gate_results": gates,
        "source_control": {
            "commit": _source_commit(root),
            "clean_tree_required_for_live_execution": True,
        },
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
            "entra_api_contract_readback_redacted",
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

    git = _trusted_git_executable()
    if git is None:
        return None, "generated:spfx-source-manifest"
    try:
        completed = subprocess.run(
            [
                git,
                "--no-optional-locks",
                "-C",
                str(root),
                "ls-files",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                _SPFX_ROOT,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None, "generated:spfx-source-manifest"
    if completed.returncode != 0:
        return None, "generated:spfx-source-manifest"

    entries: list[dict[str, str]] = []
    for relative in sorted(
        line.strip() for line in completed.stdout.splitlines() if line.strip()
    ):
        path = root / relative
        if path.is_symlink():
            return None, f"symlink:{relative}"
        if not path.exists():
            continue
        if not path.is_file():
            return None, f"invalid:{relative}"
        entries.append(
            {
                "path": relative,
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
        "source": "git_tracked_files_only",
        "sha256": hashlib.sha256(canonical).hexdigest(),
        "file_count": len(entries),
        "entries": entries,
    }, None


def _function_package_binding(
    root: Path,
) -> tuple[dict[str, str] | None, str | None]:
    builder_path = root / "deploy/runtime/azure/nac-bff/build_package.py"
    try:
        builder_source = builder_path.read_bytes()
        if hashlib.sha256(builder_source).hexdigest() != _PACKAGE_BUILDER_SHA256:
            return None, "generated:nac-bff-function.zip"
        tree = ast.parse(builder_source.decode("utf-8"), filename=str(builder_path))
        if not _package_builder_ast_is_declarative(tree):
            return None, "generated:nac-bff-function.zip"
        package = _build_function_package_bytes(root)
    except (OSError, UnicodeError, SyntaxError, ValueError, zipfile.BadZipFile):
        return None, "generated:nac-bff-function.zip"
    return {
        "path": "generated:nac-bff-function.zip",
        "sha256": hashlib.sha256(package).hexdigest(),
    }, None


def _package_builder_ast_is_declarative(tree: ast.Module) -> bool:
    expected_literals = {
        "_HOST_FILES": _PACKAGE_HOST_FILES,
        "_SOURCE_PACKAGES": _PACKAGE_SOURCE_PACKAGES,
        "_SOURCE_MODULES": _PACKAGE_SOURCE_MODULES,
        "_ZIP_TIMESTAMP": _PACKAGE_ZIP_TIMESTAMP,
    }
    observed: dict[str, object] = {}
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            continue
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if not isinstance(target, ast.Name):
                return False
            if target.id in expected_literals:
                try:
                    observed[target.id] = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    return False
                continue
            if target.id in {
                "_LOCKED_IMPORTS",
                "_FORBIDDEN_REACHABLE_AUTH_MARKERS",
            }:
                try:
                    ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    return False
                continue
            if target.id in {
                "HOST_ROOT",
                "REPO_ROOT",
                "SRC_ROOT",
                "DEFAULT_OUTPUT",
            }:
                continue
            return False
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            continue
        return False
    return observed == expected_literals


def _is_main_guard(test: ast.expr) -> bool:
    return bool(
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "__name__"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and len(test.comparators) == 1
        and isinstance(test.comparators[0], ast.Constant)
        and test.comparators[0].value == "__main__"
    )


def _build_function_package_bytes(root: Path) -> bytes:
    host_root = root / "deploy/runtime/azure/nac-bff"
    src_root = root / "src"
    files: dict[str, bytes] = {}
    for name in _PACKAGE_HOST_FILES:
        files[name] = (host_root / name).read_bytes()
    for package_name in _PACKAGE_SOURCE_PACKAGES:
        package_root = src_root / package_name
        for path in sorted(package_root.rglob("*.py")):
            relative = path.relative_to(src_root).as_posix()
            content = path.read_bytes()
            ast.parse(content.decode("utf-8"), filename=relative)
            files[relative] = content
    for name in _PACKAGE_SOURCE_MODULES:
        content = (src_root / name).read_bytes()
        ast.parse(content.decode("utf-8"), filename=name)
        files[name] = content
    files["package-manifest.json"] = _function_package_manifest(files)

    target = io.BytesIO()
    with zipfile.ZipFile(target, mode="w") as package:
        for package_path, content in sorted(files.items()):
            info = zipfile.ZipInfo(package_path, date_time=_PACKAGE_ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            package.writestr(info, content, compresslevel=9)
    return target.getvalue()


def _function_package_manifest(files: dict[str, bytes]) -> bytes:
    document = {
        "formatVersion": 2,
        "pythonRuntime": "3.12",
        "deployment": {
            "technology": "oneDeploy",
            "remoteBuildRequired": True,
            "remoteBuildFlag": "--build-remote true",
            "sourcePackage": True,
        },
        "dependencyLock": {
            "path": "requirements.txt",
            "sha256": hashlib.sha256(files["requirements.txt"]).hexdigest(),
        },
        "files": [
            {"path": file_path, "sha256": hashlib.sha256(content).hexdigest()}
            for file_path, content in sorted(files.items())
        ],
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")


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
        "entra_api_contract": ENTRA_API_CONTRACT,
        "delegated_scope": DELEGATED_SCOPE,
        "workspace_id": WORKSPACE_ID,
        "matter_id": MATTER_ID,
        "site_id": SITE_ID,
        "site_url": SITE_URL,
        "team_id": TEAM_ID,
        "list_ids": LIST_IDS,
        "app_catalog_scope": APP_CATALOG_SCOPE,
        "spfx_solution_id": SPFX_SOLUTION_ID,
        "spfx_web_part_id": SPFX_WEB_PART_ID,
        "spfx_page_name": SPFX_PAGE_NAME,
        "cli_test_client_id": CLI_TEST_CLIENT_ID,
        "provisioner_client_id": PROVISIONER_CLIENT_ID,
        "m365_cli_owner_upn": M365_CLI_OWNER_UPN,
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
        "live_success_evidence_must_be_runner_generated": True,
        "offline_plan_must_not_emit_live_success": True,
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
        ("ensure_entra_api_application", "entra_write", "Create or reuse exactly one single-tenant API by app ID URI with api.requestedAccessTokenVersion=2, capture its UUID appId, and read back the exact Matter.Read contract before Azure deploy."),
        ("deploy_bicep_baseline", "azure_write", "Verify the captured Entra v2 readback and API appId binding, then deploy the hash-bound Function, UAMI, storage and observability baseline with that exact bffApiAudience."),
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


def _source_commit(root: Path) -> str:
    git = _trusted_git_executable()
    if git is None:
        return ""
    try:
        completed = subprocess.run(
            [git, "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    commit = completed.stdout.strip().lower()
    if (
        completed.returncode != 0
        or len(commit) != 40
        or any(character not in "0123456789abcdef" for character in commit)
    ):
        return ""
    return commit


def _trusted_git_executable() -> str | None:
    try:
        metadata = _GIT_EXECUTABLE.stat()
    except OSError:
        return None
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != 0
        or metadata.st_mode & 0o022
    ):
        return None
    return str(_GIT_EXECUTABLE)
