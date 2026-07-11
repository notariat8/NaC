from __future__ import annotations

import re

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .catalog import CaseSummary, all_case_summaries, load_catalogs


TOP10_SLUGS = {
    "immobilienkaufvertrag",
    "grundschuld-hypothekenbestellung",
    "online-gmbh-gruendung",
    "handelsregisteranmeldung",
    "unterschriftsbeglaubigung",
    "testament-erbvertrag",
    "erbscheinsantrag-nachlass",
    "vorsorgevollmacht-patientenverfuegung",
    "schenkungsvertrag-uebertragungsvertrag",
    "ehevertrag-scheidungsfolgenvereinbarung",
}

NEXT10_SLUGS = {
    "loeschungsbewilligung-grundbuchloeschung",
    "teilungserklaerung-weg",
    "bautraegervertrag",
    "gesellschafterbeschluss-gmbh-ug",
    "geschaeftsanteilsuebertragung-gmbh",
    "vereinsregisteranmeldung",
    "erbausschlagung",
    "pflichtteilsverzicht-erbverzicht",
    "adoption-familienrechtliche-erklaerungen",
    "vollmacht-immobilien-gesellschaftsgeschaefte",
}

CANONICAL_SLUGS = TOP10_SLUGS | NEXT10_SLUGS
LEGACY_ALIAS_SLUGS = {"grundstueckskaufvertrag", "testament"}
BUSINESS_CASE_TYPE_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
BUSINESS_CASE_TYPE_ID_MAX_LENGTH = 128
BUSINESS_CASE_TYPE_ID_RE = re.compile(BUSINESS_CASE_TYPE_ID_PATTERN)


DOMAIN_BY_SLUG = {
    "immobilienkaufvertrag": "real_estate",
    "grundstueckskaufvertrag": "real_estate",
    "grundschuld-hypothekenbestellung": "real_estate_financing",
    "loeschungsbewilligung-grundbuchloeschung": "real_estate_register",
    "teilungserklaerung-weg": "real_estate_complex",
    "bautraegervertrag": "real_estate_complex",
    "schenkungsvertrag-uebertragungsvertrag": "real_estate_transfer",
    "online-gmbh-gruendung": "corporate_register",
    "handelsregisteranmeldung": "corporate_register",
    "gesellschafterbeschluss-gmbh-ug": "corporate_register",
    "geschaeftsanteilsuebertragung-gmbh": "corporate_transaction",
    "vereinsregisteranmeldung": "association_register",
    "testament-erbvertrag": "inheritance",
    "testament": "inheritance",
    "erbscheinsantrag-nachlass": "inheritance",
    "erbausschlagung": "inheritance",
    "pflichtteilsverzicht-erbverzicht": "inheritance",
    "ehevertrag-scheidungsfolgenvereinbarung": "family",
    "adoption-familienrechtliche-erklaerungen": "family",
    "vorsorgevollmacht-patientenverfuegung": "care_and_advance_directives",
    "vollmacht-immobilien-gesellschaftsgeschaefte": "power_of_attorney",
    "unterschriftsbeglaubigung": "certification",
}

BACKLOG_CANDIDATES = [
    "genehmigungserklaerungen",
    "rangruecktritt-rangaenderung-grundbuch",
    "dienstbarkeiten",
    "baulasten-bezogene-erklaerungen",
    "niessbrauchsbestellungen",
    "wohnrechte",
    "auseinandersetzungsvertraege-erben",
    "scheidungsimmobilien-uebertragungen",
]

SHAREPOINT_MVP_MAPPING = [
    {
        "list_or_library": "Akten",
        "ontology_entities": ["Matter", "BusinessCaseType", "MatterStatus"],
        "storage_role": "metadata_runtime",
    },
    {
        "list_or_library": "Beteiligte",
        "ontology_entities": ["Participant", "RoleBinding"],
        "storage_role": "metadata_runtime_without_raw_identity_data",
    },
    {
        "list_or_library": "AufgabenFristen",
        "ontology_entities": ["ProcessStep", "Task", "Deadline", "Gate"],
        "storage_role": "workflow_state_runtime",
    },
    {
        "list_or_library": "DokumentRegister",
        "ontology_entities": ["DocumentPointer", "DocumentType", "DocumentVersion"],
        "storage_role": "document_pointer_runtime",
    },
    {
        "list_or_library": "Vertretungsfreigaben",
        "ontology_entities": ["DeputyGrant", "AccessPurpose", "ValidityWindow"],
        "storage_role": "access_delegation_runtime",
    },
    {
        "list_or_library": "AuditJournalLite",
        "ontology_entities": ["AuditEvent", "EvidencePointer"],
        "storage_role": "starter_audit_runtime_without_worm_claim",
    },
]

PERFORMANCE_GUARDRAILS = {
    "mvp_ontology_mode": "thin_catalog_and_projection",
    "canonical_truth": "repo_versioned_catalogs_and_usecase_local_knowledge_graphs",
    "runtime_store": "sharepoint_metadata_lists_and_document_pointers",
    "not_allowed": [
        "storing_matter_instance_values_in_the_ontology",
        "storing_document_full_text_in_the_ontology",
        "runtime_owl_reasoning_as_a_request_path_requirement",
        "bulk_copying_sharepoint_or_office_content_into_agent_memory",
    ],
    "later_projection_candidates": ["rdf_store", "shacl_validation", "vector_search_for_public_metadata"],
}


@dataclass(frozen=True, slots=True)
class InventoryValidation:
    status: str
    errors: tuple[str, ...]


def build_business_case_inventory(repo_root: Path) -> dict[str, Any]:
    catalogs = load_catalogs(repo_root)
    cases = sorted(all_case_summaries(catalogs), key=lambda item: item.slug)
    entries = [_entry_from_case(case) for case in cases]
    missing_canonical = sorted(CANONICAL_SLUGS - {case.slug for case in cases})
    identity_errors = validate_business_case_entries(entries)
    domain_counts: dict[str, int] = {}
    for entry in entries:
        domain = str(entry["domain"])
        domain_counts[domain] = domain_counts.get(domain, 0) + 1

    payload = {
        "schema_version": "nac.notarial-business-case-inventory/v0.2",
        "status": "PASSED" if not missing_canonical and not identity_errors else "BLOCKED",
        "mode": "thin_catalog_for_sizing",
        "generated_from": {
            "catalog_glob": "usecases/*/knowledge-graph.graph.json",
            "central_knowledge_graph_folder_allowed": False,
            "usecase_local_knowledge_graphs_remain_authoritative": True,
        },
        "summary": {
            "business_case_count": len(entries),
            "canonical_target_count": len(CANONICAL_SLUGS),
            "canonical_covered_count": len(CANONICAL_SLUGS) - len(missing_canonical),
            "canonical_business_case_type_count": sum(1 for entry in entries if entry["catalog_entry_kind"] == "canonical"),
            "legacy_alias_count": sum(1 for entry in entries if entry["inventory_scope"] == "legacy_alias"),
            "backlog_candidate_count": len(BACKLOG_CANDIDATES),
            "domain_counts": domain_counts,
            "max_complexity_score": max((entry["sizing"]["complexity_score"] for entry in entries), default=0),
            "deep_process_slices_recommended": [
                "immobilienkaufvertrag",
                "handelsregisteranmeldung",
                "vorsorgevollmacht-patientenverfuegung",
            ],
        },
        "storage_strategy": {
            "sharepoint_role": "operative_mvp_data_store",
            "ontology_role": "versioned_repo_catalog_and_projection_contract",
            "bpmn_role": "process_model_not_runtime_engine",
            "document_content_role": "outside_ontology_and_outside_git",
            "mcp_graph_role": "runtime_access_layer_via_microsoft_graph_rest",
        },
        "type_validity_dependencies": {
            "repo_versioned_catalog_required": True,
            "vorgangsartenregister_required": True,
            "prozessregister_required": False,
            "bpmn_model_required": False,
            "viewer_required": False,
            "exact_match_required": True,
        },
        "ontology_entity_model": [
            "BusinessCaseType",
            "Matter",
            "Participant",
            "Role",
            "RoleBinding",
            "Task",
            "Deadline",
            "DocumentPointer",
            "Status",
            "Gate",
            "EvidencePointer",
            "DeputyGrant",
            "AuditEvent",
        ],
        "sharepoint_mvp_mapping": SHAREPOINT_MVP_MAPPING,
        "performance_guardrails": PERFORMANCE_GUARDRAILS,
        "business_cases": entries,
        "backlog_candidates": BACKLOG_CANDIDATES,
        "errors": [
            *[f"canonical usecase missing from inventory source: {slug}" for slug in missing_canonical],
            *identity_errors,
        ],
        "privacy": {
            "contains_real_matter_data": False,
            "contains_document_full_text": False,
            "contains_tokens_or_secrets": False,
            "contains_personal_data_values": False,
            "metadata_only": True,
        },
    }
    return payload


def validate_business_case_inventory(payload: dict[str, Any]) -> InventoryValidation:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.notarial-business-case-inventory/v0.2":
        errors.append("unexpected schema_version")
    if payload.get("mode") != "thin_catalog_for_sizing":
        errors.append("inventory must remain a thin catalog for sizing")
    summary = payload.get("summary", {})
    if not isinstance(summary, dict):
        errors.append("summary must be an object")
        summary = {}
    if summary.get("business_case_count") != 22:
        errors.append("inventory must retain exactly 22 catalog sizing entries")
    if summary.get("canonical_business_case_type_count") != 20:
        errors.append("inventory must distinguish exactly 20 canonical business-case types")
    if summary.get("legacy_alias_count") != 2:
        errors.append("inventory must distinguish exactly 2 legacy aliases")
    entries = payload.get("business_cases", [])
    errors.extend(validate_business_case_entries(entries))
    expected_dependencies = {
        "repo_versioned_catalog_required": True,
        "vorgangsartenregister_required": True,
        "prozessregister_required": False,
        "bpmn_model_required": False,
        "viewer_required": False,
        "exact_match_required": True,
    }
    if payload.get("type_validity_dependencies") != expected_dependencies:
        errors.append("BusinessCaseTypeId validity dependency contract mismatch")

    if summary.get("canonical_covered_count") != summary.get("canonical_target_count"):
        errors.append("not all canonical Top-10 and Next-10 usecases are covered")
    storage_strategy = payload.get("storage_strategy")
    if not isinstance(storage_strategy, dict):
        errors.append("storage_strategy must be an object")
        storage_strategy = {}
    if storage_strategy.get("sharepoint_role") != "operative_mvp_data_store":
        errors.append("SharePoint must remain the operative MVP data store")
    if storage_strategy.get("ontology_role") != "versioned_repo_catalog_and_projection_contract":
        errors.append("ontology must remain a versioned repo catalog/projection contract")
    generated_from = payload.get("generated_from")
    if not isinstance(generated_from, dict):
        errors.append("generated_from must be an object")
        generated_from = {}
    if not generated_from.get("usecase_local_knowledge_graphs_remain_authoritative"):
        errors.append("usecase-local knowledge graphs must remain authoritative")
    privacy = payload.get("privacy")
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object")
        privacy = {}
    for key in ("contains_real_matter_data", "contains_document_full_text", "contains_tokens_or_secrets"):
        if privacy.get(key) is not False:
            errors.append(f"privacy boundary failed: {key}")
    for entry in entries if isinstance(entries, list) else []:
        if not isinstance(entry, dict):
            continue
        if "complexity_score" not in entry.get("sizing", {}):
            errors.append(f"{entry.get('slug', '<missing-slug>')}: missing complexity score")
        if entry.get("implementation_depth") not in {"thin_catalog", "candidate_deep_process"}:
            errors.append(f"{entry.get('slug', '<missing-slug>')}: invalid implementation depth")
    return InventoryValidation(status="PASSED" if not errors else "FAILED", errors=tuple(errors))


def _entry_from_case(case: CaseSummary) -> dict[str, Any]:
    complexity_score = _complexity_score(case)
    entry: dict[str, Any] = {
        "slug": case.slug,
        "title": case.title,
        "catalog_id": case.catalog_id,
        "usecase_path": case.usecase_path,
        "inventory_scope": _inventory_scope(case.slug),
        "catalog_entry_kind": _catalog_entry_kind(case.slug),
        "source_status": case.status,
        "domain": DOMAIN_BY_SLUG.get(case.slug, "unclassified_notarial_case"),
        "implementation_depth": "candidate_deep_process" if case.slug in {
            "immobilienkaufvertrag",
            "handelsregisteranmeldung",
            "vorsorgevollmacht-patientenverfuegung",
        } else "thin_catalog",
        "sizing": {
            "required_information_nodes": case.required_information,
            "open_required_information_nodes": case.open_required_information,
            "document_types": case.documents,
            "decision_points": case.decisions,
            "gates": case.gates,
            "evidence_points": case.evidence,
            "plugin_dependencies": len(case.plugin_dependencies),
            "workflow_dependencies": len(case.workflow_dependencies),
            "complexity_score": complexity_score,
            "complexity_band": _complexity_band(complexity_score),
        },
        "runtime_boundaries": {
            "sharepoint_metadata_required": True,
            "bpmn_process_model_required": False,
            "ontology_runtime_reasoning_required": False,
            "document_full_text_in_ontology": False,
            "matter_values_in_repo": False,
        },
        "dependency_hints": {
            "plugins": list(case.plugin_dependencies),
            "workflows": list(case.workflow_dependencies),
        },
    }
    if case.business_case_type_id is not None:
        entry["business_case_type_id"] = case.business_case_type_id
    if case.legacy_alias_target_business_case_type_id is not None:
        entry["legacy_alias"] = {
            "target": {
                "business_case_type_id": case.legacy_alias_target_business_case_type_id,
            }
        }
    if case.identity_metadata_errors:
        entry["identity_metadata_errors"] = list(case.identity_metadata_errors)
    return entry


def _catalog_entry_kind(slug: str) -> str:
    if slug in CANONICAL_SLUGS:
        return "canonical"
    if slug in LEGACY_ALIAS_SLUGS:
        return "legacy_alias"
    return "additional"


def _inventory_scope(slug: str) -> str:
    if slug in CANONICAL_SLUGS:
        return "canonical_top10_or_next10"
    if slug in LEGACY_ALIAS_SLUGS:
        return "legacy_alias"
    return "additional_existing_usecase"


def _complexity_score(case: CaseSummary) -> int:
    return (
        case.required_information
        + case.documents * 2
        + case.decisions * 2
        + case.gates * 3
        + case.evidence * 2
        + len(case.plugin_dependencies) * 2
        + len(case.workflow_dependencies)
    )


def _complexity_band(score: int) -> str:
    if score >= 48:
        return "high"
    if score >= 32:
        return "medium"
    return "low"


def validate_business_case_entries(value: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, list):
        return ["business_cases must be a list"]

    slug_counts: dict[str, int] = {}
    canonical_ids: dict[str, str] = {}
    alias_targets: dict[str, str] = {}
    canonical_slugs: set[str] = set()
    alias_slugs: set[str] = set()

    for index, entry in enumerate(value):
        if not isinstance(entry, dict):
            errors.append(f"business_cases[{index}] must be an object")
            continue
        slug = entry.get("slug")
        label = slug if isinstance(slug, str) and slug else f"business_cases[{index}]"
        if not _valid_business_case_type_id(slug):
            errors.append(f"{label}: slug must use exact lowercase kebab syntax and be at most 128 characters")
            continue
        slug_counts[slug] = slug_counts.get(slug, 0) + 1
        kind = entry.get("catalog_entry_kind")
        metadata_errors = entry.get("identity_metadata_errors", [])
        if metadata_errors:
            errors.append(f"{slug}: malformed source identity metadata")

        if kind == "canonical":
            canonical_slugs.add(slug)
            business_case_type_id = entry.get("business_case_type_id")
            if not _valid_business_case_type_id(business_case_type_id):
                errors.append(f"{slug}: canonical business_case_type_id has invalid syntax")
            elif business_case_type_id != slug:
                errors.append(f"{slug}: canonical business_case_type_id must exactly equal slug")
            elif business_case_type_id in canonical_ids:
                errors.append(
                    f"{slug}: duplicate canonical business_case_type_id also used by "
                    f"{canonical_ids[business_case_type_id]}"
                )
            else:
                canonical_ids[business_case_type_id] = slug
            if "legacy_alias" in entry:
                errors.append(f"{slug}: canonical entry must not declare legacy_alias")
            if entry.get("source_status") == "legacy_alias":
                errors.append(f"{slug}: canonical entry must not have legacy_alias status")
        elif kind == "legacy_alias":
            alias_slugs.add(slug)
            if "business_case_type_id" in entry:
                errors.append(f"{slug}: alias must not have a canonical business_case_type_id")
            if entry.get("source_status") != "legacy_alias":
                errors.append(f"{slug}: alias must have legacy_alias status")
            alias = entry.get("legacy_alias")
            if not isinstance(alias, dict) or set(alias) != {"target"}:
                errors.append(f"{slug}: alias must contain exactly one structured target")
                continue
            target = alias.get("target")
            if not isinstance(target, dict) or set(target) != {"business_case_type_id"}:
                errors.append(f"{slug}: alias target must contain exactly business_case_type_id")
                continue
            target_id = target.get("business_case_type_id")
            if not _valid_business_case_type_id(target_id):
                errors.append(f"{slug}: alias target has invalid business_case_type_id syntax")
                continue
            alias_targets[slug] = target_id
        else:
            errors.append(f"{slug}: catalog_entry_kind must be canonical or legacy_alias")

    for slug, count in sorted(slug_counts.items()):
        if count != 1:
            errors.append(f"{slug}: duplicate catalog slug")
    missing_canonical = sorted(CANONICAL_SLUGS - canonical_slugs)
    unexpected_canonical = sorted(canonical_slugs - CANONICAL_SLUGS)
    missing_aliases = sorted(LEGACY_ALIAS_SLUGS - alias_slugs)
    unexpected_aliases = sorted(alias_slugs - LEGACY_ALIAS_SLUGS)
    if missing_canonical:
        errors.append("missing canonical business-case types: " + ", ".join(missing_canonical))
    if unexpected_canonical:
        errors.append("unexpected canonical business-case types: " + ", ".join(unexpected_canonical))
    if missing_aliases:
        errors.append("missing legacy aliases: " + ", ".join(missing_aliases))
    if unexpected_aliases:
        errors.append("unexpected legacy aliases: " + ", ".join(unexpected_aliases))

    canonical_id_set = set(canonical_ids)
    collisions = sorted(alias_slugs & canonical_id_set)
    if collisions:
        errors.append("alias/canonical ID collisions: " + ", ".join(collisions))
    for alias, target in sorted(alias_targets.items()):
        if target == alias:
            errors.append(f"{alias}: alias target must not reference itself")
        if target in alias_slugs:
            errors.append(f"{alias}: alias chains are not allowed (target {target})")
        elif target not in canonical_id_set:
            errors.append(f"{alias}: unknown canonical alias target {target}")

    for start in sorted(alias_targets):
        visited: set[str] = set()
        current = start
        while current in alias_targets:
            if current in visited:
                errors.append(f"{start}: alias cycle detected")
                break
            visited.add(current)
            current = alias_targets[current]

    return errors


def _valid_business_case_type_id(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) <= BUSINESS_CASE_TYPE_ID_MAX_LENGTH
        and BUSINESS_CASE_TYPE_ID_RE.fullmatch(value) is not None
    )
