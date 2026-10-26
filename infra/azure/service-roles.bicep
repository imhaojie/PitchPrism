targetScope = 'resourceGroup'
param principalId string
param contentSafetyName string
param storageName string

resource safety 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = { name: contentSafetyName }
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' existing = { name: storageName }
resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' existing = { parent: storage, name: 'default' }
resource receipts 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' existing = { parent: blobs, name: 'receipts' }
resource safetyUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(safety.id, principalId, 'safety-user')
  scope: safety
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'a97b65f3-24c7-4388-baec-2e87135dc908')
  }
}
resource receiptWriter 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(receipts.id, principalId, 'receipt-writer')
  scope: receipts
  properties: {
    principalId: principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
  }
}
