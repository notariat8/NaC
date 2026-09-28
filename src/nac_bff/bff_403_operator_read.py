"""Pure offline request compilation for the inactive Issue #756 operator design.

There is deliberately no credential, HTTP, Azure CLI, or provider port here.
The production factory remains closed regardless of synthetic plan validity.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote


class OperatorReadBlocked(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "workflows/verification-contracts/m365-bff-403-operator-read.verification.json"
)
_CONTRACT_SHA256 = "950319c7560bdab1684b6c0f8425f2e26c0a51defdeaab6e2aa7da5738e19b5b"
_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z")
_COMPONENT = re.compile(r"appi-nac-bff-test-[a-z0-9-]+\Z")
_WORKSPACE_SUFFIX = re.compile(
    r"/resourceGroups/rg-nac-bff-test/providers/"
    r"Microsoft\.OperationalInsights/workspaces/log-nac-bff-test-[a-z0-9-]+\Z"
)
_OPERATIONS = (
    "azure_function_metadata",
    "insights_component_discovery",
    "insights_component_metadata",
    "log_analytics_workspace_metadata",
    "historical_request_summary",
)
_API_VERSIONS = ("2025-03-01", "2021-04-01", "2020-02-02", "2025-07-01", None)
_PROJECTIONS = (
    ["id", "type", "name", "kind", "properties.state", "properties.provisioningState"],
    ["value[].id", "value[].type", "value[].name"],
    ["id", "properties.AppId", "properties.IngestionMode", "properties.WorkspaceResourceId", "properties.RetentionInDays", "properties.SamplingPercentage", "properties.provisioningState"],
    ["id", "properties.retentionInDays"],
    ["telemetry_rows", "http_401", "http_403", "other"],
)
_KQL_LINES = (
    "requests",
    "| where timestamp between (datetime(2026-09-25T10:42:03.397Z) .. datetime(2026-09-25T10:42:10.487Z))",
    '| where url startswith "https://func-nac-bff-test-funktion8.azurewebsites.net/v1/workspaces/notary_team_01/matters/NAC-SYN-MATTER-001/workbench-snapshot"',
    '| summarize telemetry_rows=count(), http_401=countif(resultCode == "401"), http_403=countif(resultCode == "403"), other=countif(resultCode !in ("401", "403"))',
)
_BINDING_KEYS = frozenset({"subscription", "component", "app_id", "workspace"})
_FUNCTION_FIELDS = frozenset({
    "id", "type", "name", "kind", "properties.state", "properties.provisioningState"
})
_COMPONENT_FIELDS = frozenset({
    "id", "properties.AppId", "properties.IngestionMode",
    "properties.WorkspaceResourceId", "properties.RetentionInDays",
    "properties.SamplingPercentage", "properties.provisioningState",
})
_OBSERVATION_START = datetime(2026, 9, 25, 10, 42, 3, 397000, tzinfo=timezone.utc)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def validate_contract(value: object) -> list[str]:
    """Pin the entire inactive contract, including all zero budgets and proofs."""
    if not isinstance(value, dict):
        return ["INVALID_OPERATOR_CONTRACT"]
    if (
        value.get("schema_version") != "nac.bff-403-operator-read.verification/v1"
        or value.get("status") != "LOCAL_INACTIVE_ONLY"
        or value.get("leading_issue") != "https://github.com/notariat8/NaC/issues/756"
    ):
        return ["INVALID_OPERATOR_CONTRACT"]
    target = value.get("target")
    if (
        not isinstance(target, dict)
        or target.get("workspace_class") != "synthetic_notary_team_01"
        or target.get("resource_group") != "rg-nac-bff-test"
        or target.get("function_name") != "func-nac-bff-test-funktion8"
        or target.get("component_name_prefix") != "appi-nac-bff-test-"
        or any(field.endswith("_binding_sha256") and field_value != "UNBOUND" for field, field_value in target.items())
    ):
        return ["INVALID_OPERATOR_CONTRACT"]
    resources = value.get("resources")
    if not isinstance(resources, list) or len(resources) != len(_OPERATIONS):
        return ["INVALID_OPERATOR_CONTRACT"]
    for index, (resource, operation) in enumerate(zip(resources, _OPERATIONS)):
        if (
            not isinstance(resource, dict)
            or resource.get("id") != operation
            or resource.get("method") != "GET"
            or resource.get("host") != ("api.applicationinsights.io" if index == 4 else "management.azure.com")
            or resource.get("api_version") != _API_VERSIONS[index]
            or resource.get("projection") != _PROJECTIONS[index]
            or resource.get("endpoint_binding_sha256") != "UNBOUND"
            or type(resource.get("maximum_reads")) is not int
            or resource["maximum_reads"] != 0
        ):
            return ["INVALID_OPERATOR_CONTRACT"]
    if (
        resources[1].get("filter") != "resourceType eq 'Microsoft.Insights/components' and substringof('appi-nac-bff-test-',name)"
        or type(resources[1].get("top")) is not int or resources[1]["top"] != 2
        or resources[3].get("optional_for_classic_ingestion") is not True
        or resources[4].get("query_lines") != list(_KQL_LINES)
        or resources[4].get("query_sha256") != "UNBOUND"
    ):
        return ["INVALID_OPERATOR_CONTRACT"]
    policy = value.get("read_policy")
    if not isinstance(policy, dict) or any(
        policy.get(field) is not False for field in (
            "redirect_allowed", "retry_allowed", "paging_allowed", "request_body_allowed",
            "free_url_allowed", "raw_response_log_allowed", "full_request_uri_log_allowed",
        )
    ) or any(policy.get(field) is not True for field in (
        "required_before_port_factory", "required_before_every_read", "atomic_budget_consume",
        "pre_get_component_projection_required",
    )) or type(policy.get("maximum_historical_query_gets")) is not int or policy["maximum_historical_query_gets"] != 1:
        return ["INVALID_OPERATOR_CONTRACT"]
    gates = value.get("gates")
    if not isinstance(gates, dict) or any(
        field_value is not False for field, field_value in gates.items() if field.endswith("_authorized")
    ) or any(type(gates.get(field)) is not int or gates[field] != 0 for field in (
        "maximum_provider_reads", "maximum_credential_writes", "maximum_deployments",
    )):
        return ["INVALID_OPERATOR_CONTRACT"]
    approval = value.get("approval_boundary")
    if not isinstance(approval, dict) or (
        approval.get("same_principal_accounts_are_distinct_approvers") is not False
        or approval.get("solo_four_eyes_satisfied") is not False
        or approval.get("solo_without_cited_two_person_duty") != "OWNER_SOLO_APPROVAL"
        or approval.get("uncited_two_person_duty") != "BLOCKED_REQUIREMENT_CITATION_MISSING"
        or approval.get("cited_two_person_duty_with_one_principal") != "BLOCKED_SINGLE_PRINCIPAL"
    ):
        return ["INVALID_OPERATOR_CONTRACT"]
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if hashlib.sha256(canonical.encode("utf-8")).hexdigest() != _CONTRACT_SHA256:
        return ["INVALID_OPERATOR_CONTRACT"]
    root = CONTRACT_PATH.parents[2]
    for paths in (value["specifications"], value["plans"]):
        for relative in paths.values():
            if not (root / relative).is_file():
                return ["MISSING_OPERATOR_DOCUMENT"]
    return []


def _contract() -> dict[str, Any]:
    try:
        value = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"), object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, ValueError):
        raise OperatorReadBlocked("BLOCKED_CONTRACT_BINDING") from None
    if validate_contract(value):
        raise OperatorReadBlocked("BLOCKED_CONTRACT_BINDING")
    return value


def _bound(bindings: Mapping[str, str], name: str) -> str:
    if not isinstance(bindings, Mapping) or not set(bindings).issubset(_BINDING_KEYS):
        raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
    value = bindings.get(name)
    if type(value) is not str or not value.isascii():
        raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
    return value


def _subscription(bindings: Mapping[str, str]) -> str:
    value = _bound(bindings, "subscription")
    if not _UUID.fullmatch(value):
        raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
    return value


def _workspace(bindings: Mapping[str, str]) -> str:
    value = _bound(bindings, "workspace")
    prefix = "/subscriptions/" + _subscription(bindings)
    if not value.startswith(prefix) or not _WORKSPACE_SUFFIX.fullmatch(value[len(prefix):]):
        raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
    return value


def compile_request(operation_id: str, bindings: Mapping[str, str]) -> tuple[bytes, bytes | None]:
    """Compile a fixed request in memory; never issue it or print its URI."""
    contract = _contract()
    if type(operation_id) is not str or operation_id not in _OPERATIONS:
        raise OperatorReadBlocked("BLOCKED_OPERATION")
    if not isinstance(bindings, Mapping) or not set(bindings).issubset(_BINDING_KEYS):
        raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
    resources = {item["id"]: item for item in contract["resources"]}
    resource = resources[operation_id]
    if resource["method"] != "GET" or resource["maximum_reads"] != 0:
        raise OperatorReadBlocked("BLOCKED_CONTRACT_BINDING")
    query_bytes: bytes | None = None
    if operation_id == "historical_request_summary":
        app_id = _bound(bindings, "app_id")
        if not _UUID.fullmatch(app_id):
            raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
        query_bytes = "\n".join(resource["query_lines"]).encode("utf-8")
        uri = "https://api.applicationinsights.io/v1/apps/" + app_id + "/query?query=" + quote(query_bytes.decode("utf-8"), safe="")
    else:
        subscription = _subscription(bindings)
        base = (
            "https://management.azure.com/subscriptions/" + subscription
            + "/resourceGroups/rg-nac-bff-test"
        )
        if operation_id == "azure_function_metadata":
            uri = base + "/providers/Microsoft.Web/sites/func-nac-bff-test-funktion8?api-version=2025-03-01"
        elif operation_id == "insights_component_discovery":
            encoded_filter = quote(resource["filter"], safe="'()/,")
            uri = base + "/resources?api-version=2021-04-01&$filter=" + encoded_filter + "&$top=2"
        elif operation_id == "insights_component_metadata":
            component = _bound(bindings, "component")
            if not _COMPONENT.fullmatch(component):
                raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
            uri = base + "/providers/Microsoft.Insights/components/" + component + "?api-version=2020-02-02"
        else:
            uri = "https://management.azure.com" + _workspace(bindings) + "?api-version=2025-07-01"
    if not uri.isascii() or any(character.isspace() for character in uri):
        raise OperatorReadBlocked("BLOCKED_REQUEST_BINDING")
    return uri.encode("ascii"), query_bytes


def create_production_operator_read(
    credential_provider: Callable[[], object], transport_provider: Callable[[], object]
) -> None:
    """The local-only design does not create either provider factory."""
    del credential_provider, transport_provider
    raise OperatorReadBlocked("BLOCKED_NO_REFRESH_CAPABILITY")


def classify_function_metadata(
    status_code: int,
    projection: object,
    *,
    target_proven: bool,
    read_right_proven: bool,
) -> str:
    if type(status_code) is not int or type(target_proven) is not bool or type(read_right_proven) is not bool:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    if status_code == 404 and projection is None:
        return "BFF_NOT_DEPLOYED" if target_proven and read_right_proven else "UNPROVEN"
    if status_code != 200:
        if projection is not None:
            raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
        return "UNPROVEN"
    if not isinstance(projection, dict) or set(projection) != _FUNCTION_FIELDS:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    return "UNPROVEN"  # Existence is not a deployed-package proof.


def select_insights_component(projection: object, subscription: str) -> str:
    if type(subscription) is not str or not _UUID.fullmatch(subscription):
        raise OperatorReadBlocked("BLOCKED_TARGET_BINDING")
    if not isinstance(projection, dict) or set(projection) != {"value"}:
        raise OperatorReadBlocked("BLOCKED_COMPONENT_DISCOVERY")
    values = projection["value"]
    if not isinstance(values, list) or len(values) != 1:
        raise OperatorReadBlocked("BLOCKED_COMPONENT_DISCOVERY")
    item = values[0]
    if not isinstance(item, dict) or set(item) != {"id", "type", "name"}:
        raise OperatorReadBlocked("BLOCKED_COMPONENT_DISCOVERY")
    name = item["name"]
    if type(name) is not str or not _COMPONENT.fullmatch(name):
        raise OperatorReadBlocked("BLOCKED_COMPONENT_DISCOVERY")
    expected = (
        "/subscriptions/" + subscription + "/resourceGroups/rg-nac-bff-test/"
        "providers/Microsoft.Insights/components/" + name
    )
    if (
        item["type"] != "Microsoft.Insights/components"
        or item["id"] != expected
    ):
        raise OperatorReadBlocked("BLOCKED_COMPONENT_DISCOVERY")
    return name


def validate_component_projection(
    projection: object, *, expected_component_id: str,
    pre_get_projection_proven: bool, link_proven: bool
) -> str:
    """Check a synthetic projection, not the pre-GET transport proof itself."""
    if pre_get_projection_proven is not True or link_proven is not True:
        raise OperatorReadBlocked("BLOCKED_COMPONENT_PROOF")
    if not isinstance(projection, dict) or set(projection) != _COMPONENT_FIELDS:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    app_id = projection["properties.AppId"]
    if type(app_id) is not str or not _UUID.fullmatch(app_id):
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    component_id = projection["id"]
    if type(component_id) is not str or type(expected_component_id) is not str or component_id != expected_component_id:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    match = re.fullmatch(
        r"/subscriptions/([0-9a-f-]{36})/resourceGroups/rg-nac-bff-test/"
        r"providers/Microsoft\.Insights/components/(appi-nac-bff-test-[a-z0-9-]+)",
        component_id,
    )
    if match is None or not _UUID.fullmatch(match.group(1)) or not _COMPONENT.fullmatch(match.group(2)):
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    if projection["properties.IngestionMode"] not in {"LogAnalytics", "ApplicationInsights"}:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    workspace = projection["properties.WorkspaceResourceId"]
    if projection["properties.IngestionMode"] == "LogAnalytics":
        prefix = "/subscriptions/" + match.group(1)
        if type(workspace) is not str or not workspace.startswith(prefix) or not _WORKSPACE_SUFFIX.fullmatch(workspace[len(prefix):]):
            raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    elif workspace is not None:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    retention = projection["properties.RetentionInDays"]
    sampling = projection["properties.SamplingPercentage"]
    if type(retention) is not int or not 1 <= retention <= 3650:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    if type(sampling) not in {int, float} or not 0 < sampling <= 100:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    if projection["properties.provisioningState"] != "Succeeded":
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    return app_id


def validate_workspace_projection(projection: object, expected_id: str, *, as_of_utc: datetime) -> bool:
    """Check synthetic retention against the fixed observation start."""
    if not isinstance(projection, dict) or set(projection) != {"id", "properties.retentionInDays"}:
        raise OperatorReadBlocked("BLOCKED_RETENTION_PROOF")
    if type(as_of_utc) is not datetime or as_of_utc.tzinfo is None or as_of_utc.utcoffset() != timedelta(0) or as_of_utc < _OBSERVATION_START:
        raise OperatorReadBlocked("BLOCKED_RETENTION_PROOF")
    if type(expected_id) is not str:
        raise OperatorReadBlocked("BLOCKED_RETENTION_PROOF")
    match = re.fullmatch(r"/subscriptions/([0-9a-f-]{36})(/resourceGroups/rg-nac-bff-test/providers/Microsoft\.OperationalInsights/workspaces/log-nac-bff-test-[a-z0-9-]+)", expected_id)
    if match is None or not _UUID.fullmatch(match.group(1)):
        raise OperatorReadBlocked("BLOCKED_RETENTION_PROOF")
    days = projection["properties.retentionInDays"]
    if projection["id"] != expected_id or type(days) is not int or not 1 <= days <= 3650 or _OBSERVATION_START < as_of_utc - timedelta(days=days):
        raise OperatorReadBlocked("BLOCKED_RETENTION_PROOF")
    return True


def classify_historical_summary(
    summary: object, *, capture_proven: bool, retention_proven: bool,
    link_proven: bool, permission_proven: bool,
) -> str:
    fields = {"telemetry_rows", "http_401", "http_403", "other"}
    if not isinstance(summary, dict) or set(summary) != fields:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    if any(type(summary[name]) is not int or summary[name] < 0 for name in fields):
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    if summary["telemetry_rows"] != summary["http_401"] + summary["http_403"] + summary["other"]:
        raise OperatorReadBlocked("BLOCKED_RESPONSE_REDACTION")
    proofs = (capture_proven, retention_proven, link_proven, permission_proven)
    if any(type(proof) is not bool for proof in proofs):
        raise OperatorReadBlocked("BLOCKED_PROOF_BINDING")
    if not all(proofs) or summary["telemetry_rows"] == 0:
        return "UNPROVEN"
    return "TEMPORAL_STATUS_ONLY" if summary["http_401"] or summary["http_403"] else "UNPROVEN"


__all__ = [
    "CONTRACT_PATH", "OperatorReadBlocked", "classify_function_metadata",
    "classify_historical_summary", "compile_request", "create_production_operator_read",
    "select_insights_component", "validate_component_projection",
    "validate_contract", "validate_workspace_projection",
]
