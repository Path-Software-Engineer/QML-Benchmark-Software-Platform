@description('Deployment region inherited from the resource group.')
param location string

param environmentName string
param existingEnvironmentResourceId string
param appName string
param gatewayImage string
param apiImage string
param dashboardImage string
param registryServer string
param registryUsername string

@secure()
param registryPassword string

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = if (empty(existingEnvironmentResourceId)) {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'azure-monitor'
    }
  }
}

var targetEnvironmentId = empty(existingEnvironmentResourceId)
  ? environment!.id
  : existingEnvironmentResourceId

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: {
    project: '09-qml-benchmark-platform'
    sprint: '3'
    costProfile: 'consumption-scale-to-zero'
    persistence: 'ephemeral-recruiter-demo'
  }
  properties: {
    environmentId: targetEnvironmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8088
        transport: 'auto'
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      registries: [
        {
          server: registryServer
          username: registryUsername
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: registryPassword
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'gateway'
          image: gatewayImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health/live'
                port: 8088
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 15
              timeoutSeconds: 5
              failureThreshold: 6
            }
          ]
        }
        {
          name: 'api'
          image: apiImage
          env: [
            {
              name: 'PROJECT_ROOT'
              value: '/workspace'
            }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1.0Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health/live'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 15
              timeoutSeconds: 5
              failureThreshold: 6
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/health/ready'
                port: 8080
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 12
            }
          ]
        }
        {
          name: 'dashboard'
          image: dashboardImage
          env: [
            {
              name: 'API_BASE_URL'
              value: 'http://127.0.0.1:8080'
            }
            {
              name: 'PUBLIC_API_BASE_URL'
              value: ''
            }
          ]
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          probes: [
            {
              type: 'Readiness'
              httpGet: {
                path: '/'
                port: 8050
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 10
              timeoutSeconds: 5
              failureThreshold: 12
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
        rules: [
          {
            name: 'recruiter-http'
            http: {
              metadata: {
                concurrentRequests: '10'
              }
            }
          }
        ]
      }
    }
  }
}

output appName string = app.name
output appUrl string = 'https://${app.properties.configuration.ingress.fqdn}'
output appResourceId string = app.id
