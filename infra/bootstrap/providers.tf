terraform {
  required_version = ">= 1.5.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }

  # No remote backend here on purpose: this stack creates the storage account
  # that every other stack will use as its backend, so its own state stays
  # local to the pipeline run (or can be migrated to a manually-secured
  # location later if you want to persist it).
}

provider "azurerm" {
  features {}

  # Authenticates via GitHub Actions OIDC federated credential (no client
  # secret). See .github/workflows/infra.yml.
  use_oidc = true
}
