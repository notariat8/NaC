from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "private-payload-target-design.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "private-payload-target-design.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "private-payload-target-design.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCES = {
    "private_operating_frame_gate",
    "matter_data_boundary",
    "m365_metadata_storage",
    "secure_document_link",
    "data_sovereignty_de",
    "data_sovereignty_en",
}
REQUIRED_SCOPE_FALSE = {
    "physical_schema_artifact_included",
    "productive_schema_apply_enabled",
    "private_payload_examples_in_repo_allowed",
    "github_or_target_control_payload_allowed",
    "plaintext_payload_storage_allowed",
    "graph_projection_over_plaintext_allowed",
}
REQUIRED_SCOPE_TRUE = {"requires_private_operating_frame_gate"}
REQUIRED_COMPONENTS = {
    "private_payload_envelope",
    "private_payload_access_grant",
    "encrypted_document_object_pointer",
    "redacted_private_payload_audit",
}
REQUIRED_COMPONENT_FIELDS = {
    "private_payload_envelope": {
        "payload_id",
        "tenant_id",
        "matter_id",
        "purpose",
        "data_class",
        "redaction_class",
        "storage_target",
        "payload_pointer",
        "content_hash",
        "encryption_key_ref",
        "retention_policy_ref",
        "access_policy_ref",
        "audit_event_ref",
        "created_by_role",
        "created_at",
        "legal_hold_status",
    },
    "private_payload_access_grant": {
        "grant_id",
        "payload_id",
        "tenant_id",
        "matter_id",
        "role_class",
        "purpose",
        "expires_at",
        "revocation_status",
        "step_up_required",
        "human_review_ref",
        "audit_event_ref",
    },
    "encrypted_document_object_pointer": {
        "document_ref",
        "payload_id",
        "storage_target",
        "object_pointer",
        "content_hash",
        "mime_class",
        "malware_scan_ref",
        "retention_policy_ref",
        "audit_event_ref",
    },
    "redacted_private_payload_audit": {
        "audit_event_ref",
        "payload_id",
        "event_type",
        "decision_status",
        "actor_role_class",
        "purpose",
        "created_at",
        "no_github_payload_attestation",
        "no_target_control_payload_attestation",
    },
}
REQUIRED_TARGETS = {
    "sharepoint_private_payload_metadata",
    "encrypted_object_storage_payload",
    "onprem_private_store_reference",
}
REQUIRED_CONTROLS = {
    "owner_apply_approval",
    "privacy_dpa_review",
    "dsfa_screening",
    "tenant_matter_purpose_binding",
    "role_field_access_policy",
    "encryption_at_rest",
    "encryption_in_transit",
    "key_management",
    "retention_and_deletion_policy",
    "legal_hold_handling",
    "access_review",
    "append_only_audit",
    "backup_restore_boundary",
    "incident_response",
    "human_review_before_matter_attachment",
}
REQUIRED_BLOCKED = {
    "create_private_payload_tables",
    "write_private_payload",
    "read_private_payload",
    "issue_private_document_link",
    "project_private_payload_into_graph",
    "connect_live_dms_or_specialist_system",
    "run_migration_with_real_matter_data",
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
    "raw payload example",
    "plaintext_payload_example",
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
    if payload.get("contract_id") != "workflow.private_payload_target_design":
        errors.append("contract_id muss workflow.private_payload_target_design sein")
    if payload.get("status") != "logical_design_only_no_apply":
        errors.append("status muss logical_design_only_no_apply sein")

    errors.extend(_validate_sources(payload))
    errors.extend(_validate_scope(payload))
    errors.extend(_validate_components(payload))
    errors.extend(_validate_targets(payload))
    errors.extend(_validate_lists(payload))
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
        path = REPO_ROOT / value
        if not path.is_file():
            errors.append(f"source_documents.{key} zeigt auf fehlende Datei: {value}")
    return errors


def _validate_scope(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        return ["scope muss ein Objekt sein"]
    if scope.get("design_result") != "logical_target_architecture_for_future_private_payloads":
        errors.append("scope.design_result muss logical_target_architecture_for_future_private_payloads sein")
    for key in sorted(REQUIRED_SCOPE_FALSE):
        if scope.get(key) is not False:
            errors.append(f"scope.{key} muss false sein")
    for key in sorted(REQUIRED_SCOPE_TRUE):
        if scope.get(key) is not True:
            errors.append(f"scope.{key} muss true sein")
    return errors


def _validate_components(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    components = payload.get("logical_components")
    if not isinstance(components, list) or not components:
        return ["logical_components muss eine nicht leere Liste sein"]
    by_id = {
        str(component.get("id")): component
        for component in components
        if isinstance(component, dict) and isinstance(component.get("id"), str)
    }
    for component_id in sorted(REQUIRED_COMPONENTS):
        component = by_id.get(component_id)
        if not isinstance(component, dict):
            errors.append(f"logical_components fehlt: {component_id}")
            continue
        if component.get("payload_content_stored_here") is not False:
            errors.append(f"{component_id}: payload_content_stored_here muss false sein")
        if not isinstance(component.get("storage_role"), str) or not component["storage_role"]:
            errors.append(f"{component_id}: storage_role muss gesetzt sein")
        fields = set(_string_list(component.get("required_fields")))
        for missing in sorted(REQUIRED_COMPONENT_FIELDS[component_id] - fields):
            errors.append(f"{component_id}.required_fields fehlt: {missing}")
    return errors


def _validate_targets(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = payload.get("candidate_storage_targets")
    if not isinstance(targets, list) or not targets:
        return ["candidate_storage_targets muss eine nicht leere Liste sein"]
    by_id = {
        str(target.get("id")): target
        for target in targets
        if isinstance(target, dict) and isinstance(target.get("id"), str)
    }
    for target_id in sorted(REQUIRED_TARGETS):
        target = by_id.get(target_id)
        if not isinstance(target, dict):
            errors.append(f"candidate_storage_targets fehlt: {target_id}")
            continue
        if not str(target.get("status", "")).endswith("_design_only"):
            errors.append(f"{target_id}: status muss *_design_only sein")
        blocked = set(_string_list(target.get("blocked_content")))
        for forbidden in ("tokens", "credentials"):
            if forbidden not in blocked and target_id != "onprem_private_store_reference":
                errors.append(f"{target_id}.blocked_content fehlt: {forbidden}")
        allowed = set(_string_list(target.get("allowed_content")))
        if not allowed:
            errors.append(f"{target_id}.allowed_content muss gesetzt sein")
    return errors


def _validate_lists(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    controls = set(_string_list(payload.get("required_controls")))
    for missing in sorted(REQUIRED_CONTROLS - controls):
        errors.append(f"required_controls fehlt: {missing}")
    blocked = set(_string_list(payload.get("blocked_until_future_apply")))
    for missing in sorted(REQUIRED_BLOCKED - blocked):
        errors.append(f"blocked_until_future_apply fehlt: {missing}")
    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_private_payload_target_design.py",
        "python scripts/validate_private_operating_frame_gate.py",
        "python scripts/validate_matter_data_classification_redaction.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Private-Payload-Zielarchitektur"),
        (DOC_EN, "Private-Payload Target Design"),
        (QUALITY_DE, "private_payload_target_design"),
        (QUALITY_EN, "private_payload_target_design"),
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
    print("OK: Private-Payload-Zielarchitektur bleibt Envelope-/Pointer-Design ohne Apply und ohne Payloads im Repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
