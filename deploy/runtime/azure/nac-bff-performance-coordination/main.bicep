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

@description('Object ID of the dedicated Entra service principal used only to bootstrap the bound blob with read and add. It must differ from runtimePrincipalId and receives no blob write or delete capability.')
param bootstrapPrincipalId string

@description('Object ID of the dedicated Entra service principal used only at runtime with blob read and write. It must differ from bootstrapPrincipalId and receives no blob add or delete capability.')
param runtimePrincipalId string

@description('SHA-256 of the bootstrap application certificate bound by the owner approval.')
@minLength(64)
@maxLength(64)
param bootstrapCertificateSha256 string

@description('SHA-256 of the separate runtime application certificate bound by the owner approval.')
@minLength(64)
@maxLength(64)
param runtimeCertificateSha256 string

@description('Single public IPv4 address allowed to reach the dedicated data plane during the approved run.')
param allowedClientIpAddress string

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
var bootstrapLeaseDataRoleDefinitionGuid = guid(
  subscription().id,
  resourceGroup().id,
  validatedStorageAccountName,
  containerName,
  'nac-bff-performance-lease-bootstrap-read-add-v1'
)
var runtimeLeaseDataRoleDefinitionGuid = guid(
  subscription().id,
  resourceGroup().id,
  validatedStorageAccountName,
  containerName,
  'nac-bff-performance-lease-runtime-read-write-v1'
)
var blobReadDataAction = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
var blobAddDataAction = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'
var blobWriteDataAction = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'
// Azure blob add authorizes bootstrap creation; blob write authorizes runtime overwrite and
// lease acquire/release/break. Distinct principals ensure no identity combines add and write.
// The dedicated account and identity-specific exact-path ABAC conditions limit scope; sealed
// APIs omit overwrite and break as defense-in-depth, not Azure-enforced filtering.
var exactBootstrapLeaseBlobCondition = '((!(ActionMatches{\'${blobReadDataAction}\'}) AND !(ActionMatches{\'${blobAddDataAction}\'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals \'${containerName}\' AND @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringEquals \'${leaseBlobPath}\'))'
var exactRuntimeLeaseBlobCondition = '((!(ActionMatches{\'${blobReadDataAction}\'}) AND !(ActionMatches{\'${blobWriteDataAction}\'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals \'${containerName}\' AND @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringEquals \'${leaseBlobPath}\'))'
var validatedBootstrapPrincipalId = toLower(bootstrapPrincipalId) != toLower(runtimePrincipalId) && bootstrapCertificateSha256 != runtimeCertificateSha256
  ? bootstrapPrincipalId
  : fail('Bootstrap and runtime principal and certificate identities must be different.')
var validatedRuntimePrincipalId = toLower(bootstrapPrincipalId) != toLower(runtimePrincipalId) && bootstrapCertificateSha256 != runtimeCertificateSha256
  ? runtimePrincipalId
  : fail('Bootstrap and runtime principal and certificate identities must be different.')
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
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
      ipRules: [
        {
          action: 'Allow'
          value: allowedClientIpAddress
        }
      ]
      resourceAccessRules: []
      virtualNetworkRules: []
    }
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
      nac_schema_version: 'nac.azure-bff-performance-coordination/v1'
      data_classification: 'synthetic-only'
      lease_blob_path: leaseBlobPath
      lease_blob_type: 'BlockBlob'
      lease_blob_content_length: '0'
      lease_blob_bootstrap: 'owner-gated-put-if-absent-before-runtime'
      bootstrap_authorization: 'blob-read-plus-add-only-no-write-no-delete'
      runtime_authorization: 'blob-read-plus-write-only-no-add-no-delete'
      azure_blob_write_authorization: 'runtime-write-includes-create-overwrite-lease-and-break'
      operation_restriction_boundary: 'sealed-app-api-defense-in-depth-not-azure-enforced'
      principal_separation: 'distinct-owner-bound-bootstrap-and-runtime-principals'
    }
  }
}

resource bootstrapLeaseDataRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: bootstrapLeaseDataRoleDefinitionGuid
  properties: {
    roleName: 'NaC BFF Performance Lease Bootstrap Read Add ${isolationSuffix}'
    description: 'Bootstrap-only read/add on one ABAC-conditioned blob path. Write, delete, ownership, and container management are excluded.'
    type: 'CustomRole'
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: [
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'
        ]
        notDataActions: []
      }
    ]
    assignableScopes: [
      resourceGroup().id
    ]
  }
}

resource runtimeLeaseDataRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: runtimeLeaseDataRoleDefinitionGuid
  properties: {
    roleName: 'NaC BFF Performance Lease Runtime Read Write ${isolationSuffix}'
    description: 'Runtime-only read/write on one ABAC-conditioned blob path. Add, delete, ownership, and container management are excluded; write includes overwrite and lease operations.'
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

resource bootstrapLeaseBinding 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(leaseContainer.id, validatedBootstrapPrincipalId, bootstrapLeaseDataRole.id, leaseBlobPath)
  scope: leaseContainer
  properties: {
    condition: exactBootstrapLeaseBlobCondition
    conditionVersion: '2.0'
    description: 'Bootstrap-only read/add authorization scoped to the exact NaC BFF performance lease blob path; blob write and delete are excluded.'
    principalId: validatedBootstrapPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: bootstrapLeaseDataRole.id
  }
}

resource runtimeLeaseBinding 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(leaseContainer.id, validatedRuntimePrincipalId, runtimeLeaseDataRole.id, leaseBlobPath)
  scope: leaseContainer
  properties: {
    condition: exactRuntimeLeaseBlobCondition
    conditionVersion: '2.0'
    description: 'Runtime-only read/write authorization scoped to the exact NaC BFF performance lease blob path; blob add and delete are excluded.'
    principalId: validatedRuntimePrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: runtimeLeaseDataRole.id
  }
}

output contractSchemaVersion string = 'nac.azure-bff-performance-coordination/v1'
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
output bootstrapLeaseDataRoleDefinitionId string = bootstrapLeaseDataRole.id
output runtimeLeaseDataRoleDefinitionId string = runtimeLeaseDataRole.id
output bootstrapLeaseRoleAssignmentId string = bootstrapLeaseBinding.id
output runtimeLeaseRoleAssignmentId string = runtimeLeaseBinding.id
output bootstrapCertificateSha256Binding string = bootstrapCertificateSha256
output runtimeCertificateSha256Binding string = runtimeCertificateSha256
output exactBootstrapLeaseBlobCondition string = exactBootstrapLeaseBlobCondition
output exactRuntimeLeaseBlobCondition string = exactRuntimeLeaseBlobCondition
output bootstrapAllowedDataActions array = [
  blobReadDataAction
  blobAddDataAction
]
output runtimeAllowedDataActions array = [
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
  'sealed-bootstrap-and-runtime-application-apis'
]
output principalSeparationMode string = 'DISTINCT_BOOTSTRAP_AND_RUNTIME_PRINCIPALS'
