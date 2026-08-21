output "resource_group_name" {
  description = "Resource group holding the platform resources."
  value       = azurerm_resource_group.main.name
}

output "storage_account_name" {
  description = "Name of the storage account."
  value       = module.storage.storage_account_name
}

output "cosmos_account_name" {
  description = "Name of the Cosmos DB account."
  value       = module.cosmos_db.cosmos_account_name
}

output "search_service_name" {
  description = "Name of the Azure AI Search service."
  value       = module.ai_search.search_service_name
}

output "openai_endpoint" {
  description = "Endpoint URL of the Azure OpenAI account."
  value       = module.ai_foundry.openai_endpoint
}

output "document_intelligence_endpoint" {
  description = "Endpoint URL of the Document Intelligence account."
  value       = module.ai_foundry.document_intelligence_endpoint
}

output "app_configuration_endpoint" {
  description = "Endpoint URL of the App Configuration store."
  value       = module.app_configuration.app_configuration_endpoint
}

output "pipeline_function_app_name" {
  description = "Name of the Pipeline Function App."
  value       = module.function_apps.pipeline_function_app_name
}

output "apim_gateway_url" {
  description = "Gateway URL of the API Management service."
  value       = module.api_management.apim_gateway_url
}

output "webapp_default_hostname" {
  description = "Default hostname of the chat UI web app."
  value       = module.webapp.webapp_default_hostname
}

