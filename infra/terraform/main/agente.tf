# Plan 9.3: the Azure Monitor Agent sends % Used Space every 60 s to Log
# Analytics, and the disk alerts are log search alerts on it. The metrics
# destination stays out: Microsoft keeps custom metrics in preview and says
# they will not reach GA (metrics-custom-overview, read 28/10).
# Syslog local0 is where the v3 host scripts log (backup check, reconciler).
# The agent also writes one Heartbeat per minute to the workspace.
resource "azurerm_monitor_data_collection_rule" "vms" {
  name                = "pathsol-coleta-vms-v3"
  resource_group_name = data.azurerm_resource_group.v3.name
  location            = local.location
  kind                = "Linux"
  description         = "Uso de disco e syslog local0 das VMs (secao 9.3)."

  destinations {
    log_analytics {
      name                  = "logs"
      workspace_resource_id = azurerm_log_analytics_workspace.v3.id
    }
  }

  data_flow {
    streams      = ["Microsoft-Perf", "Microsoft-Syslog"]
    destinations = ["logs"]
  }

  data_sources {
    performance_counter {
      name                          = "disco"
      streams                       = ["Microsoft-Perf"]
      sampling_frequency_in_seconds = 60
      counter_specifiers            = ["Logical Disk(*)\\% Used Space"]
    }

    syslog {
      name           = "pathsol"
      streams        = ["Microsoft-Syslog"]
      facility_names = ["local0"]
      log_levels     = ["Info", "Notice", "Warning", "Error", "Critical", "Alert", "Emergency"]
    }
  }

  tags = merge(local.tags, { componente = "agente" })
}

# Plan 9.3: the agent's local cache defaults to 10,000 MB on the OS disk;
# 4,000 is the floor. azurerm has no such rule kind, and ARM is the only way
# to create it (agent-settings docs, read 28/10).
resource "azapi_resource" "agent_settings" {
  type      = "Microsoft.Insights/dataCollectionRules@2024-03-11"
  name      = "pathsol-agente-v3"
  parent_id = data.azurerm_resource_group.v3.id
  location  = local.location

  body = {
    kind = "AgentSettings"
    properties = {
      description = "Teto do cache local do agente (secao 9.3)."
      agentSettings = {
        logs = [{ name = "MaxDiskQuotaInMB", value = "4000" }]
      }
    }
  }

  tags = merge(local.tags, { componente = "agente" })
}

resource "azurerm_monitor_data_collection_rule_association" "coleta" {
  for_each                = local.vms
  name                    = "pathsol-coleta-vms-v3"
  target_resource_id      = each.value
  data_collection_rule_id = azurerm_monitor_data_collection_rule.vms.id
}

# Microsoft's example names this association agentSettings.
resource "azurerm_monitor_data_collection_rule_association" "agente" {
  for_each                = local.vms
  name                    = "agentSettings"
  target_resource_id      = each.value
  data_collection_rule_id = azapi_resource.agent_settings.id
}
