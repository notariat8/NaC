// SPDX-License-Identifier: AGPL-3.0-or-later
// Synthetic compile input only. This file is not an Azure deployment approval.

using './main.bicep'

param location = 'germanywestcentral'
param tenantId = '870c862b-56f7-4c9b-b0d9-f1f7d32c835c'
param subscriptionId = '37cd9645-6cb9-4278-88ee-e80377cd951c'
param resourceGroupName = 'rg-nac-bff-test'
param deploymentMode = 'Incremental'
param storageAccountName = 'stnacperflease001'
param bffStorageAccountResourceId = '/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/storageAccounts/stnacbffoffline001'
param wormStorageAccountResourceId = '/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/resourceGroups/rg-nac-worm/providers/Microsoft.Storage/storageAccounts/stnacwormoffline001'
// Bootstrap can only read/add the exact bound blob. Runtime can only read/write it;
// its write capability also permits overwrite and lease break. The distinct identities,
// account/path scope, and sealed APIs provide defense-in-depth.
param bootstrapPrincipalId = '11111111-2222-4333-8444-555555555555'
param runtimePrincipalId = '66666666-7777-4888-8999-aaaaaaaaaaaa'
param bootstrapCertificateSha256 = '1111111111111111111111111111111111111111111111111111111111111111'
param runtimeCertificateSha256 = '2222222222222222222222222222222222222222222222222222222222222222'
param allowedClientIpAddress = '203.0.113.10'
param targetBindingSha256 = '1111111111111111111111111111111111111111111111111111111111111111'
param tags = {
  owner: 'replace-before-owner-gated-deployment'
  purpose: 'offline-contract-baseline'
}
