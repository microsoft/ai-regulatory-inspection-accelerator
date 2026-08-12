# New module. Neither reference project creates this in Terraform - it was
# only ever referenced as an existing resource (data "azurerm_linux_web_app").
# Minimal Linux Web App for the chat UI; calls the APIM gateway directly
# (confirmed the APIM module never wires the webapp as a backend - the chat
# API already routes to the Function App).

resource "azurerm_service_plan" "webapp" {
  name                = var.service_plan_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name

  tags = var.tags
}

resource "azurerm_linux_web_app" "chat" {
  name                = var.webapp_name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.webapp.id

  https_only = true

  site_config {
    application_stack {
      python_version = var.python_version
    }
  }

  app_settings = {
    "APPINSIGHTS_INSTRUMENTATIONKEY"        = var.app_insights_instrumentation_key
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = var.app_insights_connection_string
    "APIM_GATEWAY_URL"                      = var.apim_gateway_url
    "APIM_SUBSCRIPTION_KEY"                 = var.apim_subscription_key
  }

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}
