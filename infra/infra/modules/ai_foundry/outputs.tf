output "ai_services_id" {
  description = "ID of the AI Services (multi-service) resource"
  value       = azapi_resource.ai_services.id
}

output "ai_services_endpoint" {
  description = "Endpoint URL for AI Services"
  value       = azapi_resource.ai_services.output.properties.endpoint
}

output "ai_services_principal_id" {
  description = "Principal ID of the AI Services managed identity"
  value       = azapi_resource.ai_services.output.identity.principalId
}

output "openai_id" {
  description = "ID of the Azure OpenAI account"
  value       = azurerm_cognitive_account.openai.id
}

output "openai_endpoint" {
  description = "Endpoint URL of the Azure OpenAI account"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_primary_key" {
  description = "Primary access key of the Azure OpenAI account"
  value       = azurerm_cognitive_account.openai.primary_access_key
  sensitive   = true
}

output "document_intelligence_id" {
  description = "ID of the Azure AI Document Intelligence account"
  value       = azurerm_cognitive_account.document_intelligence.id
}

output "document_intelligence_endpoint" {
  description = "Endpoint URL of the Azure AI Document Intelligence account"
  value       = azurerm_cognitive_account.document_intelligence.endpoint
}
