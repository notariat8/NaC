from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence

from nac_mvp_test_environment import evaluate_synthetic_access_policy

from .mcp_runtime import DEFAULT_MCP_CONTRACT, load_mcp_contract
from .mvp_test_environment_binding import (
    MvpTestEnvironmentBindingError,
    validate_mvp_test_environment_binding,
)
from .mvp_test_environment_smoke import (
    DEFAULT_MVP_TEST_ENVIRONMENT_FIXTURE,
    EXPECTED_WORKSPACE_ID,
    run_mvp_test_environment_smoke_from_paths,
)
from .privileged_change import DEFAULT_PROVISIONED_STATE, load_provisioned_state
from .spfx_site_deployment import (
    ControlPlaneCommandRunner,
    DeploymentPlanError,
    build_spfx_site_deployment_plan,
    run_spfx_site_deployment,
)


DEFAULT_MVP_TEST_ENVIRONMENT_DEPLOY_OUTPUT = Path(
    "out/m365/teams-sharepoint/mvp-test-environment-deploy.redacted.json"
)
SYNTHETIC_ACCESS_DECISION_SOURCE = "deterministic_data_field_policy_evaluator"
EXPECTED_M365_TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
_CONTROL_PLANE_ENV_KEYS = {
    "HOME",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "LANG",
    "NODE_EXTRA_CA_CERTS",
    "NODE_OPTIONS",
    "NO_PROXY",
    "PATH",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "TEMP",
    "TMP",
    "TMPDIR",
    "TZ",
    "XDG_CONFIG_HOME",
    "http_proxy",
    "https_proxy",
    "no_proxy",
}


@dataclass(frozen=True)
class SubprocessCommandResult:
    returncode: int
    stdout: str
    stderr: str


class M365CliReadinessError(RuntimeError):
    """Raised before control-plane writes when no usable local M365 CLI is available."""


class ReadyControlPlaneCommandRunner(ControlPlaneCommandRunner, Protocol):
    """Control-plane runner that proves its authenticated tenant before writes."""

    def check_readiness(self) -> bool: ...


class M365CliCommandRunner:
    """Run allowlisted M365 argv with an explicitly resolved local CLI session."""

    _BINARY_ENV = "NAC_M365_CLI_BINARY"
    _HOME_ENV = "NAC_M365_CLI_HOME"
    _NODE_BIN_ENV = "NAC_M365_NODE_BIN"
    _LOCAL_BINARY = Path("/tmp/nac-m365-tools/m365-cli/bin/m365")
    _LOCAL_HOME = Path("/tmp/nac-m365-tools/home")

    def __init__(
        self,
        *,
        binary: Path | str | None = None,
        home: Path | str | None = None,
        node_bin: Path | str | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        source_values = dict(os.environ if environ is None else environ)
        self.binary = self._resolve_binary(binary, source_values)
        resolved_home = self._resolve_home(home, source_values)
        resolved_node_bin = self._resolve_node_bin(node_bin, source_values)
        values = _control_plane_environment(source_values)

        path_parts = [str(self.binary.parent)]
        if resolved_node_bin is not None:
            path_parts.insert(0, str(resolved_node_bin))
        existing_path = values.get("PATH", "")
        if existing_path:
            path_parts.append(existing_path)
        values["PATH"] = os.pathsep.join(path_parts)
        if resolved_home is not None:
            values["HOME"] = str(resolved_home)
        self._env = values

    def run(self, argv: Sequence[str]) -> SubprocessCommandResult:
        command = list(argv)
        if not command or command[0] != "m365":
            raise M365CliReadinessError("M365 runner accepts only logical m365 argv")
        command[0] = str(self.binary)
        result = subprocess.run(
            command,
            shell=False,
            text=True,
            capture_output=True,
            check=False,
            env=self._env,
        )
        return SubprocessCommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def check_readiness(self) -> bool:
        result = self.run(("m365", "status", "--output", "json"))
        if result.returncode != 0:
            return False
        try:
            payload = json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError):
            return False
        if not isinstance(payload, dict):
            return False
        connected_as = payload.get("connectedAs")
        tenant_id = payload.get("appTenant")
        cloud_type = payload.get("cloudType")
        return (
            isinstance(connected_as, str)
            and bool(connected_as.strip())
            and isinstance(tenant_id, str)
            and tenant_id.strip().lower() == EXPECTED_M365_TENANT_ID
            and cloud_type == "Public"
        )

    @classmethod
    def _resolve_binary(
        cls,
        explicit: Path | str | None,
        values: dict[str, str],
    ) -> Path:
        configured = explicit or values.get(cls._BINARY_ENV)
        if configured:
            candidate = Path(configured).expanduser()
            if not candidate.is_absolute():
                discovered = shutil.which(str(candidate), path=values.get("PATH"))
                candidate = Path(discovered) if discovered else candidate
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate.resolve()
            raise M365CliReadinessError("configured M365 CLI binary is unavailable")

        discovered = shutil.which("m365", path=values.get("PATH"))
        if discovered:
            return Path(discovered).resolve()
        if cls._LOCAL_BINARY.is_file() and os.access(cls._LOCAL_BINARY, os.X_OK):
            return cls._LOCAL_BINARY.resolve()
        raise M365CliReadinessError("M365 CLI binary was not discovered")

    @classmethod
    def _resolve_home(
        cls,
        explicit: Path | str | None,
        values: dict[str, str],
    ) -> Path | None:
        configured = explicit or values.get(cls._HOME_ENV)
        if configured:
            candidate = Path(configured).expanduser()
            if not candidate.is_dir():
                raise M365CliReadinessError("configured M365 CLI home is unavailable")
            return candidate.resolve()
        if cls._LOCAL_HOME.is_dir():
            return cls._LOCAL_HOME.resolve()
        return None

    @classmethod
    def _resolve_node_bin(
        cls,
        explicit: Path | str | None,
        values: dict[str, str],
    ) -> Path | None:
        configured = explicit or values.get(cls._NODE_BIN_ENV)
        if configured:
            candidate = Path(configured).expanduser()
            node = candidate / "node"
            if not node.is_file() or not os.access(node, os.X_OK):
                raise M365CliReadinessError("configured Node bin directory is unavailable")
            return candidate.resolve()

        discovered = shutil.which("node", path=values.get("PATH"))
        if discovered:
            return Path(discovered).resolve().parent
        candidates = sorted(Path("/tmp").glob("node-v*-linux-x64/bin"), reverse=True)
        for candidate in candidates:
            node = candidate / "node"
            if node.is_file() and os.access(node, os.X_OK):
                return candidate.resolve()
        return None


def synthetic_access_decision_fixture(request: dict[str, str]) -> dict[str, str]:
    """Evaluate the canonical synthetic assignment/deputy policy from data fields."""

    return evaluate_synthetic_access_policy(request)


def run_mvp_test_environment_deploy(
    graph_client: Any,
    *,
    repo_root: Path,
    workspace_id: str,
    owner_approved: bool,
    expected_package_sha256: str | None = None,
    include_teams: bool = False,
    correlation_id: str = "mvp-test-environment-deploy",
    provisioned_state_path: Path = DEFAULT_PROVISIONED_STATE,
    contract_path: Path = DEFAULT_MCP_CONTRACT,
    fixture_path: Path = DEFAULT_MVP_TEST_ENVIRONMENT_FIXTURE,
    command_runner: ReadyControlPlaneCommandRunner | None = None,
) -> dict[str, Any]:
    generated_scope = {
        "workspaceRefSha256": _sha256_text(workspace_id),
        "workspaceVerified": workspace_id == EXPECTED_WORKSPACE_ID,
    }
    result: dict[str, Any] = {
        "schemaVersion": "nac.m365-mvp-test-environment-deploy-evidence/v0.1",
        "status": "BLOCKED",
        "scope": generated_scope,
        "ownerGate": {"approved": owner_approved is True},
        "inputBinding": {"status": "NOT_RUN"},
        "controlPlane": {"status": "NOT_RUN"},
        "syntheticDataSmoke": {"status": "NOT_RUN"},
        "accessDecisionVerification": {
            "source": SYNTHETIC_ACCESS_DECISION_SOURCE,
            "liveBffDecision": False,
            "liveEntraBffActivation": "DEFERRED",
            "deferredReason": "requires_new_delegated_scope_and_public_https_endpoint",
            "failClosed": True,
            "policyRequirements": [
                "primary_assignment",
                "deputy_reason",
                "deputy_validity_window",
                "deputy_approval",
                "deputy_audit_event",
            ],
            "expected": {"assigned": "ALLOW", "deputy": "ALLOW", "deny": "DENY"},
        },
        "boundaries": {
            "graphApi": "https://graph.microsoft.com/v1.0",
            "syntheticDataOnly": True,
            "permissionChanges": False,
            "credentialChanges": False,
            "destructiveRollback": False,
            "cleanupRequired": True,
        },
    }

    if workspace_id != EXPECTED_WORKSPACE_ID:
        result["error"] = {"code": "WORKSPACE_SCOPE_REJECTED"}
        return result
    if owner_approved is not True:
        result["error"] = {"code": "OWNER_GATE_CLOSED"}
        return result
    if not expected_package_sha256:
        result["error"] = {"code": "PACKAGE_HASH_BINDING_REQUIRED"}
        return result

    try:
        contract = load_mcp_contract(contract_path)
        provisioned_state = load_provisioned_state(provisioned_state_path)
        binding = validate_mvp_test_environment_binding(contract, provisioned_state)
    except (MvpTestEnvironmentBindingError, OSError, ValueError, TypeError):
        result["status"] = "FAILED"
        result["inputBinding"] = {
            "status": "FAILED",
            "error": {"code": "MVP_INPUT_BINDING_INVALID"},
        }
        result["error"] = {"code": "MVP_INPUT_BINDING_INVALID"}
        return result
    result["inputBinding"] = {
        "status": "PASSED",
        **binding,
        "rawResourceIdentifiersIncluded": False,
        "controlPlanePlanBound": False,
    }

    try:
        plan = build_spfx_site_deployment_plan(
            repo_root=repo_root,
            workspace_id=workspace_id,
            include_teams=include_teams,
            expected_package_sha256=expected_package_sha256,
        )
        _validate_control_plane_plan_binding(plan, provisioned_state)
        result["inputBinding"]["controlPlanePlanBound"] = True
    except (DeploymentPlanError, OSError, ValueError) as exc:
        result["status"] = "FAILED"
        code = (
            "SPFX_PACKAGE_NOT_BUILT"
            if isinstance(exc, DeploymentPlanError) and "package is missing" in str(exc).lower()
            else "DEPLOYMENT_PLAN_INVALID"
        )
        result["controlPlane"] = {
            "status": "FAILED",
            "error": {"code": code},
        }
        return result

    try:
        runner = command_runner or M365CliCommandRunner()
        readiness_check = getattr(runner, "check_readiness", None)
        cli_ready = callable(readiness_check) and readiness_check() is True
    except (M365CliReadinessError, OSError, RuntimeError, TypeError, ValueError):
        cli_ready = False
    if not cli_ready:
        result["status"] = "FAILED"
        result["controlPlane"] = {
            "status": "FAILED",
            "error": {"code": "M365_CLI_SESSION_NOT_READY"},
        }
        return result

    deployment = run_spfx_site_deployment(plan, runner)
    result["controlPlane"] = _deployment_summary(deployment, plan.package_sha256, include_teams)
    if deployment.get("status") != "PASSED":
        result["status"] = "FAILED"
        result["error"] = {"code": "CONTROL_PLANE_DEPLOYMENT_FAILED"}
        return result

    smoke = run_mvp_test_environment_smoke_from_paths(
        graph_client,
        synthetic_access_decision_fixture,
        workspace_id=workspace_id,
        owner_approved=owner_approved,
        contract_path=contract_path,
        provisioned_state_path=provisioned_state_path,
        fixture_path=fixture_path,
        correlation_id=correlation_id,
    )
    result["syntheticDataSmoke"] = smoke
    role_checks = smoke.get("roleChecks") if isinstance(smoke, dict) else None
    role_policy_verified = (
        isinstance(role_checks, list)
        and len(role_checks) == 3
        and [check.get("actual") for check in role_checks if isinstance(check, dict)]
        == ["ALLOW", "ALLOW", "DENY"]
        and all(check.get("passed") is True for check in role_checks if isinstance(check, dict))
    )
    result["accessDecisionVerification"]["status"] = (
        "PASSED" if role_policy_verified else "FAILED"
    )
    result["accessDecisionVerification"]["checks"] = role_checks if isinstance(role_checks, list) else []
    result["status"] = (
        "PASSED"
        if smoke.get("status") == "PASSED" and role_policy_verified
        else "FAILED"
    )
    if result["status"] != "PASSED":
        result["error"] = {
            "code": (
                "ACCESS_DECISION_EVIDENCE_FAILED"
                if smoke.get("status") == "PASSED" and not role_policy_verified
                else "SYNTHETIC_DATA_SMOKE_FAILED"
            )
        }
    return result


def write_mvp_test_environment_deploy_artifact(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _deployment_summary(
    evidence: dict[str, Any], package_sha256: str, include_teams: bool
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "status": evidence.get("status", "FAILED"),
        "packageSha256": package_sha256,
        "siteScoped": True,
        "teamsIncluded": include_teams,
        "commandsExecuted": evidence.get("commands_executed", 0),
        "classifications": evidence.get("classifications", {}),
        "rawCommandOutputIncluded": False,
    }
    steps = evidence.get("steps")
    if isinstance(steps, list):
        summary["steps"] = steps
    return summary


def _validate_control_plane_plan_binding(
    plan: Any,
    provisioned_state: dict[str, Any],
) -> None:
    workspaces = provisioned_state.get("workspaces")
    matches = (
        [
            workspace
            for workspace in workspaces
            if isinstance(workspace, dict)
            and workspace.get("id") == EXPECTED_WORKSPACE_ID
        ]
        if isinstance(workspaces, list)
        else []
    )
    if len(matches) != 1:
        raise DeploymentPlanError("workspace binding is unavailable")
    workspace = matches[0]
    if (
        getattr(plan, "workspace_id", None) != EXPECTED_WORKSPACE_ID
        or getattr(plan, "site_url", None) != workspace.get("site_url")
        or getattr(plan, "team_id", None) != workspace.get("team_id")
    ):
        raise DeploymentPlanError("control-plane plan resource binding mismatch")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _control_plane_environment(values: dict[str, str]) -> dict[str, str]:
    """Return only non-credential process settings needed by Node and M365 CLI."""

    return {
        key: value
        for key, value in values.items()
        if key in _CONTROL_PLANE_ENV_KEYS or key.startswith("LC_")
    }
