# Account + database ported from project-ailanding zone/terraform/modules/cosmos_db.
# Container list ported from project-example/terraform/main.tf root-level
# azurerm_cosmosdb_sql_container resources (all 7 containers used by the
# pipeline + chat agent), which were originally declared at root because
# Cosmos lived in the AILZ subscription. Dropped: private endpoint.

resource "azurerm_cosmosdb_account" "main" {
  name                = var.cosmos_account_name
  location            = var.location
  resource_group_name = var.resource_group_name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = var.location
    failover_priority = 0
  }

  public_network_access_enabled = true

  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = var.database_name
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  throughput          = 400
}

# NOTE: The "Function App -> Cosmos DB Built-in Data Contributor" role
# assignment lives in the function_apps module (not here), because that
# identity is created by function_apps - putting the assignment here would
# create a module dependency cycle (cosmos_db needs the identity, function_apps
# needs the Cosmos endpoint).


# ── inspections ──────────────────────────────────────────────────────────────
# Primary case state container. Written by pipeline, read by webapp + chat agent.
resource "azurerm_cosmosdb_sql_container" "inspections" {
  name                  = "inspections"
  resource_group_name   = var.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/requestId"]
  partition_key_version = 2

  autoscale_settings {
    max_throughput = 4000
  }
}

# ── inbound-requests ─────────────────────────────────────────────────────────
# Raw inbound submission payloads - source of truth for case metadata.
resource "azurerm_cosmosdb_sql_container" "inbound_requests" {
  name                  = "inbound-requests"
  resource_group_name   = var.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/requestId"]
  partition_key_version = 2

  autoscale_settings {
    max_throughput = 4000
  }
}

# ── extraction-artifacts ─────────────────────────────────────────────────────
# Per-document DI extraction results (id = {requestId}_{documentTypeId}).
resource "azurerm_cosmosdb_sql_container" "extraction_artifacts" {
  name                  = "extraction-artifacts"
  resource_group_name   = var.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/requestId"]
  partition_key_version = 2

  autoscale_settings {
    max_throughput = 4000
  }
}

# ── rules ─────────────────────────────────────────────────────────────────────
# Validation rules registry.
resource "azurerm_cosmosdb_sql_container" "rules" {
  name                  = "rules"
  resource_group_name   = var.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/category"]
  partition_key_version = 2

  autoscale_settings {
    max_throughput = 4000
  }
}

# ── inspector-feedback ────────────────────────────────────────────────────────
# Inspector thumbs-up/down ratings on AI verdicts.
resource "azurerm_cosmosdb_sql_container" "inspector_feedback" {
  name                  = "inspector-feedback"
  resource_group_name   = var.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/requestId"]
  partition_key_version = 2

  autoscale_settings {
    max_throughput = 4000
  }
}

# ── callback-log ──────────────────────────────────────────────────────────────
# Delivery attempt log + exception/override events. 90-day TTL - transient
# operational records.
resource "azurerm_cosmosdb_sql_container" "callback_log" {
  name                  = "callback-log"
  resource_group_name   = var.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/requestId"]
  partition_key_version = 2
  default_ttl           = 7776000 # 90 days

  autoscale_settings {
    max_throughput = 4000
  }
}

# ── conversations ─────────────────────────────────────────────────────────────
# Chat agent conversation history per case session. 90-day TTL.
resource "azurerm_cosmosdb_sql_container" "conversations" {
  name                = "conversations"
  resource_group_name = var.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/requestId"]
  default_ttl         = 7776000 # 90 days
}
