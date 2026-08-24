output "apim_id" {
  description = "ID of the API Management service"
  value       = azurerm_api_management.apim.id
}

output "apim_name" {
  description = "Name of the API Management service"
  value       = azurerm_api_management.apim.name
}

output "apim_gateway_url" {
  description = "Gateway URL of the API Management service"
  value       = azurerm_api_management.apim.gateway_url
}

output "webapp_apim_subscription_key" {
  description = "Primary subscription key for the Inspector WebApp"
  value       = azurerm_api_management_subscription.webapp.primary_key
  sensitive   = true
}
