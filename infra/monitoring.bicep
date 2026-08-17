// Azure Monitor for Greenroom — Log Analytics + Application Insights + alert
// rules for the two existing Container Apps (greenroom-api, greenroom-frontend)
// in resource group `greenroom-rg`. The self-hosted Piston container app
// (greenroom-piston) was decommissioned 2026-08-03 in favor of the external
// Judge0 service — see DESIGN.md §3 — so it's no longer monitored here.
//
// Nothing here is deployed yet — this is a proposal to review before running.
// Deploy (after `az login`):
//   az deployment group create \
//     --resource-group greenroom-rg \
//     --template-file infra/monitoring.bicep \
//     --parameters @infra/monitoring.parameters.json
//
// After deploying, point the backend at the connection string so app-level
// events show up in Application Insights (not just container-level metrics):
//   az containerapp update --name greenroom-api --resource-group greenroom-rg \
//     --set-env-vars APPLICATIONINSIGHTS_CONNECTION_STRING="<output.appInsightsConnectionString>"
// (services/logger.py's structured JSON logs already give you most of what
// App Insights would add, via Log Analytics's ContainerAppConsoleLogs_CL
// table — the connection string is only needed if you also want the Python
// SDK's request/dependency auto-instrumentation.)

@description('Existing Container Apps environment resource ID (same one the apps already use)')
param environmentId string

@description('Email address(es) to notify on alert — comma-separated for multiple')
param alertEmail string

@description('Container App names to monitor')
param containerAppNames array = ['greenroom-api', 'greenroom-frontend']

var location = resourceGroup().location

// ── Log Analytics workspace ──────────────────────────────────────────────────
// The Container Apps environment likely already has one attached (Container
// Apps requires it) — check `az containerapp env show` for
// `properties.appLogsConfiguration.logAnalyticsConfiguration` before creating
// a second one. This resource is idempotent either way (same name = reuse).
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'greenroom-logs'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

// ── Application Insights (optional app-level tracing) ────────────────────────
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'greenroom-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// ── Action group (where alerts notify) ───────────────────────────────────────
resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: 'greenroom-alerts'
  location: 'global'
  properties: {
    groupShortName: 'grroomalert'
    enabled: true
    emailReceivers: [
      {
        name: 'primary'
        emailAddress: alertEmail
        useCommonAlertSchema: true
      }
    ]
  }
}

// ── Metric alerts, one set per container app ─────────────────────────────────
// Container Apps exposes these as standard platform metrics — no custom
// instrumentation needed, so these are safe to deploy immediately.
resource httpErrorAlerts 'Microsoft.Insights/metricAlerts@2018-03-01' = [for name in containerAppNames: {
  name: 'greenroom-${name}-5xx-rate'
  location: 'global'
  properties: {
    severity: 2 // warning
    enabled: true
    scopes: [resourceId('Microsoft.App/containerApps', name)]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'Http5xxCount'
          metricName: 'Requests'
          metricNamespace: 'Microsoft.App/containerApps'
          dimensions: [
            { name: 'statusCodeCategory', operator: 'Include', values: ['5xx'] }
          ]
          operator: 'GreaterThan'
          threshold: 10
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroup.id }]
  }
}]

resource restartAlerts 'Microsoft.Insights/metricAlerts@2018-03-01' = [for name in containerAppNames: {
  name: 'greenroom-${name}-restarts'
  location: 'global'
  properties: {
    severity: 1 // error — a restart loop means the app is actively down for someone
    enabled: true
    scopes: [resourceId('Microsoft.App/containerApps', name)]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'RestartCount'
          metricName: 'RestartCount'
          metricNamespace: 'Microsoft.App/containerApps'
          operator: 'GreaterThan'
          threshold: 2
          timeAggregation: 'Total'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroup.id }]
  }
}]

// CPU/memory pressure — Container Apps auto-scales, but sustained high usage
// at maxReplicas (backend caps at 2, per backend-container-app.bicep) means
// it's scaled out as far as it can and is still under load.
resource cpuAlerts 'Microsoft.Insights/metricAlerts@2018-03-01' = [for name in containerAppNames: {
  name: 'greenroom-${name}-high-cpu'
  location: 'global'
  properties: {
    severity: 3 // informational — a nudge to raise maxReplicas/cpu, not a page
    enabled: true
    scopes: [resourceId('Microsoft.App/containerApps', name)]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          name: 'HighCpuUsage'
          metricName: 'UsageNanoCores'
          metricNamespace: 'Microsoft.App/containerApps'
          operator: 'GreaterThan'
          threshold: 900000000 // 0.9 core sustained, i.e. near the 1-core cap most replicas run at
          timeAggregation: 'Average'
          criterionType: 'StaticThresholdCriterion'
        }
      ]
    }
    actions: [{ actionGroupId: actionGroup.id }]
  }
}]

output logAnalyticsWorkspaceId string = logAnalytics.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
