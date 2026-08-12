terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~> 1.13"
    }
  }

  # Fixed backend config - points at the storage account created by
  # infra/bootstrap. Update these values here if you rename
  # anything in the bootstrap stack.
  backend "azurerm" {
    resource_group_name  = "rg-aria-tfstate-infra"
    storage_account_name = "stariatfstateinfra"
    container_name       = "tfstate"
    key                  = "infra.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  features {}

  # Authenticates via GitHub Actions OIDC federated credential (no client
  # secret). See .github/workflows/infra.yml.
  use_oidc = true
}

provider "azapi" {
  # Used for the AI Services (multi-service) account and AI Search index
  # data-plane resources - authenticates via the same OIDC federated
  # credential as azurerm.
  use_oidc = true
}
