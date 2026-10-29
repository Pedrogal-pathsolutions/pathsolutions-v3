# Pattern 12 and plan 9.3, on the agent's data in Log Analytics. All stateful:
# one e-mail when a condition starts and one when it clears.
locals {
  # Mounts that matter: snap images always read full and container mounts
  # repeat /data. /srv/banco is VM1's database disk (slice 7); /mnt is VM2's
  # temp disk, where the job's WSI lands.
  disk_mounts = ["/", "/boot", "/data", "/srv/banco", "/mnt"]
  disk_alerts = {
    disco-80 = { threshold = 80, severity = 2 }
    disco-90 = { threshold = 90, severity = 1 }
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "disco" {
  for_each                = local.disk_alerts
  name                    = "pathsol-${each.key}-v3"
  resource_group_name     = data.azurerm_resource_group.v3.name
  location                = local.location
  scopes                  = [azurerm_log_analytics_workspace.v3.id]
  description             = "Disco acima de ${each.value.threshold}% numa montagem das VMs."
  severity                = each.value.severity
  evaluation_frequency    = "PT15M"
  window_duration         = "PT15M"
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      Perf
      | where ObjectName == "Logical Disk" and CounterName == "% Used Space"
      | where InstanceName in (${join(", ", [for m in local.disk_mounts : "\"${m}\""])})
      | summarize UsoPct = max(CounterValue) by Computer, InstanceName
    KQL
    time_aggregation_method = "Maximum"
    metric_measure_column   = "UsoPct"
    operator                = "GreaterThan"
    threshold               = each.value.threshold

    dimension {
      name     = "Computer"
      operator = "Include"
      values   = ["*"]
    }

    dimension {
      name     = "InstanceName"
      operator = "Include"
      values   = ["*"]
    }

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

# Silent only counts inside VM1's hours: the runbook starts it at 06:00 and the
# auto-shutdown stops it at 23:00, Monday to Friday, Brasília time (UTC-3, no
# daylight saving). Production hours come from the load test (decision 3).
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "vm1_silencio" {
  name                    = "pathsol-vm1-silencio-v3"
  resource_group_name     = data.azurerm_resource_group.v3.name
  location                = local.location
  scopes                  = [azurerm_log_analytics_workspace.v3.id]
  description             = "A VM1 nao manda heartbeat ha 10 min, dentro do horario dela."
  severity                = 1
  evaluation_frequency    = "PT15M"
  window_duration         = "PT15M"
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      let agora = now() - 3h;
      let minuto = (agora - startofday(agora)) / 1m;
      Heartbeat
      | where TimeGenerated > ago(10m) and _ResourceId =~ "${data.azurerm_virtual_machine.vm1.id}"
      | count
      | where Count == 0 and dayofweek(agora) between (1d .. 5d) and minuto between (380 .. 1370)
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

# VM2 runs only with work queued (CLAUDE.md). Four hours of heartbeats mean
# the three deallocation layers failed (plan 9.4; 4 h until the Phase 4
# benchmark measures the worst job).
resource "azurerm_monitor_scheduled_query_rules_alert_v2" "vm2_ligada" {
  name                    = "pathsol-vm2-ligada-v3"
  resource_group_name     = data.azurerm_resource_group.v3.name
  location                = local.location
  scopes                  = [azurerm_log_analytics_workspace.v3.id]
  description             = "A VM2 esta ligada ha mais de 4 horas."
  severity                = 2
  evaluation_frequency    = "PT15M"
  window_duration         = "PT4H"
  auto_mitigation_enabled = true

  criteria {
    query                   = <<-KQL
      Heartbeat
      | where _ResourceId =~ "${data.azurerm_virtual_machine.vm2.id}"
      | summarize Batidas = count()
      | where Batidas >= 235
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

# Plan 18: an unexpected outage of VM1 writes nothing to status.json, so this
# tells Pedro. Platform causes only; the nightly shutdown is ours. Free.
# Not Unknown: every deallocation first reports cause Unknown and only seconds
# later UserInitiated (seen on 29/10, 02:51), so Unknown fired every night. A
# platform outage is still caught by its PlatformInitiated update, and inside
# VM1's hours by pathsol-vm1-silencio-v3.
resource "azurerm_monitor_activity_log_alert" "vm1_saude" {
  name                = "pathsol-vm1-saude-v3"
  resource_group_name = data.azurerm_resource_group.v3.name
  location            = "global"
  scopes              = [data.azurerm_virtual_machine.vm1.id]
  description         = "Resource Health: VM1 indisponivel ou degradada por causa da plataforma."

  criteria {
    category = "ResourceHealth"

    resource_health {
      current = ["Unavailable", "Degraded"]
      reason  = ["PlatformInitiated"]
    }
  }

  action {
    action_group_id = azurerm_monitor_action_group.alertas.id
  }

  tags = merge(local.tags, { componente = "alertas" })
}
