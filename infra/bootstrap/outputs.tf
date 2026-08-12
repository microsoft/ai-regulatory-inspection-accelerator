output "resource_group_name" {
  description = "Resource group holding the tfstate storage account."
  value       = azurerm_resource_group.tfstate.name
}

output "storage_account_name" {
  description = "Name of the storage account used as the Terraform backend for other stacks."
  value       = azurerm_storage_account.tfstate.name
}

output "container_name" {
  description = "Blob container that stores .tfstate files."
  value       = azurerm_storage_container.tfstate.name
}
