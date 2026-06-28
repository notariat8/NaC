from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "legal-model-evaluation-benchmark.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "legal-model-evaluation-benchmark.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "legal-model-evaluation-benchmark.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCES = {
    "legal_model_customization_readiness",
    "legal_research_connectors",
    "legal_graph_contract",
    "build_now",
}
REQUIRED_SCOPE_FALSE = {
    "benchmark_dataset_generated",
    "model_evaluation_executed",
    "training_enabled",
    "model_quality_claim_enabled",
    "mandate_data_allowed",
    "publisher_full_text_allowed",
}
REQUIRED_SCOPE_TRUE = {"owner_apply_required_before_benchmark_generation"}
REQUIRED_SOURCE_CLASSES = {
    "primary_official_publication",
    "concept_reference",
    "baseline_training_dataset",
    "licensed_commentary_or_publisher_database",
}
REQUIRED_DOMAINS = {"erbrecht", "familienrecht", "gesellschaftsrecht"}
REQUIRED_TASK_FAMILIES = {
    "source_citation_accuracy",
    "temporal_validity",
    "notarial_workflow_fit",
    "refusal_and_uncertainty",
    "source_collision_handling",
}
REQUIRED_BLOCKED_ACTIONS = {
    "generate_benchmark_dataset_without_owner_apply",
    "run_model_eval_without_approved_tasks",
    "train_on_benchmark_holdout",
    "use_mandate_data_in_benchmark",
    "store_publisher_full_text_in_benchmark",
    "publish_quality_claim_without_human_review",
    "treat_automatic_score_as_notarial_truth",
}
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "benchmark_id",
    "source_inventory_ref",
    "source_hierarchy_ref",
    "license_review_ref",
    "held_out_source_manifest_ref",
    "task_family",
    "answer_key_review_ref",
    "evaluation_task_ref",
    "human_review_protocol_ref",
    "no_mandate_data_attestation",
    "no_dataset_generated_attestation",
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
    if payload.get("contract_id") != "workflow.legal_model_evaluation_benchmark":
        errors.append("contract_id muss workflow.legal_model_evaluation_benchmark sein")
    if payload.get("status") != "benchmark_blueprint_no_dataset":
        errors.append("status muss benchmark_blueprint_no_dataset sein")

    errors.extend(_validate_sources(payload))
    errors.extend(_validate_scope(payload))
    errors.extend(_validate_benchmark_design(payload))
    errors.extend(_validate_holdout_and_routes(payload))
    errors.extend(_validate_scoring_and_evidence(payload))
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


def _validate_benchmark_design(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    design = payload.get("benchmark_design")
    if not isinstance(design, dict):
        return ["benchmark_design muss ein Objekt sein"]
    if design.get("planning_only") is not True:
        errors.append("benchmark_design.planning_only muss true sein")
    if design.get("primary_language") != "de":
        errors.append("benchmark_design.primary_language muss de sein")

    source_hierarchy = design.get("source_hierarchy")
    if not isinstance(source_hierarchy, list) or not source_hierarchy:
        errors.append("benchmark_design.source_hierarchy muss eine nicht leere Liste sein")
    else:
        classes = {item.get("class") for item in source_hierarchy if isinstance(item, dict)}
        for missing in sorted(REQUIRED_SOURCE_CLASSES - classes):
            errors.append(f"benchmark_design.source_hierarchy fehlt Klasse {missing}")

    domains = set(_string_list(design.get("domains")))
    for missing in sorted(REQUIRED_DOMAINS - domains):
        errors.append(f"benchmark_design.domains fehlt {missing}")

    task_families = design.get("task_families")
    if not isinstance(task_families, list) or not task_families:
        errors.append("benchmark_design.task_families muss eine nicht leere Liste sein")
    else:
        by_id = {item.get("id"): item for item in task_families if isinstance(item, dict)}
        for missing in sorted(REQUIRED_TASK_FAMILIES - set(by_id)):
            errors.append(f"benchmark_design.task_families fehlt {missing}")
        for task_id, task in by_id.items():
            if task.get("requires_human_review") is not True:
                errors.append(f"{task_id}: requires_human_review muss true sein")
    return errors


def _validate_holdout_and_routes(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    holdout = payload.get("holdout_policy")
    if not isinstance(holdout, dict):
        errors.append("holdout_policy muss ein Objekt sein")
    else:
        if holdout.get("requires_held_out_sources") is not True:
            errors.append("holdout_policy.requires_held_out_sources muss true sein")
        if holdout.get("train_eval_overlap_allowed") is not False:
            errors.append("holdout_policy.train_eval_overlap_allowed muss false sein")
        if holdout.get("source_leakage_check_required") is not True:
            errors.append("holdout_policy.source_leakage_check_required muss true sein")

    route = payload.get("nemotron_route_plan")
    if not isinstance(route, dict):
        return errors + ["nemotron_route_plan muss ein Objekt sein"]
    if route.get("planning_only") is not True:
        errors.append("nemotron_route_plan.planning_only muss true sein")
    if route.get("benchmark_generation_candidate_step") != "byob/mcq":
        errors.append("benchmark_generation_candidate_step muss byob/mcq sein")
    if route.get("evaluation_candidate_step") != "eval/model_eval":
        errors.append("evaluation_candidate_step muss eval/model_eval sein")
    blocked_until = set(_string_list(route.get("blocked_until")))
    for gate in ("source_inventory_and_license_gate", "german_law_benchmark_gate", "owner_apply_gate"):
        if gate not in blocked_until:
            errors.append(f"nemotron_route_plan.blocked_until fehlt {gate}")
    required_inputs = set(_string_list(route.get("required_inputs_before_runnable_config")))
    for field in ("approved_benchmark_source_corpus", "evaluation_task_ids", "target_model_or_endpoint"):
        if field not in required_inputs:
            errors.append(f"required_inputs_before_runnable_config fehlt {field}")
    return errors


def _validate_scoring_and_evidence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scoring = payload.get("scoring_policy")
    if not isinstance(scoring, dict):
        errors.append("scoring_policy muss ein Objekt sein")
    else:
        if scoring.get("automatic_score_is_advisory_only") is not True:
            errors.append("scoring_policy.automatic_score_is_advisory_only muss true sein")
        if scoring.get("human_notarial_review_required") is not True:
            errors.append("scoring_policy.human_notarial_review_required muss true sein")
        blocked_claims = set(_string_list(scoring.get("blocked_quality_claims")))
        for claim in ("legally_reliable_without_review", "notarial_decision_replacement"):
            if claim not in blocked_claims:
                errors.append(f"scoring_policy.blocked_quality_claims fehlt {claim}")

    blocked = set(_string_list(payload.get("blocked_actions")))
    for missing in sorted(REQUIRED_BLOCKED_ACTIONS - blocked):
        errors.append(f"blocked_actions fehlt: {missing}")
    evidence = set(_string_list(payload.get("required_evidence_fields")))
    for missing in sorted(REQUIRED_EVIDENCE_FIELDS - evidence):
        errors.append(f"required_evidence_fields fehlt: {missing}")
    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_legal_model_evaluation_benchmark.py",
        "python scripts/validate_legal_model_customization_readiness.py",
        "python scripts/validate_legal_research_connectors.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Legal-Model-Evaluationsbenchmark"),
        (DOC_EN, "Legal Model Evaluation Benchmark"),
        (QUALITY_DE, "legal_model_evaluation_benchmark"),
        (QUALITY_EN, "legal_model_evaluation_benchmark"),
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
    print("OK: Legal-Model-Evaluationsbenchmark bleibt Blueprint ohne Datensatz, Modelllauf oder Qualitätsbehauptung.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
