# Ported from project-example/terraform/modules/function_apps + the RBAC role
# assignments that lived in project-example/terraform/main.tf root (they were
# at root there because Cosmos/OpenAI/DocInt/Search lived in a separate
# subscription; here everything's local so they're colocated with the
# Function App that needs them).
#
# Dropped: VNet integration (pipeline_subnet_id), private endpoint, private
# DNS zone, the "Downstream Services" cross-subscription data sources.
# Changed: public_network_access_enabled = true.
# Kept: Flex Consumption plan/sizing, user-assigned identity, all app
# settings (including API keys, matching the reference exactly), RBAC grants.

resource "azurerm_service_plan" "flex_consumption" {
  name                = var.flex_consumption_plan_name
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "FC1"

  tags = var.tags
}

resource "azurerm_user_assigned_identity" "function_apps" {
  name                = var.user_assigned_identity_name
  resource_group_name = var.resource_group_name
  location            = var.location

  tags = var.tags
}

# ============================================================================
# RBAC — Storage (runtime storage + raw-uploads / evidence blobs)
# ============================================================================
resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = var.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function_apps.principal_id
}

# ============================================================================
# RBAC — Cosmos DB (keyless data-plane access)
# Role ID 00000000-0000-0000-0000-000000000002 = "Cosmos DB Built-in Data Contributor"
# Kept here (not in the cosmos_db module) to avoid a module dependency cycle:
# cosmos_db doesn't know about this identity, function_apps already depends
# on cosmos_db's account id/endpoint.
# ============================================================================
resource "azurerm_cosmosdb_sql_role_assignment" "pipeline_cosmos_contributor" {
  resource_group_name = var.resource_group_name
  account_name        = element(split("/", var.cosmos_db_account_id), length(split("/", var.cosmos_db_account_id)) - 1)
  role_definition_id  = "${var.cosmos_db_account_id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_user_assigned_identity.function_apps.principal_id
  scope               = var.cosmos_db_account_id
}

# ============================================================================
# RBAC — Document Intelligence & OpenAI
# ============================================================================
resource "azurerm_role_assignment" "document_intelligence_user" {
  scope                = var.document_intelligence_id
  role_definition_name = "Cognitive Services User"
  principal_id         = azurerm_user_assigned_identity.function_apps.principal_id
}

resource "azurerm_role_assignment" "document_intelligence_contributor" {
  scope                = var.document_intelligence_id
  role_definition_name = "Cognitive Services Contributor"
  principal_id         = azurerm_user_assigned_identity.function_apps.principal_id
}

resource "azurerm_role_assignment" "openai_user" {
  scope                = var.azure_openai_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.function_apps.principal_id
}

# ============================================================================
# RBAC — AI Search (Change Feed indexer writes + REST reads)
# ============================================================================
resource "azurerm_role_assignment" "search_index_contributor" {
  scope                = var.azure_search_id
  role_definition_name = "Search Index Data Contributor"
  principal_id         = azurerm_user_assigned_identity.function_apps.principal_id
}

resource "azurerm_role_assignment" "search_index_reader" {
  scope                = var.azure_search_id
  role_definition_name = "Search Index Data Reader"
  principal_id         = azurerm_user_assigned_identity.function_apps.principal_id
}

# ============================================================================
# RBAC — App Configuration (read agent spec / runtime config)
# ============================================================================
resource "azurerm_role_assignment" "app_config_reader" {
  scope                = var.app_configuration_id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = azurerm_user_assigned_identity.function_apps.principal_id
}

# ============================================================================
# Function App - Pipeline (Flex Consumption for Durable Functions)
# ============================================================================
resource "azurerm_function_app_flex_consumption" "pipeline" {
  name                = var.pipeline_function_app_name
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.flex_consumption.id

  https_only                    = true
  public_network_access_enabled = true

  # Flex Consumption requires a deployment storage container.
  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${var.storage_account_blob_endpoint}deployments"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = var.storage_account_access_key

  runtime_name    = "python"
  runtime_version = var.python_version

  instance_memory_in_mb  = var.pipeline_instance_memory_mb
  maximum_instance_count = var.pipeline_max_instance_count

  site_config {
    application_insights_connection_string = var.app_insights_connection_string
    application_insights_key               = var.app_insights_instrumentation_key
  }

  app_settings = {
    "APPINSIGHTS_INSTRUMENTATIONKEY" = var.app_insights_instrumentation_key

    # Durable Functions — orchestration state storage
    "AzureWebJobsStorage" = var.storage_account_connection_string

    # Managed Identity — used by all Azure SDK calls
    "MANAGED_IDENTITY_CLIENT_ID" = azurerm_user_assigned_identity.function_apps.client_id

    # Blob storage for inspection files
    "RAW_UPLOADS_STORAGE_URL" = var.storage_account_blob_endpoint
    "RAW_UPLOADS_CONTAINER"   = "raw-uploads"

    # Azure AI Document Intelligence
    "DOCUMENT_INTELLIGENCE_ENDPOINT" = var.document_intelligence_endpoint
    "DI_CONFIDENCE_THRESHOLD"        = "0.85"

    # Azure OpenAI
    "AZURE_OPENAI_ENDPOINT"             = var.azure_openai_endpoint
    "AZURE_OPENAI_DEPLOYMENT"           = var.azure_openai_deployment
    "AZURE_OPENAI_API_KEY"              = var.azure_openai_key
    "AZURE_OPENAI_EMBEDDING_DEPLOYMENT" = var.azure_openai_embedding_deployment

    # Cosmos DB
    "COSMOS_DB_ENDPOINT"                 = var.cosmos_db_endpoint
    "COSMOS_DB_DATABASE"                 = var.cosmos_db_database
    "COSMOS_DB_CONTAINER"                = "inspections"
    "COSMOS_DB_INBOUND_CONTAINER"        = "inbound-requests"
    "COSMOS_DB_RESULTS_CONTAINER"        = "extraction-artifacts"
    "COSMOS_DB_RISK_EVALUATIONS_CONTAINER" = "risk-evaluations"
    "COSMOS_DB_RULES_CONTAINER"          = "rules"
    "COSMOS_DB_CALLBACK_LOG_CONTAINER"   = "callback-log"
    "COSMOS_DB_FEEDBACK_CONTAINER"       = "inspector-feedback"
    "COSMOS_CONNECTION__accountEndpoint" = var.cosmos_db_endpoint

    # Azure App Configuration
    "APP_CONFIG_ENDPOINT" = var.app_configuration_endpoint

    # Delivery settings
    "DELIVERY_TIMEOUT_SECONDS" = "30"
    "DELIVERY_MAX_RETRIES"     = "3"
    "DELIVERY_CALLBACK_URL"    = var.delivery_callback_url
    "DELIVERY_SKIP_CALLBACK"   = var.delivery_skip_callback

    # Python worker isolation — required for Flex Consumption to use vendored .python_packages
    "PYTHON_ISOLATE_WORKER_DEPENDENCIES" = "1"

    # Chat Agent + Case Summary Indexer
    "AZURE_SEARCH_ENDPOINT"                 = var.azure_search_endpoint
    "AZURE_SEARCH_KEY"                      = var.azure_search_key
    "AZURE_SEARCH_INDEX_CASE_SUMMARIES"     = "case-summaries"
    "AZURE_SEARCH_INDEX_DOCUMENT_FIELDS"    = "document-fields"
    "AZURE_SEARCH_INDEX_INSPECTOR_FEEDBACK" = "inspector-feedback"
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.function_apps.id]
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [
      tags,
      app_settings["APPINSIGHTS_INSTRUMENTATIONKEY"],
      app_settings["AzureWebJobsStorage"],
    ]
  }
}

# Auto-fetch the default function key after Function App creation - consumed
# by the APIM backend (single terraform apply resolves this dependency order
# automatically since the data source references the resource above).
data "azurerm_function_app_host_keys" "pipeline" {
  name                = azurerm_function_app_flex_consumption.pipeline.name
  resource_group_name = var.resource_group_name

  depends_on = [azurerm_function_app_flex_consumption.pipeline]
}
