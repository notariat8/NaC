#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


BOOTSTRAP_DATA_ACTIONS = {
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
}
RUNTIME_DATA_ACTIONS = {
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
}
EXPECTED_RESOURCE_TYPES = {
    "Microsoft.Storage/storageAccounts": 1,
    "Microsoft.Storage/storageAccounts/blobServices": 1,
    "Microsoft.Storage/storageAccounts/blobServices/containers": 1,
    "Microsoft.Authorization/roleDefinitions": 2,
    "Microsoft.Authorization/roleAssignments": 2,
}
EXPECTED_RESOURCE_API_VERSIONS = {
    "Microsoft.Storage/storageAccounts": "2023-05-01",
    "Microsoft.Storage/storageAccounts/blobServices": "2023-05-01",
    "Microsoft.Storage/storageAccounts/blobServices/containers": "2023-05-01",
    "Microsoft.Authorization/roleDefinitions": "2022-04-01",
    "Microsoft.Authorization/roleAssignments": "2022-04-01",
}
EXPECTED_RESOURCE_DEPENDENCIES = {
    "Microsoft.Storage/storageAccounts": [],
    "Microsoft.Storage/storageAccounts/blobServices": [
        "[resourceId('Microsoft.Storage/storageAccounts', "
        "variables('validatedStorageAccountName'))]"
    ],
    "Microsoft.Storage/storageAccounts/blobServices/containers": [
        "[resourceId('Microsoft.Storage/storageAccounts/blobServices', "
        "variables('validatedStorageAccountName'), 'default')]"
    ],
}
EXPECTED_PARAMETER_SCHEMAS = {
    "location": {
        "type": "string",
        "defaultValue": "germanywestcentral",
        "allowedValues": ["germanywestcentral"],
        "metadata": {
            "description": (
                "Azure region for the dedicated coordination storage account."
            )
        },
    },
    "tenantId": {
        "type": "string",
        "metadata": {
            "description": "Exact Entra tenant bound by the combined owner approval."
        },
    },
    "subscriptionId": {
        "type": "string",
        "metadata": {
            "description": (
                "Exact Azure subscription bound by the combined owner approval."
            )
        },
    },
    "resourceGroupName": {
        "type": "string",
        "metadata": {
            "description": (
                "Exact Azure resource group bound by the combined owner approval."
            )
        },
    },
    "deploymentMode": {
        "type": "string",
        "defaultValue": "Incremental",
        "allowedValues": ["Incremental"],
        "metadata": {
            "description": (
                "Deployment mode binding. The CLI and template accept Incremental only."
            )
        },
    },
    "storageAccountName": {
        "type": "string",
        "minLength": 3,
        "maxLength": 24,
        "metadata": {
            "description": (
                "Globally unique name for the dedicated performance-coordination "
                "storage account."
            )
        },
    },
    "bffStorageAccountResourceId": {
        "type": "string",
        "metadata": {
            "description": (
                "Authoritative ARM resource ID of the existing BFF host/deployment "
                "storage account. The account name is derived from this ID."
            )
        },
    },
    "wormStorageAccountResourceId": {
        "type": "string",
        "metadata": {
            "description": (
                "Authoritative ARM resource ID of the existing WORM evidence storage "
                "account. The account name is derived from this ID."
            )
        },
    },
    "bootstrapPrincipalId": {
        "type": "string",
        "metadata": {
            "description": (
                "Object ID of the dedicated Entra service principal used only to "
                "bootstrap the bound blob with read and add. It must differ from "
                "runtimePrincipalId and receives no blob write or delete capability."
            )
        },
    },
    "runtimePrincipalId": {
        "type": "string",
        "metadata": {
            "description": (
                "Object ID of the dedicated Entra service principal used only at "
                "runtime with blob read and write. It must differ from "
                "bootstrapPrincipalId and receives no blob add or delete capability."
            )
        },
    },
    "bootstrapCertificateSha256": {
        "type": "string",
        "minLength": 64,
        "maxLength": 64,
        "metadata": {
            "description": (
                "SHA-256 of the bootstrap application certificate bound by the owner approval."
            )
        },
    },
    "runtimeCertificateSha256": {
        "type": "string",
        "minLength": 64,
        "maxLength": 64,
        "metadata": {
            "description": (
                "SHA-256 of the separate runtime application certificate bound by the owner approval."
            )
        },
    },
    "allowedClientIpAddress": {
        "type": "string",
        "metadata": {
            "description": (
                "Single public IPv4 address allowed to reach the dedicated data plane "
                "during the approved run."
            )
        },
    },
    "targetBindingSha256": {
        "type": "string",
        "minLength": 64,
        "maxLength": 64,
        "metadata": {
            "description": "Hash binding used as the only lease blob basename."
        },
    },
    "tags": {
        "type": "object",
        "defaultValue": {},
        "metadata": {
            "description": (
                "Additional non-sensitive tags. Coordination boundary tags cannot "
                "be overridden."
            )
        },
    },
}
EXPECTED_PARAMETERS = set(EXPECTED_PARAMETER_SCHEMAS)
EXPECTED_BICEP_VERSION = "0.45.15.27210"
EXPECTED_MANDATORY_TAGS = {
    "blobPrecreation": "owner-gated-before-runtime",
    "dataClassification": "synthetic-only",
    "environment": "test",
    "managedBy": "bicep",
    "storageBoundary": "dedicated-from-bff-and-worm",
    "targetBindingSha256": "[parameters('targetBindingSha256')]",
    "workload": "nac-bff-performance-coordination",
}
EXPECTED_EXAMPLE_PARAMETERS = {
    "location": "germanywestcentral",
    "tenantId": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
    "subscriptionId": "37cd9645-6cb9-4278-88ee-e80377cd951c",
    "resourceGroupName": "rg-nac-bff-test",
    "deploymentMode": "Incremental",
    "storageAccountName": "stnacperflease001",
    "bffStorageAccountResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/"
        "storageAccounts/stnacbffoffline001"
    ),
    "wormStorageAccountResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-worm/providers/Microsoft.Storage/"
        "storageAccounts/stnacwormoffline001"
    ),
    "bootstrapPrincipalId": "11111111-2222-4333-8444-555555555555",
    "runtimePrincipalId": "66666666-7777-4888-8999-aaaaaaaaaaaa",
    "bootstrapCertificateSha256": "1" * 64,
    "runtimeCertificateSha256": "2" * 64,
    "allowedClientIpAddress": "203.0.113.10",
    "targetBindingSha256": "1" * 64,
    "tags": {
        "owner": "replace-before-owner-gated-deployment",
        "purpose": "offline-contract-baseline",
    },
}
EXPECTED_VALIDATED_DEPLOYMENT_SCOPE = (
    "[if(and(and(and(equals(tenant().tenantId, parameters('tenantId')), "
    "equals(subscription().subscriptionId, parameters('subscriptionId'))), "
    "equals(resourceGroup().name, parameters('resourceGroupName'))), "
    "equals(parameters('deploymentMode'), 'Incremental')), "
    "format('{0}/{1}/{2}', parameters('tenantId'), parameters('subscriptionId'), "
    "parameters('resourceGroupName')), fail('Performance coordination deployment "
    "scope does not match the owner-bound tenant, subscription, and resource group.'))]"
)
EXPECTED_VALIDATED_STORAGE_ACCOUNT_NAME = (
    "[if(and(and(and(and(and(and(not(empty(variables('validatedDeploymentScope'))), "
    "not(equals(toLower(variables('coordinationStorageAccountResourceId')), "
    "toLower(variables('validatedBffStorageAccountResourceId'))))), "
    "not(equals(toLower(variables('coordinationStorageAccountResourceId')), "
    "toLower(variables('validatedWormStorageAccountResourceId'))))), "
    "not(equals(toLower(variables('validatedBffStorageAccountResourceId')), "
    "toLower(variables('validatedWormStorageAccountResourceId'))))), "
    "not(equals(toLower(parameters('storageAccountName')), "
    "toLower(variables('bffStorageAccountName'))))), "
    "not(equals(toLower(parameters('storageAccountName')), "
    "toLower(variables('wormStorageAccountName'))))), "
    "not(equals(toLower(variables('bffStorageAccountName')), "
    "toLower(variables('wormStorageAccountName'))))), "
    "parameters('storageAccountName'), fail('Performance coordination, BFF, and "
    "WORM storage accounts must be pairwise distinct.'))]"
)
EXPECTED_STORAGE_RESOURCE_NAME = "[variables('validatedStorageAccountName')]"
EXPECTED_STORAGE_RESOURCE_LOCATION = "[parameters('location')]"
EXPECTED_BLOB_SERVICE_RESOURCE_NAME = (
    "[format('{0}/{1}', variables('validatedStorageAccountName'), 'default')]"
)
EXPECTED_CONTAINER_RESOURCE_NAME = (
    "[format('{0}/{1}/{2}', variables('validatedStorageAccountName'), 'default', "
    "variables('containerName'))]"
)
EXPECTED_ROLE_ASSIGNABLE_SCOPES = ["[resourceGroup().id]"]
EXPECTED_ROLE_ASSIGNMENT_SCOPE = (
    "[resourceId('Microsoft.Storage/storageAccounts/blobServices/containers', "
    "variables('validatedStorageAccountName'), 'default', variables('containerName'))]"
)

def validate_template(template: Mapping[str, Any]) -> list[str]:
    """Return fail-closed errors for an emitted coordination ARM template."""

    errors: list[str] = []
    generator = template.get("metadata")
    generator = generator.get("_generator") if isinstance(generator, Mapping) else None
    if (
        template.get("$schema")
        != "https://schema.management.azure.com/schemas/2019-04-01/"
        "deploymentTemplate.json#"
        or template.get("contentVersion") != "1.0.0.0"
        or not isinstance(generator, Mapping)
        or generator.get("name") != "bicep"
        or generator.get("version") != EXPECTED_BICEP_VERSION
    ):
        errors.append("ARM template header or pinned Bicep generator differs")
    parameters = template.get("parameters")
    variables = template.get("variables")
    resources = template.get("resources")
    outputs = template.get("outputs")
    if not isinstance(parameters, Mapping):
        return ["parameters must be an object"]
    if set(parameters) != EXPECTED_PARAMETERS:
        errors.append("parameter set differs from the bound coordination contract")
    elif parameters != EXPECTED_PARAMETER_SCHEMAS:
        errors.append("parameter schemas differ from the bound coordination contract")
    if "bffStorageAccountName" in parameters or "wormStorageAccountName" in parameters:
        errors.append("storage account names must be derived from authoritative IDs")
    if not isinstance(variables, Mapping):
        return [*errors, "variables must be an object"]
    if not isinstance(resources, list):
        return [*errors, "resources must be an array"]
    if not isinstance(outputs, Mapping):
        return [*errors, "outputs must be an object"]

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for resource in resources:
        if not isinstance(resource, Mapping) or not isinstance(resource.get("type"), str):
            errors.append("every resource must have a string type")
            continue
        grouped.setdefault(resource["type"], []).append(resource)
    actual_counts = {name: len(items) for name, items in grouped.items()}
    if actual_counts != EXPECTED_RESOURCE_TYPES:
        errors.append("resource type/count set differs from the seven-resource contract")

    for resource_type in (
        "Microsoft.Storage/storageAccounts",
        "Microsoft.Storage/storageAccounts/blobServices",
        "Microsoft.Storage/storageAccounts/blobServices/containers",
    ):
        _validate_resource_emission(
            _only(grouped, resource_type), resource_type, errors
        )

    _validate_id_binding_variables(variables, errors)
    _validate_storage(_only(grouped, "Microsoft.Storage/storageAccounts"), errors)
    _validate_blob_service(
        _only(grouped, "Microsoft.Storage/storageAccounts/blobServices"), errors
    )
    _validate_container(
        _only(
            grouped,
            "Microsoft.Storage/storageAccounts/blobServices/containers",
        ),
        errors,
    )
    _validate_role_definitions(
        grouped.get("Microsoft.Authorization/roleDefinitions", []), errors
    )
    _validate_role_assignments(
        grouped.get("Microsoft.Authorization/roleAssignments", []), errors
    )
    _validate_outputs(outputs, errors)
    return errors


def validate_parameters_artifact(
    artifact: Mapping[str, Any], template: Mapping[str, Any]
) -> list[str]:
    """Validate the build-params wrapper and its template binding."""

    errors: list[str] = []
    if set(artifact) != {"parametersJson", "templateJson", "templateSpecId"}:
        return ["compiled parameter artifact shape differs"]
    if artifact.get("templateSpecId") is not None:
        errors.append("compiled parameter artifact unexpectedly targets a template spec")
    parameters_json = artifact.get("parametersJson")
    template_json = artifact.get("templateJson")
    if not isinstance(parameters_json, str) or not isinstance(template_json, str):
        return [*errors, "compiled parameter artifact payloads must be JSON strings"]
    try:
        parameters = json.loads(parameters_json)
        embedded_template = json.loads(template_json)
    except json.JSONDecodeError:
        return [*errors, "compiled parameter artifact contains invalid nested JSON"]
    if embedded_template != template:
        errors.append("compiled parameter artifact embeds a different ARM template")
    if not isinstance(parameters, Mapping) or set(parameters) != {
        "$schema",
        "contentVersion",
        "parameters",
    }:
        return [*errors, "compiled deployment parameters shape differs"]
    if (
        parameters.get("$schema")
        != "https://schema.management.azure.com/schemas/2019-04-01/"
        "deploymentParameters.json#"
        or parameters.get("contentVersion") != "1.0.0.0"
    ):
        errors.append("compiled deployment parameters header differs")
    values = parameters.get("parameters")
    if not isinstance(values, Mapping) or set(values) != EXPECTED_PARAMETERS:
        return [*errors, "compiled deployment parameter set differs"]
    if any(
        not isinstance(entry, Mapping) or set(entry) != {"value"}
        for entry in values.values()
    ):
        errors.append("compiled deployment parameter entries are not exact values")
    elif {name: entry["value"] for name, entry in values.items()} != (
        EXPECTED_EXAMPLE_PARAMETERS
    ):
        errors.append("compiled deployment parameter values differ")
    return errors


def _validate_id_binding_variables(
    variables: Mapping[str, Any], errors: list[str]
) -> None:
    if (
        variables.get("validatedDeploymentScope")
        != EXPECTED_VALIDATED_DEPLOYMENT_SCOPE
    ):
        errors.append("validated deployment scope guard differs")
    for prefix in ("bff", "worm"):
        segments = variables.get(f"{prefix}StorageAccountResourceIdSegments")
        name = variables.get(f"{prefix}StorageAccountName")
        validated = variables.get(f"validated{prefix.title()}StorageAccountResourceId")
        if not _expression_contains(
            segments, f"parameters('{prefix}StorageAccountResourceId')"
        ):
            errors.append(f"{prefix} resource ID is not split for name derivation")
        if not _expression_contains(name, f"{prefix}StorageAccountResourceIdSegments"):
            errors.append(f"{prefix} account name is not derived from its resource ID")
        for marker in (
            "Microsoft.Storage/storageAccounts",
            "subscriptionId",
            f"{prefix}StorageAccountResourceId",
            "fail(",
        ):
            if not _expression_contains(validated, marker):
                errors.append(f"{prefix} authoritative ID validation lacks {marker}")
    if (
        variables.get("validatedStorageAccountName")
        != EXPECTED_VALIDATED_STORAGE_ACCOUNT_NAME
    ):
        errors.append("validated storage account isolation guard differs")
    expected_actions = {
        "blobReadDataAction": (
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
        ),
        "blobAddDataAction": (
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action"
        ),
        "blobWriteDataAction": (
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
        ),
    }
    for name, expected in expected_actions.items():
        if variables.get(name) != expected:
            errors.append(f"{name} differs")
    for condition_name, action_name in (
        ("exactBootstrapLeaseBlobCondition", "blobAddDataAction"),
        ("exactRuntimeLeaseBlobCondition", "blobWriteDataAction"),
    ):
        condition = variables.get(condition_name)
        if not all(
            _expression_contains(condition, marker)
            for marker in (
                "blobReadDataAction",
                action_name,
                "containerName",
                "leaseBlobPath",
                "StringEquals",
            )
        ) or _expression_contains(condition, "StringLike"):
            errors.append(f"{condition_name} expression differs")
    for principal_name, expected_parameter in (
        ("validatedBootstrapPrincipalId", "bootstrapPrincipalId"),
        ("validatedRuntimePrincipalId", "runtimePrincipalId"),
    ):
        expression = variables.get(principal_name)
        if not all(
            _expression_contains(expression, marker)
            for marker in (
                expected_parameter,
                "bootstrapPrincipalId",
                "runtimePrincipalId",
                "bootstrapCertificateSha256",
                "runtimeCertificateSha256",
                "fail(",
            )
        ):
            errors.append(f"{principal_name} separation guard differs")
    if variables.get("mandatoryResourceTags") != EXPECTED_MANDATORY_TAGS:
        errors.append("mandatory effective tags differ from runtime canonical tags")
    if variables.get("resourceTags") != (
        "[union(parameters('tags'), variables('mandatoryResourceTags'))]"
    ):
        errors.append("effective tags do not override caller tags canonically")


def _validate_resource_emission(
    resource: Mapping[str, Any] | None,
    resource_type: str,
    errors: list[str],
) -> None:
    if resource is None:
        return
    if resource.get("apiVersion") != EXPECTED_RESOURCE_API_VERSIONS[resource_type]:
        errors.append(f"{resource_type} apiVersion differs")
    dependencies = resource.get("dependsOn", [])
    expected_dependencies = EXPECTED_RESOURCE_DEPENDENCIES[resource_type]
    if (
        not isinstance(dependencies, list)
        or any(not isinstance(dependency, str) for dependency in dependencies)
        or len(dependencies) != len(set(dependencies))
        or set(dependencies) != set(expected_dependencies)
    ):
        errors.append(f"{resource_type} dependsOn set differs")


def _validate_storage(
    resource: Mapping[str, Any] | None, errors: list[str]
) -> None:
    if resource is None:
        return
    if resource.get("name") != EXPECTED_STORAGE_RESOURCE_NAME:
        errors.append("storage resource name is not the validated account name")
    if resource.get("location") != EXPECTED_STORAGE_RESOURCE_LOCATION:
        errors.append("storage resource location is not the bound location parameter")
    if resource.get("kind") != "StorageV2" or resource.get("sku") != {
        "name": "Standard_LRS"
    }:
        errors.append("storage kind or SKU differs")
    if resource.get("tags") != "[variables('resourceTags')]":
        errors.append("storage does not use canonical effective tags")
    expected_properties = {
        "accessTier": "Hot",
        "allowBlobPublicAccess": False,
        "allowCrossTenantReplication": False,
        "allowSharedKeyAccess": False,
        "defaultToOAuthAuthentication": True,
        "isHnsEnabled": False,
        "minimumTlsVersion": "TLS1_2",
        "publicNetworkAccess": "Enabled",
        "supportsHttpsTrafficOnly": True,
        "networkAcls": {
            "bypass": "None",
            "defaultAction": "Deny",
            "ipRules": [
                {
                    "action": "Allow",
                    "value": "[parameters('allowedClientIpAddress')]",
                }
            ],
            "resourceAccessRules": [],
            "virtualNetworkRules": [],
        },
    }
    properties = resource.get("properties")
    network_acls = (
        properties.get("networkAcls") if isinstance(properties, Mapping) else None
    )
    if (
        not isinstance(network_acls, Mapping)
        or network_acls.get("resourceAccessRules") != []
    ):
        errors.append("networkAcls.resourceAccessRules must be exactly empty")
    if resource.get("properties") != expected_properties:
        errors.append("storage properties or network ACLs are not exact")


def _validate_blob_service(
    resource: Mapping[str, Any] | None, errors: list[str]
) -> None:
    if resource is None:
        return
    if resource.get("name") != EXPECTED_BLOB_SERVICE_RESOURCE_NAME:
        errors.append("blob service resource name differs")
    properties = resource.get("properties")
    if not isinstance(properties, Mapping):
        errors.append("blob service properties are missing")
        return
    if properties.get("isVersioningEnabled") is not False:
        errors.append("blob service versioning must be disabled")
    for name in ("deleteRetentionPolicy", "containerDeleteRetentionPolicy"):
        policy = properties.get(name)
        if not isinstance(policy, Mapping) or policy.get("enabled") is not False:
            errors.append(f"blob service {name} must be disabled")


def _validate_container(
    resource: Mapping[str, Any] | None, errors: list[str]
) -> None:
    if resource is None:
        return
    if resource.get("name") != EXPECTED_CONTAINER_RESOURCE_NAME:
        errors.append("lease container resource name differs")
    properties = resource.get("properties")
    if not isinstance(properties, Mapping):
        errors.append("lease container properties are missing")
        return
    if properties.get("publicAccess") != "None":
        errors.append("lease container public access differs")
    metadata = properties.get("metadata")
    expected_literals = {
        "nac_schema_version": "nac.azure-bff-performance-coordination/v1",
        "data_classification": "synthetic-only",
        "lease_blob_type": "BlockBlob",
        "lease_blob_content_length": "0",
        "lease_blob_bootstrap": "owner-gated-put-if-absent-before-runtime",
        "bootstrap_authorization": "blob-read-plus-add-only-no-write-no-delete",
        "runtime_authorization": "blob-read-plus-write-only-no-add-no-delete",
        "azure_blob_write_authorization": (
            "runtime-write-includes-create-overwrite-lease-and-break"
        ),
        "operation_restriction_boundary": (
            "sealed-app-api-defense-in-depth-not-azure-enforced"
        ),
        "principal_separation": (
            "distinct-owner-bound-bootstrap-and-runtime-principals"
        ),
    }
    if not isinstance(metadata, Mapping):
        errors.append("lease container metadata is missing")
        return
    for name, expected in expected_literals.items():
        if metadata.get(name) != expected:
            errors.append(f"lease container metadata {name} differs")
    if not _expression_contains(metadata.get("lease_blob_path"), "leaseBlobPath"):
        errors.append("lease container metadata does not bind the exact blob path")


def _validate_role_definitions(
    resources: list[Mapping[str, Any]], errors: list[str]
) -> None:
    expected = {
        "bootstrapLeaseDataRoleDefinitionGuid": BOOTSTRAP_DATA_ACTIONS,
        "runtimeLeaseDataRoleDefinitionGuid": RUNTIME_DATA_ACTIONS,
    }
    selected: dict[str, Mapping[str, Any]] = {}
    for resource in resources:
        name = resource.get("name")
        matches = [key for key in expected if _expression_contains(name, key)]
        if len(matches) != 1 or matches[0] in selected:
            errors.append("custom role identity is ambiguous")
            continue
        selected[matches[0]] = resource
    if set(selected) != set(expected):
        errors.append("bootstrap/runtime custom roles are incomplete")
        return
    for identity, actions in expected.items():
        resource = selected[identity]
        if resource.get("apiVersion") != "2022-04-01":
            errors.append(f"{identity} apiVersion differs")
        if resource.get("dependsOn", []) != []:
            errors.append(f"{identity} dependencies differ")
        properties = resource.get("properties")
        permissions = (
            properties.get("permissions")
            if isinstance(properties, Mapping)
            else None
        )
        if (
            not isinstance(properties, Mapping)
            or properties.get("type") != "CustomRole"
            or properties.get("assignableScopes")
            != EXPECTED_ROLE_ASSIGNABLE_SCOPES
            or not isinstance(permissions, list)
            or len(permissions) != 1
            or not isinstance(permissions[0], Mapping)
        ):
            errors.append(f"{identity} role shape differs")
            continue
        permission = permissions[0]
        data_actions = permission.get("dataActions")
        if (
            not isinstance(data_actions, list)
            or len(data_actions) != len(set(data_actions))
            or set(data_actions) != actions
        ):
            errors.append(f"{identity} DataActions differ")
        for key in ("actions", "notActions", "notDataActions"):
            if permission.get(key) != []:
                errors.append(f"{identity} {key} must be empty")


def _validate_role_assignments(
    resources: list[Mapping[str, Any]], errors: list[str]
) -> None:
    expected = {
        "bootstrap": {
            "principal": "validatedBootstrapPrincipalId",
            "role": "bootstrapLeaseDataRoleDefinitionGuid",
            "condition": "exactBootstrapLeaseBlobCondition",
        },
        "runtime": {
            "principal": "validatedRuntimePrincipalId",
            "role": "runtimeLeaseDataRoleDefinitionGuid",
            "condition": "exactRuntimeLeaseBlobCondition",
        },
    }
    selected: dict[str, Mapping[str, Any]] = {}
    for resource in resources:
        properties = resource.get("properties")
        principal = properties.get("principalId") if isinstance(properties, Mapping) else None
        matches = [
            key
            for key, values in expected.items()
            if _expression_contains(principal, values["principal"])
        ]
        if len(matches) != 1 or matches[0] in selected:
            errors.append("role assignment identity is ambiguous")
            continue
        selected[matches[0]] = resource
    if set(selected) != set(expected):
        errors.append("bootstrap/runtime role assignments are incomplete")
        return
    for identity, values in expected.items():
        resource = selected[identity]
        properties = resource.get("properties")
        if not isinstance(properties, Mapping):
            errors.append(f"{identity} assignment properties are missing")
            continue
        if (
            resource.get("apiVersion") != "2022-04-01"
            or resource.get("scope") != EXPECTED_ROLE_ASSIGNMENT_SCOPE
            or properties.get("principalType") != "ServicePrincipal"
            or properties.get("conditionVersion") != "2.0"
            or not _expression_contains(properties.get("principalId"), values["principal"])
            or not _expression_contains(properties.get("condition"), values["condition"])
            or not _expression_contains(properties.get("roleDefinitionId"), values["role"])
            or not _expression_contains(resource.get("name"), values["principal"])
            or not _expression_contains(resource.get("name"), values["role"])
            or not _expression_contains(resource.get("name"), "leaseBlobPath")
        ):
            errors.append(f"{identity} role assignment differs")
        dependencies = resource.get("dependsOn")
        if (
            not isinstance(dependencies, list)
            or len(dependencies) != 2
            or not any(_expression_contains(item, "containers") for item in dependencies)
            or not any(_expression_contains(item, values["role"]) for item in dependencies)
        ):
            errors.append(f"{identity} assignment dependencies differ")


def _validate_outputs(outputs: Mapping[str, Any], errors: list[str]) -> None:
    expected_keys = {
        "contractSchemaVersion",
        "storageAccountName",
        "storageAccountResourceId",
        "effectiveTags",
        "bffStorageAccountResourceIdBinding",
        "bffStorageAccountNameBinding",
        "wormStorageAccountResourceIdBinding",
        "wormStorageAccountNameBinding",
        "leaseContainerName",
        "leaseContainerResourceId",
        "leaseBlobPath",
        "leaseBlobUri",
        "requiredLeaseBlobType",
        "requiredLeaseBlobContentLength",
        "targetBindingSha256",
        "bootstrapLeaseDataRoleDefinitionId",
        "runtimeLeaseDataRoleDefinitionId",
        "bootstrapLeaseRoleAssignmentId",
        "runtimeLeaseRoleAssignmentId",
        "bootstrapCertificateSha256Binding",
        "runtimeCertificateSha256Binding",
        "exactBootstrapLeaseBlobCondition",
        "exactRuntimeLeaseBlobCondition",
        "bootstrapAllowedDataActions",
        "runtimeAllowedDataActions",
        "deploymentScopeBinding",
        "blobBootstrapRequired",
        "blobBootstrapExecutedByTemplate",
        "azureRbacWriteAuthorizedOperations",
        "azureRbacOperationRestrictionEnforced",
        "operationRestrictionDefenseInDepth",
        "principalSeparationMode",
    }
    if set(outputs) != expected_keys:
        errors.append("output key set differs from the emitted contract")
    if outputs.get("effectiveTags") != {
        "type": "object",
        "value": "[variables('resourceTags')]",
    }:
        errors.append("effective tags output differs")
    bindings = {
        "storageAccountResourceId": "Microsoft.Storage/storageAccounts",
        "bffStorageAccountResourceIdBinding": "validatedBffStorageAccountResourceId",
        "bffStorageAccountNameBinding": "bffStorageAccountName",
        "wormStorageAccountResourceIdBinding": "validatedWormStorageAccountResourceId",
        "wormStorageAccountNameBinding": "wormStorageAccountName",
        "leaseContainerResourceId": "Microsoft.Storage/storageAccounts/blobServices/containers",
        "bootstrapLeaseDataRoleDefinitionId": "bootstrapLeaseDataRoleDefinitionGuid",
        "runtimeLeaseDataRoleDefinitionId": "runtimeLeaseDataRoleDefinitionGuid",
        "bootstrapLeaseRoleAssignmentId": "Microsoft.Authorization/roleAssignments",
        "runtimeLeaseRoleAssignmentId": "Microsoft.Authorization/roleAssignments",
        "bootstrapCertificateSha256Binding": "bootstrapCertificateSha256",
        "runtimeCertificateSha256Binding": "runtimeCertificateSha256",
        "exactBootstrapLeaseBlobCondition": "exactBootstrapLeaseBlobCondition",
        "exactRuntimeLeaseBlobCondition": "exactRuntimeLeaseBlobCondition",
    }
    for name, marker in bindings.items():
        output = outputs.get(name)
        if (
            not isinstance(output, Mapping)
            or output.get("type") != "string"
            or not _expression_contains(output.get("value"), marker)
        ):
            errors.append(f"output {name} does not preserve {marker}")
    for name, markers in (
        ("bootstrapAllowedDataActions", ("blobReadDataAction", "blobAddDataAction")),
        ("runtimeAllowedDataActions", ("blobReadDataAction", "blobWriteDataAction")),
    ):
        output = outputs.get(name)
        values = output.get("value") if isinstance(output, Mapping) else None
        if (
            not isinstance(output, Mapping)
            or output.get("type") != "array"
            or not isinstance(values, list)
            or len(values) != 2
            or not all(
                any(_expression_contains(value, marker) for value in values)
                for marker in markers
            )
        ):
            errors.append(f"{name} output differs")
    fixed = {
        "contractSchemaVersion": {"type": "string", "value": "nac.azure-bff-performance-coordination/v1"},
        "requiredLeaseBlobType": {"type": "string", "value": "BlockBlob"},
        "requiredLeaseBlobContentLength": {"type": "int", "value": 0},
        "blobBootstrapRequired": {"type": "bool", "value": True},
        "blobBootstrapExecutedByTemplate": {"type": "bool", "value": False},
        "azureRbacOperationRestrictionEnforced": {"type": "bool", "value": False},
        "principalSeparationMode": {
            "type": "string",
            "value": "DISTINCT_BOOTSTRAP_AND_RUNTIME_PRINCIPALS",
        },
    }
    for name, expected in fixed.items():
        if outputs.get(name) != expected:
            errors.append(f"{name} output differs")


def _only(
    grouped: Mapping[str, list[Mapping[str, Any]]], resource_type: str
) -> Mapping[str, Any] | None:
    values = grouped.get(resource_type, [])
    return values[0] if len(values) == 1 else None


def _expression_contains(value: Any, marker: str) -> bool:
    return isinstance(value, str) and marker.casefold() in value.casefold()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate emitted ARM for NaC BFF performance coordination."
    )
    parser.add_argument("template", type=Path)
    parser.add_argument("parameters", type=Path)
    args = parser.parse_args()
    try:
        value = json.loads(args.template.read_text(encoding="utf-8"))
        parameter_artifact = json.loads(args.parameters.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"invalid emitted ARM template: {exc}")
        return 1
    if not isinstance(value, Mapping):
        print("invalid emitted ARM template: root must be an object")
        return 1
    if not isinstance(parameter_artifact, Mapping):
        print("invalid emitted parameter artifact: root must be an object")
        return 1
    errors = [
        *validate_template(value),
        *validate_parameters_artifact(parameter_artifact, value),
    ]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("NaC BFF performance coordination emitted ARM validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
