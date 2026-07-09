from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .business_case_inventory import build_business_case_inventory


CONTRACT_RELATIVE_PATH = Path("workflows/contracts/notarial-ontology-sizing-storage.contract.json")
SCHEMA_VERSION = "nac.notarial-ontology-sizing-storage/v0.1"
CONTRACT_ID = "notarial.ontology_sizing_storage"


@dataclass(frozen=True, slots=True)
class OntologyStorageValidation:
    status: str
    errors: tuple[str, ...]


def build_ontology_storage_contract(repo_root: Path) -> dict[str, Any]:
    contract_path = repo_root / CONTRACT_RELATIVE_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    inventory = build_business_case_inventory(repo_root)
    evaluation = _evaluate(contract, inventory)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED" if not evaluation["errors"] else "FAILED",
        "contract_path": str(CONTRACT_RELATIVE_PATH),
        "contract": contract,
        "inventory_snapshot": {
            "schema_version": inventory["schema_version"],
            "mode": inventory["mode"],
            "status": inventory["status"],
            "summary": inventory["summary"],
            "generated_from": inventory["generated_from"],
            "storage_strategy": inventory["storage_strategy"],
            "performance_guardrails": inventory["performance_guardrails"],
            "privacy": inventory["privacy"],
        },
        "evaluation": evaluation,
    }


def validate_ontology_storage_contract(payload: dict[str, Any]) -> OntologyStorageValidation:
    errors = list(payload.get("evaluation", {}).get("errors", []))
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("contract_path") != str(CONTRACT_RELATIVE_PATH):
        errors.append("unexpected contract_path")
    contract = payload.get("contract", {})
    if contract.get("schema_version") != SCHEMA_VERSION:
        errors.append("contract schema_version mismatch")
    if contract.get("contract_id") != CONTRACT_ID:
        errors.append("contract_id mismatch")
    if payload.get("inventory_snapshot", {}).get("status") != "PASSED":
        errors.append("business-case inventory must pass before storage contract evaluation")
    return OntologyStorageValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _evaluate(contract: dict[str, Any], inventory: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    summary = inventory.get("summary", {})
    thresholds = contract.get("sizing_thresholds", {})
    scope = contract.get("scope", {})
    graph = contract.get("graph", {})
    storage_roles = contract.get("storage_roles", {})
    projection_rules = contract.get("projection_rules", {})

    _expect(contract.get("schema_version") == SCHEMA_VERSION, "contract schema_version mismatch", errors)
    _expect(contract.get("contract_id") == CONTRACT_ID, "contract_id mismatch", errors)
    _expect(scope.get("offline_contract_only") is True, "contract must be offline only", errors)
    _expect(scope.get("executes_graph_requests_now") is False, "contract must not execute Graph requests", errors)
    _expect(scope.get("changes_sharepoint_schema_now") is False, "contract must not change SharePoint schema", errors)
    _expect(scope.get("stores_tokens_or_secrets") is False, "contract must not store tokens or secrets", errors)
    _expect(scope.get("stores_matter_instance_values") is False, "contract must not store matter instance values", errors)
    _expect(scope.get("stores_document_full_text") is False, "contract must not store document full text", errors)
    _expect(
        scope.get("creates_central_knowledge_graph_folder") is False,
        "contract must not create a central knowledge-graph folder",
        errors,
    )
    _expect(graph.get("rest_only") is True, "Graph access must be REST-only", errors)
    _expect(graph.get("sdk_allowed") is False, "Graph SDK must remain blocked for this boundary", errors)
    _expect(graph.get("legacy_sharepoint_api_allowed") is False, "legacy SharePoint APIs must remain blocked", errors)
    _expect(graph.get("graph_beta_allowed") is False, "Graph beta must remain blocked", errors)

    inventory_generated_from = inventory.get("generated_from", {})
    _expect(
        inventory_generated_from.get("central_knowledge_graph_folder_allowed") is False,
        "inventory must not allow a central knowledge-graph folder",
        errors,
    )
    _expect(
        inventory_generated_from.get("usecase_local_knowledge_graphs_remain_authoritative") is True,
        "usecase-local knowledge graphs must remain authoritative",
        errors,
    )

    canonical_required = int(thresholds.get("canonical_business_cases_required", -1))
    canonical_covered = int(summary.get("canonical_covered_count", -2))
    _expect(canonical_covered >= canonical_required, "canonical business-case coverage below threshold", errors)

    business_case_count = int(summary.get("business_case_count", 0))
    max_supported = int(thresholds.get("max_supported_business_cases_without_store_migration", 0))
    _expect(business_case_count <= max_supported, "business-case count exceeds no-migration threshold", errors)

    max_complexity = int(summary.get("max_complexity_score", 0))
    architecture_review_threshold = int(thresholds.get("max_complexity_score_without_architecture_review", 0))
    _expect(
        max_complexity <= architecture_review_threshold,
        "max complexity score requires architecture review",
        errors,
    )

    deep_process_candidates = set(summary.get("deep_process_slices_recommended", []))
    if "online-gmbh-gruendung" not in deep_process_candidates:
        warnings.append("online-gmbh-gruendung is a high-complexity thin catalog and should be reviewed before deep process modeling")

    _validate_storage_roles(storage_roles, errors)
    _validate_projection_rules(projection_rules, errors)
    _validate_mapping(contract, inventory, errors)
    _validate_privacy(inventory, errors)

    return {
        "status": "PASSED" if not errors else "FAILED",
        "errors": errors,
        "warnings": warnings,
        "current_sizing": {
            "business_case_count": business_case_count,
            "canonical_covered_count": canonical_covered,
            "canonical_required": canonical_required,
            "max_complexity_score": max_complexity,
            "max_supported_business_cases_without_store_migration": max_supported,
            "max_complexity_score_without_architecture_review": architecture_review_threshold,
        },
        "derived_decision": {
            "sharepoint_remains_mvp_store": True,
            "ontology_remains_projection_contract": True,
            "runtime_reasoning_on_request_path_allowed": False,
            "deep_process_modeling_selective": True,
        },
    }


def _validate_storage_roles(storage_roles: dict[str, Any], errors: list[str]) -> None:
    sharepoint = storage_roles.get("sharepoint", {})
    ontology = storage_roles.get("ontology", {})
    bpmn = storage_roles.get("bpmn", {})
    _expect(sharepoint.get("role") == "operative_mvp_data_store", "SharePoint role mismatch", errors)
    _expect(ontology.get("role") == "versioned_repo_catalog_and_projection_contract", "ontology role mismatch", errors)
    _expect(bpmn.get("role") == "process_model_not_runtime_engine", "BPMN role mismatch", errors)
    blocked_ontology_values = set(ontology.get("does_not_store", []))
    for required in (
        "matter_instance_values",
        "document_full_text",
        "raw_sharepoint_items",
        "raw_graph_responses",
        "tokens_or_secrets",
        "personal_data_values",
    ):
        if required not in blocked_ontology_values:
            errors.append(f"ontology does_not_store missing {required}")


def _validate_projection_rules(projection_rules: dict[str, Any], errors: list[str]) -> None:
    _expect(
        projection_rules.get("source_of_truth") == "usecase_local_knowledge_graphs",
        "projection source must be usecase-local knowledge graphs",
        errors,
    )
    _expect(
        projection_rules.get("central_knowledge_graph_folder_allowed") is False,
        "central knowledge-graph folder must be blocked",
        errors,
    )
    _expect(projection_rules.get("runtime_reasoning_required") is False, "runtime reasoning must not be required", errors)
    _expect(
        projection_rules.get("runtime_database_role_allowed") is False,
        "ontology must not be a runtime database",
        errors,
    )
    blocked_targets = set(projection_rules.get("blocked_projection_targets", []))
    for required in (
        "sharepoint_file_content_index",
        "matter_payload_index",
        "agent_memory_bulk_copy",
        "runtime_owl_reasoner_on_user_request_path",
    ):
        if required not in blocked_targets:
            errors.append(f"blocked_projection_targets missing {required}")


def _validate_mapping(contract: dict[str, Any], inventory: dict[str, Any], errors: list[str]) -> None:
    inventory_mapping = {
        item.get("list_or_library"): set(item.get("ontology_entities", []))
        for item in inventory.get("sharepoint_mvp_mapping", [])
    }
    contract_mapping = {
        item.get("list_or_library"): set(item.get("ontology_entities", []))
        for item in contract.get("sharepoint_projection_mapping", [])
    }
    for list_name, entities in sorted(inventory_mapping.items()):
        if list_name not in contract_mapping:
            errors.append(f"SharePoint projection mapping missing {list_name}")
            continue
        missing_entities = entities - contract_mapping[list_name]
        if missing_entities:
            errors.append(f"{list_name} projection mapping missing entities: {', '.join(sorted(missing_entities))}")
    for item in contract.get("sharepoint_projection_mapping", []):
        _expect(
            item.get("ontology_projection", "").endswith("_only"),
            f"{item.get('list_or_library', '<unknown>')} ontology projection must be shape-only",
            errors,
        )


def _validate_privacy(inventory: dict[str, Any], errors: list[str]) -> None:
    privacy = inventory.get("privacy", {})
    for key in ("contains_real_matter_data", "contains_document_full_text", "contains_tokens_or_secrets"):
        _expect(privacy.get(key) is False, f"inventory privacy boundary failed: {key}", errors)
    _expect(privacy.get("metadata_only") is True, "inventory must stay metadata-only", errors)


def _expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)
