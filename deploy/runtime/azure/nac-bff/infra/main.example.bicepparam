using './main.bicep'

param location = 'germanywestcentral'
param environmentName = 'test'
param m365TenantId = '00000000-0000-0000-0000-000000000001'
param bffApiAudience = 'api://00000000-0000-0000-0000-000000000002'
param bffRequiredDelegatedScope = 'Matter.Read'
param maximumInstanceCount = 4
param httpPerInstanceConcurrency = 16
param tags = {
  owner: 'replace-with-owner'
  costCenter: 'replace-with-cost-center'
  purpose: 'offline-contract-example'
}
