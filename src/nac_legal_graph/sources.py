from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from .catalog import assert_no_prohibited_payload


SOURCE_ROOT = Path("workflows") / "legal-graph" / "sources"
REQUIRED_ALLOWED_OUTPUTS = {
    "source_url",
    "retrieved_at",
    "citation",
    "candidate_node_metadata",
    "candidate_edge_metadata",
}
REQUIRED_BLOCKED_ACTIONS = {
    "query_commentary_connector",
    "store_source_full_text",
    "store_commentary_full_text",
    "store_credentials",
    "send_mandate_data",
    "auto_merge_graph_patch",
}


def load_source_manifest(repo_root: Path, domain: str) -> dict[str, Any]:
    path = repo_root / SOURCE_ROOT / f"{_safe_domain(domain)}-primary-source.json"
    if not path.is_file():
        raise KeyError(f"Unknown legal graph source manifest: {domain}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Legal graph source manifest must be an object: {path}")
    _validate_source_manifest(payload)
    return payload


def legal_graph_source_status(repo_root: Path) -> dict[str, Any]:
    manifests = _load_all_source_manifests(repo_root)
    return {
        "schema_version": "nac.legal-graph-source-status/v0.1",
        "sources": len(manifests),
        "source_status": [
            {
                "source_id": manifest["source_id"],
                "domain": manifest["domain"],
                "source_type": manifest["source_type"],
                "retrieval_mode": manifest["retrieval_mode"],
                "commentary_access_allowed": manifest["commentary_access_allowed"],
                "review_required": manifest["review_required"],
            }
            for manifest in manifests
        ],
    }


def validate_source_manifest_payload(payload: dict[str, Any]) -> list[str]:
    try:
        _validate_source_manifest(payload)
    except ValueError as exc:
        return [str(exc)]
    return []


def _load_all_source_manifests(repo_root: Path) -> list[dict[str, Any]]:
    root = repo_root / SOURCE_ROOT
    if not root.is_dir():
        return []
    manifests: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            _validate_source_manifest(payload)
            manifests.append(payload)
    return manifests


def _validate_source_manifest(payload: dict[str, Any]) -> None:
    assert_no_prohibited_payload(payload)
    if payload.get("schema_version") != "nac.legal-graph-source/v0.1":
        raise ValueError("source manifest schema_version muss nac.legal-graph-source/v0.1 sein")
    if not isinstance(payload.get("source_id"), str) or not payload["source_id"]:
        raise ValueError("source manifest source_id muss gesetzt sein")
    if not isinstance(payload.get("domain"), str) or not payload["domain"]:
        raise ValueError("source manifest domain muss gesetzt sein")
    if payload.get("source_type") != "primary_law":
        raise ValueError("source manifest source_type muss primary_law sein")
    if payload.get("retrieval_mode") != "metadata_only_fixture":
        raise ValueError("source manifest retrieval_mode muss metadata_only_fixture sein")
    if payload.get("commentary_access_allowed") is not False:
        raise ValueError("source manifest commentary_access_allowed muss false sein")
    if payload.get("credentials_required") is not False:
        raise ValueError("source manifest credentials_required muss false sein")
    if payload.get("provider_query_allowed") is not False:
        raise ValueError("source manifest provider_query_allowed muss false sein")
    if payload.get("review_required") is not True:
        raise ValueError("source manifest review_required muss true sein")

    canonical_url = payload.get("canonical_url")
    if not isinstance(canonical_url, str):
        raise ValueError("source manifest canonical_url muss ein String sein")
    parsed_url = urlparse(canonical_url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise ValueError("source manifest canonical_url muss eine HTTP(S)-URL sein")

    update_fixture = payload.get("update_fixture")
    if not isinstance(update_fixture, str) or not update_fixture.endswith(".json"):
        raise ValueError("source manifest update_fixture muss eine JSON-Datei referenzieren")
    fixture_ref = PurePosixPath(update_fixture)
    if fixture_ref.is_absolute() or ".." in fixture_ref.parts:
        raise ValueError("source manifest update_fixture muss unter workflows/legal-graph/fixtures liegen")
    if fixture_ref.parts[:3] != ("workflows", "legal-graph", "fixtures"):
        raise ValueError("source manifest update_fixture muss unter workflows/legal-graph/fixtures liegen")

    allowed_outputs = set(_strings(payload.get("allowed_outputs")))
    for output in sorted(REQUIRED_ALLOWED_OUTPUTS - allowed_outputs):
        raise ValueError(f"source manifest allowed_outputs fehlt {output}")
    blocked_actions = set(_strings(payload.get("blocked_actions")))
    for action in sorted(REQUIRED_BLOCKED_ACTIONS - blocked_actions):
        raise ValueError(f"source manifest blocked_actions fehlt {action}")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _safe_domain(domain: str) -> str:
    if not domain.replace("-", "").isalnum():
        raise ValueError(f"Unsafe legal graph source domain: {domain}")
    return domain
