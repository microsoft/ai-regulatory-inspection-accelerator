variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "log_analytics_name" {
  description = "Name of the Log Analytics workspace"
  type        = string
}

variable "log_analytics_sku" {
  description = "SKU of the Log Analytics workspace"
  type        = string
  default     = "PerGB2018"
}

variable "app_insights_name" {
  description = "Name of the Application Insights instance"
  type        = string
}

variable "application_type" {
  description = "Application type for Application Insights"
  type        = string
  default     = "web"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
