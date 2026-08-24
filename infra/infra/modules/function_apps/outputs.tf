output "pipeline_function_app_id" {
  description = "ID of the Pipeline Function App"
  value       = azurerm_function_app_flex_consumption.pipeline.id
}

output "pipeline_function_app_name" {
  description = "Name of the Pipeline Function App"
  value       = azurerm_function_app_flex_consumption.pipeline.name
}

output "pipeline_function_app_default_hostname" {
  description = "Default hostname of the Pipeline Function App"
  value       = azurerm_function_app_flex_consumption.pipeline.default_hostname
}

output "pipeline_function_app_default_key" {
  description = "Default host key of the Pipeline Function App"
  value       = data.azurerm_function_app_host_keys.pipeline.default_function_key
  sensitive   = true
}

output "user_assigned_identity_id" {
  description = "ID of the User Assigned Managed Identity"
  value       = azurerm_user_assigned_identity.function_apps.id
}

output "user_assigned_identity_principal_id" {
  description = "Principal ID of the User Assigned Managed Identity"
  value       = azurerm_user_assigned_identity.function_apps.principal_id
}

output "user_assigned_identity_client_id" {
  description = "Client ID of the User Assigned Managed Identity"
  value       = azurerm_user_assigned_identity.function_apps.client_id
}
