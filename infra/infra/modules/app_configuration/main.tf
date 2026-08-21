# New module - the reference project only ever referenced an *existing* App
# Configuration store via a data source (never created one in Terraform).

resource "azurerm_app_configuration" "main" {
  name                = var.app_configuration_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku

  public_network_access = "Enabled"
  local_auth_enabled    = true

  tags = var.tags
}
