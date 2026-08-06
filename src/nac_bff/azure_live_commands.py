from __future__ import annotations

import configparser
from contextlib import ExitStack
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from nac_bff.azure_activation import FUNCTION_APP, LOCATION, RESOURCE_GROUP
from nac_bff.azure_interruption_contract import (
    BICEP_BASELINE_EXACT,
    RESOURCE_GROUP_ONLY,
    canonical_parameters_from_wrappers,
    compact_sha256_json,
    newline_sha256_json,
    resource_graph_visible_targets,
)
from nac_bff.azure_cli_sealed_runtime import (
    SealedAzureCliRuntime,
    prepare_sealed_azure_cli_runtime,
    sealed_runtime_failure_code,
)
from nac_bff.azure_performance_monitor import is_metrics_url, monitor_policy_sha256
from nac_m365_graph.sealed_toolchain import (
    SealedToolchainError,
    sealed_artifacts,
)


EXPECTED_TENANT_ID = "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
EXPECTED_SUBSCRIPTION_ID = "37cd9645-6cb9-4278-88ee-e80377cd951c"
EXPECTED_CLOUD_NAME = "AzureCloud"
FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS = 900
FUNCTION_DEPLOYMENT_PROCESS_TIMEOUT_SECONDS = 1020
AZURE_CLI_TOOLCHAIN_SHA256_ENV = "NAC_AZURE_CLI_EXPECTED_TOOLCHAIN_SHA256"
# Compatibility symbol for callers importing the former constant. The value now
# names the full toolchain attestation, never a wrapper-only digest.
AZURE_CLI_SHA256_ENV = AZURE_CLI_TOOLCHAIN_SHA256_ENV

# The isolated CLI used by the Azure activation lane is preferred over host tools.
AZURE_CLI_CANDIDATES = (
    Path("/tmp/nac-azure-cli-venv/bin/az"),
    Path("/usr/local/bin/az"),
    Path("/usr/bin/az"),
    Path("/opt/az/bin/az"),
)

ALLOWED_COMMAND_PREFIXES = (
    ("account", "show"),
    ("provider", "show"),
    ("provider", "register"),
    ("group", "exists"),
    ("group", "show"),
    ("group", "create"),
    ("deployment", "group", "create"),
    ("deployment", "group", "show"),
    ("deployment", "operation", "group", "list"),
    ("identity", "show"),
    ("functionapp", "identity", "show"),
    ("functionapp", "config", "appsettings", "set"),
    ("functionapp", "config", "appsettings", "list"),
    ("resource", "list"),
    ("resource", "show"),
    ("rest",),
    ("functionapp", "deployment", "source", "config-zip"),
)
INTERRUPTION_READ_COMMAND_PREFIXES = (
    ("account", "show"),
    ("provider", "show"),
    ("group", "exists"),
    ("group", "show"),
    ("resource", "list"),
    ("resource", "show"),
    ("rest",),
    ("deployment", "group", "show"),
    ("deployment", "operation", "group", "list"),
    ("identity", "show"),
    ("functionapp", "identity", "show"),
)

_PROVIDER_NAMESPACES = frozenset(
    {"Microsoft.Web", "Microsoft.Storage", "Microsoft.OperationalInsights"}
)
_DEPLOYMENT_NAME_RE = re.compile(r"nac-bff-[0-9a-f]{12}\Z")
_IDENTITY_NAME_RE = re.compile(r"id-nac-bff-test-[a-z0-9]+\Z")
_SMART_DETECTION_ACTION_GROUP_NAME = "Application Insights Smart Detection"
_SMART_DETECTION_ACTION_GROUP_TYPE = "Microsoft.Insights/ActionGroups"
_SMART_DETECTION_ACTION_GROUP_API_VERSION = "2021-09-01"
_RESOURCE_DETAIL_API_VERSIONS = {
    "microsoft.managedidentity/userassignedidentities": "2023-01-31",
    "microsoft.storage/storageaccounts": "2023-05-01",
    "microsoft.storage/storageaccounts/blobservices": "2023-05-01",
    "microsoft.storage/storageaccounts/blobservices/containers": "2023-05-01",
    "microsoft.operationalinsights/workspaces": "2023-09-01",
    "microsoft.insights/components": "2020-02-02",
    "microsoft.insights/components/currentbillingfeatures": "2015-05-01",
    "microsoft.web/serverfarms": "2024-04-01",
    "microsoft.web/sites": "2024-04-01",
    "microsoft.web/sites/config": "2024-04-01",
    "microsoft.authorization/roleassignments": "2022-04-01",
}
_STORAGE_BLOB_DATA_OWNER_ROLE_ID = "b7e6dc6d-f1e8-4753-8033-0f276bb0955b"
_MONITORING_METRICS_PUBLISHER_ROLE_ID = (
    "3913510d-42f4-4e42-8a64-420c390055eb"
)
_DEPLOYMENT_CONTAINER_NAME = "function-releases"
_CORS_ALLOWED_ORIGINS = [
    "https://funktion8.sharepoint.com",
    "https://teams.microsoft.com",
    "https://teams.cloud.microsoft",
]
_RESOURCE_GRAPH_URL = (
    "https://management.azure.com/providers/Microsoft.ResourceGraph/resources"
    "?api-version=2022-10-01"
)
_RESOURCE_GRAPH_SCOPE_PREFIX = (
    f"/subscriptions/{EXPECTED_SUBSCRIPTION_ID}/resourcegroups/{RESOURCE_GROUP}"
)
_RESOURCE_GRAPH_QUERY = (
    "Resources "
    f"| where subscriptionId =~ {json.dumps(EXPECTED_SUBSCRIPTION_ID)} "
    f"and resourceGroup =~ {json.dumps(RESOURCE_GROUP)} "
    "| project id, type "
    "| union (AuthorizationResources "
    f"| where subscriptionId =~ {json.dumps(EXPECTED_SUBSCRIPTION_ID)} "
    "| where tolower(tostring(properties.scope)) startswith "
    f"{json.dumps(_RESOURCE_GRAPH_SCOPE_PREFIX.lower())} "
    "| project id, type) "
    "| order by type asc, id asc"
)
_RESOURCE_GRAPH_BODY = json.dumps(
    {
        "subscriptions": [EXPECTED_SUBSCRIPTION_ID],
        "query": _RESOURCE_GRAPH_QUERY,
        "options": {"resultFormat": "objectArray"},
    },
    sort_keys=True,
    separators=(",", ":"),
)
_APP_SETTINGS_URL = (
    f"https://management.azure.com/subscriptions/{EXPECTED_SUBSCRIPTION_ID}"
    f"/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Web/sites/"
    f"{FUNCTION_APP}/config/appsettings/list?api-version=2024-04-01"
)
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z",
    re.IGNORECASE,
)

_ENV_ALLOWLIST = frozenset(
    {
        "AZURE_CONFIG_DIR",
        "HOME",
        "LANG",
        "LC_ALL",
        "PATH",
        "TMPDIR",
    }
)
_ACCOUNT_SHOW = ("account", "show")
_MAX_ARG_LENGTH = 16_384
_ATTESTATION_SCHEMA = "nac-azure-cli-toolchain-attestation-v1"
_PYTHON_NAME_RE = re.compile(r"python(?:\d+(?:\.\d+)*)?\Z")
_MAX_CLOUD_SELECTION_BYTES = 4096
_MAX_INTERPRETER_LINKS = 8
_FILE_CHUNK_SIZE = 1024 * 1024
_MONITOR_EXECUTION_AUTHORITY = object()
_PERFORMANCE_INFRASTRUCTURE_REST_AUTHORITY = object()

_PERFORMANCE_BROKER_SETTING_NAMES = frozenset(
    {
        "NAC_BFF_PERFORMANCE_LEASE_ENABLED",
        "NAC_BFF_PERFORMANCE_LEASE_TENANT_ID",
        "NAC_BFF_PERFORMANCE_LEASE_ACTOR_ID",
        "NAC_BFF_PERFORMANCE_LEASE_OWNER_SUBJECT",
        "NAC_BFF_PERFORMANCE_LEASE_OWNER_BINDING_SHA256",
        "NAC_BFF_PERFORMANCE_LEASE_COMMIT_SHA",
        "NAC_BFF_PERFORMANCE_LEASE_TREE_SHA",
        "NAC_BFF_PERFORMANCE_LEASE_FUNCTION_PACKAGE_SHA256",
        "NAC_BFF_PERFORMANCE_LEASE_PLAN_SHA256",
        "NAC_BFF_PERFORMANCE_LEASE_TARGET_BINDING_SHA256",
        "NAC_BFF_PERFORMANCE_LEASE_BLOB_PATH",
        "NAC_BFF_PERFORMANCE_LEASE_BLOB_URL",
        "NAC_BFF_PERFORMANCE_LEASE_STORAGE_BINDING_ID",
        "NAC_BFF_PERFORMANCE_LEASE_STORAGE_ATTESTATION_B64",
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_ISSUER",
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_KEY_ID",
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_B64",
        "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_SHA256",
    }
)


class AzureCliAdapter:
    """Fail-closed process boundary for the owner-gated Azure BFF runner."""

    def __init__(
        self,
        *,
        binary: str | os.PathLike[str] | None = None,
        expected_binary_sha256: str | None = None,
        environ: Mapping[str, str] | None = None,
        timeout_seconds: float = 120,
    ) -> None:
        self._binary = binary
        self._expected_binary_sha256 = expected_binary_sha256
        self._environ = None if environ is None else dict(environ)
        self._timeout_seconds = timeout_seconds

    def run(self, argv: object) -> dict[str, object]:
        return run_azure_cli(
            argv,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=self._timeout_seconds,
        )

    def run_monitor_metrics(
        self,
        argv: object,
        *,
        live_action_capability: object,
        target_binding_sha256: str,
    ) -> dict[str, object]:
        command, family, _code = _validated_command(argv)
        if (
            command is None
            or family != ("rest",)
            or not _is_monitor_metrics_command(command)
        ):
            return _command_result(
                ok=False,
                code="AZURE_CLI_COMMAND_BLOCKED",
                command=None,
            )
        _authorize_monitor_metrics(
            live_action_capability,
            target_binding_sha256=target_binding_sha256,
        )
        return _run_azure_cli(
            command,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=self._timeout_seconds,
            _monitor_execution_authority=_MONITOR_EXECUTION_AUTHORITY,
        )

    def execute_exact_rest(self, command: object) -> dict[str, object]:
        """Execute one sealed, read-only performance-infrastructure ARM GET."""

        from .azure_performance_infrastructure_ports import BoundAzureCliCommand

        if type(command) is not BoundAzureCliCommand:
            return _command_result(
                ok=False,
                code="AZURE_CLI_COMMAND_BLOCKED",
                command=None,
            )
        try:
            command._assert_issued()
        except Exception:
            return _command_result(
                ok=False,
                code="AZURE_CLI_COMMAND_BLOCKED",
                command=None,
            )
        if (
            not command.read_only
            or command.artifacts
            or command.argv[:1] != ("rest",)
        ):
            return _command_result(
                ok=False,
                code="AZURE_CLI_COMMAND_BLOCKED",
                command=None,
            )
        return _run_azure_cli(
            command.argv,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=command.timeout_seconds,
            _performance_infrastructure_command=command,
            _performance_infrastructure_rest_authority=(
                _PERFORMANCE_INFRASTRUCTURE_REST_AUTHORITY
            ),
        )

    def run_with_timeout(
        self,
        argv: object,
        *,
        timeout_seconds: float,
    ) -> dict[str, object]:
        return run_azure_cli(
            argv,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=timeout_seconds,
        )

    def run_bound(
        self,
        argv: object,
        bound_artifacts: Mapping[str, tuple[Path, str]],
    ) -> dict[str, object]:
        return run_azure_cli(
            argv,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=self._timeout_seconds,
            bound_artifacts=bound_artifacts,
        )

    def run_bound_with_timeout(
        self,
        argv: object,
        bound_artifacts: Mapping[str, tuple[Path, str]],
        *,
        timeout_seconds: float,
    ) -> dict[str, object]:
        return run_azure_cli(
            argv,
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=timeout_seconds,
            bound_artifacts=bound_artifacts,
        )

    def check_readiness(self) -> dict[str, object]:
        return check_azure_cli_readiness(
            binary=self._binary,
            expected_binary_sha256=self._expected_binary_sha256,
            environ=self._environ,
            timeout_seconds=self._timeout_seconds,
        )


class AzureCliInterruptionObservationPort:
    """Expose only the stable Azure reads required for step-2 reconciliation."""

    def __init__(
        self, azure: AzureCliAdapter, *, preflight: Callable[[], None]
    ) -> None:
        self._azure = azure
        self._preflight = preflight

    def observe_ensure_resource_group(
        self,
        *,
        tenant_id: str,
        subscription_id: str,
        resource_group: str,
        baseline_expectation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if (
            tenant_id != EXPECTED_TENANT_ID
            or subscription_id != EXPECTED_SUBSCRIPTION_ID
            or resource_group != RESOURCE_GROUP
        ):
            raise ValueError("AZURE_INTERRUPTION_TARGET_MISMATCH")

        account = self._read(("account", "show"), dict)
        if (
            account.get("environmentName") != EXPECTED_CLOUD_NAME
            or account.get("tenantId") != tenant_id
            or account.get("id") != subscription_id
            or account.get("state") != "Enabled"
        ):
            raise ValueError("AZURE_INTERRUPTION_ACCOUNT_MISMATCH")

        providers: dict[str, str] = {}
        for namespace in sorted(_PROVIDER_NAMESPACES):
            provider = self._read(
                ("provider", "show", "--namespace", namespace), dict
            )
            registration_state = provider.get("registrationState")
            if (
                provider.get("namespace") != namespace
                or not isinstance(registration_state, str)
            ):
                raise ValueError("AZURE_INTERRUPTION_PROVIDER_INVALID")
            providers[namespace] = registration_state

        exists = self._read(
            ("group", "exists", "--name", resource_group), bool
        )
        if exists is not True:
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_GROUP_MISSING")
        group = self._read(("group", "show", "--name", resource_group), dict)
        properties = group.get("properties")
        tags = group.get("tags")
        expected_group_id = (
            f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
        )
        if (
            group.get("id") != expected_group_id
            or group.get("name") != resource_group
            or group.get("location") != LOCATION
            or not isinstance(properties, dict)
            or not isinstance(properties.get("provisioningState"), str)
            or not isinstance(tags, dict)
            or set(tags) != {
                "dataClassification", "environment", "workload"
            }
            or any(not isinstance(value, str) for value in tags.values())
        ):
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_GROUP_INVALID")

        raw_inventory = self._read(
            ("resource", "list", "--resource-group", resource_group), list
        )
        legacy_result = {
            "tenant_id": tenant_id,
            "subscription_id": subscription_id,
            "providers": providers,
            "resource_groups": [
                {
                    "id": expected_group_id,
                    "name": resource_group,
                    "location": group["location"],
                    "provisioning_state": properties["provisioningState"],
                    "tags": {key: tags[key] for key in sorted(tags)},
                }
            ],
            "resource_inventory": [],
        }
        if not raw_inventory:
            return legacy_result
        result = {
            **legacy_result,
            "provider_classification": BICEP_BASELINE_EXACT,
            "deployment": None,
            "deployment_operations": [],
            "identity_binding": None,
            "live_resource_state": None,
            "baseline_expectation_sha256": None,
        }
        if baseline_expectation is None:
            raise ValueError("AZURE_INTERRUPTION_BASELINE_BINDING_MISSING")
        deployment_name = baseline_expectation.get("deployment_name")
        if not isinstance(deployment_name, str):
            raise ValueError("AZURE_INTERRUPTION_BASELINE_BINDING_INVALID")
        deployment = self._read(
            (
                "deployment", "group", "show", "--name", deployment_name,
                "--resource-group", resource_group,
            ),
            dict,
        )
        operations = self._read(
            (
                "deployment", "operation", "group", "list",
                "--name", deployment_name,
                "--resource-group", resource_group,
            ),
            list,
        )
        smart_detail = self._read(
            (
                "resource", "show",
                "--resource-group", resource_group,
                "--resource-type", _SMART_DETECTION_ACTION_GROUP_TYPE,
                "--name", _SMART_DETECTION_ACTION_GROUP_NAME,
                "--api-version", _SMART_DETECTION_ACTION_GROUP_API_VERSION,
            ),
            dict,
        )
        inventory = _interruption_inventory_projection(
            raw_inventory, smart_detail=smart_detail
        )
        identities = [
            item
            for item in inventory
            if item["type"]
            == "microsoft.managedidentity/userassignedidentities"
        ]
        if len(identities) != 1:
            raise ValueError("AZURE_INTERRUPTION_IDENTITY_INVALID")
        managed_identity = self._read(
            (
                "identity", "show",
                "--name", str(identities[0]["name"]),
                "--resource-group", resource_group,
            ),
            dict,
        )
        function_identity = self._read(
            (
                "functionapp", "identity", "show",
                "--name", FUNCTION_APP,
                "--resource-group", resource_group,
            ),
            dict,
        )
        projected_operations = _interruption_operation_projection(operations)
        resource_details = []
        for operation in projected_operations:
            detail = self._read(_resource_detail_read_command(operation), dict)
            if operation["type"] == "microsoft.web/sites/config":
                detail = {
                    "id": operation["id"],
                    "type": operation["type"],
                    "properties": detail.get("properties"),
                }
            resource_details.append(detail)
        projected_deployment = _interruption_deployment_projection(deployment)
        projected_identity = _interruption_identity_projection(
            managed_identity, function_identity
        )
        resource_graph = self._read(
            (
                "rest", "--method", "post",
                "--url", _RESOURCE_GRAPH_URL,
                "--body", _RESOURCE_GRAPH_BODY,
            ),
            dict,
        )
        live_resource_state = _interruption_live_resource_state(
            resource_details,
            projected_operations,
            inventory,
            projected_deployment,
            projected_identity,
            _resource_graph_projection(resource_graph),
        )
        repeated_inventory = self._read(
            ("resource", "list", "--resource-group", resource_group), list
        )
        repeated_smart_detail = self._read(
            (
                "resource", "show",
                "--resource-group", resource_group,
                "--resource-type", _SMART_DETECTION_ACTION_GROUP_TYPE,
                "--name", _SMART_DETECTION_ACTION_GROUP_NAME,
                "--api-version", _SMART_DETECTION_ACTION_GROUP_API_VERSION,
            ),
            dict,
        )
        if inventory != _interruption_inventory_projection(
            repeated_inventory, smart_detail=repeated_smart_detail
        ):
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_INVENTORY_CHANGED")
        result.update({
            "resource_inventory": inventory,
            "deployment": projected_deployment,
            "deployment_operations": projected_operations,
            "identity_binding": projected_identity,
            "live_resource_state": live_resource_state,
            "baseline_expectation_sha256": newline_sha256_json(
                baseline_expectation
            ),
        })
        return result

    def _read(self, argv: tuple[str, ...], expected_type: type) -> Any:
        if not any(
            argv[: len(prefix)] == prefix
            for prefix in INTERRUPTION_READ_COMMAND_PREFIXES
        ):
            raise ValueError("AZURE_INTERRUPTION_READ_COMMAND_FORBIDDEN")
        self._preflight()
        result = self._azure.run(argv)
        if not isinstance(result, dict):
            raise ValueError("AZURE_INTERRUPTION_READ_FAILED")
        value = result.get("data")
        if result.get("ok") is not True or type(value) is not expected_type:
            raise ValueError("AZURE_INTERRUPTION_READ_FAILED")
        return value


def _interruption_inventory_projection(
    value: list[Any], *, smart_detail: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    projected: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_INVALID")
        smart = (
            str(item.get("type", "")).lower()
            == _SMART_DETECTION_ACTION_GROUP_TYPE.lower()
            and item.get("name") == _SMART_DETECTION_ACTION_GROUP_NAME
        )
        source = smart_detail if smart and smart_detail is not None else item
        sku = source.get("sku")
        tags = source.get("tags")
        projected.append({
            "id": source.get("id"),
            "name": source.get("name"),
            "type": str(source.get("type", "")).lower(),
            "resource_group": source.get("resourceGroup"),
            "location": str(source.get("location", "")).lower(),
            "kind": source.get("kind"),
            "sku": (
                {key: sku.get(key) for key in ("name", "tier")}
                if isinstance(sku, dict)
                else None
            ),
            "tags": (
                {key: tags[key] for key in sorted(tags)}
                if isinstance(tags, dict)
                else None
            ),
            "managed_by": source.get("managedBy"),
            "properties": source.get("properties") if smart else None,
        })
    return sorted(
        projected,
        key=lambda item: (str(item["type"]), str(item["name"])),
    )



def _resource_detail_read_command(
    operation: dict[str, Any],
) -> tuple[str, ...]:
    if operation["type"] == "microsoft.web/sites/config":
        return ("rest", "--method", "post", "--url", _APP_SETTINGS_URL)
    return (
        "resource", "show",
        "--ids", operation["id"],
        "--api-version", _RESOURCE_DETAIL_API_VERSIONS[operation["type"]],
    )


def _resource_graph_projection(value: dict[str, Any]) -> list[dict[str, str]]:
    allowed = {
        "count", "data", "facets", "resultTruncated",
        "skipToken", "totalRecords",
    }
    if set(value) - allowed:
        raise ValueError("AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID")
    rows = value.get("data")
    count = value.get("count")
    total_records = value.get("totalRecords")
    result_truncated = value.get("resultTruncated")
    skip_token = value.get("skipToken")
    if (
        not isinstance(rows, list)
        or type(count) is not int
        or type(total_records) is not int
        or count != len(rows)
        or total_records != len(rows)
        or result_truncated not in (False, "false")
        or ("skipToken" in value and skip_token not in (None, ""))
        or ("facets" in value and not isinstance(value["facets"], list))
    ):
        raise ValueError("AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID")
    projected: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "type"}:
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID")
        resource_id = row.get("id")
        resource_type = row.get("type")
        if not isinstance(resource_id, str) or not isinstance(resource_type, str):
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID")
        lowered_id = resource_id.lower()
        lowered_type = resource_type.lower()
        if (
            not lowered_id.startswith(_RESOURCE_GRAPH_SCOPE_PREFIX.lower() + "/")
            or lowered_id in seen
        ):
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID")
        seen.add(lowered_id)
        projected.append({"id": lowered_id, "type": lowered_type})
    return sorted(projected, key=lambda item: (item["type"], item["id"]))

def _interruption_live_resource_state(
    details: list[dict[str, Any]],
    operations: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
    deployment: dict[str, Any],
    identity_binding: dict[str, Any],
    resource_graph: list[dict[str, str]],
) -> dict[str, Any]:
    if len(details) != 12 or len(operations) != 12:
        raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")
    _require_exact_resource_graph(resource_graph, inventory, operations)
    actual_graph = [
        (item["id"], item["type"])
        for item in resource_graph
    ]

    targets = sorted(
        ({"id": item["id"].lower(), "type": item["type"]}
         for item in operations),
        key=lambda item: (item["type"], item["id"]),
    )
    detail_by_id: dict[str, dict[str, Any]] = {}
    for detail in details:
        if not isinstance(detail, dict) or not isinstance(detail.get("id"), str):
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")
        resource_id = detail["id"].lower()
        if resource_id in detail_by_id:
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")
        detail_by_id[resource_id] = detail
    if set(detail_by_id) != {item["id"] for item in targets}:
        raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")

    inventory_by_type = {item["type"]: item for item in inventory}
    operations_by_id = {item["id"].lower(): item for item in operations}
    managed = identity_binding["managed_identity"]
    client_id = managed["client_id"]
    principal_id = managed["principal_id"]
    tenant_id = managed["tenant_id"]
    storage = inventory_by_type["microsoft.storage/storageaccounts"]
    workspace = inventory_by_type["microsoft.operationalinsights/workspaces"]
    component = inventory_by_type["microsoft.insights/components"]
    plan = inventory_by_type["microsoft.web/serverfarms"]
    site = inventory_by_type["microsoft.web/sites"]
    component_detail = detail_by_id[component["id"].lower()]
    component_properties = _required_properties(component_detail)
    connection_string = component_properties.get("ConnectionString")
    if not isinstance(connection_string, str) or not connection_string:
        raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")

    for target in targets:
        detail = detail_by_id[target["id"]]
        resource_type = target["type"]
        if (
            str(detail.get("type", "")).lower() != resource_type
            or operations_by_id[target["id"]]["type"] != resource_type
        ):
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")
        properties = _required_properties(detail)
        if resource_type == "microsoft.managedidentity/userassignedidentities":
            valid = _security_projection_matches(properties, {
                "clientId": client_id,
                "principalId": principal_id,
                "tenantId": tenant_id,
            })
        elif resource_type == "microsoft.storage/storageaccounts":
            valid = _security_projection_matches(properties, {
                "accessTier": "Hot",
                "allowBlobPublicAccess": False,
                "allowCrossTenantReplication": False,
                "allowSharedKeyAccess": False,
                "defaultToOAuthAuthentication": True,
                "minimumTlsVersion": "TLS1_2",
                "publicNetworkAccess": "Enabled",
                "supportsHttpsTrafficOnly": True,
                "networkAcls": {
                    "bypass": "None",
                    "defaultAction": "Allow",
                    "ipRules": [],
                    "virtualNetworkRules": [],
                },
            })
        elif resource_type == "microsoft.storage/storageaccounts/blobservices":
            valid = _security_projection_matches(properties, {
                "deleteRetentionPolicy": {"enabled": False}
            })
        elif resource_type == "microsoft.storage/storageaccounts/blobservices/containers":
            valid = _security_projection_matches(
                properties, {"publicAccess": "None"}
            )
        elif resource_type == "microsoft.operationalinsights/workspaces":
            valid = _security_projection_matches(properties, {
                "features": {
                    "disableLocalAuth": True,
                    "enableLogAccessUsingOnlyResourcePermissions": True,
                    "immediatePurgeDataOn30Days": True,
                },
                "publicNetworkAccessForIngestion": "Enabled",
                "publicNetworkAccessForQuery": "Enabled",
                "retentionInDays": 30,
                "sku": {"name": "PerGB2018"},
                "workspaceCapping": {"dailyQuotaGb": 1},
            })
        elif resource_type == "microsoft.insights/components":
            valid = _security_projection_matches(properties, {
                "Application_Type": "web",
                "ConnectionString": connection_string,
                "DisableLocalAuth": True,
                "IngestionMode": "LogAnalytics",
                "RetentionInDays": 30,
                "WorkspaceResourceId": workspace["id"],
                "publicNetworkAccessForIngestion": "Enabled",
                "publicNetworkAccessForQuery": "Enabled",
            })
        elif resource_type == "microsoft.insights/components/currentbillingfeatures":
            valid = _security_projection_matches(properties, {
                "CurrentBillingFeatures": ["Basic"],
                "DataVolumeCap": {
                    "Cap": 0.1,
                    "StopSendNotificationWhenHitCap": False,
                },
            })
        elif resource_type == "microsoft.web/serverfarms":
            valid = _security_projection_matches(properties, {
                "reserved": True, "zoneRedundant": False
            })
        elif resource_type == "microsoft.web/sites":
            valid = _function_site_state_matches(
                properties, storage, plan, managed
            )
        elif resource_type == "microsoft.web/sites/config":
            valid = properties == {
                "APPLICATIONINSIGHTS_AUTHENTICATION_STRING": (
                    f"ClientId={client_id};Authorization=AAD"
                ),
                "APPLICATIONINSIGHTS_CONNECTION_STRING": connection_string,
                "AzureWebJobsStorage__accountName": storage["name"],
                "AzureWebJobsStorage__clientId": client_id,
                "AzureWebJobsStorage__credential": "managedidentity",
                "M365_TENANT_ID": tenant_id,
                "NAC_BFF_TENANT_ID": tenant_id,
                "NAC_BFF_AUDIENCE": deployment["bff_api_audience"],
                "NAC_BFF_REQUIRED_SCOPE": "Matter.Read",
                "M365_RUNTIME_CLIENT_ID": client_id,
                "AZURE_CLIENT_ID": client_id,
            }
        elif resource_type == "microsoft.authorization/roleassignments":
            role_id = (
                _STORAGE_BLOB_DATA_OWNER_ROLE_ID
                if target["id"].startswith(storage["id"].lower() + "/")
                else _MONITORING_METRICS_PUBLISHER_ROLE_ID
                if target["id"].startswith(component["id"].lower() + "/")
                else None
            )
            valid = role_id is not None and _security_projection_matches(
                properties,
                {
                    "principalId": principal_id,
                    "principalType": "ServicePrincipal",
                    "roleDefinitionId": (
                        f"/subscriptions/{EXPECTED_SUBSCRIPTION_ID}"
                        f"/providers/Microsoft.Authorization/roleDefinitions/{role_id}"
                    ),
                },
            )
        else:
            valid = False
        if not valid:
            raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")

    return {
        "schema_version": "nac.azure-interruption-live-resource-state/v1",
        "resource_count": len(targets),
        "resource_targets_sha256": compact_sha256_json(targets),
        "resource_graph_count": len(resource_graph),
        "resource_graph_targets_sha256": compact_sha256_json([
            {"id": resource_id, "type": resource_type}
            for resource_id, resource_type in actual_graph
        ]),
        "security_properties_exact": True,
    }


def _require_exact_resource_graph(
    resource_graph: list[dict[str, str]],
    inventory: list[dict[str, Any]],
    operations: list[dict[str, Any]],
) -> None:
    expected = resource_graph_visible_targets(inventory, operations)
    if expected is None or resource_graph != expected:
        raise ValueError("AZURE_INTERRUPTION_RESOURCE_GRAPH_INVALID")


def _required_properties(value: dict[str, Any]) -> dict[str, Any]:
    properties = value.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("AZURE_INTERRUPTION_RESOURCE_STATE_INVALID")
    return properties


def _security_projection_matches(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        return bool(
            isinstance(actual, dict)
            and all(
                key in actual
                and _security_projection_matches(actual[key], value)
                for key, value in expected.items()
            )
        )
    return actual == expected


def _function_site_state_matches(
    properties: dict[str, Any],
    storage: dict[str, Any],
    plan: dict[str, Any],
    managed: dict[str, Any],
) -> bool:
    expected_storage_uri = (
        f"https://{storage['name']}.blob.core.windows.net/"
        f"{_DEPLOYMENT_CONTAINER_NAME}"
    )
    return _security_projection_matches(properties, {
        "clientAffinityEnabled": False,
        "httpsOnly": True,
        "publicNetworkAccess": "Enabled",
        "serverFarmId": plan["id"],
        "siteConfig": {
            "alwaysOn": False,
            "cors": {
                "allowedOrigins": _CORS_ALLOWED_ORIGINS,
                "supportCredentials": False,
            },
            "ftpsState": "Disabled",
            "healthCheckPath": "/healthz",
            "http20Enabled": True,
            "minTlsVersion": "1.2",
            "remoteDebuggingEnabled": False,
        },
        "functionAppConfig": {
            "deployment": {
                "storage": {
                    "authentication": {
                        "type": "UserAssignedIdentity",
                        "userAssignedIdentityResourceId": managed["id"],
                    },
                    "type": "blobContainer",
                    "value": expected_storage_uri,
                }
            },
            "runtime": {"name": "python", "version": "3.12"},
            "scaleAndConcurrency": {
                "instanceMemoryMB": 2048,
                "maximumInstanceCount": 4,
                "triggers": {"http": {"perInstanceConcurrency": 16}},
            },
        },
    })


def _interruption_deployment_projection(value: dict[str, Any]) -> dict[str, Any]:
    properties = value.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("AZURE_INTERRUPTION_DEPLOYMENT_INVALID")
    parameters = properties.get("parameters")
    outputs = properties.get("outputs")
    if not isinstance(parameters, dict) or not isinstance(outputs, dict):
        raise ValueError("AZURE_INTERRUPTION_DEPLOYMENT_INVALID")
    try:
        canonical_parameters = canonical_parameters_from_wrappers(parameters)
        projected_outputs = {
            "function_app_resource_id": _interruption_output(
                outputs, "functionAppResourceId"
            ),
            "function_app_host_name": _interruption_output(
                outputs, "functionAppHostName"
            ),
            "function_app_system_assigned_principal_id": _interruption_output(
                outputs, "functionAppSystemAssignedPrincipalId"
            ),
            "managed_identity_resource_id": _interruption_output(
                outputs, "managedIdentityResourceId"
            ),
            "managed_identity_client_id": _interruption_output(
                outputs, "managedIdentityClientId"
            ),
            "managed_identity_principal_id": _interruption_output(
                outputs, "managedIdentityPrincipalId"
            ),
        }
    except (KeyError, TypeError, ValueError):
        raise ValueError("AZURE_INTERRUPTION_DEPLOYMENT_INVALID") from None
    return {
        "name": value.get("name"),
        "resource_group": value.get("resourceGroup"),
        "provisioning_state": properties.get("provisioningState"),
        "mode": properties.get("mode"),
        "template_hash": str(properties.get("templateHash", "")),
        "parameters_sha256": compact_sha256_json(
            canonical_parameters
        ),
        "bff_api_audience": str(
            canonical_parameters["bffApiAudience"]["value"]
        ).lower(),
        "outputs": projected_outputs,
    }


def _interruption_output(outputs: dict[str, Any], key: str) -> Any:
    wrapper = outputs[key]
    if not isinstance(wrapper, dict) or set(wrapper) != {"type", "value"}:
        raise ValueError("deployment output wrapper invalid")
    return wrapper["value"]


def _interruption_identity_projection(
    managed_identity: dict[str, Any],
    function_identity: dict[str, Any],
) -> dict[str, Any]:
    assignments = function_identity.get("userAssignedIdentities")
    if not isinstance(assignments, dict):
        raise ValueError("AZURE_INTERRUPTION_IDENTITY_INVALID")
    projected_assignments: list[dict[str, Any]] = []
    for resource_id, binding in assignments.items():
        if not isinstance(resource_id, str) or not isinstance(binding, dict):
            raise ValueError("AZURE_INTERRUPTION_IDENTITY_INVALID")
        projected_assignments.append({
            "id": resource_id,
            "client_id": binding.get("clientId"),
            "principal_id": binding.get("principalId"),
        })
    return {
        "managed_identity": {
            "id": managed_identity.get("id"),
            "name": managed_identity.get("name"),
            "client_id": managed_identity.get("clientId"),
            "principal_id": managed_identity.get("principalId"),
            "tenant_id": managed_identity.get("tenantId"),
        },
        "function_app": {
            "type": function_identity.get("type"),
            "system_assigned_principal_id": function_identity.get("principalId"),
            "user_assigned_identities": sorted(
                projected_assignments, key=lambda item: item["id"].lower()
            ),
        },
    }


def _interruption_operation_projection(value: list[Any]) -> list[dict[str, str]]:
    projected: dict[tuple[str, str], dict[str, str]] = {}
    output_evaluation_seen = False
    for item in value:
        properties = item.get("properties") if isinstance(item, dict) else None
        if not isinstance(properties, dict):
            raise ValueError("AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID")
        target = properties.get("targetResource")
        if not isinstance(target, dict):
            if (
                target is not None
                or output_evaluation_seen
                or properties.get("provisioningOperation")
                != "EvaluateDeploymentOutput"
                or properties.get("provisioningState") != "Succeeded"
                or properties.get("statusCode") != "OK"
            ):
                raise ValueError(
                    "AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID"
                )
            output_evaluation_seen = True
            continue
        resource_id = target.get("id")
        resource_type = target.get("resourceType")
        if (
            not isinstance(resource_id, str)
            or not resource_id
            or not isinstance(resource_type, str)
            or not resource_type
        ):
            raise ValueError("AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID")
        operation = {
            "id": resource_id.lower(),
            "type": resource_type.lower(),
            "provisioning_state": properties.get("provisioningState"),
        }
        if (
            not operation["id"]
            or not operation["type"]
            or operation["provisioning_state"] != "Succeeded"
        ):
            raise ValueError("AZURE_INTERRUPTION_DEPLOYMENT_OPERATION_INVALID")
        key = (operation["id"], operation["type"])
        projected[key] = operation
    return sorted(projected.values(), key=lambda item: (item["type"], item["id"]))


def resolve_azure_cli_binary(
    explicit: str | os.PathLike[str] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
    expected_sha256: str | None = None,
) -> Path | None:
    """Resolve az only across an absolute, locally trusted runtime boundary."""

    expected_sha256 = _runtime_expected_sha256(expected_sha256, environ)
    if explicit is not None:
        try:
            explicit_path = Path(explicit).expanduser()
        except TypeError:
            return None
        resolved, _code = _executable_path(explicit_path, expected_sha256=expected_sha256)
        return resolved

    for candidate in AZURE_CLI_CANDIDATES:
        resolved, _code = _executable_path(candidate, expected_sha256=expected_sha256)
        if resolved is not None:
            return resolved
    return None


def build_azure_cli_env(
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Copy only non-credential settings needed by the local Azure CLI."""

    source = os.environ if environ is None else environ
    child = {
        key: value
        for key, value in source.items()
        if key in _ENV_ALLOWLIST and isinstance(value, str) and value
    }
    child["PATH"] = "/usr/bin:/bin"
    child["AZURE_CORE_COLLECT_TELEMETRY"] = "0"
    child["AZURE_CORE_NO_COLOR"] = "true"
    child["PYTHONDONTWRITEBYTECODE"] = "1"
    child["PYTHONNOUSERSITE"] = "1"
    child["PYTHONSAFEPATH"] = "1"
    return child


def run_azure_cli(
    argv: object,
    *,
    binary: str | os.PathLike[str] | None = None,
    expected_binary_sha256: str | None = None,
    environ: Mapping[str, str] | None = None,
    timeout_seconds: float = 120,
    bound_artifacts: Mapping[str, tuple[Path, str]] | None = None,
) -> dict[str, object]:
    """Run one allowlisted Azure CLI command and return parsed JSON only."""

    return _run_azure_cli(
        argv,
        binary=binary,
        expected_binary_sha256=expected_binary_sha256,
        environ=environ,
        timeout_seconds=timeout_seconds,
        bound_artifacts=bound_artifacts,
    )


def _run_azure_cli(
    argv: object,
    *,
    binary: str | os.PathLike[str] | None = None,
    expected_binary_sha256: str | None = None,
    environ: Mapping[str, str] | None = None,
    timeout_seconds: float = 120,
    bound_artifacts: Mapping[str, tuple[Path, str]] | None = None,
    _monitor_execution_authority: object | None = None,
    _performance_infrastructure_command: object | None = None,
    _performance_infrastructure_rest_authority: object | None = None,
) -> dict[str, object]:
    """Internal executor; Monitor authority is not exposed by the public API."""

    if (
        _performance_infrastructure_rest_authority
        is _PERFORMANCE_INFRASTRUCTURE_REST_AUTHORITY
    ):
        from .azure_performance_infrastructure_ports import BoundAzureCliCommand

        candidate = _performance_infrastructure_command
        try:
            if type(candidate) is not BoundAzureCliCommand:
                raise ValueError
            candidate._assert_issued()
            if (
                not candidate.read_only
                or candidate.artifacts
                or candidate.argv != tuple(argv)
                or candidate.argv[:1] != ("rest",)
            ):
                raise ValueError
            command = tuple(candidate.argv)
            family = ("rest",)
            validation_code = "AZURE_CLI_OK"
        except Exception:
            command = None
            family = None
            validation_code = "AZURE_CLI_COMMAND_BLOCKED"
    else:
        command, family, validation_code = _validated_command(argv)
    if command is None or family is None:
        return _command_result(
            ok=False,
            code=validation_code,
            command=None,
        )
    if (
        _is_monitor_metrics_command(command)
        and _monitor_execution_authority is not _MONITOR_EXECUTION_AUTHORITY
    ):
        return _command_result(
            ok=False,
            code="AZURE_CLI_COMMAND_BLOCKED",
            command=family,
        )

    bindings = tuple((bound_artifacts or {}).items())
    if any(
        sum(
            token == argument or token == f"@{argument}"
            for token in command
        ) != 1
        for argument, _ in bindings
    ):
        return _command_result(
            ok=False,
            code="AZURE_CLI_ARTIFACT_BINDING_INVALID",
            command=family,
        )

    cloud_config_code, cloud_selection_sha256 = _azure_cloud_config_boundary(
        environ
    )
    if cloud_config_code is not None:
        return _command_result(
            ok=False,
            code=cloud_config_code,
            command=family,
        )

    resolved_binary, binary_code = _resolve_azure_cli_binary(
        binary,
        environ=environ,
        expected_sha256=expected_binary_sha256,
    )
    if resolved_binary is None:
        return _command_result(
            ok=False,
            code=binary_code,
            command=family,
        )
    if (
        not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or timeout_seconds <= 0
    ):
        return _command_result(
            ok=False,
            code="AZURE_CLI_TIMEOUT_INVALID",
            command=family,
        )

    azure_argv = [*command]
    if not any(
        token == "--subscription" or token.startswith("--subscription=")
        for token in command
    ):
        azure_argv.extend(["--subscription", EXPECTED_SUBSCRIPTION_ID])
    azure_argv.extend(["--output", "json", "--only-show-errors"])

    # Resolve performs the preflight attestation. Re-attest immediately before
    # process creation so wrapper, interpreter, venv and packages cannot change
    # unnoticed between readiness and execution.
    expected_attestation = _runtime_expected_sha256(
        expected_binary_sha256,
        environ,
    )
    rechecked_binary, recheck_code = _executable_path(
        resolved_binary,
        expected_sha256=expected_attestation,
    )
    if rechecked_binary != resolved_binary:
        return _command_result(
            ok=False,
            code=recheck_code,
            command=family,
        )

    runtime = _prepare_bound_runtime(
        resolved_binary,
        expected_sha256=expected_attestation,
        cloud_selection_sha256=cloud_selection_sha256,
    )
    if runtime is None:
        return _command_result(
            ok=False,
            code="AZURE_CLI_RUNTIME_BINDING_FAILED",
            command=family,
        )

    try:
        with ExitStack() as stack:
            stack.enter_context(runtime)
            artifact_sealed = stack.enter_context(
                sealed_artifacts(
                    tuple(
                        (path, expected_sha256)
                        for _, (path, expected_sha256) in bindings
                    )
                )
            ) if bindings else None
            replacements = {
                argument: artifact_sealed.paths[index]
                for index, (argument, _) in enumerate(bindings)
            } if artifact_sealed is not None else {}
            bound_argv = [
                (
                    f"@{replacements[token[1:]]}"
                    if token.startswith("@") and token[1:] in replacements
                    else replacements.get(token, token)
                )
                for token in azure_argv
            ]
            artifact_fds = (
                artifact_sealed.pass_fds
                if artifact_sealed is not None
                else ()
            )
            completed = subprocess.run(
                runtime.command(bound_argv),
                check=False,
                capture_output=True,
                text=True,
                shell=False,
                stdin=subprocess.DEVNULL,
                timeout=timeout_seconds,
                env=build_azure_cli_env(environ),
                pass_fds=runtime.pass_fds + artifact_fds,
            )
    except SealedToolchainError:
        return _command_result(
            ok=False,
            code="AZURE_CLI_ARTIFACT_BINDING_FAILED",
            command=family,
        )
    except subprocess.TimeoutExpired:
        return _command_result(
            ok=False,
            code="AZURE_CLI_TIMEOUT",
            command=family,
        )
    except (OSError, subprocess.SubprocessError):
        return _command_result(
            ok=False,
            code="AZURE_CLI_EXECUTION_FAILED",
            command=family,
        )

    if completed.returncode != 0:
        runtime_code = sealed_runtime_failure_code(completed.returncode)
        return _command_result(
            ok=False,
            code=runtime_code or "AZURE_CLI_COMMAND_FAILED",
            command=family,
            returncode=completed.returncode,
        )

    if (
        family == ("provider", "register")
        and isinstance(completed.stdout, str)
        and not completed.stdout.strip()
    ):
        data = {}
    else:
        try:
            data = json.loads(
                completed.stdout, object_pairs_hook=_unique_json_object
            )
        except (TypeError, ValueError):
            return _command_result(
                ok=False,
                code="AZURE_CLI_OUTPUT_INVALID",
                command=family,
                returncode=completed.returncode,
            )
    return _command_result(
        ok=True,
        code="AZURE_CLI_OK",
        command=family,
        returncode=completed.returncode,
        data=data,
    )


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def check_azure_cli_readiness(
    *,
    binary: str | os.PathLike[str] | None = None,
    expected_binary_sha256: str | None = None,
    environ: Mapping[str, str] | None = None,
    timeout_seconds: float = 30,
) -> dict[str, object]:
    """Verify the active Azure account is the one fixed by the activation plan."""

    resolved_binary, binary_code = _resolve_azure_cli_binary(
        binary,
        environ=environ,
        expected_sha256=expected_binary_sha256,
    )
    if resolved_binary is None:
        return _readiness_result(
            code=binary_code,
            binary_ready=False,
            account_ready=False,
            tenant_ready=False,
            subscription_ready=False,
        )

    account_result = run_azure_cli(
        ["account", "show"],
        binary=resolved_binary,
        expected_binary_sha256=expected_binary_sha256,
        environ=environ,
        timeout_seconds=timeout_seconds,
    )
    if not account_result["ok"]:
        return _readiness_result(
            code=str(account_result["code"]),
            binary_ready=True,
            account_ready=False,
            tenant_ready=False,
            subscription_ready=False,
        )

    account = account_result.get("data")
    if not isinstance(account, dict):
        return _readiness_result(
            code="AZURE_CLI_ACCOUNT_INVALID",
            binary_ready=True,
            account_ready=False,
            tenant_ready=False,
            subscription_ready=False,
        )

    cloud_ready = account.get("environmentName") == EXPECTED_CLOUD_NAME
    tenant_ready = account.get("tenantId") == EXPECTED_TENANT_ID
    subscription_ready = account.get("id") == EXPECTED_SUBSCRIPTION_ID
    state_ready = account.get("state") == "Enabled"
    if not cloud_ready:
        code = "AZURE_CLI_CLOUD_MISMATCH"
    elif not tenant_ready:
        code = "AZURE_CLI_TENANT_MISMATCH"
    elif not subscription_ready:
        code = "AZURE_CLI_SUBSCRIPTION_MISMATCH"
    elif not state_ready:
        code = "AZURE_CLI_SUBSCRIPTION_STATE_INVALID"
    else:
        code = "AZURE_CLI_READY"
    return _readiness_result(
        code=code,
        binary_ready=True,
        account_ready=True,
        cloud_ready=cloud_ready,
        tenant_ready=tenant_ready,
        subscription_ready=subscription_ready,
        state_ready=state_ready,
    )


def _azure_cloud_config_boundary(
    environ: Mapping[str, str] | None,
) -> tuple[str | None, str | None]:
    source = os.environ if environ is None else environ
    configured = source.get("AZURE_CONFIG_DIR")
    if configured:
        config_root = Path(configured).expanduser()
    else:
        home = source.get("HOME")
        if not home:
            return "AZURE_CLI_CONFIG_HOME_MISSING", None
        config_root = Path(home).expanduser() / ".azure"
    if not config_root.is_absolute():
        return "AZURE_CLI_CONFIG_PATH_INVALID", None
    try:
        config_root.lstat()
    except FileNotFoundError:
        return None, None
    except OSError:
        return "AZURE_CLI_CONFIG_UNTRUSTED", None
    if not _strict_directory(config_root, allowed_uids={0, os.geteuid()}):
        return "AZURE_CLI_CONFIG_UNTRUSTED", None
    cloud_selection = config_root / "clouds.config"
    try:
        cloud_selection.lstat()
    except FileNotFoundError:
        return None, None
    except OSError:
        return "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED", None
    digest = _exact_default_cloud_selection_digest(cloud_selection)
    if digest is None:
        return "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED", None
    return None, digest


def _exact_default_cloud_selection_digest(path: Path) -> str | None:
    try:
        metadata = path.lstat()
    except OSError:
        return None
    if metadata.st_size > _MAX_CLOUD_SELECTION_BYTES:
        return None
    measurement = _stable_file_measurement(
        path,
        allowed_uids={0, os.geteuid()},
        prefix_length=_MAX_CLOUD_SELECTION_BYTES,
        expected_metadata=metadata,
        extra_flags=getattr(os, "O_NONBLOCK", 0),
    )
    if measurement is None:
        return None
    digest, raw = measurement
    if len(raw) != metadata.st_size:
        return None
    try:
        text = raw.decode("utf-8")
        parser = configparser.ConfigParser(
            interpolation=None,
            strict=True,
            empty_lines_in_values=False,
        )
        parser.optionxform = str
        parser.read_string(text)
    except (UnicodeDecodeError, configparser.Error):
        return None
    if parser.defaults() or parser.sections() != [EXPECTED_CLOUD_NAME]:
        return None
    selection = parser[EXPECTED_CLOUD_NAME]
    if (
        set(selection) != {"subscription"}
        or selection.get("subscription", "").strip()
        != EXPECTED_SUBSCRIPTION_ID
    ):
        return None
    return digest


@dataclass(frozen=True, slots=True)
class _CommandSchema:
    prefix: tuple[str, ...]
    required: frozenset[str] = frozenset()
    optional: frozenset[str] = frozenset()
    flags: frozenset[str] = frozenset()
    required_flags: frozenset[str] = frozenset()
    multi: frozenset[str] = frozenset()
    validators: Mapping[str, Callable[[tuple[str, ...]], bool]] | None = None


def _single_exact(expected: str) -> Callable[[tuple[str, ...]], bool]:
    return lambda values: values == (expected,)


def _single_in(expected: frozenset[str]) -> Callable[[tuple[str, ...]], bool]:
    return lambda values: len(values) == 1 and values[0] in expected


def _single_matching(pattern: re.Pattern[str]) -> Callable[[tuple[str, ...]], bool]:
    return lambda values: len(values) == 1 and pattern.fullmatch(values[0]) is not None


def _absolute_file(suffix: str, name: str | None = None) -> Callable[[tuple[str, ...]], bool]:
    def validate(values: tuple[str, ...]) -> bool:
        if len(values) != 1:
            return False
        path = Path(values[0])
        return path.is_absolute() and path.suffix == suffix and (
            name is None or path.name == name
        )

    return validate


def _deployment_parameters_file(values: tuple[str, ...]) -> bool:
    if len(values) != 1 or not values[0].startswith("@"):
        return False
    path = Path(values[0][1:])
    return (
        path.is_absolute()
        and path.name == "main.parameters.json"
        and path.suffix == ".json"
    )


def _resource_group_tags(values: tuple[str, ...]) -> bool:
    return set(values) == {
        "workload=nac-bff",
        "environment=test",
        "dataClassification=no-production-data",
    } and len(values) == 3


def _performance_broker_settings(values: tuple[str, ...]) -> bool:
    if len(values) != len(_PERFORMANCE_BROKER_SETTING_NAMES):
        return False
    parsed: dict[str, str] = {}
    for item in values:
        name, separator, value = item.partition("=")
        if (
            separator != "="
            or name not in _PERFORMANCE_BROKER_SETTING_NAMES
            or name in parsed
            or not value
            or len(value) > 8192
            or any(character in value for character in "\r\n\x00")
        ):
            return False
        parsed[name] = value
    return (
        set(parsed) == set(_PERFORMANCE_BROKER_SETTING_NAMES)
        and parsed["NAC_BFF_PERFORMANCE_LEASE_ENABLED"] == "true"
        and _UUID_RE.fullmatch(parsed["NAC_BFF_PERFORMANCE_LEASE_TENANT_ID"])
        is not None
        and _UUID_RE.fullmatch(parsed["NAC_BFF_PERFORMANCE_LEASE_ACTOR_ID"])
        is not None
        and all(
            re.fullmatch(r"[0-9a-f]{64}", parsed[name]) is not None
            for name in (
                "NAC_BFF_PERFORMANCE_LEASE_OWNER_BINDING_SHA256",
                "NAC_BFF_PERFORMANCE_LEASE_TREE_SHA",
                "NAC_BFF_PERFORMANCE_LEASE_FUNCTION_PACKAGE_SHA256",
                "NAC_BFF_PERFORMANCE_LEASE_PLAN_SHA256",
                "NAC_BFF_PERFORMANCE_LEASE_TARGET_BINDING_SHA256",
                "NAC_BFF_PERFORMANCE_LEASE_TICKET_CERTIFICATE_SHA256",
            )
        )
        and re.fullmatch(
            r"[0-9a-f]{40}",
            parsed["NAC_BFF_PERFORMANCE_LEASE_COMMIT_SHA"],
        )
        is not None
        and re.fullmatch(
            r"locks/[0-9a-f]{64}\.lock",
            parsed["NAC_BFF_PERFORMANCE_LEASE_BLOB_PATH"],
        )
        is not None
        and parsed["NAC_BFF_PERFORMANCE_LEASE_BLOB_URL"].startswith(
            "https://"
        )
        and parsed["NAC_BFF_PERFORMANCE_LEASE_BLOB_URL"].endswith(
            "/" + parsed["NAC_BFF_PERFORMANCE_LEASE_BLOB_PATH"]
        )
    )


def _resource_detail_type_from_id(value: str) -> str | None:
    lowered = value.lower()
    prefix = (
        f"/subscriptions/{EXPECTED_SUBSCRIPTION_ID}/resourcegroups/"
        f"{RESOURCE_GROUP}/providers/"
    ).lower()
    if not lowered.startswith(prefix):
        return None
    if "/providers/microsoft.authorization/roleassignments/" in lowered:
        return "microsoft.authorization/roleassignments"
    if "/microsoft.storage/storageaccounts/" in lowered:
        if "/blobservices/" in lowered and "/containers/" in lowered:
            return "microsoft.storage/storageaccounts/blobservices/containers"
        if "/blobservices/" in lowered:
            return "microsoft.storage/storageaccounts/blobservices"
        return "microsoft.storage/storageaccounts"
    if "/microsoft.insights/components/" in lowered:
        if "/currentbillingfeatures/" in lowered:
            return "microsoft.insights/components/currentbillingfeatures"
        return "microsoft.insights/components"
    if "/microsoft.web/sites/" in lowered:
        if "/config/" in lowered:
            return "microsoft.web/sites/config"
        return "microsoft.web/sites"
    candidates = (
        "microsoft.managedidentity/userassignedidentities",
        "microsoft.operationalinsights/workspaces",
        "microsoft.web/serverfarms",
    )
    for resource_type in candidates:
        if f"/{resource_type}/" in lowered:
            return resource_type
    return None


def _rest_options_valid(options: dict[str, tuple[str, ...]]) -> bool:
    if options in (
        {
            "--method": ("post",),
            "--url": (_RESOURCE_GRAPH_URL,),
            "--body": (_RESOURCE_GRAPH_BODY,),
        },
        {
            "--method": ("post",),
            "--url": (_APP_SETTINGS_URL,),
        },
    ):
        return True
    return (
        set(options) == {"--method", "--url"}
        and options["--method"] == ("get",)
        and len(options["--url"]) == 1
        and is_metrics_url(options["--url"][0])
    )


def _rest_url(values: tuple[str, ...]) -> bool:
    return len(values) == 1 and (
        values[0] in {_RESOURCE_GRAPH_URL, _APP_SETTINGS_URL}
        or is_metrics_url(values[0])
    )


def _is_monitor_metrics_command(command: Sequence[str]) -> bool:
    try:
        if not command or command[0] != "rest":
            return False
        options: dict[str, str] = {}
        index = 1
        while index < len(command):
            option = command[index]
            if index + 1 >= len(command) or not option.startswith("--"):
                return False
            options[option] = command[index + 1]
            index += 2
        return (
            options.get("--method") == "get"
            and isinstance(options.get("--url"), str)
            and is_metrics_url(options["--url"])
        )
    except (IndexError, TypeError):
        return False


def _authorize_monitor_metrics(
    capability: object,
    *,
    target_binding_sha256: str,
) -> None:
    from nac_bff.azure_performance_authorization import (
        MONITOR_READ,
        _authorize_live_action,
    )

    _authorize_live_action(
        capability,
        action=MONITOR_READ,
        target_binding_sha256=target_binding_sha256,
        binding_sha256=monitor_policy_sha256(),
        consume=True,
    )


def _resource_show_options_valid(
    options: dict[str, tuple[str, ...]]
) -> bool:
    smart = {
        "--resource-group": (RESOURCE_GROUP,),
        "--resource-type": (_SMART_DETECTION_ACTION_GROUP_TYPE,),
        "--name": (_SMART_DETECTION_ACTION_GROUP_NAME,),
        "--api-version": (_SMART_DETECTION_ACTION_GROUP_API_VERSION,),
    }
    if options == smart:
        return True
    if set(options) != {"--ids", "--api-version"}:
        return False
    resource_ids = options["--ids"]
    versions = options["--api-version"]
    if len(resource_ids) != 1 or len(versions) != 1:
        return False
    resource_type = _resource_detail_type_from_id(resource_ids[0])
    return (
        resource_type is not None
        and _RESOURCE_DETAIL_API_VERSIONS.get(resource_type) == versions[0]
    )


_COMMON_OPTIONAL = frozenset({"--subscription"})
_COMMON_VALIDATORS: dict[str, Callable[[tuple[str, ...]], bool]] = {
    "--subscription": _single_exact(EXPECTED_SUBSCRIPTION_ID)
}
_COMMAND_SCHEMAS = {
    ("account", "show"): _CommandSchema(
        ("account", "show"),
        optional=_COMMON_OPTIONAL,
        validators=_COMMON_VALIDATORS,
    ),
    ("provider", "show"): _CommandSchema(
        ("provider", "show"),
        required=frozenset({"--namespace"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--namespace": _single_in(_PROVIDER_NAMESPACES),
            **_COMMON_VALIDATORS,
        },
    ),
    ("provider", "register"): _CommandSchema(
        ("provider", "register"),
        required=frozenset({"--namespace"}),
        optional=_COMMON_OPTIONAL,
        flags=frozenset({"--wait"}),
        required_flags=frozenset({"--wait"}),
        validators={
            "--namespace": _single_in(_PROVIDER_NAMESPACES),
            **_COMMON_VALIDATORS,
        },
    ),
    ("group", "exists"): _CommandSchema(
        ("group", "exists"),
        required=frozenset({"--name"}),
        optional=_COMMON_OPTIONAL,
        validators={"--name": _single_exact(RESOURCE_GROUP), **_COMMON_VALIDATORS},
    ),
    ("group", "show"): _CommandSchema(
        ("group", "show"),
        required=frozenset({"--name"}),
        optional=_COMMON_OPTIONAL,
        validators={"--name": _single_exact(RESOURCE_GROUP), **_COMMON_VALIDATORS},
    ),
    ("group", "create"): _CommandSchema(
        ("group", "create"),
        required=frozenset({"--name", "--location", "--tags"}),
        optional=_COMMON_OPTIONAL,
        multi=frozenset({"--tags"}),
        validators={
            "--name": _single_exact(RESOURCE_GROUP),
            "--location": _single_exact(LOCATION),
            "--tags": _resource_group_tags,
            **_COMMON_VALIDATORS,
        },
    ),
    ("resource", "list"): _CommandSchema(
        ("resource", "list"),
        required=frozenset({"--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("rest",): _CommandSchema(
        ("rest",),
        required=frozenset({"--method", "--url"}),
        optional=frozenset({"--body"}),
        validators={
            "--method": _single_in(frozenset({"get", "post"})),
            "--url": _rest_url,
            "--body": _single_exact(_RESOURCE_GRAPH_BODY),
        },
    ),
    ("resource", "show"): _CommandSchema(
        ("resource", "show"),
        optional=frozenset({
            "--resource-group", "--resource-type", "--name",
            "--api-version", "--ids", *tuple(_COMMON_OPTIONAL),
        }),
        validators={
            "--resource-group": _single_exact(RESOURCE_GROUP),
            "--resource-type": _single_exact(
                _SMART_DETECTION_ACTION_GROUP_TYPE
            ),
            "--name": _single_exact(_SMART_DETECTION_ACTION_GROUP_NAME),
            "--api-version": _single_in(frozenset({
                _SMART_DETECTION_ACTION_GROUP_API_VERSION,
                *_RESOURCE_DETAIL_API_VERSIONS.values(),
            })),
            "--ids": lambda values: (
                len(values) == 1
                and _resource_detail_type_from_id(values[0]) is not None
            ),
            **_COMMON_VALIDATORS,
        },
    ),
    ("deployment", "group", "show"): _CommandSchema(
        ("deployment", "group", "show"),
        required=frozenset({"--name", "--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_matching(_DEPLOYMENT_NAME_RE),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("deployment", "operation", "group", "list"): _CommandSchema(
        ("deployment", "operation", "group", "list"),
        required=frozenset({"--name", "--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_matching(_DEPLOYMENT_NAME_RE),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("identity", "show"): _CommandSchema(
        ("identity", "show"),
        required=frozenset({"--name", "--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_matching(_IDENTITY_NAME_RE),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("functionapp", "identity", "show"): _CommandSchema(
        ("functionapp", "identity", "show"),
        required=frozenset({"--name", "--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_exact(FUNCTION_APP),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("functionapp", "config", "appsettings", "set"): _CommandSchema(
        ("functionapp", "config", "appsettings", "set"),
        required=frozenset({"--name", "--resource-group", "--settings"}),
        optional=_COMMON_OPTIONAL,
        multi=frozenset({"--settings"}),
        validators={
            "--name": _single_exact(FUNCTION_APP),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            "--settings": _performance_broker_settings,
            **_COMMON_VALIDATORS,
        },
    ),
    ("functionapp", "config", "appsettings", "list"): _CommandSchema(
        ("functionapp", "config", "appsettings", "list"),
        required=frozenset({"--name", "--resource-group"}),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_exact(FUNCTION_APP),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            **_COMMON_VALIDATORS,
        },
    ),
    ("deployment", "group", "create"): _CommandSchema(
        ("deployment", "group", "create"),
        required=frozenset(
            {"--name", "--resource-group", "--template-file", "--parameters", "--mode"}
        ),
        optional=_COMMON_OPTIONAL,
        validators={
            "--name": _single_matching(_DEPLOYMENT_NAME_RE),
            "--resource-group": _single_exact(RESOURCE_GROUP),
            "--template-file": _absolute_file(".json", "main.json"),
            "--parameters": _deployment_parameters_file,
            "--mode": _single_exact("Incremental"),
            **_COMMON_VALIDATORS,
        },
    ),
    ("functionapp", "deployment", "source", "config-zip"): _CommandSchema(
        ("functionapp", "deployment", "source", "config-zip"),
        required=frozenset(
            {
                "--resource-group",
                "--name",
                "--src",
                "--build-remote",
                "--timeout",
            }
        ),
        optional=_COMMON_OPTIONAL,
        validators={
            "--resource-group": _single_exact(RESOURCE_GROUP),
            "--name": _single_exact(FUNCTION_APP),
            "--src": _absolute_file(".zip"),
            "--build-remote": _single_exact("true"),
            "--timeout": _single_exact(str(FUNCTION_DEPLOYMENT_CLI_TIMEOUT_SECONDS)),
            **_COMMON_VALIDATORS,
        },
    ),
}


def _validated_command(
    argv: object,
) -> tuple[list[str] | None, tuple[str, ...] | None, str]:
    if isinstance(argv, (str, bytes)) or not isinstance(argv, Sequence) or not argv:
        return None, None, "AZURE_CLI_ARGV_INVALID"

    command: list[str] = []
    for token in argv:
        if (
            not isinstance(token, str)
            or not token
            or len(token) > _MAX_ARG_LENGTH
            or "\x00" in token
            or "\n" in token
            or "\r" in token
        ):
            return None, None, "AZURE_CLI_ARGV_INVALID"
        command.append(token)

    family = next(
        (
            prefix
            for prefix in sorted(_COMMAND_SCHEMAS, key=len, reverse=True)
            if tuple(command[: len(prefix)]) == prefix
        ),
        None,
    )
    if family is None:
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    schema = _COMMAND_SCHEMAS[family]
    options: dict[str, tuple[str, ...]] = {}
    seen_flags: set[str] = set()
    index = len(family)
    while index < len(command):
        option = command[index]
        if not option.startswith("--") or "=" in option:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        if option in options or option in seen_flags:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        if option in schema.flags:
            seen_flags.add(option)
            index += 1
            continue
        if option not in schema.required and option not in schema.optional:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        index += 1
        values: list[str] = []
        if option in schema.multi:
            while index < len(command) and not command[index].startswith("--"):
                values.append(command[index])
                index += 1
        elif index < len(command) and not command[index].startswith("--"):
            values.append(command[index])
            index += 1
        if not values:
            return None, None, "AZURE_CLI_COMMAND_BLOCKED"
        options[option] = tuple(values)

    if not schema.required.issubset(options):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    if not schema.required_flags.issubset(seen_flags):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    effective_options = {
        key: value for key, value in options.items() if key != "--subscription"
    }
    if family == ("resource", "show") and not (
        _resource_show_options_valid(effective_options)
    ):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    if family == ("rest",) and not _rest_options_valid(effective_options):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    validators = schema.validators or {}
    if any(not validators[option](values) for option, values in options.items()):
        return None, None, "AZURE_CLI_COMMAND_BLOCKED"
    return command, family, "AZURE_CLI_OK"


def _runtime_expected_sha256(
    explicit: str | None,
    environ: Mapping[str, str] | None,
) -> str | None:
    if explicit is not None:
        return explicit
    source = os.environ if environ is None else environ
    value = source.get(AZURE_CLI_TOOLCHAIN_SHA256_ENV)
    return value if isinstance(value, str) and value else None


def _resolve_azure_cli_binary(
    explicit: str | os.PathLike[str] | None,
    *,
    environ: Mapping[str, str] | None,
    expected_sha256: str | None,
) -> tuple[Path | None, str]:
    expected_sha256 = _runtime_expected_sha256(expected_sha256, environ)
    if explicit is not None:
        try:
            path = Path(explicit).expanduser()
        except TypeError:
            return None, "AZURE_CLI_BINARY_NOT_FOUND"
        return _executable_path(path, expected_sha256=expected_sha256)

    trust_failure: str | None = None
    for candidate in AZURE_CLI_CANDIDATES:
        resolved, code = _executable_path(
            candidate,
            expected_sha256=expected_sha256,
        )
        if resolved is not None:
            return resolved, "AZURE_CLI_BINARY_TRUSTED"
        if code != "AZURE_CLI_BINARY_NOT_FOUND" and trust_failure is None:
            trust_failure = code
    return None, trust_failure or "AZURE_CLI_BINARY_NOT_FOUND"


def _executable_path(
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> tuple[Path | None, str]:
    if not path.is_absolute() or path.name != "az":
        return None, "AZURE_CLI_BINARY_NOT_FOUND"
    try:
        metadata = path.lstat()
    except (OSError, RuntimeError):
        return None, "AZURE_CLI_BINARY_NOT_FOUND"
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if metadata.st_uid not in {0, os.geteuid()}:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if not os.access(path, os.X_OK):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    attestation, attestation_code = _toolchain_attestation(path, metadata)
    if attestation is None:
        return None, attestation_code
    if attestation.requires_expected and expected_sha256 is None:
        return None, "AZURE_CLI_BINARY_ATTESTATION_REQUIRED"
    if expected_sha256 is not None:
        if not isinstance(expected_sha256, str):
            return None, "AZURE_CLI_BINARY_ATTESTATION_INVALID"
        normalized = expected_sha256.lower()
        if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
            return None, "AZURE_CLI_BINARY_ATTESTATION_INVALID"
        if attestation.digest != normalized:
            return None, "AZURE_CLI_BINARY_ATTESTATION_MISMATCH"
    return path, "AZURE_CLI_BINARY_TRUSTED"


def _prepare_bound_runtime(
    path: Path,
    *,
    expected_sha256: str | None,
    cloud_selection_sha256: str | None,
) -> SealedAzureCliRuntime | None:
    if expected_sha256 is None or not isinstance(expected_sha256, str):
        return None
    normalized = expected_sha256.lower()
    if re.fullmatch(r"[0-9a-f]{64}", normalized) is None:
        return None
    try:
        metadata = path.lstat()
    except OSError:
        return None
    attestation, _code = _toolchain_attestation(path, metadata)
    if (
        attestation is None
        or attestation.digest != normalized
        or attestation.interpreter_path is None
        or attestation.interpreter_digest is None
        or attestation.package_root is None
        or attestation.package_digest is None
        or not attestation.runtime_uids
    ):
        return None
    return prepare_sealed_azure_cli_runtime(
        package_root=attestation.package_root,
        package_digest=attestation.package_digest,
        interpreter_path=attestation.interpreter_path,
        interpreter_digest=attestation.interpreter_digest,
        allowed_uids=set(attestation.runtime_uids),
        cloud_selection_sha256=cloud_selection_sha256,
    )


def calculate_azure_cli_toolchain_sha256(
    path: str | os.PathLike[str],
) -> str | None:
    """Calculate a validated toolchain digest for offline owner binding.

    Execution never calls this helper to invent its own expected value. The
    returned digest must cross the owner/configuration boundary separately.
    """

    try:
        candidate = Path(path).expanduser()
        metadata = candidate.lstat()
    except (OSError, RuntimeError, TypeError):
        return None
    if not candidate.is_absolute() or candidate.name != "az":
        return None
    attestation, _code = _toolchain_attestation(candidate, metadata)
    return None if attestation is None else attestation.digest


@dataclass(frozen=True, slots=True)
class _ToolchainAttestation:
    digest: str
    requires_expected: bool
    interpreter_path: Path | None = None
    interpreter_digest: str | None = None
    package_root: Path | None = None
    package_digest: str | None = None
    runtime_uids: frozenset[int] = frozenset()


def _toolchain_attestation(
    path: Path,
    metadata: os.stat_result,
) -> tuple[_ToolchainAttestation | None, str]:
    measurement = _stable_file_measurement(
        path,
        allowed_uids={metadata.st_uid},
        executable=True,
        prefix_length=4097,
        expected_metadata=metadata,
    )
    if measurement is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    content_digest, prefix = measurement
    newline = prefix.find(b"\n")
    first_line = prefix if newline < 0 else prefix[: newline + 1]

    if first_line.startswith(b"\x7fELF"):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    if not first_line.startswith(b"#!") or len(first_line) > 4096:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    try:
        shebang = first_line[2:].strip().decode("ascii")
    except UnicodeDecodeError:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if not shebang or any(character.isspace() for character in shebang):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    interpreter = Path(shebang)
    if (
        not interpreter.is_absolute()
        or interpreter.parent != path.parent
        or _PYTHON_NAME_RE.fullmatch(interpreter.name) is None
    ):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    interpreter_records, interpreter_code = _python_interpreter_attestation(
        interpreter,
        allowed_uids={0, metadata.st_uid},
    )
    if interpreter_records is None:
        return None, interpreter_code
    interpreter_values = dict(interpreter_records)
    interpreter_path = Path(interpreter_values["interpreter_path"])
    interpreter_digest = interpreter_values["interpreter_content"]

    venv_root = path.parent.parent
    if not _strict_directory(venv_root, allowed_uids={0, metadata.st_uid}):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    if not _strict_directory(path.parent, allowed_uids={0, metadata.st_uid}):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    pyvenv_digest = _stable_file_digest(
        venv_root / "pyvenv.cfg",
        allowed_uids={0, metadata.st_uid},
    )
    if pyvenv_digest is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    package_roots = sorted(venv_root.glob("lib/python*/site-packages"))
    if len(package_roots) != 1:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    package_root = package_roots[0]
    package_path_components = (
        venv_root / "lib",
        package_root.parent,
        package_root,
    )
    if any(
        not _strict_directory(component, allowed_uids={0, metadata.st_uid})
        for component in package_path_components
    ):
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    azure_entrypoint = package_root / "azure" / "cli" / "__main__.py"
    if _stable_file_digest(
        azure_entrypoint,
        allowed_uids={0, metadata.st_uid},
    ) is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"
    package_digest = _stable_tree_digest(
        package_root,
        allowed_uids={0, metadata.st_uid},
    )
    if package_digest is None:
        return None, "AZURE_CLI_BINARY_UNTRUSTED"

    source_root = path.parent / "src"
    if source_root.exists() or source_root.is_symlink():
        source_digest = _stable_tree_digest(
            source_root,
            allowed_uids={0, metadata.st_uid},
        )
        if source_digest is None:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
    else:
        source_digest = "ABSENT"

    digest = _attestation_digest(
        ("schema", _ATTESTATION_SCHEMA),
        ("kind", "python-venv-wrapper"),
        ("wrapper_path", str(path)),
        ("wrapper_mode", oct(stat.S_IMODE(metadata.st_mode))),
        ("wrapper_content", content_digest),
        ("shebang", shebang),
        *interpreter_records,
        ("venv_root", str(venv_root)),
        ("pyvenv", pyvenv_digest),
        ("package_root", str(package_root)),
        ("package_tree", package_digest),
        ("wrapper_src_tree", source_digest),
    )
    return (
        _ToolchainAttestation(
            digest=digest,
            requires_expected=True,
            interpreter_path=interpreter_path,
            interpreter_digest=interpreter_digest,
            package_root=package_root,
            package_digest=package_digest,
            runtime_uids=frozenset({0, metadata.st_uid}),
        ),
        "AZURE_CLI_BINARY_TRUSTED",
    )


def _python_interpreter_attestation(
    interpreter: Path,
    *,
    allowed_uids: set[int],
) -> tuple[tuple[tuple[str, str], ...] | None, str]:
    records: list[tuple[str, str]] = []
    current = interpreter
    seen: set[str] = set()
    for index in range(_MAX_INTERPRETER_LINKS + 1):
        normalized = os.path.abspath(os.fspath(current))
        if normalized in seen:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        seen.add(normalized)
        current = Path(normalized)
        try:
            metadata = current.lstat()
        except OSError:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        if metadata.st_uid not in allowed_uids:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        if stat.S_ISLNK(metadata.st_mode):
            if index == _MAX_INTERPRETER_LINKS:
                return None, "AZURE_CLI_BINARY_UNTRUSTED"
            try:
                target = os.readlink(current)
            except OSError:
                return None, "AZURE_CLI_BINARY_UNTRUSTED"
            records.extend(
                (
                    (f"interpreter_link_{index}_path", str(current)),
                    (f"interpreter_link_{index}_target", target),
                    (f"interpreter_link_{index}_uid", str(metadata.st_uid)),
                )
            )
            current = (
                Path(target)
                if os.path.isabs(target)
                else current.parent / target
            )
            continue
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or not os.access(current, os.X_OK)
        ):
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        measurement = _stable_file_measurement(
            current,
            allowed_uids={0},
            executable=True,
            prefix_length=4,
            expected_metadata=metadata,
        )
        if measurement is None:
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        interpreter_digest, header = measurement
        if header != b"\x7fELF":
            return None, "AZURE_CLI_BINARY_UNTRUSTED"
        records.extend(
            (
                ("interpreter_path", str(current)),
                ("interpreter_mode", oct(stat.S_IMODE(metadata.st_mode))),
                ("interpreter_content", interpreter_digest),
            )
        )
        return tuple(records), "AZURE_CLI_BINARY_TRUSTED"
    return None, "AZURE_CLI_BINARY_UNTRUSTED"


def _strict_directory(path: Path, *, allowed_uids: set[int]) -> bool:
    try:
        metadata = path.lstat()
    except OSError:
        return False
    return (
        stat.S_ISDIR(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and metadata.st_uid in allowed_uids
        and not metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
    )


def _stable_file_digest(
    path: Path,
    *,
    allowed_uids: set[int],
    executable: bool = False,
    expected_metadata: os.stat_result | None = None,
) -> str | None:
    measurement = _stable_file_measurement(
        path,
        allowed_uids=allowed_uids,
        executable=executable,
        expected_metadata=expected_metadata,
    )
    return None if measurement is None else measurement[0]


def _stable_file_measurement(
    path: Path,
    *,
    allowed_uids: set[int],
    executable: bool = False,
    prefix_length: int = 0,
    expected_metadata: os.stat_result | None = None,
    extra_flags: int = 0,
) -> tuple[str, bytes] | None:
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | extra_flags
    )
    try:
        before_path = path.lstat()
        descriptor = os.open(path, flags)
    except OSError:
        return None
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or stat.S_ISLNK(before_path.st_mode)
            or before.st_uid not in allowed_uids
            or before.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
            or (executable and not before.st_mode & stat.S_IXUSR)
            or (before.st_dev, before.st_ino)
            != (before_path.st_dev, before_path.st_ino)
            or (
                expected_metadata is not None
                and _stat_signature(before_path)
                != _stat_signature(expected_metadata)
            )
        ):
            return None
        digest = hashlib.sha256()
        prefix = bytearray()
        while True:
            chunk = os.read(descriptor, _FILE_CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            if len(prefix) < prefix_length:
                prefix.extend(chunk[: prefix_length - len(prefix)])
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        after_path = path.lstat()
    except OSError:
        return None
    if (
        _stat_signature(before) != _stat_signature(after)
        or _stat_signature(after) != _stat_signature(after_path)
    ):
        return None
    return digest.hexdigest(), bytes(prefix)

def _stable_tree_digest(root: Path, *, allowed_uids: set[int]) -> str | None:
    if not _strict_directory(root, allowed_uids=allowed_uids):
        return None
    digest = hashlib.sha256()
    directory_snapshots: list[tuple[Path, tuple[int, ...]]] = []
    try:
        for current_text, directories, files in os.walk(
            root,
            topdown=True,
            followlinks=False,
        ):
            current = Path(current_text)
            current_metadata = current.lstat()
            if not _strict_directory(current, allowed_uids=allowed_uids):
                return None
            directory_snapshots.append(
                (current, _stat_signature(current_metadata))
            )
            directories.sort()
            files.sort()
            for name in directories:
                child = current / name
                metadata = child.lstat()
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or not stat.S_ISDIR(metadata.st_mode)
                ):
                    return None
                if (
                    metadata.st_uid not in allowed_uids
                    or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                ):
                    return None
                _attestation_update(
                    digest,
                    "directory",
                    child.relative_to(root).as_posix(),
                    str(metadata.st_uid),
                    oct(stat.S_IMODE(metadata.st_mode)),
                )
            for name in files:
                child = current / name
                metadata = child.lstat()
                if (
                    stat.S_ISLNK(metadata.st_mode)
                    or not stat.S_ISREG(metadata.st_mode)
                ):
                    return None
                child_digest = _stable_file_digest(
                    child,
                    allowed_uids=allowed_uids,
                )
                if child_digest is None:
                    return None
                _attestation_update(
                    digest,
                    "file",
                    child.relative_to(root).as_posix(),
                    str(metadata.st_uid),
                    oct(stat.S_IMODE(metadata.st_mode)),
                    child_digest,
                )
    except (OSError, RuntimeError, ValueError):
        return None
    for directory, signature in directory_snapshots:
        try:
            if _stat_signature(directory.lstat()) != signature:
                return None
        except OSError:
            return None
    return digest.hexdigest()


def _stat_signature(metadata: os.stat_result) -> tuple[int, ...]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _attestation_digest(*records: tuple[str, str]) -> str:
    digest = hashlib.sha256()
    for key, value in records:
        _attestation_update(digest, key, value)
    return digest.hexdigest()


def _attestation_update(digest: object, *values: str) -> None:
    for value in values:
        encoded = value.encode("utf-8", errors="surrogateescape")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)

def _command_result(
    *,
    ok: bool,
    code: str,
    command: tuple[str, ...] | None,
    returncode: int | None = None,
    data: object = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "ok": ok,
        "status": (
            "PASSED"
            if ok
            else "BLOCKED"
            if code.startswith("AZURE_CLI_BINARY_")
            else "FAILED"
        ),
        "code": code,
        "command": None if command is None else " ".join(command),
    }
    if returncode is not None:
        result["returncode"] = returncode
    if ok:
        result["data"] = data
    return result


def _readiness_result(
    *,
    code: str,
    binary_ready: bool,
    account_ready: bool,
    cloud_ready: bool = False,
    tenant_ready: bool,
    subscription_ready: bool,
    state_ready: bool = False,
) -> dict[str, object]:
    ready = (
        binary_ready
        and account_ready
        and cloud_ready
        and tenant_ready
        and subscription_ready
        and state_ready
    )
    return {
        "status": "READY" if ready else "NOT_READY",
        "ready": ready,
        "code": code,
        "bindings": {
            "cloud_name": EXPECTED_CLOUD_NAME,
            "tenant_id": EXPECTED_TENANT_ID,
            "subscription_id": EXPECTED_SUBSCRIPTION_ID,
        },
        "checks": [
            {"id": "binary", "status": "READY" if binary_ready else "NOT_READY"},
            {"id": "account", "status": "READY" if account_ready else "NOT_READY"},
            {"id": "cloud", "status": "READY" if cloud_ready else "NOT_READY"},
            {"id": "tenant", "status": "READY" if tenant_ready else "NOT_READY"},
            {
                "id": "subscription",
                "status": "READY" if subscription_ready else "NOT_READY",
            },
            {
                "id": "subscription_state",
                "status": "READY" if state_ready else "NOT_READY",
            },
        ],
        "redaction": {
            "raw_stdout_included": False,
            "raw_stderr_included": False,
            "account_payload_included": False,
            "environment_values_included": False,
        },
    }
