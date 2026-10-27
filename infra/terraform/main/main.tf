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

data "azurerm_subscription" "current" {}

# Created by ../bootstrap.
data "azurerm_resource_group" "v3" {
  name = "rg-pathsol-v3"
}
