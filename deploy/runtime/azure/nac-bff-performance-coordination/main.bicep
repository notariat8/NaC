// SPDX-License-Identifier: AGPL-3.0-or-later
// Offline infrastructure contract only. Deployment and lease operations remain owner-gated.

targetScope = 'resourceGroup'

metadata description = 'Dedicated Azure Blob coordination boundary for one NaC BFF performance run.'

@description('Azure region for the dedicated coordination storage account.')
@allowed([
  'germanywestcentral'
])
param location string = 'germanywestcentral'

@description('Globally unique name for the dedicated performance-coordination storage account.')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('Existing BFF host/deployment storage account name. Equality with the coordination account fails closed.')
@minLength(3)
@maxLength(24)
param bffStorageAccountName string

@description('Existing WORM evidence storage account name. Equality with the coordination account fails closed.')
@minLength(3)
@maxLength(24)
param wormStorageAccountName string

@description('Name of the existing user-assigned provisioner identity receiving the exact lease-blob binding.')
@minLength(3)
@maxLength(128)
param provisionerIdentityName string

@description('Hash binding used as the only lease blob basename.')
@minLength(64)
@maxLength(64)
param targetBindingSha256 string

@description('Strong ETag of the pre-created zero-byte block blob. Blob creation is deliberately outside this no-add role.')
@minLength(4)
@maxLength(128)
param precreatedLeaseBlobETag string

@description('Additional non-sensitive tags. Coordination boundary tags cannot be overridden.')
param tags object = {}

var containerName = 'nac-bff-performance-leases'
var leaseBlobPath = 'locks/${targetBindingSha256}.lock'
var validatedStorageAccountName = storageAccountName != bffStorageAccountName && storageAccountName != wormStorageAccountName
  ? storageAccountName
  : fail('Performance coordination storage must be dedicated from BFF and WORM storage accounts.')
var isolationSuffix = uniqueString(subscription().tenantId, resourceGroup().id, validatedStorageAccountName)
var leaseDataRoleDefinitionGuid = guid(
  subscription().id,
  resourceGroup().id,
  validatedStorageAccountName,
  containerName,
  'nac-bff-performance-lease-read-write-v1'
)
var blobReadDataAction = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
var blobWriteDataAction = 'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'
// Azure authorizes acquire, release, and break through the same write DataAction.
// Exact operation filtering therefore remains fail-closed in the application API.
var exactLeaseBlobCondition = '((!(ActionMatches{\'${blobReadDataAction}\'}) AND !(ActionMatches{\'${blobWriteDataAction}\'})) OR (@Resource[Microsoft.Storage/storageAccounts/blobServices/containers:name] StringEquals \'${containerName}\' AND @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path] StringEquals \'${leaseBlobPath}\'))'
var resourceTags = union(tags, {
  workload: 'nac-bff-performance-coordination'
  environment: 'test'
  managedBy: 'bicep'
  dataClassification: 'synthetic-only'
  storageBoundary: 'dedicated-from-bff-and-worm'
  blobPrecreation: 'owner-gated-before-runtime'
})

resource provisionerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: provisionerIdentityName
}

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
      defaultAction: 'Allow'
      ipRules: []
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
      lease_blob_precreation: 'required-before-runtime'
      lease_break_boundary: 'shares-write-data-action-blocked-in-app-api'
    }
  }
}

resource leaseDataRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: leaseDataRoleDefinitionGuid
  properties: {
    roleName: 'NaC BFF Performance Lease Read Write ${isolationSuffix}'
    description: 'Read and lease one pre-created coordination blob; no add, delete, ownership, or container management.'
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

resource provisionerLeaseBinding 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(leaseContainer.id, provisionerIdentity.id, leaseDataRole.id, leaseBlobPath)
  scope: leaseContainer
  properties: {
    condition: exactLeaseBlobCondition
    conditionVersion: '2.0'
    description: 'Exact pre-created NaC BFF performance lease blob only.'
    principalId: provisionerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: leaseDataRole.id
  }
}

output contractSchemaVersion string = 'nac.azure-bff-performance-coordination/v1'
output storageAccountName string = storageAccount.name
output storageAccountResourceId string = storageAccount.id
output bffStorageAccountNameBinding string = bffStorageAccountName
output wormStorageAccountNameBinding string = wormStorageAccountName
output leaseContainerName string = leaseContainer.name
output leaseContainerResourceId string = leaseContainer.id
output leaseBlobPath string = leaseBlobPath
output leaseBlobUri string = '${storageAccount.properties.primaryEndpoints.blob}${leaseContainer.name}/${leaseBlobPath}'
output precreatedLeaseBlobETag string = precreatedLeaseBlobETag
output precreatedLeaseBlobType string = 'BlockBlob'
output precreatedLeaseBlobContentLength int = 0
output targetBindingSha256 string = targetBindingSha256
output provisionerIdentityResourceId string = provisionerIdentity.id
output provisionerIdentityPrincipalId string = provisionerIdentity.properties.principalId
output leaseDataRoleDefinitionId string = leaseDataRole.id
output provisionerLeaseRoleAssignmentId string = provisionerLeaseBinding.id
output exactLeaseBlobCondition string = exactLeaseBlobCondition
output allowedDataActions array = [
  blobReadDataAction
  blobWriteDataAction
]
output blobCreationIncluded bool = false
output leaseBreakAuthorizationBoundary string = 'SHARES_WRITE_DATA_ACTION_BLOCKED_IN_APP_API'
