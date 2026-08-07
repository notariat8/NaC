from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping
from uuid import UUID

from .azure_activation import RESOURCE_GROUP, SUBSCRIPTION_ID, TENANT_ID
from .azure_activation_attestations import (
    TOOLCHAIN_ATTESTATION_FIELDS,
    build_activation_attestation_plan,
    calculate_toolchain_attestations_sha256,
)
from .azure_performance_acceptance import (
    CONTRACT_RELATIVE_PATH,
    OWNER_ACTION,
    build_owner_comment,
    build_performance_acceptance_plan,
)
from .azure_performance_lease_broker import (
    lease_broker_state_bootstrap_policy_sha256,
)
from .azure_performance_composition import (
    validate_azure_performance_composition_readiness,
)
from .azure_performance_infrastructure_safety import (
    effective_coordination_tags,
    infrastructure_safety_policy_sha256,
    private_network_boundary_sha256,
)


SCHEMA_VERSION = "nac.m365-bff-performance-infrastructure-live-owner-gate/v1"
ACTION = OWNER_ACTION
COMMAND = "nac m365 teams-sharepoint bff-performance-infrastructure-owner-gate"
INFRASTRUCTURE_SOURCE_PATHS = (
    Path("workflows/contracts/m365-bff-performance-acceptance.contract.json"),
    Path(
        "workflows/verification-contracts/"
        "m365-bff-performance-acceptance.verification.json"
    ),
    Path("deploy/runtime/azure/nac-bff-performance-coordination/main.bicep"),
    Path(
        "deploy/runtime/azure/nac-bff-performance-coordination/"
        "main.example.bicepparam"
    ),
    Path(
        "deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.json"
    ),
    Path(
        "deploy/runtime/azure/nac-bff-performance-coordination/"
        "compiled/main.example.json"
    ),
    Path("src/nac_bff/azure_performance_runtime.py"),
    Path("src/nac_bff/azure_performance_composition.py"),
    Path("src/nac_bff/azure_performance_lease_broker.py"),
    Path("src/nac_bff/azure_performance_lease_broker_auth.py"),
    Path("src/nac_bff/azure_performance_lease_broker_client.py"),
    Path("src/nac_bff/azure_performance_lease_broker_composition.py"),
    Path("src/nac_bff/azure_performance_lease_broker_storage.py"),
    Path("src/nac_bff/azure_performance_broker_activation.py"),
    Path("src/nac_bff/graph_activation.py"),
    Path("src/nac_bff/azure_performance_acceptance.py"),
    Path("src/nac_bff/azure_performance_authorization.py"),
    Path("src/nac_bff/azure_performance_monitor.py"),
    Path("src/nac_bff/azure_performance_infrastructure_safety.py"),
    Path("src/nac_bff/azure_performance_infrastructure_ports.py"),
    Path("src/nac_bff/azure_performance_storage_ports.py"),
    Path("src/nac_bff/azure_performance_owner_gate.py"),
    Path("src/nac_bff/azure_live_commands.py"),
    Path("src/nac_cli/cli.py"),
    Path("scripts/validate_m365_azure_bff_performance_acceptance.py"),
    Path("scripts/validate_nac_bff_performance_coordination_arm.py"),
    Path("deploy/runtime/azure/immutable-evidence/main.bicep"),
    Path("deploy/runtime/azure/immutable-evidence/main.bicepparam"),
    Path("deploy/runtime/azure/immutable-evidence/compiled/main.json"),
    Path(
        "deploy/runtime/azure/immutable-evidence/compiled/"
        "main.parameters.json"
    ),
    Path("workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json"),
    Path(
        "workflows/verification-contracts/"
        "business-case-type-azure-blob-worm-s6b.verification.json"
    ),
    Path("scripts/validate_business_case_type_azure_blob_worm.py"),
)
WORM_BASELINE_SOURCE_PATHS = (
    Path("deploy/runtime/azure/immutable-evidence/main.bicep"),
    Path("deploy/runtime/azure/immutable-evidence/main.bicepparam"),
    Path("deploy/runtime/azure/immutable-evidence/compiled/main.json"),
    Path(
        "deploy/runtime/azure/immutable-evidence/compiled/"
        "main.parameters.json"
    ),
    Path("workflows/contracts/business-case-type-azure-blob-worm-s6b.contract.json"),
    Path(
        "workflows/verification-contracts/"
        "business-case-type-azure-blob-worm-s6b.verification.json"
    ),
    Path("scripts/validate_business_case_type_azure_blob_worm.py"),
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_OBJECT_RE = re.compile(r"^[0-9a-f]{40}$")
_GIT_EXECUTABLE = "/usr/bin/git"
_GIT_HEAD_ARGV = ("rev-parse", "--verify", "HEAD")
_GIT_TREE_ARGV = ("rev-parse", "--verify", "HEAD^{tree}")
_GIT_STATUS_ARGV = ("status", "--porcelain=v1", "--untracked-files=all")
_GIT_ALLOWED_ARGV = frozenset(
    {_GIT_HEAD_ARGV, _GIT_TREE_ARGV, _GIT_STATUS_ARGV}
)
_GIT_BASE_ARGV = (
    _GIT_EXECUTABLE,
    "--no-optional-locks",
    "--no-replace-objects",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.fsmonitor=false",
    "-c",
    "maintenance.auto=false",
)
_GIT_ENV = {
    "GIT_ATTR_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_PAGER": "cat",
    "GIT_TERMINAL_PROMPT": "0",
    "LC_ALL": "C",
}
_STORAGE_ACCOUNT_RE = re.compile(r"^[a-z0-9]{3,24}$")
_STORAGE_ACCOUNT_ID_RE = re.compile(
    r"^/subscriptions/(?P<subscription>[0-9a-f-]{36})/resourceGroups/"
    r"(?P<resource_group>[^/]+)/providers/Microsoft\.Storage/storageAccounts/"
    r"(?P<name>[a-z0-9]{3,24})$"
)
_FUNCTION_APP_ID_RE = re.compile(
    r"^/subscriptions/(?P<subscription>[0-9a-f-]{36})/resourceGroups/"
    r"(?P<resource_group>[^/]+)/providers/Microsoft\.Web/sites/"
    r"(?P<name>[a-zA-Z0-9-]{1,60})$"
)
_VIRTUAL_NETWORK_ID_RE = re.compile(
    r"^/subscriptions/(?P<subscription>[0-9a-f-]{36})/resourceGroups/"
    r"(?P<resource_group>[^/]+)/providers/Microsoft\.Network/virtualNetworks/"
    r"(?P<name>[a-zA-Z0-9-]{1,64})$"
)
_SUBNET_ID_RE = re.compile(
    r"^(?P<vnet>/subscriptions/(?P<subscription>[0-9a-f-]{36})/resourceGroups/"
    r"(?P<resource_group>[^/]+)/providers/Microsoft\.Network/virtualNetworks/"
    r"(?P<vnet_name>[a-zA-Z0-9-]{1,64}))/subnets/"
    r"(?P<name>[a-zA-Z0-9-]{1,80})$"
)
_PARAMETER_KEYS = frozenset(
    {
        "location",
        "storageAccountName",
        "bffStorageAccountResourceId",
        "wormStorageAccountResourceId",
        "brokerCallerServicePrincipalId",
        "brokerFunctionAppResourceId",
        "brokerVirtualNetworkResourceId",
        "brokerFunctionIntegrationSubnetResourceId",
        "brokerPrivateEndpointSubnetResourceId",
        "brokerFunctionPackageSha256",
        "brokerTicketVerificationCertificateSha256",
        "targetBindingSha256",
        "tenantId",
        "subscriptionId",
        "resourceGroupName",
        "deploymentMode",
        "tags",
    }
)
_WORM_PARAMETER_KEYS = frozenset(
    {
        "location",
        "tenantId",
        "subscriptionId",
        "resourceGroupName",
        "deploymentMode",
        "storageAccountName",
        "containerName",
        "encryptionScopeName",
        "tags",
    }
)


def build_performance_infrastructure_owner_gate(
    repo_root: Path,
    *,
    expected_activation_hash: str,
    toolchain_attestations: Mapping[str, str],
    infrastructure_parameters: Mapping[str, Any],
    worm_baseline_parameters: Mapping[str, Any],
    correlation_id: str,
    monitor_window_anchor_utc: str,
) -> dict[str, Any]:
    """Build one offline approval binding infrastructure and the complete run."""

    try:
        composition = validate_azure_performance_composition_readiness()
        if composition.get("status") != "READY" or composition.get("ready") is not True:
            raise ValueError("PERFORMANCE_PRODUCTION_COMPOSITION_NOT_READY")
        root = repo_root.expanduser().resolve()
        _require_sha256(expected_activation_hash, "expected_activation_hash")
        measurement = measure_performance_infrastructure_approval(
            root,
            expected_activation_hash=expected_activation_hash,
            toolchain_attestations=toolchain_attestations,
            infrastructure_parameters=infrastructure_parameters,
            worm_baseline_parameters=worm_baseline_parameters,
        )
        parameters = measurement["parameters"]
        contract_sha256 = measurement["contract_sha256"]
        infrastructure_approval = measurement["infrastructure_approval"]
        before = (
            infrastructure_approval["approved_commit_sha"],
            infrastructure_approval["approved_tree_sha"],
            False,
        )
        combined = build_owner_comment(
            contract_sha256,
            expected_activation_hash,
            correlation_id,
            infrastructure_approval,
            monitor_window_anchor_utc,
        )
        if not isinstance(combined, Mapping) or set(combined) != {
            "body",
            "body_sha256",
        }:
            raise ValueError("OWNER_APPROVAL_BINDING_INVALID")
        body = combined["body"]
        if (
            not isinstance(body, str)
            or combined["body_sha256"] != _sha256_text(body)
            or "\n" not in body
        ):
            raise ValueError("OWNER_APPROVAL_BINDING_INVALID")
        approval_payload = json.loads(body.split("\n", 1)[1])
        if (
            not isinstance(approval_payload, Mapping)
            or approval_payload.get("target_binding_sha256")
            != parameters["targetBindingSha256"]
            or any(
                approval_payload.get(key) != value
                for key, value in infrastructure_approval.items()
            )
        ):
            raise ValueError("OWNER_APPROVAL_BINDING_INVALID")
        after = _git_snapshot(root)
        if before != after or after[2]:
            raise ValueError("SOURCE_TREE_CHANGED_DURING_GATE_BUILD")
        return {
            "schema_version": SCHEMA_VERSION,
            "command": COMMAND,
            "status": "READY",
            "mode": "offline_owner_gate",
            "owner_approval_payload": dict(approval_payload),
            "owner_comment_body": body,
            "owner_comment_body_sha256": _sha256_text(body),
            "owner_execution_bindings": {
                **infrastructure_approval,
                "contract_sha256": approval_payload["contract_sha256"],
                "expected_activation_hash": approval_payload[
                    "expected_activation_hash"
                ],
                "phase_plan_sha256": approval_payload["phase_plan_sha256"],
                "measurement_policy_sha256": approval_payload[
                    "measurement_policy_sha256"
                ],
                "monitor_policy_sha256": approval_payload[
                    "monitor_policy_sha256"
                ],
                "lease_policy_sha256": approval_payload["lease_policy_sha256"],
                "lease_broker_policy_sha256": approval_payload[
                    "lease_broker_policy_sha256"
                ],
                "monitor_window_anchor_sha256": _sha256_text(
                    monitor_window_anchor_utc
                ),
                "owner_approval_body_sha256": _sha256_text(body),
                "target_binding_sha256": parameters["targetBindingSha256"],
            },
            "redacted_parameter_bindings": {
                "broker_private_network_boundary_sha256": private_network_boundary_sha256(
                    virtual_network_resource_id=parameters[
                        "brokerVirtualNetworkResourceId"
                    ],
                    function_integration_subnet_resource_id=parameters[
                        "brokerFunctionIntegrationSubnetResourceId"
                    ],
                    private_endpoint_subnet_resource_id=parameters[
                        "brokerPrivateEndpointSubnetResourceId"
                    ],
                ),
                "broker_principal_source": (
                    "bound-function-system-assigned-identity-readback"
                ),
                "broker_caller_service_principal_sha256": _sha256_text(
                    parameters["brokerCallerServicePrincipalId"]
                ),
                "broker_function_app_resource_id_sha256": _sha256_text(
                    parameters["brokerFunctionAppResourceId"]
                ),
                "broker_virtual_network_resource_id_sha256": _sha256_text(
                    parameters["brokerVirtualNetworkResourceId"]
                ),
                "broker_function_integration_subnet_resource_id_sha256": _sha256_text(
                    parameters["brokerFunctionIntegrationSubnetResourceId"]
                ),
                "broker_private_endpoint_subnet_resource_id_sha256": _sha256_text(
                    parameters["brokerPrivateEndpointSubnetResourceId"]
                ),
                "broker_function_package_sha256": parameters[
                    "brokerFunctionPackageSha256"
                ],
                "broker_ticket_verification_certificate_sha256": parameters[
                    "brokerTicketVerificationCertificateSha256"
                ],
                "storage_account_name_sha256": _sha256_text(
                    parameters["storageAccountName"]
                ),
                "bff_storage_account_resource_id_sha256": _sha256_text(
                    parameters["bffStorageAccountResourceId"]
                ),
                "worm_storage_account_resource_id_sha256": _sha256_text(
                    parameters["wormStorageAccountResourceId"]
                ),
                "effective_tags_sha256": _sha256_json(
                    effective_coordination_tags(
                        parameters["tags"], parameters["targetBindingSha256"]
                    )
                ),
            },
            "boundaries": {
                "network_accessed": False,
                "azure_resources_created": 0,
                "live_target_dispatches": 0,
                "private_key_read": False,
            },
            "composition_readiness": composition,
        }
    except Exception as exc:
        code = str(exc)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{1,79}", code):
            code = "PERFORMANCE_INFRASTRUCTURE_OWNER_GATE_FAILED"
        return {
            "schema_version": SCHEMA_VERSION,
            "command": COMMAND,
            "status": "NOT_READY",
            "mode": "offline_owner_gate",
            "error_code": code,
            "boundaries": {
                "network_accessed": False,
                "azure_resources_created": 0,
                "live_target_dispatches": 0,
                "private_key_read": False,
            },
        }


def measure_performance_infrastructure_approval(
    repo_root: Path,
    *,
    expected_activation_hash: str,
    toolchain_attestations: Mapping[str, str],
    infrastructure_parameters: Mapping[str, Any],
    worm_baseline_parameters: Mapping[str, Any],
) -> dict[str, Any]:
    """Re-measure every owner-bound source before any network boundary."""

    root = repo_root.expanduser().resolve()
    snapshot = _git_snapshot(root)
    if snapshot[2]:
        raise ValueError("SOURCE_TREE_NOT_CLEAN")
    _require_sha256(expected_activation_hash, "expected_activation_hash")
    measured_toolchain, measured_toolchain_sha256 = (
        _measure_current_toolchain_attestations(toolchain_attestations)
    )
    worm_parameters = _validate_worm_parameters(worm_baseline_parameters)
    parameters = _validate_parameters(infrastructure_parameters)
    if (
        parameters["brokerTicketVerificationCertificateSha256"]
        != measured_toolchain["provisioner_certificate_sha256"]
    ):
        raise ValueError("BROKER_TICKET_CERTIFICATE_BINDING_MISMATCH")
    expected_worm_resource_id = (
        f"/subscriptions/{worm_parameters['subscriptionId']}/resourceGroups/"
        f"{worm_parameters['resourceGroupName']}/providers/Microsoft.Storage/"
        f"storageAccounts/{worm_parameters['storageAccountName']}"
    )
    if parameters["wormStorageAccountResourceId"] != expected_worm_resource_id:
        raise ValueError("WORM_BASELINE_RESOURCE_BINDING_MISMATCH")
    contract_path = (root / CONTRACT_RELATIVE_PATH).resolve()
    if root not in contract_path.parents or not contract_path.is_file():
        raise ValueError("PERFORMANCE_CONTRACT_NOT_FOUND")
    contract_sha256 = _sha256_bytes(contract_path.read_bytes())
    plan = build_performance_acceptance_plan(
        expected_activation_hash,
        contract_sha256,
    )
    if parameters["targetBindingSha256"] != plan["target_binding_sha256"]:
        raise ValueError("INFRASTRUCTURE_TARGET_BINDING_MISMATCH")
    source_sha256 = _source_bundle_sha256(root)
    parameters_sha256 = _sha256_json(parameters)
    worm_source_sha256 = _source_bundle_sha256(
        root, relative_paths=WORM_BASELINE_SOURCE_PATHS
    )
    worm_parameters_sha256 = _sha256_json(worm_parameters)
    worm_compiled_arm_sha256 = _sha256_bytes(
        (root / "deploy/runtime/azure/immutable-evidence/compiled/main.json")
        .resolve()
        .read_bytes()
    )
    worm_binding_sha256 = _sha256_json(
        {
            "worm_baseline_compiled_arm_sha256": worm_compiled_arm_sha256,
            "worm_baseline_parameters_sha256": worm_parameters_sha256,
            "worm_baseline_source_sha256": worm_source_sha256,
        }
    )
    bootstrap_sha256 = lease_broker_state_bootstrap_policy_sha256()
    safety_sha256 = infrastructure_safety_policy_sha256()
    infrastructure_binding_sha256 = _sha256_json(
        {
            "infrastructure_parameters_sha256": parameters_sha256,
            "infrastructure_source_sha256": source_sha256,
            "lease_bootstrap_policy_sha256": bootstrap_sha256,
            "infrastructure_safety_policy_sha256": safety_sha256,
        }
    )
    deployment_sequence_sha256 = _sha256_json(
        {
            "infrastructure_binding_sha256": infrastructure_binding_sha256,
            "sequence": [
                "deploy_unlocked_worm_baseline",
                "verify_worm_baseline_readback",
                "deploy_performance_coordination",
                "verify_coordination_and_effective_rbac",
                "broker_conditionally_create_or_read_exact_state_blob",
                "execute_endpoint_scoped_conservative_measurement",
                "release_lease_and_finalize_redacted_evidence",
            ],
            "worm_baseline_binding_sha256": worm_binding_sha256,
        }
    )
    closing_snapshot = _git_snapshot(root)
    if snapshot != closing_snapshot or closing_snapshot[2]:
        raise ValueError("SOURCE_TREE_CHANGED_DURING_MEASUREMENT")
    return {
        "contract_sha256": contract_sha256,
        "parameters": parameters,
        "infrastructure_approval": {
            "approved_commit_sha": closing_snapshot[0],
            "approved_tree_sha": closing_snapshot[1],
            "infrastructure_binding_sha256": infrastructure_binding_sha256,
            "infrastructure_parameters_sha256": parameters_sha256,
            "infrastructure_source_sha256": source_sha256,
            "lease_bootstrap_policy_sha256": bootstrap_sha256,
            "infrastructure_safety_policy_sha256": safety_sha256,
            "toolchain_attestations_sha256": measured_toolchain_sha256,
            "worm_baseline_binding_sha256": worm_binding_sha256,
            "worm_baseline_compiled_arm_sha256": worm_compiled_arm_sha256,
            "worm_baseline_parameters_sha256": worm_parameters_sha256,
            "worm_baseline_source_sha256": worm_source_sha256,
            "deployment_sequence_sha256": deployment_sequence_sha256,
        },
    }


def format_performance_infrastructure_owner_gate(result: Mapping[str, Any]) -> str:
    lines = [f"STATUS: {result['status']}"]
    if result["status"] == "READY":
        payload = result["owner_approval_payload"]
        lines.extend(
            [
                f"Commit: {payload['approved_commit_sha']}",
                f"Tree: {payload['approved_tree_sha']}",
                f"Owner comment body SHA-256: {result['owner_comment_body_sha256']}",
                "Owner comment body:",
                str(result["owner_comment_body"]),
            ]
        )
    else:
        lines.append(str(result.get("error_code", "OWNER_GATE_NOT_READY")))
    return "\n".join(lines) + "\n"


def _validate_parameters(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _PARAMETER_KEYS:
        raise ValueError("INFRASTRUCTURE_PARAMETERS_INVALID")
    result = dict(value)
    if result["location"] != "germanywestcentral":
        raise ValueError("INFRASTRUCTURE_PARAMETERS_INVALID")
    if (
        result["tenantId"] != TENANT_ID
        or result["subscriptionId"] != SUBSCRIPTION_ID
        or result["resourceGroupName"] != RESOURCE_GROUP
        or result["deploymentMode"] != "Incremental"
    ):
        raise ValueError("INFRASTRUCTURE_DEPLOYMENT_SCOPE_INVALID")
    tags = result["tags"]
    if (
        not isinstance(tags, Mapping)
        or not tags
        or any(
            not isinstance(key, str)
            or not key
            or len(key) > 128
            or not isinstance(item, str)
            or not item
            or len(item) > 256
            for key, item in tags.items()
        )
    ):
        raise ValueError("INFRASTRUCTURE_TAGS_INVALID")
    coordination_name = result["storageAccountName"]
    resource_ids = (
        result["bffStorageAccountResourceId"],
        result["wormStorageAccountResourceId"],
    )
    matches = [
        _STORAGE_ACCOUNT_ID_RE.fullmatch(value)
        if isinstance(value, str)
        else None
        for value in resource_ids
    ]
    if (
        not isinstance(coordination_name, str)
        or _STORAGE_ACCOUNT_RE.fullmatch(coordination_name) is None
        or any(match is None for match in matches)
        or any(match.group("subscription") != SUBSCRIPTION_ID for match in matches)
        or len({coordination_name, *(match.group("name") for match in matches)})
        != 3
    ):
        raise ValueError("INFRASTRUCTURE_PARAMETERS_INVALID")
    try:
        broker_caller = UUID(str(result["brokerCallerServicePrincipalId"]))
        function_app_match = _FUNCTION_APP_ID_RE.fullmatch(
            str(result["brokerFunctionAppResourceId"])
        )
        virtual_network_match = _VIRTUAL_NETWORK_ID_RE.fullmatch(
            str(result["brokerVirtualNetworkResourceId"])
        )
        function_subnet_match = _SUBNET_ID_RE.fullmatch(
            str(result["brokerFunctionIntegrationSubnetResourceId"])
        )
        private_endpoint_subnet_match = _SUBNET_ID_RE.fullmatch(
            str(result["brokerPrivateEndpointSubnetResourceId"])
        )
    except (TypeError, ValueError):
        raise ValueError("INFRASTRUCTURE_PARAMETERS_INVALID") from None
    if (
        function_app_match is None
        or virtual_network_match is None
        or function_subnet_match is None
        or private_endpoint_subnet_match is None
        or function_app_match.group("subscription") != SUBSCRIPTION_ID
        or function_app_match.group("resource_group") != RESOURCE_GROUP
        or virtual_network_match.group("subscription") != SUBSCRIPTION_ID
        or virtual_network_match.group("resource_group") != RESOURCE_GROUP
        or function_subnet_match.group("vnet").casefold()
        != str(result["brokerVirtualNetworkResourceId"]).casefold()
        or private_endpoint_subnet_match.group("vnet").casefold()
        != str(result["brokerVirtualNetworkResourceId"]).casefold()
        or function_subnet_match.group("name").casefold()
        == private_endpoint_subnet_match.group("name").casefold()
    ):
        raise ValueError("INFRASTRUCTURE_PARAMETERS_INVALID")
    _require_sha256(result["targetBindingSha256"], "targetBindingSha256")
    _require_sha256(
        result["brokerFunctionPackageSha256"],
        "brokerFunctionPackageSha256",
    )
    _require_sha256(
        result["brokerTicketVerificationCertificateSha256"],
        "brokerTicketVerificationCertificateSha256",
    )
    return {
        key: (
            {tag: tags[tag] for tag in sorted(tags)}
            if key == "tags"
            else str(result[key])
        )
        for key in sorted(result)
    }


def _validate_worm_parameters(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != _WORM_PARAMETER_KEYS:
        raise ValueError("WORM_BASELINE_PARAMETERS_INVALID")
    result = dict(value)
    if (
        result["location"] != "germanywestcentral"
        or result["tenantId"] != TENANT_ID
        or result["subscriptionId"] != SUBSCRIPTION_ID
        or result["resourceGroupName"] != RESOURCE_GROUP
        or result["deploymentMode"] != "Incremental"
        or not isinstance(result["storageAccountName"], str)
        or _STORAGE_ACCOUNT_RE.fullmatch(result["storageAccountName"]) is None
        or not _valid_container_name(result["containerName"])
        or not _valid_container_name(result["encryptionScopeName"])
    ):
        raise ValueError("WORM_BASELINE_PARAMETERS_INVALID")
    tags = result["tags"]
    if (
        not isinstance(tags, Mapping)
        or not tags
        or any(
            not isinstance(key, str)
            or not key
            or len(key) > 128
            or not isinstance(item, str)
            or not item
            or len(item) > 256
            for key, item in tags.items()
        )
    ):
        raise ValueError("WORM_BASELINE_PARAMETERS_INVALID")
    return {
        key: (
            {tag: tags[tag] for tag in sorted(tags)}
            if key == "tags"
            else str(result[key])
        )
        for key in sorted(result)
    }


def _valid_container_name(value: Any) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])", value)
        is not None
        and "--" not in value
    )


def _validate_toolchain_attestations(
    value: Mapping[str, str],
) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != set(
        TOOLCHAIN_ATTESTATION_FIELDS
    ):
        raise ValueError("TOOLCHAIN_ATTESTATIONS_INVALID")
    result = {
        name: value[name]
        for name in TOOLCHAIN_ATTESTATION_FIELDS
    }
    if any(
        not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None
        for digest in result.values()
    ):
        raise ValueError("TOOLCHAIN_ATTESTATIONS_INVALID")
    return result


def _measure_current_toolchain_attestations(
    supplied: Mapping[str, str],
) -> tuple[dict[str, str], str]:
    expected = _validate_toolchain_attestations(supplied)
    measurement = build_activation_attestation_plan(
        provisioner_certificate_path=Path(
            os.environ.get("M365_PROVISIONER_CLIENT_CERTIFICATE_PATH", "")
        )
    )
    if measurement.get("status") != "READY":
        raise ValueError("TOOLCHAIN_ATTESTATIONS_NOT_READY")
    measured = measurement.get("toolchain_attestations")
    combined = measurement.get("toolchain_attestations_sha256")
    if (
        measurement.get("reads_private_key") is not False
        or measurement.get("executes_provider_requests") is not False
        or not isinstance(measured, Mapping)
    ):
        raise ValueError("TOOLCHAIN_ATTESTATIONS_INVALID")
    current = _validate_toolchain_attestations(measured)
    if (
        not isinstance(combined, str)
        or _SHA256_RE.fullmatch(combined) is None
        or combined != calculate_toolchain_attestations_sha256(current)
    ):
        raise ValueError("TOOLCHAIN_ATTESTATIONS_INVALID")
    if current != expected:
        raise ValueError("TOOLCHAIN_ATTESTATIONS_MISMATCH")
    return current, combined


def _source_bundle_sha256(
    root: Path,
    *,
    relative_paths: tuple[Path, ...] | None = None,
) -> str:
    entries: list[dict[str, str]] = []
    for relative in relative_paths or INFRASTRUCTURE_SOURCE_PATHS:
        path = (root / relative).resolve()
        if root not in path.parents or not path.is_file():
            raise ValueError("INFRASTRUCTURE_SOURCE_NOT_FOUND")
        entries.append(
            {
                "path": relative.as_posix(),
                "sha256": _sha256_bytes(path.read_bytes()),
            }
        )
    return _sha256_json(entries)


def _git_snapshot(root: Path) -> tuple[str, str, bool]:
    commit = _git_output(root, _GIT_HEAD_ARGV)
    tree = _git_output(root, _GIT_TREE_ARGV)
    dirty = bool(_git_output(root, _GIT_STATUS_ARGV))
    if (
        _GIT_OBJECT_RE.fullmatch(commit) is None
        or _GIT_OBJECT_RE.fullmatch(tree) is None
    ):
        raise ValueError("SOURCE_CONTROL_SNAPSHOT_INVALID")
    return commit, tree, dirty


def _git_output(root: Path, arguments: tuple[str, ...]) -> str:
    if arguments not in _GIT_ALLOWED_ARGV:
        raise ValueError("SOURCE_CONTROL_SNAPSHOT_INVALID")
    try:
        result = subprocess.run(
            [*_GIT_BASE_ARGV, "-C", str(root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="strict",
            env=dict(_GIT_ENV),
            shell=False,
            stdin=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise ValueError("SOURCE_CONTROL_SNAPSHOT_INVALID") from None
    if result.returncode != 0:
        raise ValueError("SOURCE_CONTROL_SNAPSHOT_INVALID")
    return result.stdout.strip()


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _sha256_json(value: Any) -> str:
    return _sha256_text(_canonical_json(value))


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{label.upper()}_INVALID")


__all__ = [
    "ACTION",
    "COMMAND",
    "WORM_BASELINE_SOURCE_PATHS",
    "SCHEMA_VERSION",
    "build_performance_infrastructure_owner_gate",
    "format_performance_infrastructure_owner_gate",
    "measure_performance_infrastructure_approval",
]
