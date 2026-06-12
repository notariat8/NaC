from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import assert_no_prohibited_payload, load_domain_graph
from .sources import load_source_manifest


FIXTURE_ROOT = Path("workflows") / "legal-graph" / "fixtures"
ALLOWED_EDGE_TYPES = {
    "approved_by",
    "affects_usecase",
    "amends",
    "cites",
    "needs_commentary_review",
    "supports_review_point",
    "valid_from",
    "valid_until",
}


def build_update_patch(repo_root: Path, domain: str) -> dict[str, Any]:
    graph = load_domain_graph(repo_root, domain)
    source_manifest = load_source_manifest(repo_root, domain)
    fixture_path = repo_root / source_manifest["update_fixture"]
    if not fixture_path.is_file():
        raise KeyError(f"Unknown legal graph update fixture: {domain}")

    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    assert_no_prohibited_payload(fixture)
    if fixture.get("domain") != domain:
        raise ValueError(f"Legal graph update fixture domain mismatch: {fixture_path}")

    existing_nodes = {node["id"] for node in graph.get("nodes", []) if isinstance(node, dict) and "id" in node}
    existing_edges = {
        (edge.get("from"), edge.get("to"), edge.get("type"))
        for edge in graph.get("edges", [])
        if isinstance(edge, dict)
    }

    changes: list[dict[str, Any]] = []
    candidate_nodes = fixture.get("candidate_nodes", [])
    if not isinstance(candidate_nodes, list):
        raise ValueError("Legal graph update fixture candidate_nodes must be a list")

    added_nodes: set[str] = set()
    for node in candidate_nodes:
        if not isinstance(node, dict):
            raise ValueError("Legal graph update fixture candidate node must be an object")
        node_id = node.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise ValueError("Legal graph update fixture candidate node id must be a string")
        if node.get("type") == "commentary_connector" and source_manifest.get("commentary_access_allowed") is False:
            raise ValueError("Legal graph primary source update fixture must not contain commentary connector changes")
        if node_id in existing_nodes:
            continue
        added_nodes.add(node_id)
        changes.append(
            {
                "action": "add_node",
                "status": _change_status(node),
                "node": node,
            }
        )

    candidate_edges = fixture.get("candidate_edges", [])
    if not isinstance(candidate_edges, list):
        raise ValueError("Legal graph update fixture candidate_edges must be a list")

    available_nodes = existing_nodes | added_nodes
    for edge in candidate_edges:
        if not isinstance(edge, dict):
            raise ValueError("Legal graph update fixture candidate edge must be an object")
        edge_from = edge.get("from")
        edge_to = edge.get("to")
        edge_type = edge.get("type")
        if not all(isinstance(item, str) and item for item in (edge_from, edge_to, edge_type)):
            raise ValueError("Legal graph update fixture candidate edge endpoints and type must be strings")
        if edge_type not in ALLOWED_EDGE_TYPES:
            raise ValueError(f"Legal graph update fixture edge type is not allowed: {edge_type}")
        if edge_from not in available_nodes or edge_to not in available_nodes:
            raise ValueError(f"Legal graph update fixture edge has unknown endpoint: {edge_from} -> {edge_to}")
        edge_key = (edge_from, edge_to, edge_type)
        if edge_key not in existing_edges:
            changes.append(
                {
                    "action": "add_edge",
                    "status": "proposed",
                    "edge": edge,
                }
            )

    return {
        "schema_version": "nac.legal-graph-patch/v0.1",
        "domain": domain,
        "source": fixture.get("source", {}),
        "source_manifest": {
            "source_id": source_manifest["source_id"],
            "retrieval_mode": source_manifest["retrieval_mode"],
            "commentary_access_allowed": source_manifest["commentary_access_allowed"],
            "canonical_url": source_manifest["canonical_url"],
        },
        "status": "proposed",
        "auto_merge_allowed": False,
        "human_review_required": True,
        "changes": changes,
    }


def _change_status(node: dict[str, Any]) -> str:
    if node.get("type") == "commentary_connector":
        return "blocked_contract"
    return "proposed"
