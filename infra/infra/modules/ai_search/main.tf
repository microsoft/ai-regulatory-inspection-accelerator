# Search service is new (the reference project only ever referenced an
# *existing* AI Search service via a data source - it never created one in
# Terraform). Index definitions (fields, vector search, semantic config) are
# ported as-is from project-example/terraform/main.tf.

terraform {
  required_providers {
    azapi = {
      source = "azure/azapi"
    }
    time = {
      source = "hashicorp/time"
    }
  }
}

resource "azurerm_search_service" "main" {
  name                = var.search_service_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.sku

  public_network_access_enabled = true
  local_authentication_enabled  = true # aadOrApiKey - required for azapi_data_plane_resource index management
  authentication_failure_mode   = "http403"

  tags = var.tags
}

resource "time_sleep" "wait_for_search_service" {
  depends_on      = [azurerm_search_service.main]
  create_duration = "2m"
}

locals {
  hnsw_vector_search = {
    algorithms = [
      {
        name = "hnsw-algo"
        kind = "hnsw"
        hnswParameters = {
          m              = 4
          efConstruction = 400
          efSearch       = 500
          metric         = "cosine"
        }
      }
    ]
    profiles = [
      { name = "hnsw-profile", algorithm = "hnsw-algo" }
    ]
  }
}

# ── AI Search index: case-summaries ──────────────────────────────────────────
# One document per completed case. Structured GPT case_summary + embedding.
resource "azapi_data_plane_resource" "search_index_case_summaries" {
  type      = "Microsoft.Search/searchServices/indexes@2024-07-01"
  name      = "case-summaries"
  parent_id = "${var.search_service_name}.search.windows.net"

  depends_on = [time_sleep.wait_for_search_service]

  timeouts {
    read = "10m"
  }

  body = {
    fields = [
      { name = "case_id", type = "Edm.String", key = true, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "case_status", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "verdict", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "risk_level", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "importer_name", type = "Edm.String", key = false, searchable = true, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "request_type", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "port_of_entry", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "finding_codes", type = "Collection(Edm.String)", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "finding_count", type = "Edm.Int32", key = false, searchable = false, filterable = true, retrievable = true, sortable = true, facetable = false },
      { name = "case_summary", type = "Edm.String", key = false, searchable = true, filterable = false, retrievable = true, sortable = false, facetable = false, analyzer = "standard.lucene" },
      { name = "verdict_generated_at", type = "Edm.DateTimeOffset", key = false, searchable = false, filterable = true, retrievable = true, sortable = true, facetable = false },
      { name = "indexed_at", type = "Edm.DateTimeOffset", key = false, searchable = false, filterable = false, retrievable = true, sortable = false, facetable = false },
      {
        name                = "case_summary_vector"
        type                = "Collection(Edm.Single)"
        key                 = false
        searchable          = true
        retrievable         = false
        filterable          = false
        sortable            = false
        facetable           = false
        dimensions          = 1536
        vectorSearchProfile = "hnsw-profile"
      }
    ]
    vectorSearch = local.hnsw_vector_search
    semantic = {
      configurations = [
        {
          name = "case-summary-semantic"
          prioritizedFields = {
            prioritizedContentFields  = [{ fieldName = "case_summary" }]
            prioritizedKeywordsFields = [{ fieldName = "importer_name" }, { fieldName = "finding_codes" }]
          }
        }
      ]
    }
  }

  lifecycle {
    ignore_changes = [body] # Prevent Terraform drift from manual portal edits to index schema
  }
}

# ── AI Search index: document-fields ─────────────────────────────────────────
# One document per PDF per case. Extracted key-value fields + DI OCR markdown + vector.
resource "azapi_data_plane_resource" "search_index_document_fields" {
  type      = "Microsoft.Search/searchServices/indexes@2024-07-01"
  name      = "document-fields"
  parent_id = "${var.search_service_name}.search.windows.net"

  depends_on = [
    time_sleep.wait_for_search_service,
    azapi_data_plane_resource.search_index_case_summaries,
  ]

  timeouts {
    read = "10m"
  }

  body = {
    fields = [
      { name = "id", type = "Edm.String", key = true, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "request_id", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "document_type_id", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "document_type", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "ocr_confidence", type = "Edm.Double", key = false, searchable = false, filterable = true, retrievable = true, sortable = true, facetable = false },
      { name = "detected_language", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "has_handwriting", type = "Edm.Boolean", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "low_confidence_field_count", type = "Edm.Int32", key = false, searchable = false, filterable = true, retrievable = true, sortable = true, facetable = false },
      { name = "fields_text", type = "Edm.String", key = false, searchable = true, filterable = false, retrievable = true, sortable = false, facetable = false, analyzer = "standard.lucene" },
      { name = "markdown_content", type = "Edm.String", key = false, searchable = true, filterable = false, retrievable = false, sortable = false, facetable = false, analyzer = "standard.lucene" },
      { name = "extracted_at", type = "Edm.DateTimeOffset", key = false, searchable = false, filterable = true, retrievable = true, sortable = true, facetable = false },
      { name = "indexed_at", type = "Edm.DateTimeOffset", key = false, searchable = false, filterable = false, retrievable = true, sortable = false, facetable = false },
      {
        name                = "content_vector"
        type                = "Collection(Edm.Single)"
        key                 = false
        searchable          = true
        retrievable         = false
        filterable          = false
        sortable            = false
        facetable           = false
        dimensions          = 1536
        vectorSearchProfile = "hnsw-profile"
      }
    ]
    vectorSearch = local.hnsw_vector_search
    semantic = {
      configurations = [
        {
          name = "document-fields-semantic"
          prioritizedFields = {
            prioritizedContentFields  = [{ fieldName = "fields_text" }]
            prioritizedKeywordsFields = [{ fieldName = "document_type" }]
          }
        }
      ]
    }
  }

  lifecycle {
    ignore_changes = [body]
  }
}

# ── AI Search index: inspector-feedback ──────────────────────────────────────
# One document per inspector feedback submission on an AI verdict.
resource "azapi_data_plane_resource" "search_index_inspector_feedback" {
  type      = "Microsoft.Search/searchServices/indexes@2024-07-01"
  name      = "inspector-feedback"
  parent_id = "${var.search_service_name}.search.windows.net"

  depends_on = [
    time_sleep.wait_for_search_service,
    azapi_data_plane_resource.search_index_document_fields,
  ]

  timeouts {
    read = "10m"
  }

  body = {
    fields = [
      { name = "id", type = "Edm.String", key = true, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "request_id", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = false },
      { name = "rating", type = "Edm.String", key = false, searchable = false, filterable = true, retrievable = true, sortable = false, facetable = true },
      { name = "comment", type = "Edm.String", key = false, searchable = true, filterable = false, retrievable = true, sortable = false, facetable = false, analyzer = "standard.lucene" },
      { name = "submitted_at", type = "Edm.DateTimeOffset", key = false, searchable = false, filterable = true, retrievable = true, sortable = true, facetable = false },
      {
        name                = "comment_vector"
        type                = "Collection(Edm.Single)"
        key                 = false
        searchable          = true
        retrievable         = false
        filterable          = false
        sortable            = false
        facetable           = false
        dimensions          = 1536
        vectorSearchProfile = "hnsw-profile"
      }
    ]
    vectorSearch = local.hnsw_vector_search
    semantic = {
      configurations = [
        {
          name = "inspector-feedback-semantic"
          prioritizedFields = {
            prioritizedContentFields  = [{ fieldName = "comment" }]
            prioritizedKeywordsFields = [{ fieldName = "rating" }]
          }
        }
      ]
    }
  }

  lifecycle {
    ignore_changes = [body]
  }
}
