# VM1, VM2 and the Automation account of the morning runbook predate the v3:
# Terraform only reads them (CLAUDE.md). Disks, identities and extensions on
# them are changed by az, one authorization each.
data "azurerm_resource_group" "vms" {
  name = "rg-prod-brsouth-001"
}

data "azurerm_virtual_machine" "vm1" {
  name                = "vm-appviewer-prod-001"
  resource_group_name = data.azurerm_resource_group.vms.name
}

data "azurerm_virtual_machine" "vm2" {
  name                = "vm-appfoundation-prod-001"
  resource_group_name = data.azurerm_resource_group.vms.name
}

data "azurerm_automation_account" "runbook" {
  name                = "asa-prod-brsouth-001"
  resource_group_name = data.azurerm_resource_group.vms.name
}

locals {
  vms = {
    vm1 = data.azurerm_virtual_machine.vm1.id
    vm2 = data.azurerm_virtual_machine.vm2.id
  }
}
