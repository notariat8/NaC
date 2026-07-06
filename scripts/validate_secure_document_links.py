from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "secure-document-link.contract.json"
REQUIRED_STORAGE_TARGETS = {"onedrive", "sharepoint_document_library", "sharepoint_list_item_attachment"}
REQUIRED_EVIDENCE_FIELDS = {
    "purpose",
    "expires_at",
    "matter_binding",
    "storage_target",
    "revocation",
    "audit_event",
}
REQUIRED_TRUE_POLICIES = {
    "requires_matter_binding",
    "requires_purpose",
    "requires_expiry",
    "requires_revocation",
    "requires_audit_event",
}
PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "secret_link_value",
    "ghp_",
    "gho_",
}


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    if payload.get("contract_id") != "workflow.secure_document_link":
        errors.append("contract_id muss workflow.secure_document_link sein")
    if "n8-demonotariat" not in _string_list(payload.get("client_surfaces")):
        errors.append("client_surfaces muss n8-demonotariat enthalten")

    storage_targets = set(_string_list(payload.get("storage_targets")))
    missing_targets = sorted(REQUIRED_STORAGE_TARGETS - storage_targets)
    for target in missing_targets:
        errors.append(f"storage_targets fehlt: {target}")

    link_policy = payload.get("link_policy")
    if not isinstance(link_policy, dict):
        errors.append("link_policy muss ein Objekt sein")
    else:
        if link_policy.get("secret_link_stored_in_product_repo") is not False:
            errors.append("secret_link_stored_in_product_repo muss false sein")
        for key in sorted(REQUIRED_TRUE_POLICIES):
            if link_policy.get(key) is not True:
                errors.append(f"link_policy.{key} muss true sein")

    evidence_schema = payload.get("evidence_schema")
    if not isinstance(evidence_schema, dict):
        errors.append("evidence_schema muss ein Objekt sein")
    else:
        required = set(_string_list(evidence_schema.get("required")))
        missing_fields = sorted(REQUIRED_EVIDENCE_FIELDS - required)
        for field in missing_fields:
            errors.append(f"evidence_schema.required fehlt: {field}")
        properties = evidence_schema.get("properties")
        if not isinstance(properties, dict):
            errors.append("evidence_schema.properties muss ein Objekt sein")
        else:
            for field in sorted(REQUIRED_EVIDENCE_FIELDS):
                if field not in properties:
                    errors.append(f"evidence_schema.properties fehlt: {field}")

    write_flow = _string_list(payload.get("write_flow"))
    if not write_flow or write_flow[-1] != "human_review_before_matter_attachment":
        errors.append("write_flow muss mit human_review_before_matter_attachment enden")

    guardrails = payload.get("guardrails")
    if not isinstance(guardrails, dict):
        errors.append("guardrails muss ein Objekt sein")
    else:
        for key in ("secret_links_in_git", "real_mandate_data_in_product_repo", "mobile_link_replaces_authorization"):
            if guardrails.get(key) is not False:
                errors.append(f"guardrails.{key} muss false sein")
        if guardrails.get("human_review_required_before_attachment") is not True:
            errors.append("guardrails.human_review_required_before_attachment muss true sein")

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
    print("OK: Secure Document Link Contract erfüllt Mindestfelder für Zweck, Ablauf, Aktenbindung, Speicherziel, Widerruf und Audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
