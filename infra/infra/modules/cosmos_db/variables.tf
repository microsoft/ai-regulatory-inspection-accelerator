variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "cosmos_account_name" {
  description = "Name of the Cosmos DB account"
  type        = string
}

variable "database_name" {
  description = "Name of the Cosmos DB database"
  type        = string
  default     = "inspector-db"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
