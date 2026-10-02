from __future__ import annotations

import json
import re
from typing import Any


TECHNICAL_OWNER_UPN = "funktion8@funktion8.de"
TEAM_OWNER_POLICY = {
    "technical_owner_user_principal_name": TECHNICAL_OWNER_UPN,
    "sole_team_owner_required": True,
    "standard_user_team_role": "member",
    "verify_group_and_team_owners_before_first_write": True,
    "automatic_existing_owner_migration_allowed": False,
}


def matches_owner_policy(value: Any) -> bool:
    # JSON comparison also rejects integers standing in for policy booleans.
    return isinstance(value, dict) and json.dumps(value, sort_keys=True) == json.dumps(
        TEAM_OWNER_POLICY, sort_keys=True
    )


def bound_workspaces(state: dict[str, Any]) -> list[dict[str, Any]]:
    workspaces = state.get("workspaces")
    if not isinstance(workspaces, list) or not workspaces:
        raise RuntimeError("team-owner preflight requires non-empty target workspaces")
    seen_ids: set[str] = set()
    seen_teams: set[str] = set()
    for workspace in workspaces:
        if not isinstance(workspace, dict):
            raise RuntimeError("team-owner preflight requires complete workspace bindings")
        workspace_id = workspace.get("id")
        team_id = workspace.get("team_id")
        if (not isinstance(workspace_id, str)
                or workspace_id not in {"notary_team_01", "notary_team_02"}
                or not isinstance(team_id, str) or not re.fullmatch(r"[A-Za-z0-9-]+", team_id)
                or not isinstance(workspace.get("team_display_name"), str)
                or not workspace["team_display_name"].strip()
                or not isinstance(workspace.get("site_id"), str)
                or not workspace["site_id"].strip()
                or workspace_id in seen_ids or team_id in seen_teams):
            raise RuntimeError("team-owner preflight requires unique, complete target bindings")
        seen_ids.add(workspace_id)
        seen_teams.add(team_id)
    return workspaces
