from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows" / "contracts" / "agent-control-api.contract.json"
REGISTRY_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "agent-runtime-registry.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "agent-control-api.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "agent-control-api.md"

REQUIRED_ROUTES = {
    ("GET", "/agent/status"),
    ("POST", "/agent/leases/prepare"),
    ("POST", "/api/agent/connect"),
    ("POST", "/api/agent/heartbeat"),
    ("GET", "/api/agent/work/next"),
    ("POST", "/api/agent/work/result"),
}
REQUIRED_ATP_TABLES = {
    "nac_agent_registry",
    "nac_agent_endpoints",
    "nac_sandbox_bindings",
    "nac_sandbox_leases",
    "nac_agent_session_bindings",
}
REQUIRED_BLOCKED_FIELDS = {
    "id_token",
    "access_token",
    "refresh_token",
    "session_cookie",
    "provider_claims",
    "dashboard_token",
    "private_key",
    "client_secret",
    "environment_dump",
    "raw_mandate_content",
    "document_full_text",
    "card_pin",
    "xnp_payload",
}
REQUIRED_OWNER_GATES = {
    "route_implementation",
    "oci_api_gateway_apply",
    "connector_secret_material",
    "mtls_material_import",
    "notoclaw_connector_start",
    "private_payload_access",
}
PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "oci_session_token",
    "password=",
}


def main() -> int:
    errors = validate()
    if errors:
        print("Agent control API validation failed:")
        for error in errors:
            print(f"- {error}")
        print("STATUS: FAILED")
        return 1
    print("Agent control API validation passed.")
    print("STATUS: PASSED")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    contract = _read_json(CONTRACT, errors)
    registry = _read_json(REGISTRY_CONTRACT, errors)
    if not contract:
        return errors
    errors.extend(_validate_contract(contract))
    errors.extend(_validate_registry_parity(contract, registry))
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
        "schema_version": "nac.agent-control-api/v0.1",
        "contract_id": "runtime.agent_control_api",
        "status": "contract_first_no_route_apply",
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{key} must be {value}")

    public_origin = payload.get("public_origin")
    if not isinstance(public_origin, dict):
        errors.append("public_origin must be an object")
    else:
        if public_origin.get("hostname") != "agent.notariat8.de":
            errors.append("public_origin.hostname must be agent.notariat8.de")
        if public_origin.get("edge") != "oci_identity_api_gateway_or_bff":
            errors.append("public_origin.edge must be oci_identity_api_gateway_or_bff")
        for flag in (
            "provider_specific_tunnel_allowed_for_production",
            "raw_openclaw_ui_publication_allowed",
            "direct_browser_to_brev_allowed",
        ):
            if public_origin.get(flag) is not False:
                errors.append(f"public_origin.{flag} must be false")

    route_groups = payload.get("route_groups")
    if not isinstance(route_groups, list) or not route_groups:
        errors.append("route_groups must be a non-empty list")
    else:
        routes = set()
        group_ids = set()
        for group in route_groups:
            if not isinstance(group, dict):
                errors.append("route_groups entries must be objects")
                continue
            group_id = group.get("id")
            if isinstance(group_id, str):
                group_ids.add(group_id)
            if not isinstance(group.get("authentication"), str) or not group["authentication"]:
                errors.append(f"route_group {group_id} must define authentication")
            for route in group.get("routes", []):
                if not isinstance(route, dict):
                    errors.append(f"route_group {group_id} route entries must be objects")
                    continue
                method = route.get("method")
                path = route.get("path")
                if isinstance(method, str) and isinstance(path, str):
                    routes.add((method, path))
                if route.get("response_class") not in {
                    "safe_metadata_only",
                    "connector_control_metadata",
                    "work_envelope_metadata",
                    "work_result_metadata",
                }:
                    errors.append(f"route {method} {path} has unsupported response_class")
        if group_ids != {"browser_session", "connector_control"}:
            errors.append("route_groups must include browser_session and connector_control")
        for missing in sorted(REQUIRED_ROUTES - routes):
            errors.append(f"route_groups missing {missing[0]} {missing[1]}")

    payload_policy = payload.get("payload_policy")
    if not isinstance(payload_policy, dict):
        errors.append("payload_policy must be an object")
    else:
        blocked = set(_strings(payload_policy.get("blocked_fields")))
        for missing in sorted(REQUIRED_BLOCKED_FIELDS - blocked):
            errors.append(f"payload_policy.blocked_fields missing {missing}")
        for flag in (
            "raw_mandate_data_allowed",
            "secret_material_allowed",
            "dashboard_token_capture_allowed",
            "full_identity_claim_dump_allowed",
        ):
            if payload_policy.get(flag) is not False:
                errors.append(f"payload_policy.{flag} must be false")

    lease_policy = payload.get("lease_policy")
    if not isinstance(lease_policy, dict):
        errors.append("lease_policy must be an object")
    else:
        tables = set(_strings(lease_policy.get("atp_tables")))
        for missing in sorted(REQUIRED_ATP_TABLES - tables):
            errors.append(f"lease_policy.atp_tables missing {missing}")
        for flag in (
            "active_lease_required_before_work_fetch",
            "expired_or_revoked_lease_fails_closed",
            "tenant_user_isolation_required",
            "tenant_user_matter_role_preferred",
        ):
            if lease_policy.get(flag) is not True:
                errors.append(f"lease_policy.{flag} must be true")
        if lease_policy.get("shared_sandbox_for_multiple_users_allowed") is not False:
            errors.append("lease_policy.shared_sandbox_for_multiple_users_allowed must be false")

    boundary = payload.get("implementation_boundary")
    if not isinstance(boundary, dict):
        errors.append("implementation_boundary must be an object")
    else:
        for flag in (
            "nac_web_route_implementation_in_scope",
            "oci_gateway_apply_in_scope",
            "notoclaw_connector_start_in_scope",
            "atp_schema_apply_in_scope",
        ):
            if boundary.get(flag) is not False:
                errors.append(f"implementation_boundary.{flag} must be false")
        if boundary.get("contract_and_validator_only") is not True:
            errors.append("implementation_boundary.contract_and_validator_only must be true")

    owner_gates = set(_strings(payload.get("owner_gates")))
    for missing in sorted(REQUIRED_OWNER_GATES - owner_gates):
        errors.append(f"owner_gates missing {missing}")

    commands = set(_strings(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_agent_control_api.py",
        "python scripts/validate_agent_runtime_registry.py",
        "python scripts/validate_language_parity.py",
        "python scripts/validate_doc_links.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands missing {command}")
    return errors


def _validate_registry_parity(contract: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not registry:
        return errors
    registry_tables = {
        table.get("name")
        for table in registry.get("atp_schema_artifact", {}).get("tables", [])
        if isinstance(table, dict) and isinstance(table.get("name"), str)
    }
    api_tables = set(_strings(contract.get("lease_policy", {}).get("atp_tables")))
    if not REQUIRED_ATP_TABLES <= registry_tables:
        errors.append("agent runtime registry contract must expose all API lease tables")
    if api_tables != REQUIRED_ATP_TABLES:
        errors.append("agent control API lease_policy.atp_tables must match the required registry tables exactly")
    if registry.get("public_entry", {}).get("hostname") != contract.get("public_origin", {}).get("hostname"):
        errors.append("agent control API public origin must match agent runtime registry public entry")
    return errors


def _validate_docs() -> list[str]:
    errors: list[str] = []
    required = {
        DOC_DE: [
            "Agent-Control-API Für agent.notariat8.de",
            "GET /agent/status",
            "POST /api/agent/heartbeat",
            "tenant + user + vorgang + rolle",
            "keine Routenimplementierung",
        ],
        DOC_EN: [
            "Agent Control API For agent.notariat8.de",
            "GET /agent/status",
            "POST /api/agent/heartbeat",
            "tenant + user + matter + role",
            "no route implementation",
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
