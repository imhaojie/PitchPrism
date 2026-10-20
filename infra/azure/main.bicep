targetScope = 'resourceGroup'

param location string = resourceGroup().location
param name string = 'pitchprism-${uniqueString(resourceGroup().id)}'
param modelName string
param modelVersion string
param deploymentName string = 'pitchprism-story'
param capacity int = 1
// Public, prebuilt image. No dedicated GPU, VM or provisioned model throughput.
param containerImage string = ''

resource foundry 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: name
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: name
    allowProjectManagement: true
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: foundry
  name: 'pitchprism'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: { displayName: 'PitchPrism', description: 'Evidence-grounded synthetic football stories' }
}

resource model 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundry
  name: deploymentName
  sku: { name: 'GlobalStandard', capacity: capacity }
  properties: {
    model: { format: 'OpenAI', name: modelName, version: modelVersion }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2025-01-01' = if (!empty(containerImage)) {
  name: '${name}-env'
  location: location
  properties: {
    // Console logs stay in the Container Apps platform; no paid Log Analytics workspace.
    appLogsConfiguration: { destination: 'none' }
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
  }
}

resource app 'Microsoft.App/containerApps@2025-01-01' = if (!empty(containerImage)) {
  name: 'pitchprism'
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: environment!.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: { external: true, targetPort: 4180, allowInsecure: false, transport: 'http' }
    }
    template: {
      containers: [{
        name: 'pitchprism'
        image: containerImage
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: [
          { name: 'AZURE_OPENAI_ENDPOINT', value: 'https://${foundry.name}.openai.azure.com' }
          { name: 'AZURE_OPENAI_DEPLOYMENT', value: model.name }
          { name: 'AZURE_USE_ENTRA', value: '1' }
          { name: 'PITCHPRISM_MAX_AI_CALLS_HOUR', value: '12' }
        ]
        probes: [{ type: 'Liveness', httpGet: { path: '/api/health', port: 4180 }, initialDelaySeconds: 10, periodSeconds: 30 }]
      }]
      scale: { minReplicas: 0, maxReplicas: 1, rules: [{ name: 'http', http: { metadata: { concurrentRequests: '10' } } }] }
    }
  }
}

resource modelUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(containerImage)) {
  name: guid(foundry.id, app!.id, 'model-user')
  scope: foundry
  properties: {
    principalId: app!.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

output endpoint string = 'https://${foundry.name}.openai.azure.com'
output foundryResourceId string = foundry.id
output modelDeployment string = model.name
output demoUrl string = empty(containerImage) ? '' : 'https://${app!.properties.configuration.ingress.fqdn}'
