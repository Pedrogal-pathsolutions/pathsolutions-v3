terraform {
  required_version = "~> 1.16.7"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.10.0"
    }
  }

  # The first apply runs with a local backend (backend_override.tf, not committed);
  # right after it, the state is migrated here with `terraform init -migrate-state`.
  backend "azurerm" {
    resource_group_name  = "rg-pathsol-v3"
    storage_account_name = "pathsoltfstatev3"
    container_name       = "tfstate"
    key                  = "bootstrap.tfstate"
    use_azuread_auth     = true
    use_cli              = true
    use_msi              = false
  }
}
