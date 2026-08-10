from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

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
from .node_runtime_integrity import (
    MANIFEST_ENV,
    NodeRuntimeIntegrityError,
    build_node_runtime_integrity_payloads,
)
from .sealed_toolchain import (
    SealedToolchainError,
    sealed_artifacts,
    sealed_payloads,
    sealed_toolchain,
)
from .spfx_site_deployment import (
    APP_CATALOG_SCOPE,
    ControlPlaneCommandRunner,
    DeploymentPlanError,
    INITIAL_PAGE_CONTENT,
    PACKAGE_NAME,
    PAGE_LAYOUT,
    PAGE_NAME,
    PAGE_TITLE,
    SITE_URL,
    TEAM_ID,
    WEB_PART_ID,
    build_spfx_site_deployment_plan,
    run_spfx_site_deployment,
)


DEFAULT_MVP_TEST_ENVIRONMENT_DEPLOY_OUTPUT = Path(
    "out/m365/teams-sharepoint/mvp-test-environment-deploy.redacted.json"
)
SYNTHETIC_ACCESS_DECISION_SOURCE = "deterministic_data_field_policy_evaluator"
EXPECTED_M365_TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
_CONTROL_PLANE_ENV_KEYS = {
    "LANG",
    "TZ",
}
_SHA256_HEX_LENGTH = 64
_DEFAULT_M365_CLI_TIMEOUT_SECONDS = 60.0
_MAX_M365_CLI_TIMEOUT_SECONDS = 300.0
_SAFE_NONZERO_MARKERS = (
    "no upgrade",
    "already up to date",
    "does not have an upgrade",
)
EXPECTED_M365_CLI_USER = "ofunk@funktion8.de"
EXPECTED_M365_CLI_APP_ID = "c86dded6-9723-4b8d-91f2-e0fd70e25839"
EXPECTED_M365_CLI_PROVISIONER_APP_ID = "6845f6c3-896c-4e44-a50f-2a5086a13fac"
EXPECTED_M365_CLI_PROVISIONER_USER = "NaC M365 Provisioning"
_EXPECTED_GRAPH_RESOURCE = "https://graph.microsoft.com"
_EXPECTED_API_RESOURCE = "api://funktion8.de/nac-bff"
_EXPECTED_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me?$select=id"
_EXPECTED_BFF_URL = (
    "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/"
    "notary_team_01/matters/NAC-SYN-MATTER-001"
    "?purpose=view_synthetic_matter_workspace"
)
_EXPECTED_BFF_TAMPERED_URLS = (
    _EXPECTED_BFF_URL.replace(
        "/workspaces/notary_team_01/", "/workspaces/foreign_workspace/"
    ),
    _EXPECTED_BFF_URL.replace(
        "/matters/NAC-SYN-MATTER-001", "/matters/NAC-SYN-MATTER-FOREIGN"
    ),
    _EXPECTED_BFF_URL.replace(
        "purpose=view_synthetic_matter_workspace", "purpose=foreign"
    ),
    f"{_EXPECTED_BFF_URL}&site_id=foreign",
)
_EXPECTED_BFF_ALLOWED_URLS = frozenset(
    (_EXPECTED_BFF_URL, *_EXPECTED_BFF_TAMPERED_URLS)
)
_GUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_TEAMS_CATALOG_DETAIL_URL_RE = re.compile(
    r"^https://graph\.microsoft\.com/v1\.0/appCatalogs/teamsApps/"
    r"[0-9a-fA-F-]{36}\?\$expand=appDefinitions$"
)
_TEAMS_INSTALLED_APPS_URL_RE = re.compile(
    rf"^https://graph\.microsoft\.com/v1\.0/teams/{re.escape(TEAM_ID)}/"
    r"installedApps\?\$filter=teamsApp/externalId%20eq%20'"
    r"[0-9a-fA-F-]{36}'&\$expand=teamsApp$"
)


@dataclass(frozen=True)
class SubprocessCommandResult:
    returncode: int
    stdout: str
    stderr: str


class M365CliReadinessError(RuntimeError):
    """Raised with a stable redacted code when the local M365 CLI is unsafe."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ReadyControlPlaneCommandRunner(ControlPlaneCommandRunner, Protocol):
    """Control-plane runner that proves its authenticated tenant before writes."""

    def check_readiness(self) -> bool: ...


class M365CliCommandRunner:
    """Run allowlisted M365 argv with a pinned local CLI and bounded process."""

    _BINARY_ENV = "NAC_M365_CLI_BINARY"
    _BINARY_SHA256_ENV = "NAC_M365_CLI_EXPECTED_SHA256"
    _HOME_ENV = "NAC_M365_CLI_HOME"
    _NODE_BIN_ENV = "NAC_M365_NODE_BIN"
    _NODE_SHA256_ENV = "NAC_M365_NODE_EXPECTED_SHA256"
    _TIMEOUT_ENV = "NAC_M365_CLI_TIMEOUT_SECONDS"
    _LOCAL_BINARY = Path("/tmp/nac-m365-tools/m365-cli/bin/m365")
    _LOCAL_HOME = Path("/tmp/nac-m365-tools/home")
    _SYSTEM_NODE = Path("/usr/bin/node")

    def __init__(
        self,
        *,
        binary: Path | str | None = None,
        home: Path | str | None = None,
        node_bin: Path | str | None = None,
        expected_binary_sha256: str | None = None,
        expected_node_sha256: str | None = None,
        timeout_seconds: float | None = None,
        environ: dict[str, str] | None = None,
    ) -> None:
        source_values = dict(os.environ if environ is None else environ)
        self.binary = self._resolve_binary(
            binary,
            source_values,
            expected_sha256=expected_binary_sha256,
        )
        self._runtime_root = self.binary.parent.parent
        self._binary_sha256 = self._normalize_sha256(
            expected_binary_sha256 or source_values.get(self._BINARY_SHA256_ENV),
            label="M365_CLI_BINARY",
        )
        try:
            self._runtime_payloads()
        except NodeRuntimeIntegrityError:
            raise M365CliReadinessError(
                "M365_CLI_RUNTIME_BUNDLE_MISMATCH"
            ) from None
        resolved_home = self._resolve_home(home, source_values)
        self._node_binary = self._resolve_node_binary(
            node_bin,
            source_values,
            expected_sha256=expected_node_sha256,
        )
        self._node_sha256 = _sha256_file(self._node_binary)
        self._timeout_seconds = self._resolve_timeout(timeout_seconds, source_values)
        values = _control_plane_environment(source_values)

        values["PATH"] = os.pathsep.join(("/usr/bin", "/bin"))
        values["CLIMICROSOFT365_NOUPDATE"] = "1"
        if resolved_home is not None:
            values["HOME"] = str(resolved_home)
        self._env = values

    def run(self, argv: Sequence[str]) -> SubprocessCommandResult:
        return self._run(argv, {})

    def run_bound(
        self,
        argv: Sequence[str],
        bound_artifacts: Mapping[str, tuple[Path, str]],
    ) -> SubprocessCommandResult:
        return self._run(argv, bound_artifacts)

    def _run(
        self,
        argv: Sequence[str],
        bound_artifacts: Mapping[str, tuple[Path, str]],
    ) -> SubprocessCommandResult:
        command = tuple(str(part) for part in argv)
        _validate_m365_command(command)
        bindings = tuple(bound_artifacts.items())
        if any(command.count(argument) != 1 for argument, _ in bindings):
            raise M365CliReadinessError("M365_CLI_ARTIFACT_BINDING_INVALID")
        try:
            runtime_payloads = self._runtime_payloads()
            with ExitStack() as stack:
                sealed = stack.enter_context(
                    sealed_toolchain(
                        ((self._node_binary, True, self._node_sha256),)
                    )
                )
                runtime_sealed = stack.enter_context(
                    sealed_payloads(
                        (
                            (
                                "node-runtime-manifest.json",
                                runtime_payloads.manifest,
                                False,
                            ),
                            (
                                "node-runtime-preloader.cjs",
                                runtime_payloads.commonjs_preloader,
                                False,
                            ),
                            (
                                "node-runtime-loader.mjs",
                                runtime_payloads.esm_loader,
                                False,
                            ),
                        )
                    )
                )
                artifact_sealed = stack.enter_context(
                    sealed_artifacts(
                        tuple(
                            (path, expected_sha256)
                            for _, (path, expected_sha256) in bindings
                        )
                    )
                ) if bindings else None
                replacements = {
                    argument: artifact_sealed.paths[index]
                    for index, (argument, _) in enumerate(bindings)
                } if artifact_sealed is not None else {}
                bound_command = tuple(
                    replacements.get(argument, argument) for argument in command
                )
                process_argv = [
                    sealed.paths[0],
                    "--preserve-symlinks",
                    "--require",
                    runtime_sealed.paths[1],
                    "--experimental-loader",
                    runtime_sealed.paths[2],
                    str(self.binary),
                    *bound_command[1:],
                ]
                artifact_fds = (
                    artifact_sealed.pass_fds
                    if artifact_sealed is not None
                    else ()
                )
                result = subprocess.run(
                    process_argv,
                    cwd=self.binary.parent,
                    shell=False,
                    text=True,
                    capture_output=True,
                    check=False,
                    env={
                        **self._env,
                        "NODE": sealed.paths[0],
                        MANIFEST_ENV: runtime_sealed.paths[0],
                        "NAC_NODE_RUNTIME_PRELOADER": runtime_sealed.paths[1],
                        "NAC_NODE_RUNTIME_ESM_LOADER": runtime_sealed.paths[2],
                    },
                    timeout=self._timeout_seconds,
                    pass_fds=(
                        sealed.pass_fds
                        + runtime_sealed.pass_fds
                        + artifact_fds
                    ),
                )
        except NodeRuntimeIntegrityError:
            raise M365CliReadinessError(
                "M365_CLI_RUNTIME_BUNDLE_MISMATCH"
            ) from None
        except SealedToolchainError as exc:
            if str(exc) == "SEALED_TOOLCHAIN_SHA256_MISMATCH":
                self._reattest_toolchain()
            raise M365CliReadinessError("M365_CLI_TOOLCHAIN_SEAL_FAILED") from None
        except subprocess.TimeoutExpired:
            raise M365CliReadinessError("M365_CLI_COMMAND_TIMEOUT") from None
        except OSError:
            raise M365CliReadinessError("M365_CLI_COMMAND_EXECUTION_FAILED") from None

        if result.returncode != 0:
            if "NODE_RUNTIME_" in result.stderr:
                raise M365CliReadinessError(
                    "M365_CLI_RUNTIME_BUNDLE_MISMATCH"
                )
            safe_denial = _safe_bff_http_denial(command, result.stdout, result.stderr)
            if safe_denial is not None:
                return SubprocessCommandResult(
                    returncode=result.returncode,
                    stdout=json.dumps(
                        safe_denial, sort_keys=True, separators=(",", ":")
                    ),
                    stderr="",
                )
            raw_error = f"{result.stdout}\n{result.stderr}".lower()
            safe_marker = next(
                (marker for marker in _SAFE_NONZERO_MARKERS if marker in raw_error),
                "M365_CLI_COMMAND_FAILED",
            )
            return SubprocessCommandResult(
                returncode=result.returncode,
                stdout="",
                stderr=safe_marker,
            )
        return SubprocessCommandResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr="",
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
        return (
            (
                payload.get("connectedAs") == EXPECTED_M365_CLI_USER
                and payload.get("appId") == EXPECTED_M365_CLI_APP_ID
            ) or (
                payload.get("connectedAs") == EXPECTED_M365_CLI_PROVISIONER_USER
                and payload.get("appId") == EXPECTED_M365_CLI_PROVISIONER_APP_ID
            )
        ) and payload.get("appTenant") == EXPECTED_M365_TENANT_ID and payload.get("cloudType") == "Public"

    @classmethod
    def _resolve_binary(
        cls,
        explicit: Path | str | None,
        values: dict[str, str],
        *,
        expected_sha256: str | None,
    ) -> Path:
        configured = explicit or values.get(cls._BINARY_ENV)
        candidate = Path(configured).expanduser() if configured else cls._LOCAL_BINARY
        return cls._validate_executable(
            candidate,
            None,
            label="M365_CLI_BINARY",
            allow_bundle_attestation=True,
        )

    @classmethod
    def _resolve_home(
        cls,
        explicit: Path | str | None,
        values: dict[str, str],
    ) -> Path | None:
        configured = explicit or values.get(cls._HOME_ENV)
        if configured:
            candidate = Path(configured).expanduser()
            if not candidate.is_absolute():
                raise M365CliReadinessError("M365_CLI_HOME_PATH_NOT_ABSOLUTE")
            if candidate.is_symlink() or not candidate.is_dir():
                raise M365CliReadinessError("M365_CLI_HOME_UNAVAILABLE")
            return candidate
        if cls._LOCAL_HOME.is_dir() and not cls._LOCAL_HOME.is_symlink():
            return cls._LOCAL_HOME
        return None

    @classmethod
    def _resolve_node_binary(
        cls,
        explicit: Path | str | None,
        values: dict[str, str],
        *,
        expected_sha256: str | None,
    ) -> Path:
        configured = explicit or values.get(cls._NODE_BIN_ENV)
        expected = expected_sha256 or values.get(cls._NODE_SHA256_ENV)
        if configured:
            candidate = Path(configured).expanduser()
            if not candidate.is_absolute():
                raise M365CliReadinessError("M365_NODE_PATH_NOT_ABSOLUTE")
            return cls._validate_executable(
                candidate / "node",
                expected,
                label="M365_NODE_BINARY",
            )

        if cls._SYSTEM_NODE.exists():
            return cls._validate_executable(
                cls._SYSTEM_NODE,
                expected,
                label="M365_NODE_BINARY",
            )
        raise M365CliReadinessError("M365_NODE_BINARY_UNAVAILABLE")

    def _runtime_payloads(self):
        payloads = build_node_runtime_integrity_payloads(
            self._runtime_root,
            expected_digest=self._binary_sha256,
        )
        relative_entry = self.binary.relative_to(self._runtime_root).as_posix()
        manifest = json.loads(payloads.manifest)
        if relative_entry not in manifest.get("files", {}):
            raise NodeRuntimeIntegrityError("NODE_RUNTIME_ENTRYPOINT_MISSING")
        return payloads

    def _reattest_toolchain(self) -> None:
        self._runtime_payloads()
        self._validate_executable(
            self._node_binary,
            self._node_sha256,
            label="M365_NODE_BINARY",
        )

    @classmethod
    def _validate_executable(
        cls,
        candidate: Path,
        expected_sha256: str | None,
        *,
        label: str,
        allow_bundle_attestation: bool = False,
    ) -> Path:
        if not candidate.is_absolute():
            raise M365CliReadinessError(f"{label}_PATH_NOT_ABSOLUTE")
        try:
            metadata = candidate.lstat()
        except OSError:
            raise M365CliReadinessError(f"{label}_UNAVAILABLE") from None
        if stat.S_ISLNK(metadata.st_mode) or _parent_path_has_symlink(candidate):
            raise M365CliReadinessError(f"{label}_SYMLINK_REJECTED")
        if not stat.S_ISREG(metadata.st_mode):
            raise M365CliReadinessError(f"{label}_NOT_REGULAR")
        if metadata.st_uid not in {0, os.getuid()}:
            raise M365CliReadinessError(f"{label}_OWNER_REJECTED")
        if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise M365CliReadinessError(f"{label}_MODE_UNSAFE")
        if not metadata.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH):
            raise M365CliReadinessError(f"{label}_NOT_EXECUTABLE")

        normalized_expected = expected_sha256.strip().lower() if expected_sha256 else None
        if (
            metadata.st_uid != 0
            and normalized_expected is None
            and not allow_bundle_attestation
        ):
            raise M365CliReadinessError(f"{label}_SHA256_REQUIRED")
        if normalized_expected is not None:
            if (
                len(normalized_expected) != _SHA256_HEX_LENGTH
                or any(character not in "0123456789abcdef" for character in normalized_expected)
            ):
                raise M365CliReadinessError(f"{label}_SHA256_INVALID")
            try:
                actual_sha256 = _sha256_file(candidate)
            except OSError:
                raise M365CliReadinessError(f"{label}_UNAVAILABLE") from None
            if actual_sha256 != normalized_expected:
                raise M365CliReadinessError(f"{label}_SHA256_MISMATCH")
        return candidate

    @staticmethod
    def _normalize_sha256(value: str | None, *, label: str) -> str:
        normalized = value.strip().lower() if value else ""
        if (
            len(normalized) != _SHA256_HEX_LENGTH
            or any(character not in "0123456789abcdef" for character in normalized)
        ):
            raise M365CliReadinessError(f"{label}_SHA256_INVALID")
        return normalized

    @classmethod
    def _resolve_timeout(
        cls,
        explicit: float | None,
        values: dict[str, str],
    ) -> float:
        raw_value: float | str = (
            explicit
            if explicit is not None
            else values.get(cls._TIMEOUT_ENV, _DEFAULT_M365_CLI_TIMEOUT_SECONDS)
        )
        try:
            timeout = float(raw_value)
        except (TypeError, ValueError):
            raise M365CliReadinessError("M365_CLI_TIMEOUT_INVALID") from None
        if not 0 < timeout <= _MAX_M365_CLI_TIMEOUT_SECONDS:
            raise M365CliReadinessError("M365_CLI_TIMEOUT_INVALID")
        return timeout


def _validate_m365_command(argv: Sequence[str]) -> None:
    if (
        not argv
        or argv[0] != "m365"
        or any(not isinstance(part, str) or not part for part in argv)
        or any("\x00" in part or "\n" in part or "\r" in part for part in argv)
    ):
        raise M365CliReadinessError("M365_CLI_ARGV_REJECTED")

    command = tuple(argv)
    exact_commands = {
        ("m365", "status", "--output", "json"),
        (
            "m365",
            "util",
            "accesstoken",
            "get",
            "--resource",
            _EXPECTED_API_RESOURCE,
            "--new",
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "serviceprincipal",
            "grant",
            "list",
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "serviceprincipal",
            "permissionrequest",
            "list",
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "app",
            "list",
            "--appCatalogScope",
            APP_CATALOG_SCOPE,
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "app",
            "get",
            "--name",
            PACKAGE_NAME,
            "--appCatalogScope",
            APP_CATALOG_SCOPE,
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "app",
            "instance",
            "list",
            "--siteUrl",
            SITE_URL,
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "page",
            "list",
            "--webUrl",
            SITE_URL,
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "page",
            "get",
            "--name",
            PAGE_NAME,
            "--webUrl",
            SITE_URL,
            "--output",
            "json",
        ),
        (
            "m365",
            "spo",
            "page",
            "set",
            "--name",
            PAGE_NAME,
            "--webUrl",
            SITE_URL,
            "--layoutType",
            PAGE_LAYOUT,
            "--title",
            PAGE_TITLE,
            "--output",
            "none",
        ),
        (
            "m365",
            "spo",
            "page",
            "add",
            "--name",
            PAGE_NAME,
            "--webUrl",
            SITE_URL,
            "--layoutType",
            PAGE_LAYOUT,
            "--title",
            PAGE_TITLE,
            "--output",
            "none",
        ),
        (
            "m365",
            "spo",
            "page",
            "set",
            "--name",
            PAGE_NAME,
            "--webUrl",
            SITE_URL,
            "--content",
            INITIAL_PAGE_CONTENT,
            "--output",
            "none",
        ),
        (
            "m365",
            "spo",
            "page",
            "clientsidewebpart",
            "add",
            "--webUrl",
            SITE_URL,
            "--pageName",
            PAGE_NAME,
            "--webPartId",
            WEB_PART_ID,
            "--output",
            "none",
        ),
        (
            "m365",
            "spo",
            "page",
            "set",
            "--name",
            PAGE_NAME,
            "--webUrl",
            SITE_URL,
            "--publish",
            "--output",
            "none",
        ),
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
    }
    if command in exact_commands:
        return

    if _matches_guid_command(
        command,
        prefix=("m365", "spo", "serviceprincipal", "permissionrequest", "approve", "--id"),
        suffix=("--output", "none"),
    ):
        return
    if _matches_guid_command(
        command,
        prefix=("m365", "spo", "app", "deploy", "--id"),
        suffix=("--appCatalogScope", APP_CATALOG_SCOPE, "--output", "none"),
    ):
        return
    for action in ("install", "upgrade"):
        if _matches_guid_command(
            command,
            prefix=("m365", "spo", "app", action, "--id"),
            suffix=(
                "--siteUrl",
                SITE_URL,
                "--appCatalogScope",
                APP_CATALOG_SCOPE,
                "--output",
                "none",
            ),
        ):
            return
    if _matches_guid_command(
        command,
        prefix=("m365", "teams", "app", "install", "--id"),
        suffix=("--teamId", TEAM_ID, "--output", "none"),
    ):
        return

    if _matches_spfx_app_add(command):
        return
    if _matches_exact_package_command(
        command,
        prefix=("m365", "spo", "app", "teamspackage", "download", "--appName", PACKAGE_NAME, "--fileName"),
        filename="nac-bpmn-viewer.zip",
        suffix=("--output", "none"),
    ):
        return
    if _matches_exact_package_command(
        command,
        prefix=("m365", "teams", "app", "publish", "--filePath"),
        filename="nac-bpmn-viewer.zip",
        suffix=("--output", "json"),
    ):
        return
    if _matches_guid_and_package_command(command):
        return
    if _matches_request_get(command):
        return

    raise M365CliReadinessError("M365_CLI_COMMAND_NOT_ALLOWLISTED")


def _matches_guid_command(
    command: tuple[str, ...],
    *,
    prefix: tuple[str, ...],
    suffix: tuple[str, ...],
) -> bool:
    return (
        len(command) == len(prefix) + 1 + len(suffix)
        and command[: len(prefix)] == prefix
        and _GUID_RE.fullmatch(command[len(prefix)]) is not None
        and command[len(prefix) + 1 :] == suffix
    )


def _matches_spfx_app_add(command: tuple[str, ...]) -> bool:
    prefix = ("m365", "spo", "app", "add", "--filePath")
    if len(command) not in {10, 11} or command[: len(prefix)] != prefix:
        return False
    if not _is_bound_package_path(command[len(prefix)], "nac-bpmn-viewer.sppkg"):
        return False
    expected_tail = (
        "--appCatalogScope",
        APP_CATALOG_SCOPE,
        "--output",
        "none",
    )
    tail = command[len(prefix) + 1 :]
    return tail == expected_tail or tail == (
        "--appCatalogScope",
        APP_CATALOG_SCOPE,
        "--overwrite",
        "--output",
        "none",
    )


def _matches_exact_package_command(
    command: tuple[str, ...],
    *,
    prefix: tuple[str, ...],
    filename: str,
    suffix: tuple[str, ...],
) -> bool:
    return (
        len(command) == len(prefix) + 1 + len(suffix)
        and command[: len(prefix)] == prefix
        and _is_bound_package_path(command[len(prefix)], filename)
        and command[len(prefix) + 1 :] == suffix
    )


def _matches_guid_and_package_command(command: tuple[str, ...]) -> bool:
    prefix = ("m365", "teams", "app", "update", "--id")
    if (
        len(command) != 10
        or command[: len(prefix)] != prefix
        or _GUID_RE.fullmatch(command[len(prefix)]) is None
        or command[len(prefix) + 1] != "--filePath"
        or not _is_bound_package_path(
            command[len(prefix) + 2], "nac-bpmn-viewer.zip"
        )
    ):
        return False
    return command[len(prefix) + 3 :] == ("--output", "none")


def _is_bound_package_path(raw_path: str, filename: str) -> bool:
    candidate = Path(raw_path)
    expected_suffix = (
        "spfx",
        "nac-bpmn-viewer",
        "sharepoint",
        "solution",
        filename,
    )
    return (
        candidate.is_absolute()
        and ".." not in candidate.parts
        and tuple(candidate.parts[-len(expected_suffix) :]) == expected_suffix
    )


def _safe_bff_http_denial(
    command: tuple[str, ...],
    stdout: str,
    stderr: str,
) -> dict[str, object] | None:
    if not _matches_request_get(command):
        return None
    try:
        url = command[command.index("--url") + 1]
    except (ValueError, IndexError):
        return None
    if url not in _EXPECTED_BFF_ALLOWED_URLS:
        return None
    messages = [
        value.strip()
        for value in (stdout, stderr)
        if isinstance(value, str) and value.strip()
    ]
    if len(messages) != 1 or messages[0] not in {
        "Request failed with status code 403",
        "Error: Request failed with status code 403",
    }:
        return None
    return {"status": 403, "error": {"code": "ACCESS_DENIED"}}


def _matches_request_get(command: tuple[str, ...]) -> bool:
    no_resource_prefix = ("m365", "request", "--url")
    no_resource_suffix = ("--method", "get", "--output", "json")
    if (
        len(command) == len(no_resource_prefix) + 1 + len(no_resource_suffix)
        and command[: len(no_resource_prefix)] == no_resource_prefix
        and command[len(no_resource_prefix) + 1 :] == no_resource_suffix
        and _is_allowlisted_graph_get_url(command[len(no_resource_prefix)])
    ):
        return True

    resource_prefix = ("m365", "request", "--url")
    resource_suffix = ("--resource", _EXPECTED_GRAPH_RESOURCE, "--method", "get", "--output", "json")
    if (
        len(command) == len(resource_prefix) + 1 + len(resource_suffix)
        and command[: len(resource_prefix)] == resource_prefix
        and command[len(resource_prefix)] == _EXPECTED_GRAPH_ME_URL
        and command[len(resource_prefix) + 1 :] == resource_suffix
    ):
        return True

    bff_suffix = ("--resource", _EXPECTED_API_RESOURCE, "--method", "get", "--output", "json")
    return (
        len(command) == len(resource_prefix) + 1 + len(bff_suffix)
        and command[: len(resource_prefix)] == resource_prefix
        and command[len(resource_prefix)] in _EXPECTED_BFF_ALLOWED_URLS
        and command[len(resource_prefix) + 1 :] == bff_suffix
    )


def _is_allowlisted_graph_get_url(url: str) -> bool:
    if _TEAMS_CATALOG_DETAIL_URL_RE.fullmatch(url):
        identifier = url.split("/teamsApps/", 1)[1].split("?", 1)[0]
        return _GUID_RE.fullmatch(identifier) is not None
    if _TEAMS_INSTALLED_APPS_URL_RE.fullmatch(url):
        identifier = url.split("externalId%20eq%20'", 1)[1].split("'", 1)[0]
        return _GUID_RE.fullmatch(identifier) is not None
    return False


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
            "liveEntraBffActivation": "FINAL_LIVE_RUN_PENDING",
            "pendingReason": "provisioned_endpoint_and_scope_require_current_main_live_verification",
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parent_path_has_symlink(path: Path) -> bool:
    return any(parent.is_symlink() for parent in path.parents if parent != Path("/"))


def _control_plane_environment(values: dict[str, str]) -> dict[str, str]:
    """Return only non-credential process settings needed by Node and M365 CLI."""

    return {
        key: value
        for key, value in values.items()
        if key in _CONTROL_PLANE_ENV_KEYS or key.startswith("LC_")
    }
