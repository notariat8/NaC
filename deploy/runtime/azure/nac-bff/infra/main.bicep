targetScope = 'resourceGroup'

metadata description = 'Azure-native NaC BFF baseline for a resource-group deployment in Germany West Central.'

@description('Azure region for every regional resource. The baseline is intentionally pinned to Germany West Central.')
@allowed([
  'germanywestcentral'
])
param location string = 'germanywestcentral'

@description('Short deployment environment identifier used in resource names and tags.')
@allowed([
  'test'
])
param environmentName string = 'test'

@description('Microsoft Entra tenant ID used for inbound token validation and Microsoft Graph token acquisition.')
@minLength(36)
@maxLength(36)
param m365TenantId string

@description('Exact Microsoft Entra audience expected in access tokens issued for the NaC BFF API.')
@minLength(7)
@maxLength(256)
param bffApiAudience string

@description('Single delegated scope required on inbound BFF access tokens for this synthetic MVP.')
@allowed([
  'Matter.Read'
])
param bffRequiredDelegatedScope string

@description('Globally unique fixed Azure Function hostname for the approved synthetic MVP.')
@allowed([
  'func-nac-bff-test-funktion8'
])
param functionAppName string = 'func-nac-bff-test-funktion8'

@description('Maximum Flex Consumption instances. The upper bound is a cost-control guardrail.')
@minValue(1)
@maxValue(10)
param maximumInstanceCount int = 4

@description('Maximum simultaneous HTTP trigger invocations per Flex Consumption instance.')
@minValue(1)
@maxValue(32)
param httpPerInstanceConcurrency int = 16

@description('Additional non-sensitive resource tags. Baseline ownership tags cannot be overridden.')
param tags object = {}

var resourceToken = toLower(uniqueString(subscription().id, resourceGroup().id, environmentName))
var deploymentContainerName = 'function-releases'
var corsAllowedOrigins = [
  'https://funktion8.sharepoint.com'
  'https://teams.microsoft.com'
  'https://teams.cloud.microsoft'
]
var resourceTags = union(tags, {
  workload: 'nac-bff'
  environment: environmentName
  managedBy: 'bicep'
  dataClassification: 'no-production-data'
})

// Azure built-in role IDs. These are Azure RBAC data-plane roles, not Entra or Graph application roles.
var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b'
var monitoringMetricsPublisherRoleId = '3913510d-42f4-4e42-8a64-420c390055eb'

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-nac-bff-${environmentName}-${resourceToken}'
  location: location
  tags: resourceTags
}

// This low-cost baseline keeps Function host and deployment artifacts on the public
// storage endpoint, protected by Entra ID RBAC with anonymous blobs and shared keys disabled.
resource storageAccount 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'stnacbff${resourceToken}'
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
    deleteRetentionPolicy: {
      enabled: false
    }
  }
}

resource deploymentContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: deploymentContainerName
  properties: {
    publicAccess: 'None'
  }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-nac-bff-${environmentName}-${resourceToken}'
  location: location
  tags: resourceTags
  properties: {
    features: {
      disableLocalAuth: true
      enableLogAccessUsingOnlyResourcePermissions: true
      immediatePurgeDataOn30Days: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
    workspaceCapping: {
      dailyQuotaGb: 1
    }
  }
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-nac-bff-${environmentName}-${resourceToken}'
  location: location
  tags: resourceTags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    DisableLocalAuth: true
    IngestionMode: 'LogAnalytics'
    RetentionInDays: 30
    WorkspaceResourceId: logAnalytics.id
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
  }
}

resource applicationInsightsBilling 'Microsoft.Insights/components/CurrentBillingFeatures@2015-05-01' = {
  parent: applicationInsights
  name: 'Basic'
  location: location
  properties: {
    CurrentBillingFeatures: [
      'Basic'
    ]
    DataVolumeCap: {
      Cap: json('0.1')
      StopSendNotificationWhenHitCap: false
    }
  }
}

resource flexConsumptionPlan 'Microsoft.Web/serverfarms@2024-04-01' = {
  name: 'plan-nac-bff-${environmentName}-${resourceToken}'
  location: location
  tags: resourceTags
  kind: 'functionapp'
  sku: {
    name: 'FC1'
    tier: 'FlexConsumption'
  }
  properties: {
    reserved: true
    zoneRedundant: false
  }
}

resource storageBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, managedIdentity.id, storageBlobDataOwnerRoleId)
  scope: storageAccount
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataOwnerRoleId)
  }
}


resource monitoringMetricsPublisher 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(applicationInsights.id, managedIdentity.id, monitoringMetricsPublisherRoleId)
  scope: applicationInsights
  properties: {
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', monitoringMetricsPublisherRoleId)
  }
}

resource functionApp 'Microsoft.Web/sites@2024-04-01' = {
  name: functionAppName
  location: location
  tags: resourceTags
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    clientAffinityEnabled: false
    httpsOnly: true
    publicNetworkAccess: 'Enabled'
    serverFarmId: flexConsumptionPlan.id
    siteConfig: {
      alwaysOn: false
      cors: {
        allowedOrigins: corsAllowedOrigins
        supportCredentials: false
      }
      ftpsState: 'Disabled'
      healthCheckPath: '/healthz'
      http20Enabled: true
      minTlsVersion: '1.2'
      remoteDebuggingEnabled: false
    }
    functionAppConfig: {
      deployment: {
        storage: {
          authentication: {
            type: 'UserAssignedIdentity'
            userAssignedIdentityResourceId: managedIdentity.id
          }
          type: 'blobContainer'
          value: '${storageAccount.properties.primaryEndpoints.blob}${deploymentContainer.name}'
        }
      }
      runtime: {
        name: 'python'
        version: '3.12'
      }
      scaleAndConcurrency: {
        instanceMemoryMB: 2048
        maximumInstanceCount: maximumInstanceCount
        triggers: {
          http: {
            perInstanceConcurrency: httpPerInstanceConcurrency
          }
        }
      }
    }
  }
  dependsOn: [
    monitoringMetricsPublisher
    storageBlobDataOwner
  ]
}

resource functionAppSettings 'Microsoft.Web/sites/config@2024-04-01' = {
  parent: functionApp
  name: 'appsettings'
  properties: {
    APPLICATIONINSIGHTS_AUTHENTICATION_STRING: 'ClientId=${managedIdentity.properties.clientId};Authorization=AAD'
    APPLICATIONINSIGHTS_CONNECTION_STRING: applicationInsights.properties.ConnectionString
    AzureWebJobsStorage__accountName: storageAccount.name
    AzureWebJobsStorage__clientId: managedIdentity.properties.clientId
    AzureWebJobsStorage__credential: 'managedidentity'
    M365_TENANT_ID: m365TenantId
    NAC_BFF_TENANT_ID: m365TenantId
    NAC_BFF_AUDIENCE: bffApiAudience
    NAC_BFF_REQUIRED_SCOPE: bffRequiredDelegatedScope
    M365_RUNTIME_CLIENT_ID: managedIdentity.properties.clientId
    AZURE_CLIENT_ID: managedIdentity.properties.clientId
  }
}

output functionAppResourceId string = functionApp.id
output functionAppHostName string = functionApp.properties.defaultHostName
output functionAppSystemAssignedPrincipalId string = functionApp.identity.principalId
output managedIdentityResourceId string = managedIdentity.id
output managedIdentityClientId string = managedIdentity.properties.clientId
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
