from __future__ import annotations

import configparser
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from nac_bff.azure_activation import FUNCTION_APP, LOCATION, RESOURCE_GROUP
from nac_bff.azure_cli_sealed_runtime import (
    SealedAzureCliRuntime,
    prepare_sealed_azure_cli_runtime,
    sealed_runtime_failure_code,
)
from nac_m365_graph.sealed_toolchain import (
    SealedToolchainError,
    sealed_artifacts,
)


EXPECTED_TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
EXPECTED_SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
EXPECTED_CLOUD_NAME = "AzureCloud"
AZURE_CLI_TOOLCHAIN_SHA256_ENV = "NAC_AZURE_CLI_EXPECTED_TOOLCHAIN_SHA256"
# Compatibility symbol for callers importing the former constant. The value now
# names the full toolchain attestation, never a wrapper-only digest.
AZURE_CLI_SHA256_ENV = AZURE_CLI_TOOLCHAIN_SHA256_ENV

# The isolated CLI used by the Azure activation lane is preferred over host tools.
AZURE_CLI_CANDIDATES = (
    Path("/tmp/nac-azure-cli-venv/bin/az"),
    Path("/usr/local/bin/az"),
    Path("/usr/bin/az"),
    Path("/opt/az/bin/az"),
)

ALLOWED_COMMAND_PREFIXES = (
    ("account", "show"),
    ("provider", "show"),
    ("provider", "register"),
    ("group", "exists"),
    ("group", "show"),
    ("group", "create"),
    ("deployment", "group", "create"),
    ("deployment", "group", "show"),
    ("resource", "list"),
    ("functionapp", "deployment", "source", "config-zip"),
)

_PROVIDER_NAMESPACES = frozenset(
    {"Microsoft.Web", "Microsoft.Storage", "Microsoft.OperationalInsights"}
)
_DEPLOYMENT_NAME_RE = re.compile(r"nac-bff-[0-9a-f]{12}\Z")
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z",
    re.IGNORECASE,
)

_ENV_ALLOWLIST = frozenset(
    {
        "AZURE_CONFIG_DIR",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "TMPDIR",
    }
)
_ACCOUNT_SHOW = ("account", "show")
_MAX_ARG_LENGTH = 16_384
_ATTESTATION_SCHEMA = "nac-azure-cli-toolchain-attestation-v1"
_PYTHON_NAME_RE = re.compile(r"python(?:\d+(?:\.\d+)*)?\Z")
_MAX_CLOUD_SELECTION_BYTES = 4096
_MAX_INTERPRETER_LINKS = 8
_FILE_CHUNK_SIZE = 1024 * 1024


class AzureCliAdapter:
    """Fail-closed process boundary for the owner-gated Azure BFF runner."""

    def __init__(
        self,
        *,
        binary: str | os.PathLike[str] | None = None,
        expected_binary_sha256: str | None = None,
        environ: Mapping[str, str] | None = None,
        timeout_seconds: float = 120,
    ) -> None:
        self._binary = binary
        self._expected_binary_sha256 = expected_binary_sha256
        self._environ = None if environ is None else dict(environ)
        self._timeout_seconds = timeout_seconds

    def run(self, argv: object) -> dict[str, object]:
        return run_azure_cli(
            argv,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=self._timeout_seconds,
        )

    def run_bound(
        self,
        argv: object,
        bound_artifacts: Mapping[str, tuple[Path, str]],
    ) -> dict[str, object]:
        return run_azure_cli(
            argv,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=self._timeout_seconds,
            bound_artifacts=bound_artifacts,
        )

    def check_readiness(self) -> dict[str, object]:
        return check_azure_cli_readiness(
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=self._timeout_seconds,
        )


def resolve_azure_cli_binary(
    explicit: str | os.PathLike[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    expected_sha256: str | None = None,
) -> Path | None:
    """Resolve az only across an absolute, locally trusted runtime boundary."""

    expected_sha256 = _runtime_expected_sha256(expected_sha256, environ)
    if explicit is not None:
        try:
            explicit_path = Path(explicit).expanduser()
        except TypeError:
            return None
        resolved, _code = _executable_path(explicit_path, expected_sha256=expected_sha256)
        return resolved

    for candidate in AZURE_CLI_CANDIDATES:
        resolved, _code = _executable_path(candidate, expected_sha256=expected_sha256)
        if resolved is not None:
            return resolved
    return None


def build_azure_cli_env(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Copy only non-credential settings needed by the local Azure CLI."""

    source = os.environ if environ is None else environ
    child = {
        key: value
        for key, value in source.items()
        if key in _ENV_ALLOWLIST and isinstance(value, str) and value
    }
    child["PATH"] = "/usr/bin:/bin"
    child["AZURE_CORE_COLLECT_TELEMETRY"] = "0"
    child["AZURE_CORE_NO_COLOR"] = "true"
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    child["PYTHONNOUSERSITE"] = "1"
    child["PYTHONSAFEPATH"] = "1"
    return child


def run_azure_cli(
    argv: object,
    *,
    binary: str | os.PathLike[str] | None = None,
    expected_binary_sha256: str | None = None,
    environ: Mapping[str, str] | None = None,
    timeout_seconds: float = 120,
    bound_artifacts: Mapping[str, tuple[Path, str]] | None = None,
) -> dict[str, object]:
    """Run one allowlisted Azure CLI command and return parsed JSON only."""

    command, family, validation_code = _validated_command(argv)
    if command is None or family is None:
        return _command_result(
            ok=False,
            code=validation_code,
            command=None,
        )

    bindings = tuple((bound_artifacts or {}).items())
    if any(
        sum(
            token == argument or token == f"@{argument}"
            for token in command
        ) != 1
        for argument, _ in bindings
    ):
        return _command_result(
            ok=False,
            code="AZURE_CLI_ARTIFACT_BINDING_INVALID",
            command=family,
        )

    cloud_config_code, cloud_selection_sha256 = _azure_cloud_config_boundary(
        environ
    )
    if cloud_config_code is not None:
        return _command_result(
            ok=False,
            code=cloud_config_code,
            command=family,
        )

    resolved_binary, binary_code = _resolve_azure_cli_binary(
        binary,
        environ=environ,
        expected_sha256=expected_binary_sha256,
    )
    if resolved_binary is None:
        return _command_result(
            ok=False,
            code=binary_code,
            command=family,
        )
    if (
        not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        return _command_result(
            ok=False,
            code="AZURE_CLI_TIMEOUT_INVALID",
            command=family,
        )

    azure_argv = [*command]
    if family != _ACCOUNT_SHOW and not any(
        token == "--subscription" or token.startswith("--subscription=")
        for token in command
    ):
        azure_argv.extend(["--subscription", EXPECTED_SUBSCRIPTION_ID])
    azure_argv.extend(["--output", "json", "--only-show-errors"])

    # Resolve performs the preflight attestation. Re-attest immediately before
    # process creation so wrapper, interpreter, venv and packages cannot change
    # unnoticed between readiness and execution.
    expected_attestation = _runtime_expected_sha256(
        expected_binary_sha256,
        environ,
    )
    rechecked_binary, recheck_code = _executable_path(
        resolved_binary,
        expected_sha256=expected_attestation,
    )
    if rechecked_binary != resolved_binary:
        return _command_result(
            ok=False,
            code=recheck_code,
            command=family,
        )

    runtime = _prepare_bound_runtime(
        resolved_binary,
        expected_sha256=expected_attestation,
        cloud_selection_sha256=cloud_selection_sha256,
    )
    if runtime is None:
        return _command_result(
            ok=False,
            code="AZURE_CLI_RUNTIME_BINDING_FAILED",
            command=family,
        )

    try:
        with ExitStack() as stack:
            stack.enter_context(runtime)
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
            bound_argv = [
                (
                    f"@{replacements[token[1:]]}"
                    if token.startswith("@") and token[1:] in replacements
                    else replacements.get(token, token)
                )
                for token in azure_argv
            ]
            artifact_fds = (
                artifact_sealed.pass_fds
                if artifact_sealed is not None
                else ()
            )
            completed = subprocess.run(
                runtime.command(bound_argv),
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                stdin=subprocess.DEVNULL,
                timeout=timeout_seconds,
                env=build_azure_cli_env(environ),
                pass_fds=runtime.pass_fds + artifact_fds,
            )
    except SealedToolchainError:
        return _command_result(
            ok=False,
            code="AZURE_CLI_ARTIFACT_BINDING_FAILED",
            command=family,
        )
    except subprocess.TimeoutExpired:
        return _command_result(
            ok=False,
            code="AZURE_CLI_TIMEOUT",
            command=family,
        )
    except (OSError, subprocess.SubprocessError):
        return _command_result(
            ok=False,
            code="AZURE_CLI_EXECUTION_FAILED",
            command=family,
        )

    if completed.returncode != 0:
        runtime_code = sealed_runtime_failure_code(completed.returncode)
        return _command_result(
            ok=False,
            code=runtime_code or "AZURE_CLI_COMMAND_FAILED",
            command=family,
            returncode=completed.returncode,
        )

    try:
        data = json.loads(completed.stdout)
    except (TypeError, json.JSONDecodeError):
        return _command_result(
            ok=False,
            code="AZURE_CLI_OUTPUT_INVALID",
            command=family,
            returncode=completed.returncode,
        )
    return _command_result(
        ok=True,
        code="AZURE_CLI_OK",
        command=family,
        returncode=completed.returncode,
        data=data,
    )


def check_azure_cli_readiness(
    *,
    binary: str | os.PathLike[str] | None = None,
    expected_binary_sha256: str | None = None,
    environ: Mapping[str, str] | None = None,
    timeout_seconds: float = 30,
) -> dict[str, object]:
    """Verify the active Azure account is the one fixed by the activation plan."""

    resolved_binary, binary_code = _resolve_azure_cli_binary(
        binary,
        environ=environ,
        expected_sha256=expected_binary_sha256,
    )
    if resolved_binary is None:
        return _readiness_result(
            code=binary_code,
            binary_ready=False,
            account_ready=False,
            tenant_ready=False,
            subscription_ready=False,
        )

    account_result = run_azure_cli(
        ["account", "show"],
        binary=resolved_binary,
        expected_binary_sha256=expected_binary_sha256,
        environ=environ,
        timeout_seconds=timeout_seconds,
    )
    if not account_result["ok"]:
        return _readiness_result(
            code=str(account_result["code"]),
            binary_ready=True,
            account_ready=False,
            tenant_ready=False,
            subscription_ready=False,
        )

    account = account_result.get("data")
    if not isinstance(account, dict):
        return _readiness_result(
            code="AZURE_CLI_ACCOUNT_INVALID",
            binary_ready=True,
            account_ready=False,
            tenant_ready=False,
            subscription_ready=False,
        )

    cloud_ready = account.get("environmentName") == EXPECTED_CLOUD_NAME
    tenant_ready = account.get("tenantId") == EXPECTED_TENANT_ID
    subscription_ready = account.get("id") == EXPECTED_SUBSCRIPTION_ID
    if not cloud_ready:
        code = "AZURE_CLI_CLOUD_MISMATCH"
    elif not tenant_ready:
        code = "AZURE_CLI_TENANT_MISMATCH"
    elif not subscription_ready:
        code = "AZURE_CLI_SUBSCRIPTION_MISMATCH"
    else:
        code = "AZURE_CLI_READY"
    return _readiness_result(
        code=code,
        binary_ready=True,
        account_ready=True,
        cloud_ready=cloud_ready,
        tenant_ready=tenant_ready,
        subscription_ready=subscription_ready,
    )


def _azure_cloud_config_boundary(
    environ: Mapping[str, str] | None,
) -> tuple[str | None, str | None]:
    source = os.environ if environ is None else environ
    configured = source.get("AZURE_CONFIG_DIR")
    if configured:
        config_root = Path(configured).expanduser()
    else:
        home = source.get("HOME")
        if not home:
            return "AZURE_CLI_CONFIG_HOME_MISSING", None
        config_root = Path(home).expanduser() / ".azure"
    if not config_root.is_absolute():
        return "AZURE_CLI_CONFIG_PATH_INVALID", None
    try:
        config_root.lstat()
    except FileNotFoundError:
        return None, None
    except OSError:
        return "AZURE_CLI_CONFIG_UNTRUSTED", None
    if not _strict_directory(config_root, allowed_uids={0, os.geteuid()}):
        return "AZURE_CLI_CONFIG_UNTRUSTED", None
    cloud_selection = config_root / "clouds.config"
    try:
        cloud_selection.lstat()
    except FileNotFoundError:
        return None, None
    except OSError:
        return "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED", None
    digest = _exact_default_cloud_selection_digest(cloud_selection)
    if digest is None:
        return "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED", None
    return None, digest


def _exact_default_cloud_selection_digest(path: Path) -> str | None:
    try:
        metadata = path.lstat()
    except OSError:
        return None
    if metadata.st_size > _MAX_CLOUD_SELECTION_BYTES:
        return None
    measurement = _stable_file_measurement(
        path,
        allowed_uids={0, os.geteuid()},
        prefix_length=_MAX_CLOUD_SELECTION_BYTES,
        expected_metadata=metadata,
        extra_flags=getattr(os, "O_NONBLOCK", 0),
    )
    if measurement is None:
        return None
    digest, raw = measurement
    if len(raw) != metadata.st_size:
        return None
    try:
        text = raw.decode("utf-8")
        parser = configparser.ConfigParser(
            interpolation=None,
            strict=True,
            empty_lines_in_values=False,
        )
        parser.optionxform = str
        parser.read_string(text)
    except (UnicodeDecodeError, configparser.Error):
        return None
    if parser.defaults() or parser.sections() != [EXPECTED_CLOUD_NAME]:
        return None
    selection = parser[EXPECTED_CLOUD_NAME]
    if (
        set(selection) != {"subscription"}
        or selection.get("subscription", "").strip()
        != EXPECTED_SUBSCRIPTION_ID
    ):
        return None
    return digest


@dataclass(frozen=True, slots=True)
class _CommandSchema:
    prefix: tuple[str, ...]
    required: frozenset[str] = frozenset()
    optional: frozenset[str] = frozenset()
    flags: frozenset[str] = frozenset()
    required_flags: frozenset[str] = frozenset()
    multi: frozenset[str] = frozenset()
    validators: Mapping[str, Callable[[tuple[str, ...]], bool]] | None = None


def _single_exact(expected: str) -> Callable[[tuple[str, ...]], bool]:
    return lambda values: values == (expected,)


def _single_in(expected: frozenset[str]) -> Callable[[tuple[str, ...]], bool]:
    return lambda values: len(values) == 1 and values[0] in expected


def _single_matching(pattern: re.Pattern[str]) -> Callable[[tuple[str, ...]], bool]:
    return lambda values: len(values) == 1 and pattern.fullmatch(values[0]) is not None


def _absolute_file(suffix: str, name: str | None = None) -> Callable[[tuple[str, ...]], bool]:
    def validate(values: tuple[str, ...]) -> bool:
        if len(values) != 1:
            return False
        path = Path(values[0])
        return path.is_absolute() and path.suffix == suffix and (
            name is None or path.name == name
        )

    return validate


def _deployment_parameters_file(values: tuple[str, ...]) -> bool:
    if len(values) != 1 or not values[0].startswith("@"):
        return False
    path = Path(values[0][1:])
    return (
        path.is_absolute()
        and path.name == "main.parameters.json"
        and path.suffix == ".json"
    )


def _resource_group_tags(values: tuple[str, ...]) -> bool:
    return set(values) == {
        "workload=nac-bff",
        "environment=test",
        "dataClassification=no-production-data",
    } and len(values) == 3


_COMMON_OPTIONAL = frozenset({"--subscription"})
_COMMON_VALIDATORS: dict[str, Callable[[tuple[str, ...]], bool]] = {
    "--subscription": _single_exact(EXPECTED_SUBSCRIPTION_ID)
}
_COMMAND_SCHEMAS = {
    ("account", "show"): _CommandSchema(("account", "show")),
    ("provider", "show"): _CommandSchema(
        ("provider", "show"),
        required=frozenset({"--namespace"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--namespace": _single_in(_PROVIDER_NAMESPACES),
            **_COMMON_VALIDATORS,
        },
    ),
    ("provider", "register"): _CommandSchema(
        ("provider", "register"),
        required=frozenset({"--namespace"}),
        optional=_COMMON_OPTIONAL,
        flags=frozenset({"--wait"}),
        required_flags=frozenset({"--wait"}),
        validators={
            "--namespace": _single_in(_PROVIDER_NAMESPACES),
            **_COMMON_VALIDATORS,
        },
    ),
    ("group", "exists"): _CommandSchema(
        ("group", "exists"),
        required=frozenset({"--name"}),
        optional=_COMMON_OPTIONAL,
        validators={"--name": _single_exact(RESOURCE_GROUP), **_COMMON_VALIDATORS},
    ),
    ("group", "show"): _CommandSchema(
        ("group", "show"),
        required=frozenset({"--name"}),
        optional=_COMMON_OPTIONAL,
        validators={"--name": _single_exact(RESOURCE_GROUP), **_COMMON_VALIDATORS},
    ),
    ("group", "create"): _CommandSchema(
        ("group", "create"),
        required=frozenset({"--name", "--location", "--tags"}),
        optional=_COMMON_OPTIONAL,
        multi=frozenset({"--tags"}),
        validators={
            "--name": _single_exact(RESOURCE_GROUP),
            "--location": _single_exact(LOCATION),
            "--tags": _resource_group_tags,
            **_COMMON_VALIDATORS,
        },
    ),
    ("resource", "list"): _CommandSchema(
        ("resource", "list"),
        required=frozenset({"--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("deployment", "group", "show"): _CommandSchema(
        ("deployment", "group", "show"),
        required=frozenset({"--name", "--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_matching(_DEPLOYMENT_NAME_RE),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("deployment", "group", "create"): _CommandSchema(
        ("deployment", "group", "create"),
        required=frozenset(
            {"--name", "--resource-group", "--template-file", "--parameters", "--mode"}
        ),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_matching(_DEPLOYMENT_NAME_RE),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            "--template-file": _absolute_file(".json", "main.json"),
            "--parameters": _deployment_parameters_file,
            "--mode": _single_exact("Incremental"),
            **_COMMON_VALIDATORS,
        },
    ),
    ("functionapp", "deployment", "source", "config-zip"): _CommandSchema(
        ("functionapp", "deployment", "source", "config-zip"),
        required=frozenset({"--resource-group", "--name", "--src", "--build-remote"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--resource-group": _single_exact(RESOURCE_GROUP),
            "--name": _single_exact(FUNCTION_APP),
            "--src": _absolute_file(".zip"),
            "--build-remote": _single_exact("true"),
            **_COMMON_VALIDATORS,
        },
    ),
}


def _validated_command(
    argv: object,
) -> tuple[list[str] | None, tuple[str, ...] | None, str]:
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence) or not argv:
        return None, None, "AZURE_CLI_ARGV_INVALID"

    command: list[str] = []
    for token in argv:
        if (
            not isinstance(token, str)
            or not token
            or len(token) > _MAX_ARG_LENGTH
            or "\x00" in token
            or "\n" in token
            or "\r" in token
        ):
            return None, None, "AZURE_CLI_ARGV_INVALID"
        command.append(token)

    family = next(
        (
            prefix
            for prefix in sorted(_COMMAND_SCHEMAS, key=len, reverse=True)
            if tuple(command[: len(prefix)]) == prefix
        ),
        None,
    )
    if family is None:
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    schema = _COMMAND_SCHEMAS[family]
    options: dict[str, tuple[str, ...]] = {}
    seen_flags: set[str] = set()
    index = len(family)
    while index < len(command):
        option = command[index]
        if not option.startswith("--") or "=" in option:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        if option in options or option in seen_flags:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        if option in schema.flags:
            seen_flags.add(option)
            index += 1
            continue
        if option not in schema.required and option not in schema.optional:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        index += 1
        values: list[str] = []
        if option in schema.multi:
            while index < len(command) and not command[index].startswith("--"):
                values.append(command[index])
                index += 1
        elif index < len(command) and not command[index].startswith("--"):
            values.append(command[index])
            index += 1
        if not values:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        options[option] = tuple(values)

    if not schema.required.issubset(options):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    if not schema.required_flags.issubset(seen_flags):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    validators = schema.validators or {}
    if any(not validators[option](values) for option, values in options.items()):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    return command, family, "AZURE_CLI_OK"


def _runtime_expected_sha256(
    explicit: str | None,
    environ: Mapping[str, str] | None,
) -> str | None:
    if explicit is not None:
        return explicit
    source = os.environ if environ is None else environ
    value = source.get(AZURE_CLI_TOOLCHAIN_SHA256_ENV)
    return value if isinstance(value, str) and value else None


def _resolve_azure_cli_binary(
    explicit: str | os.PathLike[str] | None,
    *,
    environ: Mapping[str, str] | None,
    expected_sha256: str | None,
) -> tuple[Path | None, str]:
    expected_sha256 = _runtime_expected_sha256(expected_sha256, environ)
    if explicit is not None:
        try:
            path = Path(explicit).expanduser()
        except TypeError:
            return None, "AZURE_CLI_BINARY_NOT_FOUND"
        return _executable_path(path, expected_sha256=expected_sha256)

    trust_failure: str | None = None
    for candidate in AZURE_CLI_CANDIDATES:
        resolved, code = _executable_path(
            candidate,
            expected_sha256=expected_sha256,
        )
        if resolved is not None:
            return resolved, "AZURE_CLI_BINARY_TRUSTED"
        if code != "AZURE_CLI_BINARY_NOT_FOUND" and trust_failure is None:
            trust_failure = code
    return None, trust_failure or "AZURE_CLI_BINARY_NOT_FOUND"


def _executable_path(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[Path | None, str]:
    if not path.is_absolute() or path.name != "az":
        return None, "AZURE_CLI_BINARY_NOT_FOUND"
    try:
        metadata = path.lstat()
    except (OSError, RuntimeError):
        return None, "AZURE_CLI_BINARY_NOT_FOUND"
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if metadata.st_uid not in {0, os.geteuid()}:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if not os.access(path, os.X_OK):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    attestation, attestation_code = _toolchain_attestation(path, metadata)
    if attestation is None:
        return None, attestation_code
    if attestation.requires_expected and expected_sha256 is None:
        return None, "AZURE_CLI_BINARY_ATTESTATION_REQUIRED"
    if expected_sha256 is not None:
        if not isinstance(expected_sha256, str):
            return None, "AZURE_CLI_BINARY_ATTESTATION_INVALID"
        normalized = expected_sha256.lower()
        if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
            return None, "AZURE_CLI_BINARY_ATTESTATION_INVALID"
        if attestation.digest != normalized:
            return None, "AZURE_CLI_BINARY_ATTESTATION_MISMATCH"
    return path, "AZURE_CLI_BINARY_TRUSTED"


def _prepare_bound_runtime(
    path: Path,
    *,
    expected_sha256: str | None,
    cloud_selection_sha256: str | None,
) -> SealedAzureCliRuntime | None:
    if expected_sha256 is None or not isinstance(expected_sha256, str):
        return None
    normalized = expected_sha256.lower()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        return None
    try:
        metadata = path.lstat()
    except OSError:
        return None
    attestation, _code = _toolchain_attestation(path, metadata)
    if (
        attestation is None
        or attestation.digest != normalized
        or attestation.interpreter_path is None
        or attestation.interpreter_digest is None
        or attestation.package_root is None
        or attestation.package_digest is None
        or not attestation.runtime_uids
    ):
        return None
    return prepare_sealed_azure_cli_runtime(
        package_root=attestation.package_root,
        package_digest=attestation.package_digest,
        interpreter_path=attestation.interpreter_path,
        interpreter_digest=attestation.interpreter_digest,
        allowed_uids=set(attestation.runtime_uids),
        cloud_selection_sha256=cloud_selection_sha256,
    )


def calculate_azure_cli_toolchain_sha256(
    path: str | os.PathLike[str],
) -> str | None:
    """Calculate a validated toolchain digest for offline owner binding.

    Execution never calls this helper to invent its own expected value. The
    returned digest must cross the owner/configuration boundary separately.
    """

    try:
        candidate = Path(path).expanduser()
        metadata = candidate.lstat()
    except (OSError, RuntimeError, TypeError):
        return None
    if not candidate.is_absolute() or candidate.name != "az":
        return None
    attestation, _code = _toolchain_attestation(candidate, metadata)
    return None if attestation is None else attestation.digest


@dataclass(frozen=True, slots=True)
class _ToolchainAttestation:
    digest: str
    requires_expected: bool
    interpreter_path: Path | None = None
    interpreter_digest: str | None = None
    package_root: Path | None = None
    package_digest: str | None = None
    runtime_uids: frozenset[int] = frozenset()


def _toolchain_attestation(
    path: Path,
    metadata: os.stat_result,
) -> tuple[_ToolchainAttestation | None, str]:
    measurement = _stable_file_measurement(
        path,
        allowed_uids={metadata.st_uid},
        executable=True,
        prefix_length=4097,
        expected_metadata=metadata,
    )
    if measurement is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    content_digest, prefix = measurement
    newline = prefix.find(b"\n")
    first_line = prefix if newline < 0 else prefix[: newline + 1]

    if first_line.startswith(b"\x7fELF"):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    if not first_line.startswith(b"#!") or len(first_line) > 4096:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    try:
        shebang = first_line[2:].strip().decode("ascii")
    except UnicodeDecodeError:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if not shebang or any(character.isspace() for character in shebang):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    interpreter = Path(shebang)
    if (
        not interpreter.is_absolute()
        or interpreter.parent != path.parent
        or _PYTHON_NAME_RE.fullmatch(interpreter.name) is None
    ):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    interpreter_records, interpreter_code = _python_interpreter_attestation(
        interpreter,
        allowed_uids={0, metadata.st_uid},
    )
    if interpreter_records is None:
        return None, interpreter_code
    interpreter_values = dict(interpreter_records)
    interpreter_path = Path(interpreter_values["interpreter_path"])
    interpreter_digest = interpreter_values["interpreter_content"]

    venv_root = path.parent.parent
    if not _strict_directory(venv_root, allowed_uids={0, metadata.st_uid}):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if not _strict_directory(path.parent, allowed_uids={0, metadata.st_uid}):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    pyvenv_digest = _stable_file_digest(
        venv_root / "pyvenv.cfg",
        allowed_uids={0, metadata.st_uid},
    )
    if pyvenv_digest is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    package_roots = sorted(venv_root.glob("lib/python*/site-packages"))
    if len(package_roots) != 1:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    package_root = package_roots[0]
    package_path_components = (
        venv_root / "lib",
        package_root.parent,
        package_root,
    )
    if any(
        not _strict_directory(component, allowed_uids={0, metadata.st_uid})
        for component in package_path_components
    ):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    azure_entrypoint = package_root / "azure" / "cli" / "__main__.py"
    if _stable_file_digest(
        azure_entrypoint,
        allowed_uids={0, metadata.st_uid},
    ) is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    package_digest = _stable_tree_digest(
        package_root,
        allowed_uids={0, metadata.st_uid},
    )
    if package_digest is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    source_root = path.parent / "src"
    if source_root.exists() or source_root.is_symlink():
        source_digest = _stable_tree_digest(
            source_root,
            allowed_uids={0, metadata.st_uid},
        )
        if source_digest is None:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
    else:
        source_digest = "ABSENT"

    digest = _attestation_digest(
        ("schema", _ATTESTATION_SCHEMA),
        ("kind", "python-venv-wrapper"),
        ("wrapper_path", str(path)),
        ("wrapper_mode", oct(stat.S_IMODE(metadata.st_mode))),
        ("wrapper_content", content_digest),
        ("shebang", shebang),
        *interpreter_records,
        ("venv_root", str(venv_root)),
        ("pyvenv", pyvenv_digest),
        ("package_root", str(package_root)),
        ("package_tree", package_digest),
        ("wrapper_src_tree", source_digest),
    )
    return (
        _ToolchainAttestation(
            digest=digest,
            requires_expected=True,
            interpreter_path=interpreter_path,
            interpreter_digest=interpreter_digest,
            package_root=package_root,
            package_digest=package_digest,
            runtime_uids=frozenset({0, metadata.st_uid}),
        ),
        "AZURE_CLI_BINARY_TRUSTED",
    )


def _python_interpreter_attestation(
    interpreter: Path,
    *,
    allowed_uids: set[int],
) -> tuple[tuple[tuple[str, str], ...] | None, str]:
    records: list[tuple[str, str]] = []
    current = interpreter
    seen: set[str] = set()
    for index in range(_MAX_INTERPRETER_LINKS + 1):
        normalized = os.path.abspath(os.fspath(current))
        if normalized in seen:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        seen.add(normalized)
        current = Path(normalized)
        try:
            metadata = current.lstat()
        except OSError:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        if metadata.st_uid not in allowed_uids:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        if stat.S_ISLNK(metadata.st_mode):
            if index == _MAX_INTERPRETER_LINKS:
                return None, "AZURE_CLI_BINARY_UNTRUSTED"
            try:
                target = os.readlink(current)
            except OSError:
                return None, "AZURE_CLI_BINARY_UNTRUSTED"
            records.extend(
                (
                    (f"interpreter_link_{index}_path", str(current)),
                    (f"interpreter_link_{index}_target", target),
                    (f"interpreter_link_{index}_uid", str(metadata.st_uid)),
                )
            )
            current = (
                Path(target)
                if os.path.isabs(target)
                else current.parent / target
            )
            continue
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or not os.access(current, os.X_OK)
        ):
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        measurement = _stable_file_measurement(
            current,
            allowed_uids={0},
            executable=True,
            prefix_length=4,
            expected_metadata=metadata,
        )
        if measurement is None:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        interpreter_digest, header = measurement
        if header != b"\x7fELF":
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        records.extend(
            (
                ("interpreter_path", str(current)),
                ("interpreter_mode", oct(stat.S_IMODE(metadata.st_mode))),
                ("interpreter_content", interpreter_digest),
            )
        )
        return tuple(records), "AZURE_CLI_BINARY_TRUSTED"
    return None, "AZURE_CLI_BINARY_UNTRUSTED"


def _strict_directory(path: Path, *, allowed_uids: set[int]) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISDIR(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and metadata.st_uid in allowed_uids
        and not metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    )


def _stable_file_digest(
    path: Path,
    *,
    allowed_uids: set[int],
    executable: bool = False,
    expected_metadata: os.stat_result | None = None,
) -> str | None:
    measurement = _stable_file_measurement(
        path,
        allowed_uids=allowed_uids,
        executable=executable,
        expected_metadata=expected_metadata,
    )
    return None if measurement is None else measurement[0]


def _stable_file_measurement(
    path: Path,
    *,
    allowed_uids: set[int],
    executable: bool = False,
    prefix_length: int = 0,
    expected_metadata: os.stat_result | None = None,
    extra_flags: int = 0,
) -> tuple[str, bytes] | None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | extra_flags
    )
    try:
        before_path = path.lstat()
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before_path.st_mode)
            or before.st_uid not in allowed_uids
            or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (executable and not before.st_mode & stat.S_IXUSR)
            or (before.st_dev, before.st_ino)
            != (before_path.st_dev, before_path.st_ino)
            or (
                expected_metadata is not None
                and _stat_signature(before_path)
                != _stat_signature(expected_metadata)
            )
        ):
            return None
        digest = hashlib.sha256()
        prefix = bytearray()
        while True:
            chunk = os.read(descriptor, _FILE_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            if len(prefix) < prefix_length:
                prefix.extend(chunk[: prefix_length - len(prefix)])
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after_path = path.lstat()
    except OSError:
        return None
    if (
        _stat_signature(before) != _stat_signature(after)
        or _stat_signature(after) != _stat_signature(after_path)
    ):
        return None
    return digest.hexdigest(), bytes(prefix)

def _stable_tree_digest(root: Path, *, allowed_uids: set[int]) -> str | None:
    if not _strict_directory(root, allowed_uids=allowed_uids):
        return None
    digest = hashlib.sha256()
    directory_snapshots: list[tuple[Path, tuple[int, ...]]] = []
    try:
        for current_text, directories, files in os.walk(
            root,
            topdown=True,
            followlinks=False,
        ):
            current = Path(current_text)
            current_metadata = current.lstat()
            if not _strict_directory(current, allowed_uids=allowed_uids):
                return None
            directory_snapshots.append(
                (current, _stat_signature(current_metadata))
            )
            directories.sort()
            files.sort()
            for name in directories:
                child = current / name
                metadata = child.lstat()
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or not stat.S_ISDIR(metadata.st_mode)
                ):
                    return None
                if (
                    metadata.st_uid not in allowed_uids
                    or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                ):
                    return None
                _attestation_update(
                    digest,
                    "directory",
                    child.relative_to(root).as_posix(),
                    str(metadata.st_uid),
                    oct(stat.S_IMODE(metadata.st_mode)),
                )
            for name in files:
                child = current / name
                metadata = child.lstat()
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or not stat.S_ISREG(metadata.st_mode)
                ):
                    return None
                child_digest = _stable_file_digest(
                    child,
                    allowed_uids=allowed_uids,
                )
                if child_digest is None:
                    return None
                _attestation_update(
                    digest,
                    "file",
                    child.relative_to(root).as_posix(),
                    str(metadata.st_uid),
                    oct(stat.S_IMODE(metadata.st_mode)),
                    child_digest,
                )
    except (OSError, RuntimeError, ValueError):
        return None
    for directory, signature in directory_snapshots:
        try:
            if _stat_signature(directory.lstat()) != signature:
                return None
        except OSError:
            return None
    return digest.hexdigest()


def _stat_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _attestation_digest(*records: tuple[str, str]) -> str:
    digest = hashlib.sha256()
    for key, value in records:
        _attestation_update(digest, key, value)
    return digest.hexdigest()


def _attestation_update(digest: object, *values: str) -> None:
    for value in values:
        encoded = value.encode("utf-8", errors="surrogateescape")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)

def _command_result(
    *,
    ok: bool,
    code: str,
    command: tuple[str, ...] | None,
    returncode: int | None = None,
    data: object = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "ok": ok,
        "status": (
            "PASSED"
            if ok
            else "BLOCKED"
            if code.startswith("AZURE_CLI_BINARY_")
            else "FAILED"
        ),
        "code": code,
        "command": None if command is None else " ".join(command),
    }
    if returncode is not None:
        result["returncode"] = returncode
    if ok:
        result["data"] = data
    return result


def _readiness_result(
    *,
    code: str,
    binary_ready: bool,
    account_ready: bool,
    cloud_ready: bool = False,
    tenant_ready: bool,
    subscription_ready: bool,
) -> dict[str, object]:
    ready = (
        binary_ready
        and account_ready
        and cloud_ready
        and tenant_ready
        and subscription_ready
    )
    return {
        "status": "READY" if ready else "NOT_READY",
        "ready": ready,
        "code": code,
        "bindings": {
            "cloud_name": EXPECTED_CLOUD_NAME,
            "tenant_id": EXPECTED_TENANT_ID,
            "subscription_id": EXPECTED_SUBSCRIPTION_ID,
        },
        "checks": [
            {"id": "binary", "status": "READY" if binary_ready else "NOT_READY"},
            {"id": "account", "status": "READY" if account_ready else "NOT_READY"},
            {"id": "cloud", "status": "READY" if cloud_ready else "NOT_READY"},
            {"id": "tenant", "status": "READY" if tenant_ready else "NOT_READY"},
            {
                "id": "subscription",
                "status": "READY" if subscription_ready else "NOT_READY",
            },
        ],
        "redaction": {
            "raw_stdout_included": False,
            "raw_stderr_included": False,
            "account_payload_included": False,
            "environment_values_included": False,
        },
    }
