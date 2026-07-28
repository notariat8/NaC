// SPDX-License-Identifier: AGPL-3.0-or-later
// Offline create/update baseline only. Locking is a separate owner-gated S7 action.

targetScope = 'resourceGroup'

@allowed([
  'germanywestcentral'
])
param location string = 'germanywestcentral'

@minLength(3)
@maxLength(24)
param storageAccountName string

@minLength(3)
@maxLength(63)
param containerName string = 'nac-worm-tenant'

@minLength(3)
@maxLength(63)
param encryptionScopeName string = 'nac-worm-tenant'

param tags object = {}

var immutableRetentionDays = 3653
var targetIsolationSuffix = uniqueString(subscription().tenantId, resourceGroup().id, storageAccountName)
var keyVaultName = 'kv-nacw-${targetIsolationSuffix}'
var cmkIdentityName = 'id-nac-worm-cmk-${targetIsolationSuffix}'
var writerIdentityName = 'id-nac-worm-writer-${targetIsolationSuffix}'
var keyVaultCryptoServiceEncryptionUserRoleId = 'e147488a-f6f5-4113-8e2d-b22465e65bf6'
var writerDataRoleId = guid(subscription().id, resourceGroup().id, 'nac-worm-blob-add-read-v2')
var writerManagementReadRoleId = guid(subscription().id, resourceGroup().id, 'nac-worm-management-read-v1')
var providerTenantBindingSha256 = sha256('nac.azure-provider-tenant.v1|${subscription().tenantId}')
var providerSubscriptionBindingSha256 = sha256('nac.azure-subscription-resource.v1|${subscription().id}')
var providerResourceBindingSha256 = sha256('nac.azure-storage-resource.v1|${resourceId('Microsoft.Storage/storageAccounts', storageAccountName)}')
var providerContextBindingSha256 = sha256('nac.azure-provider-context.v1|${providerTenantBindingSha256}|${providerSubscriptionBindingSha256}|${providerResourceBindingSha256}')
var baselineTags = union(tags, {
  workload: 'nac-immutable-evidence'
  status: 'S6B_AZURE_WORM_ADAPTER_READY_OFFLINE'
  liveStatus: 'BLOCKED_PENDING_S7_APPROVAL'
  providerTenantBindingSha256: providerTenantBindingSha256
  providerSubscriptionBindingSha256: providerSubscriptionBindingSha256
  providerResourceBindingSha256: providerResourceBindingSha256
  providerContextBindingSha256: providerContextBindingSha256
  providerContextBindingSource: 'azure-subscription-resource-tenant-readback'
  dataClassification: 'pseudonymous-personal-data'
})

resource cmkIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: cmkIdentityName
  location: location
  tags: baselineTags
}

resource writerIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: writerIdentityName
  location: location
  tags: baselineTags
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  tags: baselineTags
  properties: {
    enablePurgeProtection: true
    enableRbacAuthorization: true
    enableSoftDelete: true
    publicNetworkAccess: 'Disabled'
    sku: {
      family: 'A'
      name: 'standard'
    }
    softDeleteRetentionInDays: 90
    tenantId: subscription().tenantId
  }
}

resource keyVaultKey 'Microsoft.KeyVault/vaults/keys@2023-07-01' = {
  parent: keyVault
  name: 'nac-worm-cmk'
  properties: {
    attributes: {
      enabled: true
      exportable: false
    }
    keyOps: [
      'wrapKey'
      'unwrapKey'
    ]
    keySize: 3072
    kty: 'RSA'
  }
}

resource cmkEncryptionRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, cmkIdentity.id, keyVaultCryptoServiceEncryptionUserRoleId)
  scope: keyVault
  properties: {
    principalId: cmkIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      keyVaultCryptoServiceEncryptionUserRoleId
    )
  }
}

resource writerDataRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: writerDataRoleId
  scope: subscription()
  properties: {
    roleName: 'NaC WORM Blob Add Read'
    description: 'Add and read immutable evidence blobs without overwrite or lifecycle permissions.'
    type: 'CustomRole'
    permissions: [
      {
        actions: []
        notActions: []
        dataActions: [
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'
          'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'
        ]
        notDataActions: []
      }
    ]
    assignableScopes: [
      resourceGroup().id
    ]
  }
}

resource writerManagementReadRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: writerManagementReadRoleId
  scope: subscription()
  properties: {
    roleName: 'NaC WORM Storage Policy Read'
    description: 'Read only the container, immutability policy, and encryption scope required for fail-closed verification.'
    type: 'CustomRole'
    permissions: [
      {
        actions: [
          'Microsoft.Storage/storageAccounts/blobServices/containers/read'
          'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies/read'
          'Microsoft.Storage/storageAccounts/encryptionScopes/read'
        ]
        notActions: []
        dataActions: []
        notDataActions: []
      }
    ]
    assignableScopes: [
      resourceGroup().id
    ]
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageAccountName
  location: location
  tags: baselineTags
  kind: 'StorageV2'
  sku: {
    name: 'Standard_ZRS'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${cmkIdentity.id}': {}
    }
  }
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Disabled'
    supportsHttpsTrafficOnly: true
    networkAcls: {
      bypass: 'None'
      defaultAction: 'Deny'
      ipRules: []
      virtualNetworkRules: []
    }
    encryption: {
      identity: {
        userAssignedIdentity: cmkIdentity.id
      }
      keySource: 'Microsoft.Keyvault'
      keyvaultproperties: {
        keyname: keyVaultKey.name
        keyvaulturi: keyVault.properties.vaultUri
      }
      requireInfrastructureEncryption: true
      services: {
        blob: {
          enabled: true
          keyType: 'Account'
        }
      }
    }
  }
  dependsOn: [
    cmkEncryptionRole
  ]
}

resource encryptionScope 'Microsoft.Storage/storageAccounts/encryptionScopes@2023-05-01' = {
  parent: storage
  name: encryptionScopeName
  properties: {
    keyVaultProperties: {
      keyUri: keyVaultKey.properties.keyUriWithVersion
    }
    requireInfrastructureEncryption: true
    source: 'Microsoft.KeyVault'
    state: 'Enabled'
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: {
    isVersioningEnabled: true
    changeFeed: {
      enabled: true
      retentionInDays: 90
    }
    deleteRetentionPolicy: {
      enabled: false
    }
    containerDeleteRetentionPolicy: {
      enabled: false
    }
  }
}

resource evidenceContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: containerName
  properties: {
    defaultEncryptionScope: encryptionScopeName
    denyEncryptionScopeOverride: true
    publicAccess: 'None'
    immutableStorageWithVersioning: {
      enabled: true
    }
    metadata: {
      nac_schema_version: 'nac.azure-blob-worm-container/v0.4'
      nac_status: 'S6B_AZURE_WORM_ADAPTER_READY_OFFLINE'
      provider_tenant_binding_sha256: providerTenantBindingSha256
      provider_subscription_binding_sha256: providerSubscriptionBindingSha256
      provider_resource_binding_sha256: providerResourceBindingSha256
      provider_context_binding_sha256: providerContextBindingSha256
      provider_context_binding_source: 'azure-subscription-resource-tenant-readback'
      legal_hold_capability_source: 'container-policy-properties'
      minimum_retention_days: '${immutableRetentionDays}'
      encryption_scope: encryptionScopeName
      encryption_key_source: 'Microsoft.Keyvault'
    }
  }
  dependsOn: [
    encryptionScope
  ]
}

resource writerBlobRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(evidenceContainer.id, writerIdentity.id, writerDataRole.id)
  scope: evidenceContainer
  properties: {
    principalId: writerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: writerDataRole.id
  }
}

resource writerManagementReadAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, writerIdentity.id, writerManagementReadRole.id)
  scope: storage
  properties: {
    principalId: writerIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: writerManagementReadRole.id
  }
}

resource baselineImmutabilityPolicy 'Microsoft.Storage/storageAccounts/blobServices/containers/immutabilityPolicies@2023-05-01' = {
  parent: evidenceContainer
  name: 'default'
  properties: {
    allowProtectedAppendWrites: false
    allowProtectedAppendWritesAll: false
    immutabilityPeriodSinceCreationInDays: immutableRetentionDays
  }
}

output offlineStatus string = 'S6B_AZURE_WORM_ADAPTER_READY_OFFLINE'
output liveStatus string = 'BLOCKED_PENDING_S7_APPROVAL'
output lockActionStatus string = 'OWNER_GATED_NOT_EXECUTED'
output lockTargetResourceId string = baselineImmutabilityPolicy.id
output configuredContainerName string = evidenceContainer.name
output configuredEncryptionScope string = encryptionScope.name
output configuredProviderTenantBindingSha256 string = providerTenantBindingSha256
output configuredProviderSubscriptionBindingSha256 string = providerSubscriptionBindingSha256
output configuredProviderResourceBindingSha256 string = providerResourceBindingSha256
output configuredProviderContextBindingSha256 string = providerContextBindingSha256
output providerContextBindingSource string = 'azure-subscription-resource-tenant-readback'
output cmkIdentityResourceId string = cmkIdentity.id
output writerIdentityResourceId string = writerIdentity.id
output writerDataRoleDefinitionId string = writerDataRole.id
output writerManagementReadRoleDefinitionId string = writerManagementReadRole.id
