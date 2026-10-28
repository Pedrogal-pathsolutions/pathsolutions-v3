# Pattern 9: the worker's identity. az attaches it to VM2 while VM2 is
# deallocated. It is VM2's only identity, so IMDS hands it out without a
# client id, and the agent on VM2 signs in with it too.
resource "azurerm_user_assigned_identity" "vm2" {
  name                = "pathsol-id-vm2-v3"
  location            = local.location
  resource_group_name = data.azurerm_resource_group.v3.name

  tags = merge(local.tags, { componente = "identidade-vm2" })
}
