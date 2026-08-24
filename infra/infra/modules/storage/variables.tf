variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region for resources"
  type        = string
}

variable "storage_account_name" {
  description = "Name of the storage account (globally unique, lowercase, max 24 chars)"
  type        = string
}

variable "user_assigned_identity_id" {
  description = "ID of the User Assigned Managed Identity to attach to the storage account"
  type        = string
  default     = ""
}

variable "cors_allowed_origins" {
  description = "Allowed origins for CORS on the blob service (e.g. the chat UI web app)"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
