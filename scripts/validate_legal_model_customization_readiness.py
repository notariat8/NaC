from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "legal-model-customization-readiness.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "legal-model-customization-readiness.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "legal-model-customization-readiness.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCES = {
    "legal_research_connectors",
    "legal_graph_contract",
    "ai_sbom_policy",
    "language_policy",
    "build_now",
}
REQUIRED_SCOPE_FALSE = {
    "training_enabled",
    "checkpoint_publication_enabled",
    "production_legal_answer_system_enabled",
    "mandate_data_allowed",
    "publisher_full_text_allowed",
    "remote_execution_enabled",
}
REQUIRED_SCOPE_TRUE = {"owner_apply_required_before_any_training"}
REQUIRED_CANDIDATE_IDS = {
    "nvidia-nemotron-pretraining-legal-v1",
    "recht-bund-bgbl-data-access",
    "wikipedia-rechtsquelle-concept-reference",
}
REQUIRED_GATES = {
    "source_inventory_and_license_gate",
    "source_hierarchy_gate",
    "corpus_normalization_gate",
    "german_law_benchmark_gate",
    "model_card_and_ai_sbom_gate",
    "owner_apply_gate",
}
REQUIRED_STEPS = {
    "curate/nemo_curator",
    "data_prep/pretrain_prep",
    "pretrain/automodel",
    "pretrain/megatron_bridge",
    "eval/model_eval",
    "byob/mcq",
}
REQUIRED_BLOCKED_ACTIONS = {
    "emit_runnable_training_command_with_placeholders",
    "start_finetuning_without_owner_apply",
    "use_mandate_data_for_training",
    "store_publisher_full_text_in_product_repo",
    "publish_checkpoint_without_model_card",
    "claim_legal_truth_from_model_output",
    "skip_human_notarial_review",
}
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "readiness_id",
    "source_inventory_ref",
    "license_review_ref",
    "tdm_review_ref",
    "source_hierarchy_ref",
    "benchmark_ref",
    "evaluation_ref",
    "model_card_ref",
    "ai_sbom_ref",
    "owner_apply_ref",
    "no_mandate_data_attestation",
    "no_training_started_attestation",
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
    if payload.get("contract_id") != "workflow.legal_model_customization_readiness":
        errors.append("contract_id muss workflow.legal_model_customization_readiness sein")
    if payload.get("status") != "readiness_contract_no_training":
        errors.append("status muss readiness_contract_no_training sein")

    errors.extend(_validate_sources(payload))
    errors.extend(_validate_scope(payload))
    errors.extend(_validate_candidates(payload))
    errors.extend(_validate_gates(payload))
    errors.extend(_validate_nemotron_route(payload))
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


def _validate_candidates(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidates = payload.get("candidate_sources")
    if not isinstance(candidates, list) or not candidates:
        return ["candidate_sources muss eine nicht leere Liste sein"]
    by_id = {
        str(candidate.get("id")): candidate
        for candidate in candidates
        if isinstance(candidate, dict) and isinstance(candidate.get("id"), str)
    }
    for missing in sorted(REQUIRED_CANDIDATE_IDS - set(by_id)):
        errors.append(f"candidate_sources fehlt: {missing}")
    for candidate_id, candidate in by_id.items():
        allowed = set(_string_list(candidate.get("allowed_use_before_owner_apply")))
        blocked = set(_string_list(candidate.get("blocked_use_before_owner_apply")))
        if not allowed:
            errors.append(f"{candidate_id}: allowed_use_before_owner_apply muss gesetzt sein")
        if not blocked:
            errors.append(f"{candidate_id}: blocked_use_before_owner_apply muss gesetzt sein")
        if candidate_id == "nvidia-nemotron-pretraining-legal-v1":
            if "fine_tune_model" not in blocked or "treat_as_german_law_source" not in blocked:
                errors.append("Nemotron-Datensatz muss Training und deutsche-Rechtsquelle-Fehlnutzung blockieren")
        if candidate_id == "recht-bund-bgbl-data-access":
            if "bulk_crawl" not in blocked or "train_on_pdf_full_text" not in blocked:
                errors.append("recht.bund.de muss Bulk-Crawl und PDF-Finetuning blockieren")
        if candidate_id == "wikipedia-rechtsquelle-concept-reference":
            if "treat_as_primary_legal_source" not in blocked:
                errors.append("Rechtsquelle-Begriff muss Primaerquellen-Fehlnutzung blockieren")
    return errors


def _validate_gates(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    gates = payload.get("required_readiness_gates")
    if not isinstance(gates, list) or not gates:
        return ["required_readiness_gates muss eine nicht leere Liste sein"]
    by_id = {
        str(gate.get("id")): gate
        for gate in gates
        if isinstance(gate, dict) and isinstance(gate.get("id"), str)
    }
    for missing in sorted(REQUIRED_GATES - set(by_id)):
        errors.append(f"required_readiness_gates fehlt: {missing}")
    for gate_id, gate in by_id.items():
        if not isinstance(gate.get("must_complete_before"), str) or not gate["must_complete_before"]:
            errors.append(f"{gate_id}: must_complete_before muss gesetzt sein")
        evidence = set(_string_list(gate.get("required_evidence")))
        if len(evidence) < 3:
            errors.append(f"{gate_id}: required_evidence braucht mindestens drei Felder")
    return errors


def _validate_nemotron_route(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    plan = payload.get("nemotron_route_plan")
    if not isinstance(plan, dict):
        return ["nemotron_route_plan muss ein Objekt sein"]
    if plan.get("planning_only") is not True:
        errors.append("nemotron_route_plan.planning_only muss true sein")
    stages = plan.get("pipeline_shape")
    if not isinstance(stages, list) or not stages:
        errors.append("nemotron_route_plan.pipeline_shape muss eine nicht leere Liste sein")
    else:
        seen_steps: set[str] = set()
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            candidate_step = stage.get("candidate_step")
            if isinstance(candidate_step, str):
                seen_steps.add(candidate_step)
            seen_steps.update(_string_list(stage.get("candidate_steps")))
            status = stage.get("status")
            if not isinstance(status, str) or not status:
                errors.append("Nemotron-Stage braucht status")
            elif stage.get("stage") != "german_law_evaluation" and "blocked" not in status:
                errors.append(f"{stage.get('stage', '<unknown>')}: Stage muss vor Owner-/Review-Gate blockiert sein")
        for missing in sorted(REQUIRED_STEPS - seen_steps):
            errors.append(f"nemotron_route_plan.pipeline_shape fehlt Schritt {missing}")
    required_inputs = set(_string_list(plan.get("required_inputs_before_runnable_config")))
    for field in ("base_model_or_checkpoint", "approved_corpus_path", "hardware_gpu_count", "evaluation_task_ids"):
        if field not in required_inputs:
            errors.append(f"required_inputs_before_runnable_config fehlt: {field}")
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
        "python scripts/validate_legal_model_customization_readiness.py",
        "python scripts/validate_legal_research_connectors.py",
        "python scripts/validate_legal_graph_contracts.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Legal-Nemotron-Readiness"),
        (DOC_EN, "Legal Nemotron Readiness"),
        (QUALITY_DE, "legal_model_customization_readiness"),
        (QUALITY_EN, "legal_model_customization_readiness"),
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
    print("OK: Legal-Nemotron-Readiness bleibt ohne Training, ohne Mandatsdaten und ohne Checkpoint-Publikation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
