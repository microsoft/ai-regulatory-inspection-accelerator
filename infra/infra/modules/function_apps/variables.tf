variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "flex_consumption_plan_name" {
  description = "Name of the Flex Consumption App Service Plan"
  type        = string
}

variable "user_assigned_identity_name" {
  description = "Name of the User Assigned Managed Identity for the Function App"
  type        = string
}

variable "pipeline_function_app_name" {
  description = "Name of the Pipeline Function App"
  type        = string
}

variable "pipeline_instance_memory_mb" {
  description = "Instance memory in MB for the Flex Consumption Function App"
  type        = number
  default     = 2048
}

variable "pipeline_max_instance_count" {
  description = "Maximum instance count for the Flex Consumption Function App"
  type        = number
  default     = 100
}

variable "python_version" {
  description = "Python version for the Function App runtime"
  type        = string
  default     = "3.11"
}

# ── Storage ───────────────────────────────────────────────────────────────
variable "storage_account_id" {
  description = "Resource ID of the storage account (for RBAC)"
  type        = string
}

variable "storage_account_access_key" {
  description = "Primary access key of the storage account"
  type        = string
  sensitive   = true
}

variable "storage_account_connection_string" {
  description = "Primary connection string of the storage account"
  type        = string
  sensitive   = true
}

variable "storage_account_blob_endpoint" {
  description = "Primary blob endpoint of the storage account"
  type        = string
}

# ── Application Insights ─────────────────────────────────────────────────
variable "app_insights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
}

variable "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  type        = string
  sensitive   = true
}

# ── Cosmos DB ─────────────────────────────────────────────────────────────
variable "cosmos_db_account_id" {
  description = "Resource ID of the Cosmos DB account (for the pipeline identity's RBAC grant)"
  type        = string
}

variable "cosmos_db_endpoint" {
  description = "Cosmos DB account endpoint URL"
  type        = string
}

variable "cosmos_db_database" {
  description = "Cosmos DB database name"
  type        = string
}

# ── Azure AI Document Intelligence ───────────────────────────────────────
variable "document_intelligence_id" {
  description = "Resource ID of the Document Intelligence account (for RBAC)"
  type        = string
}

variable "document_intelligence_endpoint" {
  description = "Endpoint URL of the Document Intelligence account"
  type        = string
}

# ── Azure OpenAI ──────────────────────────────────────────────────────────
variable "azure_openai_id" {
  description = "Resource ID of the Azure OpenAI account (for RBAC)"
  type        = string
}

variable "azure_openai_endpoint" {
  description = "Endpoint URL of the Azure OpenAI account"
  type        = string
}

variable "azure_openai_key" {
  description = "API key of the Azure OpenAI account"
  type        = string
  sensitive   = true
}

variable "azure_openai_key_vault_secret_uri" {
  description = "Versionless Key Vault secret URI for the Azure OpenAI API key"
  type        = string
  default     = ""
}

variable "azure_openai_deployment" {
  description = "Name of the Azure OpenAI chat model deployment"
  type        = string
  default     = "aria-text-mini"
}

variable "azure_openai_vision_deployment" {
  description = "Name of the low-volume Azure OpenAI vision fallback deployment"
  type        = string
  default     = "aria-vision"
}

variable "azure_openai_embedding_deployment" {
  description = "Name of the Azure OpenAI embedding model deployment"
  type        = string
  default     = "text-embedding-3-small"
}

# ── Azure AI Search ───────────────────────────────────────────────────────
variable "azure_search_id" {
  description = "Resource ID of the Azure AI Search service (for RBAC)"
  type        = string
}

variable "azure_search_endpoint" {
  description = "Endpoint URL of the Azure AI Search service"
  type        = string
}

variable "azure_search_key" {
  description = "Admin API key of the Azure AI Search service"
  type        = string
  sensitive   = true
}

# ── Azure App Configuration ──────────────────────────────────────────────
variable "app_configuration_id" {
  description = "Resource ID of the App Configuration store (for RBAC)"
  type        = string
}

variable "app_configuration_endpoint" {
  description = "Endpoint URL of the App Configuration store"
  type        = string
}

# ── Delivery / callback ──────────────────────────────────────────────────
variable "delivery_callback_url" {
  description = "Callback URL for delivering verdicts (leave empty to skip)"
  type        = string
  default     = ""
}

variable "delivery_skip_callback" {
  description = "Set to \"true\" to skip the delivery callback (e.g. while the downstream integration is unavailable)"
  type        = string
  default     = "true"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
