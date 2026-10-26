// Optional supporting services. Invoked only with enableSupportServices=true.
// These consume student credit if usage exceeds service grants. No paid upgrade.
targetScope = 'resourceGroup'
param location string
param name string
// Select a region supporting text analysis, subject to the subscription's policy.
param contentSafetyLocation string = 'uaenorth'

resource safety 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: '${name}-safety'
  location: contentSafetyLocation
  kind: 'ContentSafety'
  sku: { name: 'F0' }
  properties: {
    customSubDomainName: '${name}-safety'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: 'pp${uniqueString(resourceGroup().id)}'
  location: location
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}
resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: { deleteRetentionPolicy: { enabled: true, days: 7 } }
}
resource receipts 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobs
  name: 'receipts'
  properties: { publicAccess: 'None' }
}
resource retention 'Microsoft.Storage/storageAccounts/managementPolicies@2023-05-01' = {
  parent: storage
  name: 'default'
  properties: { policy: { rules: [{
    name: 'expire-receipts'
    enabled: true
    type: 'Lifecycle'
    definition: {
      filters: { blobTypes: ['blockBlob'], prefixMatch: ['receipts/'] }
      actions: { baseBlob: { delete: { daysAfterModificationGreaterThan: 30 } } }
    }
  }] } }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: 'pp-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Enabled'
  }
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${name}-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: json('0.1') }
  }
}
resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${name}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    IngestionMode: 'LogAnalytics'
    DisableIpMasking: false
  }
}

output contentSafetyEndpoint string = safety.properties.endpoint
output contentSafetyId string = safety.id
output contentSafetyName string = safety.name
output blobEndpoint string = storage.properties.primaryEndpoints.blob
output receiptContainerId string = receipts.id
output storageName string = storage.name
output keyVaultEndpoint string = vault.properties.vaultUri
output keyVaultId string = vault.id
output insightsConnectionString string = insights.properties.ConnectionString
