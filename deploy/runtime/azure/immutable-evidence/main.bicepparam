// SPDX-License-Identifier: AGPL-3.0-or-later
// Synthetic compile input only. This file is not an Azure deployment approval.

using './main.bicep'

param storageAccountName = 'stnacwormoffline001'
param tags = {
  owner: 'replace-before-s7'
  purpose: 'offline-contract-baseline'
}
