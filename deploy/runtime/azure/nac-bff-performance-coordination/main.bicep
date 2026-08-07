// SPDX-License-Identifier: AGPL-3.0-or-later
// Offline infrastructure contract only. Deployment and lease operations remain owner-gated.

targetScope = 'resourceGroup'

metadata description = 'Dedicated Azure Blob coordination boundary for one NaC BFF performance run.'

@description('Azure region for the dedicated coordination storage account.')
@allowed([
  'germanywestcentral'
])
param location string = 'germanywestcentral'

@description('Exact Entra tenant bound by the combined owner approval.')
param tenantId string

@description('Exact Azure subscription bound by the combined owner approval.')
param subscriptionId string

@description('Exact Azure resource group bound by the combined owner approval.')
param resourceGroupName string

@description('Deployment mode binding. The CLI and template accept Incremental only.')
@allowed([
  'Incremental'
])
param deploymentMode string = 'Incremental'

@description('Globally unique name for the dedicated performance-coordination storage account.')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('Authoritative ARM resource ID of the existing BFF host/deployment storage account. The account name is derived from this ID.')
param bffStorageAccountResourceId string

@description('Authoritative ARM resource ID of the existing WORM evidence storage account. The account name is derived from this ID.')
param wormStorageAccountResourceId string

@description('Object ID of the owner-gated application service principal allowed to call the fixed broker route. It receives no Storage DataAction.')
param brokerCallerServicePrincipalId string

@description('Authoritative ARM resource ID of the BFF Function App hosting the fixed lease broker.')
param brokerFunctionAppResourceId string

@description('Authoritative ARM resource ID of the dedicated Flex Consumption integration subnet.')
param brokerFunctionIntegrationSubnetResourceId string

@description('Authoritative ARM resource ID of the separate subnet reserved for private endpoints.')
param brokerPrivateEndpointSubnetResourceId string

@description('Authoritative ARM resource ID of the VNet containing both broker subnets.')
param brokerVirtualNetworkResourceId string

@description('SHA-256 of the exact deployed BFF Function package containing the broker implementation.')
@minLength(64)
@maxLength(64)
param brokerFunctionPackageSha256 string

@description('SHA-256 of the public certificate used by the broker to verify short-lived activation tickets.')
@minLength(64)
@maxLength(64)
param brokerTicketVerificationCertificateSha256 string

@description('Hash binding used as the only lease blob basename.')
@minLength(64)
@maxLength(64)
param targetBindingSha256 string

@description('Additional non-sensitive tags. Coordination boundary tags cannot be overridden.')
param tags object = {}

var containerName = 'nac-bff-performance-leases'
var leaseBlobPath = 'locks/${targetBindingSha256}.lock'
var bffStorageAccountResourceIdSegments = split(bffStorageAccountResourceId, '/')
var wormStorageAccountResourceIdSegments = split(wormStorageAccountResourceId, '/')
var brokerFunctionAppResourceIdSegments = split(brokerFunctionAppResourceId, '/')
var brokerFunctionIntegrationSubnetResourceIdSegments = split(brokerFunctionIntegrationSubnetResourceId, '/')
var brokerPrivateEndpointSubnetResourceIdSegments = split(brokerPrivateEndpointSubnetResourceId, '/')
var brokerVirtualNetworkResourceIdSegments = split(brokerVirtualNetworkResourceId, '/')
var bffStorageAccountName = last(bffStorageAccountResourceIdSegments)
var wormStorageAccountName = last(wormStorageAccountResourceIdSegments)
var validatedDeploymentScope = tenant().tenantId == tenantId && subscription().subscriptionId == subscriptionId && resourceGroup().name == resourceGroupName && deploymentMode == 'Incremental'
  ? '${tenantId}/${subscriptionId}/${resourceGroupName}'
  : fail('Performance coordination deployment scope does not match the owner-bound tenant, subscription, and resource group.')
var validatedBffStorageAccountResourceId = length(bffStorageAccountResourceIdSegments) == 9 && empty(bffStorageAccountResourceIdSegments[0]) && toLower(bffStorageAccountResourceIdSegments[1]) == 'subscriptions' && bffStorageAccountResourceIdSegments[2] == subscriptionId && toLower(bffStorageAccountResourceIdSegments[3]) == 'resourcegroups' && !empty(bffStorageAccountResourceIdSegments[4]) && toLower(bffStorageAccountResourceIdSegments[5]) == 'providers' && toLower(bffStorageAccountResourceIdSegments[6]) == 'microsoft.storage' && toLower(bffStorageAccountResourceIdSegments[7]) == 'storageaccounts' && !empty(bffStorageAccountName) && toLower(resourceId(
    subscriptionId,
    bffStorageAccountResourceIdSegments[4],
    'Microsoft.Storage/storageAccounts',
    bffStorageAccountName
  )) == toLower(bffStorageAccountResourceId)
  ? bffStorageAccountResourceId
  : fail('BFF storage account resource ID is not an authoritative storage account ID in the owner-bound subscription.')
var validatedWormStorageAccountResourceId = length(wormStorageAccountResourceIdSegments) == 9 && empty(wormStorageAccountResourceIdSegments[0]) && toLower(wormStorageAccountResourceIdSegments[1]) == 'subscriptions' && wormStorageAccountResourceIdSegments[2] == subscriptionId && toLower(wormStorageAccountResourceIdSegments[3]) == 'resourcegroups' && !empty(wormStorageAccountResourceIdSegments[4]) && toLower(wormStorageAccountResourceIdSegments[5]) == 'providers' && toLower(wormStorageAccountResourceIdSegments[6]) == 'microsoft.storage' && toLower(wormStorageAccountResourceIdSegments[7]) == 'storageaccounts' && !empty(wormStorageAccountName) && toLower(resourceId(
    subscriptionId,
    wormStorageAccountResourceIdSegments[4],
    'Microsoft.Storage/storageAccounts',
    wormStorageAccountName
  )) == toLower(wormStorageAccountResourceId)
  ? wormStorageAccountResourceId
  : fail('WORM storage account resource ID is not an authoritative storage account ID in the owner-bound subscription.')
var coordinationStorageAccountResourceId = resourceId('Microsoft.Storage/storageAccounts', storageAccountName)
var validatedStorageAccountName = !empty(validatedDeploymentScope) && toLower(coordinationStorageAccountResourceId) != toLower(validatedBffStorageAccountResourceId) && toLower(coordinationStorageAccountResourceId) != toLower(validatedWormStorageAccountResourceId) && toLower(validatedBffStorageAccountResourceId) != toLower(validatedWormStorageAccountResourceId) && toLower(storageAccountName) != toLower(bffStorageAccountName) && toLower(storageAccountName) != toLower(wormStorageAccountName) && toLower(bffStorageAccountName) != toLower(wormStorageAccountName)
  ? storageAccountName
  : fail('Performance coordination, BFF, and WORM storage accounts must be pairwise distinct.')
var isolationSuffix = uniqueString(subscription().tenantId, resourceGroup().id, validatedStorageAccountName)
var brokerLeaseDataRoleDefinitionGuid = guid(
  subscription().id,
  resourceGroup().id,
  validatedStorageAccountName,
  containerName,
  'nac-bff-performance-lease-broker-read-write-v1'
)
var blobReadDataAction = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
var blobWriteDataAction = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'
// Blob write includes create, overwrite and every lease action. The credential is therefore
// assigned only to the non-exportable Function managed identity. The local measurement runner
// receives no Storage DataAction, token or certificate and can reach only the fixed broker API.
var exactBrokerLeaseBlobCondition = '((!(ActionMatches{\'${blobReadDataAction}\'}) AND !(ActionMatches{\'${blobWriteDataAction}\'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals \'${containerName}\' AND @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringEquals \'${leaseBlobPath}\'))'
var validatedBrokerFunctionAppResourceId = length(brokerFunctionAppResourceIdSegments) == 9 && empty(brokerFunctionAppResourceIdSegments[0]) && toLower(brokerFunctionAppResourceIdSegments[1]) == 'subscriptions' && brokerFunctionAppResourceIdSegments[2] == subscriptionId && toLower(brokerFunctionAppResourceIdSegments[3]) == 'resourcegroups' && brokerFunctionAppResourceIdSegments[4] == resourceGroupName && toLower(brokerFunctionAppResourceIdSegments[5]) == 'providers' && toLower(brokerFunctionAppResourceIdSegments[6]) == 'microsoft.web' && toLower(brokerFunctionAppResourceIdSegments[7]) == 'sites' && !empty(brokerFunctionAppResourceIdSegments[8])
  ? brokerFunctionAppResourceId
  : fail('Broker Function App resource ID is not authoritative in the owner-bound resource group.')
var validatedBrokerVirtualNetworkResourceId = length(brokerVirtualNetworkResourceIdSegments) == 9 && empty(brokerVirtualNetworkResourceIdSegments[0]) && toLower(brokerVirtualNetworkResourceIdSegments[1]) == 'subscriptions' && brokerVirtualNetworkResourceIdSegments[2] == subscriptionId && toLower(brokerVirtualNetworkResourceIdSegments[3]) == 'resourcegroups' && brokerVirtualNetworkResourceIdSegments[4] == resourceGroupName && toLower(brokerVirtualNetworkResourceIdSegments[5]) == 'providers' && toLower(brokerVirtualNetworkResourceIdSegments[6]) == 'microsoft.network' && toLower(brokerVirtualNetworkResourceIdSegments[7]) == 'virtualnetworks' && !empty(brokerVirtualNetworkResourceIdSegments[8])
  ? brokerVirtualNetworkResourceId
  : fail('Broker VNet resource ID is not authoritative in the owner-bound resource group.')
var validatedBrokerFunctionIntegrationSubnetResourceId = length(brokerFunctionIntegrationSubnetResourceIdSegments) == 11 && empty(brokerFunctionIntegrationSubnetResourceIdSegments[0]) && toLower(brokerFunctionIntegrationSubnetResourceIdSegments[1]) == 'subscriptions' && brokerFunctionIntegrationSubnetResourceIdSegments[2] == subscriptionId && toLower(brokerFunctionIntegrationSubnetResourceIdSegments[3]) == 'resourcegroups' && brokerFunctionIntegrationSubnetResourceIdSegments[4] == resourceGroupName && toLower(brokerFunctionIntegrationSubnetResourceIdSegments[5]) == 'providers' && toLower(brokerFunctionIntegrationSubnetResourceIdSegments[6]) == 'microsoft.network' && toLower(brokerFunctionIntegrationSubnetResourceIdSegments[7]) == 'virtualnetworks' && !empty(brokerFunctionIntegrationSubnetResourceIdSegments[8]) && toLower(brokerFunctionIntegrationSubnetResourceIdSegments[9]) == 'subnets' && !empty(brokerFunctionIntegrationSubnetResourceIdSegments[10]) && toLower('${validatedBrokerVirtualNetworkResourceId}/subnets/${brokerFunctionIntegrationSubnetResourceIdSegments[10]}') == toLower(brokerFunctionIntegrationSubnetResourceId)
  ? brokerFunctionIntegrationSubnetResourceId
  : fail('Broker Function integration subnet is not authoritative in the owner-bound VNet.')
var validatedBrokerPrivateEndpointSubnetResourceId = length(brokerPrivateEndpointSubnetResourceIdSegments) == 11 && empty(brokerPrivateEndpointSubnetResourceIdSegments[0]) && toLower(brokerPrivateEndpointSubnetResourceIdSegments[1]) == 'subscriptions' && brokerPrivateEndpointSubnetResourceIdSegments[2] == subscriptionId && toLower(brokerPrivateEndpointSubnetResourceIdSegments[3]) == 'resourcegroups' && brokerPrivateEndpointSubnetResourceIdSegments[4] == resourceGroupName && toLower(brokerPrivateEndpointSubnetResourceIdSegments[5]) == 'providers' && toLower(brokerPrivateEndpointSubnetResourceIdSegments[6]) == 'microsoft.network' && toLower(brokerPrivateEndpointSubnetResourceIdSegments[7]) == 'virtualnetworks' && !empty(brokerPrivateEndpointSubnetResourceIdSegments[8]) && toLower(brokerPrivateEndpointSubnetResourceIdSegments[9]) == 'subnets' && !empty(brokerPrivateEndpointSubnetResourceIdSegments[10]) && toLower('${validatedBrokerVirtualNetworkResourceId}/subnets/${brokerPrivateEndpointSubnetResourceIdSegments[10]}') == toLower(brokerPrivateEndpointSubnetResourceId) && toLower(brokerPrivateEndpointSubnetResourceId) != toLower(validatedBrokerFunctionIntegrationSubnetResourceId)
  ? brokerPrivateEndpointSubnetResourceId
  : fail('Broker private-endpoint subnet must be authoritative and separate from the Function integration subnet.')

resource brokerFunctionApp 'Microsoft.Web/sites@2024-04-01' existing = {
  name: brokerFunctionAppResourceIdSegments[8]
}

var validatedBrokerPrincipalId = !empty(validatedBrokerFunctionAppResourceId) && contains(brokerFunctionApp.identity.type, 'SystemAssigned') && !empty(brokerFunctionApp.identity.principalId) && !empty(brokerCallerServicePrincipalId) && toLower(brokerFunctionApp.identity.principalId) != toLower(brokerCallerServicePrincipalId)
  ? brokerFunctionApp.identity.principalId
  : fail('The bound broker Function requires a system-assigned identity distinct from the owner-gated caller service principal.')
var privateDnsZoneName = 'privatelink.blob.${environment().suffixes.storage}'
var privateEndpointName = 'pep-${validatedStorageAccountName}'
// Keep this mandatory set aligned with effective_coordination_tags() in the
// infrastructure safety verifier. union() prevents caller overrides.
var mandatoryResourceTags = {
  blobPrecreation: 'owner-gated-before-runtime'
  dataClassification: 'synthetic-only'
  environment: 'test'
  managedBy: 'bicep'
  storageBoundary: 'dedicated-from-bff-and-worm'
  targetBindingSha256: targetBindingSha256
  workload: 'nac-bff-performance-coordination'
}
var resourceTags = union(tags, mandatoryResourceTags)

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: validatedStorageAccountName
  location: location
  tags: resourceTags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    isHnsEnabled: false
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
      ipRules: []
      resourceAccessRules: []
      virtualNetworkRules: []
    }
  }
}

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: privateDnsZoneName
  location: 'global'
  tags: resourceTags
}

resource privateDnsVirtualNetworkLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: privateDnsZone
  name: 'link-nac-bff-${isolationSuffix}'
  location: 'global'
  tags: resourceTags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: validatedBrokerVirtualNetworkResourceId
    }
  }
}

resource coordinationBlobPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: privateEndpointName
  location: location
  tags: resourceTags
  properties: {
    subnet: {
      id: validatedBrokerPrivateEndpointSubnetResourceId
    }
    privateLinkServiceConnections: [
      {
        name: 'blob'
        properties: {
          groupIds: [
            'blob'
          ]
          privateLinkServiceId: storageAccount.id
        }
      }
    ]
  }
}

resource coordinationBlobPrivateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: coordinationBlobPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    isVersioningEnabled: false
    deleteRetentionPolicy: {
      enabled: false
    }
    containerDeleteRetentionPolicy: {
      enabled: false
    }
  }
}

resource leaseContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
    metadata: {
      nac_schema_version: 'nac.azure-bff-performance-coordination/v3'
      data_classification: 'synthetic-only'
      lease_blob_path: leaseBlobPath
      lease_blob_type: 'BlockBlob'
      lease_blob_content_length: '0'
      lease_blob_bootstrap: 'broker-internal-put-if-absent-before-acquire'
      broker_authorization: 'non-exportable-managed-identity-read-write-no-delete'
      azure_blob_write_authorization: 'broker-system-identity-write-includes-create-overwrite-lease-and-break'
      operation_restriction_boundary: 'owner-ticketed-fixed-function-route'
      local_runner_storage_authorization: 'none'
      brokerFunctionPackageSha256: brokerFunctionPackageSha256
      brokerTicketVerificationCertificateSha256: brokerTicketVerificationCertificateSha256
    }
  }
}

resource brokerLeaseDataRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: brokerLeaseDataRoleDefinitionGuid
  properties: {
    roleName: 'NaC BFF Performance Lease Broker Read Write ${isolationSuffix}'
    description: 'Broker-only read/write on one ABAC-conditioned blob path. The managed-identity credential is never exported to the local runner.'
    type: 'CustomRole'
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: [
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'
        ]
        notDataActions: []
      }
    ]
    assignableScopes: [
      resourceGroup().id
    ]
  }
}

resource brokerLeaseBinding 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(leaseContainer.id, validatedBrokerFunctionAppResourceId, brokerLeaseDataRole.id, leaseBlobPath)
  scope: leaseContainer
  properties: {
    condition: exactBrokerLeaseBlobCondition
    conditionVersion: '2.0'
    description: 'Non-exportable BFF lease-broker managed identity scoped to the exact performance lease blob path.'
    principalId: validatedBrokerPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: brokerLeaseDataRole.id
  }
}

output contractSchemaVersion string = 'nac.azure-bff-performance-coordination/v3'
output storageAccountName string = storageAccount.name
output storageAccountResourceId string = storageAccount.id
output effectiveTags object = resourceTags
output bffStorageAccountResourceIdBinding string = validatedBffStorageAccountResourceId
output bffStorageAccountNameBinding string = bffStorageAccountName
output wormStorageAccountResourceIdBinding string = validatedWormStorageAccountResourceId
output wormStorageAccountNameBinding string = wormStorageAccountName
output leaseContainerName string = leaseContainer.name
output leaseContainerResourceId string = leaseContainer.id
output leaseBlobPath string = leaseBlobPath
output leaseBlobUri string = '${storageAccount.properties.primaryEndpoints.blob}${leaseContainer.name}/${leaseBlobPath}'
output requiredLeaseBlobType string = 'BlockBlob'
output requiredLeaseBlobContentLength int = 0
output targetBindingSha256 string = targetBindingSha256
output brokerLeaseDataRoleDefinitionId string = brokerLeaseDataRole.id
output brokerLeaseRoleAssignmentId string = brokerLeaseBinding.id
output brokerPrincipalIdBinding string = validatedBrokerPrincipalId
output brokerCallerServicePrincipalIdBinding string = brokerCallerServicePrincipalId
output brokerFunctionAppResourceIdBinding string = validatedBrokerFunctionAppResourceId
output brokerVirtualNetworkResourceIdBinding string = validatedBrokerVirtualNetworkResourceId
output brokerFunctionIntegrationSubnetResourceIdBinding string = validatedBrokerFunctionIntegrationSubnetResourceId
output brokerPrivateEndpointSubnetResourceIdBinding string = validatedBrokerPrivateEndpointSubnetResourceId
output coordinationBlobPrivateEndpointResourceId string = coordinationBlobPrivateEndpoint.id
output coordinationBlobPrivateDnsZoneResourceId string = privateDnsZone.id
output coordinationBlobPrivateDnsVirtualNetworkLinkResourceId string = privateDnsVirtualNetworkLink.id
output brokerFunctionPackageSha256Binding string = brokerFunctionPackageSha256
output brokerTicketVerificationCertificateSha256Binding string = brokerTicketVerificationCertificateSha256
output exactBrokerLeaseBlobCondition string = exactBrokerLeaseBlobCondition
output brokerAllowedDataActions array = [
  blobReadDataAction
  blobWriteDataAction
]
output deploymentScopeBinding string = validatedDeploymentScope
output blobBootstrapRequired bool = true
output blobBootstrapExecutedByTemplate bool = false
output azureRbacWriteAuthorizedOperations array = [
  'blob-create'
  'blob-overwrite'
  'lease-acquire'
  'lease-release'
  'lease-break'
]
output azureRbacOperationRestrictionEnforced bool = false
output operationRestrictionDefenseInDepth array = [
  'dedicated-storage-account'
  'exact-container-and-blob-path-abac'
  'non-exportable-function-managed-identity'
  'owner-ticketed-fixed-broker-api'
]
output localRunnerStorageDataActions array = []
output credentialBoundaryMode string = 'BFF_BROKER_SYSTEM_ASSIGNED_IDENTITY_ONLY'
