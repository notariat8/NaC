from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "agent-runtime-registry.contract.json"
SCHEMA = REPO_ROOT / "deploy" / "database" / "atp-agent-runtime-registry-schema.sql"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "agent-runtime-registry.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "agent-runtime-registry.md"

REQUIRED_TABLES = {
    "nac_agent_registry",
    "nac_agent_endpoints",
    "nac_sandbox_bindings",
    "nac_sandbox_leases",
    "nac_agent_session_bindings",
}
REQUIRED_OWNER_GATES = {
    "productive_schema_apply",
    "connector_credential_material",
    "mtls_material_import",
    "productive_connector_start",
    "sandbox_auto_start_policy",
    "private_payload_access",
}
REQUIRED_BLOCKED_ACTIONS = {
    "oci_resource_manager_apply",
    "atp_schema_apply",
    "notoclaw_runtime_mutation",
    "dashboard_token_capture",
    "secret_read_or_write",
    "raw_mandate_data_processing",
    "direct_publication_of_raw_openclaw_ui",
}
PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "client_secret",
    "ghp_",
    "gho_",
    "oci_session_token",
    "password=",
}


def main() -> int:
    errors = validate()
    if errors:
        print("Agent runtime registry validation failed:")
        for error in errors:
            print(f"- {error}")
        print("STATUS: FAILED")
        return 1
    print("Agent runtime registry validation passed.")
    print("STATUS: PASSED")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    payload = _read_json(CONTRACT, errors)
    if not payload:
        return errors
    errors.extend(_validate_contract(payload))
    errors.extend(_validate_schema(payload))
    errors.extend(_validate_docs())
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing JSON artifact: {path.relative_to(REPO_ROOT)}")
        return {}
    text = path.read_text(encoding="utf-8")
    _reject_prohibited_text(path, text, errors)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON {path.relative_to(REPO_ROOT)}: {exc}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
        return {}
    return payload


def _validate_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    expected = {
        "schema_version": "nac.agent-runtime-registry/v0.1",
        "contract_id": "runtime.agent_registry",
        "status": "contract_first_no_schema_apply",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key} must be {value}")

    public_entry = payload.get("public_entry")
    if not isinstance(public_entry, dict):
        errors.append("public_entry must be an object")
    else:
        if public_entry.get("hostname") != "agent.notariat8.de":
            errors.append("public_entry.hostname must be agent.notariat8.de")
        if public_entry.get("edge") != "oci_identity_api_gateway_or_bff":
            errors.append("public_entry.edge must be oci_identity_api_gateway_or_bff")
        for flag in ("browser_to_brev_allowed", "raw_notoclaw_ui_publication_allowed", "cloudflare_dependency_allowed"):
            if public_entry.get(flag) is not False:
                errors.append(f"public_entry.{flag} must be false")

    transport = payload.get("transport")
    if not isinstance(transport, dict):
        errors.append("transport must be an object")
    else:
        if transport.get("productive_default") != "outbound_mtls_or_websocket_https_from_notoclaw_to_oci":
            errors.append("transport.productive_default must be outbound_mtls_or_websocket_https_from_notoclaw_to_oci")
        if transport.get("ssh_user_traffic_allowed") is not False:
            errors.append("transport.ssh_user_traffic_allowed must be false")
        if transport.get("ssh_operations_diagnostics_allowed") is not True:
            errors.append("transport.ssh_operations_diagnostics_allowed must be true")

    schema_artifact = payload.get("atp_schema_artifact")
    if not isinstance(schema_artifact, dict):
        errors.append("atp_schema_artifact must be an object")
    else:
        if schema_artifact.get("status") != "artifact_only_no_apply":
            errors.append("atp_schema_artifact.status must be artifact_only_no_apply")
        if schema_artifact.get("path") != "deploy/database/atp-agent-runtime-registry-schema.sql":
            errors.append("atp_schema_artifact.path must point to the agent runtime schema artifact")
        contract_tables = {
            table.get("name")
            for table in schema_artifact.get("tables", [])
            if isinstance(table, dict) and isinstance(table.get("name"), str)
        }
        for missing in sorted(REQUIRED_TABLES - contract_tables):
            errors.append(f"atp_schema_artifact.tables missing {missing}")
        guardrails = schema_artifact.get("guardrails")
        if not isinstance(guardrails, dict):
            errors.append("atp_schema_artifact.guardrails must be an object")
        else:
            for flag in (
                "idempotent_create_only",
                "json_payload_check_required",
                "tenant_boundary_required",
                "lease_expiry_required",
            ):
                if guardrails.get(flag) is not True:
                    errors.append(f"atp_schema_artifact.guardrails.{flag} must be true")
            for flag in (
                "drop_or_truncate_allowed",
                "raw_mandate_payload_columns_allowed",
                "secret_columns_allowed",
                "token_columns_allowed",
            ):
                if guardrails.get(flag) is not False:
                    errors.append(f"atp_schema_artifact.guardrails.{flag} must be false")

    entities = payload.get("entities")
    if not isinstance(entities, list):
        errors.append("entities must be a list")
    else:
        entity_tables = {
            entity.get("table")
            for entity in entities
            if isinstance(entity, dict) and isinstance(entity.get("table"), str)
        }
        for missing in sorted(REQUIRED_TABLES - entity_tables):
            errors.append(f"entities missing table {missing}")
        for entity in entities:
            if not isinstance(entity, dict):
                errors.append("entities entries must be objects")
                continue
            blocked = set(_strings(entity.get("blocked_data_classes")))
            if not blocked:
                errors.append(f"entity {entity.get('id')} must define blocked_data_classes")
            if "raw_mandate_content" not in blocked and entity.get("id") != "agent_endpoints":
                errors.append(f"entity {entity.get('id')} must block raw_mandate_content")

    allocation = payload.get("allocation_policy")
    if not isinstance(allocation, dict):
        errors.append("allocation_policy must be an object")
    else:
        if allocation.get("minimum_isolation_key") != "tenant_user":
            errors.append("allocation_policy.minimum_isolation_key must be tenant_user")
        if allocation.get("preferred_isolation_key") != "tenant_user_matter_role":
            errors.append("allocation_policy.preferred_isolation_key must be tenant_user_matter_role")
        for flag in (
            "shared_sandbox_for_multiple_users_allowed",
        ):
            if allocation.get(flag) is not False:
                errors.append(f"allocation_policy.{flag} must be false")
        for flag in ("active_lease_required_before_reuse", "matter_context_requires_private_payload_gate"):
            if allocation.get(flag) is not True:
                errors.append(f"allocation_policy.{flag} must be true")

    owner_gates = set(_strings(payload.get("owner_gates")))
    for missing in sorted(REQUIRED_OWNER_GATES - owner_gates):
        errors.append(f"owner_gates missing {missing}")
    blocked_actions = set(_strings(payload.get("blocked_actions_without_separate_owner_gate")))
    for missing in sorted(REQUIRED_BLOCKED_ACTIONS - blocked_actions):
        errors.append(f"blocked_actions_without_separate_owner_gate missing {missing}")
    commands = set(_strings(payload.get("validation_commands")))
    if "python scripts/validate_agent_runtime_registry.py" not in commands:
        errors.append("validation_commands missing python scripts/validate_agent_runtime_registry.py")
    return errors


def _validate_schema(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not SCHEMA.is_file():
        return [f"missing schema artifact: {SCHEMA.relative_to(REPO_ROOT)}"]
    text = SCHEMA.read_text(encoding="utf-8")
    _reject_prohibited_text(SCHEMA, text, errors)
    lowered = " ".join(text.lower().split())
    for table in REQUIRED_TABLES:
        if f"create table {table}" not in lowered:
            errors.append(f"schema artifact missing table {table}")
    for required in (
        "payload_json clob check (payload_json is json)",
        "lease_expires_at varchar2(32) not null",
        "connector_mode in ('outbound_mtls', 'outbound_websocket_https')",
        "isolation_key in ('tenant_user', 'tenant_user_matter_role')",
    ):
        if required not in lowered:
            errors.append(f"schema artifact missing guard {required}")
    for forbidden in ("drop table", "truncate table", "client_secret", "private_key", "access_token", "id_token"):
        if forbidden in lowered:
            errors.append(f"schema artifact contains forbidden marker {forbidden.strip()}")
    contract_tables = {
        table.get("name")
        for table in payload.get("atp_schema_artifact", {}).get("tables", [])
        if isinstance(table, dict) and isinstance(table.get("name"), str)
    }
    if contract_tables != REQUIRED_TABLES:
        errors.append("contract table list must match required schema tables exactly")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required = {
        DOC_DE: [
            "Agent-Runtime-Registry Und Sandbox-Leases",
            "agent.notariat8.de",
            "nac_sandbox_leases",
            "tenant + user + vorgang + rolle",
            "kein produktiver Apply",
        ],
        DOC_EN: [
            "Agent Runtime Registry And Sandbox Leases",
            "agent.notariat8.de",
            "nac_sandbox_leases",
            "tenant + user + matter + role",
            "no productive apply",
        ],
    }
    for path, markers in required.items():
        if not path.is_file():
            errors.append(f"missing documentation file: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        _reject_prohibited_text(path, text, errors)
        for marker in markers:
            if marker not in text:
                errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {marker}")
    return errors


def _reject_prohibited_text(path: Path, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker: {marker}")


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


if __name__ == "__main__":
    raise SystemExit(main())
