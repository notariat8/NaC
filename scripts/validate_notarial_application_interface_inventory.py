from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "notarial-application-interface-inventory.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "notarial-application-interface-inventory.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "notarial-application-interface-inventory.md"

REQUIRED_INTERFACE_IDS = {
    "mandantenportal",
    "uvz",
    "vvz",
    "xnotar_handelsregister",
    "xnotar_grundbuch",
    "xnotar_sonstige_antraege",
    "enova",
    "zvr",
    "ben",
    "xjustiz_331",
}
REQUIRED_SOURCE_KEYS = {
    "architecture_de",
    "architecture_en",
    "bnotk_application_interfaces",
    "bnotk_ben",
    "xjustiz_331_xsd",
}
REQUIRED_OWNER_GATES = {
    "bnotk_credential_use",
    "client_certificate_introduction",
    "identity_token_handling",
    "external_bnotk_network_call",
    "message_payload_processing",
    "xsd_raw_copy_or_distribution",
    "matter_payload_mapping",
    "productive_uvz_or_vvz_write",
    "productive_zvr_call",
    "productive_ben_send_or_fetch",
    "productive_xnotar_handoff",
}
REQUIRED_FALSE_POLICY = {
    "source_fulltext_ingestion_allowed",
    "external_assets_in_repo_allowed",
    "raw_xsd_copy_in_repo_allowed_without_license_gate",
    "credentials_in_repo_allowed",
    "client_certificates_in_repo_allowed",
    "tokens_in_repo_allowed",
    "matter_data_in_repo_allowed",
    "message_payloads_in_repo_allowed",
    "live_connector_apply_allowed",
    "productive_specialist_system_write_allowed",
    "m365_mvp_data_plane_changed",
}
REQUIRED_TRUE_POLICY = {
    "read_only_mcp_contract_required_before_runtime",
    "private_operating_frame_required_before_live",
    "privacy_review_required_before_personal_data",
    "owner_apply_gate_required_before_live",
}
PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "client_secret",
    "password=",
    "PIN:",
    "IdentityToken=",
    "fe_typo_user",
    "<html",
    "<xsd:schema",
    "<xs:schema",
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
    if payload.get("contract_id") != "workflow.notarial_application_interface_inventory":
        errors.append("contract_id muss workflow.notarial_application_interface_inventory sein")
    if payload.get("status") != "offline_inventory_no_live_apply":
        errors.append("status muss offline_inventory_no_live_apply sein")

    errors.extend(_validate_source_documents(payload))
    errors.extend(_validate_global_policy(payload))
    errors.extend(_validate_interfaces(payload))
    errors.extend(_validate_mcp_tools(payload))
    errors.extend(_validate_owner_gates(payload))
    errors.extend(_validate_evidence_shape(payload))
    errors.extend(_validate_docs())
    return errors


def _validate_source_documents(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source_documents = payload.get("source_documents")
    if not isinstance(source_documents, dict):
        return ["source_documents muss ein Objekt sein"]
    missing = REQUIRED_SOURCE_KEYS - set(source_documents)
    for key in sorted(missing):
        errors.append(f"source_documents.{key} fehlt")

    for key in ("architecture_de", "architecture_en"):
        value = source_documents.get(key)
        if not isinstance(value, str):
            errors.append(f"source_documents.{key} muss ein Pfad sein")
            continue
        path = REPO_ROOT / value
        if not path.is_file():
            errors.append(f"source_documents.{key} zeigt auf fehlende Datei: {value}")
            continue
        _reject_prohibited_text(path, path.read_text(encoding="utf-8"), errors)

    xjustiz = source_documents.get("xjustiz_331_xsd")
    if not isinstance(xjustiz, dict):
        errors.append("source_documents.xjustiz_331_xsd muss ein Objekt sein")
    else:
        if xjustiz.get("package_version") != "3.3.1":
            errors.append("xjustiz_331_xsd.package_version muss 3.3.1 sein")
        if xjustiz.get("xsd_file_count") != 66:
            errors.append("xjustiz_331_xsd.xsd_file_count muss 66 sein")
        if xjustiz.get("repository_storage") != "metadata_only":
            errors.append("xjustiz_331_xsd.repository_storage muss metadata_only sein")
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
    return errors


def _validate_interfaces(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    interfaces = payload.get("interfaces")
    if not isinstance(interfaces, list):
        return ["interfaces muss eine Liste sein"]
    ids = {item.get("id") for item in interfaces if isinstance(item, dict)}
    for missing in sorted(REQUIRED_INTERFACE_IDS - ids):
        errors.append(f"interfaces fehlt: {missing}")
    for item in interfaces:
        if not isinstance(item, dict):
            errors.append("interfaces enthaelt einen Nicht-Objekt-Eintrag")
            continue
        interface_id = item.get("id", "<unknown>")
        for key in ("area", "source", "families", "mvp_boundary"):
            if key not in item:
                errors.append(f"interfaces.{interface_id}.{key} fehlt")
        families = item.get("families")
        if not isinstance(families, list) or not all(isinstance(value, str) and value for value in families):
            errors.append(f"interfaces.{interface_id}.families muss nichtleere Strings enthalten")
    return errors


def _validate_mcp_tools(payload: dict[str, Any]) -> list[str]:
    tools = payload.get("planned_read_only_mcp_tools")
    if not isinstance(tools, list):
        return ["planned_read_only_mcp_tools muss eine Liste sein"]
    names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
    required = {"notarial_interface_inventory_list", "notarial_interface_boundary_check"}
    errors = [f"planned_read_only_mcp_tools fehlt: {name}" for name in sorted(required - names)]
    for tool in tools:
        if not isinstance(tool, dict):
            errors.append("planned_read_only_mcp_tools enthaelt einen Nicht-Objekt-Eintrag")
            continue
        if "external BNotK calls" not in str(tool.get("blocked_output", "")):
            errors.append(f"{tool.get('name', '<unknown>')} muss externe BNotK-Aufrufe blockieren")
    return errors


def _validate_owner_gates(payload: dict[str, Any]) -> list[str]:
    gates = payload.get("owner_gates")
    if not isinstance(gates, list):
        return ["owner_gates muss eine Liste sein"]
    gate_set = {gate for gate in gates if isinstance(gate, str)}
    return [f"owner_gates fehlt: {gate}" for gate in sorted(REQUIRED_OWNER_GATES - gate_set)]


def _validate_evidence_shape(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    evidence_shape = payload.get("evidence_shape")
    if not isinstance(evidence_shape, dict):
        return ["evidence_shape muss ein Objekt sein"]
    blocked = set(_string_list(evidence_shape.get("blocked_fields")))
    for field in ("identity_token", "client_certificate", "private_key", "pin", "matter_content"):
        if field not in blocked:
            errors.append(f"evidence_shape.blocked_fields fehlt: {field}")
    allowed = set(_string_list(evidence_shape.get("allowed_fields")))
    for field in ("interface_id", "boundary_status", "owner_gate_required"):
        if field not in allowed:
            errors.append(f"evidence_shape.allowed_fields fehlt: {field}")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    for path in (DOC_DE, DOC_EN):
        if not path.is_file():
            errors.append(f"Pflichtdokument fehlt: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        _reject_prohibited_text(path, text, errors)
        for term in (
            "Mandantenportal",
            "UVZ",
            "VVZ",
            "XNotar",
            "eNoVA",
            "Zentrales Vorsorgeregister",
            "beN",
            "XJustiz 3.3.1",
            "MCP",
        ):
            if term not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt {term} nicht")
        if "notarial-application-interface-inventory.contract.json" not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} verlinkt den Vertrag nicht")
    return errors


def _reject_prohibited_text(path: Path, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt verbotenen Marker: {marker}")


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    errors = validate_contract()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("notarial application interface inventory contract OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
