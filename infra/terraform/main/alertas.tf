resource "azurerm_monitor_action_group" "alertas" {
  name                = "pathsol-alertas-v3"
  resource_group_name = data.azurerm_resource_group.v3.name
  short_name          = "pathsolv3"

  email_receiver {
    name                    = "pedro"
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
