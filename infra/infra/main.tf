# Platform resources - ported from project-example (InspectionAgent) and
# project-ailanding zone (AI Landing Zone) Terraform, merged into a single
# self-contained stack in one subscription / one resource group.
#
# Networking is intentionally left open (no VNets / private endpoints) for
# this general-purpose accelerator. Add those yourself if your environment
# requires them.
#
# Build order (matches each resource's real dependency):
#   1. monitoring        - Log Analytics + Application Insights
#   2. storage           - storage account, raw-uploads + deployments containers
#   3. cosmos_db         - account, database, 7 containers
#   4. ai_search         - search service + 3 indexes
#   5. ai_foundry        - AI Services + OpenAI + Document Intelligence (needs cosmos_db for RBAC)
#   6. app_configuration - App Configuration store
#   7. function_apps     - Flex Consumption Function App (needs 2-6)
#   8. api_management    - APIM + backends (needs function_apps host key)
#   9. webapp            - chat UI (needs api_management gateway URL + subscription key)

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}

# ============================================================================
# 1. Monitoring
# ============================================================================
module "monitoring" {
  source = "./modules/monitoring"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  log_analytics_name  = var.log_analytics_name
  app_insights_name   = var.app_insights_name
  tags                = var.tags
}

# ============================================================================
# 2. Storage
# ============================================================================
module "storage" {
  source = "./modules/storage"

  resource_group_name  = azurerm_resource_group.main.name
  location             = azurerm_resource_group.main.location
  storage_account_name = var.storage_account_name
  cors_allowed_origins = var.cors_allowed_origins
  tags                 = var.tags
}

# ============================================================================
# 3. Cosmos DB
# ============================================================================
module "cosmos_db" {
  source = "./modules/cosmos_db"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.cosmos_location
  cosmos_account_name = var.cosmos_account_name
  database_name       = var.cosmos_database_name
  tags                = var.tags
}

# ============================================================================
# 4. Azure AI Search
# ============================================================================
module "ai_search" {
  source = "./modules/ai_search"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  search_service_name = var.search_service_name
  sku                 = var.search_sku
  tags                = var.tags
}

# ============================================================================
# 5. AI Foundry (AI Services + Azure OpenAI + Document Intelligence)
# ============================================================================
module "ai_foundry" {
  source = "./modules/ai_foundry"

  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  ai_services_name           = var.ai_services_name
  openai_name                = var.openai_name
  document_intelligence_name = var.document_intelligence_name
  cosmos_account_id          = module.cosmos_db.cosmos_account_id
  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id
  tags                       = var.tags
}

# ============================================================================
# 6. Azure App Configuration
# ============================================================================
module "app_configuration" {
  source = "./modules/app_configuration"

  resource_group_name    = azurerm_resource_group.main.name
  location               = azurerm_resource_group.main.location
  app_configuration_name = var.app_configuration_name
  tags                   = var.tags
}

# ============================================================================
# 7. Key Vault runtime secrets
# ============================================================================
resource "azurerm_key_vault" "runtime" {
  name                       = var.key_vault_name
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = false
  soft_delete_retention_days = 7
  rbac_authorization_enabled = true
  tags                       = var.tags
}

resource "azurerm_key_vault_secret" "azure_openai_api_key" {
  name         = "AZURE-OPENAI-API-KEY"
  value        = module.ai_foundry.openai_primary_key
  key_vault_id = azurerm_key_vault.runtime.id
}

resource "azurerm_role_assignment" "pipeline_key_vault_secrets_user" {
  scope                = azurerm_key_vault.runtime.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = module.function_apps.user_assigned_identity_principal_id
}

# ============================================================================
# 8. Function App (Pipeline)
# ============================================================================
module "function_apps" {
  source = "./modules/function_apps"

  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  flex_consumption_plan_name  = var.flex_consumption_plan_name
  user_assigned_identity_name = var.user_assigned_identity_name
  pipeline_function_app_name  = var.pipeline_function_app_name
  python_version              = var.python_version

  storage_account_id                = module.storage.storage_account_id
  storage_account_access_key        = module.storage.primary_access_key
  storage_account_connection_string = module.storage.primary_connection_string
  storage_account_blob_endpoint     = module.storage.primary_blob_endpoint

  app_insights_connection_string   = module.monitoring.app_insights_connection_string
  app_insights_instrumentation_key = module.monitoring.app_insights_instrumentation_key

  cosmos_db_account_id = module.cosmos_db.cosmos_account_id
  cosmos_db_endpoint   = module.cosmos_db.cosmos_endpoint
  cosmos_db_database   = module.cosmos_db.database_name

  document_intelligence_id       = module.ai_foundry.document_intelligence_id
  document_intelligence_endpoint = module.ai_foundry.document_intelligence_endpoint

  azure_openai_id                   = module.ai_foundry.openai_id
  azure_openai_endpoint             = module.ai_foundry.openai_endpoint
  azure_openai_key                  = module.ai_foundry.openai_primary_key
  azure_openai_key_vault_secret_uri = azurerm_key_vault_secret.azure_openai_api_key.versionless_id
  azure_openai_deployment           = var.azure_openai_deployment
  azure_openai_vision_deployment    = var.azure_openai_vision_deployment
  azure_openai_embedding_deployment = var.azure_openai_embedding_deployment

  azure_search_id       = module.ai_search.search_service_id
  azure_search_endpoint = module.ai_search.search_endpoint
  azure_search_key      = module.ai_search.search_primary_key

  app_configuration_id       = module.app_configuration.app_configuration_id
  app_configuration_endpoint = module.app_configuration.app_configuration_endpoint

  delivery_callback_url  = var.delivery_callback_url
  delivery_skip_callback = var.delivery_skip_callback

  tags = var.tags
}

# ============================================================================
# 8. API Management
# ============================================================================
module "api_management" {
  source = "./modules/api_management"

  apim_name           = var.apim_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  publisher_name      = var.apim_publisher_name
  publisher_email     = var.apim_publisher_email
  sku_name            = var.apim_sku_name

  log_analytics_workspace_id = module.monitoring.log_analytics_workspace_id

  pipeline_function_app_hostname = module.function_apps.pipeline_function_app_default_hostname
  pipeline_function_app_key      = module.function_apps.pipeline_function_app_default_key

  cors_allowed_origins = var.cors_allowed_origins

  tags = var.tags
}

# ============================================================================
# 9. Chat UI Web App
# ============================================================================
module "webapp" {
  source = "./modules/webapp"

  resource_group_name = azurerm_resource_group.main.name
  location            = var.webapp_location

  service_plan_name = var.webapp_service_plan_name
  sku_name          = var.webapp_sku_name
  webapp_name       = var.webapp_name
  python_version    = var.python_version

  app_insights_instrumentation_key = module.monitoring.app_insights_instrumentation_key
  app_insights_connection_string   = module.monitoring.app_insights_connection_string

  apim_gateway_url      = module.api_management.apim_gateway_url
  apim_subscription_key = module.api_management.webapp_apim_subscription_key

  tags = var.tags
}
