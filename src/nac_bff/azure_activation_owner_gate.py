from __future__ import annotations

import json
import re
from pathlib import Path
import subprocess
from typing import Any, Callable

from .azure_activation import (
    activation_step_ids,
    build_azure_bff_activation_plan,
)
from .azure_activation_approval import (
    build_owner_approval_payload,
    canonical_owner_comment_body,
    owner_comment_body_sha256,
)
from .azure_activation_attestations import (
    LIVE_CLI_ARGUMENT_BY_ATTESTATION,
    TOOLCHAIN_ATTESTATION_FIELDS,
    build_activation_attestation_plan,
    calculate_toolchain_attestations_sha256,
)


SCHEMA_VERSION = "nac.m365-azure-bff-activation-owner-gate/v1"
CONTRACT_ID = "m365.azure_bff_activation_owner_gate"
COMMAND = "nac m365 teams-sharepoint bff-azure-activation-owner-gate"
_LIVE_CONTRACT = Path(
    "workflows/contracts/m365-azure-bff-live-activation.contract.json"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class _OwnerGateError(RuntimeError):
    pass


def build_activation_owner_gate(
    repo_root: Path,
    provisioner_certificate: Path,
    *,
    azure_cli_path: Path | None = None,
    m365_cli_path: Path | None = None,
    m365_node_path: Path | None = None,
    build_python_path: Path | None = None,
    build_node_path: Path | None = None,
    build_npm_cli_path: Path | None = None,
    gh_cli_path: Path | None = None,
    activation_plan_builder: Callable[[Path], dict[str, Any]] = (
        build_azure_bff_activation_plan
    ),
    attestation_builder: Callable[..., dict[str, Any]] = (
        build_activation_attestation_plan
    ),
) -> dict[str, Any]:
    try:
        root = repo_root.expanduser().resolve()
        before = _git_snapshot(root)
        if before[2]:
            raise _OwnerGateError("SOURCE_TREE_NOT_CLEAN")

        plan = activation_plan_builder(root)
        if plan.get("status") != "READY":
            raise _OwnerGateError("ACTIVATION_PLAN_NOT_READY")
        source_control = plan.get("source_control")
        if not isinstance(source_control, dict):
            raise _OwnerGateError("ACTIVATION_SOURCE_CONTROL_INVALID")
        if source_control.get("commit") != before[0]:
            raise _OwnerGateError("ACTIVATION_COMMIT_MISMATCH")

        attestations = attestation_builder(
            provisioner_certificate_path=provisioner_certificate,
            azure_cli_path=azure_cli_path,
            m365_cli_path=m365_cli_path,
            m365_node_path=m365_node_path,
            build_python_path=build_python_path,
            build_node_path=build_node_path,
            build_npm_cli_path=build_npm_cli_path,
            gh_cli_path=gh_cli_path,
        )
        if attestations.get("status") != "READY":
            raise _OwnerGateError("TOOLCHAIN_ATTESTATIONS_NOT_READY")
        measured = attestations.get("toolchain_attestations")
        combined = attestations.get("toolchain_attestations_sha256")
        live_cli_arguments = attestations.get("live_cli_arguments")
        if (
            not isinstance(measured, dict)
            or set(measured) != set(TOOLCHAIN_ATTESTATION_FIELDS)
            or any(
                not isinstance(value, str)
                or _SHA256_RE.fullmatch(value) is None
                for value in measured.values()
            )
            or not isinstance(combined, str)
            or _SHA256_RE.fullmatch(combined) is None
            or combined != calculate_toolchain_attestations_sha256(measured)
        ):
            raise _OwnerGateError("TOOLCHAIN_ATTESTATIONS_INVALID")
        expected_live_arguments = {
            LIVE_CLI_ARGUMENT_BY_ATTESTATION[name]: measured[name]
            for name in TOOLCHAIN_ATTESTATION_FIELDS
        }
        if live_cli_arguments != expected_live_arguments:
            raise _OwnerGateError("TOOLCHAIN_LIVE_ARGUMENTS_INVALID")

        contract = _load_json(root / _LIVE_CONTRACT)
        permission_boundary = contract.get("permission_boundary")
        bindings = plan.get("bindings")
        steps = plan.get("steps")
        if not isinstance(permission_boundary, dict):
            raise _OwnerGateError("PERMISSION_BOUNDARY_INVALID")
        if not isinstance(bindings, dict) or not isinstance(steps, list):
            raise _OwnerGateError("ACTIVATION_PLAN_SHAPE_INVALID")
        step_ids = [step.get("id") for step in steps if isinstance(step, dict)]
        if (
            len(step_ids) != len(steps)
            or tuple(step_ids) != activation_step_ids()
        ):
            raise _OwnerGateError("ACTIVATION_STEP_SEQUENCE_INVALID")

        payload = build_owner_approval_payload(
            activation_hash=str(plan.get("activation_hash", "")),
            approved_commit=before[0],
            approved_tree=before[1],
            toolchain_attestations_sha256=combined,
            bindings=bindings,
            permission_boundary=permission_boundary,
            step_ids=step_ids,
        )
        body = canonical_owner_comment_body(payload)

        after = _git_snapshot(root)
        if before != after or after[2]:
            raise _OwnerGateError("SOURCE_TREE_CHANGED_DURING_GATE_BUILD")

        return {
            "schema_version": SCHEMA_VERSION,
            "contract_id": CONTRACT_ID,
            "command": COMMAND,
            "status": "READY",
            "mode": "offline_owner_gate",
            "approved_commit": before[0],
            "approved_tree": before[1],
            "activation_hash": plan["activation_hash"],
            "toolchain_attestations_sha256": combined,
            "owner_approval_payload": payload,
            "owner_comment_body": body,
            "owner_comment_body_sha256": owner_comment_body_sha256(body),
            "live_cli_arguments": live_cli_arguments,
            "boundaries": {
                "network_accessed": False,
                "provider_requests_made": 0,
                "private_key_read": False,
                "tenant_writes_started": False,
            },
        }
    except _OwnerGateError as exc:
        error_code = str(exc)
    except Exception:
        error_code = "OWNER_GATE_GENERATION_FAILED"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "command": COMMAND,
        "status": "NOT_READY",
        "mode": "offline_owner_gate",
        "error_code": error_code,
        "boundaries": {
            "network_accessed": False,
            "provider_requests_made": 0,
            "private_key_read": False,
            "tenant_writes_started": False,
        },
    }


def format_activation_owner_gate(result: dict[str, Any]) -> str:
    lines = [f"STATUS: {result['status']}"]
    if result["status"] == "READY":
        lines.extend(
            [
                f"Commit: {result['approved_commit']}",
                f"Tree: {result['approved_tree']}",
                f"Activation hash: {result['activation_hash']}",
                f"Owner comment body SHA-256: {result['owner_comment_body_sha256']}",
                "Owner comment body:",
                result["owner_comment_body"],
            ]
        )
    else:
        lines.append(f"Error: {result.get('error_code', 'OWNER_GATE_NOT_READY')}")
    return "\n".join(lines) + "\n"


def _git_snapshot(root: Path) -> tuple[str, str, bool]:
    commit = _git_output(root, "rev-parse", "HEAD")
    tree = _git_output(root, "rev-parse", "HEAD^{tree}")
    dirty = bool(
        _git_output(root, "status", "--porcelain=v1", "--untracked-files=all")
    )
    return commit, tree, dirty


def _git_output(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["/usr/bin/git", "--no-optional-locks", "-C", str(root), *arguments],
        check=False,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=15,
    )
    if result.returncode != 0:
        raise _OwnerGateError("GIT_SNAPSHOT_UNAVAILABLE")
    return result.stdout.strip()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise _OwnerGateError("LIVE_CONTRACT_INVALID")
    return value
