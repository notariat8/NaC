from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from nac_bff.azure_activation import (
    DELEGATED_SCOPE,
    LOCATION,
    PROVISIONER_CLIENT_ID,
    RESOURCE_GROUP,
    SITE_ID,
    SITE_URL,
    TEAM_ID,
    TENANT_ID,
)
from nac_bff.azure_activation_composition import (
    AzureBffLiveExecutionPort,
    GitHubApprovalVerifier,
    HttpReadinessAdapter,
    LocalBuildAdapter,
    _bound_provisioner_token_provider,
    _copy_snapshot,
    _deployment_name,
    _normalize_zip_archive,
    build_live_activation_execution_port,
    inspect_entra_api_application_prewrite,
)
from nac_bff.azure_activation_attestations import (
    AZURE_CLI_EXECUTION_PATH,
    BUILD_NODE_EXECUTION_PATH,
    BUILD_NPM_CLI_EXECUTION_PATH,
    BUILD_PYTHON_EXECUTION_PATH,
    GH_CLI_EXECUTION_PATH,
    M365_CLI_EXECUTION_PATH,
    M365_NODE_EXECUTION_PATH,
)
from nac_m365_graph.node_runtime_integrity import build_node_runtime_manifest
from nac_bff.azure_activation_runner import (
    ActivationContext,
    ActivationStepError,
    DEFAULT_OUTPUT_ROOT,
    LiveActivationRequest,
    _sha256_json as _runner_sha256_json,
    run_azure_bff_live_activation,
)
from nac_bff.azure_live_commands import _validated_command
from nac_bff.graph_activation import ApiApplicationBinding
from nac_m365_graph.auth import (
    CertificateClientCredentialsTokenProvider,
    GraphConfigError,
)


ACTIVATION_HASH = "a" * 64
COMMIT = "b" * 40
TREE = "c" * 40
APPROVAL_REFERENCE = (
    "https://github.com/notariat8/NaC/issues/632#issuecomment-123456789"
)
API_APP_ID = "11111111-1111-4111-8111-111111111111"
API_SERVICE_PRINCIPAL_ID = "22222222-2222-4222-8222-222222222222"
UAMI_APP_ID = "33333333-3333-4333-8333-333333333333"
ACTOR_ID = "44444444-4444-4444-8444-444444444444"
PERMISSION_REQUEST_ID = "55555555-5555-4555-8555-555555555555"
APP_CATALOG_ID = "66666666-6666-4666-8666-666666666666"
TEAMS_CATALOG_ID = "77777777-7777-4777-8777-777777777777"
WEB_PART_ID = "3a7bba0c-f8c4-41d6-9ec9-f8a3f7e6fa21"
AZURE_CLI_TOOLCHAIN_SHA256 = "1" * 64
M365_CLI_SHA256 = "2" * 64
M365_NODE_SHA256 = "3" * 64
BUILD_PYTHON_SHA256 = "8" * 64
BUILD_NODE_SHA256 = "4" * 64
BUILD_NPM_CLI_SHA256 = "5" * 64
GH_CLI_SHA256 = "6" * 64
PROVISIONER_CERTIFICATE_SHA256 = "7" * 64
STEPS = (
    "register_azure_providers",
    "ensure_resource_group",
    "ensure_entra_api_application",
    "deploy_bicep_baseline",
    "assign_sites_selected",
    "grant_target_site_read",
    "deploy_function_package",
    "build_and_deploy_spfx",
    "approve_spfx_bff_scope",
    "seed_synthetic_workspace",
    "run_access_and_readback_smokes",
    "run_idempotency_and_evidence",
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_json(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256_text(raw)


def _context(repo_root: Path, run_dir: Path | None = None) -> ActivationContext:
    return ActivationContext(
        repo_root=repo_root,
        run_dir=run_dir or repo_root / "out",
        correlation_reference_sha256="d" * 64,
        reason_sha256="e" * 64,
        activation_hash=ACTIVATION_HASH,
        approved_commit=COMMIT,
        approved_tree=TREE,
    )


def _request(*, body_sha256: str = "f" * 64) -> LiveActivationRequest:
    return LiveActivationRequest(
        expected_activation_hash=ACTIVATION_HASH,
        approved_commit=COMMIT,
        approved_tree=TREE,
        owner_approval_reference=APPROVAL_REFERENCE,
        approval_body_sha256=body_sha256,
        azure_cli_toolchain_sha256=AZURE_CLI_TOOLCHAIN_SHA256,
        m365_cli_sha256=M365_CLI_SHA256,
        m365_node_sha256=M365_NODE_SHA256,
        build_python_sha256=BUILD_PYTHON_SHA256,
        build_node_sha256=BUILD_NODE_SHA256,
        build_npm_cli_sha256=BUILD_NPM_CLI_SHA256,
        gh_cli_sha256=GH_CLI_SHA256,
        provisioner_certificate_sha256=PROVISIONER_CERTIFICATE_SHA256,
        reason="Activate the exact synthetic BFF target.",
        correlation_id="nac-bff-live-20260714",
        owner_approved=True,
        execute_live_activation=True,
    )


def _plan() -> dict:
    return {
        "status": "READY",
        "activation_hash": ACTIVATION_HASH,
        "source_control": {"commit": COMMIT},
        "bindings": {
            "workspace_id": "notary_team_01",
            "tenant_id": TENANT_ID,
        },
        "steps": [{"id": step} for step in STEPS],
    }


def _binding(*, created: bool = False) -> ApiApplicationBinding:
    classification = "created" if created else "reused"
    return ApiApplicationBinding(
        app_id=API_APP_ID,
        service_principal_id=API_SERVICE_PRINCIPAL_ID,
        redacted_result={
            "status": classification,
            "service_principal": {"status": classification},
        },
    )


def _deployment_parameters(app_id: str = API_APP_ID) -> dict:
    return {
        "location": {"value": LOCATION},
        "environmentName": {"value": "test"},
        "m365TenantId": {"value": TENANT_ID},
        "bffApiAudience": {"value": app_id},
        "bffRequiredDelegatedScope": {"value": DELEGATED_SCOPE},
        "functionAppName": {"value": "func-nac-bff-test-funktion8"},
        "maximumInstanceCount": {"value": 4},
        "httpPerInstanceConcurrency": {"value": 16},
        "tags": {"value": {}},
    }


def _deployment_payload(outputs: dict, *, template_hash: str = "arm-template-001") -> dict:
    return {
        "properties": {
            "provisioningState": "Succeeded",
            "mode": "Incremental",
            "templateHash": template_hash,
            "parameters": _deployment_parameters(),
            "outputs": outputs,
        }
    }


def _azure_resources() -> list[dict]:
    token = "abc123"
    tags = {
        "workload": "nac-bff",
        "environment": "test",
        "managedBy": "bicep",
        "dataClassification": "no-production-data",
    }
    specifications = (
        (
            "Microsoft.ManagedIdentity/userAssignedIdentities",
            f"id-nac-bff-test-{token}",
            {},
        ),
        (
            "Microsoft.Storage/storageAccounts",
            f"stnacbff{token}",
            {"kind": "StorageV2", "sku": {"name": "Standard_LRS"}},
        ),
        (
            "Microsoft.OperationalInsights/workspaces",
            f"log-nac-bff-test-{token}",
            {},
        ),
        (
            "Microsoft.Insights/components",
            f"appi-nac-bff-test-{token}",
            {"kind": "web"},
        ),
        (
            "Microsoft.Web/serverfarms",
            f"plan-nac-bff-test-{token}",
            {
                "kind": "functionapp",
                "sku": {"name": "FC1", "tier": "FlexConsumption"},
            },
        ),
        (
            "Microsoft.Web/sites",
            "func-nac-bff-test-funktion8",
            {"kind": "functionapp,linux"},
        ),
    )
    return [
        {
            "type": resource_type,
            "name": name,
            "resourceGroup": RESOURCE_GROUP,
            "location": LOCATION,
            "tags": dict(tags),
            **details,
        }
        for resource_type, name, details in specifications
    ]


def _catalog_detail() -> dict:
    return {
        "ID": APP_CATALOG_ID,
        "ProductId": "b7a5417c-0dd3-4e69-87c7-95adfd7e8a58",
        "IsValidAppPackage": True,
        "IsPackageDefaultSkipFeatureDeployment": False,
        "SkipDeploymentFeature": False,
        "ContainsTenantWideExtension": False,
        "AadPermissions": [
            {"Resource": "NaC M365 BFF", "Scope": DELEGATED_SCOPE}
        ],
    }


def _complete_m365_state(fake) -> None:
    fake.catalog_apps = [
        {
            "ID": APP_CATALOG_ID,
            "ProductId": "b7a5417c-0dd3-4e69-87c7-95adfd7e8a58",
        }
    ]
    fake.catalog_detail = _catalog_detail()
    fake.site_apps = [
        {"ProductId": "b7a5417c-0dd3-4e69-87c7-95adfd7e8a58"}
    ]
    fake.pages = [{"Name": "NaC-Testumgebung.aspx"}]
    fake.page_detail = {"CanvasContent1": f'{{"webPartId":"{WEB_PART_ID}"}}'}
    fake.teams_apps = [{"id": TEAMS_CATALOG_ID, "externalId": WEB_PART_ID}]
    fake.teams_detail = {
        "id": TEAMS_CATALOG_ID,
        "externalId": WEB_PART_ID,
        "appDefinitions": [
            {"version": "0.2.0", "publishingState": "published"}
        ],
    }
    fake.installed_apps = {
        "value": [
            {
                "teamsApp": {
                    "id": TEAMS_CATALOG_ID,
                    "externalId": WEB_PART_ID,
                }
            }
        ]
    }



class _FakeApproval:
    def __init__(self, result: dict | None = None) -> None:
        self.result = result or {
            "status": "PASSED",
            "code": "APPROVAL_SNAPSHOT_VERIFIED",
        }
        self.calls: list[tuple[LiveActivationRequest, ActivationContext, dict]] = []

    def verify(self, request, context, plan):
        self.calls.append((request, context, plan))
        return dict(self.result)


class _FakeAzure:
    def __init__(self) -> None:
        self.ready = {"status": "READY", "code": "AZURE_CLI_READY"}
        self.commands: list[tuple[str, ...]] = []
        self.providers = {
            "Microsoft.Web": "Registered",
            "Microsoft.Storage": "Registered",
            "Microsoft.OperationalInsights": "Registered",
        }
        self.group: dict | None = {
            "name": RESOURCE_GROUP,
            "location": LOCATION,
            "tags": {
                "workload": "nac-bff",
                "environment": "test",
                "dataClassification": "no-production-data",
            },
        }
        self.deployment_outputs: dict = {
            "managedIdentityClientId": {"value": UAMI_APP_ID},
            "functionAppHostName": {
                "value": "func-nac-bff-test-funktion8.azurewebsites.net"
            },
        }
        self.group_exists_result: dict | None = None
        self.resources: list[dict] = []
        self.deployment: dict | None = None
        self.bound_artifacts = []
        self.failure: dict | None = None

    def check_readiness(self):
        return dict(self.ready)

    def run_bound(self, argv, bound_artifacts):
        self.bound_artifacts.append(dict(bound_artifacts))
        return self.run(argv)

    def run(self, argv):
        validated, family, validation_code = _validated_command(argv)
        if validated is None or family is None or validation_code != "AZURE_CLI_OK":
            raise AssertionError(
                f"composition emitted blocked Azure command: {argv!r} "
                f"({validation_code})"
            )
        command = tuple(argv)
        self.commands.append(command)
        if self.failure is not None:
            return dict(self.failure)
        if command[:2] == ("provider", "show"):
            namespace = command[command.index("--namespace") + 1]
            return {
                "ok": True,
                "code": "AZURE_CLI_COMMAND_PASSED",
                "data": {"registrationState": self.providers[namespace]},
            }
        if command[:2] == ("provider", "register"):
            namespace = command[command.index("--namespace") + 1]
            self.providers[namespace] = "Registered"
            return {"ok": True, "code": "AZURE_CLI_COMMAND_PASSED", "data": {}}
        if command[:2] == ("group", "exists"):
            if self.group_exists_result is not None:
                return dict(self.group_exists_result)
            return {
                "ok": True,
                "code": "AZURE_CLI_COMMAND_PASSED",
                "data": self.group is not None,
            }
        if command[:2] == ("group", "show"):
            if self.group is None:
                return {"ok": False, "code": "AZURE_RESOURCE_NOT_FOUND", "data": None}
            return {"ok": True, "code": "AZURE_CLI_COMMAND_PASSED", "data": self.group}
        if command[:2] == ("resource", "list"):
            return {
                "ok": True,
                "code": "AZURE_CLI_COMMAND_PASSED",
                "data": list(self.resources),
            }
        if command[:2] == ("group", "create"):
            self.group = {
                "name": RESOURCE_GROUP,
                "location": LOCATION,
                "tags": {
                    "workload": "nac-bff",
                    "environment": "test",
                    "dataClassification": "no-production-data",
                },
            }
            return {"ok": True, "code": "AZURE_CLI_COMMAND_PASSED", "data": self.group}
        if command[:3] == ("deployment", "group", "show"):
            if self.deployment is None:
                return {
                    "ok": False,
                    "code": "AZURE_RESOURCE_NOT_FOUND",
                    "data": None,
                }
            return {
                "ok": True,
                "code": "AZURE_CLI_COMMAND_PASSED",
                "data": self.deployment,
            }
        if command[:3] == ("deployment", "group", "create"):
            self.resources = _azure_resources()
            parameters_reference = command[command.index("--parameters") + 1]
            parameters_path = Path(parameters_reference.removeprefix("@"))
            parameters = json.loads(parameters_path.read_text())["parameters"]
            self.deployment = _deployment_payload(self.deployment_outputs)
            self.deployment["properties"]["parameters"] = parameters
            return {
                "ok": True,
                "code": "AZURE_CLI_COMMAND_PASSED",
                "data": self.deployment,
            }
        if command[:4] == ("functionapp", "deployment", "source", "config-zip"):
            return {"ok": True, "code": "AZURE_CLI_COMMAND_PASSED", "data": {}}
        raise AssertionError(f"unexpected Azure command: {command}")


class _FakeM365:
    def __init__(self, synthetic=None) -> None:
        self.ready = True
        self.commands: list[tuple[str, ...]] = []
        self.synthetic = synthetic
        self.grant_snapshots: list[list[dict]] = [[]]
        self.pending: list[dict] = []
        self.catalog_apps: list[dict] = []
        self.catalog_detail: dict = {}
        self.site_apps: list[dict] = []
        self.pages: list[dict] = []
        self.page_detail: dict = {}
        self.teams_apps: list[dict] = []
        self.teams_detail: dict = {}
        self.installed_apps: dict = {"value": []}
        self.command_failure: tuple[int, str, str] | None = None
        self.allow_tampered = False
        self.bound_artifacts = []
        self.invalid_bff_payload = False

    def check_readiness(self):
        return self.ready

    def run_bound(self, argv, bound_artifacts):
        self.bound_artifacts.append(dict(bound_artifacts))
        return self.run(argv)

    def run(self, argv):
        command = tuple(argv)
        self.commands.append(command)
        if self.command_failure is not None:
            return SimpleNamespace(
                returncode=self.command_failure[0],
                stdout=self.command_failure[1],
                stderr=self.command_failure[2],
            )
        if command[1:4] == ("spo", "app", "list"):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.catalog_apps), stderr=""
            )
        if command[1:4] == ("spo", "app", "get"):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.catalog_detail), stderr=""
            )
        if command[1:5] == ("spo", "app", "instance", "list"):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.site_apps), stderr=""
            )
        if command[1:4] == ("spo", "page", "list"):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.pages), stderr=""
            )
        if command[1:4] == ("spo", "page", "get"):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.page_detail), stderr=""
            )
        if command[1:4] == ("teams", "app", "list"):
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.teams_apps), stderr=""
            )
        if command[1:6] == ("spo", "serviceprincipal", "grant", "list", "--output"):
            rows = (
                self.grant_snapshots.pop(0)
                if len(self.grant_snapshots) > 1
                else self.grant_snapshots[0]
            )
            return SimpleNamespace(returncode=0, stdout=json.dumps(rows), stderr="")
        if command[1:5] == (
            "spo",
            "serviceprincipal",
            "permissionrequest",
            "list",
        ):
            return SimpleNamespace(returncode=0, stdout=json.dumps(self.pending), stderr="")
        if command[1:5] == (
            "spo",
            "serviceprincipal",
            "permissionrequest",
            "approve",
        ):
            self.pending = []
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if command[1] == "request" and "https://graph.microsoft.com" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps({"id": ACTOR_ID}),
                stderr="",
            )
        if command[1] == "request" and "/appCatalogs/teamsApps/" in command[command.index("--url") + 1]:
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.teams_detail), stderr=""
            )
        if command[1] == "request" and "/installedApps" in command[command.index("--url") + 1]:
            return SimpleNamespace(
                returncode=0, stdout=json.dumps(self.installed_apps), stderr=""
            )
        if command[1] == "request" and "api://funktion8.de/nac-bff" in command:
            url = command[command.index("--url") + 1]
            if "site_id=foreign" in url:
                if self.allow_tampered:
                    return SimpleNamespace(returncode=0, stdout="{}", stderr="")
                return SimpleNamespace(
                    returncode=1,
                    stdout=json.dumps(
                        {
                            "status": 403,
                            "error": {"code": "ACCESS_DENIED"},
                        }
                    ),
                    stderr="",
                )
            mode = self.synthetic.mode if self.synthetic is not None else "assigned"
            if mode == "denied":
                return SimpleNamespace(
                    returncode=1,
                    stdout=json.dumps(
                        {"status": 403, "error": {"code": "ACCESS_DENIED"}}
                    ),
                    stderr="",
                )
            payload = {
                "workspaceId": "notary_team_01",
                "matter": {
                    "matterId": "NAC-SYN-MATTER-001",
                    "accessMode": "wrong" if self.invalid_bff_payload else mode,
                },
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr="")
        raise AssertionError(f"unexpected M365 command: {command}")


class _FakeBuild:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def build_function_package(self, repo_root, output_path):
        self.calls.append(("function", repo_root, output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"prepared-function-package")
        return hashlib.sha256(output_path.read_bytes()).hexdigest()

    def build_spfx(self, repo_root, isolated_build_root):
        self.calls.append(("spfx", repo_root, isolated_build_root))
        config = isolated_build_root / "config/package-solution.json"
        config.parent.mkdir(parents=True, exist_ok=True)
        config.write_text(
            json.dumps(
                {
                    "solution": {
                        "id": "b7a5417c-0dd3-4e69-87c7-95adfd7e8a58",
                        "version": "0.2.0.0",
                    }
                }
            )
            + "\n"
        )
        package = isolated_build_root / "sharepoint/solution/nac-bpmn-viewer.sppkg"
        package.parent.mkdir(parents=True, exist_ok=True)
        package.write_bytes(b"prepared-spfx-package")
        return hashlib.sha256(package.read_bytes()).hexdigest(), package


class _FakeHttpReadiness:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def wait_for_status(self, url, expected_status):
        self.calls.append((url, expected_status))


class _FakeSynthetic:
    def __init__(self) -> None:
        self.mode = "assigned"
        self.calls: list[tuple] = []

    def inspect_seed(self, actor_id, correlation_id):
        self.calls.append(("inspect", actor_id, correlation_id))
        return {"status": "PASSED", "absent_count": 6, "verified_count": 0}

    def ensure_seed(self, actor_id, correlation_id):
        self.calls.append(("seed", actor_id, correlation_id))
        self.mode = "assigned"
        return {"created_count": 2, "patched_count": 1, "verified_count": 3}

    def set_access_mode(self, mode, actor_id, correlation_id):
        self.calls.append(("mode", mode, actor_id, correlation_id))
        self.mode = mode
        return {"updated_count": 1, "verified_count": 1}

    def restore_assigned(self, actor_id, correlation_id):
        self.calls.append(("restore", actor_id, correlation_id))
        self.mode = "assigned"
        return {"updated_count": 1, "verified_count": 1}

    def verify_idempotency(self, actor_id, correlation_id):
        self.calls.append(("idempotency", actor_id, correlation_id))
        return {"verified_count": 4}


class _FakeGraph:
    def __init__(self) -> None:
        self.target_site = {"id": SITE_ID}
        self.error: Exception | None = None
        self.calls: list[str] = []

    def get(self, path):
        self.calls.append(path)
        if self.error is not None:
            raise self.error
        return self.target_site


class GitHubApprovalVerifierTests(unittest.TestCase):
    def _fixture(self, *, payload_change: dict | None = None):
        temporary = tempfile.TemporaryDirectory()
        repo_root = Path(temporary.name)
        contract = repo_root / "workflows/contracts/m365-azure-bff-live-activation.contract.json"
        contract.parent.mkdir(parents=True)
        permission_boundary = {"graph": ["Sites.Selected"], "site": ["read"]}
        contract.write_text(json.dumps({"permission_boundary": permission_boundary}))
        plan = _plan()
        context = _context(repo_root)
        payload = {
            "owner-approved": True,
            "expected_activation_sha256": ACTIVATION_HASH,
            "approved_commit_sha": COMMIT,
            "approved_tree_sha": TREE,
            "toolchain_attestations_sha256": _runner_sha256_json(
                {
                    "azure_cli_toolchain_sha256": AZURE_CLI_TOOLCHAIN_SHA256,
                    "m365_cli_sha256": M365_CLI_SHA256,
                    "m365_node_sha256": M365_NODE_SHA256,
                    "build_python_sha256": BUILD_PYTHON_SHA256,
                    "build_node_sha256": BUILD_NODE_SHA256,
                    "build_npm_cli_sha256": BUILD_NPM_CLI_SHA256,
                    "gh_cli_sha256": GH_CLI_SHA256,
                    "provisioner_certificate_sha256": (
                        PROVISIONER_CERTIFICATE_SHA256
                    ),
                }
            ),
            "target_binding_sha256": _sha256_json(plan["bindings"]),
            "permission_boundary_sha256": _sha256_json(permission_boundary),
            "step_sequence_sha256": _sha256_json(list(STEPS)),
            "no_automatic_rollback_or_deletion": True,
        }
        if payload_change:
            payload.update(payload_change)
        body = json.dumps(payload, sort_keys=True)
        request = _request(body_sha256=_sha256_text(body))
        comment = {
            "user": {"login": "ofunk"},
            "author_association": "OWNER",
            "html_url": APPROVAL_REFERENCE,
            "created_at": "2026-07-14T10:00:00Z",
            "updated_at": "2026-07-14T10:00:00Z",
            "body": body,
        }
        return temporary, request, context, plan, comment

    def _verify(self, request, context, plan, comment):
        gh = context.repo_root / "tools/gh"
        gh.parent.mkdir(exist_ok=True)
        gh.write_bytes(b"trusted-gh-test-binary")
        gh.chmod(0o700)
        verifier = GitHubApprovalVerifier(
            binary=gh,
            expected_binary_sha256=hashlib.sha256(gh.read_bytes()).hexdigest(),
            environ={},
        )
        with patch.object(verifier, "_gh_json", return_value=comment) as github:
            result = verifier.verify(request, context, plan)
        github.assert_called_once()
        return result

    def test_user_owned_gh_requires_exact_digest_and_rejects_symlink(self) -> None:
        temporary, request, context, plan, comment = self._fixture()
        self.addCleanup(temporary.cleanup)
        gh = context.repo_root / "gh"
        gh.write_bytes(b"user-owned-gh")
        gh.chmod(0o700)

        unpinned = GitHubApprovalVerifier(binary=gh, environ={})
        with patch.object(unpinned, "_gh_json") as github:
            result = unpinned.verify(request, context, plan)
        self.assertEqual(result["code"], "APPROVAL_SNAPSHOT_UNAVAILABLE")
        github.assert_not_called()

        symlink = context.repo_root / "gh-link"
        symlink.symlink_to(gh)
        linked = GitHubApprovalVerifier(
            binary=symlink,
            expected_binary_sha256=hashlib.sha256(gh.read_bytes()).hexdigest(),
            environ={},
        )
        with patch.object(linked, "_gh_json") as github:
            result = linked.verify(request, context, plan)
        self.assertEqual(result["code"], "APPROVAL_SNAPSHOT_UNAVAILABLE")
        github.assert_not_called()

    def test_valid_owner_snapshot_and_payload_binding_pass(self) -> None:
        temporary, request, context, plan, comment = self._fixture()
        self.addCleanup(temporary.cleanup)
        self.assertEqual(
            self._verify(request, context, plan, comment),
            {"status": "PASSED", "code": "APPROVAL_SNAPSHOT_VERIFIED"},
        )

    def test_valid_organization_member_snapshot_passes(self) -> None:
        temporary, request, context, plan, comment = self._fixture()
        self.addCleanup(temporary.cleanup)
        comment["author_association"] = "MEMBER"

        self.assertEqual(
            self._verify(request, context, plan, comment),
            {"status": "PASSED", "code": "APPROVAL_SNAPSHOT_VERIFIED"},
        )

    def test_toolchain_attestation_tamper_breaks_approval_binding(self) -> None:
        temporary, request, context, plan, comment = self._fixture()
        self.addCleanup(temporary.cleanup)
        mutated = replace(request, m365_cli_sha256="9" * 64)

        result = self._verify(mutated, context, plan, comment)

        self.assertEqual(
            result,
            {"status": "FAILED", "code": "APPROVAL_PAYLOAD_MISMATCH"},
        )

    def test_issue_620_reference_is_rejected_before_github_lookup(self) -> None:
        temporary, request, context, plan, _comment = self._fixture()
        self.addCleanup(temporary.cleanup)
        request = request.__class__(
            **{
                **{
                    field: getattr(request, field)
                    for field in request.__dataclass_fields__
                },
                "owner_approval_reference": (
                    "https://github.com/notariat8/NaC/issues/620"
                    "#issuecomment-123456789"
                ),
            }
        )
        gh = context.repo_root / "tools/gh"
        gh.parent.mkdir(exist_ok=True)
        gh.write_bytes(b"trusted-gh-test-binary")
        gh.chmod(0o700)
        verifier = GitHubApprovalVerifier(
            binary=gh,
            expected_binary_sha256=hashlib.sha256(gh.read_bytes()).hexdigest(),
            environ={},
        )
        with patch.object(verifier, "_gh_json") as github:
            result = verifier.verify(request, context, plan)
        self.assertEqual(result["code"], "APPROVAL_SNAPSHOT_UNAVAILABLE")
        github.assert_not_called()

    def test_wrong_owner_is_distinct_from_snapshot_mismatch(self) -> None:
        mutations = (
            lambda request, comment: comment.update(user={"login": "other"}),
            lambda request, comment: comment.pop("user"),
            lambda request, comment: comment.update(user="ofunk"),
            lambda request, comment: comment.update(author_association="CONTRIBUTOR"),
            lambda request, comment: comment.update(author_association="NONE"),
            lambda request, comment: comment.update(author_association="COLLABORATOR"),
            lambda request, comment: comment.update(author_association="FIRST_TIME_CONTRIBUTOR"),
            lambda request, comment: comment.update(author_association="FIRST_TIMER"),
            lambda request, comment: comment.update(author_association="MANNEQUIN"),
            lambda request, comment: comment.update(author_association="member"),
            lambda request, comment: comment.update(author_association="UNKNOWN"),
            lambda request, comment: comment.update(author_association=None),
            lambda request, comment: comment.update(author_association=["MEMBER"]),
            lambda request, comment: comment.update(author_association={"value": "MEMBER"}),
            lambda request, comment: comment.pop("author_association"),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                temporary, request, context, plan, comment = self._fixture()
                try:
                    mutate(request, comment)
                    result = self._verify(request, context, plan, comment)
                    self.assertEqual(result["code"], "APPROVAL_OWNER_MISMATCH")
                finally:
                    temporary.cleanup()

    def test_edited_comment_and_body_hash_fail_snapshot(self) -> None:
        mutations = (
            lambda request, comment: comment.update(
                updated_at="2026-07-14T10:01:00Z"
            ),
            lambda request, comment: request.__class__(
                **{
                    **{
                        field: getattr(request, field)
                        for field in request.__dataclass_fields__
                    },
                    "approval_body_sha256": "0" * 64,
                }
            ),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                temporary, request, context, plan, comment = self._fixture()
                try:
                    changed = mutate(request, comment)
                    if changed is not None:
                        request = changed
                    result = self._verify(request, context, plan, comment)
                    self.assertEqual(result["code"], "APPROVAL_SNAPSHOT_MISMATCH")
                finally:
                    temporary.cleanup()

    def test_payload_binding_mismatch_is_distinct_from_snapshot_mismatch(self) -> None:
        temporary, request, context, plan, comment = self._fixture(
            payload_change={"approved_tree_sha": "0" * 40}
        )
        self.addCleanup(temporary.cleanup)
        result = self._verify(request, context, plan, comment)
        self.assertEqual(result, {"status": "FAILED", "code": "APPROVAL_PAYLOAD_MISMATCH"})


class GraphPrewriteCompositionTests(unittest.TestCase):
    def test_absent_api_inspection_stays_read_only(self) -> None:
        with (
            patch(
                "nac_bff.azure_activation_composition._graph_activation."
                "inspect_entra_api_application",
                return_value={
                    "status": "absent",
                    "service_principal": {"status": "absent"},
                },
            ),
            patch(
                "nac_bff.azure_activation_composition._lookup_api_applications"
            ) as lookup,
        ):
            result = inspect_entra_api_application_prewrite(object())

        self.assertIsNone(result)
        lookup.assert_not_called()

    def test_present_api_inspection_returns_internal_exact_binding(self) -> None:
        inspection = {
            "status": "present",
            "service_principal": {"status": "present"},
        }
        with (
            patch(
                "nac_bff.azure_activation_composition._graph_activation."
                "inspect_entra_api_application",
                return_value=inspection,
            ),
            patch(
                "nac_bff.azure_activation_composition._lookup_api_applications",
                return_value=[{"id": "application"}],
            ),
            patch(
                "nac_bff.azure_activation_composition._validate_api_application",
                return_value=("object-id", API_APP_ID),
            ),
            patch(
                "nac_bff.azure_activation_composition._lookup_service_principals",
                return_value=[{"id": API_SERVICE_PRINCIPAL_ID}],
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_validate_api_service_principal",
                return_value=API_SERVICE_PRINCIPAL_ID,
            ),
        ):
            result = inspect_entra_api_application_prewrite(object())

        self.assertEqual(result.app_id, API_APP_ID)
        self.assertEqual(result.service_principal_id, API_SERVICE_PRINCIPAL_ID)
        self.assertIs(result.redacted_result, inspection)


class LocalActivationAdapterTests(unittest.TestCase):
    def test_snapshot_rejects_symlink_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target.bin"
            target.write_bytes(b"trusted")
            source = root / "source.bin"
            source.symlink_to(target)
            with self.assertRaisesRegex(
                ActivationStepError,
                r"^PREPARED_ARTIFACT_SNAPSHOT_FAILED\Z",
            ):
                _copy_snapshot(
                    source,
                    root / "snapshot.bin",
                    expected_sha256=hashlib.sha256(b"trusted").hexdigest(),
                )

    def test_spfx_zip_normalization_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.sppkg"
            second = root / "second.sppkg"
            controlled_names = (
                "ClientSideAssets.xml",
                "ClientSideAssets.xml.config.xml",
                "feature_ea9917ea-2860-45fb-89bd-121120178be3.xml.config.xml",
            )
            with zipfile.ZipFile(first, "w") as archive:
                info = zipfile.ZipInfo("b.txt", date_time=(2026, 7, 15, 10, 0, 0))
                archive.writestr(info, b"b")
                archive.writestr("a.txt", b"a")
                for index, name in enumerate(controlled_names, start=1):
                    archive.writestr(
                        name,
                        f"<Id>00000000-0000-4000-8000-{index:012d}</Id>",
                    )
            with zipfile.ZipFile(second, "w") as archive:
                info = zipfile.ZipInfo("a.txt", date_time=(2025, 1, 2, 3, 4, 6))
                archive.writestr(info, b"a")
                archive.writestr("b.txt", b"b")
                for index, name in enumerate(controlled_names, start=4):
                    archive.writestr(
                        name,
                        f"<Id>11111111-1111-4111-8111-{index:012d}</Id>",
                    )

            _normalize_zip_archive(first)
            _normalize_zip_archive(second)

            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
            )

    def test_zip_normalization_rejects_noncanonical_and_colliding_names(self) -> None:
        for names in (("a/./b",), ("a//b",), ("a/b", "a/./b")):
            with self.subTest(names=names), tempfile.TemporaryDirectory() as temporary:
                package = Path(temporary) / "unsafe.sppkg"
                with zipfile.ZipFile(package, "w") as archive:
                    for name in names:
                        archive.writestr(name, b"unsafe")
                with self.assertRaisesRegex(
                    ActivationStepError,
                    "^SPFX_PACKAGE_ARCHIVE_INVALID$",
                ):
                    _normalize_zip_archive(package)

    def test_snapshot_rejects_digest_mismatch_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source.bin"
            source.write_bytes(b"unexpected")
            destination = root / "snapshot.bin"
            with self.assertRaisesRegex(
                ActivationStepError,
                r"^PREPARED_ARTIFACT_HASH_MISMATCH\Z",
            ):
                _copy_snapshot(
                    source,
                    destination,
                    expected_sha256=hashlib.sha256(b"approved").hexdigest(),
                )
            self.assertFalse(destination.exists())

    def test_local_build_uses_isolated_snapshot_and_never_mutates_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            node = root / "node/bin/node"
            npm_cli = root / "node/lib/node_modules/npm/bin/npm-cli.js"
            node.parent.mkdir(parents=True)
            npm_cli.parent.mkdir(parents=True)
            node.write_bytes(b"trusted-node-test-binary")
            npm_cli.write_bytes(b"trusted-npm-cli-test-script")
            node.chmod(0o700)
            source = root / "spfx/nac-bpmn-viewer"
            source.mkdir(parents=True)
            (source / "package.json").write_text(
                '{"scripts":{"build":"noop"}}\n'
            )
            (source / "package-lock.json").write_text("{}\n")
            config = source / "config/package-solution.json"
            config.parent.mkdir(parents=True)
            config.write_text("{}\n")
            ignored = source / "node_modules/user-owned-marker"
            ignored.parent.mkdir(parents=True)
            ignored.write_text("preserve")
            isolated = root / "run/prepared/spfx-build"
            adapter = LocalBuildAdapter(
                node_binary=node,
                npm_cli=npm_cli,
                node_sha256=hashlib.sha256(node.read_bytes()).hexdigest(),
                npm_cli_sha256=build_node_runtime_manifest(npm_cli.parent.parent).digest,
                environ={"NODE_OPTIONS": "--require=/tmp/foreign.js"},
            )

            build_calls = []

            def fake_run(argv, *, cwd, **_kwargs):
                build_calls.append(tuple(argv))
                dependencies = cwd / "node_modules"
                heft = dependencies / "@rushstack/heft/bin/heft"
                if not heft.exists():
                    heft.parent.mkdir(parents=True)
                    heft.write_bytes(b"trusted-heft-entry")
                    (heft.parent.parent / "package.json").write_text(
                        '{"name":"@rushstack/heft"}\n'
                    )
                if len(build_calls) == 3:
                    package = cwd / "sharepoint/solution/nac-bpmn-viewer.sppkg"
                    package.parent.mkdir(parents=True, exist_ok=True)
                    with zipfile.ZipFile(package, "w") as archive:
                        archive.writestr("package/data.txt", b"deterministic-package")
                        for index, name in enumerate(
                            (
                                "ClientSideAssets.xml",
                                "ClientSideAssets.xml.config.xml",
                                "feature_ea9917ea-2860-45fb-89bd-121120178be3.xml.config.xml",
                            ),
                            start=1,
                        ):
                            archive.writestr(
                                name,
                                f"<Id>00000000-0000-4000-8000-{index:012d}</Id>",
                            )

            with patch.object(
                adapter, "_run", side_effect=fake_run
            ) as run:
                digest, package = adapter.build_spfx(root, isolated)

            self.assertEqual(digest, hashlib.sha256(package.read_bytes()).hexdigest())
            with zipfile.ZipFile(package, "r") as archive:
                self.assertEqual(
                    archive.read("package/data.txt"), b"deterministic-package"
                )
                self.assertEqual(
                    archive.getinfo("package/data.txt").date_time,
                    (1980, 1, 1, 0, 0, 0),
                )
            self.assertTrue(package.is_relative_to(isolated))
            self.assertTrue((isolated / "node_modules").is_dir())
            self.assertEqual(ignored.read_text(), "preserve")
            self.assertFalse((source / "sharepoint").exists())
            self.assertEqual(run.call_count, 3)
            self.assertEqual(
                run.call_args_list[0].args[0],
                [str(node), str(npm_cli), "ci", "--ignore-scripts", "--force"],
            )
            heft_entry = isolated / "node_modules/@rushstack/heft/bin/heft"
            self.assertEqual(
                run.call_args_list[1].args[0],
                [str(node), str(heft_entry), "test", "--clean", "--production"],
            )
            self.assertEqual(
                run.call_args_list[2].args[0],
                [str(node), str(heft_entry), "package-solution", "--production"],
            )
            self.assertTrue(
                run.call_args_list[1].kwargs["force_wasi_native_fallback"]
            )
            self.assertTrue(
                run.call_args_list[2].kwargs["force_wasi_native_fallback"]
            )
            self.assertNotIn(".bin", " ".join(" ".join(call) for call in build_calls))
            combined_commands = " ".join(" ".join(call) for call in build_calls)
            self.assertNotIn("run build", combined_commands)

    def test_function_build_rejects_python_mutation_before_process(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            python = root / "python"
            python.write_bytes(b"trusted-python")
            python.chmod(0o700)
            output = root / "function.zip"
            adapter = LocalBuildAdapter(
                python_binary=python,
                python_sha256=hashlib.sha256(python.read_bytes()).hexdigest(),
                environ={},
            )

            def resolve_then_mutate() -> Path:
                python.write_bytes(b"mutated-python")
                return python

            with (
                patch.object(
                    adapter,
                    "_resolve_python_toolchain",
                    side_effect=resolve_then_mutate,
                ),
                patch(
                    "nac_bff.azure_activation_composition.subprocess.run"
                ) as run,
                self.assertRaises(ActivationStepError) as raised,
            ):
                adapter.build_function_package(root, output)

            self.assertEqual(
                raised.exception.code, "BUILD_TOOLCHAIN_ATTESTATION_FAILED"
            )
            run.assert_not_called()

    def test_spfx_rechecks_node_and_npm_before_each_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            node = root / "node/bin/node"
            npm_cli = root / "node/lib/npm-cli.js"
            node.parent.mkdir(parents=True)
            npm_cli.parent.mkdir(parents=True)
            node.write_bytes(b"trusted-node")
            npm_cli.write_bytes(b"trusted-npm")
            node.chmod(0o700)
            source = root / "spfx/nac-bpmn-viewer"
            source.mkdir(parents=True)
            (source / "package.json").write_text("{}\n")
            (source / "package-lock.json").write_text("{}\n")
            adapter = LocalBuildAdapter(
                node_binary=node,
                npm_cli=npm_cli,
                node_sha256=hashlib.sha256(node.read_bytes()).hexdigest(),
                npm_cli_sha256=build_node_runtime_manifest(npm_cli.parent.parent).digest,
                environ={},
            )

            def first_process_then_mutate(*_args, **kwargs):
                dependencies = kwargs["cwd"] / "node_modules"
                heft = dependencies / "@rushstack/heft/bin/heft"
                heft.parent.mkdir(parents=True)
                heft.write_bytes(b"trusted-heft")
                node.write_bytes(b"mutated-node")
                return SimpleNamespace(returncode=0)

            with (
                patch(
                    "nac_bff.azure_activation_composition.subprocess.run",
                    side_effect=first_process_then_mutate,
                ) as run,
                self.assertRaises(ActivationStepError) as raised,
            ):
                adapter.build_spfx(root, root / "isolated")

            self.assertEqual(
                raised.exception.code, "BUILD_TOOLCHAIN_ATTESTATION_FAILED"
            )
            self.assertEqual(run.call_count, 1)

    def test_spfx_rejects_dependency_tamper_between_direct_heft_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            node = root / "node/bin/node"
            npm_cli = root / "node/lib/npm-cli.js"
            node.parent.mkdir(parents=True)
            npm_cli.parent.mkdir(parents=True)
            node.write_bytes(b"trusted-node")
            npm_cli.write_bytes(b"trusted-npm")
            node.chmod(0o700)
            source = root / "spfx/nac-bpmn-viewer"
            source.mkdir(parents=True)
            (source / "package.json").write_text("{}\n")
            (source / "package-lock.json").write_text("{}\n")
            adapter = LocalBuildAdapter(
                node_binary=node,
                npm_cli=npm_cli,
                node_sha256=hashlib.sha256(node.read_bytes()).hexdigest(),
                npm_cli_sha256=build_node_runtime_manifest(npm_cli.parent.parent).digest,
                environ={},
            )
            calls = []

            def fake_run(argv, *, cwd, **_kwargs):
                calls.append(tuple(argv))
                heft = cwd / "node_modules/@rushstack/heft/bin/heft"
                if len(calls) == 1:
                    heft.parent.mkdir(parents=True)
                    heft.write_bytes(b"trusted-heft")
                elif len(calls) == 2:
                    heft.write_bytes(b"tampered-heft")

            with (
                patch.object(adapter, "_run", side_effect=fake_run),
                self.assertRaises(ActivationStepError) as raised,
            ):
                adapter.build_spfx(root, root / "isolated")

            self.assertEqual(
                raised.exception.code, "SPFX_DEPENDENCY_ATTESTATION_FAILED"
            )
            self.assertEqual(len(calls), 2)
            self.assertNotIn(".bin", " ".join(" ".join(call) for call in calls))

    def test_node_runtime_loader_is_inherited_by_real_child_process(self) -> None:
        detected = shutil.which("node")
        node_candidate = (
            BUILD_NODE_EXECUTION_PATH
            if BUILD_NODE_EXECUTION_PATH.is_file()
            else Path(detected) if detected else None
        )
        if node_candidate is None:
            self.skipTest("Node.js is not installed")
        node_source = node_candidate.resolve(strict=True)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            node = root / "node"
            shutil.copyfile(node_source, node)
            node.chmod(0o700)
            runtime = root / "runtime"
            runtime.mkdir()
            dependency = runtime / "dependency.cjs"
            dependency.write_text(
                "module.exports = 'sealed-child-ok';\n", encoding="utf-8"
            )
            child = runtime / "child.cjs"
            child.write_text(
                "console.log(require(" + json.dumps(str(dependency)) + "));\n",
                encoding="utf-8",
            )
            entry = runtime / "entry.cjs"
            entry.write_text(
                "const { fork } = require('node:child_process');"
                "const child = fork("
                + json.dumps(str(child))
                + ", [], {silent: true, env: process.env});"
                "let stdout = '';"
                "child.stdout.on('data', chunk => { stdout += chunk; });"
                "child.on('exit', status => {"
                "if (status !== 0 || stdout.trim() !== 'sealed-child-ok') "
                "process.exit(41);"
                "});\n",
                encoding="utf-8",
            )
            node_digest = hashlib.sha256(node.read_bytes()).hexdigest()
            runtime_digest = build_node_runtime_manifest(runtime).digest

            LocalBuildAdapter._run(
                [str(node), str(entry)],
                cwd=root,
                attestations=((node, True, node_digest),),
                node_runtime=(runtime, runtime_digest),
            )

    def test_user_owned_toolchain_requires_exact_digests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            node = root / "node"
            npm_cli = root / "npm-runtime/bin/npm-cli.js"
            npm_cli.parent.mkdir(parents=True)
            node.write_bytes(b"node")
            npm_cli.write_bytes(b"npm")
            node.chmod(0o700)
            adapter = LocalBuildAdapter(
                node_binary=node,
                npm_cli=npm_cli,
                node_sha256="0" * 64,
                npm_cli_sha256=build_node_runtime_manifest(npm_cli.parent.parent).digest,
                environ={},
            )
            self.assertIsNone(adapter._resolve_node_toolchain())

    def test_local_build_environment_drops_node_injection_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            cwd = Path(temporary)
            tool = cwd / "trusted-tool"
            tool.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            tool.chmod(0o700)
            tool_sha256 = hashlib.sha256(tool.read_bytes()).hexdigest()
            with patch(
                "nac_bff.azure_activation_composition.subprocess.run"
            ) as run:
                run.return_value = SimpleNamespace(returncode=0)
                with patch.dict(
                    "os.environ",
                    {
                        "NODE_OPTIONS": "--require=/tmp/foreign.js",
                        "NODE_PATH": "/tmp/foreign",
                        "NPM_CONFIG_USERCONFIG": "/tmp/foreign-npmrc",
                    },
                    clear=False,
                ):
                    LocalBuildAdapter._run(
                        [str(tool)],
                        cwd=cwd,
                        attestations=((tool, True, tool_sha256),),
                        force_wasi_native_fallback=True,
                    )
            environment = run.call_args.kwargs["env"]
            self.assertNotIn("NODE_OPTIONS", environment)
            self.assertNotIn("NODE_PATH", environment)
            self.assertEqual(environment["NAPI_RS_FORCE_WASI"], "error")
            self.assertEqual(environment["PATH"], "/usr/bin:/bin")
            self.assertNotEqual(
                environment["NPM_CONFIG_USERCONFIG"],
                environment["NPM_CONFIG_GLOBALCONFIG"],
            )
            self.assertTrue(
                environment["NPM_CONFIG_USERCONFIG"].endswith("npm-user.conf")
            )
            self.assertTrue(
                environment["NPM_CONFIG_GLOBALCONFIG"].endswith("npm-global.conf")
            )
            self.assertRegex(run.call_args.args[0][0], r"^/proc/self/fd/[0-9]+$")
            self.assertEqual(len(run.call_args.kwargs["pass_fds"]), 1)

    def test_http_readiness_rejects_foreign_host_without_network(self) -> None:
        adapter = HttpReadinessAdapter(attempts=1, delay_seconds=0)
        with (
            patch(
                "nac_bff.azure_activation_composition.urllib.request.urlopen"
            ) as urlopen,
            self.assertRaises(ActivationStepError) as raised,
        ):
            adapter.wait_for_status("https://foreign.example/healthz", 200)
        self.assertEqual(raised.exception.code, "FUNCTION_HEALTH_URL_INVALID")
        urlopen.assert_not_called()

    def test_http_readiness_accepts_exact_function_host(self) -> None:
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.status = 200
        adapter = HttpReadinessAdapter(attempts=1, delay_seconds=0)
        with patch(
            "nac_bff.azure_activation_composition.urllib.request.urlopen",
            return_value=response,
        ) as urlopen:
            adapter.wait_for_status(
                "https://func-nac-bff-test-funktion8.azurewebsites.net/readyz",
                200,
            )
        urlopen.assert_called_once()


class AzureBffCompositionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo_root = Path(self.temporary.name)
        self.run_dir = self.repo_root / "out"
        self.run_dir.mkdir()
        bicep = (
            self.repo_root
            / "deploy/runtime/azure/nac-bff/infra/compiled/main.json"
        )
        bicep.parent.mkdir(parents=True)
        bicep.write_text('{"$schema":"test","resources":[]}\n')
        config = self.repo_root / "spfx/nac-bpmn-viewer/config/package-solution.json"
        config.parent.mkdir(parents=True)
        config.write_text("{}\n")
        self.context = _context(self.repo_root, self.run_dir)
        self.approval = _FakeApproval()
        self.azure = _FakeAzure()
        self.graph = _FakeGraph()
        self.synthetic = _FakeSynthetic()
        self.m365 = _FakeM365(self.synthetic)
        self.build = _FakeBuild()
        self.http_readiness = _FakeHttpReadiness()
        self.port = AzureBffLiveExecutionPort(
            repo_root=self.repo_root,
            azure=self.azure,
            graph=self.graph,
            m365=self.m365,
            approval_verifier=self.approval,
            local_build=self.build,
            http_readiness=self.http_readiness,
            synthetic=self.synthetic,
            m365_readback_attempts=3,
            m365_readback_delay_seconds=0,
            sleep=lambda _seconds: None,
        )

    def _prewrite(
        self, api_binding: ApiApplicationBinding | None = _binding()
    ):
        with (
            patch(
                "nac_bff.azure_activation_composition.build_azure_bff_activation_plan",
                return_value=_plan(),
            ),
            patch(
                "nac_bff.azure_activation_composition.inspect_entra_api_application_prewrite",
                return_value=api_binding,
            ),
            patch(
                "nac_bff.azure_activation_composition.build_spfx_site_deployment_plan",
                return_value={"status": "READY", "prepared": True},
            ),
        ):
            return self.port.verify_prewrite(self.context, _request())

    def test_prewrite_stops_at_approval_azure_m365_and_graph_boundaries(self) -> None:
        self.approval.result = {"status": "FAILED", "code": "APPROVAL_PAYLOAD_MISMATCH"}
        self.assertEqual(self._prewrite()["code"], "APPROVAL_PAYLOAD_MISMATCH")
        self.assertEqual(self.azure.commands, [])
        self.assertEqual(self.graph.calls, [])

        self.approval.result = {"status": "PASSED", "code": "APPROVAL_SNAPSHOT_VERIFIED"}
        self.azure.ready = {"status": "BLOCKED", "code": "AZURE_CLI_NOT_LOGGED_IN"}
        self.assertEqual(self._prewrite()["code"], "AZURE_CLI_NOT_READY")
        self.assertEqual(self.graph.calls, [])

        self.azure.ready = {"status": "READY", "code": "AZURE_CLI_READY"}
        self.m365.ready = False
        self.assertEqual(self._prewrite()["code"], "M365_CLI_NOT_READY")
        self.assertEqual(self.graph.calls, [])

        self.m365.ready = True
        self.graph.error = RuntimeError("secret bearer token")
        self.assertEqual(self._prewrite()["code"], "GRAPH_PROVISIONER_NOT_READY")
        self.graph.error = None
        self.graph.target_site = {
            "id": "funktion8.sharepoint.com,99999999-9999-4999-8999-999999999999"
        }
        self.assertEqual(self._prewrite()["code"], "GRAPH_TARGET_SITE_MISMATCH")

    def test_prewrite_passes_only_for_exact_target_site(self) -> None:
        self.assertEqual(
            self._prewrite(),
            {
                "status": "PASSED",
                "code": "PREWRITE_VERIFIED",
                "prebuilt_inputs_verified": True,
            },
        )
        self.assertEqual(self.graph.calls, [f"/sites/{SITE_ID}?$select=id"])

    def test_prewrite_rejects_malformed_target_site_response(self) -> None:
        self.graph.target_site = {"value": [{"id": SITE_ID}]}
        self.assertEqual(self._prewrite()["code"], "GRAPH_TARGET_SITE_MISMATCH")

    def test_missing_api_app_is_created_after_static_snapshot_without_rebuild(
        self,
    ) -> None:
        self.assertEqual(
            self._prewrite(api_binding=None),
            {
                "status": "PASSED",
                "code": "PREWRITE_VERIFIED",
                "prebuilt_inputs_verified": False,
            },
        )
        self.assertIsNone(self.port._bicep_parameters_path)
        self.assertIsNone(self.port._prepared_inputs_path)
        self.assertEqual([call[0] for call in self.build.calls], ["function", "spfx"])
        build_call_count = len(self.build.calls)

        with patch(
            "nac_bff.azure_activation_composition."
            "ensure_entra_api_application_binding",
            return_value=_binding(created=True),
        ) as ensure_api:
            result = self.port.execute_step(STEPS[2], self.context)

        self.assertEqual(result["classification"], "created")
        self.assertIs(result["prebuilt_inputs_verified"], True)
        self.assertEqual(len(self.build.calls), build_call_count)
        ensure_api.assert_called_once_with(self.graph)
        self.assertTrue(self.port._bicep_parameters_path.is_file())
        self.assertTrue(self.port._prepared_inputs_path.is_file())
        parameters = json.loads(self.port._bicep_parameters_path.read_text())
        self.assertEqual(
            parameters["parameters"]["bffApiAudience"]["value"], API_APP_ID
        )
        self.port._require_prepared_inputs(self.context)

    def test_prewrite_fails_closed_on_azure_group_probe_error(self) -> None:
        self.azure.group_exists_result = {
            "ok": False,
            "code": "AZURE_CLI_COMMAND_FAILED",
            "data": None,
        }

        result = self._prewrite()

        self.assertEqual(result["code"], "AZURE_RESOURCE_GROUP_PREFLIGHT_FAILED")
        self.assertFalse(
            any(command[:2] == ("group", "show") for command in self.azure.commands)
        )
        self.assertFalse(
            any(command[:2] == ("group", "create") for command in self.azure.commands)
        )

    def test_prewrite_blocks_ambiguous_provider_state_without_write(self) -> None:
        self.azure.providers["Microsoft.Web"] = "Unregistering"

        result = self._prewrite()

        self.assertEqual(result["code"], "AZURE_PROVIDER_STATE_AMBIGUOUS")
        self.assertFalse(
            any(command[:2] == ("provider", "register") for command in self.azure.commands)
        )

    def test_prewrite_false_group_probe_is_only_creation_path(self) -> None:
        self.azure.group = None

        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.assertFalse(
            any(command[:2] == ("group", "show") for command in self.azure.commands)
        )
        created = self.port.execute_step(STEPS[1], self.context)

        self.assertEqual(created["classification"], "created")
        self.assertEqual(
            sum(command[:2] == ("group", "create") for command in self.azure.commands),
            1,
        )

    def test_prewrite_rejects_existing_resources_without_bound_deployment(self) -> None:
        self.azure.resources = _azure_resources()

        result = self._prewrite()

        self.assertEqual(
            result["code"], "AZURE_BASELINE_DEPLOYMENT_BINDING_MISSING"
        )
        self.assertFalse(
            any(
                command[:3] == ("deployment", "group", "create")
                for command in self.azure.commands
            )
        )

    def test_cross_hash_reuses_stable_target_bound_deployment(self) -> None:
        self.azure.resources = _azure_resources()
        self.azure.deployment = _deployment_payload(self.azure.deployment_outputs)
        first_name = _deployment_name(self.context)
        other_context = replace(
            self.context,
            activation_hash="9" * 64,
            run_dir=self.repo_root / "out-cross-hash",
        )
        self.assertEqual(_deployment_name(other_context), first_name)
        original_context = self.context
        self.context = other_context
        try:
            with (
                patch(
                    "nac_bff.azure_activation_composition."
                    "_graph_activation.inspect_uami_sites_selected",
                    return_value={"status": "absent", "assignment_count": 0},
                ),
                patch(
                    "nac_bff.azure_activation_composition."
                    "_graph_activation.inspect_site_read_permission",
                    return_value={"status": "absent", "permission_count": 0},
                ),
            ):
                result = self._prewrite()
        finally:
            self.context = original_context
        self.assertEqual(result["status"], "PASSED")
        deployment_show = next(
            command
            for command in self.azure.commands
            if command[:3] == ("deployment", "group", "show")
        )
        self.assertEqual(
            deployment_show[deployment_show.index("--name") + 1],
            first_name,
        )

    def test_existing_baseline_prewrite_inspects_uami_and_site_before_any_write(
        self,
    ) -> None:
        self.azure.resources = _azure_resources()
        self.azure.deployment = _deployment_payload(self.azure.deployment_outputs)
        events: list[str] = []

        with (
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_uami_sites_selected",
                side_effect=lambda *_args, **_kwargs: (
                    events.append("sites-selected")
                    or {"status": "absent", "assignment_count": 0}
                ),
            ) as inspect_sites_selected,
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_site_read_permission",
                side_effect=lambda *_args, **_kwargs: (
                    events.append("site-read")
                    or {"status": "absent", "permission_count": 0}
                ),
            ) as inspect_site_read,
        ):
            result = self._prewrite()

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(events, ["sites-selected", "site-read"])
        inspect_sites_selected.assert_called_once_with(self.graph, UAMI_APP_ID)
        inspect_site_read.assert_called_once_with(
            self.graph, UAMI_APP_ID, site_id=SITE_ID
        )
        self.assertFalse(
            any(
                command[:2] == ("provider", "register")
                or command[:2] == ("group", "create")
                or command[:3] == ("deployment", "group", "create")
                for command in self.azure.commands
            )
        )
        self.assertFalse(
            any(
                command[1:4]
                in {
                    ("spo", "app", "add"),
                    ("spo", "app", "deploy"),
                    ("spo", "app", "install"),
                }
                or "approve" in command
                for command in self.m365.commands
            )
        )

    def test_existing_baseline_prewrite_propagates_graph_duplicate_failure(self) -> None:
        self.azure.resources = _azure_resources()
        self.azure.deployment = _deployment_payload(self.azure.deployment_outputs)
        with patch(
            "nac_bff.azure_activation_composition."
            "_graph_activation.inspect_uami_sites_selected",
            side_effect=ActivationStepError("UAMI_SITES_SELECTED_DUPLICATE"),
        ):
            result = self._prewrite()

        self.assertEqual(result["code"], "UAMI_SITES_SELECTED_DUPLICATE")
        self.assertFalse(
            any(
                command[:3] == ("deployment", "group", "create")
                for command in self.azure.commands
            )
        )

    def test_prewrite_uses_exact_page_and_teams_readback_commands(self) -> None:
        _complete_m365_state(self.m365)
        self.m365.grant_snapshots = [
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}]
        ]

        self.assertEqual(self._prewrite()["status"], "PASSED")

        self.assertIn(
            (
                "m365",
                "spo",
                "page",
                "get",
                "--name",
                "NaC-Testumgebung.aspx",
                "--webUrl",
                SITE_URL,
                "--output",
                "json",
            ),
            self.m365.commands,
        )
        self.assertIn(
            (
                "m365",
                "teams",
                "app",
                "list",
                "--distributionMethod",
                "organization",
                "--output",
                "json",
            ),
            self.m365.commands,
        )
        request_urls = [
            command[command.index("--url") + 1]
            for command in self.m365.commands
            if command[1] == "request" and "--url" in command
        ]
        self.assertIn(
            "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps/"
            f"{TEAMS_CATALOG_ID}?$expand=appDefinitions",
            request_urls,
        )
        self.assertIn(
            f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/installedApps"
            f"?$filter=teamsApp/externalId%20eq%20'{WEB_PART_ID}'"
            "&$expand=teamsApp",
            request_urls,
        )

    def test_prewrite_blocks_unexpected_grants_catalog_duplicates_and_synthetic_failure(
        self,
    ) -> None:
        exact_catalog = {"ProductId": "b7a5417c-0dd3-4e69-87c7-95adfd7e8a58"}
        cases = (
            (
                "SPFX_BFF_GRANT_BROADER_OR_DUPLICATE",
                [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": "Matter.Write"}],
                [],
                {"status": "PASSED"},
            ),
            (
                "SPFX_APP_CATALOG_BOUNDARY_FAILED",
                [],
                [exact_catalog, exact_catalog],
                {"status": "PASSED"},
            ),
            (
                "SYNTHETIC_PREFLIGHT_FAILED",
                [],
                [],
                {"status": "FAILED"},
            ),
        )
        for code, grants, catalog, synthetic_result in cases:
            with self.subTest(code=code):
                self.m365.grant_snapshots = [grants]
                self.m365.catalog_apps = catalog
                with patch.object(
                    self.synthetic, "inspect_seed", return_value=synthetic_result
                ):
                    result = self._prewrite()
                self.assertEqual(result["code"], code)
                self.assertFalse(
                    any(
                        command[:2] in {("provider", "register"), ("group", "create")}
                        for command in self.azure.commands
                    )
                )

        self.m365.grant_snapshots = [
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}]
        ]
        self.m365.pending = [
            {
                "Id": "33333333-3333-4333-8333-333333333333",
                "ResourceId": UAMI_APP_ID,
                "Resource": "External Connection",
                "Scope": "ExternalConnection.ReadWrite.All",
            },
            {
                "Id": PERMISSION_REQUEST_ID,
                "ResourceId": API_SERVICE_PRINCIPAL_ID,
                "Resource": "NaC M365 BFF",
                "Scope": DELEGATED_SCOPE,
            }
        ]
        self.assertEqual(
            self._prewrite()["code"], "SPFX_BFF_PERMISSION_STATE_DUPLICATE"
        )

    def test_prewrite_ignores_unrelated_spfx_permission_requests(self) -> None:
        unrelated = {
            "Id": "33333333-3333-4333-8333-333333333333",
            "ResourceId": UAMI_APP_ID,
            "Resource": "External Connection",
            "Scope": "ExternalConnection.ReadWrite.All",
        }
        self.m365.pending = [unrelated]
        self.assertEqual(self._prewrite(api_binding=None)["status"], "PASSED")

    def test_prewrite_rejects_duplicate_bound_spfx_permission_requests(self) -> None:
        exact = {
            "Id": PERMISSION_REQUEST_ID,
            "ResourceId": API_SERVICE_PRINCIPAL_ID,
            "Resource": "NaC M365 BFF",
            "Scope": DELEGATED_SCOPE,
        }
        self.m365.pending = [exact, dict(exact)]
        self.assertEqual(
            self._prewrite()["code"], "SPFX_BFF_PERMISSION_REQUEST_UNEXPECTED"
        )

    def test_prewrite_ignores_unrelated_spfx_grants_but_rejects_bound_duplicates(
        self,
    ) -> None:
        unrelated = {"resourceId": UAMI_APP_ID, "scope": "Files.Read.All"}
        exact = {
            "resourceId": API_SERVICE_PRINCIPAL_ID,
            "scope": DELEGATED_SCOPE,
        }
        self.m365.grant_snapshots = [[unrelated, exact]]
        self.assertEqual(self._prewrite()["status"], "PASSED")

        self.m365.grant_snapshots = [[unrelated, exact, dict(exact)]]
        self.assertEqual(
            self._prewrite()["code"], "SPFX_BFF_GRANT_BROADER_OR_DUPLICATE"
        )

    def test_prewrite_accepts_safe_legacy_spfx_package_for_upgrade(self) -> None:
        _complete_m365_state(self.m365)
        self.m365.catalog_detail["AadPermissions"] = None
        self.assertEqual(self._prewrite()["status"], "PASSED")

    def test_prewrite_rejects_unsafe_legacy_spfx_package(self) -> None:
        _complete_m365_state(self.m365)
        self.m365.catalog_detail["AadPermissions"] = [
            {"Resource": "Microsoft Graph", "Scope": "Sites.ReadWrite.All"}
        ]
        self.assertEqual(
            self._prewrite()["code"], "SPFX_APP_CATALOG_BOUNDARY_FAILED"
        )

        _complete_m365_state(self.m365)
        del self.m365.catalog_detail["AadPermissions"]
        self.assertEqual(
            self._prewrite()["code"], "SPFX_APP_CATALOG_BOUNDARY_FAILED"
        )

        _complete_m365_state(self.m365)
        self.m365.catalog_detail["AadPermissions"] = None
        self.m365.catalog_detail["ContainsTenantWideExtension"] = True
        self.assertEqual(
            self._prewrite()["code"], "SPFX_APP_CATALOG_BOUNDARY_FAILED"
        )

    def test_approved_tree_requires_two_identical_spfx_builds(self) -> None:
        class ApprovedTree:
            def materialize(self, repo_root, _destination, **_kwargs):
                return SimpleNamespace(root=repo_root, manifest_sha256="a" * 64)

        class DriftingBuild(_FakeBuild):
            def build_spfx(self, repo_root, isolated_build_root):
                digest, package = super().build_spfx(repo_root, isolated_build_root)
                if sum(call[0] == "spfx" for call in self.calls) == 2:
                    package.write_bytes(b"drifting-spfx-package")
                    digest = hashlib.sha256(package.read_bytes()).hexdigest()
                return digest, package

        self.port._approved_tree_source = ApprovedTree()
        self.port._build = DriftingBuild()
        with (
            patch(
                "nac_bff.azure_activation_composition.build_azure_bff_activation_plan",
                return_value=_plan(),
            ),
            patch(
                "nac_bff.azure_activation_composition.inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ),
        ):
            result = self.port.verify_prewrite(self.context, _request())

        self.assertEqual(result["code"], "SPFX_REPRODUCIBILITY_FAILED")
        self.assertEqual(
            [call[0] for call in self.port._build.calls],
            ["function", "spfx", "spfx"],
        )

    def test_prewrite_prepares_snapshots_and_later_deploy_rejects_mutation(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.assertEqual([call[0] for call in self.build.calls], ["function", "spfx"])
        self.assertTrue(str(self.port._bicep_path).startswith(str(self.run_dir)))
        self.assertTrue(str(self.port._spfx_package_path).startswith(str(self.run_dir)))

        self.port.execute_step(STEPS[3], self.context)
        deployment = next(
            command
            for command in self.azure.commands
            if command[:3] == ("deployment", "group", "create")
        )
        template_index = deployment.index("--template-file") + 1
        self.assertEqual(Path(deployment[template_index]), self.port._bicep_path)
        parameters_index = deployment.index("--parameters") + 1
        self.assertEqual(
            deployment[parameters_index],
            f"@{self.port._bicep_parameters_path}",
        )
        parameters = json.loads(self.port._bicep_parameters_path.read_text())
        self.assertEqual(
            parameters["parameters"]["bffApiAudience"]["value"], API_APP_ID
        )
        manifest = json.loads(self.port._prepared_inputs_path.read_text())
        self.assertEqual(
            set(manifest),
            {
                "schema_version",
                "approved_commit_sha",
                "approved_tree_sha",
                "activation_hash",
                "approved_tree_snapshot_sha256",
                "bicep_snapshot_sha256",
                "bicep_parameters_snapshot_sha256",
                "function_package_sha256",
                "spfx_package_sha256",
                "prepared_inputs_sha256",
            },
        )

        build_call_count = len(self.build.calls)
        self.port.execute_step(STEPS[6], self.context)
        self.assertEqual(len(self.build.calls), build_call_count)
        self.assertEqual(
            self.http_readiness.calls,
            [("https://func-nac-bff-test-funktion8.azurewebsites.net/healthz", 200)],
        )

        self.port._spfx_package_path.chmod(0o600)
        self.port._spfx_package_path.write_bytes(b"tampered")
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[7], self.context)
        self.assertEqual(raised.exception.code, "PREPARED_ARTIFACT_HASH_MISMATCH")

    def test_bicep_deploy_rejects_mutated_parameter_snapshot_before_write(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._bicep_parameters_path.write_text("{}\n", encoding="utf-8")
        writes_before = sum(
            command[:3] == ("deployment", "group", "create")
            for command in self.azure.commands
        )

        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[3], self.context)

        self.assertEqual(raised.exception.code, "PREPARED_ARTIFACT_HASH_MISMATCH")
        self.assertEqual(
            sum(
                command[:3] == ("deployment", "group", "create")
                for command in self.azure.commands
            ),
            writes_before,
        )

    def test_prewrite_rejects_duplicate_page_webpart_and_teams_objects(self) -> None:
        cases = (
            (
                "SPFX_PAGE_WEBPART_DUPLICATE",
                lambda: setattr(
                    self.m365,
                    "page_detail",
                    {
                        "ListItemAllFields": {
                            "CanvasContent1": "<div>legacy</div>"
                        },
                        "canvasContentJson": json.dumps(
                            [
                                {"webPartId": WEB_PART_ID},
                                {"webPartId": WEB_PART_ID},
                            ]
                        )
                    },
                ),
            ),
            (
                "TEAMS_CATALOG_APP_DUPLICATE",
                lambda: setattr(
                    self.m365,
                    "teams_apps",
                    [
                        {"id": TEAMS_CATALOG_ID, "externalId": WEB_PART_ID},
                        {
                            "id": "88888888-8888-4888-8888-888888888888",
                            "externalId": WEB_PART_ID,
                        },
                    ],
                ),
            ),
            (
                "TEAMS_INSTALLATION_DUPLICATE",
                lambda: self.m365.installed_apps.update(
                    {
                        "value": [
                            {
                                "teamsApp": {
                                    "id": TEAMS_CATALOG_ID,
                                    "externalId": WEB_PART_ID,
                                }
                            },
                            {
                                "teamsApp": {
                                    "id": TEAMS_CATALOG_ID,
                                    "externalId": WEB_PART_ID,
                                }
                            },
                        ]
                    }
                ),
            ),
        )
        for expected_code, mutate in cases:
            with self.subTest(expected_code=expected_code):
                _complete_m365_state(self.m365)
                mutate()
                result = self._prewrite()
                self.assertEqual(result["code"], expected_code)
                self.assertFalse(
                    any(
                        command[:3] == ("deployment", "group", "create")
                        for command in self.azure.commands
                    )
                )

    def test_prewrite_prefers_structured_canvas_json_over_legacy_html(self) -> None:
        _complete_m365_state(self.m365)
        self.m365.page_detail = {
            "ListItemAllFields": {
                "CanvasContent1": "<div data-sp-canvascontrol></div>"
            },
            "canvasContentJson": json.dumps([{"webPartId": WEB_PART_ID}]),
        }
        self.assertEqual(self._prewrite()["status"], "PASSED")

    def test_prewrite_rejects_malformed_structured_canvas_json(self) -> None:
        _complete_m365_state(self.m365)
        self.m365.page_detail = {
            "CanvasContent1": json.dumps([{"webPartId": WEB_PART_ID}]),
            "canvasContentJson": "<div>not-json</div>",
        }
        self.assertEqual(
            self._prewrite()["code"], "SPFX_PAGE_WEBPART_STATE_INVALID"
        )

    def test_prewrite_rejects_non_list_structured_canvas_json(self) -> None:
        for canvas in (json.dumps({}), {}, {"webPartId": WEB_PART_ID}):
            with self.subTest(canvas=canvas):
                _complete_m365_state(self.m365)
                self.m365.page_detail = {
                    "CanvasContent1": json.dumps([{"webPartId": WEB_PART_ID}]),
                    "canvasContentJson": canvas,
                }
                self.assertEqual(
                    self._prewrite()["code"],
                    "SPFX_PAGE_WEBPART_STATE_INVALID",
                )

    def test_provider_registration_is_idempotent(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        reused = self.port.execute_step(STEPS[0], self.context)
        self.assertEqual(reused["classification"], "reused")
        self.assertFalse(
            any(
                command[:2] == ("provider", "register")
                for command in self.azure.commands
            )
        )

        self.azure.commands.clear()
        self.azure.providers["Microsoft.Storage"] = "NotRegistered"
        updated = self.port.execute_step(STEPS[0], self.context)
        self.assertEqual(updated["classification"], "updated")
        registrations = [
            command for command in self.azure.commands if command[:2] == ("provider", "register")
        ]
        self.assertEqual(len(registrations), 1)

    def test_resource_group_create_reuse_and_mismatch(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        reused = self.port.execute_step(STEPS[1], self.context)
        self.assertEqual(reused["classification"], "reused")

        self.azure.group = None
        self.port._resource_group_absent = True
        created = self.port.execute_step(STEPS[1], self.context)
        self.assertEqual(created["classification"], "created")

        self.azure.group = {"name": RESOURCE_GROUP, "location": "westeurope"}
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[1], self.context)
        self.assertEqual(raised.exception.code, "RESOURCE_GROUP_MISMATCH")

    def test_bicep_requires_and_validates_exact_outputs(self) -> None:
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[3], self.context)
        self.assertEqual(raised.exception.code, "API_APPLICATION_BINDING_MISSING")

        self.assertEqual(self._prewrite()["status"], "PASSED")
        result = self.port.execute_step(STEPS[3], self.context)
        self.assertEqual(result["verified_count"], 4)

        self.azure.deployment_outputs["functionAppHostName"] = {"value": "foreign.example"}
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[3], self.context)
        self.assertEqual(raised.exception.code, "BICEP_OUTPUT_MISMATCH")

    def test_spfx_scope_pending_approval_reuse_and_broader_duplicate_block(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._api = _binding()  # Bind state as established by step three.
        exact = {"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}
        self.m365.pending = [
            {
                "Id": PERMISSION_REQUEST_ID,
                "ResourceId": API_SERVICE_PRINCIPAL_ID,
                "Resource": "NaC M365 BFF",
                "Scope": DELEGATED_SCOPE,
            }
        ]

        self.m365.grant_snapshots = [[], [], [exact]]
        approved = self.port.execute_step(STEPS[8], self.context)
        self.assertEqual(approved["classification"], "updated")
        self.assertTrue(any("approve" in command for command in self.m365.commands))

        self.m365.commands.clear()
        self.m365.grant_snapshots = [[exact]]
        reused = self.port.execute_step(STEPS[8], self.context)
        self.assertEqual(reused["classification"], "reused")
        self.assertFalse(any("approve" in command for command in self.m365.commands))

        for grants in (
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": "Matter.ReadWrite"}],
            [exact, exact],
        ):
            with self.subTest(grants=grants):
                self.m365.grant_snapshots = [grants]
                with self.assertRaises(ActivationStepError) as raised:
                    self.port.execute_step(STEPS[8], self.context)
                self.assertEqual(raised.exception.code, "SPFX_BFF_GRANT_BROADER_OR_DUPLICATE")

        self.m365.commands.clear()
        self.m365.grant_snapshots = [[]]
        self.m365.pending = [
            {
                "Id": PERMISSION_REQUEST_ID,
                "ResourceId": API_SERVICE_PRINCIPAL_ID,
                "Resource": "Unexpected API",
                "Scope": DELEGATED_SCOPE,
            }
        ]
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[8], self.context)
        self.assertEqual(
            raised.exception.code, "SPFX_BFF_PERMISSION_REQUEST_UNEXPECTED"
        )
        self.assertFalse(any("approve" in command for command in self.m365.commands))

    def test_spfx_scope_readback_timeout_never_retries_write(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._api = _binding()
        self.m365.pending = [
            {
                "Id": PERMISSION_REQUEST_ID,
                "ResourceId": API_SERVICE_PRINCIPAL_ID,
                "Resource": "NaC M365 BFF",
                "Scope": DELEGATED_SCOPE,
            }
        ]
        self.m365.grant_snapshots = [[], [], [], []]
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[8], self.context)
        self.assertEqual(
            raised.exception.code, "SPFX_BFF_GRANT_READBACK_TIMEOUT"
        )
        writes = [
            command
            for command in self.m365.commands
            if "approve" in command
        ]
        self.assertEqual(len(writes), 1)

    def test_assigned_deputy_denied_restore_final_read_then_readyz(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._actor_id = ACTOR_ID
        result = self.port.execute_step(STEPS[10], self.context)
        self.assertEqual(result["verified_count"], 7)
        self.assertEqual(
            [call[1] for call in self.synthetic.calls if call[0] == "mode"],
            ["assigned", "deputy", "denied"],
        )
        restore_index = next(
            index
            for index, call in enumerate(self.synthetic.calls)
            if call[0] == "restore"
        )
        self.assertEqual(self.synthetic.mode, "assigned")
        bff_calls = [
            command
            for command in self.m365.commands
            if command[1] == "request" and "api://funktion8.de/nac-bff" in command
        ]
        self.assertEqual(len(bff_calls), 5)
        self.assertTrue(
            any("site_id=foreign" in " ".join(command) for command in bff_calls)
        )
        self.assertGreater(len(self.synthetic.calls), restore_index)
        self.assertEqual(
            self.http_readiness.calls,
            [
                (
                    "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                    200,
                ),
                (
                    "https://func-nac-bff-test-funktion8.azurewebsites.net/readyz",
                    200,
                )
            ],
        )

    def test_step_eleven_returns_explicit_verified_signals(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        result = self.port.execute_step(STEPS[10], self.context)
        self.assertIs(result["assigned_access_passed"], True)
        self.assertIs(result["deputy_access_passed"], True)
        self.assertIs(result["denied_access_passed"], True)
        self.assertIs(result["tampered_access_passed"], True)
        self.assertIs(result["healthz_before_auth_passed"], True)
        self.assertIs(result["authenticated_read_passed"], True)
        self.assertIs(
            result["readyz_after_authenticated_read_passed"],
            True,
        )
        self.assertIs(result["synthetic_state_restored"], True)

    def test_baseexception_still_restores_synthetic_state(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        with (
            patch.object(
                self.port,
                "_request_bff",
                side_effect=KeyboardInterrupt(),
            ),
            self.assertRaises(KeyboardInterrupt),
        ):
            self.port.execute_step(STEPS[10], self.context)
        self.assertEqual(self.synthetic.mode, "assigned")
        self.assertTrue(any(call[0] == "restore" for call in self.synthetic.calls))
        self.assertEqual(
            self.http_readiness.calls,
            [(
                "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                200,
            )],
        )

    def test_tampered_or_malformed_bff_response_fails_closed(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._actor_id = ACTOR_ID
        self.m365.allow_tampered = True
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[10], self.context)
        self.assertEqual(raised.exception.code, "BFF_DENY_SMOKE_FAILED")
        self.assertEqual(self.synthetic.mode, "assigned")
        self.assertEqual(
            self.http_readiness.calls,
            [(
                "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                200,
            )],
        )

        self.http_readiness.calls.clear()

        self.m365.allow_tampered = False
        self.m365.invalid_bff_payload = True
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[10], self.context)
        self.assertEqual(raised.exception.code, "BFF_RESPONSE_INVALID")
        self.assertEqual(self.synthetic.mode, "assigned")
        self.assertEqual(
            self.http_readiness.calls,
            [(
                "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                200,
            )],
        )

    def test_unstructured_403_is_rejected_and_never_reaches_readyz(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._actor_id = ACTOR_ID
        original = self.m365.run

        def unstructured(argv):
            command = tuple(argv)
            if command[1] == "request" and self.synthetic.mode == "denied":
                return SimpleNamespace(
                    returncode=1, stdout="", stderr="incidental 403 text"
                )
            return original(argv)

        with (
            patch.object(self.m365, "run", side_effect=unstructured),
            self.assertRaises(ActivationStepError) as raised,
        ):
            self.port.execute_step(STEPS[10], self.context)
        self.assertEqual(raised.exception.code, "BFF_DENY_RESPONSE_INVALID")
        self.assertEqual(self.synthetic.mode, "assigned")
        self.assertEqual(
            self.http_readiness.calls,
            [(
                "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                200,
            )],
        )

    def test_restoration_failure_stops_before_final_read_and_readyz(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._actor_id = ACTOR_ID
        with (
            patch.object(
                self.synthetic,
                "restore_assigned",
                side_effect=RuntimeError("restore failed"),
            ),
            self.assertRaises(ActivationStepError) as raised,
        ):
            self.port.execute_step(STEPS[10], self.context)
        self.assertEqual(
            raised.exception.code, "SYNTHETIC_STATE_RESTORATION_FAILED"
        )
        self.assertEqual(
            self.http_readiness.calls,
            [(
                "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                200,
            )],
        )
        bff_calls = [
            command
            for command in self.m365.commands
            if command[1] == "request" and "api://funktion8.de/nac-bff" in command
        ]
        self.assertEqual(len(bff_calls), 4)

    def test_step_twelve_reconciles_complete_lane_read_only_and_rejects_gap(
        self,
    ) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.azure.resources = _azure_resources()
        self.azure.deployment = _deployment_payload(self.azure.deployment_outputs)
        self.port._uami_app_id = UAMI_APP_ID
        self.port.execute_step(STEPS[3], self.context)
        self.port.execute_step(STEPS[6], self.context)
        with patch(
            "nac_bff.azure_activation_composition.run_spfx_site_deployment",
            return_value={
                "status": "PASSED",
                "steps": [{}, {}],
                "package": {"sha256": self.port._spfx_package_sha256},
            },
        ):
            self.port.execute_step(STEPS[7], self.context)
        _complete_m365_state(self.m365)
        self.m365.grant_snapshots = [
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}]
        ]
        azure_start = len(self.azure.commands)
        m365_start = len(self.m365.commands)

        patches = (
            patch(
                "nac_bff.azure_activation_composition."
                "inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_uami_sites_selected",
                return_value={"status": "present", "assignment_count": 1},
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_site_read_permission",
                return_value={"status": "present", "permission_count": 1},
            ),
        )
        with patches[0], patches[1], patches[2]:
            result = self.port.execute_step(STEPS[11], self.context)

        self.assertEqual(result["status"], "PASSED")
        self.assertEqual(result["verified_count"], 28)
        self.assertRegex(result["resource_reference_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(
            self.port._function_deployment_input_sha256,
            self.port._function_package_sha256,
        )
        self.assertEqual(
            self.port._spfx_deployment_input_sha256,
            self.port._spfx_package_sha256,
        )
        self.assertTrue(self.port._function_health_readback_passed)
        self.assertTrue(self.port._spfx_control_plane_evidence_verified)
        self.assertEqual(self.port._spfx_expected_version, "0.2.0")
        azure_reconcile = self.azure.commands[azure_start:]
        self.assertFalse(
            any(
                command[:2] == ("provider", "register")
                or command[:2] == ("group", "create")
                or command[:3] == ("deployment", "group", "create")
                or command[:4]
                == ("functionapp", "deployment", "source", "config-zip")
                for command in azure_reconcile
            )
        )
        m365_reconcile = self.m365.commands[m365_start:]
        self.assertFalse(
            any(
                command[1:4]
                in {
                    ("spo", "app", "add"),
                    ("spo", "app", "deploy"),
                    ("spo", "app", "install"),
                }
                or "approve" in command
                for command in m365_reconcile
            )
        )

        self.m365.page_detail = {"CanvasContent1": "[]"}
        with (
            patch(
                "nac_bff.azure_activation_composition."
                "inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_uami_sites_selected",
                return_value={"status": "present", "assignment_count": 1},
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_site_read_permission",
                return_value={"status": "present", "permission_count": 1},
            ),
            self.assertRaises(ActivationStepError) as raised,
        ):
            self.port.execute_step(STEPS[11], self.context)
        self.assertEqual(raised.exception.code, "M365_LANE_READBACK_INCOMPLETE")

    def test_step_twelve_fails_closed_on_deployment_and_resource_drift(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port.execute_step(STEPS[3], self.context)
        self.port.execute_step(STEPS[6], self.context)
        with patch(
            "nac_bff.azure_activation_composition.run_spfx_site_deployment",
            return_value={
                "status": "PASSED",
                "steps": [{}, {}],
                "package": {"sha256": self.port._spfx_package_sha256},
            },
        ):
            self.port.execute_step(STEPS[7], self.context)
        _complete_m365_state(self.m365)
        self.m365.grant_snapshots = [
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}]
        ]

        common_patches = (
            patch(
                "nac_bff.azure_activation_composition."
                "inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_uami_sites_selected",
                return_value={"status": "present", "assignment_count": 1},
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_site_read_permission",
                return_value={"status": "present", "permission_count": 1},
            ),
        )

        original_template_hash = self.azure.deployment["properties"]["templateHash"]
        self.azure.deployment["properties"]["templateHash"] = "drifted-template"
        with (
            common_patches[0],
            common_patches[1],
            common_patches[2],
            self.assertRaises(ActivationStepError) as raised,
        ):
            self.port.execute_step(STEPS[11], self.context)
        self.assertEqual(raised.exception.code, "AZURE_DEPLOYMENT_INPUT_DRIFT")
        self.azure.deployment["properties"]["templateHash"] = original_template_hash

        original_tags = dict(self.azure.resources[0]["tags"])
        self.azure.resources[0]["tags"]["managedBy"] = "manual"
        with (
            patch(
                "nac_bff.azure_activation_composition."
                "inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ),
            self.assertRaises(ActivationStepError) as raised,
        ):
            self.port.execute_step(STEPS[11], self.context)
        self.assertEqual(raised.exception.code, "AZURE_RESOURCE_PROPERTY_DRIFT")
        self.azure.resources[0]["tags"] = original_tags

    def test_spfx_deployment_rejects_mismatched_causal_input_digest(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.assertIsNone(self.port._spfx_deployment_input_sha256)
        self.assertFalse(self.port._spfx_control_plane_evidence_verified)
        with (
            patch(
                "nac_bff.azure_activation_composition.run_spfx_site_deployment",
                return_value={
                    "status": "PASSED",
                    "steps": [{}, {}],
                    "package": {"sha256": "f" * 64},
                },
            ),
            self.assertRaises(ActivationStepError) as raised,
        ):
            self.port.execute_step(STEPS[7], self.context)
        self.assertEqual(raised.exception.code, "SPFX_DEPLOYMENT_FAILED")
        self.assertIsNone(self.port._spfx_deployment_input_sha256)
        self.assertFalse(self.port._spfx_control_plane_evidence_verified)

    def test_step_twelve_rejects_spfx_provider_version_drift(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port.execute_step(STEPS[3], self.context)
        self.port.execute_step(STEPS[6], self.context)
        with patch(
            "nac_bff.azure_activation_composition.run_spfx_site_deployment",
            return_value={
                "status": "PASSED",
                "steps": [{}, {}],
                "package": {"sha256": self.port._spfx_package_sha256},
            },
        ):
            self.port.execute_step(STEPS[7], self.context)
        _complete_m365_state(self.m365)
        self.m365.teams_detail["appDefinitions"] = [
            {"version": "0.3.0", "publishingState": "published"}
        ]
        self.m365.grant_snapshots = [
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}]
        ]
        with (
            patch(
                "nac_bff.azure_activation_composition."
                "inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_uami_sites_selected",
                return_value={"status": "present", "assignment_count": 1},
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "_graph_activation.inspect_site_read_permission",
                return_value={"status": "present", "permission_count": 1},
            ),
            self.assertRaises(ActivationStepError) as raised,
        ):
            self.port.execute_step(STEPS[11], self.context)
        self.assertEqual(raised.exception.code, "TEAMS_CATALOG_VERSION_DRIFT")

    def test_step_twelve_requires_causal_package_and_manifest_bindings(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._deployed_prepared_inputs_sha256 = None
        self.port._function_deployment_input_sha256 = self.port._function_package_sha256
        self.port._spfx_deployment_input_sha256 = self.port._spfx_package_sha256
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[11], self.context)
        self.assertEqual(raised.exception.code, "DEPLOYED_INPUT_BINDING_MISSING")

    def test_all_twelve_handlers_execute_in_contract_order_with_fakes(self) -> None:
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.m365.pending = [
            {
                "Id": PERMISSION_REQUEST_ID,
                "ResourceId": API_SERVICE_PRINCIPAL_ID,
                "Resource": "NaC M365 BFF",
                "Scope": DELEGATED_SCOPE,
            }
        ]
        self.m365.grant_snapshots = [
            [],
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}],
        ]
        completed: list[str] = []

        def deploy_spfx(_plan, _runner, *, bound_artifacts=None):
            self.assertIsNotNone(bound_artifacts)
            _complete_m365_state(self.m365)
            return {
                "status": "PASSED",
                "steps": [{}, {}],
                "package": {"sha256": self.port._spfx_package_sha256},
            }

        with (
            patch(
                "nac_bff.azure_activation_composition.ensure_entra_api_application_binding",
                return_value=_binding(),
            ) as ensure_api,
            patch(
                "nac_bff.azure_activation_composition.ensure_uami_sites_selected",
                return_value={"status": "reused"},
            ) as ensure_sites_selected,
            patch(
                "nac_bff.azure_activation_composition.ensure_site_read_permission",
                return_value={"status": "reused"},
            ) as ensure_site_read,
            patch(
                "nac_bff.azure_activation_composition.inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ) as inspect_api,
            patch(
                "nac_bff.azure_activation_composition._graph_activation."
                "inspect_uami_sites_selected",
                return_value={"status": "present", "assignment_count": 1},
            ) as inspect_sites_selected,
            patch(
                "nac_bff.azure_activation_composition._graph_activation."
                "inspect_site_read_permission",
                return_value={"status": "present", "permission_count": 1},
            ) as inspect_site_read,
            patch(
                "nac_bff.azure_activation_composition.run_spfx_site_deployment",
                side_effect=deploy_spfx,
            ) as deploy_spfx_mock,
        ):
            for step in STEPS:
                result = self.port.execute_step(step, self.context)
                self.assertEqual(result["status"], "PASSED", step)
                completed.append(step)

        self.assertEqual(tuple(completed), STEPS)
        self.assertEqual(
            self.http_readiness.calls,
            [
                (
                    "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                    200,
                ),
                (
                    "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                    200,
                ),
                (
                    "https://func-nac-bff-test-funktion8.azurewebsites.net/readyz",
                    200,
                ),
                (
                    "https://func-nac-bff-test-funktion8.azurewebsites.net/healthz",
                    200,
                ),
            ],
        )
        self.assertEqual(ensure_api.call_count, 1)
        self.assertEqual(ensure_sites_selected.call_count, 1)
        self.assertEqual(ensure_site_read.call_count, 1)
        inspect_api.assert_called_once()
        inspect_sites_selected.assert_called_once()
        inspect_site_read.assert_called_once()
        deploy_spfx_mock.assert_called_once()
        self.assertEqual(self.synthetic.calls[-1][0], "idempotency")
        self.assertEqual(self.synthetic.mode, "assigned")

    def test_runner_adopts_all_twelve_real_composition_step_outputs(self) -> None:
        self.m365.grant_snapshots = [
            [],
            [],
            [{"resourceId": API_SERVICE_PRINCIPAL_ID, "scope": DELEGATED_SCOPE}],
        ]
        plan = _plan()
        permission_boundary_sha256 = "6" * 64
        lock_root = self.repo_root / ".test-live-locks"

        def deploy_spfx(_plan, _runner, *, bound_artifacts=None):
            self.assertIsNotNone(bound_artifacts)
            _complete_m365_state(self.m365)
            self.m365.pending = [
                {
                    "Id": PERMISSION_REQUEST_ID,
                    "ResourceId": API_SERVICE_PRINCIPAL_ID,
                    "Resource": "NaC M365 BFF",
                    "Scope": DELEGATED_SCOPE,
                }
            ]
            return {
                "status": "PASSED",
                "steps": [{}, {}],
                "package": {"sha256": self.port._spfx_package_sha256},
            }

        with (
            patch(
                "nac_bff.azure_activation_runner.build_azure_bff_activation_plan",
                return_value=plan,
            ),
            patch(
                "nac_bff.azure_activation_runner._permission_boundary_hash",
                return_value=permission_boundary_sha256,
            ),
            patch(
                "nac_bff.azure_activation_runner._clean_tree",
                return_value=True,
            ),
            patch(
                "nac_bff.azure_activation_runner._head_commit",
                return_value=COMMIT,
            ),
            patch(
                "nac_bff.azure_activation_runner._head_tree",
                return_value=TREE,
            ),
            patch(
                "nac_bff.azure_activation_runner._HOST_LOCK_ROOT",
                lock_root,
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "build_azure_bff_activation_plan",
                return_value=plan,
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "inspect_entra_api_application_prewrite",
                return_value=_binding(),
            ) as inspect_api,
            patch(
                "nac_bff.azure_activation_composition."
                "build_spfx_site_deployment_plan",
                return_value={"status": "READY", "prepared": True},
            ),
            patch(
                "nac_bff.azure_activation_composition."
                "ensure_entra_api_application_binding",
                return_value=_binding(),
            ) as ensure_api,
            patch(
                "nac_bff.azure_activation_composition.ensure_uami_sites_selected",
                return_value={"status": "reused"},
            ) as ensure_sites_selected,
            patch(
                "nac_bff.azure_activation_composition.ensure_site_read_permission",
                return_value={"status": "reused"},
            ) as ensure_site_read,
            patch(
                "nac_bff.azure_activation_composition._graph_activation."
                "inspect_uami_sites_selected",
                return_value={"status": "present", "assignment_count": 1},
            ) as inspect_sites_selected,
            patch(
                "nac_bff.azure_activation_composition._graph_activation."
                "inspect_site_read_permission",
                return_value={"status": "present", "permission_count": 1},
            ) as inspect_site_read,
            patch(
                "nac_bff.azure_activation_composition.run_spfx_site_deployment",
                side_effect=deploy_spfx,
            ) as deploy_spfx_mock,
            patch.object(
                self.port,
                "execute_step",
                wraps=self.port.execute_step,
            ) as execute_step,
        ):
            result = run_azure_bff_live_activation(
                repo_root=self.repo_root,
                request=_request(),
                execution_port=self.port,
                output_root=self.repo_root / DEFAULT_OUTPUT_ROOT,
                now=lambda: datetime(
                    2026, 7, 14, 12, 0, tzinfo=timezone.utc
                ),
            )

        run_dir = self.repo_root / DEFAULT_OUTPUT_ROOT / ACTIVATION_HASH
        evidence_path = run_dir / "activation.redacted.json"
        receipt_paths = list(
            (lock_root / "success-receipts").glob(
                "*.success.redacted.json"
            )
        )
        self.assertEqual(result["status"], "PASSED", result)
        step_eleven = result["step_results"][10]
        signals = {
            "assigned_access_passed": True,
            "deputy_access_passed": True,
            "denied_access_passed": True,
            "tampered_access_passed": True,
            "healthz_before_auth_passed": True,
            "authenticated_read_passed": True,
            "readyz_after_authenticated_read_passed": True,
            "synthetic_state_restored": True,
        }

        self.assertEqual(len(result["step_results"]), 12)
        self.assertEqual(
            [item["id"] for item in result["step_results"]],
            list(STEPS),
        )
        self.assertTrue(
            all(item["status"] == "PASSED" for item in result["step_results"])
        )
        self.assertEqual(
            [call.args[0] for call in execute_step.call_args_list],
            list(STEPS),
        )
        self.assertTrue(evidence_path.is_file())
        self.assertEqual(json.loads(evidence_path.read_text()), result)
        self.assertEqual(len(receipt_paths), 1)
        self.assertEqual(
            json.loads(receipt_paths[0].read_text())["status"],
            "COMMITTED",
        )
        self.assertEqual(
            step_eleven["id"],
            "run_access_and_readback_smokes",
        )
        self.assertEqual(
            step_eleven["response_sha256"],
            _runner_sha256_json(
                {
                    "provider_response_sha256": None,
                    "verified_access_probe_signals": signals,
                }
            ),
        )
        for signal in (
            "healthz_before_auth_passed",
            "authenticated_read_passed",
            "readyz_after_authenticated_read_passed",
            "synthetic_state_restored",
        ):
            self.assertIs(result["summary"][signal], True)
        self.assertEqual(ensure_api.call_count, 1)
        self.assertEqual(ensure_sites_selected.call_count, 1)
        self.assertEqual(ensure_site_read.call_count, 1)
        self.assertEqual(inspect_api.call_count, 2)
        inspect_sites_selected.assert_called_once()
        inspect_site_read.assert_called_once()
        deploy_spfx_mock.assert_called_once()
        self.assertEqual(self.synthetic.calls[-1][0], "idempotency")
        self.assertEqual(self.synthetic.mode, "assigned")

    def test_azure_and_m365_failures_are_stable_and_redacted(self) -> None:
        secret = "Bearer secret-token-sentinel"
        self.azure.failure = {
            "ok": False,
            "code": f"AZURE_{secret}",
            "data": {"stderr": secret},
        }
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[0], self.context)
        self.assertEqual(raised.exception.code, "STEP_FAILED")
        self.assertNotIn(secret, raised.exception.code)

        self.azure.failure = None
        self.assertEqual(self._prewrite()["status"], "PASSED")
        self.port._api = _binding()
        self.m365.command_failure = (1, secret, secret)
        with self.assertRaises(ActivationStepError) as raised:
            self.port.execute_step(STEPS[8], self.context)
        self.assertEqual(raised.exception.code, "M365_COMMAND_FAILED")
        self.assertNotIn(secret, str(raised.exception))

    def _provisioner_certificate_environment(self) -> tuple[dict[str, str], str]:
        credential_dir = self.repo_root / "credentials"
        credential_dir.mkdir(mode=0o700)
        certificate = credential_dir / "cert.pem"
        private_key = credential_dir / "key.pem"
        certificate.write_bytes(b"test-public-certificate")
        private_key.write_bytes(b"test-private-key")
        certificate.chmod(0o644)
        private_key.chmod(0o600)
        return (
            {
                "M365_TENANT_ID": TENANT_ID,
                "M365_PROVISIONER_CLIENT_ID": PROVISIONER_CLIENT_ID,
                "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH": str(certificate),
                "M365_PROVISIONER_CLIENT_KEY_PATH": str(private_key),
            },
            hashlib.sha256(certificate.read_bytes()).hexdigest(),
        )

    def test_provisioner_identity_requires_exact_certificate_app(self) -> None:
        environ, certificate_sha256 = self._provisioner_certificate_environment()
        provider = _bound_provisioner_token_provider(
            environ, expected_certificate_sha256=certificate_sha256
        )
        self.assertIsInstance(
            provider, CertificateClientCredentialsTokenProvider
        )
        self.assertEqual(provider.config.client_id, PROVISIONER_CLIENT_ID)

    def test_provisioner_identity_rejects_unbound_certificate_or_unsafe_key(
        self,
    ) -> None:
        environ, certificate_sha256 = self._provisioner_certificate_environment()
        with self.assertRaises(GraphConfigError) as wrong_certificate:
            _bound_provisioner_token_provider(
                environ, expected_certificate_sha256="9" * 64
            )
        self.assertEqual(
            str(wrong_certificate.exception),
            "PROVISIONER_CERTIFICATE_FILE_UNTRUSTED",
        )

        Path(environ["M365_PROVISIONER_CLIENT_KEY_PATH"]).chmod(0o644)
        with self.assertRaises(GraphConfigError) as unsafe_key:
            _bound_provisioner_token_provider(
                environ, expected_certificate_sha256=certificate_sha256
            )
        self.assertEqual(
            str(unsafe_key.exception), "PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED"
        )

    def test_provisioner_rechecks_credential_files_before_each_token_fetch(
        self,
    ) -> None:
        environ, certificate_sha256 = self._provisioner_certificate_environment()
        provider = _bound_provisioner_token_provider(
            environ, expected_certificate_sha256=certificate_sha256
        )
        Path(environ["M365_PROVISIONER_CLIENT_KEY_PATH"]).chmod(0o644)
        with self.assertRaises(GraphConfigError) as raised:
            provider.fetch_access_token()
        self.assertEqual(
            str(raised.exception), "PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED"
        )

    def test_provisioner_uses_descriptor_bytes_without_reopening_paths(self) -> None:
        environ, certificate_sha256 = self._provisioner_certificate_environment()
        certificate_path = Path(
            environ["M365_PROVISIONER_CLIENT_CERTIFICATE_PATH"]
        )
        private_key_path = Path(environ["M365_PROVISIONER_CLIENT_KEY_PATH"])
        original_certificate = certificate_path.read_bytes()
        original_private_key = private_key_path.read_bytes()
        provider = _bound_provisioner_token_provider(
            environ, expected_certificate_sha256=certificate_sha256
        )
        captured: dict[str, bytes] = {}

        def build_assertion(
            _config,
            _endpoint,
            *,
            certificate_bytes,
            private_key_bytes,
        ):
            captured["certificate"] = certificate_bytes
            captured["private_key"] = private_key_bytes
            certificate_path.write_bytes(b"replacement-certificate")
            private_key_path.write_bytes(b"replacement-private-key")
            return "signed.jwt"

        with (
            patch(
                "nac_bff.azure_activation_composition."
                "_build_client_assertion_from_bytes",
                side_effect=build_assertion,
            ),
            patch(
                "nac_bff.azure_activation_composition._post_token_form",
                return_value="graph-token",
            ) as post_token,
            patch.object(
                Path,
                "read_bytes",
                side_effect=AssertionError("credential path reopened"),
            ),
        ):
            token = provider.fetch_access_token()

        self.assertEqual(token, "graph-token")
        self.assertEqual(captured["certificate"], original_certificate)
        self.assertEqual(captured["private_key"], original_private_key)
        self.assertEqual(
            post_token.call_args.args[1]["client_assertion"], "signed.jwt"
        )

    def test_provisioner_rejects_symlink_swap_before_descriptor_open(self) -> None:
        environ, certificate_sha256 = self._provisioner_certificate_environment()
        certificate_path = Path(
            environ["M365_PROVISIONER_CLIENT_CERTIFICATE_PATH"]
        )
        original_path = certificate_path.with_name("original-cert.pem")
        provider = _bound_provisioner_token_provider(
            environ, expected_certificate_sha256=certificate_sha256
        )
        certificate_path.rename(original_path)
        certificate_path.symlink_to(original_path)

        with (
            patch(
                "nac_bff.azure_activation_composition."
                "_build_client_assertion_from_bytes"
            ) as build_assertion,
            self.assertRaises(GraphConfigError) as raised,
        ):
            provider.fetch_access_token()

        self.assertEqual(
            str(raised.exception), "PROVISIONER_CERTIFICATE_FILE_UNTRUSTED"
        )
        build_assertion.assert_not_called()

    def test_provisioner_identity_rejects_wrong_app_and_static_token(self) -> None:
        with self.assertRaises(GraphConfigError) as wrong_app:
            _bound_provisioner_token_provider(
                {
                    "M365_TENANT_ID": TENANT_ID,
                    "M365_PROVISIONER_CLIENT_ID": "11111111-1111-4111-8111-111111111111",
                    "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH": "/tmp/cert.pem",
                    "M365_PROVISIONER_CLIENT_KEY_PATH": "/tmp/key.pem",
                },
                expected_certificate_sha256="1" * 64,
            )
        self.assertEqual(str(wrong_app.exception), "PROVISIONER_IDENTITY_MISMATCH")

        with self.assertRaises(GraphConfigError) as static_token:
            _bound_provisioner_token_provider(
                {
                    "M365_TENANT_ID": TENANT_ID,
                    "M365_PROVISIONER_CLIENT_ID": PROVISIONER_CLIENT_ID,
                    "M365_GRAPH_ACCESS_TOKEN": "not-read-or-emitted",
                },
                expected_certificate_sha256="1" * 64,
            )
        self.assertEqual(
            str(static_token.exception), "PROVISIONER_CERTIFICATE_MODE_REQUIRED"
        )

    def test_live_factory_uses_exact_attested_execution_paths(self) -> None:
        request = SimpleNamespace(
            azure_cli_toolchain_sha256=AZURE_CLI_TOOLCHAIN_SHA256,
            m365_cli_sha256=M365_CLI_SHA256,
            m365_node_sha256=M365_NODE_SHA256,
            build_python_sha256=BUILD_PYTHON_SHA256,
            build_node_sha256=BUILD_NODE_SHA256,
            build_npm_cli_sha256=BUILD_NPM_CLI_SHA256,
            gh_cli_sha256=GH_CLI_SHA256,
            provisioner_certificate_sha256=PROVISIONER_CERTIFICATE_SHA256,
        )
        with (
            patch(
                "nac_bff.azure_activation_composition."
                "_bound_provisioner_token_provider",
                return_value=object(),
            ),
            patch(
                "nac_bff.azure_activation_composition.GraphRestClient",
                return_value=object(),
            ),
            patch(
                "nac_bff.azure_activation_composition.M365CliCommandRunner"
            ) as m365,
            patch(
                "nac_bff.azure_activation_composition.AzureCliAdapter"
            ) as azure,
            patch(
                "nac_bff.azure_activation_composition.GitHubApprovalVerifier"
            ) as github,
            patch(
                "nac_bff.azure_activation_composition.LocalBuildAdapter"
            ) as local_build,
            patch(
                "nac_bff.azure_activation_composition.HttpReadinessAdapter"
            ),
            patch(
                "nac_bff.azure_activation_composition.LiveSyntheticWorkspaceManager"
            ),
        ):
            build_live_activation_execution_port(Path("/repo"), request)

        self.assertEqual(m365.call_args.kwargs["binary"], M365_CLI_EXECUTION_PATH)
        self.assertEqual(
            m365.call_args.kwargs["node_bin"], M365_NODE_EXECUTION_PATH.parent
        )
        self.assertEqual(azure.call_args.kwargs["binary"], AZURE_CLI_EXECUTION_PATH)
        self.assertEqual(github.call_args.kwargs["binary"], GH_CLI_EXECUTION_PATH)
        self.assertEqual(
            local_build.call_args.kwargs["python_binary"],
            BUILD_PYTHON_EXECUTION_PATH,
        )
        self.assertEqual(
            local_build.call_args.kwargs["node_binary"],
            BUILD_NODE_EXECUTION_PATH,
        )
        self.assertEqual(
            local_build.call_args.kwargs["npm_cli"],
            BUILD_NPM_CLI_EXECUTION_PATH,
        )

    def test_live_factory_is_not_used_by_isolated_composition_tests(self) -> None:
        with patch(
            "nac_bff.azure_activation_composition.build_live_activation_execution_port",
            side_effect=AssertionError("live factory must not be called"),
        ) as factory:
            with self.assertRaises(ActivationStepError) as raised:
                self.port.execute_step("not_allowlisted", self.context)
        self.assertEqual(raised.exception.code, "STEP_NOT_ALLOWLISTED")
        factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
