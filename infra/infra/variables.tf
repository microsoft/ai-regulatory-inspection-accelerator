variable "resource_group_name" {
  description = "Name of the resource group for the platform resources."
  type        = string
  default     = "rg-aria-infra"
}

variable "location" {
  description = "Azure region for the platform resources."
  type        = string
  default     = "eastus"
}

variable "tags" {
  description = "Common tags applied to all platform resources."
  type        = map(string)
  default = {
    project     = "aria"
    environment = "dev"
    managed_by  = "terraform"
  }
}

# ============================================================================
# Monitoring
# ============================================================================
variable "log_analytics_name" {
  description = "Name of the Log Analytics workspace"
  type        = string
  default     = "log-aria-infra"
}

variable "app_insights_name" {
  description = "Name of the Application Insights instance"
  type        = string
  default     = "appi-aria-infra"
}

# ============================================================================
# Storage
# ============================================================================
variable "storage_account_name" {
  description = "Name of the storage account (globally unique, lowercase, max 24 chars)"
  type        = string
  default     = "stariainfra"
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS on the storage account + APIM APIs (e.g. the chat UI web app URL). Empty disables CORS."
  type        = list(string)
  default     = []
}

# ============================================================================
# Cosmos DB
# ============================================================================
variable "cosmos_account_name" {
  description = "Name of the Cosmos DB account (globally unique)"
  type        = string
  default     = "cosmos-aria-infra"
}

variable "cosmos_database_name" {
  description = "Name of the Cosmos DB database"
  type        = string
  default     = "inspector-db"
}

variable "cosmos_location" {
  description = "Azure region for Cosmos DB. Kept separate to accommodate regional capacity."
  type        = string
  default     = "westus3"
}

# ============================================================================
# Azure AI Search
# ============================================================================
variable "search_service_name" {
  description = "Name of the Azure AI Search service (globally unique)"
  type        = string
  default     = "srch-aria-infra"
}

variable "search_sku" {
  description = "SKU of the Azure AI Search service (must be 'basic' or higher - semantic ranker used by the indexes requires it; 'free' does not support semantic search)"
  type        = string
  default     = "basic"
}

# ============================================================================
# AI Foundry (AI Services / OpenAI / Document Intelligence)
# ============================================================================
variable "ai_services_name" {
  description = "Name of the AI Services (multi-service Cognitive Services) account (globally unique)"
  type        = string
  default     = "aisvc-aria-infra"
}

variable "openai_name" {
  description = "Name of the Azure OpenAI account (globally unique)"
  type        = string
  default     = "oai-aria-infra"
}

variable "azure_openai_deployment" {
  description = "Name of the Azure OpenAI chat model deployment (deploy the model separately - not managed by this stack, matching the reference project)"
  type        = string
  default     = "aria-text-mini"
}

variable "azure_openai_vision_deployment" {
  description = "Name of the low-volume Azure OpenAI vision fallback deployment"
  type        = string
  default     = "aria-vision"
}

variable "azure_openai_embedding_deployment" {
  description = "Name of the Azure OpenAI embedding model deployment (deploy the model separately - not managed by this stack, matching the reference project)"
  type        = string
  default     = "text-embedding-3-small"
}

variable "document_intelligence_name" {
  description = "Name of the Azure AI Document Intelligence account (globally unique)"
  type        = string
  default     = "di-aria-infra"
}

# ============================================================================
# Azure App Configuration
# ============================================================================
variable "app_configuration_name" {
  description = "Name of the App Configuration store (globally unique)"
  type        = string
  default     = "appcs-aria-infra"
}

# ============================================================================
# Function App (Pipeline)
# ============================================================================
variable "flex_consumption_plan_name" {
  description = "Name of the Flex Consumption App Service Plan"
  type        = string
  default     = "plan-aria-pipeline"
}

variable "user_assigned_identity_name" {
  description = "Name of the User Assigned Managed Identity for the Function App"
  type        = string
  default     = "id-aria-pipeline"
}

variable "pipeline_function_app_name" {
  description = "Name of the Pipeline Function App (globally unique)"
  type        = string
  default     = "func-aria-pipeline"
}

variable "python_version" {
  description = "Python version for the Function App and web app runtimes"
  type        = string
  default     = "3.11"
}

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

# ============================================================================
# API Management
# ============================================================================
variable "apim_name" {
  description = "Name of the API Management service (globally unique)"
  type        = string
  default     = "apim-aria-infra"
}

variable "apim_publisher_name" {
  description = "Publisher name for the API Management service"
  type        = string
  default     = "ARIA"
}

variable "apim_publisher_email" {
  description = "Publisher email for the API Management service"
  type        = string
  default     = "admin@example.com"
}

variable "apim_sku_name" {
  description = "SKU of the API Management service. Format: {tier}_{capacity}. Consumption_0 is pay-per-call with no fixed hourly cost."
  type        = string
  default     = "Consumption_0"
}

# ============================================================================
# Chat UI Web App
# ============================================================================
variable "webapp_service_plan_name" {
  description = "Name of the App Service Plan for the chat UI web app"
  type        = string
  default     = "plan-aria-chat-wus3"
}

variable "webapp_sku_name" {
  description = "SKU of the chat UI web app's App Service Plan"
  type        = string
  default     = "F1"
}

variable "webapp_name" {
  description = "Name of the chat UI web app (globally unique)"
  type        = string
  default     = "app-aria-chat"
}

variable "webapp_location" {
  description = "Azure region for the chat UI web app. Kept separate to accommodate App Service quota."
  type        = string
  default     = "westus3"
}
