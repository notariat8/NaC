from __future__ import annotations

import ctypes
from dataclasses import dataclass
from pathlib import Path
import os
import re
import sys
from typing import Any, Protocol

from .activation_security_backend import get_platform_security_backend


PLATFORM_SECURITY_BACKEND_UNAVAILABLE = (
    "PLATFORM_SECURITY_BACKEND_UNAVAILABLE"
)
PLATFORM_BOUNDARY_SCHEMA_VERSION = "nac.platform-security-boundary/v0.1"
_SAFE_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


class ActivationExecutionPort(Protocol):
    def verify_prewrite(
        self, context: "ActivationContext", request: "LiveActivationRequest"
    ) -> dict[str, Any]: ...

    def execute_step(
        self, step_id: str, context: "ActivationContext"
    ) -> dict[str, Any]: ...


class ActivationStepError(RuntimeError):
    def __init__(self, code: str) -> None:
        if type(code) is str and "SECRET_SENTINEL" in code.upper():
            safe_code = "SENSITIVE_VALUE_REJECTED"
        else:
            safe_code = (
                code
                if type(code) is str and _SAFE_CODE_RE.fullmatch(code)
                else "STEP_FAILED"
            )
        super().__init__(safe_code)
        self.code = safe_code


@dataclass(frozen=True, slots=True)
class LiveActivationRequest:
    expected_activation_hash: str
    approved_commit: str
    approved_tree: str
    owner_approval_reference: str
    approval_body_sha256: str
    azure_cli_toolchain_sha256: str
    m365_cli_sha256: str
    m365_node_sha256: str
    build_python_sha256: str
    build_node_sha256: str
    build_npm_cli_sha256: str
    gh_cli_sha256: str
    provisioner_certificate_sha256: str
    provisioner_bootstrap_binding_sha256: str
    reason: str
    correlation_id: str
    owner_approved: bool
    execute_live_activation: bool
    resume: bool = False

    @property
    def toolchain_attestations(self) -> dict[str, str]:
        return {
            "azure_cli_toolchain_sha256": self.azure_cli_toolchain_sha256,
            "m365_cli_sha256": self.m365_cli_sha256,
            "m365_node_sha256": self.m365_node_sha256,
            "build_python_sha256": self.build_python_sha256,
            "build_node_sha256": self.build_node_sha256,
            "build_npm_cli_sha256": self.build_npm_cli_sha256,
            "gh_cli_sha256": self.gh_cli_sha256,
            "provisioner_certificate_sha256": self.provisioner_certificate_sha256,
        }

    @property
    def toolchain_attestations_sha256(self) -> str:
        import hashlib
        import json

        encoded = (
            json.dumps(
                self.toolchain_attestations,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            )
            + "\n"
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ActivationContext:
    repo_root: Path
    run_dir: Path
    correlation_reference_sha256: str
    reason_sha256: str
    activation_hash: str
    approved_commit: str
    approved_tree: str


def hermetic_posix_primitives_available() -> bool:
    """Report local POSIX primitives without authorizing a live backend."""

    if os.name == "posix" and sys.platform == "linux":
        if not Path("/proc/self/fd").is_dir():
            return False
        required_os_capabilities = (
            "geteuid",
            "memfd_create",
            "MFD_ALLOW_SEALING",
            "O_CLOEXEC",
            "O_NOFOLLOW",
        )
        if any(not hasattr(os, name) for name in required_os_capabilities):
            return False
        try:
            import fcntl
            import pwd

            libc = ctypes.CDLL(None, use_errno=True)
        except (ImportError, OSError):
            return False
        return all(
            hasattr(fcntl, name)
            for name in (
                "F_ADD_SEALS",
                "F_GET_SEALS",
                "F_SEAL_WRITE",
                "F_SEAL_GROW",
                "F_SEAL_SHRINK",
                "F_SEAL_SEAL",
                "LOCK_EX",
                "LOCK_NB",
                "LOCK_UN",
                "flock",
            )
        ) and callable(getattr(pwd, "getpwuid", None)) and all(
            hasattr(libc, name) for name in ("mount", "prctl", "unshare")
        )
    return platform_security_backend_available()


def platform_security_backend_available() -> bool:
    """Report only a complete platform backend suitable for live boundaries."""

    try:
        get_platform_security_backend()
    except (ImportError, OSError, RuntimeError):
        return False
    return True


def require_platform_security_backend() -> None:
    if not platform_security_backend_available():
        raise ActivationStepError(PLATFORM_SECURITY_BACKEND_UNAVAILABLE)


__all__ = [
    "ActivationContext",
    "ActivationExecutionPort",
    "ActivationStepError",
    "LiveActivationRequest",
    "PLATFORM_BOUNDARY_SCHEMA_VERSION",
    "PLATFORM_SECURITY_BACKEND_UNAVAILABLE",
    "hermetic_posix_primitives_available",
    "platform_security_backend_available",
    "require_platform_security_backend",
]
