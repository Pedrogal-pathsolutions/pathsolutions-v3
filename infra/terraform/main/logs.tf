# Plan 9.3: the Azure Monitor Agent sends disk usage here. The agent signs in
# with Entra ID, so the workspace keys stay off.
resource "azurerm_log_analytics_workspace" "v3" {
  name                         = "pathsol-logs-v3"
  location                     = local.location
  resource_group_name          = data.azurerm_resource_group.v3.name
  sku                          = "PerGB2018"
  retention_in_days            = 30
  local_authentication_enabled = false

  tags = merge(local.tags, { componente = "logs" })
}
