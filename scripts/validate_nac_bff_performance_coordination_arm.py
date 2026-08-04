#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping


BROKER_DATA_ACTIONS = {
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
}
EXPECTED_RESOURCE_TYPES = {
    "Microsoft.Storage/storageAccounts": 1,
    "Microsoft.Storage/storageAccounts/blobServices": 1,
    "Microsoft.Storage/storageAccounts/blobServices/containers": 1,
    "Microsoft.Authorization/roleDefinitions": 1,
    "Microsoft.Authorization/roleAssignments": 1,
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
    "brokerPrincipalId": {
        "type": "string",
        "metadata": {
            "description": (
                "Object ID of the non-exportable BFF Function managed identity "
                "used only by the fixed lease-broker route."
            )
        },
    },
    "brokerCallerServicePrincipalId": {
        "type": "string",
        "metadata": {
            "description": (
                "Object ID of the owner-gated application service principal allowed "
                "to call the fixed broker route. It receives no Storage DataAction."
            )
        },
    },
    "brokerFunctionAppResourceId": {
        "type": "string",
        "metadata": {
            "description": (
                "Authoritative ARM resource ID of the BFF Function App hosting the "
                "fixed lease broker."
            )
        },
    },
    "brokerFunctionPackageSha256": {
        "type": "string",
        "minLength": 64,
        "maxLength": 64,
        "metadata": {
            "description": (
                "SHA-256 of the exact deployed BFF Function package containing the "
                "broker implementation."
            )
        },
    },
    "brokerTicketVerificationCertificateSha256": {
        "type": "string",
        "minLength": 64,
        "maxLength": 64,
        "metadata": {
            "description": (
                "SHA-256 of the public certificate used by the broker to verify "
                "short-lived activation tickets."
            )
        },
    },
    "brokerOutboundIpAddresses": {
        "type": "array",
        "minLength": 1,
        "maxLength": 32,
        "metadata": {
            "description": (
                "Exact public IPv4 addresses reported by the bound BFF Function App "
                "for broker egress. Local runner addresses are forbidden."
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
    "brokerPrincipalId": "11111111-2222-4333-8444-555555555555",
    "brokerCallerServicePrincipalId": "66666666-7777-4888-8999-aaaaaaaaaaaa",
    "brokerFunctionAppResourceId": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Web/"
        "sites/fn-nac-bff-test"
    ),
    "brokerFunctionPackageSha256": "1" * 64,
    "brokerTicketVerificationCertificateSha256": "2" * 64,
    "brokerOutboundIpAddresses": ["203.0.113.10"],
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
EXPECTED_BROKER_ROLE_GUID = (
    "[guid(subscription().id, resourceGroup().id, "
    "variables('validatedStorageAccountName'), variables('containerName'), "
    "'nac-bff-performance-lease-broker-read-write-v1')]"
)
EXPECTED_BROKER_CONDITION = (
    "[format('((!(ActionMatches{{''{0}''}}) AND !(ActionMatches{{''{1}''}})) "
    "OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] "
    "StringEquals ''{2}'' AND "
    "@Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] "
    "StringEquals ''{3}''))', variables('blobReadDataAction'), "
    "variables('blobWriteDataAction'), variables('containerName'), "
    "variables('leaseBlobPath'))]"
)
EXPECTED_VALIDATED_BROKER_FUNCTION_APP_ID = (
    "[if(and(and(and(and(and(and(and(and(and(equals(length(variables("
    "'brokerFunctionAppResourceIdSegments')), 9), empty(variables("
    "'brokerFunctionAppResourceIdSegments')[0])), equals(toLower(variables("
    "'brokerFunctionAppResourceIdSegments')[1]), 'subscriptions')), equals(variables("
    "'brokerFunctionAppResourceIdSegments')[2], parameters('subscriptionId'))), "
    "equals(toLower(variables('brokerFunctionAppResourceIdSegments')[3]), "
    "'resourcegroups')), not(empty(variables('brokerFunctionAppResourceIdSegments')"
    "[4]))), equals(toLower(variables('brokerFunctionAppResourceIdSegments')[5]), "
    "'providers')), equals(toLower(variables('brokerFunctionAppResourceIdSegments')"
    "[6]), 'microsoft.web')), equals(toLower(variables("
    "'brokerFunctionAppResourceIdSegments')[7]), 'sites')), not(empty(variables("
    "'brokerFunctionAppResourceIdSegments')[8]))), parameters("
    "'brokerFunctionAppResourceId'), fail('Broker Function App resource ID is not "
    "authoritative in the owner-bound subscription.'))]"
)
EXPECTED_VALIDATED_BROKER_PRINCIPAL_ID = (
    "[if(and(and(and(not(empty(variables('validatedBrokerFunctionAppResourceId'))), "
    "not(empty(parameters('brokerPrincipalId')))), not(empty(parameters("
    "'brokerCallerServicePrincipalId')))), not(equals(toLower(parameters("
    "'brokerPrincipalId')), toLower(parameters('brokerCallerServicePrincipalId'))))), "
    "parameters('brokerPrincipalId'), fail('Distinct broker managed identity and "
    "owner-gated caller service principal are required.'))]"
)
EXPECTED_VARIABLE_KEYS = {
    "copy",
    "containerName",
    "leaseBlobPath",
    "bffStorageAccountResourceIdSegments",
    "wormStorageAccountResourceIdSegments",
    "brokerFunctionAppResourceIdSegments",
    "bffStorageAccountName",
    "wormStorageAccountName",
    "validatedDeploymentScope",
    "validatedBffStorageAccountResourceId",
    "validatedWormStorageAccountResourceId",
    "coordinationStorageAccountResourceId",
    "validatedStorageAccountName",
    "isolationSuffix",
    "brokerLeaseDataRoleDefinitionGuid",
    "blobReadDataAction",
    "blobWriteDataAction",
    "exactBrokerLeaseBlobCondition",
    "validatedBrokerFunctionAppResourceId",
    "validatedBrokerPrincipalId",
    "mandatoryResourceTags",
    "resourceTags",
}


def validate_template(template: Mapping[str, Any]) -> list[str]:
    """Return fail-closed errors for an emitted coordination ARM template."""

    errors: list[str] = []
    if set(template) != {
        "$schema",
        "contentVersion",
        "metadata",
        "parameters",
        "variables",
        "resources",
        "outputs",
    }:
        errors.append("ARM template top-level shape differs")
    metadata = template.get("metadata")
    generator = metadata.get("_generator") if isinstance(metadata, Mapping) else None
    if (
        template.get("$schema")
        != "https://schema.management.azure.com/schemas/2019-04-01/"
        "deploymentTemplate.json#"
        or template.get("contentVersion") != "1.0.0.0"
        or not isinstance(generator, Mapping)
        or generator.get("name") != "bicep"
        or generator.get("version") != EXPECTED_BICEP_VERSION
        or not isinstance(generator.get("templateHash"), str)
        or set(metadata) != {"_generator", "description"}
        or metadata.get("description")
        != "Dedicated Azure Blob coordination boundary for one NaC BFF performance run."
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
    legacy_parameters = {
        "bootstrapPrincipalId",
        "runtimePrincipalId",
        "bootstrapCertificateSha256",
        "runtimeCertificateSha256",
        "allowedClientIpAddress",
    }
    if legacy_parameters & set(parameters):
        errors.append("superseded direct-storage parameters remain in the contract")
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
        errors.append("resource type/count set differs from the five-resource contract")

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
    if set(variables) != EXPECTED_VARIABLE_KEYS:
        errors.append("variable key set differs from the broker coordination contract")
    if variables.get("copy") != [
        {
            "name": "brokerIpRules",
            "count": "[length(parameters('brokerOutboundIpAddresses'))]",
            "input": {
                "action": "Allow",
                "value": (
                    "[parameters('brokerOutboundIpAddresses')"
                    "[copyIndex('brokerIpRules')]]"
                ),
            },
        }
    ]:
        errors.append("broker outbound IP firewall rule expansion differs")
    exact_literals = {
        "containerName": "nac-bff-performance-leases",
        "leaseBlobPath": (
            "[format('locks/{0}.lock', parameters('targetBindingSha256'))]"
        ),
        "bffStorageAccountResourceIdSegments": (
            "[split(parameters('bffStorageAccountResourceId'), '/')]"
        ),
        "wormStorageAccountResourceIdSegments": (
            "[split(parameters('wormStorageAccountResourceId'), '/')]"
        ),
        "brokerFunctionAppResourceIdSegments": (
            "[split(parameters('brokerFunctionAppResourceId'), '/')]"
        ),
        "bffStorageAccountName": (
            "[last(variables('bffStorageAccountResourceIdSegments'))]"
        ),
        "wormStorageAccountName": (
            "[last(variables('wormStorageAccountResourceIdSegments'))]"
        ),
        "coordinationStorageAccountResourceId": (
            "[resourceId('Microsoft.Storage/storageAccounts', "
            "parameters('storageAccountName'))]"
        ),
        "isolationSuffix": (
            "[uniqueString(subscription().tenantId, resourceGroup().id, "
            "variables('validatedStorageAccountName'))]"
        ),
        "brokerLeaseDataRoleDefinitionGuid": EXPECTED_BROKER_ROLE_GUID,
        "blobReadDataAction": (
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read"
        ),
        "blobWriteDataAction": (
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write"
        ),
        "exactBrokerLeaseBlobCondition": EXPECTED_BROKER_CONDITION,
        "validatedBrokerFunctionAppResourceId": (
            EXPECTED_VALIDATED_BROKER_FUNCTION_APP_ID
        ),
        "validatedBrokerPrincipalId": EXPECTED_VALIDATED_BROKER_PRINCIPAL_ID,
        "resourceTags": (
            "[union(parameters('tags'), variables('mandatoryResourceTags'))]"
        ),
    }
    for name, expected in exact_literals.items():
        if variables.get(name) != expected:
            errors.append(f"{name} differs")
    if (
        variables.get("validatedDeploymentScope")
        != EXPECTED_VALIDATED_DEPLOYMENT_SCOPE
    ):
        errors.append("validated deployment scope guard differs")
    for prefix, label in (("bff", "BFF"), ("worm", "WORM")):
        name = f"validated{prefix.title()}StorageAccountResourceId"
        if variables.get(name) != _expected_validated_storage_resource_id(
            prefix, label
        ):
            errors.append(f"{prefix} authoritative storage resource ID guard differs")
    if (
        variables.get("validatedStorageAccountName")
        != EXPECTED_VALIDATED_STORAGE_ACCOUNT_NAME
    ):
        errors.append("validated storage account isolation guard differs")
    if variables.get("mandatoryResourceTags") != EXPECTED_MANDATORY_TAGS:
        errors.append("mandatory effective tags differ from runtime canonical tags")


def _expected_validated_storage_resource_id(prefix: str, label: str) -> str:
    segments = f"{prefix}StorageAccountResourceIdSegments"
    account_name = f"{prefix}StorageAccountName"
    parameter = f"{prefix}StorageAccountResourceId"
    return (
        f"[if(and(and(and(and(and(and(and(and(and(and(equals(length(variables('"
        f"{segments}')), 9), empty(variables('{segments}')[0])), "
        f"equals(toLower(variables('{segments}')[1]), 'subscriptions')), "
        f"equals(variables('{segments}')[2], parameters('subscriptionId'))), "
        f"equals(toLower(variables('{segments}')[3]), 'resourcegroups')), "
        f"not(empty(variables('{segments}')[4]))), "
        f"equals(toLower(variables('{segments}')[5]), 'providers')), "
        f"equals(toLower(variables('{segments}')[6]), 'microsoft.storage')), "
        f"equals(toLower(variables('{segments}')[7]), 'storageaccounts')), "
        f"not(empty(variables('{account_name}')))), "
        f"equals(toLower(resourceId(parameters('subscriptionId'), variables('"
        f"{segments}')[4], 'Microsoft.Storage/storageAccounts', variables('"
        f"{account_name}'))), toLower(parameters('{parameter}')))), "
        f"parameters('{parameter}'), fail('{label} storage account resource ID is "
        "not an authoritative storage account ID in the owner-bound subscription.'))]"
    )


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
    if set(resource) != {
        "type",
        "apiVersion",
        "name",
        "location",
        "tags",
        "kind",
        "sku",
        "properties",
    }:
        errors.append("storage resource shape differs")
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
            "ipRules": "[variables('brokerIpRules')]",
            "resourceAccessRules": [],
            "virtualNetworkRules": [],
        },
    }
    properties = resource.get("properties")
    network_acls = (
        properties.get("networkAcls") if isinstance(properties, Mapping) else None
    )
    if not isinstance(network_acls, Mapping):
        errors.append("networkAcls must be an object")
    if resource.get("properties") != expected_properties:
        errors.append("storage properties or broker outbound IP ACLs are not exact")


def _validate_blob_service(
    resource: Mapping[str, Any] | None, errors: list[str]
) -> None:
    if resource is None:
        return
    if set(resource) != {
        "type",
        "apiVersion",
        "name",
        "properties",
        "dependsOn",
    }:
        errors.append("blob service resource shape differs")
    if resource.get("name") != EXPECTED_BLOB_SERVICE_RESOURCE_NAME:
        errors.append("blob service resource name differs")
    if resource.get("properties") != {
        "isVersioningEnabled": False,
        "deleteRetentionPolicy": {"enabled": False},
        "containerDeleteRetentionPolicy": {"enabled": False},
    }:
        errors.append("blob service properties are not exact")


def _validate_container(
    resource: Mapping[str, Any] | None, errors: list[str]
) -> None:
    if resource is None:
        return
    if set(resource) != {
        "type",
        "apiVersion",
        "name",
        "properties",
        "dependsOn",
    }:
        errors.append("lease container resource shape differs")
    if resource.get("name") != EXPECTED_CONTAINER_RESOURCE_NAME:
        errors.append("lease container resource name differs")
    expected_properties = {
        "publicAccess": "None",
        "metadata": {
            "nac_schema_version": "nac.azure-bff-performance-coordination/v1",
            "data_classification": "synthetic-only",
            "lease_blob_path": "[variables('leaseBlobPath')]",
            "lease_blob_type": "BlockBlob",
            "lease_blob_content_length": "0",
            "lease_blob_bootstrap": (
                "broker-internal-put-if-absent-before-acquire"
            ),
            "broker_authorization": (
                "non-exportable-managed-identity-read-write-no-delete"
            ),
            "azure_blob_write_authorization": (
                "broker-uami-write-includes-create-overwrite-lease-and-break"
            ),
            "operation_restriction_boundary": (
                "owner-ticketed-fixed-function-route"
            ),
            "local_runner_storage_authorization": "none",
            "brokerFunctionPackageSha256": (
                "[parameters('brokerFunctionPackageSha256')]"
            ),
            "brokerTicketVerificationCertificateSha256": (
                "[parameters('brokerTicketVerificationCertificateSha256')]"
            ),
        },
    }
    if resource.get("properties") != expected_properties:
        errors.append("lease container properties or broker metadata are not exact")


def _validate_role_definitions(
    resources: list[Mapping[str, Any]], errors: list[str]
) -> None:
    if len(resources) != 1:
        errors.append("broker custom role count differs")
        return
    resource = resources[0]
    expected_properties = {
        "roleName": (
            "[format('NaC BFF Performance Lease Broker Read Write {0}', "
            "variables('isolationSuffix'))]"
        ),
        "description": (
            "Broker-only read/write on one ABAC-conditioned blob path. The "
            "managed-identity credential is never exported to the local runner."
        ),
        "type": "CustomRole",
        "permissions": [
            {
                "actions": [],
                "notActions": [],
                "dataActions": [
                    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
                    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
                ],
                "notDataActions": [],
            }
        ],
        "assignableScopes": EXPECTED_ROLE_ASSIGNABLE_SCOPES,
    }
    if (
        set(resource) != {"type", "apiVersion", "name", "properties"}
        or resource.get("type") != "Microsoft.Authorization/roleDefinitions"
        or resource.get("apiVersion") != "2022-04-01"
        or resource.get("name")
        != "[variables('brokerLeaseDataRoleDefinitionGuid')]"
        or resource.get("properties") != expected_properties
    ):
        errors.append("broker exact-path custom role differs")
        return
    actions = expected_properties["permissions"][0]["dataActions"]
    if set(actions) != BROKER_DATA_ACTIONS or any(
        action.endswith("/delete") for action in actions
    ):
        errors.append("broker custom role DataActions differ")


def _validate_role_assignments(
    resources: list[Mapping[str, Any]], errors: list[str]
) -> None:
    if len(resources) != 1:
        errors.append("broker role assignment count differs")
        return
    expected = {
        "type": "Microsoft.Authorization/roleAssignments",
        "apiVersion": "2022-04-01",
        "scope": EXPECTED_ROLE_ASSIGNMENT_SCOPE,
        "name": (
            "[guid(resourceId('Microsoft.Storage/storageAccounts/blobServices/"
            "containers', variables('validatedStorageAccountName'), 'default', "
            "variables('containerName')), variables('validatedBrokerPrincipalId'), "
            "resourceId('Microsoft.Authorization/roleDefinitions', variables("
            "'brokerLeaseDataRoleDefinitionGuid')), variables('leaseBlobPath'))]"
        ),
        "properties": {
            "condition": "[variables('exactBrokerLeaseBlobCondition')]",
            "conditionVersion": "2.0",
            "description": (
                "Non-exportable BFF lease-broker managed identity scoped to the "
                "exact performance lease blob path."
            ),
            "principalId": "[variables('validatedBrokerPrincipalId')]",
            "principalType": "ServicePrincipal",
            "roleDefinitionId": (
                "[resourceId('Microsoft.Authorization/roleDefinitions', variables("
                "'brokerLeaseDataRoleDefinitionGuid'))]"
            ),
        },
        "dependsOn": [
            "[resourceId('Microsoft.Authorization/roleDefinitions', variables("
            "'brokerLeaseDataRoleDefinitionGuid'))]",
            "[resourceId('Microsoft.Storage/storageAccounts/blobServices/containers', "
            "variables('validatedStorageAccountName'), 'default', "
            "variables('containerName'))]",
        ],
    }
    if resources[0] != expected:
        errors.append("broker UAMI exact-path role assignment differs")


def _validate_outputs(outputs: Mapping[str, Any], errors: list[str]) -> None:
    expected = {
        "contractSchemaVersion": {
            "type": "string",
            "value": "nac.azure-bff-performance-coordination/v1",
        },
        "storageAccountName": {
            "type": "string",
            "value": "[variables('validatedStorageAccountName')]",
        },
        "storageAccountResourceId": {
            "type": "string",
            "value": (
                "[resourceId('Microsoft.Storage/storageAccounts', "
                "variables('validatedStorageAccountName'))]"
            ),
        },
        "effectiveTags": {
            "type": "object",
            "value": "[variables('resourceTags')]",
        },
        "bffStorageAccountResourceIdBinding": {
            "type": "string",
            "value": "[variables('validatedBffStorageAccountResourceId')]",
        },
        "bffStorageAccountNameBinding": {
            "type": "string",
            "value": "[variables('bffStorageAccountName')]",
        },
        "wormStorageAccountResourceIdBinding": {
            "type": "string",
            "value": "[variables('validatedWormStorageAccountResourceId')]",
        },
        "wormStorageAccountNameBinding": {
            "type": "string",
            "value": "[variables('wormStorageAccountName')]",
        },
        "leaseContainerName": {
            "type": "string",
            "value": "[variables('containerName')]",
        },
        "leaseContainerResourceId": {
            "type": "string",
            "value": EXPECTED_ROLE_ASSIGNMENT_SCOPE,
        },
        "leaseBlobPath": {
            "type": "string",
            "value": "[variables('leaseBlobPath')]",
        },
        "leaseBlobUri": {
            "type": "string",
            "value": (
                "[format('{0}{1}/{2}', reference(resourceId("
                "'Microsoft.Storage/storageAccounts', variables("
                "'validatedStorageAccountName')), '2023-05-01').primaryEndpoints.blob, "
                "variables('containerName'), variables('leaseBlobPath'))]"
            ),
        },
        "requiredLeaseBlobType": {"type": "string", "value": "BlockBlob"},
        "requiredLeaseBlobContentLength": {"type": "int", "value": 0},
        "targetBindingSha256": {
            "type": "string",
            "value": "[parameters('targetBindingSha256')]",
        },
        "brokerLeaseDataRoleDefinitionId": {
            "type": "string",
            "value": (
                "[resourceId('Microsoft.Authorization/roleDefinitions', variables("
                "'brokerLeaseDataRoleDefinitionGuid'))]"
            ),
        },
        "brokerLeaseRoleAssignmentId": {
            "type": "string",
            "value": (
                "[extensionResourceId(resourceId('Microsoft.Storage/storageAccounts/"
                "blobServices/containers', variables('validatedStorageAccountName'), "
                "'default', variables('containerName')), "
                "'Microsoft.Authorization/roleAssignments', guid(resourceId("
                "'Microsoft.Storage/storageAccounts/blobServices/containers', "
                "variables('validatedStorageAccountName'), 'default', variables("
                "'containerName')), variables('validatedBrokerPrincipalId'), "
                "resourceId('Microsoft.Authorization/roleDefinitions', variables("
                "'brokerLeaseDataRoleDefinitionGuid')), variables('leaseBlobPath')))]"
            ),
        },
        "brokerPrincipalIdBinding": {
            "type": "string",
            "value": "[variables('validatedBrokerPrincipalId')]",
        },
        "brokerCallerServicePrincipalIdBinding": {
            "type": "string",
            "value": "[parameters('brokerCallerServicePrincipalId')]",
        },
        "brokerFunctionAppResourceIdBinding": {
            "type": "string",
            "value": "[variables('validatedBrokerFunctionAppResourceId')]",
        },
        "brokerFunctionPackageSha256Binding": {
            "type": "string",
            "value": "[parameters('brokerFunctionPackageSha256')]",
        },
        "brokerTicketVerificationCertificateSha256Binding": {
            "type": "string",
            "value": (
                "[parameters('brokerTicketVerificationCertificateSha256')]"
            ),
        },
        "exactBrokerLeaseBlobCondition": {
            "type": "string",
            "value": "[variables('exactBrokerLeaseBlobCondition')]",
        },
        "brokerAllowedDataActions": {
            "type": "array",
            "value": [
                "[variables('blobReadDataAction')]",
                "[variables('blobWriteDataAction')]",
            ],
        },
        "deploymentScopeBinding": {
            "type": "string",
            "value": "[variables('validatedDeploymentScope')]",
        },
        "blobBootstrapRequired": {"type": "bool", "value": True},
        "blobBootstrapExecutedByTemplate": {"type": "bool", "value": False},
        "azureRbacWriteAuthorizedOperations": {
            "type": "array",
            "value": [
                "blob-create",
                "blob-overwrite",
                "lease-acquire",
                "lease-release",
                "lease-break",
            ],
        },
        "azureRbacOperationRestrictionEnforced": {
            "type": "bool",
            "value": False,
        },
        "operationRestrictionDefenseInDepth": {
            "type": "array",
            "value": [
                "dedicated-storage-account",
                "exact-container-and-blob-path-abac",
                "non-exportable-function-managed-identity",
                "owner-ticketed-fixed-broker-api",
            ],
        },
        "localRunnerStorageDataActions": {"type": "array", "value": []},
        "credentialBoundaryMode": {
            "type": "string",
            "value": "BFF_BROKER_UAMI_ONLY",
        },
    }
    if outputs != expected:
        errors.append("output contract differs from the exact broker boundary")


def _only(
    grouped: Mapping[str, list[Mapping[str, Any]]], resource_type: str
) -> Mapping[str, Any] | None:
    values = grouped.get(resource_type, [])
    return values[0] if len(values) == 1 else None


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
