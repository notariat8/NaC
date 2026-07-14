using './main.bicep'

param location = 'germanywestcentral'
param environmentName = 'test'
param m365TenantId = '00000000-0000-0000-0000-000000000001'
param bffApiAudience = '00000000-0000-0000-0000-000000000002'
param bffRequiredDelegatedScope = 'Matter.Read'
param functionAppName = 'func-nac-bff-test-funktion8'
param maximumInstanceCount = 4
param httpPerInstanceConcurrency = 16
param tags = {
  owner: 'replace-with-owner'
  costCenter: 'replace-with-cost-center'
  purpose: 'offline-contract-example'
}
