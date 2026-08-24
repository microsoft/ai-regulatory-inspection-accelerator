# Ported from project-ailanding zone/terraform/modules/monitoring (Log Analytics)
# and project-example/terraform/modules/monitoring (Application Insights).
# Merged into a single module since this stack is self-contained (no shared/
# external Log Analytics workspace from a separate subscription).

resource "azurerm_log_analytics_workspace" "main" {
  name                = var.log_analytics_name
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = var.log_analytics_sku
  retention_in_days   = 30

  tags = var.tags
}

resource "azurerm_application_insights" "main" {
  name                = var.app_insights_name
  location            = var.location
  resource_group_name = var.resource_group_name
  application_type    = var.application_type
  workspace_id        = azurerm_log_analytics_workspace.main.id

  tags = var.tags
}
