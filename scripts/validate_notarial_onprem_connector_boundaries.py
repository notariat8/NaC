from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "notarial-onprem-connector-boundaries.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "notarial-onprem-connector-boundaries.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "notarial-onprem-connector-boundaries.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"
LEGACY_ARCHIVE = REPO_ROOT / "archive" / "legacy-oci-atp" / "README.md"

REQUIRED_CONNECTOR_IDS = {
    "xnp_snp_xnotar",
    "cyberjack_card_workstation",
    "register_land_register",
}
REQUIRED_STUB_PATHS = {
    "connectors/xnp/README.md",
    "connectors/cyberjack/README.md",
    "connectors/register/README.md",
}
REQUIRED_FALSE_POLICY = {
    "credentials_in_repo_allowed",
    "secrets_in_target_control_allowed",
    "matter_data_in_repo_allowed",
    "matter_data_in_target_control_allowed",
    "pin_capture_allowed",
    "card_raw_data_storage_allowed",
    "certificate_secret_storage_allowed",
    "productive_write_without_owner_gate_allowed",
    "automated_xnp_to_nac_data_intake_allowed",
    "remote_control_of_specialist_system_allowed",
}
REQUIRED_TRUE_POLICY = {
    "redacted_evidence_only",
    "human_review_required",
    "private_operating_frame_required_before_live",
    "privacy_review_required_before_personal_data",
    "test_mode_required_before_live",
}
REQUIRED_EVIDENCE_FIELDS = {
    "connector_id",
    "readiness_status",
    "checked_at",
    "checked_by_role",
    "source_system_label",
    "redaction_class",
    "no_secret_attestation",
    "no_matter_data_attestation",
    "human_review_status",
    "audit_event_ref",
}
REQUIRED_OWNER_GATES = {
    "credential_introduction",
    "personal_data_processing",
    "productive_xnp_or_xnotar_action",
    "productive_register_or_land_register_action",
    "signature_or_card_operation",
    "specialist_system_write",
    "external_network_write",
    "destructive_action",
}
REQUIRED_BLOCKED_ACTIONS = {
    "store_credentials",
    "store_secret_material",
    "store_matter_data",
    "remote_control_specialist_system",
}
REQUIRED_ALLOWED_EVIDENCE_ACTIONS = {
    "record_redacted_status_evidence",
    "model_bpmn_gate",
}
REQUIRED_ROLES = {
    "notariatsfachkraft",
    "notarin_notar",
    "it_betrieb",
    "owner",
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
    "secret_value",
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
        return [f"{path.relative_to(REPO_ROOT)} ist kein gültiges JSON: {exc}"]
    if not isinstance(payload, dict):
        return [f"{path.relative_to(REPO_ROOT)} muss ein JSON-Objekt sein"]

    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != "workflow.notarial_onprem_connector_boundaries":
        errors.append("contract_id muss workflow.notarial_onprem_connector_boundaries sein")
    if payload.get("status") != "archived_legacy_no_live_apply":
        errors.append("status muss archived_legacy_no_live_apply sein")

    errors.extend(_validate_source_documents(payload))
    errors.extend(_validate_runtime_profile(payload))
    errors.extend(_validate_global_policy(payload))
    errors.extend(_validate_connector_entries(payload))
    errors.extend(_validate_docs())
    return errors


def _validate_source_documents(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        return ["source_documents muss ein Objekt sein"]
    for key in (
        "demo_matrix_de",
        "demo_matrix_en",
        "runtime_boundary_de",
        "runtime_boundary_en",
        "minimum_requirements_de",
        "minimum_requirements_en",
    ):
        value = source_documents.get(key)
        if not isinstance(value, str):
            errors.append(f"source_documents.{key} fehlt")
            continue
        path = REPO_ROOT / value
        if not path.is_file():
            errors.append(f"source_documents.{key} zeigt auf fehlende Datei: {value}")
            continue
        text = path.read_text(encoding="utf-8")
        _reject_prohibited_text(path, text, errors)
    matrix_de = (REPO_ROOT / "docs" / "de" / "demo" / "notarkammer-xnp-quellenmatrix.md").read_text(encoding="utf-8")
    matrix_en = (REPO_ROOT / "docs" / "en" / "demo" / "notarkammer-xnp-quellenmatrix.md").read_text(encoding="utf-8")
    if "NaC darf nicht behaupten" not in matrix_de:
        errors.append("deutsche XNP-Quellenmatrix muss Nicht-Behauptungsgrenze enthalten")
    if "NaC must not claim" not in matrix_en:
        errors.append("englische XNP-Quellenmatrix muss Nicht-Behauptungsgrenze enthalten")
    return errors


def _validate_runtime_profile(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    runtime_profile = payload.get("runtime_profile")
    if not isinstance(runtime_profile, dict):
        return ["runtime_profile muss ein Objekt sein"]
    if runtime_profile.get("required_profile_before_local_hardware_tests") != "notary-workstation":
        errors.append("runtime_profile.required_profile_before_local_hardware_tests muss notary-workstation sein")
    if runtime_profile.get("target_control_path") != "/home/ubuntu/nac-target-control":
        errors.append("runtime_profile.target_control_path muss /home/ubuntu/nac-target-control sein")
    paths = set(_string_list(runtime_profile.get("target_connector_stub_paths")))
    for missing in sorted(REQUIRED_STUB_PATHS - paths):
        errors.append(f"runtime_profile.target_connector_stub_paths fehlt: {missing}")
    return errors


def _validate_global_policy(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    policy = payload.get("global_policy")
    if not isinstance(policy, dict):
        return ["global_policy muss ein Objekt sein"]
    for key in sorted(REQUIRED_FALSE_POLICY):
        if policy.get(key) is not False:
            errors.append(f"global_policy.{key} muss false sein")
    for key in sorted(REQUIRED_TRUE_POLICY):
        if policy.get(key) is not True:
            errors.append(f"global_policy.{key} muss true sein")

    evidence_fields = set(_string_list(payload.get("required_evidence_fields")))
    for missing in sorted(REQUIRED_EVIDENCE_FIELDS - evidence_fields):
        errors.append(f"required_evidence_fields fehlt: {missing}")

    owner_gates = set(_string_list(payload.get("owner_gates")))
    for missing in sorted(REQUIRED_OWNER_GATES - owner_gates):
        errors.append(f"owner_gates fehlt: {missing}")

    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_notarial_onprem_connector_boundaries.py",
        "python scripts/validate_nac_onprem_agent_runtime.py",
        "python scripts/validate_language_parity.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands fehlt: {command}")
    return errors


def _validate_connector_entries(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    connectors = payload.get("connectors")
    if not isinstance(connectors, list) or not connectors:
        return ["connectors muss eine nicht leere Liste sein"]

    by_id: dict[str, dict[str, Any]] = {}
    for index, connector in enumerate(connectors, start=1):
        if not isinstance(connector, dict):
            errors.append(f"connectors[{index}] muss ein Objekt sein")
            continue
        connector_id = connector.get("id")
        if not isinstance(connector_id, str) or not connector_id:
            errors.append(f"connectors[{index}].id muss gesetzt sein")
            continue
        if connector_id in by_id:
            errors.append(f"Connector-ID doppelt: {connector_id}")
        by_id[connector_id] = connector

    for connector_id in sorted(REQUIRED_CONNECTOR_IDS):
        connector = by_id.get(connector_id)
        if connector is None:
            errors.append(f"connectors fehlt: {connector_id}")
            continue
        errors.extend(_validate_connector(connector_id, connector))
    return errors


def _validate_connector(connector_id: str, connector: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if connector.get("status") != "boundary_contract_no_live_apply":
        errors.append(f"{connector_id}: status muss boundary_contract_no_live_apply sein")
    if connector.get("target_stub_path") not in REQUIRED_STUB_PATHS:
        errors.append(f"{connector_id}: target_stub_path muss ein erwarteter Target-Control-Stub sein")

    allowed_actions = set(_string_list(connector.get("allowed_actions")))
    blocked_actions = set(_string_list(connector.get("blocked_actions")))
    allowed_data = set(_string_list(connector.get("data_classes_allowed_before_live_gate")))
    blocked_data = set(_string_list(connector.get("data_classes_blocked")))
    roles = set(_string_list(connector.get("required_roles")))

    for missing in sorted(REQUIRED_ALLOWED_EVIDENCE_ACTIONS - allowed_actions):
        errors.append(f"{connector_id}: allowed_actions fehlt: {missing}")
    for blocked_prefix in ("productive_", "store_", "capture_", "trigger_", "read_", "export_"):
        if any(action.startswith(blocked_prefix) for action in allowed_actions):
            errors.append(f"{connector_id}: allowed_actions enthält produktive oder sensitive Aktion mit Präfix {blocked_prefix}")
    for missing in sorted(REQUIRED_BLOCKED_ACTIONS - blocked_actions):
        errors.append(f"{connector_id}: blocked_actions fehlt: {missing}")
    if "safe_metadata_only" not in allowed_data:
        errors.append(f"{connector_id}: data_classes_allowed_before_live_gate braucht safe_metadata_only")
    for required_blocked in ("raw_mandate_content", "credentials", "tokens"):
        if required_blocked not in blocked_data:
            errors.append(f"{connector_id}: data_classes_blocked fehlt: {required_blocked}")
    for missing in sorted(REQUIRED_ROLES - roles):
        errors.append(f"{connector_id}: required_roles fehlt: {missing}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required_markers = (
        (DOC_DE, "Notarielle On-Prem-Connector-Grenzen"),
        (DOC_EN, "Notarial On-Prem Connector Boundaries"),
        (LEGACY_ARCHIVE, "workflows/contracts/notarial-onprem-connector-boundaries.contract.json"),
    )
    for path, marker in required_markers:
        if not path.is_file():
            errors.append(f"Pflichtdokument fehlt: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        _reject_prohibited_text(path, text, errors)
        if marker not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} enthält Marker nicht: {marker}")
    return errors


def _reject_prohibited_text(path: Path, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{path.relative_to(REPO_ROOT)} enthält unzulässigen Marker: {marker}")


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
    print("OK: Notarielle On-Prem-Connector-Grenzen bleiben redigierte Evidence-/Readiness-Verträge ohne Credentials, Mandatsdaten oder Live-Apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
