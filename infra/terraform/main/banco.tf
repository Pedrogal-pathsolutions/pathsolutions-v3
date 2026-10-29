# Plan 7 (pattern 8): Postgres runs in a container on VM1, on a disk of its
# own, so a full cache never stops the database. az attaches it with host
# cache ReadOnly (ReadWrite can lose data if the VM crashes); XFS on it.
resource "azurerm_managed_disk" "banco" {
  name                 = "pathsol-banco-v3"
  location             = local.location
  resource_group_name  = data.azurerm_resource_group.v3.name
  storage_account_type = "Premium_LRS"
  create_option        = "Empty"
  disk_size_gb         = 64 # P6

  network_access_policy         = "DenyAll"
  public_network_access_enabled = false

  tags = merge(local.tags, { componente = "banco" })

  lifecycle {
    prevent_destroy = true
  }
}

# Plan 7: pgBackRest repository (pgbackrest/) and the daily pg_dump (dump/).
# No legal hold and outside the WSI cold rule. Backups past 35 days are the
# only blobs the v3 ever deletes (CLAUDE.md, decision 1).
resource "azurerm_storage_container" "backup" {
  name               = "backup-banco"
  storage_account_id = azurerm_storage_account.wsi.id

  lifecycle {
    prevent_destroy = true
  }
}

# Plan 7: pathsol-banco writes every check of the database, the backups, the
# restore test and the TLS certificates to syslog local0; failures with
# priority err, which the agent stores as SeverityLevel "error" (seen 29/10).
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "banco_falha" {
  name                    = "pathsol-banco-falha-v3"
  resource_group_name     = data.azurerm_resource_group.v3.name
  location                = local.location
  scopes                  = [azurerm_log_analytics_workspace.v3.id]
  description             = "Falha no banco, no backup, no dump, na restauracao ou num certificado TLS (Syslog local0, pathsol-banco)."
  severity                = 1
  evaluation_frequency    = "PT15M"
  window_duration         = "PT30M"
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      Syslog
      | where _ResourceId =~ "${data.azurerm_virtual_machine.vm1.id}"
      | where Facility == "local0" and ProcessName == "pathsol-banco" and SeverityLevel == "error"
      | summarize Falhas = count()
    KQL
    time_aggregation_method = "Total"
    metric_measure_column   = "Falhas"
    operator                = "GreaterThan"
    threshold               = 0

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.alertas.id]
  }

  tags = merge(local.tags, { componente = "alertas" })
}

# The legacy backup stopped without a sound after 15/09 (plan 7): the checks
# run every 15 min, so 40 min without a line inside VM1's hours (from 06:40,
# after the first run past boot) means they stopped.
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "banco_silencio" {
  name                    = "pathsol-banco-silencio-v3"
  resource_group_name     = data.azurerm_resource_group.v3.name
  location                = local.location
  scopes                  = [azurerm_log_analytics_workspace.v3.id]
  description             = "A verificacao do banco nao grava no syslog ha 40 min, dentro do horario da VM1."
  severity                = 2
  evaluation_frequency    = "PT15M"
  window_duration         = "PT45M"
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      let agora = now() - 3h;
      let minuto = (agora - startofday(agora)) / 1m;
      Syslog
      | where TimeGenerated > ago(40m) and _ResourceId =~ "${data.azurerm_virtual_machine.vm1.id}"
      | where Facility == "local0" and ProcessName == "pathsol-banco"
      | count
      | where Count == 0 and dayofweek(agora) between (1d .. 5d) and minuto between (400 .. 1370)
    KQL
    time_aggregation_method = "Count"
    operator                = "GreaterThan"
    threshold               = 0

    failing_periods {
      minimum_failing_periods_to_trigger_alert = 1
      number_of_evaluation_periods             = 1
    }
  }

  action {
    action_groups = [azurerm_monitor_action_group.alertas.id]
  }

  tags = merge(local.tags, { componente = "alertas" })
}
