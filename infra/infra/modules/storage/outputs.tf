output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "primary_blob_endpoint" {
  description = "Primary blob endpoint"
  value       = azurerm_storage_account.main.primary_blob_endpoint
}

output "primary_web_endpoint" {
  description = "Static website endpoint for the hackathon demo"
  value       = azurerm_storage_account.main.primary_web_endpoint
}

output "primary_access_key" {
  description = "Primary access key for the storage account"
  value       = azurerm_storage_account.main.primary_access_key
  sensitive   = true
}

output "primary_connection_string" {
  description = "Primary connection string for the storage account"
  value       = azurerm_storage_account.main.primary_connection_string
  sensitive   = true
}

output "raw_uploads_container_name" {
  description = "Name of the raw uploads blob container"
  value       = azapi_resource.raw_uploads_container.name
}

output "deployments_container_name" {
  description = "Name of the Flex Consumption deployments blob container"
  value       = azapi_resource.deployments_container.name
}
