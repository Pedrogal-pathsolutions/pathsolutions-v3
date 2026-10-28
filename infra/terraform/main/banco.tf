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
