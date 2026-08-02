from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from . import azure_activation_runner as runner
from .approved_git_tree import ApprovedGitTreeError, GitApprovedTreeSource
from .azure_activation import (
    FUNCTION_APP,
    LOCATION,
    RESOURCE_GROUP,
    SITE_ID,
    SUBSCRIPTION_ID,
    TEAM_ID,
    TENANT_ID,
    WORKSPACE_ID,
)
from .azure_interruption_contract import (
    BICEP_BASELINE_EXACT,
    RESOURCE_GROUP_ONLY,
    canonical_parameters_from_wrappers,
    compact_sha256_json,
    resource_graph_visible_targets,
)


PREPARED_MANIFEST_SCHEMA = "nac.m365-azure-bff-prepared-inputs/v1"
EXPECTATION_SCHEMA = "nac.m365-azure-bff-interruption-baseline-expectation/v1"
SMART_DETECTION_NAME = "Application Insights Smart Detection"
RESOURCE_TAGS = {
    "dataClassification": "no-production-data",
    "environment": "test",
    "managedBy": "bicep",
    "workload": "nac-bff",
}
EXPECTED_RESOURCE_PROPERTIES = {
    "microsoft.storage/storageaccounts": {
        "kind": "StorageV2",
        "sku": {"name": "Standard_LRS", "tier": "Standard"},
    },
    "microsoft.insights/components": {"kind": "web"},
    "microsoft.web/serverfarms": {
        "kind": "functionapp",
        "sku": {"name": "FC1", "tier": "FlexConsumption"},
    },
    "microsoft.web/sites": {"kind": "functionapp,linux"},
}
DEPLOYMENT_CONTAINER_NAME = "function-releases"
SMART_DETECTION_RECEIVER_COUNTS = {
    "armRoleReceivers": 2,
    "emailReceivers": 0,
    "smsReceivers": 0,
    "webhookReceivers": 0,
    "eventHubReceivers": 0,
    "itsmReceivers": 0,
    "azureAppPushReceivers": 0,
    "automationRunbookReceivers": 0,
    "voiceReceivers": 0,
    "logicAppReceivers": 0,
    "azureFunctionReceivers": 0,
}
SMART_DETECTION_ARM_ROLE_RECEIVERS = (
    {
        "name": "Monitoring Contributor",
        "roleId": "749f88d5-cbae-40b8-bcfc-e573ddc772fa",
        "useCommonAlertSchema": True,
    },
    {
        "name": "Monitoring Reader",
        "roleId": "43d0d8ad-25c7-4714-9337-8ba259a9fe05",
        "useCommonAlertSchema": True,
    },
)
MANIFEST_KEYS = {
    "schema_version",
    "approved_commit_sha",
    "approved_tree_sha",
    "activation_hash",
    "approved_tree_snapshot_sha256",
    "bicep_snapshot_sha256",
    "bicep_parameters_snapshot_sha256",
    "function_package_sha256",
    "spfx_package_sha256",
    "prepared_inputs_sha256",
}
EXPECTED_TOP_LEVEL_TYPES = {
    "microsoft.managedidentity/userassignedidentities",
    "microsoft.storage/storageaccounts",
    "microsoft.operationalinsights/workspaces",
    "microsoft.insights/components",
    "microsoft.web/serverfarms",
    "microsoft.web/sites",
    "microsoft.insights/actiongroups",
}
EXPECTED_DEPLOYMENT_TYPE_COUNTS = {
    "microsoft.authorization/roleassignments": 2,
    "microsoft.insights/components": 1,
    "microsoft.insights/components/currentbillingfeatures": 1,
    "microsoft.managedidentity/userassignedidentities": 1,
    "microsoft.operationalinsights/workspaces": 1,
    "microsoft.storage/storageaccounts": 1,
    "microsoft.storage/storageaccounts/blobservices": 1,
    "microsoft.storage/storageaccounts/blobservices/containers": 1,
    "microsoft.web/serverfarms": 1,
    "microsoft.web/sites": 1,
    "microsoft.web/sites/config": 1,
}
EXPECTATION_KEYS = {
    "schema_version",
    "activation_hash",
    "approved_commit_sha",
    "approved_tree_sha",
    "prepared_inputs_sha256",
    "prepared_inputs_manifest_sha256",
    "bicep_snapshot_sha256",
    "bicep_parameters_snapshot_sha256",
    "azure_template_hash",
    "template_resource_graph_sha256",
    "deployment_name",
    "deployment_parameters_sha256",
    "bff_api_audience",
    "deployment_type_counts",
}
APPROVED_TREE_BICEP_PATH = (
    "deploy/runtime/azure/nac-bff/infra/compiled/main.json"
)
EXPECTED_PARAMETER_VALUES = {
    "location": LOCATION,
    "environmentName": "test",
    "m365TenantId": TENANT_ID,
    "bffRequiredDelegatedScope": "Matter.Read",
    "functionAppName": FUNCTION_APP,
    "maximumInstanceCount": 4,
    "httpPerInstanceConcurrency": 16,
    "tags": {},
}



DEPLOYMENT_NAME = "nac-bff-" + compact_sha256_json(
    {
        "tenant_id": TENANT_ID,
        "resource_group": RESOURCE_GROUP,
        "location": LOCATION,
        "function_app": FUNCTION_APP,
        "workspace_id": WORKSPACE_ID,
        "site_id": SITE_ID,
        "team_id": TEAM_ID,
    }
)[:12]
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z",
    re.IGNORECASE,
)


def read_bound_prepared_artifact(root: Path, relative_path: str) -> bytes | None:
    descriptors: list[int] = []
    try:
        relative = Path(relative_path)
        if relative.is_absolute() or not relative.parts or any(
            part in {"", ".", ".."} for part in relative.parts
        ):
            return None
        directory_flags = (
            os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        )
        descriptor = os.open(root, directory_flags)
        descriptors.append(descriptor)
        root_metadata = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(root_metadata.st_mode)
            or root_metadata.st_uid != os.geteuid()
            or stat.S_IMODE(root_metadata.st_mode) & 0o022
        ):
            return None
        for component in relative.parts[:-1]:
            descriptor = os.open(
                component, directory_flags, dir_fd=descriptors[-1]
            )
            descriptors.append(descriptor)
            metadata = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(metadata.st_mode)
                or metadata.st_uid != os.geteuid()
                or stat.S_IMODE(metadata.st_mode) & 0o022
            ):
                return None
        descriptor = os.open(
            relative.parts[-1],
            os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
            dir_fd=descriptors[-1],
        )
        descriptors.append(descriptor)
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or stat.S_IMODE(opened.st_mode) not in (0o400, 0o600)
            or opened.st_nlink != 1
            or opened.st_size < 1
            or opened.st_size > runner._MAX_SECURE_ARTIFACT_BYTES
        ):
            return None
        raw = runner._read_bounded_descriptor(descriptor)
        after = os.fstat(descriptor)
        if raw is None or not runner._same_secure_snapshot(opened, after):
            return None
        return raw
    except OSError:
        return None
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)

def load_expectation(
    run_dir: Path,
    state: dict[str, Any],
    request: runner.LiveActivationRequest,
    *,
    repo_root: Path,
    approved_tree_source: GitApprovedTreeSource | None = None,
) -> tuple[dict[str, Any] | None, str | None]:
    relative_paths = (
        "prepared/prepared-inputs.redacted.json",
        "prepared/main.json",
        "prepared/main.parameters.json",
        f"prepared/approved-tree/{APPROVED_TREE_BICEP_PATH}",
    )
    raw = tuple(
        read_bound_prepared_artifact(run_dir, relative_path)
        for relative_path in relative_paths
    )
    if raw == (None, None, None, None):
        prepared_root = run_dir / "prepared"
        if prepared_root.is_symlink() or any(
            (run_dir / relative_path).is_symlink()
            for relative_path in relative_paths
        ):
            return None, "INTERRUPTION_BASELINE_BINDING_INVALID"
        return None, None
    if any(value is None for value in raw):
        return None, "INTERRUPTION_BASELINE_BINDING_INVALID"
    raw_manifest, raw_template, raw_parameters, raw_tree_template = raw
    assert raw_manifest is not None
    assert raw_template is not None
    assert raw_parameters is not None
    assert raw_tree_template is not None
    try:
        manifest = json.loads(raw_manifest)
        template = json.loads(raw_template)
        parameters = json.loads(raw_parameters)
    except (TypeError, ValueError):
        return None, "INTERRUPTION_BASELINE_BINDING_INVALID"
    if (
        not isinstance(manifest, dict)
        or set(manifest) != MANIFEST_KEYS
        or manifest.get("schema_version") != PREPARED_MANIFEST_SCHEMA
        or manifest.get("activation_hash") != request.expected_activation_hash
        or manifest.get("approved_commit_sha") != request.approved_commit
        or manifest.get("approved_tree_sha") != request.approved_tree
        or manifest.get("activation_hash") != state.get("activation_hash")
    ):
        return None, "INTERRUPTION_BASELINE_BINDING_MISMATCH"
    try:
        tree_inspection = (approved_tree_source or GitApprovedTreeSource()).inspect(
            repo_root,
            approved_commit=request.approved_commit,
            approved_tree=request.approved_tree,
        )
    except ApprovedGitTreeError:
        return None, "INTERRUPTION_BASELINE_GIT_PROVENANCE_INVALID"
    tree_bicep_sha256 = tree_inspection.file_sha256.get(
        APPROVED_TREE_BICEP_PATH
    )
    if (
        manifest.get("approved_tree_snapshot_sha256")
        != tree_inspection.manifest_sha256
        or tree_bicep_sha256 != hashlib.sha256(raw_template).hexdigest()
        or hashlib.sha256(raw_tree_template).hexdigest() != tree_bicep_sha256
        or raw_tree_template != raw_template
    ):
        return None, "INTERRUPTION_BASELINE_GIT_PROVENANCE_MISMATCH"

    manifest_base = {
        key: manifest[key]
        for key in MANIFEST_KEYS
        if key != "prepared_inputs_sha256"
    }
    digest_keys = MANIFEST_KEYS - {
        "schema_version",
        "approved_commit_sha",
        "approved_tree_sha",
        "activation_hash",
    }
    if (
        any(
            not isinstance(manifest.get(key), str)
            or not runner._SHA256_RE.fullmatch(manifest[key])
            for key in digest_keys
        )
        or manifest["prepared_inputs_sha256"]
        != compact_sha256_json(manifest_base)
        or hashlib.sha256(raw_template).hexdigest()
        != manifest["bicep_snapshot_sha256"]
        or hashlib.sha256(raw_parameters).hexdigest()
        != manifest["bicep_parameters_snapshot_sha256"]
    ):
        return None, "INTERRUPTION_BASELINE_BINDING_MISMATCH"
    metadata = template.get("metadata") if isinstance(template, dict) else None
    generator = metadata.get("_generator") if isinstance(metadata, dict) else None
    template_hash = generator.get("templateHash") if isinstance(generator, dict) else None
    resources = template.get("resources") if isinstance(template, dict) else None
    parameter_values = parameters.get("parameters") if isinstance(parameters, dict) else None
    if (
        not isinstance(template_hash, str)
        or not template_hash.isdigit()
        or not isinstance(resources, list)
        or len(resources) != 12
        or not isinstance(parameter_values, dict)
    ):
        return None, "INTERRUPTION_BASELINE_BINDING_INVALID"
    try:
        canonical_parameters = canonical_parameters_from_wrappers(parameter_values)
        type_counts = Counter(
            str(resource["type"]).lower()
            for resource in resources
            if isinstance(resource, dict)
        )
    except (KeyError, TypeError, ValueError):
        return None, "INTERRUPTION_BASELINE_BINDING_INVALID"
    expected_parameter_keys = set(EXPECTED_PARAMETER_VALUES) | {
        "bffApiAudience"
    }
    if (
        set(canonical_parameters) != expected_parameter_keys
        or not _UUID_RE.fullmatch(
            str(canonical_parameters.get("bffApiAudience", {}).get("value", ""))
        )
        or any(
            canonical_parameters.get(key) != {"value": value}
            for key, value in EXPECTED_PARAMETER_VALUES.items()
        )
        or dict(sorted(type_counts.items())) != EXPECTED_DEPLOYMENT_TYPE_COUNTS
    ):
        return None, "INTERRUPTION_BASELINE_BINDING_INVALID"
    expectation = {
        "schema_version": EXPECTATION_SCHEMA,
        "activation_hash": request.expected_activation_hash,
        "approved_commit_sha": request.approved_commit,
        "approved_tree_sha": request.approved_tree,
        "prepared_inputs_sha256": manifest["prepared_inputs_sha256"],
        "prepared_inputs_manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "bicep_snapshot_sha256": manifest["bicep_snapshot_sha256"],
        "bicep_parameters_snapshot_sha256": manifest[
            "bicep_parameters_snapshot_sha256"
        ],
        "azure_template_hash": template_hash,
        "template_resource_graph_sha256": runner._sha256_json(resources),
        "deployment_name": DEPLOYMENT_NAME,
        "deployment_parameters_sha256": compact_sha256_json(
            canonical_parameters
        ),
        "bff_api_audience": str(
            canonical_parameters["bffApiAudience"]["value"]
        ).lower(),
        "deployment_type_counts": dict(sorted(type_counts.items())),
    }
    if set(expectation) != EXPECTATION_KEYS:
        return None, "INTERRUPTION_BASELINE_BINDING_INVALID"
    return expectation, None


def exact_baseline_matches(
    inventory: object,
    deployment: object,
    operations: object,
    identity_binding: object,
    live_resource_state: object,
    expectation: dict[str, Any],
) -> bool:
    if not _deployment_matches(deployment, expectation):
        return False
    if not isinstance(operations, list) or len(operations) != 12:
        return False
    operation_counts = Counter()
    operation_ids: set[str] = set()
    for operation in operations:
        if (
            not isinstance(operation, dict)
            or set(operation) != {"id", "type", "provisioning_state"}
            or operation.get("provisioning_state") != "Succeeded"
            or not isinstance(operation.get("id"), str)
            or not isinstance(operation.get("type"), str)
        ):
            return False
        operation_id = operation["id"]
        if not operation_id or operation_id in operation_ids:
            return False
        operation_ids.add(operation_id)
        operation_counts[operation["type"]] += 1
    graph_targets = resource_graph_visible_targets(inventory, operations)
    if (
        graph_targets is None
        or dict(sorted(operation_counts.items()))
        != expectation["deployment_type_counts"]
        or not _operation_targets_match(operations, inventory)
        or live_resource_state != {
            "schema_version": (
                "nac.azure-interruption-live-resource-state/v1"
            ),
            "resource_count": 12,
            "resource_targets_sha256": compact_sha256_json(sorted(
                (
                    {"id": item["id"].lower(), "type": item["type"]}
                    for item in operations
                ),
                key=lambda item: (item["type"], item["id"]),
            )),
            "resource_graph_count": len(graph_targets),
            "resource_graph_targets_sha256": compact_sha256_json(
                graph_targets
            ),
            "security_properties_exact": True,
        }
    ):
        return False
    return _inventory_matches(inventory, deployment, identity_binding)
def _operation_targets_match(
    operations: list[dict[str, Any]], inventory: object
) -> bool:
    if not isinstance(inventory, list):
        return False
    by_type = {
        str(item.get("type")): item
        for item in inventory
        if isinstance(item, dict)
    }
    try:
        identity_id = str(
            by_type["microsoft.managedidentity/userassignedidentities"]["id"]
        ).lower()
        storage_id = str(
            by_type["microsoft.storage/storageaccounts"]["id"]
        ).lower()
        workspace_id = str(
            by_type["microsoft.operationalinsights/workspaces"]["id"]
        ).lower()
        component_id = str(
            by_type["microsoft.insights/components"]["id"]
        ).lower()
        plan_id = str(
            by_type["microsoft.web/serverfarms"]["id"]
        ).lower()
        site_id = str(by_type["microsoft.web/sites"]["id"]).lower()
    except (KeyError, TypeError):
        return False
    expected = {
        "microsoft.managedidentity/userassignedidentities": {identity_id},
        "microsoft.storage/storageaccounts": {storage_id},
        "microsoft.storage/storageaccounts/blobservices": {
            f"{storage_id}/blobservices/default"
        },
        "microsoft.storage/storageaccounts/blobservices/containers": {
            f"{storage_id}/blobservices/default/containers/{DEPLOYMENT_CONTAINER_NAME}"
        },
        "microsoft.operationalinsights/workspaces": {workspace_id},
        "microsoft.insights/components": {component_id},
        "microsoft.insights/components/currentbillingfeatures": {
            f"{component_id}/currentbillingfeatures/basic"
        },
        "microsoft.web/serverfarms": {plan_id},
        "microsoft.web/sites": {site_id},
        "microsoft.web/sites/config": {f"{site_id}/config/appsettings"},
    }
    actual: dict[str, set[str]] = {}
    role_assignment_parents: set[str] = set()
    for operation in operations:
        operation_type = str(operation.get("type", ""))
        target_id = str(operation.get("id", "")).lower()
        if operation_type == "microsoft.authorization/roleassignments":
            marker = "/providers/microsoft.authorization/roleassignments/"
            if marker not in target_id:
                return False
            parent, assignment_id = target_id.rsplit(marker, 1)
            if parent not in {storage_id, component_id} or not _UUID_RE.fullmatch(
                assignment_id
            ):
                return False
            role_assignment_parents.add(parent)
        else:
            actual.setdefault(operation_type, set()).add(target_id)
    return bool(
        actual == expected
        and role_assignment_parents == {storage_id, component_id}
    )

def _deployment_matches(deployment: object, expectation: dict[str, Any]) -> bool:
    if not isinstance(deployment, dict) or set(deployment) != {
        "name", "resource_group", "provisioning_state", "mode",
        "template_hash", "parameters_sha256", "bff_api_audience",
        "outputs",
    }:
        return False
    return bool(
        deployment.get("name") == expectation["deployment_name"]
        and deployment.get("resource_group") == RESOURCE_GROUP
        and deployment.get("provisioning_state") == "Succeeded"
        and deployment.get("mode") == "Incremental"
        and deployment.get("template_hash") == expectation["azure_template_hash"]
        and deployment.get("parameters_sha256")
        == expectation["deployment_parameters_sha256"]
        and deployment.get("bff_api_audience")
        == expectation["bff_api_audience"]
    )


def _inventory_matches(
    inventory: object,
    deployment: dict[str, Any],
    identity_binding: object,
) -> bool:
    if not isinstance(inventory, list) or len(inventory) != 7:
        return False
    by_type: dict[str, dict[str, Any]] = {}
    keys = {
        "id", "name", "type", "resource_group",
        "location", "kind", "sku", "tags",
        "managed_by", "properties",
    }
    for item in inventory:
        if (
            not isinstance(item, dict)
            or set(item) != keys
            or item.get("type") in by_type
        ):
            return False
        by_type[item.get("type")] = item
    if set(by_type) != EXPECTED_TOP_LEVEL_TYPES:
        return False
    identity = by_type["microsoft.managedidentity/userassignedidentities"]
    name = identity.get("name")
    prefix = "id-nac-bff-test-"
    if not isinstance(name, str) or not name.startswith(prefix):
        return False
    token = name[len(prefix):]
    if re.fullmatch(r"[a-z0-9]+", token or "") is None:
        return False
    names = {
        "microsoft.managedidentity/userassignedidentities": name,
        "microsoft.storage/storageaccounts": f"stnacbff{token}",
        "microsoft.operationalinsights/workspaces": f"log-nac-bff-test-{token}",
        "microsoft.insights/components": f"appi-nac-bff-test-{token}",
        "microsoft.web/serverfarms": f"plan-nac-bff-test-{token}",
        "microsoft.web/sites": FUNCTION_APP,
        "microsoft.insights/actiongroups": SMART_DETECTION_NAME,
    }
    prefix_id = (
        f"/subscriptions/{SUBSCRIPTION_ID}/resourcegroups/"
        f"{RESOURCE_GROUP}/providers/"
    ).lower()
    for resource_type, item in by_type.items():
        expected_name = names[resource_type]
        if (
            item.get("name") != expected_name
            or item.get("resource_group") != RESOURCE_GROUP
            or str(item.get("id", "")).lower()
            != f"{prefix_id}{resource_type}/{expected_name}".lower()
        ):
            return False
        expected_properties = EXPECTED_RESOURCE_PROPERTIES.get(resource_type)
        if expected_properties is not None:
            expected_kind = expected_properties.get("kind")
            expected_sku = expected_properties.get("sku")
            if (
                str(item.get("kind", "")).lower()
                != str(expected_kind).lower()
                or (
                    "sku" in expected_properties
                    and item.get("sku") != expected_sku
                )
            ):
                return False
        if item.get("managed_by") is not None:
            return False
        if resource_type == "microsoft.insights/actiongroups":
            if (
                str(item.get("location", "")).lower() != "global"
                or item.get("tags") not in ({}, None)
                or item.get("kind") is not None
                or item.get("sku") is not None
                or not _smart_detection_properties_match(
                    item.get("properties")
                )
            ):
                return False
        elif item.get("properties") is not None:
            return False
        elif (
            str(item.get("location", "")).lower() != LOCATION
            or item.get("tags") != RESOURCE_TAGS
        ):
            return False
    outputs = deployment.get("outputs")
    if not isinstance(outputs, dict):
        return False
    outputs_match = bool(
        set(outputs) == {
            "function_app_resource_id",
            "function_app_host_name",
            "managed_identity_resource_id",
            "managed_identity_client_id",
            "managed_identity_principal_id",
        }
        and str(outputs["function_app_resource_id"]).lower()
        == str(by_type["microsoft.web/sites"]["id"]).lower()
        and outputs["function_app_host_name"]
        == f"{FUNCTION_APP}.azurewebsites.net"
        and str(outputs["managed_identity_resource_id"]).lower()
        == str(identity["id"]).lower()
        and _UUID_RE.fullmatch(
            str(outputs["managed_identity_client_id"])
        )
        and _UUID_RE.fullmatch(
            str(outputs["managed_identity_principal_id"])
        )
    )
    return bool(
        outputs_match
        and str(deployment.get("bff_api_audience", "")).lower()
        != str(outputs.get("managed_identity_client_id", "")).lower()
        and _identity_binding_matches(identity_binding, identity, outputs)
    )



def _smart_detection_properties_match(value: object) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "groupShortName", "enabled", *SMART_DETECTION_RECEIVER_COUNTS
    }:
        return False
    if value.get("groupShortName") != "SmartDetect" or value.get("enabled") is not True:
        return False
    for name, count in SMART_DETECTION_RECEIVER_COUNTS.items():
        receivers = value.get(name)
        if not isinstance(receivers, list) or len(receivers) != count:
            return False
    return bool(
        sorted(
            value["armRoleReceivers"], key=lambda item: str(item.get("name"))
        )
        == sorted(
            SMART_DETECTION_ARM_ROLE_RECEIVERS,
            key=lambda item: item["name"],
        )
    )

def _identity_binding_matches(
    value: object,
    identity_resource: dict[str, Any],
    deployment_outputs: dict[str, Any],
) -> bool:
    if not isinstance(value, dict) or set(value) != {
        "managed_identity", "function_app"
    }:
        return False
    managed = value.get("managed_identity")
    function_app = value.get("function_app")
    if (
        not isinstance(managed, dict)
        or set(managed) != {
            "id", "name", "client_id", "principal_id", "tenant_id"
        }
        or not isinstance(function_app, dict)
        or set(function_app) != {"type", "user_assigned_identities"}
        or function_app.get("type") != "UserAssigned"
    ):
        return False
    assignments = function_app.get("user_assigned_identities")
    if not isinstance(assignments, list) or len(assignments) != 1:
        return False
    assignment = assignments[0]
    if not isinstance(assignment, dict) or set(assignment) != {
        "id", "client_id", "principal_id"
    }:
        return False
    identity_id = str(identity_resource.get("id", "")).lower()
    client_id = deployment_outputs.get("managed_identity_client_id")
    principal_id = deployment_outputs.get("managed_identity_principal_id")
    return bool(
        str(managed.get("id", "")).lower() == identity_id
        and managed.get("name") == identity_resource.get("name")
        and managed.get("client_id") == client_id
        and managed.get("principal_id") == principal_id
        and managed.get("tenant_id") == TENANT_ID
        and str(assignment.get("id", "")).lower() == identity_id
        and assignment.get("client_id") == client_id
        and assignment.get("principal_id") == principal_id
    )
