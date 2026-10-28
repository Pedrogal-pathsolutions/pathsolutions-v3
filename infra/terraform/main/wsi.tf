locals {
  # One WSI container per tenant (pattern 6). A new tenant gets its container,
  # already under legal hold, in an approved plan before its first upload.
  wsi_tenants = toset(["diagnose", "publico"])
}

# Decision 1: ZRS, Hot on upload. No soft delete until the MVP (CLAUDE.md).
resource "azurerm_storage_account" "wsi" {
  name                            = "pathsolwsiv3"
  resource_group_name             = data.azurerm_resource_group.v3.name
  location                        = local.location
  account_kind                    = "StorageV2"
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  access_tier                     = "Hot"
  min_tls_version                 = "TLS1_2"
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true
  allow_nested_items_to_be_public = false
  # The extension uploads from the labs' own networks with a user delegation
  # SAS, so the endpoint stays reachable; every request needs Entra ID or that SAS.
  public_network_access = "Enabled"

  tags = merge(local.tags, { componente = "wsi" })

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_container" "wsi" {
  for_each           = local.wsi_tenants
  name               = "wsi-${each.key}"
  storage_account_id = azurerm_storage_account.wsi.id

  lifecycle {
    prevent_destroy = true
  }
}

# Derivatives have no legal hold (plan 6.6). Blob paths start with the tenant:
# `tenant/slide/extractor_version/` (pathsol-contrato-h5).
resource "azurerm_storage_container" "h5" {
  name               = "slide-h5"
  storage_account_id = azurerm_storage_account.wsi.id

  lifecycle {
    prevent_destroy = true
  }
}

# Decision 1. Counted from creation, because a write would reset the
# modification time. A new tenant container joins the WSI rule in the plan
# that creates it.
resource "azurerm_storage_management_policy" "wsi" {
  storage_account_id = azurerm_storage_account.wsi.id

  rule {
    name    = "wsi-cold-30d"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = [for c in azurerm_storage_container.wsi : c.name]
    }
    actions {
      base_blob {
        tier_to_cold_after_days_since_creation_greater_than = 30
      }
    }
  }

  rule {
    name    = "h5-cool-90d"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = [azurerm_storage_container.h5.name]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_creation_greater_than = 90
      }
    }
  }

  # Plan 7: only pg_dump files. pgBackRest expires its own files, and the
  # prefix never reaches a WSI container.
  rule {
    name    = "backup-dump-35d"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["${azurerm_storage_container.backup.name}/dump/"]
    }
    actions {
      base_blob {
        delete_after_days_since_creation_greater_than = 35
      }
    }
  }
}

# azurerm has no legal hold resource. The action runs once, when the container
# is created; if someone clears the hold later, Terraform does not notice.
resource "azapi_resource_action" "wsi_legal_hold" {
  for_each    = azurerm_storage_container.wsi
  type        = "Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01"
  resource_id = each.value.id
  action      = "setLegalHold"

  body = {
    tags = ["decisao1"]
    # true would let new blocks be appended to protected blobs.
    allowProtectedAppendWritesAll = false
  }
}

# Stops deleting the account, not its blobs; the legal hold covers the blobs.
resource "azurerm_management_lock" "wsi" {
  name       = "nao-apagar"
  scope      = azurerm_storage_account.wsi.id
  lock_level = "CanNotDelete"
  notes      = "WSIs da v3 (decisao 1)."
}

# Pattern 6: the API, the worker and the operator read and write blobs but never
# delete, move or act as immutability superuser. Assigned when each identity
# gets its access.
resource "azurerm_role_definition" "blob_sem_exclusao" {
  name        = "pathsol-blob-sem-exclusao-v3"
  scope       = data.azurerm_resource_group.v3.id
  description = "Le e grava blobs, sem excluir nem mover (padrao 6)."

  permissions {
    actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/read",
      "Microsoft.Storage/storageAccounts/blobServices/generateUserDelegationKey/action",
    ]
    data_actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
    ]
  }

  assignable_scopes = [data.azurerm_resource_group.v3.id]
}
