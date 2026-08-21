# Bootstrap stack: creates the storage account that holds Terraform state
# for every other stack in this repo (infra, and later app/service stacks).
#
# Public network access is disabled to comply with the subscription policy.

resource "azurerm_resource_group" "tfstate" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}

resource "azapi_resource" "tfstate" {
  type      = "Microsoft.Storage/storageAccounts@2023-05-01"
  name      = var.storage_account_name
  parent_id = azurerm_resource_group.tfstate.id
  location  = azurerm_resource_group.tfstate.location
  tags      = var.tags

  body = jsonencode({
    kind = "StorageV2"
    sku = {
      name = "Standard_LRS"
    }
    properties = {
      allowBlobPublicAccess    = false
      allowSharedKeyAccess     = false
      minimumTlsVersion        = "TLS1_2"
      publicNetworkAccess      = "Disabled"
      supportsHttpsTrafficOnly = true
    }
  })
}

resource "azapi_resource" "blob_service" {
  type      = "Microsoft.Storage/storageAccounts/blobServices@2023-05-01"
  name      = "default"
  parent_id = azapi_resource.tfstate.id

  body = jsonencode({
    properties = {
      isVersioningEnabled = true
      deleteRetentionPolicy = {
        enabled = true
        days    = 7
      }
      containerDeleteRetentionPolicy = {
        enabled = true
        days    = 7
      }
    }
  })
}

resource "azapi_resource" "tfstate_container" {
  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
  name      = var.container_name
  parent_id = azapi_resource.blob_service.id

  body = jsonencode({
    properties = {
      publicAccess = "None"
    }
  })
}
