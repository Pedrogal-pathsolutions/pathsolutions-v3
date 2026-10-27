# Pattern 26: status.json, read by the extension when the API does not answer.
# The static website endpoint stays anonymous even with anonymous blob access
# off (learn.microsoft.com, static website hosting). No diagnostic logs.
resource "azurerm_storage_account" "status" {
  name                            = "pathsolstatusv3"
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

  tags = merge(local.tags, { componente = "status" })

  # The extension manifest pins this host from its first version.
  lifecycle {
    prevent_destroy = true
  }
}

# A data plane call. With shared key off it is authorized by
# blobServices/write on the account, which Pedro's login has.
resource "azurerm_storage_account_static_website" "status" {
  storage_account_id = azurerm_storage_account.status.id
  index_document     = "status.json"
}
