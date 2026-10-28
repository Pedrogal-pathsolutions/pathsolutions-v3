# Custom roles hold exactly what each process calls. The VM roles must be
# assignable in the VMs' group; each is assigned on one VM only.
locals {
  vm_read = [
    "Microsoft.Compute/virtualMachines/read",
    "Microsoft.Compute/virtualMachines/instanceView/read",
  ]
}

# Pattern 9: the reconciler on VM1 starts VM2 for a job and is the last of the
# three layers that deallocate it.
resource "azurerm_role_definition" "vm2_energia" {
  name        = "pathsol-vm2-energia-v3"
  scope       = data.azurerm_resource_group.vms.id
  description = "Le, liga e desaloca a VM2 (padrao 9)."

  permissions {
    actions = concat(local.vm_read, [
      "Microsoft.Compute/virtualMachines/start/action",
      "Microsoft.Compute/virtualMachines/deallocate/action",
    ])
  }

  assignable_scopes = [data.azurerm_resource_group.vms.id]
}

# Pattern 9: the worker and the watchdog deallocate VM2 through ARM, never
# from the OS, because a VM stopped from inside keeps billing.
resource "azurerm_role_definition" "vm2_autodesalocar" {
  name        = "pathsol-vm2-autodesalocar-v3"
  scope       = data.azurerm_resource_group.vms.id
  description = "Le e desaloca a propria VM2 (padrao 9)."

  permissions {
    actions = concat(local.vm_read, ["Microsoft.Compute/virtualMachines/deallocate/action"])
  }

  assignable_scopes = [data.azurerm_resource_group.vms.id]
}

# Pattern 27: the morning runbook only starts VM1. It replaces Virtual Machine
# Contributor on the whole group, which can delete VMs; az removes that one
# after the new runbook runs.
resource "azurerm_role_definition" "vm1_ligar" {
  name        = "pathsol-vm1-ligar-v3"
  scope       = data.azurerm_resource_group.vms.id
  description = "Le e liga a VM1 (padrao 27)."

  permissions {
    actions = [
      "Microsoft.Compute/virtualMachines/read",
      "Microsoft.Compute/virtualMachines/start/action",
    ]
  }

  assignable_scopes = [data.azurerm_resource_group.vms.id]
}

# Plan 9.1: get, delete and update messages. A retry extends the invisibility
# and bumps attempt in one Update Message, which needs messages/write; no
# built-in role has exactly these two.
resource "azurerm_role_definition" "fila_worker" {
  name        = "pathsol-fila-worker-v3"
  scope       = data.azurerm_resource_group.v3.id
  description = "Pega, apaga e atualiza mensagens da fila de jobs (secao 9.1)."

  permissions {
    data_actions = [
      "Microsoft.Storage/storageAccounts/queueServices/queues/messages/process/action",
      "Microsoft.Storage/storageAccounts/queueServices/queues/messages/write",
    ]
  }

  assignable_scopes = [data.azurerm_resource_group.v3.id]
}

# Plan 7: pgBackRest expires old backups and WAL with Blob Batch, whose parent
# request needs containers/write. Deleting stays inside the backup container.
resource "azurerm_role_definition" "backup_banco" {
  name        = "pathsol-backup-banco-v3"
  scope       = data.azurerm_resource_group.v3.id
  description = "Le, grava e apaga backups do banco, so no container de backup (secao 7)."

  permissions {
    actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/read",
      "Microsoft.Storage/storageAccounts/blobServices/containers/write",
    ]
    data_actions = [
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action",
      "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete",
    ]
  }

  assignable_scopes = [data.azurerm_resource_group.v3.id]
}

data "azurerm_role_definition" "builtin" {
  for_each = toset([
    "Storage Blob Data Reader",
    "Storage Queue Data Message Sender",
    "Storage Queue Data Reader",
  ])
  name = each.key
}

locals {
  vm1_principal_id     = data.azurerm_virtual_machine.vm1.identity[0].principal_id
  runbook_principal_id = data.azurerm_automation_account.runbook.identity[0].principal_id

  role_assignments = merge(
    {
      vm1-vm2-energia = {
        scope     = data.azurerm_virtual_machine.vm2.id
        role_id   = azurerm_role_definition.vm2_energia.role_definition_resource_id
        principal = local.vm1_principal_id
      }
      # The reconciler peeks the queue and reads its approximate count.
      vm1-fila-leitura = {
        scope     = azurerm_storage_queue.jobs.id
        role_id   = data.azurerm_role_definition.builtin["Storage Queue Data Reader"].id
        principal = local.vm1_principal_id
      }
      # Plan 18: the status unit overwrites status.json.
      vm1-status = {
        scope     = "${azurerm_storage_account.status.id}/blobServices/default/containers/$web"
        role_id   = azurerm_role_definition.blob_sem_exclusao.role_definition_resource_id
        principal = local.vm1_principal_id
      }
      # pgBackRest 2.60 takes IMDS's default identity, VM1's system one.
      vm1-backup = {
        scope     = azurerm_storage_container.backup.id
        role_id   = azurerm_role_definition.backup_banco.role_definition_resource_id
        principal = local.vm1_principal_id
      }
      vm2-autodesalocar = {
        scope     = data.azurerm_virtual_machine.vm2.id
        role_id   = azurerm_role_definition.vm2_autodesalocar.role_definition_resource_id
        principal = azurerm_user_assigned_identity.vm2.principal_id
      }
      vm2-fila = {
        scope     = azurerm_storage_queue.jobs.id
        role_id   = azurerm_role_definition.fila_worker.role_definition_resource_id
        principal = azurerm_user_assigned_identity.vm2.principal_id
      }
      # Plan 9.1: after the third technical failure, the worker moves the message.
      vm2-dead-letter = {
        scope     = azurerm_storage_queue.dead_letter.id
        role_id   = data.azurerm_role_definition.builtin["Storage Queue Data Message Sender"].id
        principal = azurerm_user_assigned_identity.vm2.principal_id
      }
      # The worker writes .h5 files and may rewrite one on a retry of the same job.
      vm2-h5 = {
        scope     = azurerm_storage_container.h5.id
        role_id   = azurerm_role_definition.blob_sem_exclusao.role_definition_resource_id
        principal = azurerm_user_assigned_identity.vm2.principal_id
      }
      runbook-vm1 = {
        scope     = data.azurerm_virtual_machine.vm1.id
        role_id   = azurerm_role_definition.vm1_ligar.role_definition_resource_id
        principal = local.runbook_principal_id
      }
    },
    # The worker only reads WSIs.
    { for k, c in azurerm_storage_container.wsi : "vm2-wsi-${k}" => {
      scope     = c.id
      role_id   = data.azurerm_role_definition.builtin["Storage Blob Data Reader"].id
      principal = azurerm_user_assigned_identity.vm2.principal_id
    } },
  )
}

resource "azurerm_role_assignment" "v3" {
  for_each           = local.role_assignments
  scope              = each.value.scope
  role_definition_id = each.value.role_id
  principal_id       = each.value.principal
  # Skips the Entra ID lookup that fails while a new identity replicates.
  principal_type = "ServicePrincipal"
}
