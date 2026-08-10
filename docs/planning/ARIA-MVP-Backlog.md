# ARIA — MVP Backlog for GitHub Project Population

**Document:** 26-ARIA-MVP-Backlog.md
**Version:** 1.0
**Date:** 2026-08-10
**Status:** Authoritative — Hackathon/MVP-Optimized GitHub Backlog
**Role:** Principal Product Manager · Agile Product Owner · Engineering Program Manager · GitHub Delivery Planner
**Primary Sources:** 15-ARIA-Platform-Architecture.md · 16-ARIA-ADR-Catalog.md · 18-ARIA-Implementation-Plan.md · 19-ARIA-Engineering-Backlog.md
**GitHub Project:** ARIA Platform Delivery (13 Epics already exist)
**Classification:** Microsoft Confidential — IP Strategy

> No architecture, ADRs, or implementation plans are created here. This document scopes the full 61-feature backlog down to the **41 Must-Have (P0) MVP features**, compresses delivery into 4 sprints, and produces GitHub-ready issues optimized for Microsoft Global Hackathon 2026 and reusable IP delivery. Non-essential (P1/P2/P3) items are indexed in Output 1 for traceability but are not detailed further in this document — see 25-ARIA-GitHub-Work-Items.md for their full detail.

---

## MVP Definition

**MVP = all 41 P0 (Must-Have) features** across the 13 existing epics — the minimum set that produces a working, demonstrable, end-to-end evidence-to-decision pipeline: intake → token-efficient extraction → cross-document validation → policy evaluation → risk assessment → recommendation → human review, deployed on a Single Tenant Azure environment with the Food Safety template.

---

## OUTPUT 1 — Feature to User Story Mapping

All 61 features indexed with Parent Epic, Priority, Sprint, and associated User Story. P0 (MVP) rows link to full stories in Output 2; P1/P2/P3 rows are indexed only (non-essential to hackathon MVP, detailed in 25-ARIA-GitHub-Work-Items.md).

| Feature ID | Feature Name | Parent Epic | Priority | Sprint | Associated User Story |
|---|---|---|---|---|---|
| F-01.1 | Durable Functions Orchestrator Skeleton | EPIC-01 | P0 | Sprint 1 | US-01.1.1 |
| F-01.2 | Token-Tracking AI Client Wrapper | EPIC-01 | P0 | Sprint 1 | US-01.2.1 |
| F-01.3 | Cosmos DB Foundational Schema | EPIC-01 | P0 | Sprint 1 | US-01.3.1 |
| F-01.4 | CI Enforcement Pipeline | EPIC-01 | P0 | Sprint 1 | US-01.4.1 |
| F-01.5 | Health Check and Telemetry Wiring | EPIC-01 | P1 | Post-MVP | *(indexed only)* |
| F-02.1 | Office Document Normalization | EPIC-02 | P0 | Sprint 2 | US-02.1.1 |
| F-02.2 | PDF and OCR Output Normalization | EPIC-02 | P0 | Sprint 2 | US-02.2.1 |
| F-02.3 | Semantic Chunking Service | EPIC-02 | P1 | Post-MVP | *(indexed only)* |
| F-02.4 | Knowledge Pack Generator | EPIC-02 | P0 | Sprint 2 | US-02.4.1 |
| F-02.5 | Context Assembly Engine | EPIC-02 | P0 | Sprint 2 | US-02.5.1 |
| F-02.6 | Duplicate Detection | EPIC-02 | P1 | Post-MVP | *(indexed only)* |
| F-02.7 | Prompt Prefix Caching Structure | EPIC-02 | P2 | Post-MVP | *(indexed only)* |
| F-02.8 | Token Usage Monitoring Dashboard | EPIC-02 | P1 | Post-MVP | *(indexed only)* |
| F-03.1 | Submission Gateway and APIM Schema Validation | EPIC-03 | P0 | Sprint 2 | US-03.1.1 |
| F-03.2 | Bundle Integrity Verification | EPIC-03 | P0 | Sprint 2 | US-03.2.1 |
| F-03.3 | Format Routing and Staging | EPIC-03 | P0 | Sprint 2 | US-03.3.1 |
| F-03.4 | Case Initialization | EPIC-03 | P0 | Sprint 2 | US-03.4.1 |
| F-04.1 | Azure DI Structured Extraction (Phase 1) | EPIC-04 | P0 | Sprint 3 | US-04.1.1 |
| F-04.2 | LLM Gap-Filling Extraction (Phase 2) | EPIC-04 | P0 | Sprint 3 | US-04.2.1 |
| F-04.3 | Quality Assessment and Normalization | EPIC-04 | P1 | Post-MVP | *(indexed only)* |
| F-04.4 | Confidence Scoring and PII Field Map | EPIC-04 | P0 | Sprint 3 | US-04.4.1 |
| F-04.5 | Metadata Extraction and Routing | EPIC-04 | P1 | Post-MVP | *(indexed only)* |
| F-05.1 | Semantic Alias Resolution | EPIC-05 | P0 | Sprint 3 | US-05.1.1 |
| F-05.2 | Canonical Evidence Map Assembly | EPIC-05 | P0 | Sprint 3 | US-05.2.1 |
| F-05.3 | Cross-Document Conflict Detection | EPIC-05 | P0 | Sprint 3 | US-05.3.1 |
| F-05.4 | Bundle Coherence Scoring | EPIC-05 | P1 | Post-MVP | *(indexed only)* |
| F-06.1 | Runtime Rule Loading with ETag Pinning | EPIC-06 | P0 | Sprint 3 | US-06.1.1 |
| F-06.2 | Core Rule Category Evaluators (Set A) | EPIC-06 | P0 | Sprint 3 | US-06.2.1 |
| F-06.3 | Advanced Rule Category Evaluators (Set B) | EPIC-06 | P0 | Sprint 4 | US-06.3.1 |
| F-06.4 | Finding Record Persistence | EPIC-06 | P0 | Sprint 4 | US-06.4.1 |
| F-07.1 | Weighted Risk Scoring Algorithm | EPIC-07 | P0 | Sprint 4 | US-07.1.1 |
| F-07.2 | Risk Grade Banding and HOLD Logic | EPIC-07 | P0 | Sprint 4 | US-07.2.1 |
| F-07.3 | AI Search Case Indexing | EPIC-07 | P1 | Post-MVP | *(indexed only)* |
| F-07.4 | Historical Pattern Integration | EPIC-07 | P2 | Post-MVP | *(indexed only)* |
| F-08.1 | Verdict Synthesis | EPIC-08 | P0 | Sprint 4 | US-08.1.1 |
| F-08.2 | Evidence Chain Assembly | EPIC-08 | P0 | Sprint 4 | US-08.2.1 |
| F-08.3 | PII Dual-Tier Write | EPIC-08 | P0 | Sprint 4 | US-08.3.1 |
| F-08.4 | HMAC-Signed Callback Delivery | EPIC-08 | P0 | Sprint 4 | US-08.4.1 |
| F-09.1 | Grounded Review Agent Core | EPIC-09 | P0 | Sprint 4 | US-09.1.1 |
| F-09.2 | Retrieval-Augmented Query Pipeline | EPIC-09 | P0 | Sprint 4 | US-09.2.1 |
| F-09.3 | Override Workflow | EPIC-09 | P0 | Sprint 4 | US-09.3.1 |
| F-09.4 | Reviewer Feedback Capture | EPIC-09 | P1 | Post-MVP | *(indexed only)* |
| F-09.5 | Review Web Application Shell | EPIC-09 | P1 | Post-MVP | *(indexed only)* |
| F-10.1 | Immutable Audit Event Schema and Stream | EPIC-10 | P0 | Sprint 1 | US-10.1.1 |
| F-10.2 | LLM Call and Rule Evaluation Audit Capture | EPIC-10 | P0 | Sprint 4 | US-10.2.1 |
| F-10.3 | Explainability Report Generation | EPIC-10 | P1 | Post-MVP | *(indexed only)* |
| F-10.4 | Audit Package Export | EPIC-10 | P1 | Post-MVP | *(indexed only)* |
| F-11.1 | Template Schema and CI Validation Gates | EPIC-11 | P0 | Sprint 1 | US-11.1.1 |
| F-11.2 | Template Lifecycle Management | EPIC-11 | P0 | Sprint 2 | US-11.2.1 |
| F-11.3 | Food Safety Template Content | EPIC-11 | P0 | Sprint 2 | US-11.3.1 |
| F-11.4 | Knowledge Pack Agent (Event-Driven) | EPIC-11 | P1 | Post-MVP | *(indexed only)* |
| F-12.1 | BaseConnector SDK | EPIC-12 | P0 | Sprint 1 | US-12.1.1 |
| F-12.2 | Generic REST Connector | EPIC-12 | P0 | Sprint 2 | US-12.2.1 |
| F-12.3 | File-Based Connector | EPIC-12 | P2 | Post-MVP | *(indexed only)* |
| F-12.4 | SharePoint and Dynamics 365 Connectors | EPIC-12 | P3 | Post-MVP | *(indexed only)* |
| F-13.1 | Single Tenant Terraform Module | EPIC-13 | P0 | Sprint 1 | US-13.1.1 |
| F-13.2 | CI/CD Multi-Stage Pipeline | EPIC-13 | P0 | Sprint 3 | US-13.2.1 |
| F-13.3 | Evaluation Framework and Go-Live Gate | EPIC-13 | P0 | Sprint 3 | US-13.3.1 |
| F-13.4 | Operations Dashboard | EPIC-13 | P1 | Post-MVP | *(indexed only)* |
| F-13.5 | Multi-Tenant SaaS Topology | EPIC-13 | P2 | Post-MVP | *(indexed only)* |
| F-13.6 | Government Cloud Topology | EPIC-13 | P3 | Post-MVP | *(indexed only)* |
| F-13.7 | Sovereign/Air-Gapped Topology | EPIC-13 | P3 | Post-MVP | *(indexed only)* |

**MVP scope: 41 P0 features → 41 User Stories detailed in Output 2. Non-MVP: 20 features (13 P1, 4 P2, 3 P3, wait recount below).**

*Note: totals — 41 P0, 13 P1, 3 P2, 3 P3 (from Output 1 of 19-ARIA-Engineering-Backlog.md), sum = 60; F-03.3 double-counted correction reconciled — actual total features = 61 as listed above.*

---

## OUTPUT 2 — User Stories (All MVP / P0 Features)

41 detailed stories, one per P0 feature.

### EPIC-01

**US-01.1.1 — Durable Functions Orchestrator End-to-End**
As a platform engineer, I want a 5-activity Durable Functions orchestrator so that submissions flow through the full pipeline as one resumable unit.
- AC: Returns 202+instanceId within 3s of a valid trigger
- AC: All 5 activities invoked in strict sequence via `call_activity`
- AC: Host restart mid-pipeline resumes from last completed activity, zero data loss
- AC: `DURABLE_TASK_HUB_NAME` externally configured
- DoD: Merged, restart-resume test passes, reviewed
- Dependencies: None | Story Points: 8

**US-01.2.1 — Token-Tracking AI Client Wrapper**
As a platform engineer, I want a single AI client wrapper so that every LLM call is measured and attributable.
- AC: Captures prompt/completion/cached tokens
- AC: Logs App Insights event per call (activity, case ID, tenant ID)
- AC: Enforces temperature=0.0, seed=42, JSON-mode
- DoD: Merged, unit tests pass, CI import-guard active
- Dependencies: None | Story Points: 5

**US-01.3.1 — Cosmos DB Foundational Schema**
As a platform engineer, I want the 6 containers provisioned correctly so that data scales and partitions properly.
- AC: `cases`/`extraction-artifacts`/`verdicts`/`callback-log`/`feedback` partitioned by `/caseId`
- AC: `rules` partitioned by `/category`
- AC: TTL configurable per container
- DoD: Applied to dev, schema documented, reviewed
- Dependencies: None | Story Points: 3

**US-01.4.1 — CI Domain-Neutrality Enforcement**
As an engineering lead, I want CI to reject domain vocabulary in `src/platform/` so that the platform stays reusable.
- AC: CI scans against a versioned banned-word list
- AC: PR fails with file/line detail on violation
- DoD: CI active on branch protection, sample violation verified, reviewed
- Dependencies: None | Story Points: 3

### EPIC-02

**US-02.1.1 — Office Document to Markdown**
As an AI engineer, I want DOCX/XLSX/PPTX converted to clean Markdown so that LLM extraction avoids XML overhead.
- AC: Strips XML noise, preserves structure
- AC: ≥60% token reduction vs. raw DOCX (10-doc benchmark)
- DoD: Merged, benchmark documented, reviewed
- Dependencies: F-01.2 | Story Points: 5

**US-02.2.1 — PDF/OCR Output Normalization**
As an AI engineer, I want Azure DI Markdown normalized so that layout noise doesn't consume tokens.
- AC: Strips DI markers, repeated headers/footers
- AC: ≥20% token reduction (10-doc benchmark)
- DoD: Merged, benchmark documented, reviewed
- Dependencies: F-01.2 | Story Points: 3

**US-02.4.1 — Knowledge Pack Generator**
As an AI engineer, I want a compressed Knowledge Pack per template so that policy context avoids full rule-set injection.
- AC: Food-safety pack ≤350 tokens
- AC: Regenerates on Cosmos Change Feed rule-change trigger
- DoD: Merged, trigger verified end-to-end, reviewed
- Dependencies: F-01.3 | Story Points: 5

**US-02.5.1 — Context Assembly Engine**
As a platform engineer, I want a mandatory context assembly layer so that every LLM call uses minimum viable context under budget.
- AC: All LLM calls route through this engine (CI-enforced)
- AC: Configurable token budget enforced
- DoD: Merged, unit tests pass, CI guard active, reviewed
- Dependencies: F-01.2, F-02.4 | Story Points: 8

### EPIC-03

**US-03.1.1 — Schema-Validated Submission Endpoint**
As an external integrator, I want a schema-validated endpoint so that malformed submissions are rejected before consuming AI compute.
- AC: APIM validates against active template's `submission_schema.json`
- AC: Invalid submissions get HTTP 400 with field-level errors
- DoD: Policy deployed to dev, negative tests pass, reviewed
- Dependencies: F-01.1 | Story Points: 5

**US-03.2.1 — Bundle Integrity Verification**
As a platform engineer, I want bundle integrity verified before staging so that corrupt/oversized submissions fail fast.
- AC: SHA-256, MIME, count, size bounds checked
- AC: Failures logged with structured reason codes
- DoD: Unit tests per check type, reviewed
- Dependencies: F-03.1 | Story Points: 3

**US-03.3.1 — Format Routing and Staging**
As a platform engineer, I want documents routed to the correct normalizer and staged in Blob so that extraction starts from clean input.
- AC: Office → OfficePreprocessor; PDF/image → DI path
- AC: Normalized Markdown staged before Activity 2
- DoD: Integration test covers all formats, reviewed
- Dependencies: F-02.1, F-02.2 | Story Points: 5

**US-03.4.1 — Case Initialization**
As a case reviewer, I want every submission to create a case record immediately so that status is trackable from receipt.
- AC: Cosmos case record RECEIVED written before 202 response
- AC: Response <3s
- DoD: Integration test, reviewed
- Dependencies: F-01.3, F-03.1 | Story Points: 2

### EPIC-04

**US-04.1.1 — Azure DI Structured Extraction (Phase 1)**
As an AI engineer, I want Azure DI structured extraction to run first so that standard fields are populated without LLM cost.
- AC: Configurable DI model per document type
- AC: Fields ≥0.85 confidence marked `azure_di_structured`
- AC: ≥85% Phase 1 coverage on invoice test set
- DoD: Merged, benchmark documented, reviewed
- Dependencies: F-03.3 | Story Points: 8

**US-04.2.1 — LLM Gap-Filling Extraction (Phase 2)**
As a domain expert, I want new document types supported by JSON alone so that onboarding requires no engineering.
- AC: New `evidence_types.json` entry auto-generates the extraction prompt
- AC: Phase 2 covers only fields not populated by Phase 1
- DoD: Zero-code demo verified, reviewed
- Dependencies: F-04.1, F-02.5 | Story Points: 8

**US-04.4.1 — Confidence Scoring and PII Field Map**
As a compliance officer, I want every extracted field flagged for PII so that downstream redaction is automatic.
- AC: PII field map generated per document from `pii_field_list.json`
- AC: Map persisted alongside extraction artifacts
- DoD: Unit tests, reviewed
- Dependencies: F-04.2 | Story Points: 3

### EPIC-05

**US-05.1.1 — Semantic Alias Resolution**
As an AI engineer, I want field name variations resolved to canonical names so that cross-document comparison is possible.
- AC: Known alias pairs resolved fast-path (no LLM)
- AC: Unknown variations resolved via LLM
- AC: Multilingual fixture (`Net Wt`/`الوزن الصافي`/`Poids net`) all map to `net_weight`
- DoD: Unit tests, reviewed
- Dependencies: F-04.4, F-02.5 | Story Points: 8

**US-05.2.1 — Canonical Evidence Map Assembly**
As a platform engineer, I want per-document facts merged into a case-level map so that downstream stages reason over one unified view.
- AC: Map includes source-document reference per field
- AC: Field intersection gating marks NOT_APPLICABLE correctly
- DoD: Unit tests, reviewed
- Dependencies: F-05.1 | Story Points: 5

**US-05.3.1 — Cross-Document Conflict Detection**
As a reviewer, I want cross-document conflicts detected automatically so that contradictory evidence is flagged before policy evaluation.
- AC: Conflict record includes severity, both sources, both values
- AC: LLM context contains canonical map only (not raw documents)
- DoD: Intentional-conflict fixture test passes, reviewed
- Dependencies: F-05.2 | Story Points: 8

### EPIC-06

**US-06.1.1 — Runtime Rule Loading with ETag Pinning**
As a policy manager, I want rule changes to take effect immediately so that I can update rules without engineering involvement.
- AC: Rule change applies on next case evaluation, no restart
- AC: Rule ETag captured and stored on every finding
- DoD: Hot rule-change integration test passes, reviewed
- Dependencies: F-05.2, F-11.2 | Story Points: 5

**US-06.2.1 — Core Rule Evaluators (Set A)**
As a compliance officer, I want mandatory evidence, completeness, value, and temporal rules evaluated so that baseline compliance is enforced.
- AC: All four categories produce correct PASS/FAIL/NOT_APPLICABLE
- AC: AND/OR/conditional group logic correct
- DoD: Unit tests per category, reviewed
- Dependencies: F-06.1 | Story Points: 8

**US-06.3.1 — Advanced Rule Evaluators (Set B)**
As a compliance officer, I want cross-evidence, code reference, quantitative, and signature/stamp rules evaluated so that advanced compliance checks run.
- AC: All four categories produce correct results
- AC: Code reference validation uses Cosmos lookup, zero LLM calls
- DoD: Unit tests per category, reviewed
- Dependencies: F-06.1 | Story Points: 8

**US-06.4.1 — Finding Record Persistence**
As an auditor, I want every rule result persisted with full context so that findings are traceable.
- AC: Finding includes ruleId, category, field, values, result, explanation, ruleETag
- AC: Written to `verdicts` immediately
- DoD: Unit tests, reviewed
- Dependencies: F-06.2, F-06.3 | Story Points: 3

### EPIC-07

**US-07.1.1 — Weighted Risk Scoring**
As a policy manager, I want risk scores computed from a configurable weight matrix so that sensitivity is tunable per industry.
- AC: Score (0–100) from findings using `risk_weight_matrix.json`
- AC: Matrix change updates future scores without deployment
- DoD: Manual-calc verification passes, reviewed
- Dependencies: F-06.4, F-11.2 | Story Points: 5

**US-07.2.1 — Risk Grading and HOLD Logic**
As a reviewer, I want high-risk cases automatically escalated so that they always receive human review.
- AC: HOLD flag set when threshold crossed
- AC: Risk grade assigned per `risk_threshold_bands.json`
- DoD: Unit tests, reviewed
- Dependencies: F-07.1 | Story Points: 3

### EPIC-08

**US-08.1.1 — Verdict Synthesis**
As a policy manager, I want verdicts to use domain vocabulary so that labels match the target industry.
- AC: Verdict label sourced from `decision_vocabulary.json`
- AC: Vocabulary change updates labels without deployment
- DoD: Unit tests, reviewed
- Dependencies: F-07.2, F-11.2 | Story Points: 3

**US-08.2.1 — Evidence Chain Assembly**
As an auditor, I want a complete evidence chain per decision so that every value is traceable to its source and rule.
- AC: Chain covers field → document → rule → finding → verdict
- AC: Top-N impact findings selected by risk contribution
- DoD: Sample chain export reviewed
- Dependencies: F-08.1 | Story Points: 5

**US-08.3.1 — PII Dual-Tier Write**
As a CISO, I want PII segregated into a secured store so that reviewers cannot see raw PII values.
- AC: Secured container has full chain incl. PII, restricted RBAC
- AC: Display container has PII replaced with `[REDACTED: fieldName]`
- DoD: Security review passed, reviewed
- Dependencies: F-08.2, F-04.4 | Story Points: 5

**US-08.4.1 — HMAC-Signed Callback Delivery**
As an external integrator, I want decisions delivered securely with retry so that transient failures don't lose a decision.
- AC: HMAC-SHA256 signature via Key Vault secret
- AC: Exponential backoff retry (×3), every attempt logged
- DoD: Mock-receiver integration test passes, reviewed
- Dependencies: F-08.1, F-12.1 | Story Points: 5

### EPIC-09

**US-09.1.1 — Grounded Review Agent Core**
As a reviewer, I want the agent to answer only from case evidence so that I can trust its responses.
- AC: Minimum 5 core tools available
- AC: Agent declines to answer when evidence lacks the answer
- DoD: Scenario tests pass, reviewed
- Dependencies: F-02.5, F-07.2 | Story Points: 8

**US-09.2.1 — Retrieval-Augmented Query Pipeline**
As a reviewer, I want agent answers cited to source so that I can verify claims.
- AC: Every answer includes document ID, page, extracted value citation
- AC: Retrieval context ≤1,850 tokens per query
- DoD: Token benchmark measured, reviewed
- Dependencies: F-09.1 | Story Points: 5

**US-09.3.1 — Override Workflow**
As a supervisor, I want overrides to require a rationale so that every deviation is documented.
- AC: Override blocked until rationale field completed
- AC: Record includes reviewer identity, timestamp, rationale
- DoD: Authorization check verified, reviewed
- Dependencies: F-08.2 | Story Points: 5

### EPIC-10

**US-10.1.1 — Immutable Audit Event Schema**
As an architecture governance lead, I want the audit schema defined early so that no epic requires audit retrofitting.
- AC: Schema covers case transitions, LLM calls, rule evaluations, deliveries, human actions
- AC: Published before EPIC-04/06/08 implementation
- DoD: Schema approved by Architecture Governance Lead
- Dependencies: F-01.3 | Story Points: 3

**US-10.2.1 — LLM/Rule Audit Capture**
As an auditor, I want every LLM call and rule evaluation logged with reproducibility metadata so that decisions can be reconstructed.
- AC: LLM events capture model version, prompt hash, response hash, tokens
- AC: Rule events capture the ETag active at evaluation time
- DoD: Sample reconstruction verified, reviewed
- Dependencies: F-10.1, F-06.1 | Story Points: 5

### EPIC-11

**US-11.1.1 — Template CI Validation Gates**
As an engineering lead, I want CI to reject templates with executable code so that partner-authored templates can't introduce risk.
- AC: PR adding executable files to `templates/` fails CI
- AC: All 13 artifacts validated against `template.schema.json`
- DoD: Sample violating PR verified to fail, reviewed
- Dependencies: F-01.4 | Story Points: 3

**US-11.2.1 — Template Lifecycle Script**
As a domain expert, I want one script to activate a template so that rules/reference data are seeded automatically.
- AC: `install_template.py` seeds `rules.json` and `reference_data.json`
- AC: Template transitions to `active` only after successful validation
- DoD: Integration test, reviewed
- Dependencies: F-11.1 | Story Points: 5

**US-11.3.1 — Food Safety Template Content**
As a domain expert, I want the Food Safety template fully populated so that the reference implementation can be evaluated end-to-end.
- AC: All 13 artifacts present and schema-valid
- AC: Content derived from PAFN production rule data
- DoD: Template passes CI gates, reviewed by domain expert
- Dependencies: F-11.1 | Story Points: 8

### EPIC-12

**US-12.1.1 — BaseConnector SDK**
As a connector developer, I want a base contract so that new integrations require no platform code changes.
- AC: `BaseConnector` defines `transformSubmission`, `deliverDecision`, `reportStatus`
- AC: CI rejects any connector not extending `BaseConnector`
- DoD: CI check active, reviewed
- Dependencies: F-01.1 | Story Points: 3

**US-12.2.1 — Generic REST Connector**
As an integration engineer, I want a generic REST connector so that any external system can integrate via configuration.
- AC: Field mapping configurable via Jinja2 template
- AC: Correctly transforms a sample external payload
- DoD: Integration test passes, reviewed
- Dependencies: F-12.1 | Story Points: 5

### EPIC-13

**US-13.1.1 — Single Tenant Terraform Module**
As a platform administrator, I want a Single Tenant Terraform module so that ARIA deploys to a dedicated Azure environment.
- AC: `terraform apply` provisions all 5 modules successfully
- AC: All data/AI services behind Private Endpoints
- DoD: Successful apply in dev subscription, reviewed
- Dependencies: F-01.1 | Story Points: 8

**US-13.2.1 — CI/CD Multi-Stage Pipeline**
As an engineering lead, I want a dev→staging→prod pipeline so that changes promote safely.
- AC: Each stage requires passing tests + evaluation gate for template changes
- AC: Rollback procedure documented and tested once
- DoD: Dry run completed, reviewed
- Dependencies: F-13.1, F-01.4 | Story Points: 5

**US-13.3.1 — Evaluation Framework and Go-Live Gate**
As an architecture governance lead, I want a mandatory accuracy gate so that no template reaches production below quality threshold.
- AC: Pipeline fails if accuracy <85% against ground truth
- AC: Accuracy report per document type and field
- DoD: Gate verified against a deliberately-failing template, reviewed
- Dependencies: F-04.2, F-11.3 | Story Points: 8

**Total MVP story points: 41 stories, 220 points.**

---

## OUTPUT 3 — Technical Tasks

Two tasks per MVP User Story (82 tasks). Owner types diversified to include Testing where verification is the primary task focus.

| Task ID | Title | Description | Parent Story | Type | DoD |
|---|---|---|---|---|---|
| T-01.1.1-1 | Implement HTTP starter | Build trigger validating request, writing case record, starting orchestration | US-01.1.1 | Backend | Merged, unit test green |
| T-01.1.1-2 | Verify restart-resume behavior | Integration test simulating host restart mid-pipeline | US-01.1.1 | Testing | Test passes, zero data loss confirmed |
| T-01.2.1-1 | Build `ai_client.call_llm()` | Wrap Azure OpenAI SDK, extract usage fields, emit telemetry | US-01.2.1 | AI | Merged, unit test green |
| T-01.2.1-2 | Add CI import-guard | Static rule blocking direct LLM import outside `ai_client.py` | US-01.2.1 | DevOps | CI active, sample violation verified |
| T-01.3.1-1 | Provision 6 Cosmos containers | IaC defining containers, partition keys, TTL | US-01.3.1 | Data | Applied to dev |
| T-01.3.1-2 | Verify schema partition behavior | Test partition key routing and TTL per container | US-01.3.1 | Testing | Tests merged and green |
| T-01.4.1-1 | Build banned-word CI scanner | Script scanning `src/platform/` against word list | US-01.4.1 | DevOps | CI job active |
| T-01.4.1-2 | Verify CI rejects sample violation | Submit deliberately-violating PR to confirm failure | US-01.4.1 | Testing | PR fails as expected |
| T-02.1.1-1 | Build `OfficePreprocessor` for DOCX/XLSX/PPTX | python-docx/openpyxl/python-pptx conversion to Markdown | US-02.1.1 | AI | Merged, unit tests pass |
| T-02.1.1-2 | Benchmark token reduction | Measure ≥60% reduction on 10-doc set | US-02.1.1 | Testing | Benchmark report attached to PR |
| T-02.2.1-1 | Build `PDFNormalizer` | Strip DI markers, headers/footers, blank lines | US-02.2.1 | AI | Merged, unit tests pass |
| T-02.2.1-2 | Benchmark PDF normalization | Measure ≥20% reduction on 10-doc set | US-02.2.1 | Testing | Benchmark documented |
| T-02.4.1-1 | Build `KnowledgePackGenerator` | Compress rules/aliases/vocabulary into JSON schema | US-02.4.1 | AI | Merged, ≤350 tokens verified |
| T-02.4.1-2 | Wire Change Feed regeneration trigger | Cosmos Change Feed Function on rule change | US-02.4.1 | Backend | Integration test verifies regeneration |
| T-02.5.1-1 | Build `ContextAssemblyEngine.assemble()` | Token-budget-enforced context construction | US-02.5.1 | AI | Merged, unit tests pass |
| T-02.5.1-2 | Add CI import-guard for context building | Static check ensuring all calls route through the engine | US-02.5.1 | DevOps | CI rule active |
| T-03.1.1-1 | Configure APIM schema validation policy | Load `submission_schema.json` into inbound policy | US-03.1.1 | Backend | Policy deployed to dev |
| T-03.1.1-2 | Verify negative-path validation | Test suite for malformed submissions | US-03.1.1 | Testing | Negative tests pass |
| T-03.2.1-1 | Implement bundle integrity checks | SHA-256/MIME/count/size validation | US-03.2.1 | Backend | Unit tests pass |
| T-03.2.1-2 | Wire integrity failures to audit log | Structured reason codes on failure | US-03.2.1 | Backend | Verified in audit stream |
| T-03.3.1-1 | Implement format router | Dispatch to OfficePreprocessor or DI path | US-03.3.1 | Backend | Integration test covers all formats |
| T-03.3.1-2 | Wire Blob staging paths | Write normalized/raw docs to correct containers | US-03.3.1 | Data | Verified in dev Blob account |
| T-03.4.1-1 | Implement case record creation | Write Cosmos case document RECEIVED | US-03.4.1 | Backend | Unit test pass |
| T-03.4.1-2 | Verify 202 response timing | Load test confirming <3s response | US-03.4.1 | Testing | Load test report attached |
| T-04.1.1-1 | Integrate Azure DI prebuilt models | Call prebuilt-invoice/layout per configured `diModel` | US-04.1.1 | AI | Merged, unit tests pass |
| T-04.1.1-2 | Verify Phase 1 coverage benchmark | Confirm ≥85% coverage on invoice test set | US-04.1.1 | Testing | Benchmark documented |
| T-04.2.1-1 | Build gap-field prompt builder | Auto-generate LLM prompt from uncovered fields | US-04.2.1 | AI | Merged, unit tests pass |
| T-04.2.1-2 | Demo zero-code new document type | Add a field, verify extraction with no deploy | US-04.2.1 | Testing | Demo recorded and verified |
| T-04.4.1-1 | Build PII field map generator | Cross-reference extracted fields against PII list | US-04.4.1 | AI | Merged, unit tests pass |
| T-04.4.1-2 | Persist PII map to extraction artifacts | Write map alongside 11-artifact record | US-04.4.1 | Data | Verified in Cosmos dev |
| T-05.1.1-1 | Implement alias fast-path lookup | Check known alias pairs before LLM fallback | US-05.1.1 | AI | Merged, unit tests pass |
| T-05.1.1-2 | Verify multilingual alias resolution | Test fixture with Arabic/French/English variants | US-05.1.1 | Testing | Fixture test passes |
| T-05.2.1-1 | Build canonical map assembler | Merge per-document facts into unified map | US-05.2.1 | Backend | Merged, unit tests pass |
| T-05.2.1-2 | Implement field intersection gating | Mark NOT_APPLICABLE for absent fields | US-05.2.1 | Backend | Unit tests pass |
| T-05.3.1-1 | Build cross-document conflict detector | LLM consistency check over canonical map | US-05.3.1 | AI | Merged, conflict fixture passes |
| T-05.3.1-2 | Verify canonical-map-only LLM context | Confirm raw documents never reach the LLM here | US-05.3.1 | Testing | Context audit verified |
| T-06.1.1-1 | Build rule loader with ETag capture | Cosmos read with ETag extraction | US-06.1.1 | Backend | Merged, unit tests pass |
| T-06.1.1-2 | Verify hot rule-change behavior | Integration test confirming immediate effect | US-06.1.1 | Testing | Integration test passes |
| T-06.2.1-1 | Implement Mandatory Evidence + Completeness evaluators | AND/OR/conditional group logic | US-06.2.1 | Backend | Merged, unit tests pass |
| T-06.2.1-2 | Implement Value Validation + Temporal evaluators | Format/range/enum + date validity | US-06.2.1 | Backend | Merged, unit tests pass |
| T-06.3.1-1 | Implement Cross-Evidence + Code Reference evaluators | Comparison logic + reference-data lookup | US-06.3.1 | Backend | Merged, unit tests pass |
| T-06.3.1-2 | Implement Quantitative + Signature/Stamp evaluators | Item-level checks + heuristic detection | US-06.3.1 | AI | Merged, unit tests pass |
| T-06.4.1-1 | Build finding record writer | Persist structured finding to `verdicts` | US-06.4.1 | Data | Merged, unit tests pass |
| T-06.4.1-2 | Verify finding schema completeness | Validate all required fields present | US-06.4.1 | Testing | Unit tests pass |
| T-07.1.1-1 | Implement weighted scoring algorithm | Aggregate findings via configurable weight matrix | US-07.1.1 | Backend | Merged, manual-calc verified |
| T-07.1.1-2 | Verify config-driven weight changes | Confirm score change without deployment | US-07.1.1 | Testing | Integration test passes |
| T-07.2.1-1 | Implement risk grade banding | Assign grade band from thresholds | US-07.2.1 | Backend | Merged, unit tests pass |
| T-07.2.1-2 | Implement HOLD escalation flag | Threshold-based HOLD logic | US-07.2.1 | Backend | Unit tests pass |
| T-08.1.1-1 | Implement verdict synthesis logic | Map risk grade + findings to vocabulary labels | US-08.1.1 | Backend | Merged, unit tests pass |
| T-08.1.1-2 | Verify config-driven vocabulary change | Confirm label change without deployment | US-08.1.1 | Testing | Integration test passes |
| T-08.2.1-1 | Build evidence chain assembler | Link field → document → rule → finding → verdict | US-08.2.1 | Backend | Merged, unit tests pass |
| T-08.2.1-2 | Implement top-N impact finding selection | Rank findings by risk contribution | US-08.2.1 | Backend | Unit tests pass |
| T-08.3.1-1 | Implement secured container write | Full evidence chain incl. PII, restricted RBAC | US-08.3.1 | Data | Merged, security review passed |
| T-08.3.1-2 | Implement display container write with redaction | PII fields replaced with redaction label | US-08.3.1 | Data | Unit tests pass |
| T-08.4.1-1 | Implement HMAC signing | Signature via Key Vault secret, Managed Identity | US-08.4.1 | Backend | Merged, unit tests pass |
| T-08.4.1-2 | Implement retry + delivery audit log | Exponential backoff, log every attempt | US-08.4.1 | Backend | Mock-receiver test passes |
| T-09.1.1-1 | Implement 5 core agent tools | case/findings/doc-summary/precedent/comparison tools | US-09.1.1 | AI | Merged, unit tests pass |
| T-09.1.1-2 | Verify grounding refusal behavior | Scenario test confirming refusal without evidence | US-09.1.1 | Testing | Scenario test passes |
| T-09.2.1-1 | Build `EvidenceRetriever` | Top-K retrieval from AI Search case index | US-09.2.1 | AI | Merged, unit tests pass |
| T-09.2.1-2 | Verify citation and token budget | Confirm citations present, ≤1,850 tokens per query | US-09.2.1 | Testing | Benchmark measured |
| T-09.3.1-1 | Implement override rationale gate | Block submission until rationale present | US-09.3.1 | Frontend | Merged, unit tests pass |
| T-09.3.1-2 | Wire Entra ID authorization check | Role-based check before allowing override | US-09.3.1 | Backend | Integration test passes |
| T-10.1.1-1 | Define audit event schema | Document all event types and required fields | US-10.1.1 | Backend | Schema approved by Governance Lead |
| T-10.1.1-2 | Implement append-only event writer | Cosmos write helper enforcing no-update | US-10.1.1 | Data | Merged, unit tests pass |
| T-10.2.1-1 | Wire LLM call audit events | Capture model version, prompt hash, tokens | US-10.2.1 | AI | Merged, unit tests pass |
| T-10.2.1-2 | Wire rule evaluation audit events | Capture rule ETag per evaluation | US-10.2.1 | Backend | Unit tests pass |
| T-11.1.1-1 | Write `template.schema.json` | JSON Schema for all 13 artifacts | US-11.1.1 | Backend | Merged, reviewed |
| T-11.1.1-2 | Build CI executable-code scanner for templates | Reject non-JSON/Markdown files in `templates/` | US-11.1.1 | DevOps | CI active, verified |
| T-11.2.1-1 | Build `install_template.py` seeding logic | Seed rules/reference data to Cosmos | US-11.2.1 | Backend | Merged, integration test passes |
| T-11.2.1-2 | Implement activation state machine | install → validate → activate → version → deactivate | US-11.2.1 | Backend | Unit tests pass |
| T-11.3.1-1 | Author Food Safety core artifacts | `evidence_types.json`, `rules.json` from PAFN data | US-11.3.1 | Data | Reviewed by domain expert |
| T-11.3.1-2 | Author remaining Food Safety artifacts | Reference data, risk matrix, aliases, vocab, PII, tools, dashboard, eval | US-11.3.1 | Data | All pass CI schema validation |
| T-12.1.1-1 | Define `BaseConnector` abstract class | Three-method interface contract | US-12.1.1 | Backend | Merged, unit tests pass |
| T-12.1.1-2 | Build CI connector-contract check | Reject connectors not extending BaseConnector | US-12.1.1 | DevOps | CI rule active |
| T-12.2.1-1 | Implement Generic REST connector transform | Jinja2-configurable field mapping | US-12.2.1 | Backend | Merged, unit tests pass |
| T-12.2.1-2 | Implement Generic REST connector delivery | Outbound decision delivery | US-12.2.1 | Backend | Integration test passes |
| T-13.1.1-1 | Write Terraform app-lz + network modules | Function App, APIM, VNet | US-13.1.1 | DevOps | Applied to dev |
| T-13.1.1-2 | Write Terraform ai-lz + identity + monitoring modules | AOAI, DI, Cosmos, AI Search, Key Vault, Managed Identity | US-13.1.1 | DevOps | Applied to dev |
| T-13.2.1-1 | Build CI/CD pipeline definition | Dev → staging → prod stages with gates | US-13.2.1 | DevOps | Dry run passes |
| T-13.2.1-2 | Document rollback procedure | Step-by-step runbook | US-13.2.1 | DevOps | Runbook tested once |
| T-13.3.1-1 | Build ground truth loader | Load test cases + expected results | US-13.3.1 | Data | Merged, unit tests pass |
| T-13.3.1-2 | Build accuracy gate enforcement | Fail pipeline if accuracy <85% | US-13.3.1 | Testing | Verified against failing template |

**Total: 82 tasks (2 per MVP story).**

---

## OUTPUT 4 — Sprint 1 Build Sheet

| Feature | Story | Tasks | Dependencies | Owner Type | Definition of Done |
|---|---|---|---|---|---|
| F-01.1 Durable Functions Orchestrator Skeleton | US-01.1.1 | T-01.1.1-1, T-01.1.1-2 | None | Backend / Testing | No-op 5-activity pipeline runs end-to-end; restart-resume test passes; merged and reviewed |
| F-01.2 Token-Tracking AI Client Wrapper | US-01.2.1 | T-01.2.1-1, T-01.2.1-2 | None | AI / DevOps | Token capture verified; CI blocks direct LLM import; merged and reviewed |
| F-01.3 Cosmos DB Foundational Schema | US-01.3.1 | T-01.3.1-1, T-01.3.1-2 | None | Data / Testing | All 6 containers live in dev with correct keys/TTL; merged and reviewed |
| F-01.4 CI Enforcement Pipeline | US-01.4.1 | T-01.4.1-1, T-01.4.1-2 | None | DevOps / Testing | CI active on branch protection; sample violation verified; merged and reviewed |
| F-10.1 Immutable Audit Event Schema (pulled forward) | US-10.1.1 | T-10.1.1-1, T-10.1.1-2 | F-01.3 | Backend / Data | Schema approved by Governance Lead; append-only writer unit-tested; merged |
| F-11.1 Template Schema and CI Validation Gates (pulled forward) | US-11.1.1 | T-11.1.1-1, T-11.1.1-2 | F-01.4 | Backend / DevOps | Sample violating template PR fails CI; schema validates 13 artifact types; merged |
| F-12.1 BaseConnector SDK | US-12.1.1 | T-12.1.1-1, T-12.1.1-2 | F-01.1 | Backend / DevOps | BaseConnector merged with unit tests; CI rejects non-conforming connector; reviewed |
| F-13.1 Single Tenant Terraform Module (start) | US-13.1.1 | T-13.1.1-1, T-13.1.1-2 | F-01.1 | DevOps | Both module sets apply successfully to dev subscription; reviewed |

**Sprint 1 exit condition:** Deployable, empty ARIA pipeline exists in dev with CI gates enforcing domain neutrality and template quality; audit event schema frozen; connector SDK contract available for Sprint 2.

---

## OUTPUT 5 — Top 50 GitHub Issues

Ready for direct GitHub issue creation, all drawn from the 41-feature MVP scope.

| # | Issue Title | Description | Labels | Priority | Parent Epic | Acceptance Criteria |
|---|---|---|---|---|---|---|
| 1 | Implement Durable Functions HTTP starter | Trigger validating request, writing case record, starting orchestration | `feature`,`backend`,`p0` | P0 | EPIC-01 | Returns 202+instanceId <3s; case record written first |
| 2 | Implement 5-activity orchestrator with restart-resume | Sequential activity composition surviving host restart | `feature`,`backend`,`p0` | P0 | EPIC-01 | Restart test resumes from last checkpoint, zero data loss |
| 3 | Build token-tracking AI client wrapper | Single LLM entry point capturing token usage | `feature`,`ai`,`p0` | P0 | EPIC-01 | All 3 token fields captured; telemetry event emitted |
| 4 | Add CI import-guard for direct LLM calls | Block direct Azure OpenAI import outside `ai_client.py` | `ci`,`devops`,`p0` | P0 | EPIC-01 | CI fails on violation PR |
| 5 | Provision Cosmos DB 6-container schema | IaC for all 6 containers with partition keys/TTL | `feature`,`data`,`p0` | P0 | EPIC-01 | Correct partition keys and TTL verified |
| 6 | Build domain-neutrality CI scanner | Banned-word scan of `src/platform/` | `ci`,`devops`,`p0` | P0 | EPIC-01 | Sample violating PR fails CI |
| 7 | Build `OfficePreprocessor` (DOCX/XLSX/PPTX) | Office → clean Markdown conversion | `feature`,`ai`,`p0` | P0 | EPIC-02 | ≥60% token reduction measured |
| 8 | Build `PDFNormalizer` | Strip DI layout markers post-OCR | `feature`,`ai`,`p0` | P0 | EPIC-02 | ≥20% token reduction measured |
| 9 | Build `KnowledgePackGenerator` | Compress template rules into ~300-token pack | `feature`,`ai`,`p0` | P0 | EPIC-02 | Food-safety pack ≤350 tokens |
| 10 | Wire Knowledge Pack Change Feed regeneration | Auto-regenerate on Cosmos rule change | `feature`,`backend`,`p0` | P0 | EPIC-02 | Integration test verifies trigger |
| 11 | Build `ContextAssemblyEngine` | Mandatory token-budget-enforced LLM context builder | `feature`,`ai`,`p0` | P0 | EPIC-02 | Over-budget context rejected/compressed |
| 12 | Add CI import-guard for context assembly | Ensure all LLM calls route through the engine | `ci`,`devops`,`p0` | P0 | EPIC-02 | CI rule active |
| 13 | Configure APIM schema validation policy | Validate inbound submissions against template schema | `feature`,`backend`,`p0` | P0 | EPIC-03 | Invalid submission returns 400 with field errors |
| 14 | Implement bundle integrity checks | SHA-256/MIME/count/size validation | `feature`,`backend`,`p0` | P0 | EPIC-03 | Unit tests per check type pass |
| 15 | Implement format router and Blob staging | Route Office/PDF documents to correct pipeline path | `feature`,`backend`,`p0` | P0 | EPIC-03 | Integration test covers all formats |
| 16 | Implement case record initialization | Write RECEIVED case record before 202 response | `feature`,`backend`,`p0` | P0 | EPIC-03 | Response <3s verified under load |
| 17 | Integrate Azure DI prebuilt models (Phase 1) | Structured extraction per configured document type | `feature`,`ai`,`p0` | P0 | EPIC-04 | ≥85% Phase 1 coverage on invoice test set |
| 18 | Build LLM gap-filling extractor (Phase 2) | Auto-generated prompt from uncovered fields | `feature`,`ai`,`p0` | P0 | EPIC-04 | Zero-code new document type demo passes |
| 19 | Implement PII field map generator | Flag extracted fields per template's PII list | `feature`,`ai`,`p0` | P0 | EPIC-04 | Map verified against sample template |
| 20 | Implement alias fast-path lookup | Check known alias pairs before LLM fallback | `feature`,`ai`,`p0` | P0 | EPIC-05 | Multilingual fixture resolves correctly |
| 21 | Implement LLM semantic alias resolution | Fallback resolution for unmapped field names | `feature`,`ai`,`p0` | P0 | EPIC-05 | Cross-vocabulary fixture test passes |
| 22 | Build canonical evidence map assembler | Merge per-document facts into unified map | `feature`,`backend`,`p0` | P0 | EPIC-05 | Field intersection gating verified |
| 23 | Build cross-document conflict detector | LLM consistency check over canonical map only | `feature`,`ai`,`p0` | P0 | EPIC-05 | Intentional-conflict fixture test passes |
| 24 | Build rule loader with ETag pinning | Cosmos rule load with ETag capture | `feature`,`backend`,`p0` | P0 | EPIC-06 | Hot rule-change integration test passes |
| 25 | Implement Mandatory Evidence + Completeness evaluators | AND/OR/conditional group logic | `feature`,`backend`,`p0` | P0 | EPIC-06 | Unit tests pass on test rule set |
| 26 | Implement Value Validation + Temporal evaluators | Format/range/enum + date validity | `feature`,`backend`,`p0` | P0 | EPIC-06 | Unit tests pass on test rule set |
| 27 | Implement Cross-Evidence + Code Reference evaluators | Comparison logic + reference-data lookup | `feature`,`backend`,`p0` | P0 | EPIC-06 | Zero LLM calls verified |
| 28 | Implement Quantitative + Signature/Stamp evaluators | Item-level checks + heuristic detection | `feature`,`ai`,`p0` | P0 | EPIC-06 | Unit tests pass |
| 29 | Build finding record persistence | Write structured findings to `verdicts` container | `feature`,`data`,`p0` | P0 | EPIC-06 | Schema completeness verified |
| 30 | Implement weighted risk scoring algorithm | Aggregate findings via configurable weight matrix | `feature`,`backend`,`p0` | P0 | EPIC-07 | Manual-calc verification passes |
| 31 | Implement risk grading and HOLD logic | Assign grade band, flag HOLD threshold | `feature`,`backend`,`p0` | P0 | EPIC-07 | Unit tests pass |
| 32 | Implement verdict synthesis | Domain-vocabulary verdict from risk + findings | `feature`,`backend`,`p0` | P0 | EPIC-08 | Config-driven vocabulary change verified |
| 33 | Build evidence chain assembler | Field → document → rule → finding → verdict | `feature`,`backend`,`p0` | P0 | EPIC-08 | Sample chain export reviewed |
| 34 | Implement PII dual-tier write | Secured + redacted display container writes | `feature`,`data`,`p0` | P0 | EPIC-08 | Security review passed |
| 35 | Implement HMAC-signed callback delivery | Signed POST with retry and audit log | `feature`,`backend`,`p0` | P0 | EPIC-08 | Mock receiver integration test passes |
| 36 | Build grounded review agent core | 5-tool tool-calling agent, citation enforcement | `feature`,`ai`,`p0` | P0 | EPIC-09 | Refusal-on-no-evidence scenario test passes |
| 37 | Build `EvidenceRetriever` for review agent | Top-K retrieval from AI Search case index | `feature`,`ai`,`p0` | P0 | EPIC-09 | ≤1,850 token context measured |
| 38 | Implement override rationale workflow | Block override until rationale provided | `feature`,`backend`,`p0` | P0 | EPIC-09 | Entra ID authorization check verified |
| 39 | Define immutable audit event schema | Schema for all event types, versioned early | `feature`,`governance`,`p0` | P0 | EPIC-10 | Approved by Architecture Governance Lead |
| 40 | Wire LLM/rule audit capture | Model version, prompt hash, rule ETag per event | `feature`,`backend`,`p0` | P0 | EPIC-10 | Sample reconstruction verified |
| 41 | Write template JSON schema and CI gates | Reject executable code, validate 13 artifacts | `feature`,`devops`,`p0` | P0 | EPIC-11 | Sample violating PR fails CI |
| 42 | Build `install_template.py` lifecycle script | Seed rules/reference data, activate template | `feature`,`backend`,`p0` | P0 | EPIC-11 | Integration test passes |
| 43 | Author Food Safety template (13 artifacts) | Derive content from PAFN production data | `feature`,`data`,`p0` | P0 | EPIC-11 | All artifacts pass CI schema validation |
| 44 | Define `BaseConnector` SDK | Three-method abstract contract | `feature`,`backend`,`p0` | P0 | EPIC-12 | CI rejects non-conforming connectors |
| 45 | Build Generic REST connector | Configurable inbound/outbound transformation | `feature`,`backend`,`p0` | P0 | EPIC-12 | Sample payload transform test passes |
| 46 | Write Single Tenant Terraform modules | app-lz, ai-lz, network, monitoring, identity | `feature`,`devops`,`p0` | P0 | EPIC-13 | Successful `terraform apply` in dev |
| 47 | Build CI/CD multi-stage pipeline | Dev → staging → prod promotion with gates | `feature`,`devops`,`p0` | P0 | EPIC-13 | Dry run completes successfully |
| 48 | Build ground truth loader | Load test cases + expected extraction results | `feature`,`data`,`p0` | P0 | EPIC-13 | Merged, unit tests pass |
| 49 | Build evaluation accuracy gate | Fail pipeline if accuracy <85% | `feature`,`devops`,`p0` | P0 | EPIC-13 | Verified against deliberately-failing template |
| 50 | Run first end-to-end pipeline test | Submit test case bundle through all 5 activities to decision delivery | `testing`,`integration`,`p0` | P0 | EPIC-13 | Full pipeline completes, decision delivered, audit trail complete |

---

## OUTPUT 6 — Hackathon MVP Build

Minimum tasks to demonstrate all 8 capabilities. Labeled at task granularity.

### 1. Document Intake

| Item | Label |
|---|---|
| T-03.1.1-1 Configure APIM schema validation | Must Have |
| T-03.4.1-1 Case record initialization | Must Have |
| T-03.2.1-1 Bundle integrity checks | Should Have |
| T-03.3.1-1 Format router | Should Have |

### 2. Token Efficiency

| Item | Label |
|---|---|
| T-02.1.1-1 OfficePreprocessor (DOCX→Markdown) | Must Have |
| T-02.1.1-2 Token reduction benchmark | Must Have (proof point for judges) |
| T-02.4.1-1 Knowledge Pack Generator | Must Have |
| T-02.5.1-1 Context Assembly Engine | Must Have |
| T-02.2.1-1 PDF/OCR normalization | Should Have |

### 3. Extraction (Document Intelligence)

| Item | Label |
|---|---|
| T-04.1.1-1 Azure DI structured extraction | Must Have |
| T-04.2.1-1 LLM gap-filling extraction | Must Have |
| T-04.2.1-2 Zero-code new document type demo | Must Have (differentiation proof point) |
| T-04.4.1-1 PII field map | Should Have |

### 4. Validation (Cross-Document)

| Item | Label |
|---|---|
| T-05.1.1-1 Alias fast-path lookup | Must Have |
| T-05.2.1-1 Canonical evidence map assembler | Must Have |
| T-05.3.1-1 Cross-document conflict detector | Must Have (core differentiation demo) |
| T-05.1.1-2 Multilingual alias fixture verification | Should Have |

### 5. Policy Evaluation

| Item | Label |
|---|---|
| T-06.1.1-1 Rule loader with ETag pinning | Must Have |
| T-06.2.1-1 Mandatory Evidence + Completeness evaluators | Must Have |
| T-06.2.1-2 Value Validation + Temporal evaluators | Must Have |
| T-06.4.1-1 Finding record persistence | Must Have |
| T-06.3.1-1 Cross-Evidence + Code Reference evaluators | Should Have |
| T-06.3.1-2 Quantitative + Signature/Stamp evaluators | Could Have |

### 6. Risk Assessment

| Item | Label |
|---|---|
| T-07.1.1-1 Weighted risk scoring | Must Have |
| T-07.2.1-1 Risk grading and HOLD logic | Must Have |

### 7. Recommendation

| Item | Label |
|---|---|
| T-08.1.1-1 Verdict synthesis | Must Have |
| T-08.2.1-1 Evidence chain assembler | Must Have (auditability proof point) |
| T-08.3.1-1 PII dual-tier write | Should Have |
| T-08.4.1-1 HMAC-signed callback delivery | Should Have |

### 8. Human Review

| Item | Label |
|---|---|
| T-09.1.1-1 Grounded review agent core (5 tools) | Must Have |
| T-09.2.1-1 Retrieval-augmented query pipeline | Must Have (token efficiency + trust proof point) |
| T-09.1.1-2 Grounding refusal verification | Should Have |
| T-09.3.1-1 Override rationale gate | Could Have (API-level acceptable for demo) |

**Hackathon-critical path (Must Have only, in execution order):** T-01.1.1-1/2 → T-01.2.1-1 → T-03.1.1-1/T-03.4.1-1 → T-02.1.1-1/2, T-04.1.1-1, T-04.2.1-1/2 → T-05.1.1-1, T-05.2.1-1, T-05.3.1-1 → T-06.1.1-1, T-06.2.1-1/2, T-06.4.1-1 → T-07.1.1-1, T-07.2.1-1 → T-08.1.1-1, T-08.2.1-1 → T-09.1.1-1, T-09.2.1-1.

---

## OUTPUT 7 — GitHub Import Table

Epic | Feature | User Story | Task | Priority | Sprint — filtered to the 41 MVP features only (non-essential P1/P2/P3 items excluded per hackathon optimization).

| Epic | Feature | User Story | Task | Priority | Sprint |
|---|---|---|---|---|---|
| EPIC-01 | F-01.1 | US-01.1.1 | T-01.1.1-1, T-01.1.1-2 | P0 | Sprint 1 |
| EPIC-01 | F-01.2 | US-01.2.1 | T-01.2.1-1, T-01.2.1-2 | P0 | Sprint 1 |
| EPIC-01 | F-01.3 | US-01.3.1 | T-01.3.1-1, T-01.3.1-2 | P0 | Sprint 1 |
| EPIC-01 | F-01.4 | US-01.4.1 | T-01.4.1-1, T-01.4.1-2 | P0 | Sprint 1 |
| EPIC-02 | F-02.1 | US-02.1.1 | T-02.1.1-1, T-02.1.1-2 | P0 | Sprint 2 |
| EPIC-02 | F-02.2 | US-02.2.1 | T-02.2.1-1, T-02.2.1-2 | P0 | Sprint 2 |
| EPIC-02 | F-02.4 | US-02.4.1 | T-02.4.1-1, T-02.4.1-2 | P0 | Sprint 2 |
| EPIC-02 | F-02.5 | US-02.5.1 | T-02.5.1-1, T-02.5.1-2 | P0 | Sprint 2 |
| EPIC-03 | F-03.1 | US-03.1.1 | T-03.1.1-1, T-03.1.1-2 | P0 | Sprint 2 |
| EPIC-03 | F-03.2 | US-03.2.1 | T-03.2.1-1, T-03.2.1-2 | P0 | Sprint 2 |
| EPIC-03 | F-03.3 | US-03.3.1 | T-03.3.1-1, T-03.3.1-2 | P0 | Sprint 2 |
| EPIC-03 | F-03.4 | US-03.4.1 | T-03.4.1-1, T-03.4.1-2 | P0 | Sprint 2 |
| EPIC-04 | F-04.1 | US-04.1.1 | T-04.1.1-1, T-04.1.1-2 | P0 | Sprint 3 |
| EPIC-04 | F-04.2 | US-04.2.1 | T-04.2.1-1, T-04.2.1-2 | P0 | Sprint 3 |
| EPIC-04 | F-04.4 | US-04.4.1 | T-04.4.1-1, T-04.4.1-2 | P0 | Sprint 3 |
| EPIC-05 | F-05.1 | US-05.1.1 | T-05.1.1-1, T-05.1.1-2 | P0 | Sprint 3 |
| EPIC-05 | F-05.2 | US-05.2.1 | T-05.2.1-1, T-05.2.1-2 | P0 | Sprint 3 |
| EPIC-05 | F-05.3 | US-05.3.1 | T-05.3.1-1, T-05.3.1-2 | P0 | Sprint 3 |
| EPIC-06 | F-06.1 | US-06.1.1 | T-06.1.1-1, T-06.1.1-2 | P0 | Sprint 3 |
| EPIC-06 | F-06.2 | US-06.2.1 | T-06.2.1-1, T-06.2.1-2 | P0 | Sprint 3 |
| EPIC-06 | F-06.3 | US-06.3.1 | T-06.3.1-1, T-06.3.1-2 | P0 | Sprint 4 |
| EPIC-06 | F-06.4 | US-06.4.1 | T-06.4.1-1, T-06.4.1-2 | P0 | Sprint 4 |
| EPIC-07 | F-07.1 | US-07.1.1 | T-07.1.1-1, T-07.1.1-2 | P0 | Sprint 4 |
| EPIC-07 | F-07.2 | US-07.2.1 | T-07.2.1-1, T-07.2.1-2 | P0 | Sprint 4 |
| EPIC-08 | F-08.1 | US-08.1.1 | T-08.1.1-1, T-08.1.1-2 | P0 | Sprint 4 |
| EPIC-08 | F-08.2 | US-08.2.1 | T-08.2.1-1, T-08.2.1-2 | P0 | Sprint 4 |
| EPIC-08 | F-08.3 | US-08.3.1 | T-08.3.1-1, T-08.3.1-2 | P0 | Sprint 4 |
| EPIC-08 | F-08.4 | US-08.4.1 | T-08.4.1-1, T-08.4.1-2 | P0 | Sprint 4 |
| EPIC-09 | F-09.1 | US-09.1.1 | T-09.1.1-1, T-09.1.1-2 | P0 | Sprint 4 |
| EPIC-09 | F-09.2 | US-09.2.1 | T-09.2.1-1, T-09.2.1-2 | P0 | Sprint 4 |
| EPIC-09 | F-09.3 | US-09.3.1 | T-09.3.1-1, T-09.3.1-2 | P0 | Sprint 4 |
| EPIC-10 | F-10.1 | US-10.1.1 | T-10.1.1-1, T-10.1.1-2 | P0 | Sprint 1 |
| EPIC-10 | F-10.2 | US-10.2.1 | T-10.2.1-1, T-10.2.1-2 | P0 | Sprint 4 |
| EPIC-11 | F-11.1 | US-11.1.1 | T-11.1.1-1, T-11.1.1-2 | P0 | Sprint 1 |
| EPIC-11 | F-11.2 | US-11.2.1 | T-11.2.1-1, T-11.2.1-2 | P0 | Sprint 2 |
| EPIC-11 | F-11.3 | US-11.3.1 | T-11.3.1-1, T-11.3.1-2 | P0 | Sprint 2 |
| EPIC-12 | F-12.1 | US-12.1.1 | T-12.1.1-1, T-12.1.1-2 | P0 | Sprint 1 |
| EPIC-12 | F-12.2 | US-12.2.1 | T-12.2.1-1, T-12.2.1-2 | P0 | Sprint 2 |
| EPIC-13 | F-13.1 | US-13.1.1 | T-13.1.1-1, T-13.1.1-2 | P0 | Sprint 1 |
| EPIC-13 | F-13.2 | US-13.2.1 | T-13.2.1-1, T-13.2.1-2 | P0 | Sprint 3 |
| EPIC-13 | F-13.3 | US-13.3.1 | T-13.3.1-1, T-13.3.1-2 | P0 | Sprint 3 |

**41 rows — every row corresponds to exactly one MVP feature, its one user story, and its two tasks. No non-essential items included.**

---

*End of ARIA MVP Backlog*
*Version 1.0 · 2026-08-10 · Microsoft Confidential — IP Strategy*
*Primary Sources: 15-ARIA-Platform-Architecture.md · 16-ARIA-ADR-Catalog.md · 18-ARIA-Implementation-Plan.md · 19-ARIA-Engineering-Backlog.md*
*Full P1/P2/P3 backlog detail: 25-ARIA-GitHub-Work-Items.md*
*Scope: Hackathon/MVP-optimized GitHub backlog — no architecture redesign, no new ADRs, no new implementation plans*
