# Plan 4.3: the JWT signing key and the other secrets. Azure RBAC only; each
# identity gets its role when it first needs the vault.
# Key Vault soft delete cannot be turned off, and its retention is fixed at
# creation. Purge protection stays off: once on, it can never be turned off.
resource "azurerm_key_vault" "v3" {
  name                       = "pathsol-kv-v3"
  location                   = local.location
  resource_group_name        = data.azurerm_resource_group.v3.name
  tenant_id                  = data.azurerm_subscription.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  soft_delete_retention_days = 90
  purge_protection_enabled   = false

  tags = merge(local.tags, { componente = "segredos" })

  lifecycle {
    prevent_destroy = true
  }
}
