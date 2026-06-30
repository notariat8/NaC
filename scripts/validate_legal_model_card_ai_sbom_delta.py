from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "legal-model-card-ai-sbom-delta.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "legal-model-card-ai-sbom-delta.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "legal-model-card-ai-sbom-delta.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCES = {
    "legal_model_customization_readiness",
    "legal_source_inventory_license_tdm",
    "legal_model_evaluation_benchmark",
    "ai_sbom_baseline",
    "build_now",
}
REQUIRED_SCOPE_FALSE = {
    "training_enabled",
    "model_evaluation_executed",
    "benchmark_dataset_generated",
    "checkpoint_publication_enabled",
    "production_legal_answer_system_enabled",
    "mandate_data_allowed",
    "publisher_full_text_allowed",
}
REQUIRED_SCOPE_TRUE = {"owner_apply_required_before_checkpoint_or_quality_claim"}
REQUIRED_MODEL_CARD_SECTIONS = {
    "base_model_or_checkpoint",
    "intended_use",
    "prohibited_use",
    "source_inventory_summary",
    "license_tdm_summary",
    "data_lineage",
    "evaluation_summary",
    "known_limitations",
    "human_review_protocol",
    "ai_sbom_ref",
    "owner_apply_ref",
    "no_mandate_data_attestation",
}
REQUIRED_AI_SBOM_COMPONENTS = {
    "base_model_or_checkpoint",
    "dataset_candidates",
    "legal_source_inventory",
    "training_or_evaluation_runtime",
    "third_party_services",
    "license_and_tdm_status",
    "risk_controls",
    "human_review_boundary",
}
REQUIRED_CANDIDATE_IDS = {
    "nvidia-nemotron-pretraining-legal-v1",
    "recht-bund-bgbl-data-access",
    "wikipedia-rechtsquelle-concept-reference",
}
REQUIRED_GATES = {
    "model_card_completeness_gate",
    "ai_sbom_delta_gate",
    "legal_use_limitations_gate",
    "evaluation_disclosure_gate",
    "owner_apply_gate",
}
REQUIRED_BLOCKED_ACTIONS = {
    "publish_checkpoint_without_model_card",
    "publish_model_card_with_placeholders",
    "publish_ai_sbom_delta_with_placeholders",
    "claim_legal_answer_quality_without_evaluation_and_human_review",
    "omit_license_tdm_status",
    "omit_no_mandate_data_attestation",
    "start_training_from_model_card_delta",
    "store_source_text_in_model_card_or_ai_sbom",
    "use_mandate_data_for_model_card_or_ai_sbom",
}
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "delta_id",
    "model_card_ref",
    "ai_sbom_ref",
    "source_inventory_ref",
    "license_review_ref",
    "tdm_review_ref",
    "evaluation_ref",
    "limitations_ref",
    "owner_apply_ref",
    "no_mandate_data_attestation",
    "no_checkpoint_published_attestation",
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
    if payload.get("contract_id") != "workflow.legal_model_card_ai_sbom_delta":
        errors.append("contract_id muss workflow.legal_model_card_ai_sbom_delta sein")
    if payload.get("status") != "model_card_ai_sbom_delta_no_checkpoint":
        errors.append("status muss model_card_ai_sbom_delta_no_checkpoint sein")

    errors.extend(_validate_sources(payload))
    errors.extend(_validate_scope(payload))
    errors.extend(_validate_model_card_policy(payload))
    errors.extend(_validate_ai_sbom_policy(payload))
    errors.extend(_validate_candidates(payload))
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


def _validate_model_card_policy(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = payload.get("model_card_delta_policy")
    if not isinstance(policy, dict):
        return ["model_card_delta_policy muss ein Objekt sein"]
    if policy.get("planning_only") is not True:
        errors.append("model_card_delta_policy.planning_only muss true sein")
    sections = set(_string_list(policy.get("minimum_sections")))
    for missing in sorted(REQUIRED_MODEL_CARD_SECTIONS - sections):
        errors.append(f"model_card_delta_policy.minimum_sections fehlt: {missing}")
    blocked = set(_string_list(policy.get("blocked_sections_before_owner_apply")))
    for section in ("production_quality_claim", "notarial_decision_replacement", "checkpoint_download_url"):
        if section not in blocked:
            errors.append(f"model_card_delta_policy.blocked_sections_before_owner_apply fehlt: {section}")
    return errors


def _validate_ai_sbom_policy(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = payload.get("ai_sbom_delta_policy")
    if not isinstance(policy, dict):
        return ["ai_sbom_delta_policy muss ein Objekt sein"]
    if policy.get("planning_only") is not True:
        errors.append("ai_sbom_delta_policy.planning_only muss true sein")
    if policy.get("ai_sbom_status") != "pending_delta_no_runtime":
        errors.append("ai_sbom_delta_policy.ai_sbom_status muss pending_delta_no_runtime sein")
    components = set(_string_list(policy.get("required_delta_components")))
    for missing in sorted(REQUIRED_AI_SBOM_COMPONENTS - components):
        errors.append(f"ai_sbom_delta_policy.required_delta_components fehlt: {missing}")
    blocked = set(_string_list(policy.get("blocked_delta_components_before_owner_apply")))
    for component in ("publisher_full_text_payload", "mandate_data_payload", "secret_or_credential_material"):
        if component not in blocked:
            errors.append(f"ai_sbom_delta_policy.blocked_delta_components_before_owner_apply fehlt: {component}")
    return errors


def _validate_candidates(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = payload.get("candidate_delta_entries")
    if not isinstance(entries, list) or not entries:
        return ["candidate_delta_entries muss eine nicht leere Liste sein"]
    by_id = {
        str(entry.get("id")): entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    for missing in sorted(REQUIRED_CANDIDATE_IDS - set(by_id)):
        errors.append(f"candidate_delta_entries fehlt: {missing}")
    for entry_id, entry in by_id.items():
        if not isinstance(entry.get("model_card_role"), str) or not entry["model_card_role"]:
            errors.append(f"{entry_id}: model_card_role muss gesetzt sein")
        if not isinstance(entry.get("ai_sbom_role"), str) or not entry["ai_sbom_role"]:
            errors.append(f"{entry_id}: ai_sbom_role muss gesetzt sein")
        if not _string_list(entry.get("required_status_before_use")):
            errors.append(f"{entry_id}: required_status_before_use muss gesetzt sein")
        blocked = set(_string_list(entry.get("blocked_before_owner_apply")))
        if not blocked:
            errors.append(f"{entry_id}: blocked_before_owner_apply muss gesetzt sein")
        if entry_id == "nvidia-nemotron-pretraining-legal-v1":
            if "publish_checkpoint" not in blocked or "claim_german_law_coverage" not in blocked:
                errors.append("Nemotron-Delta muss Checkpoint und deutsche-Rechtsabdeckung blockieren")
        if entry_id == "recht-bund-bgbl-data-access":
            if "download_full_text_corpus" not in blocked or "generate_benchmark_rows" not in blocked:
                errors.append("recht.bund.de-Delta muss Volltextdownload und Benchmarkzeilen blockieren")
        if entry_id == "wikipedia-rechtsquelle-concept-reference":
            if "treat_as_primary_legal_source" not in blocked:
                errors.append("Rechtsquelle-Delta muss Primaerquellen-Fehlnutzung blockieren")
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
        "python scripts/validate_legal_model_card_ai_sbom_delta.py",
        "python scripts/validate_legal_model_customization_readiness.py",
        "python scripts/validate_legal_source_inventory_license_tdm.py",
        "python scripts/validate_legal_model_evaluation_benchmark.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Legal-Model-Card-/AI-SBOM-Delta"),
        (DOC_EN, "Legal Model Card AI-SBOM Delta"),
        (QUALITY_DE, "legal_model_card_ai_sbom_delta"),
        (QUALITY_EN, "legal_model_card_ai_sbom_delta"),
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
    print("OK: Legal-Model-Card-/AI-SBOM-Delta bleibt ohne Training, ohne Checkpoint und ohne Qualitätsbehauptung.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
