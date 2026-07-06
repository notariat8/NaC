from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "private-operating-frame-gate.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "private-operating-frame-gate.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "private-operating-frame-gate.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCE_DOCUMENTS = {
    "matter_data_boundary",
    "m365_metadata_storage",
    "secure_document_link",
    "onprem_connector_boundary",
    "privacy_dpa_de",
    "privacy_dpa_en",
    "data_sovereignty_de",
    "data_sovereignty_en",
}
REQUIRED_TRUE_REQUIREMENTS = {
    "owner_recorded_decision_required",
    "privacy_dpa_review_required",
    "dsfa_screening_required",
    "role_tenant_matter_purpose_binding_required",
    "field_level_classification_required",
    "private_payload_schema_required",
    "encryption_at_rest_required",
    "encryption_in_transit_required",
    "key_management_required",
    "retention_and_deletion_policy_required",
    "access_review_required",
    "append_only_audit_required",
    "data_subject_rights_process_required",
    "incident_response_required",
    "backup_restore_boundary_required",
    "test_data_separation_required",
    "human_review_before_matter_attachment_required",
}
REQUIRED_SCOPE_FALSE = {
    "productive_processing_enabled_by_this_contract",
    "productive_schema_apply_enabled_by_this_contract",
    "graph_studio_activation_enabled_by_this_contract",
    "connector_live_apply_enabled_by_this_contract",
    "github_or_target_control_private_payload_allowed",
}
REQUIRED_BLOCKED_WITHOUT_GATE = {
    "productive_personal_data_processing",
    "raw_mandate_content_storage",
    "document_full_text_storage",
    "identity_document_raw_data_storage",
    "register_raw_content_storage",
    "land_register_raw_content_storage",
    "xnp_or_xnotar_payload_storage",
    "secure_document_private_payload_link",
    "atp_private_payload_schema_apply",
    "object_storage_document_write",
    "onprem_dms_or_specialist_system_write",
    "graph_projection_over_private_payload",
}
REQUIRED_PRIVATE_CLASSES = {
    "raw_mandate_content",
    "document_full_text",
    "identity_document_raw_data",
    "register_raw_content",
    "land_register_raw_content",
    "property_raw_data",
    "financial_account_real_data",
    "health_family_estate_raw_data",
    "personal_identifiers_with_gate",
    "external_payload_with_gate",
}
REQUIRED_FORBIDDEN_SURFACES = {
    "product_repo",
    "github_issues_prs_actions_artifacts",
    "notoclaw_target_control",
    "public_webapp_demo",
    "source_code_fixtures",
    "quality_gate_artifacts",
}
REQUIRED_STORAGE_TARGETS = {
    "atp_private_payload_schema",
    "encrypted_object_storage_documents",
    "onprem_dms_or_specialist_system",
}
REQUIRED_GATE_SEQUENCE = [
    "architecture_decision",
    "privacy_dpa_review",
    "dsfa_screening",
    "private_payload_schema_design",
    "security_and_key_management_review",
    "retention_and_deletion_review",
    "role_tenant_matter_purpose_binding_review",
    "test_mode_with_synthetic_or_redacted_data",
    "human_subject_matter_review",
    "owner_apply_approval",
]
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "gate_id",
    "decision_status",
    "decided_at",
    "decided_by_role",
    "scope",
    "data_classes",
    "storage_target",
    "tenant_binding",
    "matter_binding",
    "purpose_binding",
    "retention_policy_ref",
    "encryption_policy_ref",
    "access_policy_ref",
    "audit_event_ref",
    "no_github_payload_attestation",
    "no_target_control_payload_attestation",
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
    if payload.get("contract_id") != "workflow.private_operating_frame_gate":
        errors.append("contract_id muss workflow.private_operating_frame_gate sein")
    if payload.get("status") != "contract_only_no_productive_apply":
        errors.append("status muss contract_only_no_productive_apply sein")

    errors.extend(_validate_sources(payload))
    errors.extend(_validate_scope(payload))
    errors.extend(_validate_requirements(payload))
    errors.extend(_validate_lists(payload))
    errors.extend(_validate_storage_targets(payload))
    errors.extend(_validate_docs())
    return errors


def _validate_sources(payload: dict[str, Any]) -> list[str]:
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


def _validate_scope(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        return ["scope muss ein Objekt sein"]
    if scope.get("contract_result") != "approval_boundary_for_future_private_payload_design":
        errors.append("scope.contract_result muss approval_boundary_for_future_private_payload_design sein")
    for key in sorted(REQUIRED_SCOPE_FALSE):
        if scope.get(key) is not False:
            errors.append(f"scope.{key} muss false sein")
    return errors


def _validate_requirements(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    requirements = payload.get("operating_frame_requirements")
    if not isinstance(requirements, dict):
        return ["operating_frame_requirements muss ein Objekt sein"]
    for key in sorted(REQUIRED_TRUE_REQUIREMENTS):
        if requirements.get(key) is not True:
            errors.append(f"operating_frame_requirements.{key} muss true sein")
    return errors


def _validate_lists(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    list_requirements = (
        ("blocked_without_gate", REQUIRED_BLOCKED_WITHOUT_GATE),
        ("private_payload_classes_after_gate", REQUIRED_PRIVATE_CLASSES),
        ("always_forbidden_surfaces", REQUIRED_FORBIDDEN_SURFACES),
        ("required_evidence_fields", REQUIRED_EVIDENCE_FIELDS),
    )
    for key, required_values in list_requirements:
        values = set(_string_list(payload.get(key)))
        for missing in sorted(required_values - values):
            errors.append(f"{key} fehlt: {missing}")
    gate_sequence = _string_list(payload.get("gate_sequence"))
    if gate_sequence != REQUIRED_GATE_SEQUENCE:
        errors.append("gate_sequence muss die verbindliche Reihenfolge abbilden")
    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_private_operating_frame_gate.py",
        "python scripts/validate_matter_data_classification_redaction.py",
        "python scripts/validate_teams_sharepoint_graph_data_plane.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_storage_targets(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = payload.get("candidate_private_storage_targets")
    if not isinstance(targets, list) or not targets:
        return ["candidate_private_storage_targets muss eine nicht leere Liste sein"]
    by_id = {
        str(target.get("id")): target
        for target in targets
        if isinstance(target, dict) and isinstance(target.get("id"), str)
    }
    for target_id in sorted(REQUIRED_STORAGE_TARGETS):
        target = by_id.get(target_id)
        if not isinstance(target, dict):
            errors.append(f"candidate_private_storage_targets fehlt: {target_id}")
            continue
        if target.get("status") != "future_design_only":
            errors.append(f"{target_id}: status muss future_design_only sein")
        controls = set(_string_list(target.get("required_controls")))
        if len(controls) < 5:
            errors.append(f"{target_id}: required_controls braucht konkrete Mindestkontrollen")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Privater Betriebsrahmen und Private-Payload-Gate"),
        (DOC_EN, "Private Operating Frame And Private-Payload Gate"),
        (QUALITY_DE, "private_operating_frame_gate"),
        (QUALITY_EN, "private_operating_frame_gate"),
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
    print("OK: Privater Betriebsrahmen bleibt ein Gate-Vertrag ohne produktiven Apply oder private Payloads in GitHub/notoclaw.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
