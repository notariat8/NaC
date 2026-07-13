from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .mcp_runtime import DEFAULT_MCP_CONTRACT
from .privileged_change import DEFAULT_PROVISIONED_STATE


EXPECTED_WORKSPACE_ID = "notary_team_01"


class MvpTestEnvironmentBindingError(ValueError):
    """Raised when MVP test-environment inputs drift from canonical repo state."""


def validate_mvp_test_environment_binding(
    contract: dict[str, Any],
    provisioned_state: dict[str, Any],
    *,
    canonical_contract_path: Path = DEFAULT_MCP_CONTRACT,
    canonical_state_path: Path = DEFAULT_PROVISIONED_STATE,
) -> dict[str, str]:
    canonical_contract = _load_json_object(canonical_contract_path)
    canonical_state = _load_json_object(canonical_state_path)

    contract_sha256 = _canonical_sha256(contract)
    canonical_contract_sha256 = _canonical_sha256(canonical_contract)
    if contract_sha256 != canonical_contract_sha256:
        raise MvpTestEnvironmentBindingError("MCP_CONTRACT_BINDING_MISMATCH")

    state_sha256 = _canonical_sha256(provisioned_state)
    canonical_state_sha256 = _canonical_sha256(canonical_state)
    if state_sha256 != canonical_state_sha256:
        raise MvpTestEnvironmentBindingError("PROVISIONED_STATE_BINDING_MISMATCH")

    candidate_workspace = _single_workspace(provisioned_state, EXPECTED_WORKSPACE_ID)
    canonical_workspace = _single_workspace(canonical_state, EXPECTED_WORKSPACE_ID)
    _validate_workspace_identity(candidate_workspace, canonical_workspace)

    return {
        "contractSha256": contract_sha256,
        "provisionedStateSha256": state_sha256,
        "workspaceBindingSha256": _canonical_sha256(_workspace_binding(candidate_workspace)),
    }


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MvpTestEnvironmentBindingError("CANONICAL_BINDING_SOURCE_INVALID") from exc
    if not isinstance(payload, dict):
        raise MvpTestEnvironmentBindingError("CANONICAL_BINDING_SOURCE_INVALID")
    return payload


def _single_workspace(state: dict[str, Any], workspace_id: str) -> dict[str, Any]:
    workspaces = state.get("workspaces")
    if not isinstance(workspaces, list):
        raise MvpTestEnvironmentBindingError("WORKSPACE_BINDING_INVALID")
    matches = [
        workspace
        for workspace in workspaces
        if isinstance(workspace, dict) and workspace.get("id") == workspace_id
    ]
    if len(matches) != 1:
        raise MvpTestEnvironmentBindingError("WORKSPACE_BINDING_INVALID")
    return matches[0]


def _validate_workspace_identity(
    candidate: dict[str, Any], canonical: dict[str, Any]
) -> None:
    candidate_binding = _workspace_binding(candidate)
    canonical_binding = _workspace_binding(canonical)
    if candidate_binding != canonical_binding:
        raise MvpTestEnvironmentBindingError("WORKSPACE_RESOURCE_BINDING_MISMATCH")


def _workspace_binding(workspace: dict[str, Any]) -> dict[str, Any]:
    lists = workspace.get("lists")
    if not isinstance(lists, dict):
        raise MvpTestEnvironmentBindingError("WORKSPACE_LIST_BINDING_INVALID")
    list_ids: dict[str, str] = {}
    for name, value in lists.items():
        if (
            not isinstance(name, str)
            or not isinstance(value, dict)
            or not isinstance(value.get("id"), str)
            or not value["id"]
        ):
            raise MvpTestEnvironmentBindingError("WORKSPACE_LIST_BINDING_INVALID")
        list_ids[name] = value["id"]

    binding = {
        "workspace_id": workspace.get("id"),
        "team_id": workspace.get("team_id"),
        "site_id": workspace.get("site_id"),
        "site_url": workspace.get("site_url"),
        "list_ids": list_ids,
    }
    if any(not isinstance(binding[key], str) or not binding[key] for key in (
        "workspace_id",
        "team_id",
        "site_id",
        "site_url",
    )):
        raise MvpTestEnvironmentBindingError("WORKSPACE_RESOURCE_BINDING_INVALID")
    return binding


def _canonical_sha256(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
