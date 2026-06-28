from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "matter-data-classification-redaction.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "matter-data-classification-redaction.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "matter-data-classification-redaction.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCE_DOCUMENTS = {
    "data_protection_policy",
    "matter_model_de",
    "matter_model_en",
    "atp_storage_contract",
    "secure_document_link_contract",
    "onprem_runtime_contract",
    "onprem_connector_contract",
}
REQUIRED_ALLOWED_CLASSES = {
    "safe_metadata_only",
    "synthetic_demo_data",
    "policy_reference",
    "validation_evidence_without_secret_values",
    "redacted_evidence_metadata",
    "approved_public_source_reference",
    "hash_or_pointer_without_private_payload",
}
REQUIRED_BLOCKED_CLASSES = {
    "raw_mandate_content",
    "document_full_text",
    "identity_document_raw_data",
    "register_raw_content",
    "land_register_raw_content",
    "property_raw_data",
    "financial_account_real_data",
    "health_family_estate_raw_data",
    "personal_identifiers_without_separate_gate",
    "external_payload_without_separate_gate",
    "tokens",
    "credentials",
    "pin",
    "card_raw_data",
    "provider_claim_dump",
}
REQUIRED_SURFACES = {
    "product_repo",
    "github_surfaces",
    "notoclaw_target_control",
    "public_webapp_demo",
    "authenticated_workspace_start",
    "atp_metadata_slice",
    "secure_document_link_evidence",
    "private_operating_frame_after_gate",
}
SURFACES_BLOCKING_ALL_MATTER_CLASSES = REQUIRED_SURFACES - {"private_operating_frame_after_gate"}
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "payload_type",
    "redaction_class",
    "purpose",
    "tenant_binding",
    "matter_binding_status",
    "role_class",
    "checked_at",
    "checked_by_role",
    "source_system_label",
    "hash_or_reference",
    "no_secret_attestation",
    "no_matter_data_attestation",
    "audit_event_ref",
}
REQUIRED_OWNER_GATES = {
    "private_operating_frame",
    "privacy_dpa_review",
    "retention_policy",
    "encryption_policy",
    "role_tenant_matter_purpose_binding",
    "productive_personal_data_processing",
    "connector_private_payload",
    "atp_private_payload_schema",
    "secure_document_private_payload",
}
REQUIRED_FALSE_POLICY = {
    "raw_matter_data_in_product_repo_allowed",
    "raw_matter_data_in_github_surfaces_allowed",
    "raw_matter_data_in_target_control_allowed",
    "raw_matter_data_in_public_webapp_allowed",
    "raw_matter_data_in_atp_metadata_slice_allowed",
    "secrets_in_product_repo_allowed",
    "secrets_in_target_control_allowed",
    "provider_claim_dumps_allowed",
}
REQUIRED_TRUE_POLICY = {
    "metadata_only_until_private_operating_frame",
    "purpose_binding_required",
    "tenant_binding_required",
    "matter_binding_required_before_private_payload",
    "human_review_required_before_personal_data",
    "retention_policy_required_before_personal_data",
    "encryption_policy_required_before_personal_data",
    "owner_gate_required_before_productive_personal_data",
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
    if payload.get("contract_id") != "workflow.matter_data_classification_redaction":
        errors.append("contract_id muss workflow.matter_data_classification_redaction sein")
    if payload.get("status") != "boundary_contract_metadata_only_until_private_gate":
        errors.append("status muss boundary_contract_metadata_only_until_private_gate sein")

    errors.extend(_validate_source_documents(payload))
    errors.extend(_validate_policy(payload))
    errors.extend(_validate_data_classes(payload))
    errors.extend(_validate_surfaces(payload))
    errors.extend(_validate_evidence_and_gates(payload))
    errors.extend(_validate_docs())
    return errors


def _validate_source_documents(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        return ["source_documents muss ein Objekt sein"]
    for key in sorted(REQUIRED_SOURCE_DOCUMENTS):
        value = source_documents.get(key)
        if not isinstance(value, str):
            errors.append(f"source_documents.{key} fehlt")
            continue
        path = REPO_ROOT / value
        if not path.is_file():
            errors.append(f"source_documents.{key} zeigt auf fehlende Datei: {value}")
    return errors


def _validate_policy(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = payload.get("classification_policy")
    if not isinstance(policy, dict):
        return ["classification_policy muss ein Objekt sein"]
    for key in sorted(REQUIRED_FALSE_POLICY):
        if policy.get(key) is not False:
            errors.append(f"classification_policy.{key} muss false sein")
    for key in sorted(REQUIRED_TRUE_POLICY):
        if policy.get(key) is not True:
            errors.append(f"classification_policy.{key} muss true sein")
    return errors


def _validate_data_classes(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    data_classes = payload.get("data_classes")
    if not isinstance(data_classes, list) or not data_classes:
        return ["data_classes muss eine nicht leere Liste sein"]
    by_id: dict[str, dict[str, Any]] = {}
    for index, data_class in enumerate(data_classes, start=1):
        if not isinstance(data_class, dict):
            errors.append(f"data_classes[{index}] muss ein Objekt sein")
            continue
        class_id = data_class.get("id")
        if not isinstance(class_id, str) or not class_id:
            errors.append(f"data_classes[{index}].id muss gesetzt sein")
            continue
        if class_id in by_id:
            errors.append(f"Datenklasse doppelt: {class_id}")
        by_id[class_id] = data_class
        if not isinstance(data_class.get("category"), str) or not data_class["category"]:
            errors.append(f"{class_id}: category muss gesetzt sein")
        if not isinstance(data_class.get("description"), str) or not data_class["description"]:
            errors.append(f"{class_id}: description muss gesetzt sein")

    for missing in sorted(REQUIRED_ALLOWED_CLASSES - set(by_id)):
        errors.append(f"data_classes fehlt erlaubte Klasse: {missing}")
    for missing in sorted(REQUIRED_BLOCKED_CLASSES - set(by_id)):
        errors.append(f"data_classes fehlt gesperrte Klasse: {missing}")

    for class_id in sorted(REQUIRED_ALLOWED_CLASSES):
        category = by_id.get(class_id, {}).get("category")
        if category != "allowed_before_private_gate":
            errors.append(f"{class_id}: category muss allowed_before_private_gate sein")
    for class_id in sorted(REQUIRED_BLOCKED_CLASSES):
        category = by_id.get(class_id, {}).get("category")
        if category not in {
            "blocked_until_private_gate",
            "always_blocked_from_repo_and_target_control",
        }:
            errors.append(f"{class_id}: category muss eine gesperrte Kategorie sein")
    return errors


def _validate_surfaces(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        return ["surfaces muss eine nicht leere Liste sein"]
    by_id: dict[str, dict[str, Any]] = {}
    for index, surface in enumerate(surfaces, start=1):
        if not isinstance(surface, dict):
            errors.append(f"surfaces[{index}] muss ein Objekt sein")
            continue
        surface_id = surface.get("id")
        if not isinstance(surface_id, str) or not surface_id:
            errors.append(f"surfaces[{index}].id muss gesetzt sein")
            continue
        if surface_id in by_id:
            errors.append(f"Surface-ID doppelt: {surface_id}")
        by_id[surface_id] = surface

    for missing in sorted(REQUIRED_SURFACES - set(by_id)):
        errors.append(f"surfaces fehlt: {missing}")

    for surface_id, surface in by_id.items():
        allowed = set(_string_list(surface.get("allowed_data_classes")))
        blocked = set(_string_list(surface.get("blocked_data_classes")))
        gate = surface.get("required_gate_before_private_payload")
        if not isinstance(gate, str) or not gate:
            errors.append(f"{surface_id}: required_gate_before_private_payload muss gesetzt sein")
        if "safe_metadata_only" not in allowed:
            errors.append(f"{surface_id}: allowed_data_classes braucht safe_metadata_only")
        for secret_class in ("tokens", "credentials", "pin", "card_raw_data", "provider_claim_dump"):
            if secret_class not in blocked:
                errors.append(f"{surface_id}: blocked_data_classes fehlt: {secret_class}")
        if surface_id in SURFACES_BLOCKING_ALL_MATTER_CLASSES:
            for class_id in sorted(REQUIRED_BLOCKED_CLASSES):
                if class_id not in blocked:
                    errors.append(f"{surface_id}: blocked_data_classes fehlt: {class_id}")
        if allowed & REQUIRED_BLOCKED_CLASSES:
            errors.append(f"{surface_id}: allowed_data_classes enthaelt gesperrte Datenklasse")
    return errors


def _validate_evidence_and_gates(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence_fields = set(_string_list(payload.get("required_redaction_evidence_fields")))
    for missing in sorted(REQUIRED_EVIDENCE_FIELDS - evidence_fields):
        errors.append(f"required_redaction_evidence_fields fehlt: {missing}")

    owner_gates = set(_string_list(payload.get("owner_gates")))
    for missing in sorted(REQUIRED_OWNER_GATES - owner_gates):
        errors.append(f"owner_gates fehlt: {missing}")

    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_matter_data_classification_redaction.py",
        "python scripts/validate_notarial_onprem_connector_boundaries.py",
        "python scripts/validate_nac_onprem_agent_runtime.py",
        "python scripts/validate_atp_runtime_contracts.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Mandatsdaten-Klassifikation und Redaktion"),
        (DOC_EN, "Matter Data Classification And Redaction"),
        (QUALITY_DE, "matter_data_classification_redaction"),
        (QUALITY_EN, "matter_data_classification_redaction"),
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
    print(
        "OK: Mandatsdaten-Klassifikation bleibt metadata-only bis privater "
        "Betriebs-, Datenschutz-, Sicherheits- und Owner-Gate gesetzt ist."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
