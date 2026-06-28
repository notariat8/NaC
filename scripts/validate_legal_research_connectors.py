from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "legal-research-connectors.contract.json"

REQUIRED_POLICY_TRUE = {
    "requires_terms_review",
    "requires_avv_review_for_personal_data",
    "requires_human_legal_review",
    "requires_source_attribution",
}
REQUIRED_CANDIDATE_FIELDS = {
    "id",
    "display_name",
    "provider",
    "source_type",
    "status",
    "integration_level",
    "canonical_url",
    "source_seen_at",
    "credentials_required",
    "credentials_in_repo_allowed",
    "personal_data_allowed",
    "license_review_required",
    "avv_dpa_required_before_personal_data",
    "allowed_actions",
    "blocked_actions",
    "evidence_fields",
    "human_review_required_for",
}
ALLOWED_INTEGRATION_LEVELS = {"none", "metadata_only"}
LICENSE_REVIEW_SOURCE_TYPES = {
    "publisher_database_mcp_listing",
    "ai_answer_product",
    "market_landscape",
    "training_dataset_candidate",
    "official_publication_data_access",
    "concept_reference",
}
AI_OR_MCP_SOURCE_TYPES = {
    "mcp_server_listing",
    "publisher_database_mcp_listing",
    "ai_answer_product",
    "market_landscape",
    "training_dataset_candidate",
}
REQUIRED_EVIDENCE_FIELDS = {"source_url", "checked_at", "checked_by", "data_classes", "notes"}
REQUIRED_BLOCKED_ACTIONS = {
    "send_mandate_data_to_external_ai",
    "automated_provider_query_without_contract",
}
PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "secret_value",
}


def validate_contract(path: Path = CONTRACT_PATH) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Pflichtvertrag fehlt: {path.relative_to(REPO_ROOT)}"]

    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} enthält unzulässigen Secret-Marker: {marker}")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{path.relative_to(REPO_ROOT)} ist kein gültiges JSON: {exc}"]

    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != "workflow.legal_research_connectors":
        errors.append("contract_id muss workflow.legal_research_connectors sein")

    policy = payload.get("candidate_policy")
    if not isinstance(policy, dict):
        errors.append("candidate_policy muss ein Objekt sein")
    else:
        if policy.get("credentials_allowed_in_repo") is not False:
            errors.append("candidate_policy.credentials_allowed_in_repo muss false sein")
        if policy.get("production_mandate_data_allowed") is not False:
            errors.append("candidate_policy.production_mandate_data_allowed muss false sein")
        for key in sorted(REQUIRED_POLICY_TRUE):
            if policy.get(key) is not True:
                errors.append(f"candidate_policy.{key} muss true sein")

    required_evidence = set(_string_list(payload.get("required_evidence_fields")))
    for field in sorted(REQUIRED_EVIDENCE_FIELDS - required_evidence):
        errors.append(f"required_evidence_fields fehlt: {field}")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        errors.append("candidates muss eine nicht leere Liste sein")
        return errors

    seen_ids: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            errors.append(f"candidates[{index}] muss ein Objekt sein")
            continue
        candidate_id = candidate.get("id", f"#{index}")
        if not isinstance(candidate_id, str) or not candidate_id:
            errors.append(f"candidates[{index}].id muss gesetzt sein")
            continue
        if candidate_id in seen_ids:
            errors.append(f"Kandidaten-ID doppelt: {candidate_id}")
        seen_ids.add(candidate_id)

        for field in sorted(REQUIRED_CANDIDATE_FIELDS):
            if field not in candidate:
                errors.append(f"{candidate_id}: Pflichtfeld fehlt: {field}")

        if candidate.get("credentials_in_repo_allowed") is not False:
            errors.append(f"{candidate_id}: credentials_in_repo_allowed muss false sein")
        if candidate.get("personal_data_allowed") is not False:
            errors.append(f"{candidate_id}: personal_data_allowed muss false sein")
        if candidate.get("integration_level") not in ALLOWED_INTEGRATION_LEVELS:
            errors.append(f"{candidate_id}: integration_level darf nur none oder metadata_only sein")

        canonical_url = candidate.get("canonical_url")
        if not isinstance(canonical_url, str):
            errors.append(f"{candidate_id}: canonical_url muss ein String sein")
        else:
            parsed = urlparse(canonical_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append(f"{candidate_id}: canonical_url muss eine HTTP(S)-URL sein")
            if parsed.query:
                errors.append(f"{candidate_id}: canonical_url darf keine Query enthalten")
            if "shem=" in canonical_url:
                errors.append(f"{candidate_id}: canonical_url enthält Trackingparameter")

        source_type = candidate.get("source_type")
        if source_type in LICENSE_REVIEW_SOURCE_TYPES and candidate.get("license_review_required") is not True:
            errors.append(f"{candidate_id}: lizenzrelevante Quelle braucht license_review_required true")
        if source_type in AI_OR_MCP_SOURCE_TYPES and candidate.get("ai_sbom_status") not in {"pending", "not_applicable"}:
            errors.append(f"{candidate_id}: ai_sbom_status muss pending oder not_applicable sein")
        if source_type == "training_dataset_candidate" and "start_finetuning_without_owner_apply" not in candidate.get("blocked_actions", []):
            errors.append(f"{candidate_id}: Trainingsdatensatz muss start_finetuning_without_owner_apply blockieren")
        if source_type == "training_dataset_candidate" and "treat_dataset_as_german_law_source" not in candidate.get("blocked_actions", []):
            errors.append(f"{candidate_id}: Trainingsdatensatz muss treat_dataset_as_german_law_source blockieren")
        if source_type == "official_publication_data_access" and "bulk_crawl_without_terms_review" not in candidate.get("blocked_actions", []):
            errors.append(f"{candidate_id}: amtlicher Datenabruf muss bulk_crawl_without_terms_review blockieren")
        if source_type == "concept_reference" and "treat_concept_reference_as_primary_legal_source" not in candidate.get("blocked_actions", []):
            errors.append(f"{candidate_id}: Begriffshinweis muss treat_concept_reference_as_primary_legal_source blockieren")

        allowed_actions = set(_string_list(candidate.get("allowed_actions")))
        blocked_actions = set(_string_list(candidate.get("blocked_actions")))
        evidence_fields = set(_string_list(candidate.get("evidence_fields")))
        if any(action.startswith(("query_", "scrape_", "apply_", "write_")) for action in allowed_actions):
            errors.append(f"{candidate_id}: allowed_actions darf keine produktive Ausführung enthalten")
        for action in sorted(REQUIRED_BLOCKED_ACTIONS - blocked_actions):
            errors.append(f"{candidate_id}: blocked_actions fehlt: {action}")
        for field in sorted(REQUIRED_EVIDENCE_FIELDS - evidence_fields):
            errors.append(f"{candidate_id}: evidence_fields fehlt: {field}")

    return errors


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
    print("OK: Legal Research Connectors bleiben Kandidaten ohne Credentials, Produktintegration oder Mandatsdaten und erzwingen Lizenz-/AVV-/Review-Gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
