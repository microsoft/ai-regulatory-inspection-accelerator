# Ported from project-example/terraform/modules/storage.
# Dropped: private endpoint (subnet_id, private_dns_zone_ids), CAF resource
# lock, per-environment GRS/retention branching (kept simple - LRS, 7 days).
# Kept: versioning, soft-delete, change feed, lifecycle management policy,
# CORS support, raw-uploads container.
# Added: "deployments" container - required by the Flex Consumption Function
# App (storage_container_endpoint) but never actually created by Terraform in
# the reference project (assumed to pre-exist out-of-band).

terraform {
  required_providers {
    azapi = {
      source = "azure/azapi"
    }
  }
}

resource "azurerm_storage_account" "main" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  public_network_access_enabled     = true
  allow_nested_items_to_be_public   = false
  min_tls_version                   = "TLS1_2"
  https_traffic_only_enabled        = true
  infrastructure_encryption_enabled = true

  network_rules {
    default_action = "Allow"
    bypass         = ["AzureServices"]
  }

  blob_properties {
    versioning_enabled       = true
    change_feed_enabled      = true
    last_access_time_enabled = true

    delete_retention_policy {
      days = 7
    }

    container_delete_retention_policy {
      days = 7
    }

    dynamic "cors_rule" {
      for_each = length(var.cors_allowed_origins) > 0 ? [1] : []
      content {
        allowed_origins    = var.cors_allowed_origins
        allowed_methods    = ["GET", "HEAD", "PUT", "OPTIONS"]
        allowed_headers    = ["*"]
        exposed_headers    = ["*"]
        max_age_in_seconds = 3600
      }
    }
  }

  # Only attach a UserAssigned identity when one is actually supplied - an
  # empty identity_ids list with type = "UserAssigned" is rejected by the
  # API at apply time.
  dynamic "identity" {
    for_each = var.user_assigned_identity_id != "" ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [var.user_assigned_identity_id]
    }
  }

  tags = var.tags
}

resource "azurerm_storage_management_policy" "lifecycle" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "archiveOldUploads"
    enabled = true
    filters {
      prefix_match = ["cases/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than    = 30
        tier_to_archive_after_days_since_modification_greater_than = 90
        # No delete - original documents retained indefinitely for audit purposes.
      }
    }
  }
}

# Evidence / case document uploads.
resource "azapi_resource" "raw_uploads_container" {
  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
  name      = "raw-uploads"
  parent_id = "${azurerm_storage_account.main.id}/blobServices/default"

  body = {
    properties = {
      publicAccess = "None"
    }
  }
}

# Flex Consumption deployment package container (required by
# azurerm_function_app_flex_consumption.storage_container_endpoint).
resource "azapi_resource" "deployments_container" {
  type      = "Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01"
  name      = "deployments"
  parent_id = "${azurerm_storage_account.main.id}/blobServices/default"

  body = {
    properties = {
      publicAccess = "None"
    }
  }
}
