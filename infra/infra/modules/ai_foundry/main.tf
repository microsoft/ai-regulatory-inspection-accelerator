# Ported from project-ailanding zone/terraform/modules/microsoft_foundry.
# Dropped: private DNS zones, private endpoints, the 90s time_sleep wait for
# identity/DNS propagation (not needed once nothing is gated behind a VNet),
# Key Vault Crypto/Secrets User role grants (no Key Vault in this stack).
# Changed: public_network_access / networkAcls flipped from Disabled/Deny to
# enabled, since this stack has no private endpoints.
# Kept: SKUs (S0), resource kinds, diagnostic settings, Cosmos DB RBAC grant.

terraform {
  required_providers {
    azapi = {
      source = "azure/azapi"
    }
  }
}

data "azurerm_client_config" "current" {}

resource "azapi_resource" "ai_services" {
  type                      = "Microsoft.CognitiveServices/accounts@2024-10-01"
  name                      = var.ai_services_name
  location                  = var.location
  parent_id                 = "/subscriptions/${data.azurerm_client_config.current.subscription_id}/resourceGroups/${var.resource_group_name}"
  schema_validation_enabled = false

  body = jsonencode({
    kind = "AIServices"
    properties = {
      customSubDomainName = var.ai_services_name
      publicNetworkAccess = "Enabled"
      networkAcls = {
        defaultAction = "Allow"
      }
    }
    sku = {
      name = "S0"
    }
    identity = {
      type = "SystemAssigned"
    }
  })

  response_export_values = ["identity", "properties"]

  tags = var.tags
}

resource "azurerm_cognitive_account" "openai" {
  name                          = var.openai_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "OpenAI"
  sku_name                      = "S0"
  custom_subdomain_name         = var.openai_name
  public_network_access_enabled = true
  local_auth_enabled            = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "openai" {
  name                       = "diag-openai"
  target_resource_id         = azurerm_cognitive_account.openai.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_cognitive_account" "document_intelligence" {
  name                          = var.document_intelligence_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  kind                          = "FormRecognizer"
  sku_name                      = "S0"
  custom_subdomain_name         = var.document_intelligence_name
  public_network_access_enabled = true
  local_auth_enabled            = true

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "document_intelligence" {
  name                       = "diag-docint"
  target_resource_id         = azurerm_cognitive_account.document_intelligence.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_metric {
    category = "AllMetrics"
  }
}

# Grant AI Services (multi-service account) access to Cosmos DB.
# Role ID 00000000-0000-0000-0000-000000000002 = "Cosmos DB Built-in Data Contributor"
resource "azurerm_cosmosdb_sql_role_assignment" "ai_services_cosmos_contributor" {
  resource_group_name = var.resource_group_name
  account_name        = element(split("/", var.cosmos_account_id), length(split("/", var.cosmos_account_id)) - 1)
  role_definition_id  = "${var.cosmos_account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = jsondecode(azapi_resource.ai_services.output).identity.principalId
  scope               = var.cosmos_account_id
}

resource "azurerm_monitor_diagnostic_setting" "ai_services" {
  name                       = "diag-aiservices"
  target_resource_id         = azapi_resource.ai_services.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "Audit"
  }

  enabled_log {
    category = "RequestResponse"
  }

  enabled_log {
    category = "Trace"
  }
}
