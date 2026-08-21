variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "app_configuration_name" {
  description = "Name of the App Configuration store (must be globally unique)"
  type        = string
}

variable "sku" {
  description = "SKU of the App Configuration store"
  type        = string
  default     = "free"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
