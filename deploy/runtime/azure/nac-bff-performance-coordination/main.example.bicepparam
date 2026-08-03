// SPDX-License-Identifier: AGPL-3.0-or-later
// Synthetic compile input only. This file is not an Azure deployment approval.

using './main.bicep'

param location = 'germanywestcentral'
param storageAccountName = 'stnacperflease001'
param bffStorageAccountName = 'stnacbffoffline001'
param wormStorageAccountName = 'stnacwormoffline001'
param provisionerIdentityName = 'id-nac-bff-performance-provisioner-test'
param targetBindingSha256 = '1111111111111111111111111111111111111111111111111111111111111111'
param precreatedLeaseBlobETag = '"0x8DBABCDEF012345"'
param tags = {
  owner: 'replace-before-owner-gated-deployment'
  purpose: 'offline-contract-baseline'
}
