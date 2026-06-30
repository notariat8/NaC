from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "legal-source-inventory-license-tdm.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "legal-source-inventory-license-tdm.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "legal-source-inventory-license-tdm.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCES = {
    "legal_research_connectors",
    "legal_model_customization_readiness",
    "legal_model_evaluation_benchmark",
    "legal_graph_contract",
    "build_now",
}
REQUIRED_SCOPE_FALSE = {
    "source_text_ingestion_enabled",
    "benchmark_dataset_generated",
    "model_training_enabled",
    "model_evaluation_executed",
    "mandate_data_allowed",
    "publisher_full_text_allowed",
    "automated_bulk_crawl_enabled",
}
REQUIRED_SCOPE_TRUE = {"owner_apply_required_before_ingestion"}
REQUIRED_INVENTORY_IDS = {
    "nvidia-nemotron-pretraining-legal-v1",
    "recht-bund-bgbl-data-access",
    "wikipedia-rechtsquelle-concept-reference",
}
REQUIRED_MINIMUM_FIELDS = {
    "source_id",
    "canonical_url",
    "source_class",
    "jurisdiction_fit",
    "license_status",
    "tdm_status",
    "terms_review_ref",
    "attribution_plan",
    "allowed_pre_apply_actions",
    "blocked_pre_apply_actions",
    "human_review_owner",
}
REQUIRED_REVIEW_DEPTH_FIELDS = {
    "record_completeness",
    "license_terms_depth",
    "tdm_depth",
    "attribution_depth",
    "storage_boundary_depth",
    "next_required_review",
}
REQUIRED_GATES = {
    "source_record_completeness_gate",
    "license_basis_gate",
    "tdm_permitted_use_gate",
    "storage_boundary_gate",
    "owner_apply_gate",
}
REQUIRED_BLOCKED_ACTIONS = {
    "download_full_text_corpus_without_owner_apply",
    "bulk_crawl_without_terms_review",
    "generate_benchmark_dataset_without_license_tdm_gate",
    "run_model_eval_without_approved_tasks",
    "train_or_finetune_without_owner_apply",
    "store_publisher_full_text_in_product_repo",
    "use_mandate_data_for_source_inventory",
    "treat_concept_reference_as_primary_source",
    "claim_legal_truth_from_inventory_status",
}
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "inventory_id",
    "source_inventory_ref",
    "license_review_ref",
    "tdm_review_ref",
    "terms_review_ref",
    "attribution_plan_ref",
    "storage_boundary_ref",
    "owner_apply_ref",
    "no_mandate_data_attestation",
    "no_source_text_ingested_attestation",
}
PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "client_secret",
    "ghp_",
    "gho_",
    "oci_session_token",
    "password=",
    "PIN:",
}


def validate_contract(path: Path = CONTRACT_PATH) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Pflichtvertrag fehlt: {path.relative_to(REPO_ROOT)}"]

    text = path.read_text(encoding="utf-8")
    _reject_prohibited_text(path, text, errors)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{path.relative_to(REPO_ROOT)} ist kein gueltiges JSON: {exc}"]
    if not isinstance(payload, dict):
        return [f"{path.relative_to(REPO_ROOT)} muss ein JSON-Objekt sein"]

    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != "workflow.legal_source_inventory_license_tdm":
        errors.append("contract_id muss workflow.legal_source_inventory_license_tdm sein")
    if payload.get("status") != "source_inventory_readiness_no_ingestion":
        errors.append("status muss source_inventory_readiness_no_ingestion sein")

    errors.extend(_validate_sources(payload))
    errors.extend(_validate_scope(payload))
    errors.extend(_validate_inventory_policy(payload))
    errors.extend(_validate_source_inventory(payload))
    errors.extend(_validate_gates(payload))
    errors.extend(_validate_blocked_actions_and_evidence(payload))
    errors.extend(_validate_docs())
    return errors


def _validate_sources(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        return ["source_documents muss ein Objekt sein"]
    for key in sorted(REQUIRED_SOURCES):
        value = source_documents.get(key)
        if not isinstance(value, str):
            errors.append(f"source_documents.{key} fehlt")
            continue
        if not (REPO_ROOT / value).is_file():
            errors.append(f"source_documents.{key} zeigt auf fehlende Datei: {value}")
    return errors


def _validate_scope(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        return ["scope muss ein Objekt sein"]
    for key in sorted(REQUIRED_SCOPE_FALSE):
        if scope.get(key) is not False:
            errors.append(f"scope.{key} muss false sein")
    for key in sorted(REQUIRED_SCOPE_TRUE):
        if scope.get(key) is not True:
            errors.append(f"scope.{key} muss true sein")
    return errors


def _validate_inventory_policy(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = payload.get("inventory_policy")
    if not isinstance(policy, dict):
        return ["inventory_policy muss ein Objekt sein"]
    if policy.get("planning_only") is not True:
        errors.append("inventory_policy.planning_only muss true sein")
    if policy.get("primary_language") != "de":
        errors.append("inventory_policy.primary_language muss de sein")
    minimum_fields = set(_string_list(policy.get("minimum_record_fields")))
    for missing in sorted(REQUIRED_MINIMUM_FIELDS - minimum_fields):
        errors.append(f"inventory_policy.minimum_record_fields fehlt: {missing}")
    blocked = set(_string_list(policy.get("blocked_pre_apply_actions")))
    for action in ("download_full_text_corpus", "bulk_crawl_source", "train_or_finetune_model"):
        if action not in blocked:
            errors.append(f"inventory_policy.blocked_pre_apply_actions fehlt: {action}")
    return errors


def _validate_source_inventory(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    inventory = payload.get("source_inventory")
    if not isinstance(inventory, list) or not inventory:
        return ["source_inventory muss eine nicht leere Liste sein"]
    by_id = {
        str(item.get("source_id")): item
        for item in inventory
        if isinstance(item, dict) and isinstance(item.get("source_id"), str)
    }
    for missing in sorted(REQUIRED_INVENTORY_IDS - set(by_id)):
        errors.append(f"source_inventory fehlt: {missing}")
    for source_id, item in by_id.items():
        missing_fields = [field for field in sorted(REQUIRED_MINIMUM_FIELDS) if field not in item]
        for field in missing_fields:
            errors.append(f"{source_id}: Pflichtfeld fehlt: {field}")
        allowed = set(_string_list(item.get("allowed_pre_apply_actions")))
        blocked = set(_string_list(item.get("blocked_pre_apply_actions")))
        if not allowed:
            errors.append(f"{source_id}: allowed_pre_apply_actions muss gesetzt sein")
        if not blocked:
            errors.append(f"{source_id}: blocked_pre_apply_actions muss gesetzt sein")
        if item.get("terms_review_ref") != "pending":
            errors.append(f"{source_id}: terms_review_ref bleibt vor Review pending")
        if item.get("human_review_owner") != "owner_required":
            errors.append(f"{source_id}: human_review_owner muss owner_required sein")
        review_depth = item.get("review_depth")
        if not isinstance(review_depth, dict):
            errors.append(f"{source_id}: review_depth muss ein Objekt sein")
        else:
            for field in sorted(REQUIRED_REVIEW_DEPTH_FIELDS):
                if not isinstance(review_depth.get(field), str) or not review_depth[field]:
                    errors.append(f"{source_id}: review_depth.{field} muss gesetzt sein")
            if review_depth.get("record_completeness") != "seed_metadata_complete":
                errors.append(f"{source_id}: review_depth.record_completeness muss seed_metadata_complete sein")
        if source_id == "nvidia-nemotron-pretraining-legal-v1":
            if "train_or_finetune_model" not in blocked or "treat_as_german_law_source" not in blocked:
                errors.append("Nemotron-Datensatz muss Training und deutsche-Rechtsquelle-Fehlnutzung blockieren")
        if source_id == "recht-bund-bgbl-data-access":
            for action in ("download_full_text_corpus", "bulk_crawl_source", "normalize_full_text_for_training"):
                if action not in blocked:
                    errors.append(f"recht.bund.de muss {action} blockieren")
        if source_id == "wikipedia-rechtsquelle-concept-reference":
            if "treat_as_primary_legal_source" not in blocked:
                errors.append("Rechtsquelle-Begriff muss Primaerquellen-Fehlnutzung blockieren")
    return errors


def _validate_gates(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    gates = payload.get("required_gates")
    if not isinstance(gates, list) or not gates:
        return ["required_gates muss eine nicht leere Liste sein"]
    by_id = {
        str(gate.get("id")): gate
        for gate in gates
        if isinstance(gate, dict) and isinstance(gate.get("id"), str)
    }
    for missing in sorted(REQUIRED_GATES - set(by_id)):
        errors.append(f"required_gates fehlt: {missing}")
    for gate_id, gate in by_id.items():
        if not isinstance(gate.get("must_complete_before"), str) or not gate["must_complete_before"]:
            errors.append(f"{gate_id}: must_complete_before muss gesetzt sein")
        evidence = set(_string_list(gate.get("required_evidence")))
        if len(evidence) < 4:
            errors.append(f"{gate_id}: required_evidence braucht mindestens vier Felder")
    return errors


def _validate_blocked_actions_and_evidence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    blocked = set(_string_list(payload.get("blocked_actions")))
    for missing in sorted(REQUIRED_BLOCKED_ACTIONS - blocked):
        errors.append(f"blocked_actions fehlt: {missing}")
    evidence = set(_string_list(payload.get("required_evidence_fields")))
    for missing in sorted(REQUIRED_EVIDENCE_FIELDS - evidence):
        errors.append(f"required_evidence_fields fehlt: {missing}")
    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_legal_source_inventory_license_tdm.py",
        "python scripts/validate_legal_model_customization_readiness.py",
        "python scripts/validate_legal_model_evaluation_benchmark.py",
        "python scripts/validate_legal_research_connectors.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Legal-Source-Inventar"),
        (DOC_EN, "Legal Source Inventory"),
        (QUALITY_DE, "legal_source_inventory_license_tdm"),
        (QUALITY_EN, "legal_source_inventory_license_tdm"),
    )
    for path, marker in required_markers:
        if not path.is_file():
            errors.append(f"Pflichtdokument fehlt: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        _reject_prohibited_text(path, text, errors)
        if marker not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt Marker nicht: {marker}")
    return errors


def _reject_prohibited_text(path: Path, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt unzulaessigen Marker: {marker}")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    errors = validate_contract()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Legal-Source-Inventar bleibt ohne Ingestion, Benchmark, Modelllauf oder Training.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
