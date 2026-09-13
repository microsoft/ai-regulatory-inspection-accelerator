terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 2.12"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.13"
    }
  }

  # Fixed backend config - points at the storage account created by
  # infra/bootstrap. Update these values here if you rename
  # anything in the bootstrap stack.
  backend "azurerm" {
    resource_group_name  = "rg-aria-tfstate-infra"
    storage_account_name = "stariatfstate40f8a183"
    container_name       = "tfstate"
    key                  = "infra.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}

  # Authentication is selected through ARM environment variables:
  # GitHub Actions uses OIDC, while local runs use Azure CLI credentials.
}

provider "azapi" {
  # Uses the same ARM environment authentication as azurerm.
}
