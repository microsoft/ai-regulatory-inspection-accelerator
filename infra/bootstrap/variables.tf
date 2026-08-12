variable "resource_group_name" {
  description = "Name of the resource group that holds the Terraform state storage account."
  type        = string
  default     = "rg-aria-tfstate-infra"
}

variable "location" {
  description = "Azure region for the Terraform state resources."
  type        = string
  default     = "eastus"
}

variable "storage_account_name" {
  description = "Globally-unique storage account name (lowercase letters/numbers only, max 24 chars). Rename this if it's already taken - storage account names are unique across all of Azure, not just your subscription."
  type        = string
  default     = "stariatfstateinfra"
}

variable "container_name" {
  description = "Blob container that stores the .tfstate files."
  type        = string
  default     = "tfstate"
}

variable "tags" {
  description = "Common tags applied to all bootstrap resources."
  type        = map(string)
  default = {
    project     = "aria"
    environment = "shared"
    managed_by  = "terraform"
    purpose     = "tfstate"
  }
}
