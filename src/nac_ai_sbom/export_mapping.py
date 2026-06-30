from __future__ import annotations

import json
from pathlib import Path
from typing import Any


AI_SBOM_BASELINE_PATH = Path("sbom") / "ai" / "nac-ai-sbom-draft.json"
EXPORT_MAPPING_PATH = Path("sbom") / "ai" / "nac-ai-sbom-export-mapping.json"
REQUIRED_TARGET_PROFILES = {"cyclonedx-json", "spdx-json"}
REQUIRED_CLUSTERS = {
    "metadata",
    "system_level_properties",
    "models",
    "datasets",
    "infrastructure",
    "agent_tooling_candidates",
    "security_properties",
    "key_performance_indicators",
}
REQUIRED_SCOPE_FALSE = {
    "release_export_enabled",
    "external_tool_execution_enabled",
    "dependency_scan_execution_enabled",
    "model_runtime_inventory_enabled",
    "mandate_data_allowed",
    "secret_material_allowed",
}
REQUIRED_EVIDENCE = {
    "ai_sbom_baseline_ref",
    "cyclonedx_json_ref",
    "spdx_json_ref",
    "tool_versions_ref",
    "release_tag_ref",
    "owner_apply_ref",
    "no_mandate_data_attestation",
    "no_secret_material_attestation",
}
REQUIRED_BLOCKED_ACTIONS = {
    "attach_ai_sbom_to_release_without_owner_apply",
    "run_external_sbom_tool_from_mapping",
    "store_mandate_data_in_sbom_export",
    "store_secret_material_in_sbom_export",
    "claim_cyclonedx_or_spdx_compliance_without_generated_artifact",
    "publish_release_bound_ai_sbom_without_review",
}
PROHIBITED_MARKERS = {
    "api_key",
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "password=",
    "PIN:",
}


def load_export_mapping(repo_root: Path) -> dict[str, Any]:
    path = repo_root / EXPORT_MAPPING_PATH
    if not path.is_file():
        raise KeyError(f"Unknown AI-SBOM export mapping: {EXPORT_MAPPING_PATH}")
    text = path.read_text(encoding="utf-8")
    _reject_prohibited_text(path, text, repo_root)
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError(f"AI-SBOM export mapping must be an object: {path}")
    validate_export_mapping_payload(payload, repo_root)
    return payload


def ai_sbom_export_mapping_status(repo_root: Path) -> dict[str, Any]:
    payload = load_export_mapping(repo_root)
    scope = payload["scope"]
    return {
        "schema_version": "nac.ai-sbom-export-mapping-status/v0.1",
        "artifact_id": payload["artifact_id"],
        "status": payload["status"],
        "target_profiles": [
            {
                "id": profile["id"],
                "format": profile["format"],
                "status": profile["status"],
                "release_binding": profile["release_binding"],
            }
            for profile in payload["target_profiles"]
        ],
        "mapped_clusters": [item["nac_cluster"] for item in payload["cluster_mapping"]],
        "release_export_enabled": scope["release_export_enabled"],
        "external_tool_execution_enabled": scope["external_tool_execution_enabled"],
        "mandate_data_allowed": scope["mandate_data_allowed"],
        "secret_material_allowed": scope["secret_material_allowed"],
        "owner_apply_required_before_release_binding": scope[
            "owner_apply_required_before_release_binding"
        ],
        "blocked_actions": payload["blocked_actions"],
    }


def validate_export_mapping_payload(payload: dict[str, Any], repo_root: Path) -> None:
    if payload.get("schema_version") != "nac.ai-sbom-export-mapping/v0.1":
        raise ValueError("AI-SBOM export mapping schema_version muss nac.ai-sbom-export-mapping/v0.1 sein")
    if payload.get("artifact_id") != "nac-ai-sbom-cyclonedx-spdx-export-mapping":
        raise ValueError("AI-SBOM export mapping artifact_id ist unerwartet")
    if payload.get("status") != "mapping_selected_no_release_export":
        raise ValueError("AI-SBOM export mapping status muss mapping_selected_no_release_export sein")
    _validate_source_documents(payload, repo_root)
    _validate_scope(payload)
    _validate_target_profiles(payload)
    _validate_cluster_mapping(payload, repo_root)
    _validate_evidence_and_blocked_actions(payload)


def _validate_source_documents(payload: dict[str, Any], repo_root: Path) -> None:
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        raise ValueError("AI-SBOM export mapping source_documents muss ein Objekt sein")
    if source_documents.get("ai_sbom_baseline") != str(AI_SBOM_BASELINE_PATH):
        raise ValueError("AI-SBOM export mapping muss die AI-SBOM-Baseline referenzieren")
    for key, value in source_documents.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("AI-SBOM export mapping source_documents braucht String-Eintraege")
        if not (repo_root / value).is_file():
            raise ValueError(f"AI-SBOM export mapping source_documents.{key} zeigt auf fehlende Datei")


def _validate_scope(payload: dict[str, Any]) -> None:
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        raise ValueError("AI-SBOM export mapping scope muss ein Objekt sein")
    for key in sorted(REQUIRED_SCOPE_FALSE):
        if scope.get(key) is not False:
            raise ValueError(f"AI-SBOM export mapping scope.{key} muss false sein")
    if scope.get("owner_apply_required_before_release_binding") is not True:
        raise ValueError("AI-SBOM export mapping owner_apply_required_before_release_binding muss true sein")


def _validate_target_profiles(payload: dict[str, Any]) -> None:
    profiles = payload.get("target_profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("AI-SBOM export mapping target_profiles muss eine nicht leere Liste sein")
    by_id = {
        item.get("id"): item
        for item in profiles
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = REQUIRED_TARGET_PROFILES - set(by_id)
    if missing:
        raise ValueError(f"AI-SBOM export mapping target_profiles fehlen: {', '.join(sorted(missing))}")
    for profile_id, profile in by_id.items():
        for field in ("format", "role", "status", "tooling_candidate", "release_binding"):
            if not isinstance(profile.get(field), str) or not profile[field]:
                raise ValueError(f"AI-SBOM export mapping target {profile_id} braucht {field}")
        if profile["status"] != "selected_mapping_target_no_export":
            raise ValueError(f"AI-SBOM export mapping target {profile_id} darf noch keinen Export aktivieren")
        if profile["release_binding"] != "pending":
            raise ValueError(f"AI-SBOM export mapping target {profile_id} release_binding muss pending sein")


def _validate_cluster_mapping(payload: dict[str, Any], repo_root: Path) -> None:
    baseline = _load_baseline(repo_root)
    baseline_clusters = set(baseline.get("clusters", {}))
    mapping = payload.get("cluster_mapping")
    if not isinstance(mapping, list) or not mapping:
        raise ValueError("AI-SBOM export mapping cluster_mapping muss eine nicht leere Liste sein")
    mapped_clusters = {
        item.get("nac_cluster")
        for item in mapping
        if isinstance(item, dict) and isinstance(item.get("nac_cluster"), str)
    }
    missing = REQUIRED_CLUSTERS - mapped_clusters
    if missing:
        raise ValueError(f"AI-SBOM export mapping cluster_mapping fehlt: {', '.join(sorted(missing))}")
    missing_in_baseline = REQUIRED_CLUSTERS - baseline_clusters
    if missing_in_baseline:
        raise ValueError(f"AI-SBOM baseline cluster fehlen: {', '.join(sorted(missing_in_baseline))}")
    for item in mapping:
        if not isinstance(item, dict):
            raise ValueError("AI-SBOM export mapping cluster_mapping Eintraege muessen Objekte sein")
        cluster = item.get("nac_cluster")
        for field in ("cyclonedx_target", "spdx_target"):
            if not isinstance(item.get(field), str) or not item[field]:
                raise ValueError(f"AI-SBOM export mapping cluster {cluster} braucht {field}")
        if not isinstance(item.get("required_before_release"), bool):
            raise ValueError(f"AI-SBOM export mapping cluster {cluster} braucht required_before_release")


def _validate_evidence_and_blocked_actions(payload: dict[str, Any]) -> None:
    evidence = set(_strings(payload.get("required_release_evidence")))
    missing_evidence = REQUIRED_EVIDENCE - evidence
    if missing_evidence:
        raise ValueError(
            "AI-SBOM export mapping required_release_evidence fehlt: "
            f"{', '.join(sorted(missing_evidence))}"
        )
    blocked = set(_strings(payload.get("blocked_actions")))
    missing_blocked = REQUIRED_BLOCKED_ACTIONS - blocked
    if missing_blocked:
        raise ValueError(f"AI-SBOM export mapping blocked_actions fehlt: {', '.join(sorted(missing_blocked))}")


def _load_baseline(repo_root: Path) -> dict[str, Any]:
    path = repo_root / AI_SBOM_BASELINE_PATH
    if not path.is_file():
        raise ValueError("AI-SBOM baseline fehlt")
    return json.loads(path.read_text(encoding="utf-8"))


def _reject_prohibited_text(path: Path, text: str, repo_root: Path) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            raise ValueError(f"{path.relative_to(repo_root)} enthaelt unzulaessigen Marker: {marker}")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
