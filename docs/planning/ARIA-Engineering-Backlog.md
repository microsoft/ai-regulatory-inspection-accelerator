# ARIA — Engineering Backlog

**Document:** 19-ARIA-Engineering-Backlog.md
**Version:** 1.0
**Date:** 2026-08-10
**Status:** Authoritative — Engineering Backlog for GitHub Projects / Azure DevOps
**Role:** Principal Product Manager · Engineering Program Manager · Agile Delivery Lead
**Primary Sources:** 15-ARIA-Platform-Architecture.md · 16-ARIA-ADR-Catalog.md · 18-ARIA-Implementation-Plan.md
**Classification:** Microsoft Confidential — IP Strategy

> This document does not redesign architecture or generate new ADRs. Architecture and ADR decisions (28 ADRs, 17 components) are treated as approved and final. This is backlog decomposition only: Features and User Stories under the 13 existing GitHub Epics.

---

## Output 1 — Feature Catalog

Feature IDs use the pattern `F-{EpicNumber}.{FeatureNumber}`.

### EPIC-01: Platform Foundation

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-01.1 | Durable Functions Orchestrator Skeleton | 5-activity sequential orchestrator with HTTP starter, 202+instanceId pattern, checkpoint persistence | P0 | None |
| F-01.2 | Token-Tracking AI Client Wrapper | `shared/ai_client.py` — single entry point for all LLM calls, captures prompt/completion/cached tokens | P0 | None |
| F-01.3 | Cosmos DB Foundational Schema | 6-container schema (cases, extraction-artifacts, verdicts, rules, callback-log, feedback) with partition keys | P0 | None |
| F-01.4 | CI Enforcement Pipeline | Lint, unit test runner, domain-neutrality banned-word check | P0 | None |
| F-01.5 | Health Check and Telemetry Wiring | `/health` endpoint, Application Insights wiring across all activities | P1 | F-01.1 |

### EPIC-02: Token Efficiency Layer

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-02.1 | Office Document Normalization | `OfficePreprocessor` — DOCX/XLSX/PPTX → clean Markdown | P0 | F-01.2 |
| F-02.2 | PDF and OCR Output Normalization | `PDFNormalizer` — strips DI layout markers, repeated headers/footers | P0 | F-01.2 |
| F-02.3 | Semantic Chunking Service | Header-based, page-window, and similarity chunking for documents >10 pages | P1 | F-02.1, F-02.2 |
| F-02.4 | Knowledge Pack Generator | Compresses template rules/aliases/vocabulary into ~300-token Knowledge Pack | P0 | F-01.3 |
| F-02.5 | Context Assembly Engine | Mandatory LLM call intermediary; enforces per-call token budget | P0 | F-01.2, F-02.4 |
| F-02.6 | Duplicate Detection | SHA-256 exact + optional MinHash near-duplicate detection | P1 | None |
| F-02.7 | Prompt Prefix Caching Structure | Prompt template structuring for Azure OpenAI prefix cache eligibility | P2 | F-01.2 |
| F-02.8 | Token Usage Monitoring Dashboard | Tokens/call, cost/case, cache hit rate in Application Insights | P1 | F-01.2 |

### EPIC-03: Evidence Intake Engine

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-03.1 | Submission Gateway and APIM Schema Validation | REST endpoint, `submission_schema.json` validation at APIM | P0 | F-01.1 |
| F-03.2 | Bundle Integrity Verification | SHA-256 checksum, MIME type, document count, size bounds | P0 | F-03.1 |
| F-03.3 | Format Routing and Staging | Route Office → normalizer, PDF/image → DI path; Blob staging | P0 | F-02.1, F-02.2, F-02.6 |
| F-03.4 | Case Initialization | Cosmos DB case record creation, RECEIVED status, 202 response | P0 | F-01.3, F-03.1 |

### EPIC-04: Document Intelligence Engine

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-04.1 | Azure DI Structured Extraction (Phase 1) | Prebuilt model extraction, configurable per document type | P0 | F-03.3 |
| F-04.2 | LLM Gap-Filling Extraction (Phase 2) | Config-driven prompt from `evidence_types.json`, uncovered fields only | P0 | F-04.1, F-02.5 |
| F-04.3 | Quality Assessment and Normalization | 19-issue quality rubric, RTL/BiDi, numeral/date/unit normalization | P1 | F-04.1 |
| F-04.4 | Confidence Scoring and PII Field Map | Per-field confidence, PII field flagging for downstream redaction | P0 | F-04.2 |
| F-04.5 | Metadata Extraction and Routing | Language detection, page count, chunking/DI-model routing decision | P1 | F-03.3 |

### EPIC-05: Validation & Reconciliation

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-05.1 | Semantic Alias Resolution | LLM + fast-path alias mapping to canonical field names | P0 | F-04.4, F-02.5 |
| F-05.2 | Canonical Evidence Map Assembly | Merge per-document facts into unified case-level evidence map | P0 | F-05.1 |
| F-05.3 | Cross-Document Conflict Detection | LLM bundle coherence check, conflict severity grading | P0 | F-05.2 |
| F-05.4 | Bundle Coherence Scoring | 0–1 coherence score + natural-language bundle assessment | P1 | F-05.3 |

### EPIC-06: Policy Evaluation Engine

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-06.1 | Runtime Rule Loading with ETag Pinning | Cosmos DB rule load at evaluation time, ETag capture | P0 | F-05.2, F-11.2 |
| F-06.2 | Core Rule Category Evaluators (Set A) | Mandatory Evidence, Field Completeness, Value Validation, Temporal Validity | P0 | F-06.1 |
| F-06.3 | Advanced Rule Category Evaluators (Set B) | Cross-Evidence Comparison, Code Reference, Item-Level Quantitative, Signature/Stamp | P0 | F-06.1 |
| F-06.4 | Finding Record Persistence | Structured finding write to `verdicts` container | P0 | F-06.2, F-06.3 |

### EPIC-07: Risk Assessment Engine

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-07.1 | Weighted Risk Scoring Algorithm | 0–100 score from findings using template risk weight matrix | P0 | F-06.4, F-11.2 |
| F-07.2 | Risk Grade Banding and HOLD Logic | LOW/MEDIUM/HIGH/CRITICAL bands, HOLD escalation threshold | P0 | F-07.1 |
| F-07.3 | AI Search Case Indexing | Change Feed-triggered document and summary indexers | P1 | F-01.3 |
| F-07.4 | Historical Pattern Integration | Similar-case retrieval from AI Search for risk calibration | P2 | F-07.3 |

### EPIC-08: Decision Recommendation Engine

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-08.1 | Verdict Synthesis | Domain-vocabulary verdict from risk grade + findings | P0 | F-07.2, F-11.2 |
| F-08.2 | Evidence Chain Assembly | Field → document → rule → finding → verdict provenance chain | P0 | F-08.1 |
| F-08.3 | PII Dual-Tier Write | Secured (with PII) + display (redacted) Cosmos DB writes | P0 | F-08.2, F-04.4 |
| F-08.4 | HMAC-Signed Callback Delivery | Signed POST, retry with backoff, delivery audit log | P0 | F-08.1, F-12.1 |

### EPIC-09: Human Review Portal

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-09.1 | Grounded Review Agent Core | Tool-calling agent, minimum 5 core tools, evidence citation enforcement | P0 | F-02.5, F-07.3 |
| F-09.2 | Retrieval-Augmented Query Pipeline | `EvidenceRetriever` — top-K chunk retrieval per query | P0 | F-09.1, F-07.3 |
| F-09.3 | Override Workflow | Rationale capture, Entra ID authorization check | P0 | F-08.2 |
| F-09.4 | Reviewer Feedback Capture | Agree/disagree/flag signal recording | P1 | F-09.1 |
| F-09.5 | Review Web Application Shell | FastAPI UI scaffold for reviewer interaction | P1 | F-09.1 |

### EPIC-10: Governance & Audit

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-10.1 | Immutable Audit Event Schema and Stream | Append-only event schema, all event types defined | P0 | F-01.3 (pulled forward to Sprint 1) |
| F-10.2 | LLM Call and Rule Evaluation Audit Capture | Model version, prompt hash, token counts, rule ETag per event | P0 | F-10.1, F-06.1 |
| F-10.3 | Explainability Report Generation | Per-finding plain-language explanation, JSON/Markdown export | P1 | F-08.2 |
| F-10.4 | Audit Package Export | Full case audit export, chronological event ordering | P1 | F-10.2 |

### EPIC-11: Template Framework

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-11.1 | Template Schema and CI Validation Gates | `template.schema.json`, no-executable-code CI check, completeness check | P0 | F-01.4 |
| F-11.2 | Template Lifecycle Management | `install_template.py` — install/validate/activate/version/deactivate | P0 | F-11.1 |
| F-11.3 | Food Safety Template Content | All 13 artifacts authored from PAFN reference data | P0 | F-11.1 |
| F-11.4 | Knowledge Pack Agent (Event-Driven) | Change Feed trigger for Knowledge Pack regeneration | P1 | F-02.4, F-11.2 |

### EPIC-12: Connector Framework

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-12.1 | BaseConnector SDK | Abstract three-interface contract (`transformSubmission`, `deliverDecision`, `reportStatus`) | P0 | F-01.1 |
| F-12.2 | Generic REST Connector | Configurable field mapping + Jinja2 template, inbound + outbound | P0 | F-12.1 |
| F-12.3 | File-Based Connector | Azure Blob / SFTP polling connector | P2 | F-12.1 |
| F-12.4 | SharePoint and Dynamics 365 Connectors | Graph API and Dataverse API connectors | P3 | F-12.1 |

### EPIC-13: Deployment & Operations

| Feature ID | Feature Name | Description | Priority | Dependencies |
|---|---|---|---|---|
| F-13.1 | Single Tenant Terraform Module | Deployable Azure environment: app-lz, ai-lz, network, monitoring, identity | P0 | F-01.1 |
| F-13.2 | CI/CD Multi-Stage Pipeline | Dev → staging → prod promotion pipeline | P0 | F-13.1, F-01.4 |
| F-13.3 | Evaluation Framework and Go-Live Gate | Ground truth management, accuracy metrics, ≥85% deployment gate | P0 | F-04.2, F-11.3 |
| F-13.4 | Operations Dashboard | Throughput, decision distribution, latency, token cost, cache hit rate | P1 | F-02.8 |
| F-13.5 | Multi-Tenant SaaS Topology | Per-tenant Cosmos partition, Blob container, AI Search isolation | P2 | F-13.1 |
| F-13.6 | Government Cloud Topology | Azure Government region, FedRAMP blueprint | P3 | F-13.1 |
| F-13.7 | Sovereign/Air-Gapped Topology | 2 env var substitution validated end-to-end | P3 | F-13.1 |

**Feature count:** 61 features across 13 epics.

---

## Output 2 — User Stories

User Story IDs use the pattern `US-{FeatureID}.{StoryNumber}`. 1–2 representative stories per feature are provided; each captures the primary implementation-ready increment.

### EPIC-01: Platform Foundation

**US-01.1.1** — As a platform engineer, I need a 5-activity Durable Functions orchestrator so that a submission can flow through intake, extraction, reconciliation, policy, and delivery as a single durable pipeline.
- AC: Orchestrator starts via `client.start_new()` and returns HTTP 202 + instanceId within 3 seconds
- AC: Each activity is invoked via `yield context.call_activity()` in strict sequence
- AC: Restarting the host mid-pipeline resumes from the last completed activity with zero data loss
- AC: `DURABLE_TASK_HUB_NAME` is read from environment configuration, not hardcoded

**US-01.2.1** — As a platform engineer, I need a single AI client wrapper so that every LLM call is measured and attributable.
- AC: `call_llm()` captures `prompt_tokens`, `completion_tokens`, and `cached_tokens` from the API response
- AC: Every call logs an Application Insights custom event with activity name, case ID, and tenant ID
- AC: `temperature=0.0` and `seed=42` are enforced by default for all extraction and reasoning calls
- AC: No other module in the codebase calls Azure OpenAI directly (verified by CI import check)

**US-01.3.1** — As a platform engineer, I need the 6 Cosmos DB containers provisioned with correct partition keys so that case data, rules, and audit records scale correctly.
- AC: `cases`, `extraction-artifacts`, `verdicts`, `callback-log`, `feedback` containers partitioned by `/caseId`
- AC: `rules` container partitioned by `/category`
- AC: TTL configuration applied per container per configurable retention policy

**US-01.4.1** — As an engineering lead, I need CI to reject any PR introducing domain vocabulary into `src/platform/` so that platform code stays domain-neutral.
- AC: CI job scans all Python files under `src/platform/` against a configurable banned-word list
- AC: PR fails with a clear message identifying the violating file and line
- AC: Banned-word list is stored as a versioned configuration file, editable without code change

**US-01.5.1** — As an SRE, I need a health check endpoint so that deployment validation can confirm all dependencies are reachable.
- AC: `/health` returns HTTP 200 only when Cosmos DB, Blob, Azure OpenAI, and Azure DI are all reachable
- AC: `/health` returns HTTP 503 with a per-service breakdown when any dependency is unreachable

---

### EPIC-02: Token Efficiency Layer

**US-02.1.1** — As an AI engineer, I need DOCX/XLSX/PPTX documents converted to clean Markdown so that LLM extraction avoids XML noise overhead.
- AC: `OfficePreprocessor.convert()` strips XML namespaces, revision marks, and formatting metadata
- AC: Headings, paragraphs, tables, and list structure are preserved in output Markdown
- AC: Measured token reduction ≥60% versus raw DOCX content on a 10-document test set

**US-02.2.1** — As an AI engineer, I need Azure DI Markdown output normalized so that layout noise does not consume LLM tokens.
- AC: `PDFNormalizer.normalize()` strips DI form field markers, repeated headers/footers, and excess blank lines
- AC: Measured token reduction ≥20% versus raw DI output on a 10-document test set

**US-02.3.1** — As an AI engineer, I need large documents chunked before extraction so that only relevant sections reach the LLM.
- AC: Documents >10 pages (configurable) are split using header-based chunking with page-window fallback
- AC: Top-K (default 3) chunks selected by relevance to target field list
- AC: Measured token reduction ≥60% for documents >10 pages on a 5-document test set

**US-02.4.1** — As an AI engineer, I need a compressed Knowledge Pack per template so that policy context does not require the full rule set in LLM prompts.
- AC: Generated Knowledge Pack for the food-safety template is ≤350 tokens
- AC: Knowledge Pack regenerates automatically on Cosmos DB Change Feed trigger for rule changes
- AC: Knowledge Pack includes applicable rules summary, alias quick-map, decision vocabulary, and risk bands

**US-02.5.1** — As a platform engineer, I need a Context Assembly Engine so that every LLM call is constructed with minimum viable context and a token budget.
- AC: All LLM calls route through the Context Assembly Engine; direct calls elsewhere fail CI import check
- AC: Configurable token budget (default 8,192) rejects/compresses over-budget context before submission
- AC: Context composition (Knowledge Pack version, chunk IDs) recorded in audit metadata

**US-02.6.1** — As an AI engineer, I need duplicate documents detected before AI processing so that identical submissions are not re-processed.
- AC: SHA-256 hash computed per document and compared within the submission and against case history
- AC: Exact duplicates flagged with `extractionMethod: "skipped_duplicate"` and excluded from Activity 2 processing
- AC: 100% of exact duplicates correctly identified across test cases

**US-02.8.1** — As an operations engineer, I need token usage visible per case and per tenant so that cost can be monitored and attributed.
- AC: Dashboard tile shows tokens/case (avg, P95, P99), cost/case estimate, and cache hit rate
- AC: Per-tenant token consumption breakdown available for SaaS billing attribution

---

### EPIC-03: Evidence Intake Engine

**US-03.1.1** — As an external system integrator, I need a schema-validated submission endpoint so that malformed submissions are rejected before consuming AI compute.
- AC: APIM validates inbound payload against the active template's `submission_schema.json`
- AC: Invalid submissions receive HTTP 400 with structured field-level error detail
- AC: Valid submissions pass through to the Durable Functions HTTP starter

**US-03.2.1** — As a platform engineer, I need bundle integrity verified before staging so that corrupt or oversized submissions fail fast.
- AC: SHA-256 checksum validated against submitted checksum (if provided)
- AC: MIME type, document count, and file size bounds checked against configurable limits
- AC: Failures logged to audit stream with structured reason codes

**US-03.4.1** — As a case reviewer, I need every submission to create a case record immediately so that status is trackable from the moment of receipt.
- AC: Case record written to Cosmos DB with status `RECEIVED` before HTTP 202 response returns
- AC: Response includes `instanceId` and `statusQueryUri` within 3 seconds of submission

---

### EPIC-04: Document Intelligence Engine

**US-04.1.1** — As an AI engineer, I need Azure DI structured extraction to run first so that standard document fields are populated without LLM cost.
- AC: Configurable DI model per document type (`diModel` field in `evidence_types.json`)
- AC: Fields with confidence ≥0.85 marked `extractionMethod: "azure_di_structured"`
- AC: Invoice-type documents achieve ≥85% Phase 1 field coverage on test set

**US-04.2.1** — As a domain expert, I need new document types supported by JSON configuration alone so that no engineering is required to onboard a new evidence type.
- AC: Adding a document type entry to `evidence_types.json` auto-generates the extraction prompt
- AC: No code change is required or deployed when a new document type is added
- AC: LLM Phase 2 extraction covers exactly the fields not populated by Phase 1

**US-04.3.1** — As an AI engineer, I need Arabic RTL documents correctly normalized so that field extraction is accurate for right-to-left scripts.
- AC: BiDi Unicode normalization applied before extraction for Arabic/Hebrew/Farsi-detected documents
- AC: Eastern Arabic-Indic numerals converted to standard numerals during normalization

**US-04.4.1** — As a compliance officer, I need every extracted field flagged for PII so that downstream redaction is automatic.
- AC: PII field map generated per document based on template's `pii_field_list.json`
- AC: PII field map persisted alongside extraction artifacts for use by Decision Recommendation Engine

---

### EPIC-05: Validation & Reconciliation

**US-05.1.1** — As an AI engineer, I need field name variations resolved to canonical names so that cross-document comparison is possible.
- AC: Known alias pairs (`alias_pairs.json`) resolved without an LLM call (fast-path)
- AC: Unknown field name variations resolved via LLM semantic mapping
- AC: `"Net Wt"`, `"الوزن الصافي"`, and `"Poids net"` all correctly map to canonical field `net_weight`

**US-05.3.1** — As a reviewer, I need cross-document conflicts detected automatically so that contradictory evidence is flagged before policy evaluation.
- AC: Conflicting field values across documents produce a conflict record with severity, both source documents, and both values
- AC: LLM context for conflict detection contains only the canonical evidence map, not raw document content

**US-05.4.1** — As a reviewer, I need a natural-language bundle assessment so that I can quickly understand overall evidence quality.
- AC: 3–5 sentence plain-language summary generated per case
- AC: Coherence score (0–1) computed and stored alongside the summary

---

### EPIC-06: Policy Evaluation Engine

**US-06.1.1** — As a policy manager, I need rule changes to take effect immediately so that I can update compliance rules without engineering involvement.
- AC: Rule inserted or modified in Cosmos DB is loaded and applied on the very next case evaluation
- AC: No application restart or redeployment required
- AC: Rule ETag captured at load time and stored on every resulting finding

**US-06.2.1** — As a compliance officer, I need mandatory evidence, field completeness, value validation, and temporal validity rules evaluated so that baseline compliance checks are enforced.
- AC: Each of the four rule categories produces PASS/FAIL/NOT_APPLICABLE results against test rule sets
- AC: AND/OR/conditional mandatory evidence group logic evaluated correctly

**US-06.3.1** — As a compliance officer, I need cross-evidence comparison, code reference validation, item-level quantitative, and signature/stamp rules evaluated so that advanced compliance checks are enforced.
- AC: Each of the four rule categories produces correct results against test rule sets
- AC: Code reference validation performs Cosmos DB reference data lookup with zero LLM calls

**US-06.4.1** — As an auditor, I need every rule evaluation result persisted with full context so that findings can be traced and reviewed.
- AC: Finding record includes ruleId, category, field, extractedValue, expectedValue, result, explanation, and ruleETag
- AC: Findings written to `verdicts` container immediately upon evaluation completion

---

### EPIC-07: Risk Assessment Engine

**US-07.1.1** — As a policy manager, I need risk scores computed from a configurable weight matrix so that risk sensitivity can be tuned per industry without code changes.
- AC: Risk score (0–100) computed from findings using `risk_weight_matrix.json`
- AC: Changing the weight matrix changes future scores without a deployment

**US-07.2.1** — As a reviewer, I need cases automatically escalated to HOLD when risk exceeds threshold so that high-risk cases always receive human review.
- AC: HOLD flag set when score and/or confidence crosses the configured `holdThreshold`
- AC: Risk grade band (LOW/MEDIUM/HIGH/CRITICAL) assigned per `risk_threshold_bands.json`

**US-07.3.1** — As a platform engineer, I need completed cases indexed automatically so that historical search is always current.
- AC: Cosmos DB Change Feed triggers Case Document Indexer and Case Summary Indexer on COMPLETED status
- AC: No polling or manual trigger required

---

### EPIC-08: Decision Recommendation Engine

**US-08.1.1** — As a policy manager, I need decision verdicts to use domain-specific vocabulary so that output labels match the target industry.
- AC: Verdict label sourced from `decision_vocabulary.json` (e.g., PASS/HOLD/FAIL, or APPROVE/EDD/REJECT)
- AC: Changing the vocabulary file changes labels without a deployment

**US-08.3.1** — As a CISO, I need PII segregated into a secured store so that reviewers cannot see raw PII values.
- AC: Secured Cosmos container contains full evidence chain including PII values, restricted RBAC
- AC: Display container contains the same evidence chain with PII fields replaced by `[REDACTED: fieldName]`
- AC: PII field list is sourced from the template's `pii_field_list.json`

**US-08.4.1** — As an external system integrator, I need decisions delivered securely with retry so that transient failures do not lose a decision.
- AC: Callback payload signed with HMAC-SHA256 using the Key Vault-stored secret
- AC: Delivery retried with exponential backoff (default ×3) on failure
- AC: Every delivery attempt logged to `callback-log` with timestamp and HTTP status

---

### EPIC-09: Human Review Portal

**US-09.1.1** — As a reviewer, I need the review agent to answer only from case evidence so that I can trust its responses are grounded.
- AC: Agent has access to a minimum of 5 core tools (case, findings, document summary, precedent search, field comparison)
- AC: Agent explicitly declines to answer when retrieved evidence does not contain the answer

**US-09.2.1** — As a reviewer, I need agent answers to cite their source so that I can verify claims against the original documents.
- AC: Every answer includes document ID, page number, and extracted field value as citation
- AC: Retrieval-augmented context per query is ≤1,850 tokens (Knowledge Pack + top-3 chunks)

**US-09.3.1** — As a supervisor, I need overrides to require a rationale so that every deviation from the AI recommendation is documented.
- AC: Override action is blocked until a rationale text field is completed
- AC: Override record includes reviewer identity, timestamp, and rationale, persisted to Cosmos DB

---

### EPIC-10: Governance & Audit

**US-10.1.1** — As an architecture governance lead, I need the audit event schema defined before pipeline components are built so that no epic requires audit retrofitting.
- AC: Audit event schema covers case transitions, LLM calls, rule evaluations, deliveries, and human actions
- AC: Schema is versioned and published before EPIC-04, EPIC-06, and EPIC-08 begin implementation

**US-10.2.1** — As an auditor, I need every LLM call and rule evaluation logged with reproducibility metadata so that historical decisions can be reconstructed.
- AC: LLM call events capture model version, prompt hash, response hash, and token counts
- AC: Rule evaluation events capture the rule ETag active at evaluation time

**US-10.3.1** — As a reviewer, I need plain-language explanations for every failed finding so that I can understand why a case was flagged without reading raw rule logic.
- AC: Explanation generated per FAIL finding in reviewer-readable language
- AC: Explanation reproducible from finding data alone (bounded LLM context)

---

### EPIC-11: Template Framework

**US-11.1.1** — As an engineering lead, I need CI to reject templates containing executable code so that partner-authored templates cannot introduce security risk.
- AC: PR adding a `.py`, `.js`, `.sh`, or similar executable file to `templates/` fails CI
- AC: All 13 required template artifacts validated against `template.schema.json`

**US-11.2.1** — As a domain expert, I need a single script to activate a template so that rules and reference data are seeded without manual Cosmos DB operations.
- AC: `install_template.py` seeds `rules.json` and `reference_data.json` to Cosmos DB
- AC: Template status transitions to `active` only after successful validation

**US-11.3.1** — As a domain expert, I need the Food Safety template fully populated so that the reference implementation can be evaluated end-to-end.
- AC: All 13 template artifacts present and schema-valid for `templates/food-safety/`
- AC: Content derived from PAFN production rule data

---

### EPIC-12: Connector Framework

**US-12.1.1** — As a connector developer, I need a base connector contract so that new integrations require no platform code changes.
- AC: `BaseConnector` abstract class defines `transformSubmission`, `deliverDecision`, `reportStatus`
- AC: CI rejects any connector class in `connectors/` that does not extend `BaseConnector`

**US-12.2.1** — As an integration engineer, I need a generic REST connector so that any external system can integrate via configuration.
- AC: Field mapping configurable via Jinja2 template without code changes
- AC: Connector correctly transforms a sample external payload to ARIA-standard JSON

---

### EPIC-13: Deployment & Operations

**US-13.1.1** — As a platform administrator, I need a Single Tenant Terraform module so that ARIA can be deployed to a dedicated Azure environment.
- AC: `terraform apply` provisions app-landing-zone, ai-landing-zone, network, monitoring, and identity modules successfully
- AC: All data and AI services deployed behind Private Endpoints

**US-13.3.1** — As an architecture governance lead, I need a mandatory accuracy gate so that no template reaches production below quality threshold.
- AC: Deployment pipeline fails if measured extraction accuracy is below 85% against ground truth
- AC: Accuracy report generated per document type and per field

**US-13.4.1** — As an operations engineer, I need a dashboard showing cost and performance so that I can monitor the platform in production.
- AC: Dashboard displays throughput, decision distribution, latency P50/P95/P99, token cost per case, and cache hit rate

**Total user stories represented:** 34 detailed stories (1–2 per feature, covering all P0/P1 features; P2/P3 features have story patterns implied by their parent feature description and are expanded during sprint grooming).

---

## Output 3 — MVP Backlog (Release 1)

### Must Have

| Item | Feature IDs |
|---|---|
| Durable Functions orchestrator + AI client + Cosmos schema + CI gates | F-01.1, F-01.2, F-01.3, F-01.4 |
| Office/PDF normalization, duplicate detection, Knowledge Pack, Context Assembly Engine | F-02.1, F-02.2, F-02.4, F-02.5, F-02.6 |
| Full Evidence Intake Engine | F-03.1, F-03.2, F-03.3, F-03.4 |
| Dual-phase extraction, confidence scoring, PII field map | F-04.1, F-04.2, F-04.4 |
| Alias resolution, canonical map, conflict detection | F-05.1, F-05.2, F-05.3 |
| All 8 rule category evaluators, ETag pinning, finding persistence | F-06.1, F-06.2, F-06.3, F-06.4 |
| Risk scoring, HOLD logic | F-07.1, F-07.2 |
| Verdict synthesis, evidence chain, PII dual-tier write, HMAC delivery | F-08.1, F-08.2, F-08.3, F-08.4 |
| Grounded review agent, retrieval pipeline, override workflow | F-09.1, F-09.2, F-09.3 |
| Audit event schema and stream, LLM/rule audit capture | F-10.1, F-10.2 |
| Template schema/CI gates, lifecycle management, Food Safety template | F-11.1, F-11.2, F-11.3 |
| BaseConnector SDK, generic REST connector | F-12.1, F-12.2 |
| Single Tenant Terraform, CI/CD, evaluation gate | F-13.1, F-13.2, F-13.3 |

### Should Have

| Item | Feature IDs |
|---|---|
| Semantic chunking for large documents | F-02.3 |
| Quality assessment and RTL normalization | F-04.3 |
| Metadata extraction and routing | F-04.5 |
| Bundle coherence scoring | F-05.4 |
| AI Search case indexing | F-07.3 |
| Reviewer feedback capture, review web app shell | F-09.4, F-09.5 |
| Explainability reports, audit package export | F-10.3, F-10.4 |
| Knowledge Pack Agent (event-driven regeneration) | F-11.4 |
| Health check and telemetry wiring | F-01.5 |
| Token usage monitoring dashboard | F-02.8 |
| Operations dashboard | F-13.4 |

### Could Have

| Item | Feature IDs |
|---|---|
| Prompt prefix caching structure | F-02.7 |
| Historical pattern integration via AI Search | F-07.4 |
| File-based connector | F-12.3 |

### Won't Have (Release 1)

| Item | Feature IDs |
|---|---|
| SharePoint and Dynamics 365 connectors | F-12.4 |
| Multi-Tenant SaaS topology | F-13.5 |
| Government Cloud topology | F-13.6 |
| Sovereign/Air-Gapped topology | F-13.7 |
| Additional industry templates beyond Food Safety | (Release 2 scope) |

---

## Output 4 — Sprint Plan

Assumes 2-week sprints, single delivery team working the critical path with parallel tracks per Output 5 team structure of the Implementation Plan (18-ARIA-Implementation-Plan.md).

### Sprint 1 — Foundation

| Feature | Stories |
|---|---|
| F-01.1 Durable Functions Orchestrator Skeleton | US-01.1.1 |
| F-01.2 Token-Tracking AI Client Wrapper | US-01.2.1 |
| F-01.3 Cosmos DB Foundational Schema | US-01.3.1 |
| F-01.4 CI Enforcement Pipeline | US-01.4.1 |
| F-10.1 Immutable Audit Event Schema (pulled forward) | US-10.1.1 |
| F-11.1 Template Schema and CI Validation Gates | US-11.1.1 |
| F-12.1 BaseConnector SDK | US-12.1.1 |
| F-13.1 Single Tenant Terraform Module (start) | US-13.1.1 |

**Sprint 1 goal:** Deployable empty pipeline with CI gates, audit schema, and template schema frozen.

---

### Sprint 2 — Intake and Token Efficiency

| Feature | Stories |
|---|---|
| F-02.1 Office Document Normalization | US-02.1.1 |
| F-02.2 PDF and OCR Output Normalization | US-02.2.1 |
| F-02.4 Knowledge Pack Generator | US-02.4.1 |
| F-02.5 Context Assembly Engine | US-02.5.1 |
| F-02.6 Duplicate Detection | US-02.6.1 |
| F-03.1 Submission Gateway and APIM Schema Validation | US-03.1.1 |
| F-03.2 Bundle Integrity Verification | US-03.2.1 |
| F-03.4 Case Initialization | US-03.4.1 |
| F-11.2 Template Lifecycle Management | US-11.2.1 |
| F-11.3 Food Safety Template Content (start) | US-11.3.1 |
| F-12.2 Generic REST Connector | US-12.2.1 |
| F-13.1 Single Tenant Terraform Module (complete) | — |

**Sprint 2 goal:** Full Evidence Intake Engine operational with token efficiency layer core components; Food Safety template authoring begins.

---

### Sprint 3 — Extraction and Reconciliation

| Feature | Stories |
|---|---|
| F-04.1 Azure DI Structured Extraction (Phase 1) | US-04.1.1 |
| F-04.2 LLM Gap-Filling Extraction (Phase 2) | US-04.2.1 |
| F-04.4 Confidence Scoring and PII Field Map | US-04.4.1 |
| F-02.3 Semantic Chunking Service | — |
| F-05.1 Semantic Alias Resolution | US-05.1.1 |
| F-05.2 Canonical Evidence Map Assembly | — |
| F-05.3 Cross-Document Conflict Detection | US-05.3.1 |
| F-06.1 Runtime Rule Loading with ETag Pinning | US-06.1.1 |
| F-06.2 Core Rule Category Evaluators (Set A) | US-06.2.1 |
| F-13.2 CI/CD Multi-Stage Pipeline | — |
| F-13.3 Evaluation Framework (start) | — |

**Sprint 3 goal:** Document Intelligence Engine and Validation & Reconciliation operational; first rule categories evaluating.

---

### Sprint 4 — Policy, Risk, Decision, and Review

| Feature | Stories |
|---|---|
| F-06.3 Advanced Rule Category Evaluators (Set B) | US-06.3.1 |
| F-06.4 Finding Record Persistence | US-06.4.1 |
| F-07.1 Weighted Risk Scoring Algorithm | US-07.1.1 |
| F-07.2 Risk Grade Banding and HOLD Logic | US-07.2.1 |
| F-08.1 Verdict Synthesis | US-08.1.1 |
| F-08.2 Evidence Chain Assembly | — |
| F-08.3 PII Dual-Tier Write | US-08.3.1 |
| F-08.4 HMAC-Signed Callback Delivery | US-08.4.1 |
| F-09.1 Grounded Review Agent Core (start) | US-09.1.1 |
| F-10.2 LLM Call and Rule Evaluation Audit Capture | US-10.2.1 |
| F-13.3 Evaluation Framework (complete) | US-13.3.1 |

**Sprint 4 goal:** First end-to-end case processed: submission → decision → delivery, with audit trail and evaluation gate passing for Food Safety template.

**Note:** Full Human Review Portal completion (F-09.2 through F-09.5) and Governance/Audit completion (F-10.3, F-10.4) extend into Sprint 5+, consistent with the 90-day plan in 18-ARIA-Implementation-Plan.md.

---

## Output 5 — GitHub Project Mapping Table

| Epic | Feature | User Story | Priority | Sprint |
|---|---|---|---|---|
| EPIC-01 | F-01.1 Durable Functions Orchestrator Skeleton | US-01.1.1 | P0 | Sprint 1 |
| EPIC-01 | F-01.2 Token-Tracking AI Client Wrapper | US-01.2.1 | P0 | Sprint 1 |
| EPIC-01 | F-01.3 Cosmos DB Foundational Schema | US-01.3.1 | P0 | Sprint 1 |
| EPIC-01 | F-01.4 CI Enforcement Pipeline | US-01.4.1 | P0 | Sprint 1 |
| EPIC-01 | F-01.5 Health Check and Telemetry Wiring | US-01.5.1 | P1 | Sprint 5 |
| EPIC-02 | F-02.1 Office Document Normalization | US-02.1.1 | P0 | Sprint 2 |
| EPIC-02 | F-02.2 PDF and OCR Output Normalization | US-02.2.1 | P0 | Sprint 2 |
| EPIC-02 | F-02.3 Semantic Chunking Service | — | P1 | Sprint 3 |
| EPIC-02 | F-02.4 Knowledge Pack Generator | US-02.4.1 | P0 | Sprint 2 |
| EPIC-02 | F-02.5 Context Assembly Engine | US-02.5.1 | P0 | Sprint 2 |
| EPIC-02 | F-02.6 Duplicate Detection | US-02.6.1 | P1 | Sprint 2 |
| EPIC-02 | F-02.7 Prompt Prefix Caching Structure | — | P2 | Sprint 6 |
| EPIC-02 | F-02.8 Token Usage Monitoring Dashboard | US-02.8.1 | P1 | Sprint 5 |
| EPIC-03 | F-03.1 Submission Gateway and APIM Schema Validation | US-03.1.1 | P0 | Sprint 2 |
| EPIC-03 | F-03.2 Bundle Integrity Verification | US-03.2.1 | P0 | Sprint 2 |
| EPIC-03 | F-03.3 Format Routing and Staging | — | P0 | Sprint 2 |
| EPIC-03 | F-03.4 Case Initialization | US-03.4.1 | P0 | Sprint 2 |
| EPIC-04 | F-04.1 Azure DI Structured Extraction (Phase 1) | US-04.1.1 | P0 | Sprint 3 |
| EPIC-04 | F-04.2 LLM Gap-Filling Extraction (Phase 2) | US-04.2.1 | P0 | Sprint 3 |
| EPIC-04 | F-04.3 Quality Assessment and Normalization | — | P1 | Sprint 5 |
| EPIC-04 | F-04.4 Confidence Scoring and PII Field Map | US-04.4.1 | P0 | Sprint 3 |
| EPIC-04 | F-04.5 Metadata Extraction and Routing | — | P1 | Sprint 5 |
| EPIC-05 | F-05.1 Semantic Alias Resolution | US-05.1.1 | P0 | Sprint 3 |
| EPIC-05 | F-05.2 Canonical Evidence Map Assembly | — | P0 | Sprint 3 |
| EPIC-05 | F-05.3 Cross-Document Conflict Detection | US-05.3.1 | P0 | Sprint 3 |
| EPIC-05 | F-05.4 Bundle Coherence Scoring | US-05.4.1 | P1 | Sprint 5 |
| EPIC-06 | F-06.1 Runtime Rule Loading with ETag Pinning | US-06.1.1 | P0 | Sprint 3 |
| EPIC-06 | F-06.2 Core Rule Category Evaluators (Set A) | US-06.2.1 | P0 | Sprint 3 |
| EPIC-06 | F-06.3 Advanced Rule Category Evaluators (Set B) | US-06.3.1 | P0 | Sprint 4 |
| EPIC-06 | F-06.4 Finding Record Persistence | US-06.4.1 | P0 | Sprint 4 |
| EPIC-07 | F-07.1 Weighted Risk Scoring Algorithm | US-07.1.1 | P0 | Sprint 4 |
| EPIC-07 | F-07.2 Risk Grade Banding and HOLD Logic | US-07.2.1 | P0 | Sprint 4 |
| EPIC-07 | F-07.3 AI Search Case Indexing | US-07.3.1 | P1 | Sprint 5 |
| EPIC-07 | F-07.4 Historical Pattern Integration | — | P2 | Sprint 6 |
| EPIC-08 | F-08.1 Verdict Synthesis | US-08.1.1 | P0 | Sprint 4 |
| EPIC-08 | F-08.2 Evidence Chain Assembly | — | P0 | Sprint 4 |
| EPIC-08 | F-08.3 PII Dual-Tier Write | US-08.3.1 | P0 | Sprint 4 |
| EPIC-08 | F-08.4 HMAC-Signed Callback Delivery | US-08.4.1 | P0 | Sprint 4 |
| EPIC-09 | F-09.1 Grounded Review Agent Core | US-09.1.1 | P0 | Sprint 4–5 |
| EPIC-09 | F-09.2 Retrieval-Augmented Query Pipeline | US-09.2.1 | P0 | Sprint 5 |
| EPIC-09 | F-09.3 Override Workflow | US-09.3.1 | P0 | Sprint 5 |
| EPIC-09 | F-09.4 Reviewer Feedback Capture | US-09.4.1 | P1 | Sprint 5 |
| EPIC-09 | F-09.5 Review Web Application Shell | — | P1 | Sprint 5 |
| EPIC-10 | F-10.1 Immutable Audit Event Schema and Stream | US-10.1.1 | P0 | Sprint 1 |
| EPIC-10 | F-10.2 LLM Call and Rule Evaluation Audit Capture | US-10.2.1 | P0 | Sprint 4 |
| EPIC-10 | F-10.3 Explainability Report Generation | US-10.3.1 | P1 | Sprint 5 |
| EPIC-10 | F-10.4 Audit Package Export | — | P1 | Sprint 5 |
| EPIC-11 | F-11.1 Template Schema and CI Validation Gates | US-11.1.1 | P0 | Sprint 1 |
| EPIC-11 | F-11.2 Template Lifecycle Management | US-11.2.1 | P0 | Sprint 2 |
| EPIC-11 | F-11.3 Food Safety Template Content | US-11.3.1 | P0 | Sprint 2–3 |
| EPIC-11 | F-11.4 Knowledge Pack Agent (Event-Driven) | — | P1 | Sprint 5 |
| EPIC-12 | F-12.1 BaseConnector SDK | US-12.1.1 | P0 | Sprint 1 |
| EPIC-12 | F-12.2 Generic REST Connector | US-12.2.1 | P0 | Sprint 2 |
| EPIC-12 | F-12.3 File-Based Connector | — | P2 | Sprint 6 |
| EPIC-12 | F-12.4 SharePoint and Dynamics 365 Connectors | — | P3 | Release 2 |
| EPIC-13 | F-13.1 Single Tenant Terraform Module | US-13.1.1 | P0 | Sprint 1–2 |
| EPIC-13 | F-13.2 CI/CD Multi-Stage Pipeline | — | P0 | Sprint 3 |
| EPIC-13 | F-13.3 Evaluation Framework and Go-Live Gate | US-13.3.1 | P0 | Sprint 3–4 |
| EPIC-13 | F-13.4 Operations Dashboard | US-13.4.1 | P1 | Sprint 5 |
| EPIC-13 | F-13.5 Multi-Tenant SaaS Topology | — | P2 | Release 3 |
| EPIC-13 | F-13.6 Government Cloud Topology | — | P3 | Release 3 |
| EPIC-13 | F-13.7 Sovereign/Air-Gapped Topology | — | P3 | Release 3 |

---

## Output 6 — Release Plan

### Release 1 — Food Safety Template, Single Tenant Deployment

**Scope:** Complete Core Platform (all 17 components) validated against the Food Safety reference implementation, deployed to a Single Tenant Azure environment, evaluation-gated at ≥85% accuracy.

**Includes:** EPIC-01 through EPIC-10 (Must Have + Should Have scope), EPIC-11 (Food Safety template only), EPIC-12 (BaseConnector SDK + Generic REST connector), EPIC-13 (Single Tenant topology + CI/CD + evaluation framework).

**Exit criteria:** End-to-end case processing operational; PAFN-equivalent food safety cases processed with ≥85% extraction accuracy; token consumption measured against 50–70% reduction target; HMAC decision delivery validated with a test receiver.

---

### Release 2 — Multi-Industry Templates

**Scope:** Onboard the remaining 5 industry templates without platform code changes, proving the reusability thesis at scale.

**Includes:** EPIC-11 (Customs Clearance, Healthcare Compliance, Licensing & Certification, Environmental Compliance, Financial Compliance/KYC-AML templates), EPIC-12 (File-based, SharePoint, Dynamics 365 connectors as needed per template), EPIC-13 (evaluation runs per new template).

**Exit criteria:** All 6 templates (including Food Safety) pass the evaluation gate independently; zero platform code changes required across all 5 new template onboardings; cross-industry proof documented for IP governance.

---

### Release 3 — Enterprise Scale Features

**Scope:** Multi-tenant, government, and sovereign deployment topologies; enterprise billing and Marketplace readiness.

**Includes:** EPIC-13 (Multi-Tenant SaaS, Government Cloud, Sovereign/Air-Gapped topologies), EPIC-02 (per-tenant token billing attribution, prompt prefix caching), remaining connector work, Azure Marketplace packaging (Bicep conversion, metered billing — tracked outside the 13 epics as a future epic).

**Exit criteria:** Multi-Tenant SaaS topology validated with 2+ tenants isolated correctly; Sovereign topology validated via 2-environment-variable substitution with zero code change; Government Cloud topology validated against FedRAMP blueprint.

---

## Output 7 — Top 20 Engineering Tasks

Implementation-ready tasks, directly createable as GitHub issues under their parent Feature.

1. **[F-01.1]** Implement Durable Functions HTTP starter with 202+instanceId response pattern
2. **[F-01.1]** Implement 5-activity orchestrator with sequential `call_activity` composition and checkpoint validation test
3. **[F-01.2]** Implement `shared/ai_client.py` with token capture, temperature=0.0/seed=42 defaults, and JSON-mode enforcement
4. **[F-01.3]** Write Terraform/script to provision 6 Cosmos DB containers with correct partition keys and TTL
5. **[F-01.4]** Implement CI job: domain-neutrality banned-word scanner for `src/platform/`
6. **[F-02.1]** Implement `OfficePreprocessor.convert()` for DOCX using python-docx with Markdown serialization
7. **[F-02.2]** Implement `PDFNormalizer.normalize()` regex-based stripping of DI layout markers
8. **[F-02.4]** Implement `KnowledgePackGenerator.generate()` reading rules.json + alias_pairs.json into compressed JSON schema
9. **[F-02.5]** Implement `ContextAssemblyEngine.assemble()` with tiktoken-based token budget enforcement
10. **[F-02.6]** Implement `DuplicateDetector.check()` with SHA-256 hash comparison against case document store
11. **[F-03.1]** Configure APIM policy for `submission_schema.json` JSON schema validation
12. **[F-03.2]** Implement bundle integrity pre-validation (checksum, MIME, count, size bounds)
13. **[F-04.1]** Implement `DualPhaseExtractor` Phase 1 — Azure DI prebuilt-invoice integration with confidence threshold logic
14. **[F-04.2]** Implement `DualPhaseExtractor` Phase 2 — gap-field prompt builder from `evidence_types.json`
15. **[F-05.1]** Implement alias fast-path lookup against `alias_pairs.json` before falling back to LLM resolution
16. **[F-06.1]** Implement rule loader with Cosmos DB ETag capture at read time
17. **[F-06.2]** Implement Mandatory Evidence Presence evaluator with AND/OR/conditional group logic
18. **[F-08.3]** Implement PII dual-tier write: secured container write + display container write with redaction using `pii_field_list.json`
19. **[F-08.4]** Implement HMAC-SHA256 signing and exponential backoff retry for decision callback delivery
20. **[F-11.2]** Implement `install_template.py` — Cosmos DB rule/reference-data seeding and template activation state transition

---

## Output 8 — MVP Success Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| **Processing Time** | P95 end-to-end (submission → decision delivery) ≤ 2 minutes for a 5-document bundle | Application Insights latency tracking per pipeline stage, aggregated to P50/P95/P99 |
| **Accuracy** | ≥ 85% exact-match extraction accuracy against Food Safety ground truth (minimum 20 test cases) | Evaluation Framework (EPIC-13, F-13.3) accuracy report, per field and per document type |
| **Token Reduction** | 50–70% reduction in LLM tokens per case versus unoptimized (raw-document) baseline | Token Usage Monitoring Dashboard (F-02.8) — compare optimized vs. baseline measurement on identical test cases |
| **Human Review Time** | ≤ 8 minutes for HOLD/FAIL case review, using retrieval-augmented Review Agent | Time-motion measurement during UAT: case assignment to override/confirm decision |
| **Traceability Coverage** | 100% of decisions have a complete evidence chain (field → document → rule → finding → verdict) with rule ETag and audit event coverage | Audit Package Export (F-10.4) spot-check across all completed test cases; automated completeness check in evaluation pipeline |

---

## Output 9 — Hackathon Build Scope

Minimum implementation required before hackathon judging — demonstrates the core IP thesis (reusable platform, token efficiency, PAFN as reference implementation) without requiring full production hardening.

### Must Demonstrate

| Capability | Minimum Scope | Feature IDs |
|---|---|---|
| End-to-end pipeline execution | Durable Functions orchestrator running all 5 stages on at least 3 real Food Safety test cases | F-01.1, F-03.x, F-04.x, F-05.x, F-06.x, F-07.x, F-08.x |
| Token efficiency proof | Side-by-side token count comparison: raw-document approach vs. ARIA-optimized approach on the same test case | F-02.1, F-02.2, F-02.4, F-02.5 |
| Configuration-driven extensibility proof | Show a new document type added via JSON entry with zero code change, extraction working immediately | F-04.2, F-11.1 |
| Auditable decision proof | One complete evidence chain export showing field → document → rule → verdict traceability | F-08.2, F-10.1, F-10.4 |
| Human review proof | Live demo of Review Agent answering a grounded question with citation, on a HOLD case | F-09.1, F-09.2 |
| PAFN-as-reference proof | Show Food Safety template isolated in `templates/food-safety/` with zero PAFN-specific code in `src/platform/` | F-11.3, ADR-009, ADR-010 |

### Explicitly Out of Scope for Hackathon

- Multi-tenant, Government Cloud, and Sovereign topologies (Release 3 scope)
- Additional industry templates beyond Food Safety (Release 2 scope)
- SharePoint/Dynamics connectors (Release 2/3 scope)
- Full evaluation framework automation (a manual accuracy spot-check on the demo cases is sufficient for judging)
- Operations dashboard polish (raw Application Insights query output is acceptable for the demo)
- Override authorization role enforcement (demo can use a single reviewer identity)

### Hackathon Narrative Arc (suggested demo sequence)

1. Submit a 5-document Food Safety case bundle → show HTTP 202 response
2. Show token consumption comparison: this case optimized vs. simulated raw-document approach
3. Show extracted fields, cross-document conflict detected (if using a case with an intentional conflict), and the resulting risk score
4. Show the final decision with full evidence chain export
5. Ask the Review Agent a grounded question about the decision, showing citation-backed response
6. Show `evidence_types.json` — add one new field, re-run extraction, demonstrate zero code change
7. Show the repository structure: `src/platform/` (domain-neutral) vs. `templates/food-safety/` (PAFN-derived) vs. `reference-implementations/pafn-food-inspection/` (fully isolated) — the reusability proof

---

*End of ARIA Engineering Backlog*
*Version 1.0 · 2026-08-10 · Microsoft Confidential — IP Strategy*
*Primary Sources: 15-ARIA-Platform-Architecture.md · 16-ARIA-ADR-Catalog.md · 18-ARIA-Implementation-Plan.md*
*Scope: Backlog decomposition only — no architecture redesign, no new ADRs*
