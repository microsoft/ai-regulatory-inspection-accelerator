variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "ai_services_name" {
  description = "Name of the AI Services (multi-service Cognitive Services) account (must be globally unique)"
  type        = string
}

variable "openai_name" {
  description = "Name of the Azure OpenAI account (must be globally unique)"
  type        = string
}

variable "document_intelligence_name" {
  description = "Name of the Azure AI Document Intelligence account (must be globally unique)"
  type        = string
}

variable "cosmos_account_id" {
  description = "Resource ID of the Cosmos DB account to grant the AI Services identity access to"
  type        = string
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics Workspace ID for diagnostic settings"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
