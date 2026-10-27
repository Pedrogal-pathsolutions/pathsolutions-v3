terraform {
  required_version = "~> 1.16.7"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.10.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-pathsol-v3"
    storage_account_name = "pathsoltfstatev3"
    container_name       = "tfstate"
    key                  = "main.tfstate"
    use_azuread_auth     = true
    use_cli              = true
    use_msi              = false
  }
}
