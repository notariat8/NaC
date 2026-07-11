from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .business_case_inventory import BUSINESS_CASE_TYPE_ID_PATTERN, build_business_case_inventory
from .ontology_storage_contract import build_ontology_storage_contract


CONTRACT_RELATIVE_PATH = Path("workflows/contracts/notarial-process-ontology.contract.json")
SCHEMA_VERSION = "nac.notarial-process-ontology/v2"
CONTRACT_ID = "notarial.process_ontology"
NULLABLE_PROCESS_BPMN_FIELDS = {
    "NacBpmnModelId",
    "BpmnDriveItemId",
    "BpmnXmlSha256",
    "BpmnGitPath",
    "BpmnGitCommitSha",
    "NacBpmnVersion",
    "BpmnContentMode",
}


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
    evaluation = payload.get("evaluation")
    if isinstance(evaluation, dict) and isinstance(evaluation.get("errors", []), list):
        errors = list(evaluation.get("errors", []))
    else:
        errors = ["evaluation must be an object with an errors list"]
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append("unexpected schema_version")
    if payload.get("contract_id") != CONTRACT_ID:
        errors.append("unexpected contract_id")
    if payload.get("contract_path") != str(CONTRACT_RELATIVE_PATH):
        errors.append("unexpected contract_path")
    contract = payload.get("contract")
    if not isinstance(contract, dict):
        errors.append("contract must be an object")
        contract = {}
    if contract.get("schema_version") != SCHEMA_VERSION:
        errors.append("contract schema_version mismatch")
    if contract.get("contract_id") != CONTRACT_ID:
        errors.append("contract_id mismatch")
    _validate_s1_contract_shape(contract, errors)

    inventory_snapshot = payload.get("inventory_snapshot")
    if not isinstance(inventory_snapshot, dict):
        errors.append("inventory_snapshot must be an object")
        inventory_snapshot = {}
    if inventory_snapshot.get("status") != "PASSED":
        errors.append("business-case inventory must pass before process ontology contract evaluation")
    storage_snapshot = payload.get("storage_contract_snapshot")
    if not isinstance(storage_snapshot, dict):
        errors.append("storage_contract_snapshot must be an object")
        storage_snapshot = {}
    if storage_snapshot.get("status") != "PASSED":
        errors.append("ontology storage contract must pass before process ontology contract evaluation")
    inventory_summary = inventory_snapshot.get("summary")
    if not isinstance(inventory_summary, dict):
        errors.append("inventory snapshot summary must be an object")
        inventory_summary = {}
    if inventory_summary.get("business_case_count") != 22:
        errors.append("inventory snapshot must retain 22 catalog sizing entries")
    if inventory_summary.get("canonical_business_case_type_count") != 20:
        errors.append("inventory snapshot must contain 20 canonical business-case types")
    if inventory_summary.get("legacy_alias_count") != 2:
        errors.append("inventory snapshot must contain 2 legacy aliases")
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
    _validate_s1_contract_shape(contract, errors)
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
            "type_validity_requires_vorgangsartenregister": True,
            "type_validity_requires_process_register": False,
            "type_validity_requires_bpmn_model": False,
            "type_validity_requires_viewer": False,
            "process_key_equals_business_case_type_id_when_present": True,
        },
    }


def _case_contract_index(inventory: dict[str, Any], contract: dict[str, Any]) -> list[dict[str, Any]]:
    phases = contract.get("required_process_phases", [])
    index: list[dict[str, Any]] = []
    for item in inventory.get("business_cases", []):
        entry = {
            "slug": item["slug"],
            "catalog_entry_kind": item["catalog_entry_kind"],
            "domain": item["domain"],
            "implementation_depth": item["implementation_depth"],
            "complexity_band": item["sizing"]["complexity_band"],
            "process_phase_template_count": len(phases),
            "type_validity_dependencies": ["repo_versioned_catalog", "Vorgangsartenregister"],
            "process_register_required_for_type_validity": False,
            "bpmn_required_for_type_validity": False,
            "viewer_required_for_type_validity": False,
            "sharepoint_projection": {
                "business_case_type_registry": "Vorgangsartenregister",
                "matter_metadata": "Akten",
                "tasks_and_deadlines": "AufgabenFristen",
                "document_pointers": "DokumentRegister",
                "access_delegation": "Vertretungsfreigaben",
                "audit": "AuditJournalLite",
                "optional_process_registry": "Prozessregister",
                "optional_bpmn_library": "BPMN Models",
            },
            "stores_matter_values_in_repo": False,
            "stores_document_full_text": False,
            "requires_live_apply_now": False,
        }
        if item["catalog_entry_kind"] == "canonical":
            entry["business_case_type_id"] = item["business_case_type_id"]
        else:
            entry["legacy_alias"] = item["legacy_alias"]
        index.append(entry)
    return index


def _expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)

def _validate_s1_contract_shape(contract: Any, errors: list[str]) -> None:
    if not isinstance(contract, dict):
        errors.append("contract must be an object")
        return

    identity = contract.get("business_case_type_identity")
    if not isinstance(identity, dict):
        errors.append("business_case_type_identity must be an object")
    else:
        _expect(identity.get("canonical_field") == "BusinessCaseTypeId", "canonical identity field must be BusinessCaseTypeId", errors)
        _expect(identity.get("canonical_source") == "canonical_usecase_slug", "canonical identity source must be the usecase slug", errors)
        _expect(identity.get("canonical_id_equals_slug") is True, "canonical BusinessCaseTypeId must equal slug", errors)
        _expect(identity.get("syntax_pattern") == BUSINESS_CASE_TYPE_ID_PATTERN, "BusinessCaseTypeId syntax pattern mismatch", errors)
        _expect(identity.get("max_length") == 128, "BusinessCaseTypeId max length must be 128", errors)
        _expect(identity.get("exact_match_without_normalization") is True, "BusinessCaseTypeId matching must be exact", errors)
        _expect(identity.get("canonical_count") == 20, "identity contract must contain 20 canonical types", errors)
        _expect(identity.get("legacy_alias_count") == 2, "identity contract must contain 2 aliases", errors)
        _expect(identity.get("catalog_sizing_entry_count") == 22, "identity contract must retain 22 sizing entries", errors)
        _expect(identity.get("aliases_have_canonical_id") is False, "aliases must not have canonical IDs", errors)
        _expect(
            identity.get("aliases_require_one_direct_known_canonical_target") is True,
            "aliases must target one direct known canonical ID",
            errors,
        )
        _expect(
            identity.get("alias_collisions_chains_cycles_self_targets_and_duplicates_allowed") is False,
            "alias collisions, chains, cycles, self-targets and duplicates must be blocked",
            errors,
        )

    runtime = contract.get("runtime_type_validity")
    if not isinstance(runtime, dict):
        errors.append("runtime_type_validity must be an object")
    else:
        _expect(
            _string_set(runtime.get("required_dependencies")) == {"repo_versioned_catalog", "Vorgangsartenregister"},
            "type validity must depend exactly on repo catalog and Vorgangsartenregister",
            errors,
        )
        non_dependencies = _string_set(runtime.get("non_dependencies"))
        for optional in ("Prozessregister", "BPMN Models", "bpmn_model", "bpmn_viewer"):
            _expect(optional in non_dependencies, f"type validity must not depend on {optional}", errors)
        _expect(
            runtime.get("missing_optional_process_or_bpmn_projection_invalidates_type") is False,
            "missing process/BPMN projections must not invalidate a type",
            errors,
        )
        _expect(
            runtime.get("vorgangsartenregister_is_viewer_independent") is True,
            "Vorgangsartenregister must be viewer-independent",
            errors,
        )

    projection = contract.get("sharepoint_projection_rules")
    if not isinstance(projection, dict):
        errors.append("sharepoint_projection_rules must be an object")
        return
    required_lists = _string_set(projection.get("required_lists_or_libraries"))
    optional_lists = _string_set(projection.get("optional_future_lists_or_libraries"))
    _expect("Vorgangsartenregister" in required_lists, "Vorgangsartenregister must be a required projection", errors)
    _expect("Prozessregister" in optional_lists, "Prozessregister must remain optional", errors)
    _expect("BPMN Models" in optional_lists, "BPMN Models must remain optional", errors)
    _expect(not required_lists & optional_lists, "required and optional projections must be disjoint", errors)

    projections = projection.get("projection_contracts")
    if not isinstance(projections, dict):
        errors.append("projection_contracts must be an object")
        return
    type_registry = projections.get("Vorgangsartenregister")
    if not isinstance(type_registry, dict):
        errors.append("Vorgangsartenregister projection contract must be an object")
    else:
        _expect(type_registry.get("required_for_type_validity") is True, "Vorgangsartenregister must be required for type validity", errors)
        _expect(type_registry.get("viewer_independent") is True, "Vorgangsartenregister projection must be viewer-independent", errors)
        _expect(type_registry.get("unique_indexed_key") == "BusinessCaseTypeId", "Vorgangsartenregister key must be BusinessCaseTypeId", errors)
        _expect(
            _string_set(type_registry.get("required_fields"))
            == {"BusinessCaseTypeId", "LifecycleStatus", "Selectable", "CatalogVersion"},
            "Vorgangsartenregister fields mismatch",
            errors,
        )
        _expect(type_registry.get("bpmn_or_viewer_fields_allowed") is False, "Vorgangsartenregister must not require BPMN/viewer fields", errors)

    process_registry = projections.get("Prozessregister")
    if not isinstance(process_registry, dict):
        errors.append("Prozessregister projection contract must be an object")
    else:
        _expect(process_registry.get("required_for_type_validity") is False, "Prozessregister must not be required for type validity", errors)
        _expect(process_registry.get("optional") is True, "Prozessregister must be optional", errors)
        process_key = process_registry.get("process_key")
        if not isinstance(process_key, dict):
            errors.append("Prozessregister process_key must be an object")
        else:
            _expect(process_key.get("field") == "ProcessKey", "process key field must be ProcessKey", errors)
            for key in ("indexed", "unique", "equals_business_case_type_id_when_present"):
                _expect(process_key.get(key) is True, f"Prozessregister ProcessKey must set {key}", errors)
        _expect(
            NULLABLE_PROCESS_BPMN_FIELDS <= _string_set(process_registry.get("nullable_bpmn_link_fields")),
            "all Prozessregister BPMN link fields must be nullable",
            errors,
        )

    bpmn_models = projections.get("BPMN Models")
    if not isinstance(bpmn_models, dict):
        errors.append("BPMN Models projection contract must be an object")
    else:
        _expect(bpmn_models.get("required_for_type_validity") is False, "BPMN Models must not be required for type validity", errors)
        _expect(bpmn_models.get("optional") is True, "BPMN Models must be optional", errors)

    bpmn_alignment = contract.get("bpmn_alignment")
    if not isinstance(bpmn_alignment, dict):
        errors.append("bpmn_alignment must be an object")
    else:
        _expect(bpmn_alignment.get("runtime_engine") is False, "BPMN must not become a runtime engine", errors)
        _expect(bpmn_alignment.get("pointer_entity") == "BpmnModelPointer", "BPMN pointer entity mismatch", errors)
        _expect(bpmn_alignment.get("pointer_nullable") is True, "BPMN pointer must be nullable", errors)
        _expect(
            bpmn_alignment.get("required_for_type_validity") is False,
            "BPMN pointer must not be required for type validity",
            errors,
        )


def _string_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {item for item in value if isinstance(item, str)}
