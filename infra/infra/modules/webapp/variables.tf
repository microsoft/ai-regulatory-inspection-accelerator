variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "service_plan_name" {
  description = "Name of the App Service Plan for the chat UI web app"
  type        = string
}

variable "sku_name" {
  description = "SKU of the App Service Plan"
  type        = string
  default     = "B1"
}

variable "webapp_name" {
  description = "Name of the chat UI web app"
  type        = string
}

variable "python_version" {
  description = "Python version for the web app runtime"
  type        = string
  default     = "3.11"
}

variable "app_insights_instrumentation_key" {
  description = "Application Insights instrumentation key"
  type        = string
  sensitive   = true
}

variable "app_insights_connection_string" {
  description = "Application Insights connection string"
  type        = string
  sensitive   = true
}

variable "apim_gateway_url" {
  description = "Gateway URL of the API Management service"
  type        = string
}

variable "apim_subscription_key" {
  description = "APIM subscription key used by the web app to call the gateway"
  type        = string
  sensitive   = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
