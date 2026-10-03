"""Current direct membership proof for the fixed synthetic notary Team.

No roles or person mappings are inferred from membership. No positive cache.
"""
from __future__ import annotations

from urllib.parse import urlencode, quote
from uuid import UUID

from .synthetic_workspace_graph import GraphGetClient, SYNTHETIC_SITE_ID, _client_is_hardened

TEAM_ID = "124f1b11-207d-4307-bfd1-ac0fd73aa90a"
SITE_URL = "https://funktion8.sharepoint.com/sites/NaC-Notar-01"


def _path(suffix: str, query: dict[str, str]) -> str:
    return f"/groups/{TEAM_ID}{suffix}?" + urlencode(query, quote_via=quote)


MEMBERSHIP_PATHS = frozenset({
    _path("", {"$select": "id,groupTypes,resourceProvisioningOptions"}),
    _path("/sites/root", {"$select": "id,webUrl"}),
    _path("/members", {"$select": "id", "$top": "100"}),
})


def _subject(value: object) -> str | None:
    try:
        if type(value) is not str or len(value) != 36:
            return None
        parsed = UUID(value)
        return str(parsed) if parsed.int and str(parsed) == value.lower() else None
    except ValueError:
        return None


class FixedTeamMembership:
    def __init__(self, client: GraphGetClient):
        if not _client_is_hardened(client):
            raise ValueError("hardened membership client required")
        self._client = client

    def contains(self, actor_id: object) -> bool:
        actor = _subject(actor_id)
        if actor is None:
            return False
        try:
            group = self._client.get(_path("", {"$select": "id,groupTypes,resourceProvisioningOptions"}))
            if (type(group) is not dict or group.get("id") != TEAM_ID
                    or group.get("groupTypes") != ["Unified"]
                    or type(group.get("resourceProvisioningOptions")) is not list
                    or "Team" not in group["resourceProvisioningOptions"]
                    or "@odata.nextLink" in group):
                return False
            site = self._client.get(_path("/sites/root", {"$select": "id,webUrl"}))
            if (type(site) is not dict or site.get("id") != SYNTHETIC_SITE_ID
                    or site.get("webUrl") != SITE_URL or "@odata.nextLink" in site):
                return False
            # Direct members, not a typed cast: casts require the eventual index.
            # The verified Unified group is the fixed Microsoft 365 Team.
            members = self._client.get(_path("/members", {"$select": "id", "$top": "100"}))
            if (type(members) is not dict or "@odata.nextLink" in members
                    or "odata.nextLink" in members or type(members.get("value")) is not list
                    or len(members["value"]) > 100):
                return False
            ids = []
            for row in members["value"]:
                if type(row) is not dict or _subject(row.get("id")) is None:
                    return False
                if row.get("@odata.type", "#microsoft.graph.user") != "#microsoft.graph.user":
                    return False
                ids.append(_subject(row["id"]))
            return len(ids) == len(set(ids)) and actor in ids
        except Exception:
            return False
