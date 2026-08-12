# Ported from project-example/terraform/modules/api_management.
# Dropped: VNet integration (virtual_network_type = "Internal" -> "None"),
# apim_subnet_id, the private DNS zone + A records for APIM Internal mode
# (root main.tf in the reference — not needed once APIM is public).
# Dropped: webapp_hostname / webapp_function_key variables — confirmed
# unused in the reference module body (chat routes go to the Function App,
# not the webapp; the webapp only *calls* APIM, it isn't a backend).
# Kept: APIs, operations, policies, product, subscription — unchanged.

locals {
  _cors_origins_xml = join("\n", [for o in var.cors_allowed_origins : "        <origin>${o}</origin>"])
  _cors_xml = length(var.cors_allowed_origins) > 0 ? join("\n", [
    "    <cors allow-credentials=\"true\">",
    "      <allowed-origins>",
    local._cors_origins_xml,
    "      </allowed-origins>",
    "      <allowed-methods>",
    "        <method>GET</method>",
    "        <method>POST</method>",
    "        <method>OPTIONS</method>",
    "      </allowed-methods>",
    "      <allowed-headers>",
    "        <header>*</header>",
    "      </allowed-headers>",
    "    </cors>",
  ]) : ""

  _chat_policy_xml = join("\n", [
    "<policies>",
    "  <inbound>",
    "    <base />",
    local._cors_xml,
    "    <set-backend-service backend-id=\"${azurerm_api_management_backend.inspector_pipeline_chat.name}\" />",
    "  </inbound>",
    "  <backend><base /></backend>",
    "  <outbound><base /></outbound>",
    "  <on-error><base /></on-error>",
    "</policies>",
  ])
}

resource "azurerm_api_management" "apim" {
  name                 = var.apim_name
  location             = var.location
  resource_group_name  = var.resource_group_name
  publisher_name       = var.publisher_name
  publisher_email      = var.publisher_email
  sku_name             = var.sku_name
  virtual_network_type = "None"

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "apim" {
  count                      = var.log_analytics_workspace_id != null ? 1 : 0
  name                       = "diag-${var.apim_name}"
  target_resource_id         = azurerm_api_management.apim.id
  log_analytics_workspace_id = var.log_analytics_workspace_id

  enabled_log {
    category = "GatewayLogs"
  }

  enabled_log {
    category = "WebSocketConnectionLogs"
  }
}

# ============================================================================
# Named Value — Function App Key (stored securely in APIM)
# ============================================================================
resource "azurerm_api_management_named_value" "function_key" {
  name                = "inspector-pipeline-function-key"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  display_name        = "inspector-pipeline-function-key"
  secret              = true
  value               = var.pipeline_function_app_key
}

# ============================================================================
# Backend — /inspections routes -> Function App
# ============================================================================
resource "azurerm_api_management_backend" "inspector_pipeline" {
  name                = "inspector-pipeline-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  protocol            = "http"
  url                 = "https://${var.pipeline_function_app_hostname}/api/inspections"

  credentials {
    header = {
      "x-functions-key" = "{{inspector-pipeline-function-key}}"
    }
  }

  depends_on = [azurerm_api_management_named_value.function_key]
}

# ============================================================================
# API — /inspections
# ============================================================================
resource "azurerm_api_management_api" "inspector" {
  name                = "inspector-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision            = "1"
  display_name        = "ARIA Inspection Agent API"
  path                = "inspections"
  protocols           = ["https"]

  subscription_required = true
  subscription_key_parameter_names {
    header = "Ocp-Apim-Subscription-Key"
    query  = "subscription-key"
  }
}

resource "azurerm_api_management_api_operation" "post_inspection" {
  operation_id        = "post-inspection"
  api_name            = azurerm_api_management_api.inspector.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Submit Inspection"
  method              = "POST"
  url_template        = "/"
}

resource "azurerm_api_management_api_operation" "get_verdict" {
  operation_id        = "get-verdict"
  api_name            = azurerm_api_management_api.inspector.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Get Verdict"
  method              = "GET"
  url_template        = "/{requestId}/verdict"

  template_parameter {
    name     = "requestId"
    required = true
    type     = "string"
  }
}

resource "azurerm_api_management_api_operation" "list_inspections" {
  operation_id        = "list-inspections"
  api_name            = azurerm_api_management_api.inspector.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "List Inspections"
  method              = "GET"
  url_template        = "/"
}

resource "azurerm_api_management_api_operation" "post_feedback" {
  operation_id        = "post-feedback"
  api_name            = azurerm_api_management_api.inspector.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Submit Inspector Feedback"
  method              = "POST"
  url_template        = "/{requestId}/feedback"

  template_parameter {
    name     = "requestId"
    required = true
    type     = "string"
  }
}

resource "azurerm_api_management_api_operation" "get_request_payload" {
  operation_id        = "get-request-payload"
  api_name            = azurerm_api_management_api.inspector.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Get Inbound Request Payload"
  method              = "GET"
  url_template        = "/{requestId}"

  template_parameter {
    name     = "requestId"
    required = true
    type     = "string"
  }
}

resource "azurerm_api_management_api_policy" "inspector" {
  api_name            = azurerm_api_management_api.inspector.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name

  xml_content = <<XML
<policies>
  <inbound>
    <base />
    ${local._cors_xml}
    <set-backend-service backend-id="${azurerm_api_management_backend.inspector_pipeline.name}" />
  </inbound>
  <backend>
    <forward-request timeout="60" follow-redirects="false" />
  </backend>
  <outbound>
    <base />
  </outbound>
  <on-error>
    <base />
  </on-error>
</policies>
XML

  depends_on = [azurerm_api_management_backend.inspector_pipeline]
}

# ============================================================================
# Chat Agent API — /chat
# ============================================================================
resource "azurerm_api_management_backend" "inspector_pipeline_chat" {
  name                = "inspector-pipeline-chat-backend"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  protocol            = "http"
  url                 = "https://${var.pipeline_function_app_hostname}/api/chat"

  credentials {
    header = {
      "x-functions-key" = "{{inspector-pipeline-function-key}}"
    }
  }

  depends_on = [azurerm_api_management_named_value.function_key]
}

resource "azurerm_api_management_api" "chat" {
  name                = "chat-api"
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  revision            = "1"
  display_name        = "ARIA Inspector Chat Agent API"
  path                = "chat"
  protocols           = ["https"]

  subscription_required = true
  subscription_key_parameter_names {
    header = "Ocp-Apim-Subscription-Key"
    query  = "subscription-key"
  }
}

resource "azurerm_api_management_api_operation" "chat_post_message" {
  operation_id        = "chat-post-message"
  api_name            = azurerm_api_management_api.chat.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Send Chat Message"
  method              = "POST"
  url_template        = "/{requestId}/message"

  template_parameter {
    name     = "requestId"
    required = true
    type     = "string"
  }
}

resource "azurerm_api_management_api_operation" "chat_get_history" {
  operation_id        = "chat-get-history"
  api_name            = azurerm_api_management_api.chat.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Get Conversation History"
  method              = "GET"
  url_template        = "/{requestId}/history"

  template_parameter {
    name     = "requestId"
    required = true
    type     = "string"
  }
}

resource "azurerm_api_management_api_operation" "chat_get_evidence" {
  operation_id        = "chat-get-evidence"
  api_name            = azurerm_api_management_api.chat.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
  display_name        = "Get Finding Evidence"
  method              = "GET"
  url_template        = "/{requestId}/evidence/{findingCode}"

  template_parameter {
    name     = "requestId"
    required = true
    type     = "string"
  }

  template_parameter {
    name     = "findingCode"
    required = true
    type     = "string"
  }
}

resource "azurerm_api_management_api_policy" "chat" {
  api_name            = azurerm_api_management_api.chat.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name

  xml_content = local._chat_policy_xml

  depends_on = [azurerm_api_management_api_operation.chat_post_message]
}

# ============================================================================
# Product — groups inspector + chat APIs under one subscription
# ============================================================================
resource "azurerm_api_management_product" "inspector" {
  product_id            = "inspection-agent"
  resource_group_name   = var.resource_group_name
  api_management_name   = azurerm_api_management.apim.name
  display_name          = "ARIA Inspection Agent"
  subscription_required = true
  subscriptions_limit   = 10
  approval_required     = false
  published             = true
}

resource "azurerm_api_management_product_api" "inspector" {
  product_id          = azurerm_api_management_product.inspector.product_id
  api_name            = azurerm_api_management_api.inspector.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
}

resource "azurerm_api_management_product_api" "chat" {
  product_id          = azurerm_api_management_product.inspector.product_id
  api_name            = azurerm_api_management_api.chat.name
  api_management_name = azurerm_api_management.apim.name
  resource_group_name = var.resource_group_name
}

# ============================================================================
# Subscription — consumed by the chat UI web app as APIM_SUBSCRIPTION_KEY
# ============================================================================
resource "azurerm_api_management_subscription" "webapp" {
  resource_group_name = var.resource_group_name
  api_management_name = azurerm_api_management.apim.name
  product_id          = azurerm_api_management_product.inspector.id
  display_name        = "Inspector WebApp"
  state               = "active"
  allow_tracing       = false

  depends_on = [azurerm_api_management_product.inspector]
}
