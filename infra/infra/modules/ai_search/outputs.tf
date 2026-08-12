output "search_service_id" {
  description = "ID of the Azure AI Search service"
  value       = azurerm_search_service.main.id
}

output "search_service_name" {
  description = "Name of the Azure AI Search service"
  value       = azurerm_search_service.main.name
}

output "search_endpoint" {
  description = "Endpoint URL of the Azure AI Search service"
  value       = "https://${azurerm_search_service.main.name}.search.windows.net"
}

output "search_primary_key" {
  description = "Primary admin API key of the Azure AI Search service"
  value       = azurerm_search_service.main.primary_key
  sensitive   = true
}
