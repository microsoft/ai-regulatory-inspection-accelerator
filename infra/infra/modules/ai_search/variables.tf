variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "search_service_name" {
  description = "Name of the Azure AI Search service"
  type        = string
}

variable "sku" {
  description = "SKU of the Azure AI Search service (must be 'basic' or higher for semantic ranker)"
  type        = string
  default     = "basic"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
