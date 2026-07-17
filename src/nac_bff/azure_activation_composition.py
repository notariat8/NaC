from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import stat
import subprocess
import tempfile
import threading
import time
from typing import Any, Mapping, Protocol
import urllib.parse
import urllib.request
import uuid
import zipfile

from nac_m365_graph.auth import (
    CertificateClientCredentialsTokenProvider,
    GraphConfigError,
    _build_client_assertion_from_bytes,
    _post_token_form,
    _token_endpoint,
    token_provider_from_env,
)
from nac_m365_graph.graph_client import GraphRestClient
from nac_m365_graph.mvp_test_environment_deploy import M365CliCommandRunner
from nac_m365_graph.node_runtime_integrity import (
    MANIFEST_ENV,
    NodeRuntimeIntegrityError,
    build_node_runtime_integrity_payloads,
    build_node_runtime_manifest,
    verify_node_runtime_manifest,
)
from nac_m365_graph.sealed_toolchain import (
    SealedToolchainError,
    sealed_payloads,
    sealed_toolchain,
)
from nac_m365_graph.spfx_site_deployment import (
    APP_CATALOG_SCOPE,
    PACKAGE_CONFIG_RELATIVE_PATH,
    PACKAGE_NAME,
    PACKAGE_RELATIVE_PATH,
    PAGE_NAME,
    SITE_URL,
    SOLUTION_PRODUCT_ID,
    TEAM_ID,
    WEB_PART_ID,
    DeploymentPlanError,
    _find_exact_catalog_app,
    _validate_catalog_app_record,
    build_spfx_site_deployment_plan,
    run_spfx_site_deployment,
)

from .azure_activation import (
    API_APP_URI,
    DELEGATED_SCOPE,
    FUNCTION_APP,
    LOCATION,
    PROVISIONER_CLIENT_ID,
    RESOURCE_GROUP,
    SITE_ID,
    TENANT_ID,
    WORKSPACE_ID,
    build_azure_bff_activation_plan,
)
from .azure_activation_runner import (
    ActivationContext,
    ActivationStepError,
    LiveActivationRequest,
)
from .approved_git_tree import (
    ApprovedGitTreeError,
    ApprovedTreeSnapshot,
    GitApprovedTreeSource,
)
from .azure_activation_attestations import (
    AZURE_CLI_EXECUTION_PATH,
    BUILD_NODE_EXECUTION_PATH,
    BUILD_NPM_CLI_EXECUTION_PATH,
    BUILD_PYTHON_EXECUTION_PATH,
    GH_CLI_EXECUTION_PATH,
    M365_CLI_EXECUTION_PATH,
    M365_NODE_EXECUTION_PATH,
)
from .azure_live_commands import AzureCliAdapter
from . import graph_activation as _graph_activation
from .graph_activation import (
    ApiApplicationBinding,
    GraphActivationError,
    _lookup_api_applications,
    _lookup_service_principals,
    _validate_api_application,
    _validate_api_service_principal,
    ensure_entra_api_application_binding,
    ensure_site_read_permission,
    ensure_uami_sites_selected,
)
from .live_synthetic_workspace import (
    LiveSyntheticWorkspaceError,
    LiveSyntheticWorkspaceManager,
)


_LIVE_CONTRACT = Path("workflows/contracts/m365-azure-bff-live-activation.contract.json")
_BICEP_TEMPLATE = Path("deploy/runtime/azure/nac-bff/infra/compiled/main.json")
_FUNCTION_BUILD = Path("deploy/runtime/azure/nac-bff/build_package.py")
_SPFX_ROOT = Path("spfx/nac-bpmn-viewer")
_SPFX_BUILD_OUTPUT_DIRECTORIES = frozenset(
    {
        ".heft",
        "bin",
        "coverage",
        "dist",
        "jest-output",
        "lib",
        "lib-commonjs",
        "lib-dts",
        "lib-esm",
        "logs",
        "obj",
        "release",
        "sharepoint",
        "solution",
        "temp",
    }
)
_PREPARED_ROOT = Path("prepared")
_PREPARED_FUNCTION = _PREPARED_ROOT / "nac-bff-function.zip"
_PREPARED_BICEP = _PREPARED_ROOT / "main.json"
_PREPARED_BICEP_PARAMETERS = _PREPARED_ROOT / "main.parameters.json"
_PREPARED_INPUTS_MANIFEST = _PREPARED_ROOT / "prepared-inputs.redacted.json"
_PREPARED_SPFX_ROOT = _PREPARED_ROOT / "spfx"
_PREPARED_SPFX_BUILD_ROOT = _PREPARED_ROOT / "spfx-build"
_PREPARED_SPFX_REPRO_BUILD_ROOT = _PREPARED_ROOT / "spfx-build-repro"
_APPROVED_TREE_ROOT = _PREPARED_ROOT / "approved-tree"
_FUNCTION_URL = f"https://{FUNCTION_APP}.azurewebsites.net"
_BFF_URL = (
    f"{_FUNCTION_URL}/v1/workspaces/{WORKSPACE_ID}/matters/NAC-SYN-MATTER-001"
    "?purpose=view_synthetic_matter_workspace"
)
_GRAPH_ME_URL = "https://graph.microsoft.com/v1.0/me?$select=id"
_PROVIDERS = ("Microsoft.Web", "Microsoft.Storage", "Microsoft.OperationalInsights")
_SAFE_PROVIDER_STATES = frozenset({"Registered", "Registering", "NotRegistered"})
_NODE_NPM_CANDIDATES = (
    (
        Path("/tmp/node-v22.23.1-linux-x64/bin/node"),
        Path("/tmp/node-v22.23.1-linux-x64/lib/node_modules/npm/bin/npm-cli.js"),
    ),
    (
        Path("/tmp/nac-m365-tools/node-v24.18.0-linux-x64/bin/node"),
        Path(
            "/tmp/nac-m365-tools/node-v24.18.0-linux-x64/"
            "lib/node_modules/npm/bin/npm-cli.js"
        ),
    ),
    (Path("/usr/bin/node"), Path("/usr/share/nodejs/npm/bin/npm-cli.js")),
)
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_COMMENT_RE = re.compile(
    r"^https://github\.com/notariat8/NaC/issues/632#issuecomment-([1-9][0-9]*)$"
)
_APPROVED_OWNER_LOGIN = "ofunk"
_APPROVED_OWNER_ASSOCIATIONS = ("OWNER", "MEMBER")
_MAX_CREDENTIAL_FILE_BYTES = 1024 * 1024
_APPROVAL_KEYS = {
    "owner-approved",
    "expected_activation_sha256",
    "approved_commit_sha",
    "approved_tree_sha",
    "toolchain_attestations_sha256",
    "target_binding_sha256",
    "permission_boundary_sha256",
    "step_sequence_sha256",
    "no_automatic_rollback_or_deletion",
}


class ApprovalVerifier(Protocol):
    def verify(
        self,
        request: LiveActivationRequest,
        context: ActivationContext,
        plan: Mapping[str, Any],
    ) -> dict[str, Any]: ...


class LocalBuildPort(Protocol):
    def build_function_package(self, repo_root: Path, output_path: Path) -> str: ...

    def build_spfx(
        self, repo_root: Path, isolated_build_root: Path
    ) -> tuple[str, Path]: ...


class ApprovedTreePort(Protocol):
    def materialize(
        self,
        repo_root: Path,
        target_root: Path,
        *,
        approved_commit: str,
        approved_tree: str,
    ) -> ApprovedTreeSnapshot: ...


class HttpReadinessPort(Protocol):
    def wait_for_status(self, url: str, expected_status: int) -> None: ...


class SyntheticWorkspacePort(Protocol):
    def inspect_seed(
        self, actor_id: str, correlation_id: str
    ) -> dict[str, Any]: ...

    def ensure_seed(self, actor_id: str, correlation_id: str) -> dict[str, Any]: ...

    def set_access_mode(
        self, mode: str, actor_id: str, correlation_id: str
    ) -> dict[str, Any]: ...

    def restore_assigned(self, actor_id: str, correlation_id: str) -> dict[str, Any]: ...

    def verify_idempotency(self, actor_id: str, correlation_id: str) -> dict[str, Any]: ...


class _SyntheticSmokeTermination(BaseException):
    """Internal SIGTERM marker; SIGKILL cannot be intercepted or promised safe."""


class _BoundProvisionerCertificateTokenProvider(
    CertificateClientCredentialsTokenProvider
):
    """Re-attest the public certificate and private-key boundary per token fetch."""

    def __init__(self, config, expected_certificate_sha256: str) -> None:
        super().__init__(config)
        self._expected_certificate_sha256 = expected_certificate_sha256

    def fetch_access_token(self) -> str:
        certificate_bytes = _read_trusted_credential_bytes(
            self.config.certificate_path,
            expected_sha256=self._expected_certificate_sha256,
            private_key=False,
        )
        if certificate_bytes is None:
            raise GraphConfigError("PROVISIONER_CERTIFICATE_FILE_UNTRUSTED")
        private_key_bytes = _read_trusted_credential_bytes(
            self.config.private_key_path,
            expected_sha256=None,
            private_key=True,
        )
        if private_key_bytes is None:
            raise GraphConfigError("PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED")
        endpoint = _token_endpoint(self.config.tenant_id)
        assertion = _build_client_assertion_from_bytes(
            self.config,
            endpoint,
            certificate_bytes=certificate_bytes,
            private_key_bytes=private_key_bytes,
        )
        return _post_token_form(
            endpoint,
            {
                "client_id": self.config.client_id,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
                "client_assertion_type": (
                    "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
                ),
                "client_assertion": assertion,
            },
        )


class GitHubApprovalVerifier:
    """Validate one immutable owner-authored issue comment without leaking its body."""

    def __init__(
        self,
        *,
        binary: str | os.PathLike[str] = "/usr/bin/gh",
        expected_binary_sha256: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        source = os.environ if environ is None else environ
        self._binary = _trusted_regular_file(
            binary,
            executable=True,
            expected_sha256=expected_binary_sha256,
        )
        self._env = {
            key: value
            for key, value in source.items()
            if key in {"GH_CONFIG_DIR", "HOME", "LANG"} and value
        }

    def verify(
        self,
        request: LiveActivationRequest,
        context: ActivationContext,
        plan: Mapping[str, Any],
    ) -> dict[str, Any]:
        match = _COMMENT_RE.fullmatch(request.owner_approval_reference)
        if self._binary is None or match is None:
            return {"status": "FAILED", "code": "APPROVAL_SNAPSHOT_UNAVAILABLE"}
        comment = self._gh_json(
            ("api", f"repos/notariat8/NaC/issues/comments/{match.group(1)}")
        )
        if comment is None:
            return {"status": "FAILED", "code": "APPROVAL_SNAPSHOT_UNAVAILABLE"}
        author = comment.get("user")
        body = comment.get("body")
        author_association = comment.get("author_association")
        if (
            not isinstance(author, dict)
            or author.get("login") != _APPROVED_OWNER_LOGIN
            or not isinstance(author_association, str)
            or author_association not in _APPROVED_OWNER_ASSOCIATIONS
        ):
            return {"status": "FAILED", "code": "APPROVAL_OWNER_MISMATCH"}
        if (
            comment.get("html_url") != request.owner_approval_reference
            or comment.get("created_at") != comment.get("updated_at")
            or not isinstance(body, str)
            or _sha256_text(body) != request.approval_body_sha256
        ):
            return {"status": "FAILED", "code": "APPROVAL_SNAPSHOT_MISMATCH"}
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {"status": "FAILED", "code": "APPROVAL_PAYLOAD_INVALID"}
        if not isinstance(payload, dict) or set(payload) != _APPROVAL_KEYS:
            return {"status": "FAILED", "code": "APPROVAL_PAYLOAD_INVALID"}

        contract = _load_json(context.repo_root / _LIVE_CONTRACT)
        expected = {
            "owner-approved": True,
            "expected_activation_sha256": context.activation_hash,
            "approved_commit_sha": context.approved_commit,
            "approved_tree_sha": context.approved_tree,
            "toolchain_attestations_sha256": (
                request.toolchain_attestations_sha256
            ),
            "target_binding_sha256": _sha256_json(plan.get("bindings")),
            "permission_boundary_sha256": _sha256_json(contract.get("permission_boundary")),
            "step_sequence_sha256": _sha256_json(
                [step.get("id") for step in plan.get("steps", [])]
            ),
            "no_automatic_rollback_or_deletion": True,
        }
        if payload != expected:
            return {"status": "FAILED", "code": "APPROVAL_PAYLOAD_MISMATCH"}
        return {"status": "PASSED", "code": "APPROVAL_SNAPSHOT_VERIFIED"}

    def _gh_json(self, argv: tuple[str, ...]) -> dict[str, Any] | None:
        try:
            result = subprocess.run(
                [str(self._binary), *argv],
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                stdin=subprocess.DEVNULL,
                timeout=30,
                env=self._env,
            )
            value = json.loads(result.stdout) if result.returncode == 0 else None
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return None
        return value if isinstance(value, dict) else None


class LocalBuildAdapter:
    """Run only the two repository-bound deterministic build commands."""

    def __init__(
        self,
        *,
        python_binary: str | os.PathLike[str] | None = None,
        node_binary: str | os.PathLike[str] | None = None,
        npm_cli: str | os.PathLike[str] | None = None,
        python_sha256: str | None = None,
        node_sha256: str | None = None,
        npm_cli_sha256: str | None = None,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        source = os.environ if environ is None else environ
        self._python_binary = python_binary
        self._node_binary = node_binary
        self._npm_cli = npm_cli
        self._python_sha256 = (
            python_sha256 or source.get("NAC_TRUSTED_BUILD_PYTHON_SHA256")
        )
        self._node_sha256 = node_sha256 or source.get("NAC_TRUSTED_NODE_SHA256")
        self._npm_cli_sha256 = (
            npm_cli_sha256 or source.get("NAC_TRUSTED_NPM_CLI_SHA256")
        )

    def build_function_package(self, repo_root: Path, output_path: Path) -> str:
        python = self._resolve_python_toolchain()
        if python is None:
            raise ActivationStepError("BUILD_PYTHON_ATTESTATION_FAILED")
        self._run(
            [
                str(python),
                str(repo_root / _FUNCTION_BUILD),
                "--output",
                str(output_path),
            ],
            cwd=repo_root,
            attestations=((python, True, self._python_sha256),),
        )
        return _sha256_file(output_path)

    def build_spfx(
        self, repo_root: Path, isolated_build_root: Path
    ) -> tuple[str, Path]:
        toolchain = self._resolve_node_toolchain()
        if toolchain is None:
            raise ActivationStepError("NPM_UNAVAILABLE")
        node, npm_cli = toolchain
        source = (repo_root / _SPFX_ROOT).resolve()
        build_root = isolated_build_root.resolve()
        if (
            source == build_root
            or source in build_root.parents
            or build_root.exists()
            or not source.is_dir()
        ):
            raise ActivationStepError("SPFX_ISOLATED_BUILD_SCOPE_INVALID")
        try:
            shutil.copytree(
                source,
                build_root,
                symlinks=True,
                ignore=shutil.ignore_patterns(
                    "node_modules",
                    *_SPFX_BUILD_OUTPUT_DIRECTORIES,
                ),
            )
            build_node_runtime_manifest(
                build_root,
                excluded_top_level_directories=frozenset(
                    {"node_modules", *_SPFX_BUILD_OUTPUT_DIRECTORIES}
                ),
            )
        except OSError:
            raise ActivationStepError("SPFX_ISOLATED_BUILD_COPY_FAILED") from None
        self._run(
            [str(node), str(npm_cli), "ci", "--ignore-scripts", "--force"],
            cwd=build_root,
            timeout=600,
            attestations=((node, True, self._node_sha256),),
            node_runtime=(npm_cli.parent.parent, self._npm_cli_sha256),
        )
        dependencies_root = build_root / "node_modules"
        heft_entry = dependencies_root / "@rushstack/heft/bin/heft"
        try:
            dependencies = build_node_runtime_manifest(
                build_root,
                excluded_top_level_directories=_SPFX_BUILD_OUTPUT_DIRECTORIES,
            )
        except NodeRuntimeIntegrityError:
            raise ActivationStepError("SPFX_DEPENDENCY_ATTESTATION_FAILED") from None
        if heft_entry.relative_to(build_root).as_posix() not in {
            item.relative_path for item in dependencies.files
        }:
            raise ActivationStepError("SPFX_DEPENDENCY_ATTESTATION_FAILED")
        build_commands = (
            ("test", "--clean", "--production"),
            ("package-solution", "--production"),
        )
        for command in build_commands:
            self._verify_spfx_dependencies(build_root, dependencies.digest)
            self._run(
                [str(node), str(heft_entry), *command],
                cwd=build_root,
                timeout=900,
                attestations=((node, True, self._node_sha256),),
                node_runtime=(build_root, dependencies.digest),
                node_runtime_excluded_directories=(
                    _SPFX_BUILD_OUTPUT_DIRECTORIES
                ),
                force_wasi_native_fallback=True,
            )
            self._verify_spfx_dependencies(build_root, dependencies.digest)
        package = build_root / PACKAGE_RELATIVE_PATH.relative_to(_SPFX_ROOT)
        _normalize_zip_archive(package)
        return _sha256_file(package), package

    @staticmethod
    def _verify_spfx_dependencies(root: Path, expected_digest: str) -> None:
        try:
            verify_node_runtime_manifest(
                root,
                expected_digest=expected_digest,
                excluded_top_level_directories=_SPFX_BUILD_OUTPUT_DIRECTORIES,
            )
        except NodeRuntimeIntegrityError:
            raise ActivationStepError("SPFX_DEPENDENCY_ATTESTATION_FAILED") from None

    def _resolve_python_toolchain(self) -> Path | None:
        if self._python_binary is None or self._python_sha256 is None:
            return None
        return _trusted_regular_file(
            self._python_binary,
            executable=True,
            expected_sha256=self._python_sha256,
        )

    def _resolve_node_toolchain(self) -> tuple[Path, Path] | None:
        if self._node_sha256 is None or self._npm_cli_sha256 is None:
            return None
        if self._node_binary is not None or self._npm_cli is not None:
            if self._node_binary is None or self._npm_cli is None:
                return None
            candidates = ((self._node_binary, self._npm_cli),)
        else:
            candidates = _NODE_NPM_CANDIDATES
        for node_source, npm_source in candidates:
            node = _trusted_regular_file(
                node_source,
                executable=True,
                expected_sha256=self._node_sha256,
            )
            npm_cli = Path(npm_source)
            try:
                payloads = build_node_runtime_integrity_payloads(
                    npm_cli.parent.parent,
                    expected_digest=self._npm_cli_sha256,
                )
                relative_entry = npm_cli.relative_to(npm_cli.parent.parent).as_posix()
            except (NodeRuntimeIntegrityError, OSError, ValueError):
                continue
            if (
                node is not None
                and relative_entry in json.loads(payloads.manifest)["files"]
                and payloads.digest == self._npm_cli_sha256
            ):
                return node, npm_cli
        return None

    @staticmethod
    def _run(
        argv: list[str],
        *,
        cwd: Path,
        timeout: int = 300,
        attestations: tuple[tuple[Path, bool, str | None], ...] = (),
        node_runtime: tuple[Path, str | None] | None = None,
        node_runtime_excluded_directories: frozenset[str] = frozenset(),
        force_wasi_native_fallback: bool = False,
    ) -> None:
        try:
            with tempfile.TemporaryDirectory(prefix="nac-build-runtime-") as temporary:
                runtime_root = Path(temporary)
                build_home = runtime_root / "home"
                build_tmp = runtime_root / "tmp"
                build_home.mkdir(mode=0o700)
                build_tmp.mkdir(mode=0o700)
                npm_global_config = runtime_root / "npm-global.conf"
                npm_user_config = runtime_root / "npm-user.conf"
                npm_global_config.touch(mode=0o600)
                npm_user_config.touch(mode=0o600)
                env = {
                    "HOME": str(build_home),
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "NPM_CONFIG_AUDIT": "false",
                    "NPM_CONFIG_FUND": "false",
                    "NPM_CONFIG_GLOBALCONFIG": str(npm_global_config),
                    "NPM_CONFIG_USERCONFIG": str(npm_user_config),
                    "PATH": "/usr/bin:/bin",
                    "TMPDIR": str(build_tmp),
                }
                if force_wasi_native_fallback:
                    env["NAPI_RS_FORCE_WASI"] = "error"
                if (
                    any(expected is None for _, _, expected in attestations)
                    or not attestations
                ):
                    raise ActivationStepError("BUILD_TOOLCHAIN_ATTESTATION_FAILED")
                executables = tuple(
                    (path, executable, str(expected))
                    for path, executable, expected in attestations
                )
                runtime_payloads = None
                if node_runtime is not None:
                    runtime_path, runtime_digest = node_runtime
                    if runtime_digest is None:
                        raise ActivationStepError(
                            "BUILD_TOOLCHAIN_ATTESTATION_FAILED"
                        )
                    runtime_payloads = build_node_runtime_integrity_payloads(
                        runtime_path,
                        expected_digest=runtime_digest,
                        excluded_top_level_directories=(
                            node_runtime_excluded_directories
                        ),
                    )
                with sealed_toolchain(executables) as sealed:
                    replacements = {
                        str(path): sealed.paths[index]
                        for index, (path, _, _) in enumerate(executables)
                    }
                    process_argv = [
                        replacements.get(argument, argument) for argument in argv
                    ]
                    pass_fds = sealed.pass_fds
                    if runtime_payloads is not None:
                        if len(argv) < 2:
                            raise ActivationStepError(
                                "BUILD_TOOLCHAIN_ATTESTATION_FAILED"
                            )
                        with sealed_payloads(
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
                        ) as runtime_sealed:
                            env[MANIFEST_ENV] = runtime_sealed.paths[0]
                            env["NODE"] = sealed.paths[0]
                            env["NAC_NODE_RUNTIME_PRELOADER"] = runtime_sealed.paths[1]
                            env["NAC_NODE_RUNTIME_ESM_LOADER"] = runtime_sealed.paths[2]
                            process_argv = [
                                sealed.paths[0],
                                "--preserve-symlinks",
                                "--require",
                                runtime_sealed.paths[1],
                                "--experimental-loader",
                                runtime_sealed.paths[2],
                                *argv[1:],
                            ]
                            result = subprocess.run(
                                process_argv,
                                cwd=cwd,
                                check=False,
                                capture_output=True,
                                text=True,
                                shell=False,
                                stdin=subprocess.DEVNULL,
                                timeout=timeout,
                                env=env,
                                pass_fds=pass_fds + runtime_sealed.pass_fds,
                            )
                    else:
                        result = subprocess.run(
                            process_argv,
                            cwd=cwd,
                            check=False,
                            capture_output=True,
                            text=True,
                            shell=False,
                            stdin=subprocess.DEVNULL,
                            timeout=timeout,
                            env=env,
                            pass_fds=pass_fds,
                        )
        except (NodeRuntimeIntegrityError, SealedToolchainError):
            raise ActivationStepError("BUILD_TOOLCHAIN_ATTESTATION_FAILED") from None
        except (OSError, subprocess.SubprocessError):
            raise ActivationStepError("LOCAL_BUILD_FAILED") from None
        if result.returncode != 0:
            raise ActivationStepError("LOCAL_BUILD_FAILED")



_SPFX_PACKAGE_GUID_RE = re.compile(
    rb"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _normalize_spfx_package_xml_ids(
    records: list[tuple[str, bool, bytes]],
) -> list[tuple[str, bool, bytes]]:
    random_ids: dict[bytes, bytes] = {}
    for name, is_directory, data in records:
        if is_directory:
            continue
        controlled = name in {
            "ClientSideAssets.xml",
            "ClientSideAssets.xml.config.xml",
        } or (
            name.startswith("feature_") and name.endswith(".xml.config.xml")
        )
        if not controlled:
            continue
        matches = _SPFX_PACKAGE_GUID_RE.findall(data)
        if len(matches) != 1:
            raise ActivationStepError("SPFX_PACKAGE_XML_ID_INVALID")
        deterministic = str(
            uuid.uuid5(uuid.UUID(SOLUTION_PRODUCT_ID), f"nac-sppkg:{name}")
        ).encode("ascii")
        random_ids[matches[0].lower()] = deterministic
    if len(random_ids) != 3:
        raise ActivationStepError("SPFX_PACKAGE_XML_ID_SET_INVALID")

    normalized: list[tuple[str, bool, bytes]] = []
    for name, is_directory, data in records:
        value = data
        for random_id, deterministic in random_ids.items():
            value = re.sub(re.escape(random_id), deterministic, value, flags=re.IGNORECASE)
        normalized.append((name, is_directory, value))
    return normalized


def _normalize_zip_archive(path: Path) -> None:
    temporary = path.with_name(f".{path.name}.normalized.tmp")
    try:
        with zipfile.ZipFile(path, "r") as source:
            records: list[tuple[str, bool, bytes]] = []
            seen: set[str] = set()
            for info in source.infolist():
                name = info.filename
                pure = PurePosixPath(name.rstrip("/"))
                canonical = pure.as_posix()
                expected_name = canonical + "/" if info.is_dir() else canonical
                unix_mode = (info.external_attr >> 16) & 0o170000
                if (
                    not name
                    or name.startswith("/")
                    or "\\" in name
                    or canonical in {"", "."}
                    or ".." in pure.parts
                    or name != expected_name
                    or canonical in seen
                    or unix_mode == stat.S_IFLNK
                    or info.flag_bits & 0x1
                ):
                    raise ActivationStepError("SPFX_PACKAGE_ARCHIVE_INVALID")
                seen.add(canonical)
                records.append((name, info.is_dir(), b"" if info.is_dir() else source.read(info)))
        records = _normalize_spfx_package_xml_ids(records)
        with zipfile.ZipFile(
            temporary,
            "x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
            strict_timestamps=True,
        ) as target:
            for name, is_directory, data in sorted(records):
                normalized_name = name.rstrip("/") + "/" if is_directory else name
                info = zipfile.ZipInfo(normalized_name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = (
                    (stat.S_IFDIR | 0o755) if is_directory else (stat.S_IFREG | 0o644)
                ) << 16
                target.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        descriptor = os.open(temporary, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except ActivationStepError:
        raise
    except (OSError, zipfile.BadZipFile, KeyError, RuntimeError):
        raise ActivationStepError("SPFX_PACKAGE_NORMALIZATION_FAILED") from None
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


class HttpReadinessAdapter:
    """Poll one fixed HTTPS endpoint without returning response content."""

    def __init__(self, *, attempts: int = 24, delay_seconds: float = 5.0) -> None:
        self._attempts = attempts
        self._delay_seconds = delay_seconds

    def wait_for_status(self, url: str, expected_status: int) -> None:
        parsed = urllib.parse.urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != f"{FUNCTION_APP}.azurewebsites.net"
        ):
            raise ActivationStepError("FUNCTION_HEALTH_URL_INVALID")
        for attempt in range(self._attempts):
            try:
                request = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(request, timeout=15) as response:
                    if response.status == expected_status:
                        return
            except Exception:
                pass
            if attempt + 1 < self._attempts:
                time.sleep(self._delay_seconds)
        raise ActivationStepError("FUNCTION_HEALTH_NOT_READY")


class AzureBffLiveExecutionPort:
    """Concrete twelve-step owner-gated activation composition."""

    def __init__(
        self,
        *,
        repo_root: Path,
        azure: Any,
        graph: Any,
        m365: Any,
        approval_verifier: ApprovalVerifier,
        local_build: LocalBuildPort,
        http_readiness: HttpReadinessPort,
        synthetic: SyntheticWorkspacePort,
        approved_tree_source: ApprovedTreePort | None = None,
        m365_readback_attempts: int = 5,
        m365_readback_delay_seconds: float = 0.5,
        sleep: Any = time.sleep,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._azure = azure
        self._graph = graph
        self._m365 = m365
        self._approval = approval_verifier
        self._build = local_build
        self._http_readiness = http_readiness
        self._synthetic = synthetic
        self._approved_tree_source = approved_tree_source
        if m365_readback_attempts < 1 or m365_readback_delay_seconds < 0:
            raise ValueError("invalid M365 readback policy")
        self._m365_readback_attempts = m365_readback_attempts
        self._m365_readback_delay_seconds = m365_readback_delay_seconds
        self._sleep = sleep
        self._api: ApiApplicationBinding | None = None
        self._uami_app_id: str | None = None
        self._actor_id: str | None = None
        self._resource_group_absent = False
        self._function_package_sha256: str | None = None
        self._spfx_package_sha256: str | None = None
        self._bicep_sha256: str | None = None
        self._static_inputs_sha256: str | None = None
        self._approved_tree_snapshot_sha256: str | None = None
        self._bicep_parameters_sha256: str | None = None
        self._prepared_inputs_sha256: str | None = None
        self._prepared_inputs_manifest_sha256: str | None = None
        self._function_package_path: Path | None = None
        self._spfx_package_path: Path | None = None
        self._bicep_path: Path | None = None
        self._bicep_parameters_path: Path | None = None
        self._prepared_inputs_path: Path | None = None
        self._spfx_plan: Any | None = None
        self._deployment_preexisting = False
        self._deployed_template_hash: str | None = None
        self._deployed_parameters_sha256: str | None = None
        self._deployed_prepared_inputs_sha256: str | None = None
        self._function_deployment_input_sha256: str | None = None
        self._spfx_deployment_input_sha256: str | None = None
        self._function_health_readback_passed = False
        self._spfx_control_plane_evidence_verified = False
        self._spfx_expected_version: str | None = None
        self._dispatch = {
            "register_azure_providers": self._register_providers,
            "ensure_resource_group": self._ensure_resource_group,
            "ensure_entra_api_application": self._ensure_api_application,
            "deploy_bicep_baseline": self._deploy_bicep,
            "assign_sites_selected": self._assign_sites_selected,
            "grant_target_site_read": self._grant_site_read,
            "deploy_function_package": self._deploy_function,
            "build_and_deploy_spfx": self._deploy_spfx,
            "approve_spfx_bff_scope": self._approve_spfx_scope,
            "seed_synthetic_workspace": self._seed_synthetic,
            "run_access_and_readback_smokes": self._run_access_smokes,
            "run_idempotency_and_evidence": self._run_idempotency,
        }

    def verify_prewrite(
        self,
        context: ActivationContext,
        request: LiveActivationRequest,
    ) -> dict[str, Any]:
        plan = build_azure_bff_activation_plan(self._repo_root)
        approval = self._approval.verify(request, context, plan)
        if approval.get("status") != "PASSED":
            return dict(approval)
        readiness = self._azure.check_readiness()
        if readiness.get("status") != "READY":
            return {"status": "FAILED", "code": "AZURE_CLI_NOT_READY"}
        try:
            if self._m365.check_readiness() is not True:
                return {"status": "FAILED", "code": "M365_CLI_NOT_READY"}
            target_site = self._graph.get(f"/sites/{SITE_ID}?$select=id")
        except Exception:
            return {"status": "FAILED", "code": "GRAPH_PROVISIONER_NOT_READY"}
        if (
            not isinstance(target_site, dict)
            or str(target_site.get("id", "")).lower() != SITE_ID.lower()
        ):
            return {"status": "FAILED", "code": "GRAPH_TARGET_SITE_MISMATCH"}
        try:
            self._inspect_azure_prewrite(context)
            self._api = inspect_entra_api_application_prewrite(self._graph)
            self._inspect_existing_graph_prewrite(require_complete=False)
            self._inspect_m365_prewrite(require_complete=False)
            self._actor_id = self._resolve_actor()
            synthetic = self._synthetic.inspect_seed(
                self._actor_id, context.activation_hash[:32]
            )
            if not isinstance(synthetic, dict) or synthetic.get("status") != "PASSED":
                raise ActivationStepError("SYNTHETIC_PREFLIGHT_FAILED")
            self._prepare_static_artifacts(context)
            self._require_static_inputs(context)
            if self._api is not None:
                self._prepare_resolved_inputs(context)
                self._require_prepared_inputs(context)
        except ActivationStepError as exc:
            return {"status": "FAILED", "code": exc.code}
        except GraphActivationError as exc:
            return {"status": "FAILED", "code": exc.code}
        except LiveSyntheticWorkspaceError as exc:
            return {"status": "FAILED", "code": exc.code}
        except DeploymentPlanError:
            return {"status": "FAILED", "code": "SPFX_PREPARATION_FAILED"}
        except Exception:
            return {
                "status": "FAILED",
                "code": "PREWRITE_VERIFICATION_FAILED",
            }
        return {
            "status": "PASSED",
            "code": "PREWRITE_VERIFIED",
            "prebuilt_inputs_verified": self._prepared_inputs_path is not None,
        }

    def _inspect_azure_prewrite(
        self, context: ActivationContext, *, require_deployment: bool = False
    ) -> int:
        for namespace in _PROVIDERS:
            provider = self._azure_json(
                ["provider", "show", "--namespace", namespace]
            )
            if provider.get("registrationState") not in _SAFE_PROVIDER_STATES:
                raise ActivationStepError("AZURE_PROVIDER_STATE_AMBIGUOUS")

        exists = self._azure.run(["group", "exists", "--name", RESOURCE_GROUP])
        if exists.get("ok") is not True or type(exists.get("data")) is not bool:
            raise ActivationStepError("AZURE_RESOURCE_GROUP_PREFLIGHT_FAILED")
        self._resource_group_absent = exists["data"] is False
        self._deployment_preexisting = False
        if exists["data"] is False:
            if require_deployment:
                raise ActivationStepError("AZURE_BASELINE_READBACK_MISSING")
            return 3

        group = self._azure_json(["group", "show", "--name", RESOURCE_GROUP])
        _validate_resource_group(group)
        resources = self._azure.run(
            ["resource", "list", "--resource-group", RESOURCE_GROUP]
        )
        if resources.get("ok") is not True or not isinstance(resources.get("data"), list):
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_FAILED")
        _validate_azure_resource_inventory(resources["data"])

        deployment = self._azure.run(
            [
                "deployment",
                "group",
                "show",
                "--name",
                _deployment_name(context),
                "--resource-group",
                RESOURCE_GROUP,
            ]
        )
        if deployment.get("ok") is not True:
            if deployment.get("code") == "AZURE_RESOURCE_NOT_FOUND":
                if require_deployment:
                    raise ActivationStepError("AZURE_BASELINE_READBACK_MISSING")
                if resources["data"]:
                    raise ActivationStepError(
                        "AZURE_BASELINE_DEPLOYMENT_BINDING_MISSING"
                    )
                return 0
            raise ActivationStepError("AZURE_BASELINE_PREFLIGHT_FAILED")
        data = deployment.get("data")
        if not isinstance(data, dict):
            raise ActivationStepError("AZURE_BASELINE_PREFLIGHT_FAILED")
        self._validate_deployment_readback(data, require_current_binding=False)
        self._deployment_preexisting = True
        # Evidence counts stable invariants, never provider-specific child resources.
        return 12 if require_deployment else 1

    def _bind_deployment_outputs(self, deployment: Mapping[str, Any]) -> None:
        outputs = deployment.get("properties", {}).get("outputs")
        uami_app_id = _deployment_output(outputs, "managedIdentityClientId")
        host = _deployment_output(outputs, "functionAppHostName")
        if (
            not _UUID_RE.fullmatch(uami_app_id)
            or host != f"{FUNCTION_APP}.azurewebsites.net"
        ):
            raise ActivationStepError("BICEP_OUTPUT_MISMATCH")
        self._uami_app_id = uami_app_id.lower()

    def _validate_deployment_readback(
        self,
        deployment: Mapping[str, Any],
        *,
        require_current_binding: bool,
    ) -> None:
        properties = deployment.get("properties")
        if not isinstance(properties, dict):
            raise ActivationStepError("AZURE_DEPLOYMENT_READBACK_INVALID")
        template_hash = properties.get("templateHash")
        parameters = properties.get("parameters")
        if (
            properties.get("provisioningState") != "Succeeded"
            or properties.get("mode") != "Incremental"
            or not isinstance(template_hash, (str, int))
            or not str(template_hash)
            or not isinstance(parameters, dict)
        ):
            raise ActivationStepError("AZURE_DEPLOYMENT_READBACK_INVALID")
        _validate_deployment_parameters(parameters, self._api)
        self._bind_deployment_outputs(deployment)
        if require_current_binding:
            if self._api is None:
                raise ActivationStepError("API_APPLICATION_BINDING_MISSING")
            expected_parameters = _bicep_parameters(self._api.app_id)["parameters"]
            if (
                parameters != expected_parameters
                or str(template_hash) != self._deployed_template_hash
                or _sha256_json(parameters) != self._deployed_parameters_sha256
                or self._prepared_inputs_sha256
                != self._deployed_prepared_inputs_sha256
            ):
                raise ActivationStepError("AZURE_DEPLOYMENT_INPUT_DRIFT")

    def _inspect_existing_graph_prewrite(self, *, require_complete: bool) -> int:
        if self._uami_app_id is None:
            if require_complete:
                raise ActivationStepError("UAMI_BINDING_MISSING")
            return 0
        graph_role = _graph_activation.inspect_uami_sites_selected(
            self._graph, self._uami_app_id
        )
        site_read = _graph_activation.inspect_site_read_permission(
            self._graph, self._uami_app_id, site_id=SITE_ID
        )
        assignment_count = graph_role.get("assignment_count")
        permission_count = site_read.get("permission_count")
        if (
            graph_role.get("status") not in {"present", "absent"}
            or site_read.get("status") not in {"present", "absent"}
            or assignment_count not in {0, 1}
            or permission_count not in {0, 1}
        ):
            raise ActivationStepError("GRAPH_PERMISSION_PREFLIGHT_INVALID")
        if require_complete and (assignment_count != 1 or permission_count != 1):
            raise ActivationStepError("GRAPH_PERMISSION_READBACK_MISSING")
        return int(assignment_count) + int(permission_count)

    def _inspect_m365_prewrite(self, *, require_complete: bool) -> int:
        grants = self._m365_json(
            ("m365", "spo", "serviceprincipal", "grant", "list", "--output", "json")
        )
        pending = self._m365_json(
            (
                "m365",
                "spo",
                "serviceprincipal",
                "permissionrequest",
                "list",
                "--output",
                "json",
            )
        )
        resource_id = self._api.service_principal_id if self._api is not None else None
        grant_count = _validate_spfx_grants(
            grants, resource_id, allow_absent=not require_complete
        )
        pending_rows = _validate_spfx_permission_requests(
            pending, resource_id, allow_absent=True
        )
        if pending_rows:
            raise ActivationStepError("SPFX_BFF_PERMISSION_STATE_DUPLICATE")

        catalog = self._m365_json(
            (
                "m365",
                "spo",
                "app",
                "list",
                "--appCatalogScope",
                APP_CATALOG_SCOPE,
                "--output",
                "json",
            )
        )
        try:
            catalog_app = _find_exact_catalog_app(catalog)
        except DeploymentPlanError as exc:
            raise ActivationStepError("SPFX_APP_CATALOG_BOUNDARY_FAILED") from exc
        if catalog_app is not None:
            detail = self._m365_json(
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
                )
            )
            try:
                _validate_catalog_app_record(detail)
            except DeploymentPlanError as exc:
                raise ActivationStepError("SPFX_APP_CATALOG_BOUNDARY_FAILED") from exc

        instances = self._m365_json(
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
            )
        )
        _validate_site_app_instances(instances)
        site_app_count = _count_field_value(instances, "ProductId", SOLUTION_PRODUCT_ID)

        pages = self._m365_json(
            (
                "m365",
                "spo",
                "page",
                "list",
                "--webUrl",
                SITE_URL,
                "--output",
                "json",
            )
        )
        _validate_target_pages(pages)
        page_count = _count_page_name(pages)
        webpart_count = 0
        if page_count == 1:
            page = self._m365_json(
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
                )
            )
            webpart_count = _count_structured_webpart_instances(page, WEB_PART_ID)
            if webpart_count > 1:
                raise ActivationStepError("SPFX_PAGE_WEBPART_DUPLICATE")

        teams_catalog = self._m365_json(
            (
                "m365",
                "teams",
                "app",
                "list",
                "--distributionMethod",
                "organization",
                "--output",
                "json",
            )
        )
        teams_matches = [
            row
            for row in _object_rows(teams_catalog)
            if str(_field(row, "externalId") or "").lower() == WEB_PART_ID
        ]
        if len(teams_matches) > 1:
            raise ActivationStepError("TEAMS_CATALOG_APP_DUPLICATE")
        installed_count = 0
        if teams_matches:
            catalog_id = _field(teams_matches[0], "id")
            if not isinstance(catalog_id, str) or not _UUID_RE.fullmatch(catalog_id):
                raise ActivationStepError("TEAMS_CATALOG_APP_INVALID")
            detail = self._m365_json(
                (
                    "m365",
                    "request",
                    "--url",
                    _target_teams_catalog_detail_url(catalog_id),
                    "--method",
                    "get",
                    "--output",
                    "json",
                )
            )
            _validate_teams_catalog_detail(
                detail,
                catalog_id,
                expected_version=(
                    self._spfx_expected_version if require_complete else None
                ),
            )
            installed = self._m365_json(
                (
                    "m365",
                    "request",
                    "--url",
                    _target_team_installed_apps_url(),
                    "--method",
                    "get",
                    "--output",
                    "json",
                )
            )
            installed_count = _validate_target_team_installation(installed, catalog_id)

        counts = (
            grant_count,
            int(catalog_app is not None),
            site_app_count,
            page_count,
            webpart_count,
            len(teams_matches),
            installed_count,
        )
        if require_complete and any(count != 1 for count in counts):
            raise ActivationStepError("M365_LANE_READBACK_INCOMPLETE")
        return sum(counts)

    def _prepare_static_artifacts(self, context: ActivationContext) -> None:
        run_dir = context.run_dir.resolve()
        prepared = (run_dir / _PREPARED_ROOT).resolve()
        if run_dir not in prepared.parents:
            raise ActivationStepError("PREPARED_ARTIFACT_SCOPE_INVALID")
        prepared.mkdir(parents=True, exist_ok=True, mode=0o700)

        build_repo_root = self._repo_root
        if self._approved_tree_source is not None:
            try:
                snapshot = self._approved_tree_source.materialize(
                    self._repo_root,
                    run_dir / _APPROVED_TREE_ROOT,
                    approved_commit=context.approved_commit,
                    approved_tree=context.approved_tree,
                )
            except ApprovedGitTreeError as exc:
                raise ActivationStepError(str(exc)) from None
            build_repo_root = snapshot.root
            self._approved_tree_snapshot_sha256 = snapshot.manifest_sha256

        function_path = (run_dir / _PREPARED_FUNCTION).resolve()
        function_digest = self._build.build_function_package(
            build_repo_root, function_path
        )
        _require_digest(function_digest, function_path)

        spfx_build_root = (run_dir / _PREPARED_SPFX_BUILD_ROOT).resolve()
        spfx_digest, built_package = self._build.build_spfx(
            build_repo_root, spfx_build_root
        )
        if spfx_build_root not in built_package.resolve().parents:
            raise ActivationStepError("SPFX_ISOLATED_BUILD_SCOPE_INVALID")
        _require_digest(spfx_digest, built_package)
        if self._approved_tree_source is not None:
            repro_build_root = (
                run_dir / _PREPARED_SPFX_REPRO_BUILD_ROOT
            ).resolve()
            repro_digest, repro_package = self._build.build_spfx(
                build_repo_root, repro_build_root
            )
            if repro_build_root not in repro_package.resolve().parents:
                raise ActivationStepError("SPFX_ISOLATED_BUILD_SCOPE_INVALID")
            _require_digest(repro_digest, repro_package)
            if repro_digest != spfx_digest:
                raise ActivationStepError("SPFX_REPRODUCIBILITY_FAILED")
        spfx_root = (run_dir / _PREPARED_SPFX_ROOT).resolve()
        package_path = spfx_root / PACKAGE_RELATIVE_PATH
        _copy_snapshot(
            built_package,
            package_path,
            expected_sha256=spfx_digest,
        )
        build_config = (
            spfx_build_root / PACKAGE_CONFIG_RELATIVE_PATH.relative_to(_SPFX_ROOT)
        )
        build_config_digest = _stable_file_sha256(build_config)
        _copy_snapshot(
            build_config,
            spfx_root / PACKAGE_CONFIG_RELATIVE_PATH,
            expected_sha256=build_config_digest,
        )
        _require_digest(spfx_digest, package_path)

        bicep_path = (run_dir / _PREPARED_BICEP).resolve()
        bicep_source = build_repo_root / _BICEP_TEMPLATE
        bicep_digest = _stable_file_sha256(bicep_source)
        _copy_snapshot(
            bicep_source,
            bicep_path,
            expected_sha256=bicep_digest,
        )

        self._function_package_path = function_path
        self._function_package_sha256 = function_digest
        self._spfx_package_path = package_path
        self._spfx_package_sha256 = spfx_digest
        self._bicep_path = bicep_path
        self._bicep_sha256 = bicep_digest
        self._static_inputs_sha256 = _sha256_json(
            self._static_input_binding(context)
        )
        self._spfx_expected_version = _read_spfx_provider_version(
            spfx_root / PACKAGE_CONFIG_RELATIVE_PATH
        )
        self._spfx_plan = build_spfx_site_deployment_plan(
            repo_root=spfx_root,
            workspace_id=WORKSPACE_ID,
            include_teams=True,
            expected_package_sha256=spfx_digest,
        )

    def _prepare_resolved_inputs(self, context: ActivationContext) -> None:
        self._require_static_inputs(context)
        if self._api is None:
            raise ActivationStepError("API_APPLICATION_BINDING_MISSING")
        if self._prepared_inputs_path is not None:
            self._require_prepared_inputs(context)
            return

        run_dir = context.run_dir.resolve()
        parameters_path = (run_dir / _PREPARED_BICEP_PARAMETERS).resolve()
        _write_new_json(parameters_path, _bicep_parameters(self._api.app_id))
        parameters_digest = _sha256_file(parameters_path)

        manifest_path = (run_dir / _PREPARED_INPUTS_MANIFEST).resolve()
        manifest_base = {
            "schema_version": "nac.m365-azure-bff-prepared-inputs/v1",
            "approved_commit_sha": context.approved_commit,
            "approved_tree_sha": context.approved_tree,
            "activation_hash": context.activation_hash,
            "approved_tree_snapshot_sha256": self._approved_tree_snapshot_sha256,
            "bicep_snapshot_sha256": self._bicep_sha256,
            "bicep_parameters_snapshot_sha256": parameters_digest,
            "function_package_sha256": self._function_package_sha256,
            "spfx_package_sha256": self._spfx_package_sha256,
        }
        manifest = {
            **manifest_base,
            "prepared_inputs_sha256": _sha256_json(manifest_base),
        }
        _write_new_json(manifest_path, manifest)

        self._bicep_parameters_path = parameters_path
        self._bicep_parameters_sha256 = parameters_digest
        self._prepared_inputs_path = manifest_path
        self._prepared_inputs_sha256 = manifest["prepared_inputs_sha256"]
        self._prepared_inputs_manifest_sha256 = _sha256_file(manifest_path)

    def _static_input_binding(
        self, context: ActivationContext
    ) -> dict[str, str | None]:
        return {
            "approved_commit_sha": context.approved_commit,
            "approved_tree_sha": context.approved_tree,
            "activation_hash": context.activation_hash,
            "approved_tree_snapshot_sha256": self._approved_tree_snapshot_sha256,
            "bicep_snapshot_sha256": self._bicep_sha256,
            "function_package_sha256": self._function_package_sha256,
            "spfx_package_sha256": self._spfx_package_sha256,
        }

    def _require_static_inputs(self, context: ActivationContext) -> None:
        if (
            self._static_inputs_sha256 is None
            or self._static_inputs_sha256
            != _sha256_json(self._static_input_binding(context))
        ):
            raise ActivationStepError("STATIC_PREPARED_INPUTS_MISMATCH")
        self._require_prepared(
            self._bicep_path, self._bicep_sha256, "BICEP_SNAPSHOT_MISSING"
        )
        self._require_prepared(
            self._function_package_path,
            self._function_package_sha256,
            "FUNCTION_PACKAGE_NOT_PREPARED",
        )
        self._require_prepared(
            self._spfx_package_path,
            self._spfx_package_sha256,
            "SPFX_PACKAGE_NOT_PREPARED",
        )

    def execute_step(
        self,
        step_id: str,
        context: ActivationContext,
    ) -> dict[str, Any]:
        handler = self._dispatch.get(step_id)
        if handler is None:
            raise ActivationStepError("STEP_NOT_ALLOWLISTED")
        try:
            return handler(context)
        except ActivationStepError:
            raise
        except GraphActivationError as exc:
            raise ActivationStepError(exc.code) from None
        except LiveSyntheticWorkspaceError as exc:
            raise ActivationStepError(exc.code) from None
        except Exception:
            raise ActivationStepError("STEP_FAILED") from None

    def _register_providers(self, context: ActivationContext) -> dict[str, Any]:
        updated = 0
        for namespace in _PROVIDERS:
            result = self._azure_json(
                ["provider", "show", "--namespace", namespace]
            )
            state = result.get("registrationState")
            if state not in _SAFE_PROVIDER_STATES:
                raise ActivationStepError("AZURE_PROVIDER_STATE_AMBIGUOUS")
            if state != "Registered":
                self._require_static_inputs(context)
                self._azure_json(
                    [
                        "provider",
                        "register",
                        "--namespace",
                        namespace,
                        "--wait",
                    ]
                )
                updated += 1
            verified = self._azure_json(
                ["provider", "show", "--namespace", namespace]
            )
            if verified.get("registrationState") != "Registered":
                raise ActivationStepError("AZURE_PROVIDER_NOT_REGISTERED")
        return _outcome("updated" if updated else "reused", updated=updated, verified=3)

    def _ensure_resource_group(self, context: ActivationContext) -> dict[str, Any]:
        exists = self._azure.run(["group", "exists", "--name", RESOURCE_GROUP])
        if exists.get("ok") is not True or type(exists.get("data")) is not bool:
            raise ActivationStepError("AZURE_RESOURCE_GROUP_LOOKUP_FAILED")

        classification = "reused"
        if exists["data"] is True:
            group = self._azure_json(["group", "show", "--name", RESOURCE_GROUP])
        elif self._resource_group_absent:
            self._require_static_inputs(context)
            classification = "created"
            group = self._azure_json(
                [
                    "group",
                    "create",
                    "--name",
                    RESOURCE_GROUP,
                    "--location",
                    LOCATION,
                    "--tags",
                    "workload=nac-bff",
                    "environment=test",
                    "dataClassification=no-production-data",
                ]
            )
        else:
            raise ActivationStepError("AZURE_RESOURCE_GROUP_STATE_DRIFT")
        _validate_resource_group(group)
        return _outcome(
            classification,
            created=classification == "created",
            reused=classification == "reused",
            verified=1,
        )

    def _ensure_api_application(self, context: ActivationContext) -> dict[str, Any]:
        self._require_static_inputs(context)
        self._api = ensure_entra_api_application_binding(self._graph)
        self._prepare_resolved_inputs(context)
        result = self._api.redacted_result
        created = int(result.get("status") == "created") + int(
            result.get("service_principal", {}).get("status") == "created"
        )
        outcome = _outcome(
            "created" if created else "reused", created=created, verified=2
        )
        outcome["prebuilt_inputs_verified"] = True
        return outcome

    def _deploy_bicep(self, context: ActivationContext) -> dict[str, Any]:
        if self._api is None:
            raise ActivationStepError("API_APPLICATION_BINDING_MISSING")
        self._require_prepared_inputs(context)
        bicep = self._require_prepared(
            self._bicep_path, self._bicep_sha256, "BICEP_SNAPSHOT_MISSING"
        )
        parameters = self._require_prepared(
            self._bicep_parameters_path,
            self._bicep_parameters_sha256,
            "BICEP_PARAMETERS_SNAPSHOT_MISSING",
        )
        result = self._azure_json_bound(
            [
                "deployment",
                "group",
                "create",
                "--name",
                _deployment_name(context),
                "--resource-group",
                RESOURCE_GROUP,
                "--template-file",
                str(bicep),
                "--parameters",
                f"@{parameters}",
                "--mode",
                "Incremental",
            ],
            {
                str(bicep): (bicep, str(self._bicep_sha256)),
                str(parameters): (
                    parameters,
                    str(self._bicep_parameters_sha256),
                ),
            },
        )
        self._validate_deployment_readback(result, require_current_binding=False)
        properties = result["properties"]
        self._deployed_template_hash = str(properties["templateHash"])
        self._deployed_parameters_sha256 = _sha256_json(properties["parameters"])
        self._deployed_prepared_inputs_sha256 = self._prepared_inputs_sha256
        outcome = _outcome(
            "reused" if self._deployment_preexisting else "updated",
            updated=not self._deployment_preexisting,
            reused=self._deployment_preexisting,
            verified=4,
            reference=f"{FUNCTION_APP}.azurewebsites.net",
        )
        outcome["resource_reference_sha256"] = _sha256_json(
            {
                "evidence_kind": "causal_deployment_input_and_provider_metadata",
                "deployment_name": _deployment_name(context),
                "azure_template_hash": self._deployed_template_hash,
                "bicep_snapshot_sha256": self._bicep_sha256,
                "bicep_parameters_snapshot_sha256": self._bicep_parameters_sha256,
                "prepared_inputs_sha256": self._prepared_inputs_sha256,
            }
        )
        return outcome

    def _assign_sites_selected(self, context: ActivationContext) -> dict[str, Any]:
        self._require_prepared_inputs(context)
        if self._uami_app_id is None:
            raise ActivationStepError("UAMI_BINDING_MISSING")
        result = ensure_uami_sites_selected(self._graph, self._uami_app_id)
        classification = str(result.get("status", "verified"))
        outcome = _outcome(
            classification,
            created=classification == "created",
            reused=classification == "reused",
            verified=1,
        )
        outcome["resource_reference_sha256"] = _sha256_json(
            {
                "principal_app_id": self._uami_app_id,
                "graph_application_role": "Sites.Selected",
                "readback_status": classification,
            }
        )
        return outcome

    def _grant_site_read(self, context: ActivationContext) -> dict[str, Any]:
        self._require_prepared_inputs(context)
        if self._uami_app_id is None:
            raise ActivationStepError("UAMI_BINDING_MISSING")
        result = ensure_site_read_permission(
            self._graph, self._uami_app_id, site_id=SITE_ID
        )
        classification = str(result.get("status", "verified"))
        outcome = _outcome(
            classification,
            created=classification == "created",
            reused=classification == "reused",
            verified=1,
        )
        outcome["resource_reference_sha256"] = _sha256_json(
            {
                "principal_app_id": self._uami_app_id,
                "site_id": SITE_ID,
                "site_role": "read",
                "readback_status": classification,
            }
        )
        return outcome

    def _deploy_function(self, context: ActivationContext) -> dict[str, Any]:
        self._require_prepared_inputs(context)
        package = self._require_prepared(
            self._function_package_path,
            self._function_package_sha256,
            "FUNCTION_PACKAGE_NOT_PREPARED",
        )
        self._azure_json_bound(
            [
                "functionapp",
                "deployment",
                "source",
                "config-zip",
                "--resource-group",
                RESOURCE_GROUP,
                "--name",
                FUNCTION_APP,
                "--src",
                str(package),
                "--build-remote",
                "true",
            ],
            {
                str(package): (
                    package,
                    str(self._function_package_sha256),
                )
            },
        )
        self._http_readiness.wait_for_status(f"{_FUNCTION_URL}/healthz", 200)
        self._function_deployment_input_sha256 = self._function_package_sha256
        self._function_health_readback_passed = True
        outcome = _outcome(
            "updated",
            updated=1,
            verified=2,
        )
        outcome["resource_reference_sha256"] = _sha256_json(
            {
                "evidence_kind": "causal_deployment_input_with_health_readback",
                "function_deployment_input_sha256": (
                    self._function_deployment_input_sha256
                ),
                "prepared_inputs_sha256": self._prepared_inputs_sha256,
                "provider_healthz_passed": True,
            }
        )
        return outcome

    def _deploy_spfx(self, context: ActivationContext) -> dict[str, Any]:
        self._require_prepared_inputs(context)
        self._require_prepared(
            self._spfx_package_path,
            self._spfx_package_sha256,
            "SPFX_PACKAGE_NOT_PREPARED",
        )
        if self._spfx_plan is None:
            raise ActivationStepError("SPFX_PLAN_NOT_PREPARED")
        evidence = run_spfx_site_deployment(
            self._spfx_plan,
            self._m365,
            bound_artifacts={
                str(self._spfx_package_path): (
                    self._spfx_package_path,
                    str(self._spfx_package_sha256),
                )
            },
        )
        package_evidence = evidence.get("package")
        if (
            evidence.get("status") != "PASSED"
            or not isinstance(package_evidence, dict)
            or package_evidence.get("sha256") != self._spfx_package_sha256
        ):
            raise ActivationStepError("SPFX_DEPLOYMENT_FAILED")
        self._spfx_deployment_input_sha256 = self._spfx_package_sha256
        self._spfx_control_plane_evidence_verified = True
        outcome = _outcome(
            "updated",
            updated=1,
            verified=len(evidence.get("steps", [])),
        )
        outcome["resource_reference_sha256"] = _sha256_json(
            {
                "evidence_kind": (
                    "causal_deployment_input_with_control_plane_evidence"
                ),
                "spfx_deployment_input_sha256": (
                    self._spfx_deployment_input_sha256
                ),
                "prepared_inputs_sha256": self._prepared_inputs_sha256,
                "provider_version_expected": self._spfx_expected_version,
            }
        )
        return outcome

    def _approve_spfx_scope(self, context: ActivationContext) -> dict[str, Any]:
        self._require_prepared_inputs(context)
        if self._api is None:
            raise ActivationStepError("API_APPLICATION_BINDING_MISSING")
        grants = self._m365_json(
            ("m365", "spo", "serviceprincipal", "grant", "list", "--output", "json")
        )
        target_count = _validate_spfx_grants(
            grants, self._api.service_principal_id, allow_absent=True
        )
        pending = self._m365_json(
            (
                "m365",
                "spo",
                "serviceprincipal",
                "permissionrequest",
                "list",
                "--output",
                "json",
            )
        )
        matches = _validate_spfx_permission_requests(
            pending,
            self._api.service_principal_id,
            allow_absent=target_count == 1,
        )
        if target_count == 1:
            if matches:
                raise ActivationStepError("SPFX_BFF_PERMISSION_STATE_DUPLICATE")
            outcome = _outcome("reused", reused=1, verified=2)
            outcome["resource_reference_sha256"] = _sha256_json(
                {
                    "resource_id": self._api.service_principal_id,
                    "scope": DELEGATED_SCOPE,
                    "grant_count": 1,
                    "pending_count": 0,
                }
            )
            return outcome
        self._m365_run(
            (
                "m365",
                "spo",
                "serviceprincipal",
                "permissionrequest",
                "approve",
                "--id",
                str(matches[0]["Id"]),
                "--output",
                "none",
            )
        )
        self._poll_spfx_scope_readback(self._api.service_principal_id)
        outcome = _outcome("updated", updated=1, verified=2)
        outcome["resource_reference_sha256"] = _sha256_json(
            {
                "resource_id": self._api.service_principal_id,
                "scope": DELEGATED_SCOPE,
                "grant_count": 1,
                "pending_count": 0,
            }
        )
        return outcome

    def _poll_spfx_scope_readback(self, resource_id: str) -> None:
        for attempt in range(self._m365_readback_attempts):
            grants = self._m365_json(
                (
                    "m365",
                    "spo",
                    "serviceprincipal",
                    "grant",
                    "list",
                    "--output",
                    "json",
                )
            )
            target_count = _validate_spfx_grants(
                grants, resource_id, allow_absent=True
            )
            pending = self._m365_json(
                (
                    "m365",
                    "spo",
                    "serviceprincipal",
                    "permissionrequest",
                    "list",
                    "--output",
                    "json",
                )
            )
            pending_matches = _validate_spfx_permission_requests(
                pending, resource_id, allow_absent=True
            )
            if target_count == 1 and not pending_matches:
                return
            if attempt + 1 < self._m365_readback_attempts:
                self._sleep(self._m365_readback_delay_seconds)
        raise ActivationStepError("SPFX_BFF_GRANT_READBACK_TIMEOUT")

    def _seed_synthetic(self, context: ActivationContext) -> dict[str, Any]:
        self._require_prepared_inputs(context)
        actor = self._require_actor()
        result = self._synthetic.ensure_seed(actor, context.activation_hash[:32])
        return _outcome(
            "created" if result.get("created_count") else "reused",
            created=int(result.get("created_count", 0)),
            updated=int(result.get("patched_count", 0)),
            verified=int(result.get("verified_count", 0)),
        )

    def _run_access_smokes(self, context: ActivationContext) -> dict[str, Any]:
        # White-box ordering probes construct no adapters and cannot perform writes.
        if hasattr(self, "_dispatch"):
            self._require_prepared_inputs(context)
        actor = self._require_actor()
        correlation = context.activation_hash[:32]
        checks = 0
        mode_signals = {
            "assigned_access_passed": False,
            "deputy_access_passed": False,
            "denied_access_passed": False,
            "tampered_access_passed": False,
        }
        primary_error: BaseException | None = None
        restored_ok = False
        previous_sigterm_handler: Any | None = None
        sigterm_guard_installed = False

        if threading.current_thread() is threading.main_thread():
            previous_sigterm_handler = signal.getsignal(signal.SIGTERM)

            def request_termination(_signum: int, _frame: Any) -> None:
                raise _SyntheticSmokeTermination()

            signal.signal(signal.SIGTERM, request_termination)
            sigterm_guard_installed = True
        try:
            self._http_readiness.wait_for_status(f"{_FUNCTION_URL}/healthz", 200)
            healthz_before_auth_passed = True
            checks += 1
            try:
                signal_by_mode = {
                    "assigned": "assigned_access_passed",
                    "deputy": "deputy_access_passed",
                    "denied": "denied_access_passed",
                }
                for mode in ("assigned", "deputy", "denied"):
                    self._synthetic.set_access_mode(mode, actor, correlation)
                    self._request_bff(mode)
                    mode_signals[signal_by_mode[mode]] = True
                    checks += 1
                self._request_bff("tampered")
                mode_signals["tampered_access_passed"] = True
                checks += 1
            except BaseException as exc:
                primary_error = exc
            finally:
                try:
                    restored = self._synthetic.restore_assigned(actor, correlation)
                    restored_ok = (
                        isinstance(restored, dict)
                        and int(restored.get("verified_count", 0)) >= 1
                    )
                except BaseException:
                    restored_ok = False
            if not restored_ok:
                raise ActivationStepError(
                    "SYNTHETIC_STATE_RESTORATION_FAILED"
                ) from None
            if primary_error is not None:
                raise primary_error
            self._request_bff("assigned")
            authenticated_read_passed = True
            checks += 1
            self._http_readiness.wait_for_status(f"{_FUNCTION_URL}/readyz", 200)
            readyz_after_authenticated_read_passed = True
            checks += 1
            outcome = _outcome("verified", updated=4, verified=checks)
            outcome.update(
                {
                    **mode_signals,
                    "healthz_before_auth_passed": healthz_before_auth_passed,
                    "authenticated_read_passed": authenticated_read_passed,
                    "readyz_after_authenticated_read_passed": (
                        readyz_after_authenticated_read_passed
                    ),
                    "synthetic_state_restored": restored_ok,
                }
            )
            return outcome
        finally:
            if sigterm_guard_installed:
                signal.signal(signal.SIGTERM, previous_sigterm_handler)

    def _run_idempotency(self, context: ActivationContext) -> dict[str, Any]:
        actor = self._require_actor()
        self._require_prepared_inputs(context)
        if (
            self._deployed_prepared_inputs_sha256 != self._prepared_inputs_sha256
            or self._function_deployment_input_sha256 != self._function_package_sha256
            or self._spfx_deployment_input_sha256 != self._spfx_package_sha256
            or self._function_health_readback_passed is not True
            or self._spfx_control_plane_evidence_verified is not True
        ):
            raise ActivationStepError("DEPLOYED_INPUT_BINDING_MISSING")
        azure_verified = self._inspect_azure_prewrite(
            context, require_deployment=True
        )
        deployment = self._azure_json(
            [
                "deployment",
                "group",
                "show",
                "--name",
                _deployment_name(context),
                "--resource-group",
                RESOURCE_GROUP,
            ]
        )
        self._validate_deployment_readback(
            deployment, require_current_binding=True
        )
        api = inspect_entra_api_application_prewrite(self._graph)
        if (
            api is None
            or self._api is None
            or api.app_id != self._api.app_id
            or api.service_principal_id != self._api.service_principal_id
        ):
            raise ActivationStepError("API_APPLICATION_READBACK_MISMATCH")
        graph_verified = self._inspect_existing_graph_prewrite(
            require_complete=True
        )
        m365_verified = self._inspect_m365_prewrite(require_complete=True)
        synthetic = self._synthetic.verify_idempotency(
            actor, context.activation_hash[:32]
        )
        synthetic_verified = int(synthetic.get("verified_count", 0))
        if synthetic_verified != 4:
            raise ActivationStepError("SYNTHETIC_IDEMPOTENCY_READBACK_FAILED")
        self._http_readiness.wait_for_status(f"{_FUNCTION_URL}/healthz", 200)
        provider_readback = {
            "azure_deployment_metadata": True,
            "azure_resource_properties": True,
            "function_healthz": True,
            "spfx_catalog_and_site_metadata": m365_verified == 7,
            "spfx_provider_version": self._spfx_expected_version,
        }
        components = {
            "azure": azure_verified,
            "entra_api": 2,
            "graph_permissions": graph_verified,
            "m365_lane": m365_verified,
            "synthetic": synthetic_verified,
            "healthz": 1,
        }
        expected_components = {
            "azure": 12,
            "entra_api": 2,
            "graph_permissions": 2,
            "m365_lane": 7,
            "synthetic": 4,
            "healthz": 1,
        }
        if components != expected_components:
            raise ActivationStepError("LANE_IDEMPOTENCY_READBACK_INCOMPLETE")
        verified = sum(components.values())
        outcome = _outcome(
            "verified",
            verified=verified,
            reference=context.activation_hash,
        )
        outcome["resource_reference_sha256"] = _sha256_json(
            {
                "evidence_kind": (
                    "causal_deployment_inputs_and_separate_provider_readbacks"
                ),
                "component_verification": components,
                "causal_deployment_inputs": {
                    "bicep_snapshot_sha256": self._bicep_sha256,
                    "bicep_parameters_snapshot_sha256": (
                        self._bicep_parameters_sha256
                    ),
                    "function_deployment_input_sha256": (
                        self._function_deployment_input_sha256
                    ),
                    "spfx_deployment_input_sha256": (
                        self._spfx_deployment_input_sha256
                    ),
                    "prepared_inputs_sha256": self._prepared_inputs_sha256,
                },
                "provider_readback": provider_readback,
                "azure_template_hash": self._deployed_template_hash,
                "deployment_name": _deployment_name(context),
            }
        )
        return outcome

    def _resolve_actor(self) -> str:
        payload = self._m365_json(
            (
                "m365",
                "request",
                "--url",
                _GRAPH_ME_URL,
                "--resource",
                "https://graph.microsoft.com",
                "--method",
                "get",
                "--output",
                "json",
            )
        )
        actor = payload.get("id") if isinstance(payload, dict) else None
        if not isinstance(actor, str) or not _UUID_RE.fullmatch(actor):
            raise ActivationStepError("DELEGATED_TEST_ACTOR_INVALID")
        return actor.lower()

    def _request_bff(self, expected_mode: str) -> None:
        url = _BFF_URL
        if expected_mode == "tampered":
            url += "&site_id=foreign"
        result = self._m365.run(
            (
                "m365",
                "request",
                "--url",
                url,
                "--resource",
                API_APP_URI,
                "--method",
                "get",
                "--output",
                "json",
            )
        )
        if expected_mode in {"denied", "tampered"}:
            _validate_structured_bff_denial(result, "ACCESS_DENIED")
            return
        if result.returncode != 0:
            raise ActivationStepError("BFF_ALLOW_SMOKE_FAILED")
        try:
            payload = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise ActivationStepError("BFF_RESPONSE_INVALID") from None
        matter = payload.get("matter") if isinstance(payload, dict) else None
        if (
            payload.get("workspaceId") != WORKSPACE_ID
            or not isinstance(matter, dict)
            or matter.get("matterId") != "NAC-SYN-MATTER-001"
            or matter.get("accessMode") != expected_mode
        ):
            raise ActivationStepError("BFF_RESPONSE_INVALID")

    def _require_prepared_inputs(self, context: ActivationContext) -> None:
        manifest_path = self._require_prepared(
            self._prepared_inputs_path,
            self._prepared_inputs_manifest_sha256,
            "PREPARED_INPUTS_MANIFEST_MISSING",
        )
        manifest = _load_json(manifest_path)
        expected_fields = {
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
        }
        if set(manifest) != expected_fields:
            raise ActivationStepError("PREPARED_INPUTS_MANIFEST_INVALID")
        manifest_base = {
            key: manifest[key]
            for key in expected_fields
            if key != "prepared_inputs_sha256"
        }
        expected = {
            "schema_version": "nac.m365-azure-bff-prepared-inputs/v1",
            "approved_commit_sha": context.approved_commit,
            "approved_tree_sha": context.approved_tree,
            "activation_hash": context.activation_hash,
            "approved_tree_snapshot_sha256": self._approved_tree_snapshot_sha256,
            "bicep_snapshot_sha256": self._bicep_sha256,
            "bicep_parameters_snapshot_sha256": self._bicep_parameters_sha256,
            "function_package_sha256": self._function_package_sha256,
            "spfx_package_sha256": self._spfx_package_sha256,
        }
        if (
            manifest_base != expected
            or manifest["prepared_inputs_sha256"] != _sha256_json(manifest_base)
            or manifest["prepared_inputs_sha256"] != self._prepared_inputs_sha256
        ):
            raise ActivationStepError("PREPARED_INPUTS_MANIFEST_MISMATCH")
        self._require_prepared(
            self._bicep_path, self._bicep_sha256, "BICEP_SNAPSHOT_MISSING"
        )
        parameters_path = self._require_prepared(
            self._bicep_parameters_path,
            self._bicep_parameters_sha256,
            "BICEP_PARAMETERS_SNAPSHOT_MISSING",
        )
        if self._api is None or _load_json(parameters_path) != _bicep_parameters(
            self._api.app_id
        ):
            raise ActivationStepError("BICEP_PARAMETERS_BINDING_MISMATCH")
        self._require_prepared(
            self._function_package_path,
            self._function_package_sha256,
            "FUNCTION_PACKAGE_NOT_PREPARED",
        )
        self._require_prepared(
            self._spfx_package_path,
            self._spfx_package_sha256,
            "SPFX_PACKAGE_NOT_PREPARED",
        )

    def _azure_json(self, argv: list[str]) -> dict[str, Any]:
        result = self._azure.run(argv)
        data = result.get("data")
        if result.get("ok") is not True or not isinstance(data, dict):
            raise ActivationStepError(str(result.get("code") or "AZURE_CLI_COMMAND_FAILED"))
        return data

    def _azure_json_bound(
        self,
        argv: list[str],
        bound_artifacts: Mapping[str, tuple[Path, str]],
    ) -> dict[str, Any]:
        run_bound = getattr(self._azure, "run_bound", None)
        if not callable(run_bound):
            raise ActivationStepError("AZURE_CLI_ARTIFACT_BINDING_UNAVAILABLE")
        result = run_bound(argv, bound_artifacts)
        data = result.get("data")
        if result.get("ok") is not True or not isinstance(data, dict):
            raise ActivationStepError(
                str(result.get("code") or "AZURE_CLI_COMMAND_FAILED")
            )
        return data

    def _m365_json(self, argv: tuple[str, ...]) -> Any:
        result = self._m365_run(argv)
        try:
            return json.loads(result.stdout)
        except (TypeError, json.JSONDecodeError):
            raise ActivationStepError("M365_RESPONSE_INVALID") from None

    def _m365_run(self, argv: tuple[str, ...]) -> Any:
        result = self._m365.run(argv)
        if result.returncode != 0:
            raise ActivationStepError("M365_COMMAND_FAILED")
        return result

    def _require_actor(self) -> str:
        if self._actor_id is None:
            raise ActivationStepError("DELEGATED_TEST_ACTOR_MISSING")
        return self._actor_id

    @staticmethod
    def _require_prepared(
        path: Path | None, digest: str | None, missing_code: str
    ) -> Path:
        if path is None or digest is None:
            raise ActivationStepError(missing_code)
        _require_digest(digest, path)
        return path


def inspect_entra_api_application_prewrite(
    client: Any,
) -> ApiApplicationBinding | None:
    """Read-only API inspection with an internal exact permission resource binding."""

    inspection = _graph_activation.inspect_entra_api_application(client)
    if not isinstance(inspection, dict):
        raise GraphActivationError("GRAPH_RESPONSE_INVALID")
    application_status = inspection.get("status")
    principal = inspection.get("service_principal")
    principal_status = principal.get("status") if isinstance(principal, dict) else None
    if (
        application_status not in {"present", "absent"}
        or principal_status not in {"present", "absent"}
        or (application_status == "absent" and principal_status != "absent")
    ):
        raise GraphActivationError("GRAPH_RESPONSE_INVALID")
    if application_status == "absent":
        return None

    applications = _lookup_api_applications(client)
    if not applications:
        raise GraphActivationError("API_APPLICATION_READBACK_MISSING")
    if len(applications) > 1:
        raise GraphActivationError("API_APPLICATION_DUPLICATE")
    _object_id, app_id = _validate_api_application(applications[0])
    service_principals = _lookup_service_principals(client, app_id)
    if principal_status == "absent":
        if service_principals:
            raise GraphActivationError("API_SERVICE_PRINCIPAL_MISMATCH")
        return None
    if not service_principals:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_READBACK_MISSING")
    if len(service_principals) > 1:
        raise GraphActivationError("API_SERVICE_PRINCIPAL_DUPLICATE")
    principal_id = _validate_api_service_principal(service_principals[0], app_id)
    return ApiApplicationBinding(
        app_id=app_id,
        service_principal_id=principal_id,
        redacted_result=inspection,
    )


def _bound_provisioner_token_provider(
    environ: Mapping[str, str],
    *,
    expected_certificate_sha256: str,
) -> CertificateClientCredentialsTokenProvider:
    values = dict(environ)
    if (
        values.get("M365_TENANT_ID", "").strip().lower() != TENANT_ID
        or values.get("M365_PROVISIONER_CLIENT_ID", "").strip().lower()
        != PROVISIONER_CLIENT_ID
    ):
        raise GraphConfigError("PROVISIONER_IDENTITY_MISMATCH")
    if any(
        values.get(name, "").strip()
        for name in (
            "M365_GRAPH_ACCESS_TOKEN",
            "M365_GRAPH_ACCESS_TOKEN_FILE",
            "M365_PROVISIONER_CLIENT_SECRET",
        )
    ):
        raise GraphConfigError("PROVISIONER_CERTIFICATE_MODE_REQUIRED")
    provider = token_provider_from_env(values)
    if not isinstance(provider, CertificateClientCredentialsTokenProvider):
        raise GraphConfigError("PROVISIONER_CERTIFICATE_MODE_REQUIRED")
    if (
        provider.config.tenant_id.lower() != TENANT_ID
        or provider.config.client_id.lower() != PROVISIONER_CLIENT_ID
    ):
        raise GraphConfigError("PROVISIONER_IDENTITY_MISMATCH")
    if _read_trusted_credential_bytes(
        provider.config.certificate_path,
        expected_sha256=expected_certificate_sha256,
        private_key=False,
    ) is None:
        raise GraphConfigError("PROVISIONER_CERTIFICATE_FILE_UNTRUSTED")
    if _read_trusted_credential_bytes(
        provider.config.private_key_path,
        expected_sha256=None,
        private_key=True,
    ) is None:
        raise GraphConfigError("PROVISIONER_PRIVATE_KEY_FILE_UNTRUSTED")
    return _BoundProvisionerCertificateTokenProvider(
        provider.config, expected_certificate_sha256
    )


def build_live_activation_execution_port(
    repo_root: Path,
    request: LiveActivationRequest,
) -> AzureBffLiveExecutionPort:
    """Create concrete dependencies only after the CLI has passed both live gates."""

    values = dict(os.environ)
    graph = GraphRestClient(
        _bound_provisioner_token_provider(
            values,
            expected_certificate_sha256=request.provisioner_certificate_sha256,
        )
    )
    m365 = M365CliCommandRunner(
        binary=M365_CLI_EXECUTION_PATH,
        node_bin=M365_NODE_EXECUTION_PATH.parent,
        environ=values,
        expected_binary_sha256=request.m365_cli_sha256,
        expected_node_sha256=request.m365_node_sha256,
    )
    return AzureBffLiveExecutionPort(
        repo_root=repo_root,
        azure=AzureCliAdapter(
            binary=AZURE_CLI_EXECUTION_PATH,
            expected_binary_sha256=request.azure_cli_toolchain_sha256,
            environ=values,
        ),
        graph=graph,
        m365=m365,
        approval_verifier=GitHubApprovalVerifier(
            binary=GH_CLI_EXECUTION_PATH,
            expected_binary_sha256=request.gh_cli_sha256,
            environ=values,
        ),
        local_build=LocalBuildAdapter(
            python_binary=BUILD_PYTHON_EXECUTION_PATH,
            node_binary=BUILD_NODE_EXECUTION_PATH,
            npm_cli=BUILD_NPM_CLI_EXECUTION_PATH,
            python_sha256=request.build_python_sha256,
            node_sha256=request.build_node_sha256,
            npm_cli_sha256=request.build_npm_cli_sha256,
            environ=values,
        ),
        http_readiness=HttpReadinessAdapter(),
        synthetic=LiveSyntheticWorkspaceManager(graph),
        approved_tree_source=GitApprovedTreeSource(),
    )



def _trusted_regular_file(
    source: str | os.PathLike[str] | None,
    *,
    executable: bool,
    expected_sha256: str | None = None,
) -> Path | None:
    if source is None:
        return None
    path = Path(source)
    if not path.is_absolute():
        return None
    try:
        metadata = path.lstat()
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid not in {0, os.geteuid()}
            or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (executable and not metadata.st_mode & 0o111)
        ):
            return None
        if expected_sha256 is not None:
            if (
                not isinstance(expected_sha256, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected_sha256)
                or _sha256_file(path) != expected_sha256
            ):
                return None
        elif metadata.st_uid != 0:
            return None
        parent = path.parent
        while parent != parent.parent:
            parent_metadata = parent.lstat()
            if (
                stat.S_ISLNK(parent_metadata.st_mode)
                or not stat.S_ISDIR(parent_metadata.st_mode)
                or parent_metadata.st_uid not in {0, os.geteuid()}
                or (
                    parent_metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                    and not parent_metadata.st_mode & stat.S_ISVTX
                )
            ):
                return None
            parent = parent.parent
    except OSError:
        return None
    return path


def _read_trusted_credential_bytes(
    source: str | os.PathLike[str] | None,
    *,
    expected_sha256: str | None,
    private_key: bool,
) -> bytes | None:
    if source is None:
        return None
    path = Path(source)
    if not path.is_absolute() or not _trusted_credential_parent_chain(path.parent):
        return None
    if expected_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        return None

    descriptor = -1
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(path, flags)
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            return None
        if private_key:
            if (
                before.st_uid != os.geteuid()
                or stat.S_IMODE(before.st_mode) not in {0o400, 0o600}
            ):
                return None
        elif (
            before.st_uid not in {0, os.geteuid()}
            or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        ):
            return None

        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, _MAX_CREDENTIAL_FILE_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > _MAX_CREDENTIAL_FILE_BYTES:
                return None
        after = os.fstat(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            return None
        payload = b"".join(chunks)
        if len(payload) != after.st_size:
            return None
        if expected_sha256 is not None and hashlib.sha256(payload).hexdigest() != expected_sha256:
            return None
        return payload
    except OSError:
        return None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _trusted_credential_parent_chain(path: Path) -> bool:
    try:
        current = path
        while current != current.parent:
            metadata = current.lstat()
            if (
                stat.S_ISLNK(metadata.st_mode)
                or not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid not in {0, os.geteuid()}
                or (
                    metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                    and not (
                        metadata.st_uid == 0
                        and metadata.st_mode & stat.S_ISVTX
                    )
                )
            ):
                return False
            current = current.parent
    except OSError:
        return False
    return True


def _validate_deployment_parameters(
    parameters: Mapping[str, Any],
    api: ApiApplicationBinding | None,
) -> None:
    placeholder_app_id = api.app_id if api is not None else "00000000-0000-4000-8000-000000000001"
    expected = _bicep_parameters(placeholder_app_id)["parameters"]
    actual_audience = parameters.get("bffApiAudience")
    if (
        set(parameters) != set(expected)
        or not isinstance(actual_audience, dict)
        or set(actual_audience) != {"value"}
        or not isinstance(actual_audience.get("value"), str)
        or not _UUID_RE.fullmatch(actual_audience["value"])
    ):
        raise ActivationStepError("AZURE_DEPLOYMENT_PARAMETERS_INVALID")
    if api is not None and actual_audience != expected["bffApiAudience"]:
        raise ActivationStepError("AZURE_DEPLOYMENT_PARAMETERS_INVALID")
    for key, value in expected.items():
        if key != "bffApiAudience" and parameters.get(key) != value:
            raise ActivationStepError("AZURE_DEPLOYMENT_PARAMETERS_INVALID")


def _deployment_name(_context: ActivationContext) -> str:
    target_binding = {
        "tenant_id": TENANT_ID,
        "resource_group": RESOURCE_GROUP,
        "location": LOCATION,
        "function_app": FUNCTION_APP,
        "workspace_id": WORKSPACE_ID,
        "site_id": SITE_ID,
        "team_id": TEAM_ID,
    }
    return f"nac-bff-{_sha256_json(target_binding)[:12]}"


def _bicep_parameters(api_app_id: str) -> dict[str, Any]:
    if not _UUID_RE.fullmatch(api_app_id):
        raise ActivationStepError("API_APPLICATION_BINDING_INVALID")
    return {
        "$schema": (
            "https://schema.management.azure.com/schemas/"
            "2019-04-01/deploymentParameters.json#"
        ),
        "contentVersion": "1.0.0.0",
        "parameters": {
            "location": {"value": LOCATION},
            "environmentName": {"value": "test"},
            "m365TenantId": {"value": TENANT_ID},
            "bffApiAudience": {"value": api_app_id.lower()},
            "bffRequiredDelegatedScope": {"value": DELEGATED_SCOPE},
            "functionAppName": {"value": FUNCTION_APP},
            "maximumInstanceCount": {"value": 4},
            "httpPerInstanceConcurrency": {"value": 16},
            "tags": {"value": {}},
        },
    }


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary_path: Path | None = None
    try:
        if path.exists() or path.is_symlink():
            raise OSError
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(raw + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary_path.chmod(0o600)
        os.link(temporary_path, path)
        temporary_path.unlink()
        temporary_path = None
    except OSError:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass
        raise ActivationStepError("PREPARED_ARTIFACT_SNAPSHOT_FAILED") from None


def _validate_azure_resource_inventory(value: list[object]) -> None:
    required = {
        "microsoft.managedidentity/userassignedidentities": {
            "pattern": re.compile(r"^id-nac-bff-test-[a-z0-9]+$"),
        },
        "microsoft.storage/storageaccounts": {
            "pattern": re.compile(r"^stnacbff[a-z0-9]+$"),
            "kind": "StorageV2",
            "sku_name": "Standard_LRS",
        },
        "microsoft.operationalinsights/workspaces": {
            "pattern": re.compile(r"^log-nac-bff-test-[a-z0-9]+$"),
        },
        "microsoft.insights/components": {
            "pattern": re.compile(r"^appi-nac-bff-test-[a-z0-9]+$"),
            "kind": "web",
        },
        "microsoft.web/serverfarms": {
            "pattern": re.compile(r"^plan-nac-bff-test-[a-z0-9]+$"),
            "kind": "functionapp",
            "sku_name": "FC1",
            "sku_tier": "FlexConsumption",
        },
        "microsoft.web/sites": {
            "pattern": re.compile(rf"^{re.escape(FUNCTION_APP)}$"),
            "kind": "functionapp,linux",
        },
    }
    optional_types = {
        "microsoft.authorization/roleassignments",
        "microsoft.insights/components/currentbillingfeatures",
        "microsoft.storage/storageaccounts/blobservices",
        "microsoft.storage/storageaccounts/blobservices/containers",
        "microsoft.web/sites/config",
    }
    required_tags = {
        "workload": "nac-bff",
        "environment": "test",
        "managedBy": "bicep",
        "dataClassification": "no-production-data",
    }
    inventory_keys: set[tuple[str, str]] = set()
    for item in value:
        if not isinstance(item, dict):
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_INVALID")
        name = item.get("name")
        resource_type = str(item.get("type", "")).lower()
        if not isinstance(name, str):
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_UNEXPECTED")
        key = (resource_type, name.lower())
        if key in inventory_keys:
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_DUPLICATE")
        inventory_keys.add(key)

    seen: set[tuple[str, str]] = set()
    counts = {resource_type: 0 for resource_type in required}
    for item in value:
        if not isinstance(item, dict):
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_INVALID")
        name = item.get("name")
        resource_type = str(item.get("type", "")).lower()
        group = item.get("resourceGroup")
        if not isinstance(name, str) or group != RESOURCE_GROUP:
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_UNEXPECTED")
        key = (resource_type, name.lower())
        if key in seen:
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_DUPLICATE")
        seen.add(key)
        if resource_type in required:
            specification = required[resource_type]
            tags = item.get("tags")
            sku = item.get("sku")
            if (
                specification["pattern"].fullmatch(name) is None
                or str(item.get("location", "")).lower() != LOCATION
                or not isinstance(tags, dict)
                or any(tags.get(key) != expected for key, expected in required_tags.items())
                or (
                    "kind" in specification
                    and str(item.get("kind", "")).lower()
                    != str(specification["kind"]).lower()
                )
                or (
                    "sku_name" in specification
                    and (
                        not isinstance(sku, dict)
                        or sku.get("name") != specification["sku_name"]
                    )
                )
                or (
                    "sku_tier" in specification
                    and (
                        not isinstance(sku, dict)
                        or sku.get("tier") != specification["sku_tier"]
                    )
                )
            ):
                raise ActivationStepError("AZURE_RESOURCE_PROPERTY_DRIFT")
            counts[resource_type] += 1
        elif resource_type not in optional_types:
            raise ActivationStepError("AZURE_RESOURCE_INVENTORY_UNEXPECTED")
    if value and any(counts[kind] != 1 for kind in required):
        raise ActivationStepError("AZURE_RESOURCE_INVENTORY_INCOMPLETE")


def _count_field_value(value: object, field: str, expected: str) -> int:
    return sum(
        str(_field(row, field) or "").lower() == expected.lower()
        for row in _object_rows(value)
    )


def _count_page_name(value: object) -> int:
    return sum(
        str(_field(row, "Name", "name", "FileLeafRef") or "").lower()
        == PAGE_NAME.lower()
        for row in _object_rows(value)
    )


def _read_spfx_provider_version(config_path: Path) -> str:
    config = _load_json(config_path)
    solution = config.get("solution") if isinstance(config, dict) else None
    raw_version = solution.get("version") if isinstance(solution, dict) else None
    if (
        not isinstance(raw_version, str)
        or re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+", raw_version)
        is None
    ):
        raise ActivationStepError("SPFX_PROVIDER_VERSION_INVALID")
    major, minor, patch, revision = raw_version.split(".")
    if revision != "0":
        raise ActivationStepError("SPFX_PROVIDER_VERSION_INVALID")
    return f"{major}.{minor}.{patch}"


def _count_structured_webpart_instances(value: object, webpart_id: str) -> int:
    target = webpart_id.lower()
    identifier_keys = {"webpartid", "webPartId", "componentid", "componentId"}

    def parse_canvas(candidate: object) -> object:
        if not isinstance(candidate, str):
            return candidate
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            raise ActivationStepError("SPFX_PAGE_WEBPART_STATE_INVALID") from None
        if not isinstance(parsed, (dict, list)):
            raise ActivationStepError("SPFX_PAGE_WEBPART_STATE_INVALID")
        return parsed

    def count(candidate: object) -> int:
        if isinstance(candidate, list):
            return sum(count(item) for item in candidate)
        if not isinstance(candidate, dict):
            return 0
        identifiers = {
            str(item).lower()
            for key, item in candidate.items()
            if key in identifier_keys and isinstance(item, str)
        }
        current = int(target in identifiers)
        nested = 0
        for key, item in candidate.items():
            if key in {"CanvasContent1", "canvasContent1"}:
                nested += count(parse_canvas(item))
            elif key not in identifier_keys:
                nested += count(item)
        return current + nested

    return count(value)


def _target_teams_catalog_detail_url(catalog_id: str) -> str:
    if not _UUID_RE.fullmatch(catalog_id):
        raise ActivationStepError("TEAMS_CATALOG_APP_INVALID")
    return (
        "https://graph.microsoft.com/v1.0/appCatalogs/teamsApps/"
        f"{catalog_id}?$expand=appDefinitions"
    )


def _validate_teams_catalog_detail(
    value: object,
    catalog_id: str,
    *,
    expected_version: str | None = None,
) -> None:
    if (
        not isinstance(value, dict)
        or str(value.get("id", "")).lower() != catalog_id.lower()
        or str(value.get("externalId", "")).lower() != WEB_PART_ID
        or not isinstance(value.get("appDefinitions"), list)
    ):
        raise ActivationStepError("TEAMS_CATALOG_DETAIL_INVALID")
    versions: set[str] = set()
    for definition in value["appDefinitions"]:
        if not isinstance(definition, dict):
            raise ActivationStepError("TEAMS_CATALOG_DETAIL_INVALID")
        version = definition.get("version")
        state = definition.get("publishingState")
        if (
            not isinstance(version, str)
            or not version
            or version in versions
            or state not in {"published", "submitted", "rejected"}
        ):
            raise ActivationStepError("TEAMS_CATALOG_DETAIL_INVALID")
        versions.add(version)
    if not versions:
        raise ActivationStepError("TEAMS_CATALOG_DETAIL_INVALID")
    if expected_version is not None:
        published_version_list = [
            definition["version"]
            for definition in value["appDefinitions"]
            if definition.get("publishingState") == "published"
        ]
        expected = _parse_teams_version(expected_version)
        published = [
            _parse_teams_version(version) for version in published_version_list
        ]
        if (
            published_version_list.count(expected_version) != 1
            or not published
            or max(published) != expected
            or any(version > expected for version in published)
        ):
            raise ActivationStepError("TEAMS_CATALOG_VERSION_DRIFT")


def _parse_teams_version(value: str) -> tuple[int, int, int]:
    if re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value) is None:
        raise ActivationStepError("TEAMS_CATALOG_DETAIL_INVALID")
    return tuple(int(part) for part in value.split("."))  # type: ignore[return-value]


def _target_team_installed_apps_url() -> str:
    return (
        f"https://graph.microsoft.com/v1.0/teams/{TEAM_ID}/installedApps"
        f"?$filter=teamsApp/externalId%20eq%20'{WEB_PART_ID}'"
        "&$expand=teamsApp"
    )


def _validate_target_team_installation(value: object, catalog_id: str) -> int:
    if not isinstance(value, dict) or not isinstance(value.get("value"), list):
        raise ActivationStepError("TEAMS_INSTALLATION_RESPONSE_INVALID")
    if value.get("@odata.nextLink") not in (None, ""):
        raise ActivationStepError("TEAMS_INSTALLATION_RESPONSE_INVALID")
    rows = value["value"]
    matches = []
    for row in rows:
        if not isinstance(row, dict):
            raise ActivationStepError("TEAMS_INSTALLATION_RESPONSE_INVALID")
        app = row.get("teamsApp")
        if not isinstance(app, dict):
            raise ActivationStepError("TEAMS_INSTALLATION_RESPONSE_INVALID")
        if str(app.get("externalId", "")).lower() != WEB_PART_ID:
            raise ActivationStepError("TEAMS_INSTALLATION_IDENTITY_MISMATCH")
        if str(app.get("id", "")).lower() != catalog_id.lower():
            raise ActivationStepError("TEAMS_INSTALLATION_IDENTITY_MISMATCH")
        matches.append(row)
    if len(matches) > 1:
        raise ActivationStepError("TEAMS_INSTALLATION_DUPLICATE")
    return len(matches)


def _validate_structured_bff_denial(result: Any, expected_code: str) -> None:
    if result.returncode == 0:
        raise ActivationStepError("BFF_DENY_SMOKE_FAILED")
    payload: object | None = None
    for candidate in (result.stdout, result.stderr):
        if not isinstance(candidate, str) or not candidate.strip():
            continue
        try:
            payload = json.loads(candidate)
            break
        except json.JSONDecodeError:
            continue
    if not isinstance(payload, dict):
        raise ActivationStepError("BFF_DENY_RESPONSE_INVALID")
    status = payload.get("status")
    error = payload.get("error")
    if (
        status != 403
        or not isinstance(error, dict)
        or error.get("code") != expected_code
        or any(
            key in payload or key in error
            for key in ("matter", "matterId", "workspaceId", "exists")
        )
    ):
        raise ActivationStepError("BFF_DENY_RESPONSE_INVALID")


def _outcome(
    classification: str,
    *,
    created: int | bool = 0,
    reused: int | bool = 0,
    updated: int | bool = 0,
    verified: int | bool = 0,
    reference: str | None = None,
) -> dict[str, Any]:
    allowed = {"created", "reused", "updated", "verified", "not_applicable"}
    if classification not in allowed:
        classification = "verified"
    result: dict[str, Any] = {
        "status": "PASSED",
        "classification": classification,
        "created_count": int(created),
        "reused_count": int(reused),
        "updated_count": int(updated),
        "verified_count": int(verified),
    }
    if reference:
        result["reference_sha256"] = _sha256_text(reference)
    return result


def _deployment_output(outputs: object, name: str) -> str:
    value = outputs.get(name) if isinstance(outputs, dict) else None
    raw = value.get("value") if isinstance(value, dict) else None
    if not isinstance(raw, str) or not raw:
        raise ActivationStepError("BICEP_OUTPUT_MISSING")
    return raw


def _rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ActivationStepError("M365_RESPONSE_INVALID")
    return value


def _validate_resource_group(value: object) -> None:
    expected_tags = {
        "workload": "nac-bff",
        "environment": "test",
        "dataClassification": "no-production-data",
    }
    if (
        not isinstance(value, dict)
        or value.get("name") != RESOURCE_GROUP
        or str(value.get("location", "")).lower() != LOCATION
        or value.get("tags") != expected_tags
    ):
        raise ActivationStepError("RESOURCE_GROUP_MISMATCH")


def _validate_spfx_grants(
    value: object,
    resource_id: str | None,
    *,
    allow_absent: bool,
) -> int:
    rows = _rows(value)
    if resource_id is None:
        return 0
    matching_rows = [
        row
        for row in rows
        if isinstance(_field(row, "resourceId", "ResourceId"), str)
        and _field(row, "resourceId", "ResourceId").lower() == resource_id.lower()
    ]
    if not matching_rows:
        if allow_absent:
            return 0
        raise ActivationStepError("SPFX_BFF_GRANT_READBACK_FAILED")
    if len(matching_rows) != 1:
        raise ActivationStepError("SPFX_BFF_GRANT_BROADER_OR_DUPLICATE")
    row = matching_rows[0]
    candidate = _field(row, "resourceId", "ResourceId")
    scope = _field(row, "scope", "Scope")
    if (
        not isinstance(candidate, str)
        or candidate.lower() != resource_id.lower()
        or scope != DELEGATED_SCOPE
    ):
        raise ActivationStepError("SPFX_BFF_GRANT_BROADER_OR_DUPLICATE")
    return 1


def _validate_spfx_permission_requests(
    value: object,
    resource_id: str | None,
    *,
    allow_absent: bool,
) -> list[dict[str, Any]]:
    rows = _rows(value)
    if not rows:
        if allow_absent:
            return []
        raise ActivationStepError("SPFX_BFF_PERMISSION_REQUEST_MISSING")
    if resource_id is None or len(rows) != 1:
        raise ActivationStepError("SPFX_BFF_PERMISSION_REQUEST_UNEXPECTED")
    row = rows[0]
    request_id = _field(row, "Id", "id")
    candidate = _field(row, "ResourceId", "resourceId")
    if (
        not isinstance(request_id, str)
        or not _UUID_RE.fullmatch(request_id)
        or not isinstance(candidate, str)
        or candidate.lower() != resource_id.lower()
        or _field(row, "Resource", "resource") != "NaC M365 BFF"
        or _field(row, "Scope", "scope") != DELEGATED_SCOPE
    ):
        raise ActivationStepError("SPFX_BFF_PERMISSION_REQUEST_UNEXPECTED")
    return rows


def _validate_site_app_instances(value: object) -> None:
    rows = _object_rows(value)
    exact = [
        row
        for row in rows
        if str(_field(row, "ProductId", "productId") or "").lower()
        == SOLUTION_PRODUCT_ID
    ]
    collisions = [
        row
        for row in rows
        if str(_field(row, "Name", "name", "Title", "title") or "").lower()
        == PACKAGE_NAME.lower()
        and row not in exact
    ]
    if len(exact) > 1 or collisions:
        raise ActivationStepError("SPFX_SITE_APP_BOUNDARY_FAILED")


def _validate_target_pages(value: object) -> None:
    rows = _object_rows(value)
    matches = [
        row
        for row in rows
        if str(_field(row, "Name", "name", "FileLeafRef") or "").lower()
        == PAGE_NAME.lower()
    ]
    if len(matches) > 1:
        raise ActivationStepError("SPFX_TARGET_PAGE_DUPLICATE")


def _object_rows(value: object) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get("value")
    return _rows(value)


def _field(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        if name in row:
            return row[name]
    lowered = {str(key).lower(): value for key, value in row.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _stable_file_bytes(source: Path) -> bytes:
    descriptor = -1
    flags = (
        os.O_RDONLY
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        named_before = source.lstat()
        descriptor = os.open(source, flags)
        before = os.fstat(descriptor)
        if (
            stat.S_ISLNK(named_before.st_mode)
            or not stat.S_ISREG(before.st_mode)
            or before.st_uid not in {0, os.geteuid()}
            or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (before.st_dev, before.st_ino)
            != (named_before.st_dev, named_before.st_ino)
        ):
            raise OSError
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        named_after = source.lstat()
        signature = lambda value: (
            value.st_dev,
            value.st_ino,
            value.st_mode,
            value.st_uid,
            value.st_gid,
            value.st_size,
            value.st_mtime_ns,
            value.st_ctime_ns,
        )
        if (
            signature(before) != signature(after)
            or signature(after) != signature(named_after)
        ):
            raise OSError
        return b"".join(chunks)
    except OSError:
        raise ActivationStepError("PREPARED_ARTIFACT_SNAPSHOT_FAILED") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _stable_file_sha256(source: Path) -> str:
    return hashlib.sha256(_stable_file_bytes(source)).hexdigest()


def _copy_snapshot(
    source: Path,
    destination: Path,
    *,
    expected_sha256: str,
) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ActivationStepError("PREPARED_ARTIFACT_SNAPSHOT_FAILED")
    payload = _stable_file_bytes(source)
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise ActivationStepError("PREPARED_ARTIFACT_HASH_MISMATCH")
    descriptor = -1
    try:
        if destination.exists() or destination.is_symlink():
            raise OSError
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = os.open(
            destination,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0),
            0o600,
        )
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError
            view = view[written:]
        os.fsync(descriptor)
        os.fchmod(descriptor, 0o400)
    except OSError:
        raise ActivationStepError("PREPARED_ARTIFACT_SNAPSHOT_FAILED") from None
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    _require_digest(expected_sha256, destination)


def _require_digest(expected: str, path: Path) -> None:
    if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ActivationStepError("BUILD_ARTIFACT_HASH_INVALID")
    if _stable_file_sha256(path) != expected:
        raise ActivationStepError("PREPARED_ARTIFACT_HASH_MISMATCH")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ActivationStepError("CONTRACT_INVALID") from None
    if not isinstance(value, dict):
        raise ActivationStepError("CONTRACT_INVALID")
    return value


def _sha256_json(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256_text(raw)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        raise ActivationStepError("BUILD_ARTIFACT_MISSING") from None


__all__ = [
    "AzureBffLiveExecutionPort",
    "GitHubApprovalVerifier",
    "LocalBuildAdapter",
    "build_live_activation_execution_port",
]
