from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import assert_no_prohibited_payload


AI_SBOM_DELTA_PROPOSAL_PATH = (
    Path("workflows")
    / "legal-model"
    / "ai-sbom-deltas"
    / "legal-nemotron-metadata-only.ai-sbom-delta.json"
)
REQUIRED_SCOPE_FALSE = {
    "baseline_update_only",
    "runtime_activation_enabled",
    "endpoint_enabled",
    "training_enabled",
    "model_evaluation_executed",
    "benchmark_dataset_generated",
    "checkpoint_publication_enabled",
    "mandate_data_allowed",
    "publisher_full_text_allowed",
}
REQUIRED_DELTA_COMPONENTS = {
    "base_model_or_checkpoint",
    "dataset_candidates",
    "legal_source_inventory",
    "training_or_evaluation_runtime",
    "third_party_services",
    "license_and_tdm_status",
    "risk_controls",
    "human_review_boundary",
}
REQUIRED_CANDIDATES = {
    "nvidia-nemotron-pretraining-legal-v1",
    "recht-bund-bgbl-data-access",
    "wikipedia-rechtsquelle-concept-reference",
}
REQUIRED_ATTESTATIONS = {
    "no_mandate_data",
    "no_source_text_stored",
    "no_checkpoint_published",
    "no_runtime_enabled",
    "no_endpoint_enabled",
    "no_quality_claim",
    "no_secret_material",
}
REQUIRED_BLOCKED_ACTIONS = {
    "activate_model_endpoint_from_ai_sbom_delta",
    "publish_checkpoint_from_ai_sbom_delta",
    "train_from_ai_sbom_delta",
    "execute_model_evaluation_from_ai_sbom_delta",
    "store_source_text_in_ai_sbom_delta",
    "store_mandate_data_in_ai_sbom_delta",
    "claim_legal_answer_quality_from_ai_sbom_delta",
    "generate_benchmark_rows_without_owner_apply",
}
PLACEHOLDER_MARKERS = {"todo", "tbd", "placeholder", "changeme", "dummy"}


def load_ai_sbom_delta_proposal(repo_root: Path) -> dict[str, Any]:
    path = repo_root / AI_SBOM_DELTA_PROPOSAL_PATH
    if not path.is_file():
        raise KeyError(f"Unknown legal AI-SBOM delta proposal: {AI_SBOM_DELTA_PROPOSAL_PATH}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Legal AI-SBOM delta proposal must be an object: {path}")
    validate_ai_sbom_delta_proposal(payload, repo_root)
    return payload


def legal_ai_sbom_delta_proposal_status(repo_root: Path) -> dict[str, Any]:
    payload = load_ai_sbom_delta_proposal(repo_root)
    attestations = payload["attestations"]
    return {
        "schema_version": "nac.legal-ai-sbom-delta-proposal-status/v0.1",
        "artifact_id": payload["artifact_id"],
        "status": payload["status"],
        "delta_components": [
            {
                "id": item["id"],
                "status": item["status"],
                "evidence_ref": item["evidence_ref"],
            }
            for item in payload["delta_components"]
        ],
        "candidate_components": [
            {
                "id": item["id"],
                "component_type": item["component_type"],
                "status": item["status"],
            }
            for item in payload["candidate_components"]
        ],
        "no_mandate_data": attestations["no_mandate_data"],
        "no_source_text_stored": attestations["no_source_text_stored"],
        "no_checkpoint_published": attestations["no_checkpoint_published"],
        "no_runtime_enabled": attestations["no_runtime_enabled"],
        "no_endpoint_enabled": attestations["no_endpoint_enabled"],
        "owner_apply_required_before_runtime_or_checkpoint": payload["scope"][
            "owner_apply_required_before_runtime_or_checkpoint"
        ],
        "blocked_actions": payload["blocked_actions"],
    }


def validate_ai_sbom_delta_proposal(payload: dict[str, Any], repo_root: Path) -> None:
    assert_no_prohibited_payload(payload)
    if payload.get("schema_version") != "nac.legal-ai-sbom-delta-proposal/v0.1":
        raise ValueError("AI-SBOM delta proposal schema_version muss nac.legal-ai-sbom-delta-proposal/v0.1 sein")
    if payload.get("artifact_id") != "legal-nemotron-metadata-only-ai-sbom-delta-proposal":
        raise ValueError("AI-SBOM delta proposal artifact_id ist unerwartet")
    if payload.get("status") != "proposal_no_runtime_no_checkpoint":
        raise ValueError("AI-SBOM delta proposal status muss proposal_no_runtime_no_checkpoint sein")
    _validate_source_documents(payload, repo_root)
    _validate_scope(payload)
    _validate_delta_components(payload)
    _validate_candidates(payload)
    _validate_attestations(payload)
    _validate_blocked_actions(payload)


def _validate_source_documents(payload: dict[str, Any], repo_root: Path) -> None:
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        raise ValueError("AI-SBOM delta proposal source_documents muss ein Objekt sein")
    for key, value in source_documents.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("AI-SBOM delta proposal source_documents braucht String-Eintraege")
        if not (repo_root / value).is_file():
            raise ValueError(f"AI-SBOM delta proposal source_documents.{key} zeigt auf fehlende Datei")


def _validate_scope(payload: dict[str, Any]) -> None:
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("AI-SBOM delta proposal scope muss ein Objekt sein")
    for key in sorted(REQUIRED_SCOPE_FALSE):
        if scope.get(key) is not False:
            raise ValueError(f"AI-SBOM delta proposal scope.{key} muss false sein")
    if scope.get("owner_apply_required_before_runtime_or_checkpoint") is not True:
        raise ValueError("AI-SBOM delta proposal owner_apply_required_before_runtime_or_checkpoint muss true sein")


def _validate_delta_components(payload: dict[str, Any]) -> None:
    components = payload.get("delta_components")
    if not isinstance(components, list) or not components:
        raise ValueError("AI-SBOM delta proposal delta_components muss eine nicht leere Liste sein")
    by_id = {
        item.get("id"): item
        for item in components
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = REQUIRED_DELTA_COMPONENTS - set(by_id)
    if missing:
        raise ValueError(f"AI-SBOM delta proposal delta_components fehlen: {', '.join(sorted(missing))}")
    for component_id, component in by_id.items():
        for field in ("status", "summary", "evidence_ref"):
            if not isinstance(component.get(field), str) or not component[field]:
                raise ValueError(f"AI-SBOM delta proposal component {component_id} braucht {field}")
        if len(component["summary"]) < 24:
            raise ValueError(f"AI-SBOM delta proposal component {component_id} braucht summary")
        _reject_placeholders(
            f"component {component_id}",
            f"{component['status']} {component['summary']} {component['evidence_ref']}",
        )


def _validate_candidates(payload: dict[str, Any]) -> None:
    candidates = payload.get("candidate_components")
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("AI-SBOM delta proposal candidate_components muss eine nicht leere Liste sein")
    by_id = {
        item.get("id"): item
        for item in candidates
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = REQUIRED_CANDIDATES - set(by_id)
    if missing:
        raise ValueError(f"AI-SBOM delta proposal candidate_components fehlen: {', '.join(sorted(missing))}")
    for candidate_id, candidate in by_id.items():
        for field in ("component_type", "sbom_role", "status"):
            if not isinstance(candidate.get(field), str) or not candidate[field]:
                raise ValueError(f"AI-SBOM delta proposal candidate {candidate_id} braucht {field}")
        if not _strings(candidate.get("blocked_before_owner_apply")):
            raise ValueError(f"AI-SBOM delta proposal candidate {candidate_id} braucht blocked_before_owner_apply")


def _validate_attestations(payload: dict[str, Any]) -> None:
    attestations = payload.get("attestations")
    if not isinstance(attestations, dict):
        raise ValueError("AI-SBOM delta proposal attestations muss ein Objekt sein")
    for key in sorted(REQUIRED_ATTESTATIONS):
        if attestations.get(key) is not True:
            raise ValueError(f"AI-SBOM delta proposal attestations.{key} muss true sein")


def _validate_blocked_actions(payload: dict[str, Any]) -> None:
    blocked = set(_strings(payload.get("blocked_actions")))
    missing = REQUIRED_BLOCKED_ACTIONS - blocked
    if missing:
        raise ValueError(f"AI-SBOM delta proposal blocked_actions fehlen: {', '.join(sorted(missing))}")
    if not _strings(payload.get("next_required_evidence")):
        raise ValueError("AI-SBOM delta proposal next_required_evidence muss gesetzt sein")


def _reject_placeholders(label: str, text: str) -> None:
    lowered = text.lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker in lowered:
            raise ValueError(f"AI-SBOM delta proposal {label} enthaelt Platzhaltermarker: {marker}")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
