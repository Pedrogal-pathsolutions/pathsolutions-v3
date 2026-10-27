# Plan 9.1. Azure queues have no queue-level TTL: the producer sets each
# message's TTL to -1 (never expires) and its visibility timeout.
resource "azurerm_storage_queue" "jobs" {
  name               = "jobs"
  storage_account_id = azurerm_storage_account.wsi.id
}

# Plan 9.2: queue metrics are per account, not per queue, so the dead-letter
# queue gets an account of its own. LRS: its messages carry only internal ids,
# and the job state lives in Postgres.
resource "azurerm_storage_account" "dead_letter" {
  name                            = "pathsoldlqv3"
  resource_group_name             = data.azurerm_resource_group.v3.name
  location                        = local.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  access_tier                     = "Hot"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false

  tags = merge(local.tags, { componente = "dead-letter" })

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_queue" "dead_letter" {
  name               = "jobs-dead-letter"
  storage_account_id = azurerm_storage_account.dead_letter.id
}

resource "azurerm_monitor_metric_alert" "dead_letter_new" {
  name                = "pathsol-dlq-mensagem-nova-v3"
  resource_group_name = data.azurerm_resource_group.v3.name
  scopes              = ["${azurerm_storage_account.dead_letter.id}/queueServices/default"]
  description         = "Mensagem nova na dead-letter: um job falhou 3 vezes."
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.Storage/storageAccounts/queueServices"
    metric_name      = "Transactions"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0

    dimension {
      name     = "ApiName"
      operator = "Include"
      values   = ["PutMessage"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.alertas.id
  }

  tags = merge(local.tags, { componente = "alertas" })
}

# Stays fired while the queue is not empty. QueueMessageCount is counted about
# once a day (plan 9.2), so this one fires and clears late.
resource "azurerm_monitor_metric_alert" "dead_letter_not_empty" {
  name                = "pathsol-dlq-nao-vazia-v3"
  resource_group_name = data.azurerm_resource_group.v3.name
  scopes              = ["${azurerm_storage_account.dead_letter.id}/queueServices/default"]
  description         = "A dead-letter tem mensagens esperando tratamento."
  severity            = 2
  frequency           = "PT1H"
  window_size         = "P1D"

  criteria {
    metric_namespace = "Microsoft.Storage/storageAccounts/queueServices"
    metric_name      = "QueueMessageCount"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.alertas.id
  }

  tags = merge(local.tags, { componente = "alertas" })
}
