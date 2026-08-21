variable "apim_name" {
  description = "Name of the API Management service"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for the API Management service"
  type        = string
}

variable "publisher_name" {
  description = "Publisher name for the API Management service"
  type        = string
}

variable "publisher_email" {
  description = "Publisher email for the API Management service"
  type        = string
}

variable "sku_name" {
  description = "SKU of the API Management service. Format: {tier}_{capacity}."
  type        = string
  default     = "Developer_1"
}

variable "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID for diagnostic settings"
  type        = string
  default     = null
}

variable "pipeline_function_app_hostname" {
  description = "Default hostname of the Pipeline Function App"
  type        = string
}

variable "pipeline_function_app_key" {
  description = "Host key of the Pipeline Function App"
  type        = string
  sensitive   = true
}

variable "cors_allowed_origins" {
  description = "List of allowed origins for CORS on the APIM APIs. Empty list disables CORS."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
