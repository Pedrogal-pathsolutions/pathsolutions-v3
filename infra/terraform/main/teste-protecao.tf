# Plan 6.3, slice 8: the WSI protection tests run in a throwaway account, not
# in pathsolwsiv3, because a test blob under legal hold could never leave.
# Same settings as the WSI account where the tests depend on them; LRS,
# because replication changes none of them. No prevent_destroy and no lock:
# Pedro deletes it after the tests, and this file goes with it.
resource "azurerm_storage_account" "teste" {
  name                            = "pathsoltestev3"
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
  public_network_access           = "Enabled"

  tags = merge(local.tags, { componente = "teste" })
}

resource "azurerm_storage_container" "teste" {
  name               = "wsi-teste"
  storage_account_id = azurerm_storage_account.teste.id
}

resource "azapi_resource_action" "teste_legal_hold" {
  type        = "Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01"
  resource_id = azurerm_storage_container.teste.id
  action      = "setLegalHold"

  body = {
    tags                          = ["teste"]
    allowProtectedAppendWritesAll = false
  }
}

# Decision 1 assumes the lifecycle moves a WSI under legal hold to Cold; here
# the daily run does it as soon as it sees the blob.
resource "azurerm_storage_management_policy" "teste" {
  storage_account_id = azurerm_storage_account.teste.id

  rule {
    name    = "teste-cold"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = [azurerm_storage_container.teste.name]
    }
    actions {
      base_blob {
        tier_to_cold_after_days_since_creation_greater_than = 0
      }
    }
  }
}

data "azurerm_client_config" "current" {}

locals {
  # The identities of pattern 6 with the roles they get on WSI containers:
  # VM1 (API and operator) writes without deleting, VM2 only reads. A user
  # delegation key is requested from the account, so VM1 gets the delegator
  # role there. Pedro, as data owner, runs the steps that delete.
  teste_role_assignments = {
    vm1-sem-exclusao = {
      scope     = azurerm_storage_container.teste.id
      role_id   = azurerm_role_definition.blob_sem_exclusao.role_definition_resource_id
      principal = local.vm1_principal_id
      type      = "ServicePrincipal"
    }
    vm1-delegacao = {
      scope     = azurerm_storage_account.teste.id
      role_id   = data.azurerm_role_definition.builtin["Storage Blob Delegator"].id
      principal = local.vm1_principal_id
      type      = "ServicePrincipal"
    }
    vm2-leitura = {
      scope     = azurerm_storage_container.teste.id
      role_id   = data.azurerm_role_definition.builtin["Storage Blob Data Reader"].id
      principal = azurerm_user_assigned_identity.vm2.principal_id
      type      = "ServicePrincipal"
    }
    pedro-dono = {
      scope     = azurerm_storage_container.teste.id
      role_id   = data.azurerm_role_definition.builtin["Storage Blob Data Owner"].id
      principal = data.azurerm_client_config.current.object_id
      type      = "User"
    }
  }
}

resource "azurerm_role_assignment" "teste" {
  for_each           = local.teste_role_assignments
  scope              = each.value.scope
  role_definition_id = each.value.role_id
  principal_id       = each.value.principal
  principal_type     = each.value.type
}
