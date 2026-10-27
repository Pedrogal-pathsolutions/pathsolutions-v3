# Decision 2 (a): these replace the P20 of VM1 and the P15 of VM2, which are
# deleted outside Terraform, one authorization each. Terraform only creates
# them; az attaches them, because the VMs stay out of Terraform. Not zonal,
# like both VMs.
locals {
  data_disks_gb = {
    vm1 = 128 # P10: Docker and containerd roots and the caches (plan 5.4)
    vm2 = 64  # P6: Docker and containerd roots; jobs use the temp disk
  }
}

resource "azurerm_managed_disk" "data" {
  for_each             = local.data_disks_gb
  name                 = "pathsol-dados-${each.key}-v3"
  location             = local.location
  resource_group_name  = data.azurerm_resource_group.v3.name
  storage_account_type = "Premium_LRS"
  create_option        = "Empty"
  disk_size_gb         = each.value

  # No export or import by SAS: the VM1 tile cache keeps copies of WSIs.
  network_access_policy         = "DenyAll"
  public_network_access_enabled = false

  tags = merge(local.tags, { componente = "disco-${each.key}" })

  lifecycle {
    prevent_destroy = true
  }
}
