# Bootstrap stack: creates the storage account that holds Terraform state
# for every other stack in this repo (infra, and later app/service stacks).
#
# Networking is left open (public network access enabled) on purpose - this
# is a general-purpose accelerator, not a locked-down reference deployment.
# Add network_rules / private endpoints yourself if your environment requires
# them.

resource "azurerm_resource_group" "tfstate" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}

resource "azurerm_storage_account" "tfstate" {
  name                = var.storage_account_name
  resource_group_name = azurerm_resource_group.tfstate.name
  location            = azurerm_resource_group.tfstate.location

  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  # Kept open for simplicity - see note above.
  public_network_access_enabled = true

  # Access via Azure AD (OIDC identity), not storage account keys.
  shared_access_key_enabled = false

  blob_properties {
    versioning_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "tfstate" {
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.tfstate.name
  container_access_type = "private"
}
