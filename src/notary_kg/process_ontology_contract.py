from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .business_case_inventory import build_business_case_inventory
from .ontology_storage_contract import build_ontology_storage_contract


CONTRACT_RELATIVE_PATH = Path("workflows/contracts/notarial-process-ontology.contract.json")
SCHEMA_VERSION = "nac.notarial-process-ontology/v1"
CONTRACT_ID = "notarial.process_ontology"


@dataclass(frozen=True, slots=True)
class ProcessOntologyContractValidation:
    status: str
    errors: tuple[str, ...]


def build_process_ontology_contract(repo_root: Path) -> dict[str, Any]:
    contract = json.loads((repo_root / CONTRACT_RELATIVE_PATH).read_text(encoding="utf-8"))
    inventory = build_business_case_inventory(repo_root)
    storage_contract = build_ontology_storage_contract(repo_root)
    evaluation = _evaluate(contract, inventory, storage_contract)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "PASSED" if not evaluation["errors"] else "FAILED",
        "contract_path": str(CONTRACT_RELATIVE_PATH),
        "contract": contract,
        "inventory_snapshot": {
            "schema_version": inventory["schema_version"],
            "status": inventory["status"],
            "summary": inventory["summary"],
            "storage_strategy": inventory["storage_strategy"],
            "privacy": inventory["privacy"],
        },
        "storage_contract_snapshot": {
            "schema_version": storage_contract["schema_version"],
            "status": storage_contract["status"],
            "contract_path": storage_contract["contract_path"],
            "derived_decision": storage_contract["evaluation"]["derived_decision"],
        },
        "case_contract_index": _case_contract_index(inventory, contract),
        "evaluation": evaluation,
    }


def validate_process_ontology_contract(payload: dict[str, Any]) -> ProcessOntologyContractValidation:
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
        errors.append("business-case inventory must pass before process ontology contract evaluation")
    if payload.get("storage_contract_snapshot", {}).get("status") != "PASSED":
        errors.append("ontology storage contract must pass before process ontology contract evaluation")
    return ProcessOntologyContractValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _evaluate(contract: dict[str, Any], inventory: dict[str, Any], storage_contract: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    summary = inventory.get("summary", {})
    scope = contract.get("scope", {})
    source_of_truth = contract.get("source_of_truth", {})
    graph_boundary = contract.get("graph_boundary", {})
    projection = contract.get("sharepoint_projection_rules", {})
    sizing = contract.get("sizing_policy", {})
    storage_decision = storage_contract.get("evaluation", {}).get("derived_decision", {})

    _expect(contract.get("schema_version") == SCHEMA_VERSION, "contract schema_version mismatch", errors)
    _expect(contract.get("contract_id") == CONTRACT_ID, "contract_id mismatch", errors)
    _expect(scope.get("offline_contract_only") is True, "contract must remain offline only", errors)
    _expect(scope.get("executes_graph_requests_now") is False, "contract must not execute Graph requests", errors)
    _expect(scope.get("writes_sharepoint_now") is False, "contract must not write SharePoint now", errors)
    _expect(scope.get("changes_sharepoint_schema_now") is False, "contract must not change SharePoint schema now", errors)
    _expect(scope.get("stores_matter_instance_values_in_repo") is False, "repo must not store matter instance values", errors)
    _expect(scope.get("stores_document_full_text") is False, "contract must not store document full text", errors)
    _expect(
        scope.get("creates_central_knowledge_graph_folder") is False,
        "central knowledge-graph folder must remain blocked",
        errors,
    )

    _expect(
        source_of_truth.get("business_case_catalog") == "usecase_local_knowledge_graphs",
        "business-case catalog source mismatch",
        errors,
    )
    _expect(
        source_of_truth.get("runtime_store") == "sharepoint_metadata_lists_and_document_pointers",
        "runtime store must remain SharePoint metadata and document pointers",
        errors,
    )
    _expect(
        source_of_truth.get("ontology_role") == "versioned_product_model_contract_and_projection_shape",
        "ontology role must remain product-model projection shape",
        errors,
    )

    _expect(graph_boundary.get("m365_data_plane") == "microsoft_graph_rest_v1", "M365 data plane must be Graph REST v1", errors)
    for key in ("sdk_allowed", "legacy_sharepoint_api_allowed", "graph_beta_allowed"):
        _expect(graph_boundary.get(key) is False, f"graph boundary must block {key}", errors)

    entity_classes = contract.get("canonical_entity_classes", [])
    phases = contract.get("required_process_phases", [])
    relationships = contract.get("relationship_templates", [])
    required_lists = set(projection.get("required_lists_or_libraries", []))
    inventory_lists = {item.get("list_or_library") for item in inventory.get("sharepoint_mvp_mapping", [])}
    missing_lists = sorted(inventory_lists - required_lists)
    if missing_lists:
        errors.append(f"process ontology contract missing required SharePoint projections: {', '.join(missing_lists)}")
    for required in ("Matter", "BusinessCaseType", "ProcessPhase", "Task", "DocumentPointer", "EvidencePointer", "DeputyGrant", "AuditEvent"):
        if required not in entity_classes:
            errors.append(f"canonical_entity_classes missing {required}")
    for required in ("intake", "drafting", "review_and_approval", "completion", "archive"):
        if required not in phases:
            errors.append(f"required_process_phases missing {required}")
    for relationship in relationships:
        if relationship.get("from") not in entity_classes:
            errors.append(f"{relationship.get('id', '<unknown>')}: from entity is not canonical")
        if relationship.get("to") not in entity_classes:
            errors.append(f"{relationship.get('id', '<unknown>')}: to entity is not canonical")
        if not relationship.get("sharepoint_projection"):
            errors.append(f"{relationship.get('id', '<unknown>')}: missing SharePoint projection")

    _expect(storage_decision.get("sharepoint_remains_mvp_store") is True, "storage contract must keep SharePoint as MVP store", errors)
    _expect(storage_decision.get("ontology_remains_projection_contract") is True, "storage contract must keep ontology as projection contract", errors)
    _expect(
        storage_decision.get("runtime_reasoning_on_request_path_allowed") is False,
        "runtime ontology reasoning must remain off the request path",
        errors,
    )

    business_case_count = int(summary.get("business_case_count", 0))
    canonical_covered = int(summary.get("canonical_covered_count", 0))
    canonical_required = int(sizing.get("minimum_canonical_business_cases", 0))
    _expect(sizing.get("all_business_cases_must_be_included") is True, "all business cases must be included in sizing", errors)
    _expect(business_case_count >= canonical_required, "business-case count below minimum canonical policy", errors)
    _expect(canonical_covered >= canonical_required, "canonical business-case coverage below minimum", errors)
    _expect(
        len(entity_classes) <= int(sizing.get("max_entity_classes_without_architecture_review", 0)),
        "entity class count exceeds architecture-review threshold",
        errors,
    )
    _expect(
        len(relationships) <= int(sizing.get("max_relationship_templates_without_architecture_review", 0)),
        "relationship template count exceeds architecture-review threshold",
        errors,
    )
    _expect(
        len(phases) <= int(sizing.get("max_required_process_phases_without_architecture_review", 0)),
        "process phase count exceeds architecture-review threshold",
        errors,
    )

    if "Prozessregister" in projection.get("optional_future_lists_or_libraries", []):
        warnings.append("Prozessregister is optional for MVP and needs owner-gated schema apply before live use")
    if "BPMN Models" in projection.get("optional_future_lists_or_libraries", []):
        warnings.append("BPMN Models library is optional for SPFx viewer and needs owner-gated schema apply before live use")

    return {
        "status": "PASSED" if not errors else "FAILED",
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "business_case_count": business_case_count,
            "canonical_covered_count": canonical_covered,
            "canonical_required": canonical_required,
            "entity_class_count": len(entity_classes),
            "relationship_template_count": len(relationships),
            "process_phase_count": len(phases),
            "required_sharepoint_projection_count": len(required_lists),
            "case_contract_index_count": len(inventory.get("business_cases", [])),
        },
        "derived_decision": {
            "sharepoint_remains_mvp_store": True,
            "ontology_is_product_model_contract": True,
            "all_business_cases_counted_for_sizing": True,
            "deep_modeling_can_remain_selective": True,
            "runtime_reasoning_on_request_path_allowed": False,
            "live_apply_required_now": False,
        },
    }


def _case_contract_index(inventory: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    phases = contract.get("required_process_phases", [])
    return [
        {
            "slug": item["slug"],
            "domain": item["domain"],
            "implementation_depth": item["implementation_depth"],
            "complexity_band": item["sizing"]["complexity_band"],
            "process_phase_template_count": len(phases),
            "sharepoint_projection": {
                "matter_metadata": "Akten",
                "tasks_and_deadlines": "AufgabenFristen",
                "document_pointers": "DokumentRegister",
                "access_delegation": "Vertretungsfreigaben",
                "audit": "AuditJournalLite",
            },
            "stores_matter_values_in_repo": False,
            "stores_document_full_text": False,
            "requires_live_apply_now": False,
        }
        for item in inventory.get("business_cases", [])
    ]


def _expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)
