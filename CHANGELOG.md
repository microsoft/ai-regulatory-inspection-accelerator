# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- Initial README, folder structure, and documentation scaffolding
- Food Safety Inspection template
- Customs, KYC/AML, Insurance Claims, Healthcare Prior Auth template placeholders
- Generic REST and File-based platform connectors
- SharePoint and Dynamics 365 community connectors
- Connector SDK base contract
- Food Inspection reference implementation
- Terraform IaC: 5 modules (app-landing-zone, ai-landing-zone, network, monitoring, identity)
- Core Platform pipeline orchestrator (`src/platform/orchestration/pipeline.py`) - decorator-free,
  unit-testable Durable Functions orchestrator sequencing Pre-Validation, DI Extraction,
  Rules & Policy, and Delivery agents
- Core Platform submission guard (`src/platform/orchestration/submission.py`) - pure idempotency/
  restart-resume decision logic, decoupled from Azure Functions HTTP and Durable Functions client types
- Core Platform pre-validation checks (`src/platform/intake/pre_validation.py`) - structural,
  metadata-only submission validation (document count, duplicate detection, MIME type, missing
  checksum, attachment type consistency, empty items)
- Core Platform field normalization (`src/platform/document_intelligence/field_normalization.py`) -
  Arabic/BiDi numeral and date normalization, currency extraction, config-driven field-alias
  resolution and canonicalization (with an injectable LLM semantic-resolver hook), and
  issue-date + validity-period expiry computation
- Core Platform quality assessment (`src/platform/document_intelligence/quality_assessment.py`) -
  pre-OCR image quality threshold decision logic with an injectable vision-model callback
- Core Platform token-tracking AI client (`src/platform/shared/ai_client.py`) - centralized,
  provider-injected completion wrapper capturing prompt, completion, total, and cached tokens
  with per-case, per-tenant, per-activity attribution and safe success/failure telemetry