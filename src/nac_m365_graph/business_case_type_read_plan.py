from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CONTRACT_PATH = Path("workflows/contracts/business-case-type-graph-read-edge.contract.json")
DEFAULT_OPERATION = "case_create_validation"
DEFAULT_ROLE = "runtime_service"
DEFAULT_RUNTIME_PERMISSION = "Sites.Selected"
DEFAULT_SITE_GRANT_ROLE = "read"

_APPROVED_OPERATION_ROLE_BINDINGS = {
    "case_create_validation": [
        "notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"
    ],
    "matter_type_correction_validation": ["MatterCorrector", "runtime_service"],
    "backfill_validation": ["BackfillOperator", "runtime_service"],
    "optional_process_read": [
        "notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"
    ],
}
_ITEM_FIELDS = ["id", "eTag"]
_REGISTRY_FIELDS = ["BusinessCaseTypeId", "LifecycleStatus", "Selectable", "CatalogVersion"]
_FILTER_FIELDS = ["BusinessCaseTypeId", "CatalogVersion"]

_SAFE_PLAN_DEFAULTS: dict[str, Any] = {
    "method": "GET",
    "graph_version": "v1.0",
    "logical_resource_binding": "Vorgangsartenregister",
    "selected_field_names": [
        "id",
        "eTag",
        "BusinessCaseTypeId",
        "LifecycleStatus",
        "Selectable",
        "CatalogVersion",
    ],
    "page_limit": 100,
    "item_limit": 1000,
    "response_byte_limit": 1048576,
    "contract_version": "nac.business-case-type-graph-read-edge/v0.1",
}


def build_business_case_type_read_plan(
    repo_root: Path,
    *,
    operation: str = DEFAULT_OPERATION,
    role: str = DEFAULT_ROLE,
    runtime_permission: str = DEFAULT_RUNTIME_PERMISSION,
    site_grant_role: str = DEFAULT_SITE_GRANT_ROLE,
) -> dict[str, Any]:
    contract = _load_contract(repo_root)
    contract_valid = _contract_is_valid(contract)

    bindings = _dict_at(contract, "authorization", "operation_role_bindings") if contract_valid else {}
    allowed_roles = bindings.get(operation) if isinstance(bindings, dict) else None
    operation_allowed = isinstance(allowed_roles, list)
    gates = {
        "contract_valid": contract_valid,
        "operation_allowed": operation_allowed,
        "role_allowed_for_operation": operation_allowed and role in allowed_roles,
        "runtime_permission_allowed": contract_valid
        and runtime_permission in _list_at(contract, "authorization", "allowed_runtime_permissions_exact"),
        "site_grant_role_allowed": contract_valid
        and site_grant_role == _value_at(contract, "binding", "site_grant_role_exact"),
        "offline_only": contract_valid and _offline_guards_hold(contract),
    }
    values = _plan_values(contract) if contract_valid else dict(_SAFE_PLAN_DEFAULTS)
    return {
        "status": "PASSED" if all(gates.values()) else "BLOCKED",
        "method": values["method"],
        "graph_version": values["graph_version"],
        "logical_resource_binding": values["logical_resource_binding"],
        "selected_field_names": values["selected_field_names"],
        "page_limit": values["page_limit"],
        "item_limit": values["item_limit"],
        "response_byte_limit": values["response_byte_limit"],
        "gate_results": gates,
        "contract_version": values["contract_version"],
    }


def format_business_case_type_read_plan(plan: dict[str, Any]) -> str:
    lines = [
        f"STATUS: {plan['status']}",
        f"Method: {plan['method']}",
        f"Graph version: {plan['graph_version']}",
        f"Logical resource: {plan['logical_resource_binding']}",
        f"Selected fields: {', '.join(plan['selected_field_names'])}",
        f"Page limit: {plan['page_limit']}",
        f"Item limit: {plan['item_limit']}",
        f"Response byte limit: {plan['response_byte_limit']}",
        f"Contract version: {plan['contract_version']}",
        "Gates:",
    ]
    lines.extend(f"  {name}: {str(value).lower()}" for name, value in plan["gate_results"].items())
    return "\n".join(lines) + "\n"


def _load_contract(repo_root: Path) -> dict[str, Any]:
    try:
        payload = json.loads((repo_root / CONTRACT_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _contract_is_valid(contract: dict[str, Any]) -> bool:
    bindings = _dict_at(contract, "authorization", "operation_role_bindings")
    checks = (
        contract.get("schema_version") == _SAFE_PLAN_DEFAULTS["contract_version"],
        contract.get("contract_id") == "m365.business_case_type_graph_read_edge",
        _value_at(contract, "slice", "read_edge_only") is True,
        _value_at(contract, "slice", "s4b_writes_in_scope") is False,
        _value_at(contract, "slice", "allowed_live_graph_calls") == 0,
        _value_at(contract, "binding", "logical_list_name") == _SAFE_PLAN_DEFAULTS["logical_resource_binding"],
        _value_at(contract, "binding", "site_id_must_equal_bound_value") is True,
        _value_at(contract, "binding", "list_id_must_equal_bound_value") is True,
        _value_at(contract, "binding", "mismatch_behavior") == "block_before_transport",
        _value_at(contract, "binding", "site_grant_role_exact") == DEFAULT_SITE_GRANT_ROLE,
        _value_at(contract, "binding", "broader_site_grant_roles_allowed") is False,
        _list_at(contract, "authorization", "allowed_runtime_permissions_exact") == [DEFAULT_RUNTIME_PERMISSION],
        _value_at(contract, "authorization", "delegated_permissions_allowed") is False,
        _value_at(contract, "authorization", "schema_permissions_allowed") is False,
        _value_at(contract, "authorization", "provisioning_permissions_allowed") is False,
        _value_at(contract, "authorization", "broader_site_permissions_allowed") is False,
        bindings == _APPROVED_OPERATION_ROLE_BINDINGS,
        _value_at(contract, "authorization", "unknown_operation_or_role_behavior") == "block_before_transport",
        _value_at(contract, "graph_request", "base_url") == "https://graph.microsoft.com/v1.0",
        _list_at(contract, "graph_request", "allowed_methods") == ["GET"],
        _value_at(contract, "graph_request", "api_version") == "v1.0",
        _list_at(contract, "graph_request", "item_select_exact") == _ITEM_FIELDS,
        _list_at(contract, "graph_request", "fields_select_exact") == _REGISTRY_FIELDS,
        _list_at(contract, "graph_request", "selected_properties_exact") == _SAFE_PLAN_DEFAULTS["selected_field_names"],
        _list_at(contract, "graph_request", "filter_fields_exact") == _FILTER_FIELDS,
        _value_at(contract, "graph_request", "graph_beta_allowed") is False,
        _value_at(contract, "graph_request", "graph_sdk_allowed") is False,
        _value_at(contract, "graph_request", "sharepoint_rest_allowed") is False,
        _value_at(contract, "graph_request", "pnp_allowed") is False,
        _value_at(contract, "graph_request", "redirects_allowed") is False,
        _value_at(contract, "graph_request", "request_headers", "collection_if_none_match_allowed") is False,
        _value_at(
            contract,
            "graph_request",
            "request_headers",
            "row_etag_as_collection_if_none_match_allowed",
        )
        is False,
        _value_at(contract, "paging", "complete_collection_required") is True,
        _value_at(contract, "paging", "partial_success_allowed") is False,
        _value_at(contract, "paging", "next_link_must_be_absolute_https") is True,
        _value_at(contract, "paging", "next_link_host_exact") == "graph.microsoft.com",
        _value_at(contract, "paging", "next_link_base_path_exact") == "/v1.0",
        _value_at(contract, "paging", "next_link_same_site_required") is True,
        _value_at(contract, "paging", "next_link_same_list_required") is True,
        _value_at(contract, "paging", "next_link_same_collection_required") is True,
        _value_at(contract, "paging", "next_link_same_projection_required") is True,
        _value_at(contract, "paging", "canonical_next_link_loop_detection") is True,
        _value_at(contract, "paging", "max_pages") == 100,
        _value_at(contract, "paging", "max_items") == 1000,
        _value_at(contract, "response_typing", "max_response_bytes") == 1048576,
        _value_at(contract, "paging", "next_link_same_business_case_type_id_filter_required") is True,
        _value_at(contract, "paging", "next_link_same_catalog_version_filter_required") is True,
        _value_at(contract, "offline_cli", "command") == "nac m365 teams-sharepoint business-case-type-read-plan",
        _offline_guards_hold(contract),
    )
    return all(checks)

def _offline_guards_hold(contract: dict[str, Any]) -> bool:
    offline = _dict_at(contract, "offline_cli")
    return all(
        (
            offline.get("credentials_accepted_or_loaded") is False,
            offline.get("http_allowed") is False,
            offline.get("dns_allowed") is False,
            offline.get("live_graph_client_instantiated") is False,
            offline.get("live_calls_allowed") == 0,
        )
    )


def _plan_values(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "method": _list_at(contract, "graph_request", "allowed_methods")[0],
        "graph_version": _value_at(contract, "graph_request", "api_version"),
        "logical_resource_binding": _value_at(contract, "binding", "logical_list_name"),
        "selected_field_names": _list_at(contract, "graph_request", "selected_properties_exact"),
        "page_limit": _value_at(contract, "paging", "max_pages"),
        "item_limit": _value_at(contract, "paging", "max_items"),
        "response_byte_limit": _value_at(contract, "response_typing", "max_response_bytes"),
        "contract_version": contract["schema_version"],
    }


def _dict_at(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    value = _value_at(payload, *keys)
    return value if isinstance(value, dict) else {}


def _list_at(payload: dict[str, Any], *keys: str) -> list[Any]:
    value = _value_at(payload, *keys)
    return value if isinstance(value, list) else []


def _value_at(payload: dict[str, Any], *keys: str) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value
