// SPDX-License-Identifier: AGPL-3.0-or-later
// Synthetic compile input only. This file is not an Azure deployment approval.

using './main.bicep'

param location = 'germanywestcentral'
param tenantId = '870c862b-56f7-4c9b-b0d9-f1f7d32c835c'
param subscriptionId = '37cd9645-6cb9-4278-88ee-e80377cd951c'
param resourceGroupName = 'rg-nac-bff-test'
param storageAccountName = 'stnacperflease001'
param bffStorageAccountResourceId = '/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/resourceGroups/rg-nac-bff-test/providers/Microsoft.Storage/storageAccounts/stnacbffoffline001'
param wormStorageAccountResourceId = '/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/resourceGroups/rg-nac-worm/providers/Microsoft.Storage/storageAccounts/stnacwormoffline001'
// Azure blobs/add creates the exact bound blob; blobs/write also permits overwrite and
// lease break. Account/path scope and sealed APIs provide defense-in-depth.
param provisionerPrincipalId = '11111111-2222-4333-8444-555555555555'
param allowedClientIpAddress = '203.0.113.10'
param targetBindingSha256 = '1111111111111111111111111111111111111111111111111111111111111111'
param tags = {
  owner: 'replace-before-owner-gated-deployment'
  purpose: 'offline-contract-baseline'
}
