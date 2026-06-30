from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import assert_no_prohibited_payload


MODEL_CARD_PROPOSAL_PATH = (
    Path("workflows")
    / "legal-model"
    / "model-card-proposals"
    / "legal-nemotron-metadata-only.model-card.json"
)
REQUIRED_SCOPE_FALSE = {
    "training_enabled",
    "checkpoint_publication_enabled",
    "model_evaluation_executed",
    "benchmark_dataset_generated",
    "production_legal_answer_system_enabled",
    "mandate_data_allowed",
    "publisher_full_text_allowed",
}
REQUIRED_SECTIONS = {
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
REQUIRED_CANDIDATES = {
    "nvidia-nemotron-pretraining-legal-v1",
    "recht-bund-bgbl-data-access",
    "wikipedia-rechtsquelle-concept-reference",
}
REQUIRED_ATTESTATIONS = {
    "no_mandate_data",
    "no_checkpoint_published",
    "no_source_text_stored",
    "no_quality_claim",
    "no_runtime_enabled",
}
REQUIRED_BLOCKED_ACTIONS = {
    "train_from_model_card_proposal",
    "publish_checkpoint_from_model_card_proposal",
    "claim_legal_answer_quality",
    "store_source_text_in_model_card",
    "use_mandate_data_in_model_card",
    "activate_runtime_endpoint",
    "generate_benchmark_rows_without_owner_apply",
}
PLACEHOLDER_MARKERS = {"todo", "tbd", "placeholder", "changeme", "dummy"}


def load_model_card_proposal(repo_root: Path) -> dict[str, Any]:
    path = repo_root / MODEL_CARD_PROPOSAL_PATH
    if not path.is_file():
        raise KeyError(f"Unknown legal model card proposal: {MODEL_CARD_PROPOSAL_PATH}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Legal model card proposal must be an object: {path}")
    validate_model_card_proposal(payload, repo_root)
    return payload


def legal_model_card_proposal_status(repo_root: Path) -> dict[str, Any]:
    payload = load_model_card_proposal(repo_root)
    sections = payload["model_card_sections"]
    attestations = payload["attestations"]
    return {
        "schema_version": "nac.legal-model-card-proposal-status/v0.1",
        "artifact_id": payload["artifact_id"],
        "status": payload["status"],
        "sections": len(sections),
        "candidate_references": [
            {
                "id": item["id"],
                "role": item["role"],
                "status": item["status"],
            }
            for item in payload["candidate_references"]
        ],
        "no_mandate_data": attestations["no_mandate_data"],
        "no_checkpoint_published": attestations["no_checkpoint_published"],
        "no_runtime_enabled": attestations["no_runtime_enabled"],
        "owner_apply_required_before_use": payload["scope"]["owner_apply_required_before_use"],
        "blocked_actions": payload["blocked_actions"],
    }


def validate_model_card_proposal(payload: dict[str, Any], repo_root: Path) -> None:
    assert_no_prohibited_payload(payload)
    if payload.get("schema_version") != "nac.legal-model-card-proposal/v0.1":
        raise ValueError("model card proposal schema_version muss nac.legal-model-card-proposal/v0.1 sein")
    if payload.get("artifact_id") != "legal-nemotron-metadata-only-model-card-proposal":
        raise ValueError("model card proposal artifact_id ist unerwartet")
    if payload.get("status") != "proposal_no_checkpoint_no_training":
        raise ValueError("model card proposal status muss proposal_no_checkpoint_no_training sein")
    _validate_source_documents(payload, repo_root)
    _validate_scope(payload)
    _validate_sections(payload)
    _validate_candidates(payload)
    _validate_attestations(payload)
    _validate_blocked_actions(payload)


def _validate_source_documents(payload: dict[str, Any], repo_root: Path) -> None:
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        raise ValueError("model card proposal source_documents muss ein Objekt sein")
    for key, value in source_documents.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("model card proposal source_documents braucht String-Eintraege")
        if not (repo_root / value).is_file():
            raise ValueError(f"model card proposal source_documents.{key} zeigt auf fehlende Datei")


def _validate_scope(payload: dict[str, Any]) -> None:
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("model card proposal scope muss ein Objekt sein")
    for key in sorted(REQUIRED_SCOPE_FALSE):
        if scope.get(key) is not False:
            raise ValueError(f"model card proposal scope.{key} muss false sein")
    if scope.get("owner_apply_required_before_use") is not True:
        raise ValueError("model card proposal owner_apply_required_before_use muss true sein")


def _validate_sections(payload: dict[str, Any]) -> None:
    sections = payload.get("model_card_sections")
    if not isinstance(sections, dict):
        raise ValueError("model card proposal model_card_sections muss ein Objekt sein")
    missing = REQUIRED_SECTIONS - set(sections)
    if missing:
        raise ValueError(f"model card proposal model_card_sections fehlen: {', '.join(sorted(missing))}")
    for section_id, section in sections.items():
        if not isinstance(section, dict):
            raise ValueError(f"model card proposal section {section_id} muss ein Objekt sein")
        status = section.get("status")
        summary = section.get("summary")
        refs = section.get("refs")
        if not isinstance(status, str) or not status:
            raise ValueError(f"model card proposal section {section_id} braucht status")
        if not isinstance(summary, str) or len(summary) < 24:
            raise ValueError(f"model card proposal section {section_id} braucht summary")
        if not _strings(refs):
            raise ValueError(f"model card proposal section {section_id} braucht refs")
        _reject_placeholders(f"section {section_id}", f"{status} {summary} {' '.join(_strings(refs))}")


def _validate_candidates(payload: dict[str, Any]) -> None:
    candidates = payload.get("candidate_references")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("model card proposal candidate_references muss eine nicht leere Liste sein")
    by_id = {
        item.get("id"): item
        for item in candidates
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = REQUIRED_CANDIDATES - set(by_id)
    if missing:
        raise ValueError(f"model card proposal candidate_references fehlen: {', '.join(sorted(missing))}")
    for candidate_id, candidate in by_id.items():
        for field in ("role", "status"):
            if not isinstance(candidate.get(field), str) or not candidate[field]:
                raise ValueError(f"model card proposal candidate {candidate_id} braucht {field}")
        if not _strings(candidate.get("blocked_before_owner_apply")):
            raise ValueError(f"model card proposal candidate {candidate_id} braucht blocked_before_owner_apply")


def _validate_attestations(payload: dict[str, Any]) -> None:
    attestations = payload.get("attestations")
    if not isinstance(attestations, dict):
        raise ValueError("model card proposal attestations muss ein Objekt sein")
    for key in sorted(REQUIRED_ATTESTATIONS):
        if attestations.get(key) is not True:
            raise ValueError(f"model card proposal attestations.{key} muss true sein")


def _validate_blocked_actions(payload: dict[str, Any]) -> None:
    blocked = set(_strings(payload.get("blocked_actions")))
    missing = REQUIRED_BLOCKED_ACTIONS - blocked
    if missing:
        raise ValueError(f"model card proposal blocked_actions fehlen: {', '.join(sorted(missing))}")
    if not _strings(payload.get("next_required_evidence")):
        raise ValueError("model card proposal next_required_evidence muss gesetzt sein")


def _reject_placeholders(label: str, text: str) -> None:
    lowered = text.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker in lowered:
            raise ValueError(f"model card proposal {label} enthaelt Platzhaltermarker: {marker}")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
