resource "azurerm_monitor_action_group" "alertas" {
  name                = "pathsol-alertas-v3"
  resource_group_name = data.azurerm_resource_group.v3.name
  short_name          = "pathsolv3"

  # The portal set this name on 29/10, when Pedro confirmed the address with the
  # one-time code that action groups now require; renaming it means another write.
  email_receiver {
    name                    = "Reynaldo_-EmailAction-"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }

  tags = merge(local.tags, { componente = "alertas" })
}

# D3 ceiling. Cost Management shows list prices; the CSP partner invoice may differ.
# It only warns, 1 to 3 days late, and never stops resources.
resource "azurerm_consumption_budget_subscription" "teto" {
  name            = "pathsol-orcamento-v3"
  subscription_id = data.azurerm_subscription.current.id
  amount          = 5000
  time_grain      = "Monthly"

  time_period {
    start_date = "2026-10-01T00:00:00Z"
  }

  dynamic "notification" {
    for_each = {
      actual_50    = { threshold = 50, type = "Actual" }
      actual_80    = { threshold = 80, type = "Actual" }
      actual_100   = { threshold = 100, type = "Actual" }
      forecast_100 = { threshold = 100, type = "Forecasted" }
    }
    content {
      threshold      = notification.value.threshold
      threshold_type = notification.value.type
      operator       = "GreaterThanOrEqualTo"
      contact_emails = [var.alert_email]
    }
  }
}

# Pattern 6 (plan 6.4): writes that weaken the WSI protection. Free. Success and
# failure both fire, so a denied attempt alerts too; Pedro's applies fire some.
# Turning shared key back on is a storage account write, and it is the only way
# the keys Terraform reads with listKeys become usable; every plan calls
# listKeys, so it gets no alert of its own.
locals {
  control_plane_alerts = {
    clear-legal-hold = {
      operation = "Microsoft.Storage/storageAccounts/blobServices/containers/clearLegalHold/action"
      scope     = data.azurerm_resource_group.v3.id
    }
    lifecycle-write = {
      operation = "Microsoft.Storage/storageAccounts/managementPolicies/write"
      scope     = data.azurerm_resource_group.v3.id
    }
    lifecycle-delete = {
      operation = "Microsoft.Storage/storageAccounts/managementPolicies/delete"
      scope     = data.azurerm_resource_group.v3.id
    }
    container-delete = {
      operation = "Microsoft.Storage/storageAccounts/blobServices/containers/delete"
      scope     = data.azurerm_resource_group.v3.id
    }
    storage-write = {
      operation = "Microsoft.Storage/storageAccounts/write"
      scope     = data.azurerm_resource_group.v3.id
    }
    # Turning blob soft delete off or shortening it is a blob service write.
    blob-service-write = {
      operation = "Microsoft.Storage/storageAccounts/blobServices/write"
      scope     = data.azurerm_resource_group.v3.id
    }
    storage-delete = {
      operation = "Microsoft.Storage/storageAccounts/delete"
      scope     = data.azurerm_resource_group.v3.id
    }
    lock-delete = {
      operation = "Microsoft.Authorization/locks/delete"
      scope     = data.azurerm_resource_group.v3.id
    }
    # Subscription scope: an assignment there is inherited by the group.
    role-assignment = {
      operation = "Microsoft.Authorization/roleAssignments/write"
      scope     = data.azurerm_subscription.current.id
    }
    # Editing pathsol-blob-sem-exclusao-v3 could add delete to it.
    role-definition = {
      operation = "Microsoft.Authorization/roleDefinitions/write"
      scope     = data.azurerm_subscription.current.id
    }
  }
}

resource "azurerm_monitor_activity_log_alert" "control_plane" {
  for_each            = local.control_plane_alerts
  name                = "pathsol-${each.key}-v3"
  resource_group_name = data.azurerm_resource_group.v3.name
  location            = "global"
  scopes              = [each.value.scope]
  description         = "Activity log: ${each.value.operation}"

  criteria {
    category       = "Administrative"
    operation_name = each.value.operation
    statuses       = ["Succeeded", "Failed"]
  }

  action {
    action_group_id = azurerm_monitor_action_group.alertas.id
  }

  tags = merge(local.tags, { componente = "alertas" })
}
