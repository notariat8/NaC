from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from .catalog import assert_no_prohibited_payload


SOURCE_ROOT = Path("workflows") / "legal-graph" / "sources"
SOURCE_INVENTORY_CONTRACT = (
    Path("workflows") / "contracts" / "legal-source-inventory-license-tdm.contract.json"
)
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


def legal_source_inventory_status(repo_root: Path) -> dict[str, Any]:
    payload = load_source_inventory_contract(repo_root)
    inventory = payload["source_inventory"]
    required_gates = payload["required_gates"]
    scope = payload["scope"]
    policy = payload["inventory_policy"]
    return {
        "schema_version": "nac.legal-source-inventory-status/v0.1",
        "contract_id": payload["contract_id"],
        "status": payload["status"],
        "sources": len(inventory),
        "planning_only": policy["planning_only"],
        "source_text_ingestion_enabled": scope["source_text_ingestion_enabled"],
        "benchmark_dataset_generated": scope["benchmark_dataset_generated"],
        "model_training_enabled": scope["model_training_enabled"],
        "owner_apply_required_before_ingestion": scope["owner_apply_required_before_ingestion"],
        "source_status": [
            {
                "source_id": source["source_id"],
                "source_class": source["source_class"],
                "jurisdiction_fit": source["jurisdiction_fit"],
                "license_status": source["license_status"],
                "tdm_status": source["tdm_status"],
                "terms_review_ref": source["terms_review_ref"],
                "attribution_plan": source["attribution_plan"],
                "human_review_owner": source["human_review_owner"],
                "review_depth": source["review_depth"],
                "allowed_pre_apply_actions": source["allowed_pre_apply_actions"],
                "blocked_pre_apply_actions": source["blocked_pre_apply_actions"],
            }
            for source in inventory
        ],
        "required_gates": [
            {
                "id": gate["id"],
                "must_complete_before": gate["must_complete_before"],
                "required_evidence": gate["required_evidence"],
            }
            for gate in required_gates
        ],
        "blocked_actions": payload["blocked_actions"],
    }


def load_source_inventory_contract(repo_root: Path) -> dict[str, Any]:
    path = repo_root / SOURCE_INVENTORY_CONTRACT
    if not path.is_file():
        raise KeyError(f"Unknown legal source inventory contract: {SOURCE_INVENTORY_CONTRACT}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Legal source inventory contract must be an object: {path}")
    _validate_source_inventory_contract(payload)
    return payload


def validate_source_manifest_payload(payload: dict[str, Any]) -> list[str]:
    try:
        _validate_source_manifest(payload)
    except ValueError as exc:
        return [str(exc)]
    return []


def _validate_source_inventory_contract(payload: dict[str, Any]) -> None:
    assert_no_prohibited_payload(payload)
    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        raise ValueError("source inventory contract schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != "workflow.legal_source_inventory_license_tdm":
        raise ValueError(
            "source inventory contract contract_id muss workflow.legal_source_inventory_license_tdm sein"
        )
    if payload.get("status") != "source_inventory_readiness_no_ingestion":
        raise ValueError("source inventory contract status muss source_inventory_readiness_no_ingestion sein")
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("source inventory contract scope muss ein Objekt sein")
    for key in (
        "source_text_ingestion_enabled",
        "benchmark_dataset_generated",
        "model_training_enabled",
        "model_evaluation_executed",
        "mandate_data_allowed",
        "publisher_full_text_allowed",
        "automated_bulk_crawl_enabled",
    ):
        if scope.get(key) is not False:
            raise ValueError(f"source inventory contract scope.{key} muss false sein")
    if scope.get("owner_apply_required_before_ingestion") is not True:
        raise ValueError("source inventory contract owner_apply_required_before_ingestion muss true sein")
    policy = payload.get("inventory_policy")
    if not isinstance(policy, dict) or policy.get("planning_only") is not True:
        raise ValueError("source inventory contract inventory_policy.planning_only muss true sein")
    inventory = payload.get("source_inventory")
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("source inventory contract source_inventory muss eine nicht leere Liste sein")
    for source in inventory:
        if not isinstance(source, dict):
            raise ValueError("source inventory contract source_inventory Eintraege muessen Objekte sein")
        for field in (
            "source_id",
            "source_class",
            "jurisdiction_fit",
            "license_status",
            "tdm_status",
            "terms_review_ref",
            "attribution_plan",
            "human_review_owner",
        ):
            if not isinstance(source.get(field), str) or not source[field]:
                raise ValueError(f"source inventory contract Quelle braucht {field}")
        review_depth = source.get("review_depth")
        if not isinstance(review_depth, dict):
            raise ValueError(f"source inventory contract {source['source_id']} braucht review_depth")
        for field in (
            "record_completeness",
            "license_terms_depth",
            "tdm_depth",
            "attribution_depth",
            "storage_boundary_depth",
            "next_required_review",
        ):
            if not isinstance(review_depth.get(field), str) or not review_depth[field]:
                raise ValueError(
                    f"source inventory contract {source['source_id']} braucht review_depth.{field}"
                )
        if not _strings(source.get("allowed_pre_apply_actions")):
            raise ValueError(f"source inventory contract {source['source_id']} braucht allowed_pre_apply_actions")
        if not _strings(source.get("blocked_pre_apply_actions")):
            raise ValueError(f"source inventory contract {source['source_id']} braucht blocked_pre_apply_actions")
    gates = payload.get("required_gates")
    if not isinstance(gates, list) or not gates:
        raise ValueError("source inventory contract required_gates muss eine nicht leere Liste sein")
    for gate in gates:
        if not isinstance(gate, dict):
            raise ValueError("source inventory contract required_gates Eintraege muessen Objekte sein")
        if not isinstance(gate.get("id"), str) or not gate["id"]:
            raise ValueError("source inventory contract required_gates brauchen id")
        if not isinstance(gate.get("must_complete_before"), str) or not gate["must_complete_before"]:
            raise ValueError(f"source inventory contract Gate {gate['id']} braucht must_complete_before")
        if not _strings(gate.get("required_evidence")):
            raise ValueError(f"source inventory contract Gate {gate['id']} braucht required_evidence")
    if not _strings(payload.get("blocked_actions")):
        raise ValueError("source inventory contract blocked_actions muss gesetzt sein")


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
