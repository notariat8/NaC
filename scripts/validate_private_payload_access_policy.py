from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "private-payload-access-policy.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "private-payload-access-policy.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "private-payload-access-policy.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_SOURCES = {
    "role_model_policy",
    "access_control_policy",
    "private_payload_target_design",
    "private_operating_frame_gate",
    "matter_data_boundary",
}
REQUIRED_SCOPE_FALSE = {
    "live_access_enabled",
    "productive_personal_data_processing_enabled",
    "private_payload_examples_in_repo_allowed",
    "target_control_private_payload_allowed",
    "automation_may_approve_access",
    "guest_may_access_private_payload_by_default",
}
REQUIRED_SCOPE_TRUE = {"owner_apply_required_before_enforcement"}
REQUIRED_ROLES = {
    "notar_fachlich",
    "notariatsfachkraft",
    "kostenverantwortung",
    "revision_audit",
    "owner",
    "automation",
    "client_guest_user",
}
REQUIRED_PURPOSES = {
    "notarial_review",
    "casework_preparation",
    "cost_review",
    "matter_attachment",
    "external_participant_upload",
    "redacted_audit",
    "owner_apply",
    "incident_response",
}
REQUIRED_MATRIX_IDS = {
    "notary_read_for_review",
    "clerk_prepare_casework",
    "cost_review_limited",
    "audit_redacted_only",
    "owner_apply_gate",
    "automation_policy_metadata_only",
    "guest_upload_link_limited",
}
PRIVATE_DATA_CLASSES = {
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
REQUIRED_DENIALS = {
    "no_public_or_target_control_access",
    "no_automation_approval",
    "no_guest_default_read",
}
REQUIRED_EVIDENCE_FIELDS = {
    "schema_version",
    "grant_id",
    "payload_id",
    "tenant_id",
    "matter_id",
    "role_class",
    "purpose",
    "data_classes",
    "decision_status",
    "decision_reason",
    "expires_at",
    "revocation_status",
    "step_up_status",
    "human_review_ref",
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
    if payload.get("contract_id") != "workflow.private_payload_access_policy":
        errors.append("contract_id muss workflow.private_payload_access_policy sein")
    if payload.get("status") != "policy_contract_no_live_access":
        errors.append("status muss policy_contract_no_live_access sein")

    errors.extend(_validate_sources(payload))
    errors.extend(_validate_scope(payload))
    errors.extend(_validate_roles(payload))
    errors.extend(_validate_matrix(payload))
    errors.extend(_validate_denials_and_evidence(payload))
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
    for key in sorted(REQUIRED_SCOPE_FALSE):
        if scope.get(key) is not False:
            errors.append(f"scope.{key} muss false sein")
    for key in sorted(REQUIRED_SCOPE_TRUE):
        if scope.get(key) is not True:
            errors.append(f"scope.{key} muss true sein")
    return errors


def _validate_roles(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    roles = payload.get("role_classes")
    if not isinstance(roles, list) or not roles:
        return ["role_classes muss eine nicht leere Liste sein"]
    by_id = {
        str(role.get("id")): role
        for role in roles
        if isinstance(role, dict) and isinstance(role.get("id"), str)
    }
    for missing in sorted(REQUIRED_ROLES - set(by_id)):
        errors.append(f"role_classes fehlt: {missing}")
    for role_id, role in by_id.items():
        actions = set(_string_list(role.get("allowed_request_actions")))
        if not actions:
            errors.append(f"{role_id}: allowed_request_actions muss gesetzt sein")
        if not isinstance(role.get("approval_level"), str) or not role["approval_level"]:
            errors.append(f"{role_id}: approval_level muss gesetzt sein")
        if role_id == "automation" and any("approve" in action or "read_private_payload" in action for action in actions):
            errors.append("automation darf keine privaten Payloads lesen oder freigeben")
        if role_id == "client_guest_user" and any("read_private_payload" in action for action in actions):
            errors.append("client_guest_user darf keinen Default-Private-Payload-Read erhalten")

    purposes = set(_string_list(payload.get("purpose_classes")))
    for missing in sorted(REQUIRED_PURPOSES - purposes):
        errors.append(f"purpose_classes fehlt: {missing}")
    return errors


def _validate_matrix(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    matrix = payload.get("access_matrix")
    if not isinstance(matrix, list) or not matrix:
        return ["access_matrix muss eine nicht leere Liste sein"]
    by_id = {
        str(entry.get("id")): entry
        for entry in matrix
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }
    for missing in sorted(REQUIRED_MATRIX_IDS - set(by_id)):
        errors.append(f"access_matrix fehlt: {missing}")
    for entry_id, entry in by_id.items():
        role = entry.get("role_class")
        if role not in REQUIRED_ROLES:
            errors.append(f"{entry_id}: role_class ist unbekannt")
        if entry.get("purpose") not in REQUIRED_PURPOSES:
            errors.append(f"{entry_id}: purpose ist unbekannt")
        actions = set(_string_list(entry.get("allowed_actions")))
        data_classes = set(_string_list(entry.get("allowed_data_classes")))
        gates = set(_string_list(entry.get("required_gates")))
        if not actions:
            errors.append(f"{entry_id}: allowed_actions muss gesetzt sein")
        if not data_classes:
            errors.append(f"{entry_id}: allowed_data_classes muss gesetzt sein")
        if "append_only_audit" not in gates:
            errors.append(f"{entry_id}: required_gates braucht append_only_audit")
        if data_classes & PRIVATE_DATA_CLASSES and "private_operating_frame_gate" not in gates:
            errors.append(f"{entry_id}: private Datenklassen brauchen private_operating_frame_gate")
        if role == "automation" and data_classes & PRIVATE_DATA_CLASSES:
            errors.append("automation darf keine privaten Datenklassen erhalten")
        if role == "client_guest_user" and data_classes & PRIVATE_DATA_CLASSES:
            errors.append("client_guest_user darf keine privaten Datenklassen direkt erhalten")
    return errors


def _validate_denials_and_evidence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    denials = payload.get("global_denials")
    if not isinstance(denials, list) or not denials:
        errors.append("global_denials muss eine nicht leere Liste sein")
    else:
        denial_ids = {str(item.get("id")) for item in denials if isinstance(item, dict)}
        for missing in sorted(REQUIRED_DENIALS - denial_ids):
            errors.append(f"global_denials fehlt: {missing}")
        combined = json.dumps(denials, ensure_ascii=False)
        for marker in ("github_issues_prs_actions_artifacts", "notoclaw_target_control", "automation", "client_guest_user"):
            if marker not in combined:
                errors.append(f"global_denials muss {marker} sperren")

    evidence = set(_string_list(payload.get("required_access_evidence_fields")))
    for missing in sorted(REQUIRED_EVIDENCE_FIELDS - evidence):
        errors.append(f"required_access_evidence_fields fehlt: {missing}")

    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_private_payload_access_policy.py",
        "python scripts/validate_private_payload_target_design.py",
        "python scripts/validate_private_operating_frame_gate.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Private-Payload-Zugriffsmatrix"),
        (DOC_EN, "Private-Payload Access Policy"),
        (QUALITY_DE, "private_payload_access_policy"),
        (QUALITY_EN, "private_payload_access_policy"),
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
    print("OK: Private-Payload-Zugriffsmatrix bleibt Policy-Vertrag ohne Live-Zugriff und ohne Payloads im Repo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
