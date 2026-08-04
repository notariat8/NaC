// SPDX-License-Identifier: AGPL-3.0-or-later
// Synthetic compile input only. This file is not an Azure deployment approval.

using './main.bicep'

param tenantId = '870c862b-56f7-4c9b-b0d9-f1f7d32c835c'
param subscriptionId = '37cd9645-6cb9-4278-88ee-e80377cd951c'
param resourceGroupName = 'rg-nac-bff-test'
param deploymentMode = 'Incremental'
param storageAccountName = 'stnacwormoffline001'
param tags = {
  owner: 'replace-before-s7'
  purpose: 'offline-contract-baseline'
}
