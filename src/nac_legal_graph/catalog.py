from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DOMAIN_ROOT = Path("workflows") / "legal-graph" / "domains"
EMPTY_VALUES = (None, "", [], {})
PROHIBITED_TEXT_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
}
MANDATE_VALUE_KEYS = {"value"}
COMMENTARY_TEXT_KEYS = {
    "commentary_full_text",
    "commentary_text",
    "full_text",
    "kommentar_volltext",
    "provider_full_text",
}
CREDENTIAL_KEYS = {
    "access_token",
    "api_key",
    "client_secret",
    "cookie",
    "credential",
    "credentials",
    "password",
    "private_key",
    "refresh_token",
    "secret",
}


def load_domain_graph(repo_root: Path, domain: str) -> dict[str, Any]:
    path = repo_root / DOMAIN_ROOT / f"{_safe_domain(domain)}.graph.json"
    if not path.is_file():
        raise KeyError(f"Unknown legal graph domain: {domain}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert_no_prohibited_payload(payload)
    return payload


def legal_graph_status(repo_root: Path) -> dict[str, Any]:
    graphs = _load_all_graphs(repo_root)
    return {
        "schema_version": "nac.legal-graph-status/v0.1",
        "domains": len(graphs),
        "domain_status": [_domain_status(graph) for graph in graphs],
    }


def build_review_payload(repo_root: Path, domain: str) -> dict[str, Any]:
    graph = load_domain_graph(repo_root, domain)
    review_items = [
        {
            "id": node["id"],
            "type": node["type"],
            "label": node.get("label", node["id"]),
            "status": node.get("status", node.get("usage_status", "metadata_only")),
        }
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("type") in {"source_document", "review_point", "commentary_connector"}
    ]
    return {
        "schema_version": "nac.legal-graph-review/v0.1",
        "domain": graph["domain"]["id"],
        "graph_id": graph["graph_id"],
        "guardrails": graph["guardrails"],
        "review_items": review_items,
    }


def _load_all_graphs(repo_root: Path) -> list[dict[str, Any]]:
    root = repo_root / DOMAIN_ROOT
    if not root.is_dir():
        return []
    return [load_domain_graph(repo_root, path.name.removesuffix(".graph.json")) for path in sorted(root.glob("*.graph.json"))]


def _domain_status(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    return {
        "id": graph["domain"]["id"],
        "label_de": graph["domain"].get("label_de", graph["domain"]["id"]),
        "status": graph["domain"].get("status", "unknown"),
        "nodes": len(nodes),
        "edges": len([edge for edge in graph.get("edges", []) if isinstance(edge, dict)]),
        "review_required": sum(1 for node in nodes if str(node.get("status", "")).endswith("review_required")),
        "commentary_connectors": sum(1 for node in nodes if node.get("type") == "commentary_connector"),
    }


def assert_no_prohibited_payload(value: Any) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key in MANDATE_VALUE_KEYS and item not in EMPTY_VALUES:
                raise ValueError("Legal graph must not contain mandate values")
            if normalized_key in COMMENTARY_TEXT_KEYS and item not in EMPTY_VALUES:
                raise ValueError("Legal graph must not contain commentary full text")
            if normalized_key in CREDENTIAL_KEYS and item not in EMPTY_VALUES:
                raise ValueError("Legal graph must not contain credentials or secrets")
            assert_no_prohibited_payload(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_prohibited_payload(item)
    elif isinstance(value, str):
        lowered = value.lower()
        for marker in PROHIBITED_TEXT_MARKERS:
            if marker.lower() in lowered:
                raise ValueError("Legal graph must not contain credentials or secrets")


def _assert_no_values(value: Any) -> None:
    if isinstance(value, dict):
        if "value" in value and value["value"] not in EMPTY_VALUES:
            raise ValueError("Legal graph must not contain mandate values")
        for item in value.values():
            _assert_no_values(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_values(item)


def _safe_domain(domain: str) -> str:
    if not domain.replace("-", "").isalnum():
        raise ValueError(f"Unsafe legal graph domain: {domain}")
    return domain
