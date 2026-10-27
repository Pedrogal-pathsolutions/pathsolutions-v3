# Decision 4: Terraform authenticates only with Pedro's az CLI login,
# never with the VM1 managed identity (that one belongs to the API).
provider "azurerm" {
  subscription_id     = "bd87a1ca-e4f5-460b-9f12-c89e114293f1"
  use_cli             = true
  use_msi             = false
  storage_use_azuread = true
  features {}
}

locals {
  location = "brazilsouth"
  tags = {
    projeto = "pathsolutions"
    versao  = "v3"
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "v3" {
  name     = "rg-pathsol-v3"
  location = local.location
  tags     = merge(local.tags, { componente = "base" })

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_account" "tfstate" {
  name                            = "pathsoltfstatev3"
  resource_group_name             = azurerm_resource_group.v3.name
  location                        = local.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  access_tier                     = "Hot"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false

  # Versioning lets a bad state write be rolled back. It is not soft delete.
  blob_properties {
    versioning_enabled = true
  }

  tags = merge(local.tags, { componente = "estado" })

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_container" "tfstate" {
  name               = "tfstate"
  storage_account_id = azurerm_storage_account.tfstate.id
}

resource "azurerm_management_lock" "tfstate" {
  name       = "nao-apagar"
  scope      = azurerm_storage_account.tfstate.id
  lock_level = "CanNotDelete"
  notes      = "Estado do Terraform da v3."
}

# Owner has no data-plane access, and the backend reads, writes and leases the
# state blob with Entra ID. Scoped to the state container only.
resource "azurerm_role_assignment" "tfstate_operator" {
  scope                = azurerm_storage_container.tfstate.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
  principal_type       = "User"
}
