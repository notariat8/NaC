from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from typing import Mapping

from .azure_live_commands import calculate_azure_cli_toolchain_sha256
from nac_m365_graph.node_runtime_integrity import build_node_runtime_manifest


_SCHEMA_VERSION = "nac.m365-azure-bff-activation-attestations/v1"
TOOLCHAIN_ATTESTATION_FIELDS = (
    "azure_cli_toolchain_sha256",
    "m365_cli_sha256",
    "m365_node_sha256",
    "build_python_sha256",
    "build_node_sha256",
    "build_npm_cli_sha256",
    "gh_cli_sha256",
    "provisioner_certificate_sha256",
)
LIVE_CLI_ARGUMENT_BY_ATTESTATION = {
    name: "--" + name.removesuffix("_sha256").replace("_", "-") + "-sha256"
    for name in TOOLCHAIN_ATTESTATION_FIELDS
}
AZURE_CLI_EXECUTION_PATH = Path("/tmp/nac-azure-cli-venv/bin/az")
M365_CLI_EXECUTION_PATH = Path(
    "/tmp/nac-m365-tools/m365-cli/lib/node_modules/"
    "@pnp/cli-microsoft365/dist/index.js"
)
M365_NODE_EXECUTION_PATH = Path(
    "/tmp/nac-m365-tools/node-v24.18.0-linux-x64/bin/node"
)
BUILD_PYTHON_EXECUTION_PATH = Path("/usr/bin/python3.14")
BUILD_NODE_EXECUTION_PATH = Path("/tmp/node-v22.23.1-linux-x64/bin/node")
BUILD_NPM_CLI_EXECUTION_PATH = Path(
    "/tmp/node-v22.23.1-linux-x64/lib/node_modules/npm/bin/npm-cli.js"
)
GH_CLI_EXECUTION_PATH = Path("/usr/bin/gh")

_WIN_AZURE_CLI_EXECUTION_PATH = Path(
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft SDKs\Azure\CLI2\wbin\az.cmd")
)
_WIN_M365_CLI_EXECUTION_PATH = Path(
    os.path.expandvars(r"%APPDATA%\npm\node_modules\@pnp\cli-microsoft365\dist\index.js")
)
_WIN_M365_NODE_EXECUTION_PATH = Path(
    os.path.expandvars(r"%ProgramFiles%\nodejs\node.exe")
)
_WIN_BUILD_PYTHON_EXECUTION_PATH = Path(sys.executable)
_WIN_BUILD_NODE_EXECUTION_PATH = Path(
    os.path.expandvars(r"%ProgramFiles%\nodejs\node.exe")
)
_WIN_BUILD_NPM_CLI_EXECUTION_PATH = Path(
    os.path.expandvars(r"%ProgramFiles%\nodejs\node_modules\npm\bin\npm-cli.js")
)
_WIN_GH_CLI_EXECUTION_PATH = Path(
    os.path.expandvars(r"%ProgramFiles%\GitHub CLI\gh.exe")
)

_IS_WINDOWS = os.name == "nt"

_EXECUTION_PATHS = {
    "azure_cli": _WIN_AZURE_CLI_EXECUTION_PATH if _IS_WINDOWS else AZURE_CLI_EXECUTION_PATH,
    "m365_cli": _WIN_M365_CLI_EXECUTION_PATH if _IS_WINDOWS else M365_CLI_EXECUTION_PATH,
    "m365_node": _WIN_M365_NODE_EXECUTION_PATH if _IS_WINDOWS else M365_NODE_EXECUTION_PATH,
    "build_python": _WIN_BUILD_PYTHON_EXECUTION_PATH if _IS_WINDOWS else BUILD_PYTHON_EXECUTION_PATH,
    "build_node": _WIN_BUILD_NODE_EXECUTION_PATH if _IS_WINDOWS else BUILD_NODE_EXECUTION_PATH,
    "build_npm_cli": _WIN_BUILD_NPM_CLI_EXECUTION_PATH if _IS_WINDOWS else BUILD_NPM_CLI_EXECUTION_PATH,
    "gh_cli": _WIN_GH_CLI_EXECUTION_PATH if _IS_WINDOWS else GH_CLI_EXECUTION_PATH,
}


def build_activation_attestation_plan(
    *,
    provisioner_certificate_path: Path,
    azure_cli_path: Path | None = None,
    m365_cli_path: Path | None = None,
    m365_node_path: Path | None = None,
    build_python_path: Path | None = None,
    build_node_path: Path | None = None,
    build_npm_cli_path: Path | None = None,
    gh_cli_path: Path | None = None,
) -> dict[str, object]:
    """Measure only public/local execution material for the consolidated gate."""

    requested_paths = {
        "azure_cli": azure_cli_path,
        "m365_cli": m365_cli_path,
        "m365_node": m365_node_path,
        "build_python": build_python_path,
        "build_node": build_node_path,
        "build_npm_cli": build_npm_cli_path,
        "gh_cli": gh_cli_path,
    }
    if any(
        value is not None and Path(value) != _EXECUTION_PATHS[name]
        for name, value in requested_paths.items()
    ):
        return {
            "schema_version": _SCHEMA_VERSION,
            "status": "NOT_READY",
            "error": {"code": "EXECUTION_ATTESTATION_PATH_MISMATCH"},
            "reads_private_key": False,
            "executes_provider_requests": False,
        }
    paths = {
        **_EXECUTION_PATHS,
        "provisioner_certificate": provisioner_certificate_path,
    }
    azure_digest = calculate_azure_cli_toolchain_sha256(paths["azure_cli"])
    measured = {
        "azure_cli_toolchain_sha256": azure_digest,
        "m365_cli_sha256": _trusted_node_runtime_digest(paths["m365_cli"]),
        "m365_node_sha256": _trusted_file_sha256(paths["m365_node"], executable=True),
        "build_python_sha256": _trusted_file_sha256(
            paths["build_python"], executable=True
        ),
        "build_node_sha256": _trusted_file_sha256(paths["build_node"], executable=True),
        "build_npm_cli_sha256": _trusted_node_runtime_digest(
            paths["build_npm_cli"]
        ),
        "gh_cli_sha256": _trusted_file_sha256(paths["gh_cli"], executable=True),
        "provisioner_certificate_sha256": _trusted_file_sha256(
            paths["provisioner_certificate"], executable=False
        ),
    }
    if tuple(measured) != TOOLCHAIN_ATTESTATION_FIELDS or any(value is None for value in measured.values()):
        return {
            "schema_version": _SCHEMA_VERSION,
            "status": "NOT_READY",
            "error": {"code": "EXECUTION_ATTESTATION_INPUT_UNTRUSTED"},
            "reads_private_key": False,
            "executes_provider_requests": False,
        }
    attestations = {name: str(measured[name]) for name in TOOLCHAIN_ATTESTATION_FIELDS}
    combined = calculate_toolchain_attestations_sha256(attestations)
    return {
        "schema_version": _SCHEMA_VERSION,
        "status": "READY",
        "toolchain_attestations": attestations,
        "toolchain_attestations_sha256": combined,
        "live_cli_arguments": {
            LIVE_CLI_ARGUMENT_BY_ATTESTATION[name]: attestations[name]
            for name in TOOLCHAIN_ATTESTATION_FIELDS
        },

        "reads_private_key": False,
        "executes_provider_requests": False,
    }


def _trusted_file_sha256(path: Path, *, executable: bool) -> str | None:
    path = Path(path)
    if _IS_WINDOWS:
        return _trusted_file_sha256_win(path, executable=executable)
    if not path.is_absolute() or not _trusted_parent_chain(path.parent):
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
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                return None
            digest = hashlib.sha256()
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
            final = os.fstat(descriptor)
            if (
                (final.st_dev, final.st_ino, final.st_size, final.st_mtime_ns)
                != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
            ):
                return None
            return digest.hexdigest()
        finally:
            os.close(descriptor)
    except OSError:
        return None


def _trusted_node_runtime_digest(entrypoint: Path) -> str | None:
    try:
        return build_node_runtime_manifest(Path(entrypoint).parent.parent).digest
    except (OSError, RuntimeError):
        return None


def _trusted_parent_chain(path: Path) -> bool:
    if _IS_WINDOWS:
        return _trusted_parent_chain_win(path)
    current = path
    try:
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


def _trusted_file_sha256_win(path: Path, *, executable: bool) -> str | None:
    """Windows-native SHA-256 verification without POSIX dependencies."""
    try:
        from .azure_live_commands_win import verified_sha256
        return verified_sha256(path)
    except ImportError:
        # Fallback: basic hash on Windows if win module unavailable
        if not path.is_absolute() or not path.is_file():
            return None
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()


def _trusted_parent_chain_win(path: Path) -> bool:
    """Windows parent chain check: verify path exists and is accessible."""
    try:
        current = path
        while current != current.parent:
            if not current.exists() or not current.is_dir():
                return False
            current = current.parent
    except OSError:
        return False
    return True


def calculate_toolchain_attestations_sha256(
    value: Mapping[str, str],
) -> str:
    payload = (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
