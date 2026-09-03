targetScope = 'subscription'

@description('Azure region containing the shared Container Apps Consumption environment.')
param location string = 'centralus'

@description('Resource group dedicated to the Project 09 recruiter demo.')
param resourceGroupName string = 'rg-p9-qml-benchmark-demo'

@description('Container Apps managed environment name when creation is explicitly allowed.')
param environmentName string = 'p9qml-env'

@description('Existing Container Apps environment resource ID; empty creates a dedicated one.')
param existingEnvironmentResourceId string = ''

@description('Public Container App name.')
param appName string = 'p9qml-platform'

@description('Immutable gateway image reference.')
param gatewayImage string

@description('Immutable API image reference.')
param apiImage string

@description('Immutable dashboard image reference.')
param dashboardImage string

@description('OCI registry hostname.')
param registryServer string = 'ghcr.io'

@description('OCI registry username.')
param registryUsername string

@secure()
@description('OCI registry token with read access to the release images.')
param registryPassword string

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: resourceGroupName
  location: location
  tags: {
    project: '09-qml-benchmark-platform'
    sprint: '3'
    costProfile: 'consumption-scale-to-zero'
    persistence: 'ephemeral-recruiter-demo'
  }
}

module workload 'workload.bicep' = {
  name: 'p9qml-workload'
  scope: resourceGroup
  params: {
    location: location
    environmentName: environmentName
    existingEnvironmentResourceId: existingEnvironmentResourceId
    appName: appName
    gatewayImage: gatewayImage
    apiImage: apiImage
    dashboardImage: dashboardImage
    registryServer: registryServer
    registryUsername: registryUsername
    registryPassword: registryPassword
  }
}

output appUrl string = workload.outputs.appUrl
output appName string = workload.outputs.appName
output appResourceId string = workload.outputs.appResourceId
output resourceGroupName string = resourceGroup.name
output costBoundary string = 'Consumption minReplicas=0 maxReplicas=1; shared environment; no ACR, Log Analytics, Azure Files or managed database.'
output persistenceBoundary string = 'Cloud reports use replica memory and reset after scale-to-zero or replacement.'
