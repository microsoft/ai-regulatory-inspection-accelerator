# ARIA — Implementation Plan

**Document:** 18-ARIA-Implementation-Plan.md
**Version:** 1.0
**Date:** 2026-08-10
**Status:** Authoritative — Engineering Delivery Planning
**Role:** Principal Engineering Lead · Technical Program Manager · Platform Delivery Architect
**Primary Inputs:** 15-ARIA-Platform-Architecture.md · 16-ARIA-ADR-Catalog.md
**Assumptions:** Architecture approved · ADR catalog approved · GitHub project created · 13 epics exist (17-ARIA-GitHub-Epics.md)
**Classification:** Microsoft Confidential — IP Strategy

> This document does not redesign architecture, generate diagrams, or create user stories. It is implementation planning only: sequencing, dependencies, risk, team structure, and delivery waves for the 13 approved epics.

---

## Output 1 — Workstream Analysis

### EPIC-01: Platform Foundation

| Attribute | Detail |
|---|---|
| **Objective** | Establish the domain-neutral pipeline skeleton, shared service clients, data models, and CI enforcement that every other epic builds on |
| **Architectural Components** | Durable Functions orchestrator (C-15 orchestration) · `shared/ai_client.py` · Cosmos DB 6-container schema · `src/models/` · CI lint/domain-neutrality gate |
| **Dependencies** | None |
| **Risks** | Task hub misconfiguration blocks all downstream Durable Functions work · Cosmos DB partition key design mistakes are expensive to reverse post-data-load · CI banned-word list incomplete at launch, allowing early domain leakage |
| **Suggested Order** | 1st — must complete before any other epic starts substantive work |

---

### EPIC-02: Token Efficiency Layer

| Attribute | Detail |
|---|---|
| **Objective** | Build the cross-cutting token optimization components (normalization, chunking, Knowledge Packs, context assembly) that every AI-calling epic depends on |
| **Architectural Components** | `OfficePreprocessor` · `PDFNormalizer` · `SemanticChunker` · `KnowledgePackGenerator` · `ContextAssemblyEngine` · `DuplicateDetector` · prompt caching structure |
| **Dependencies** | EPIC-01 (`shared/ai_client.py` skeleton) |
| **Risks** | If built after EPIC-04 (Document Intelligence) instead of before, extraction code will need retrofitting — token efficiency is cheapest to build first, expensive to retrofit · Context Assembly Engine becoming a bottleneck if not designed for extensibility from day one |
| **Suggested Order** | 2nd — immediately after Platform Foundation, before any component that calls an LLM |

---

### EPIC-03: Evidence Intake Engine

| Attribute | Detail |
|---|---|
| **Objective** | Implement the submission gateway: bundle validation, duplicate detection, normalization routing, and case initialization |
| **Architectural Components** | C-01 Evidence Intake Engine · APIM schema validation (ADR-019) · Blob staging · Cosmos `cases` container |
| **Dependencies** | EPIC-01 (Platform Foundation) · EPIC-02 (OfficePreprocessor, DuplicateDetector) |
| **Risks** | APIM schema validation policy must stay synchronized with template `submission_schema.json` — manual drift risk · Bundle integrity checks (SHA-256, MIME, size) insufficiently tested against malformed/malicious payloads |
| **Suggested Order** | 3rd — first case-processing epic; unblocks all downstream pipeline stages |

---

### EPIC-04: Document Intelligence Engine

| Attribute | Detail |
|---|---|
| **Objective** | Implement dual-phase field extraction (Azure DI structured + LLM gap-filling) with chunking and normalization applied |
| **Architectural Components** | C-02 through C-06 (DI Engine, Metadata Extraction, Normalization, Markdown Conversion, Semantic Chunking) · `evidence_types.json` schema consumption |
| **Dependencies** | EPIC-03 (Evidence Intake) · EPIC-02 (SemanticChunker, ContextAssemblyEngine, PDFNormalizer) |
| **Risks** | Azure DI prebuilt model coverage gaps for non-standard document types force higher LLM Phase 2 load than planned · Field alias/data-type schema (`evidence_types.json`) extension (ADR-002 implementation note) not yet built — extraction quality depends on it · Confidence score calibration between Phase 1 (DI) and Phase 2 (LLM) requires tuning per document type |
| **Suggested Order** | 4th — the single largest engineering epic; longest lead time |

---

### EPIC-05: Validation & Reconciliation

| Attribute | Detail |
|---|---|
| **Objective** | Reconcile per-document extracted facts into a canonical evidence map and detect cross-document conflicts |
| **Architectural Components** | C-08 Cross-Document Validation Engine (also covers Data Reconciliation sub-component per Input Pack Section 5.3) · alias resolution · coherence scoring |
| **Dependencies** | EPIC-04 (extraction artifacts) · EPIC-02 (Context Assembly Engine — canonical map, not raw docs, sent to LLM) |
| **Risks** | Semantic alias resolution accuracy depends on quality of `alias_pairs.json` fast-path coverage — undercovered templates increase LLM cost and reduce reliability · Conflict severity grading thresholds are template-specific and require per-industry tuning |
| **Suggested Order** | 5th |

---

### EPIC-06: Policy Evaluation Engine

| Attribute | Detail |
|---|---|
| **Objective** | Deterministically evaluate the eight rule categories against the canonical evidence map with rule ETag pinning |
| **Architectural Components** | C-10 Policy Evaluation Engine · Cosmos `rules` container · 8 rule category evaluators |
| **Dependencies** | EPIC-05 (canonical evidence map) · EPIC-11 (template `rules.json` seed data via `install_template.py`) |
| **Risks** | Eight rule category evaluators represent significant scope — under-scoping any one category (e.g., Item-Level Quantitative) delays the whole epic · Rule ETag pinning logic must be correct on day one; retrofitting audit reproducibility after go-live is costly |
| **Suggested Order** | 6th — this is the first fully deterministic (non-LLM) stage; can start rule-category-evaluator development in parallel with EPIC-05 once canonical map schema is frozen |

---

### EPIC-07: Risk Assessment Engine

| Attribute | Detail |
|---|---|
| **Objective** | Compute weighted risk scores, integrate historical patterns via AI Search, and determine HOLD escalation |
| **Architectural Components** | C-11 Risk Assessment Engine · Azure AI Search (ADR-020) · Change Feed indexers (ADR-023 pattern) |
| **Dependencies** | EPIC-06 (policy findings) · EPIC-11 (risk weight matrix, threshold bands from template) |
| **Risks** | AI Search index schema versioning is an open architecture decision (Architecture Readiness Checklist item) — building before this is resolved risks rework · Case Document/Summary Indexers require COMPLETED cases to exist before historical pattern search has any data — cold-start problem for new deployments |
| **Suggested Order** | 7th |

---

### EPIC-08: Decision Recommendation Engine

| Attribute | Detail |
|---|---|
| **Objective** | Synthesize the final verdict, assemble the evidence chain, perform PII dual-tier write, and deliver via HMAC-signed callback |
| **Architectural Components** | C-12 Decision Recommendation Engine · PII dual-tier write (ADR-021) · HMAC delivery (ADR-008) · Connector outbound path (ADR-024) |
| **Dependencies** | EPIC-05, EPIC-06, EPIC-07 (evidence map, findings, risk score) · EPIC-12 (connector outbound interface) |
| **Risks** | PII field list (`pii_field_list.json`) completeness is template-author-dependent — an incomplete list causes unredacted PII exposure in the display store · Override authorization enforcement mechanism is an open architecture decision — building the override write path before this is resolved risks rework |
| **Suggested Order** | 8th — this is the pipeline's terminal stage; cannot start meaningfully until EPIC-05/06/07 produce stable output contracts |

---

### EPIC-09: Human Review Portal

| Attribute | Detail |
|---|---|
| **Objective** | Deliver the grounded, retrieval-augmented conversational review agent and override workflow |
| **Architectural Components** | C-13 Human Review Framework · `EvidenceRetriever` (ADR-017) · Context Assembly Engine integration · FastAPI review web app |
| **Dependencies** | EPIC-02 (ContextAssemblyEngine) · EPIC-07 (AI Search case index population) · EPIC-08 (decision + evidence chain to review) |
| **Risks** | Retrieval quality depends entirely on Azure AI Search index completeness from EPIC-04/05 — poor indexing degrades review agent accuracy · Copilot Studio integration is an open architecture decision; scope creep risk if pursued prematurely |
| **Suggested Order** | 9th — can begin UI/agent scaffolding in parallel with EPIC-08, but full integration requires EPIC-08 complete |

---

### EPIC-10: Governance & Audit

| Attribute | Detail |
|---|---|
| **Objective** | Implement the immutable audit event stream, explainability reporting, and point-in-time decision reconstruction |
| **Architectural Components** | C-14 Explainability Framework · C-15 Audit Framework · rule ETag + model version capture |
| **Dependencies** | EPIC-06 (rule ETag pinning) · EPIC-08 (decision package) |
| **Risks** | Audit event schema must be designed before EPIC-04/06/08 are built (all three emit audit events) — if this epic starts too late, retrofitting audit emission into completed components is expensive. **This is a sequencing risk, not a dependency risk** — audit event schema definition should be pulled forward even though full audit query/export tooling completes later · GDPR right-to-erasure conflict with immutable audit trail is an unresolved open decision |
| **Suggested Order** | 10th for full delivery, but **audit event schema must be defined during EPIC-01** to avoid retrofit cost |

---

### EPIC-11: Template Framework

| Attribute | Detail |
|---|---|
| **Objective** | Build the 13-artifact template package structure, CI enforcement, lifecycle management, and produce the first Food Safety template |
| **Architectural Components** | Template schema (`templates/_schema/`) · CI validation gates (ADR-025) · `install_template.py` · Knowledge Pack Generator (ADR-015, ADR-023) |
| **Dependencies** | EPIC-01 (Platform Foundation) · EPIC-02 (Knowledge Pack Generator) |
| **Risks** | Template schema must be frozen early — every downstream epic (EPIC-04 through EPIC-09) consumes template artifacts; late schema changes cascade across the whole platform · Food Safety template is the only template with existing source data (PAFN) — other 5 templates require net-new domain expert authoring effort not yet scoped |
| **Suggested Order** | Schema and CI gates: 2nd (parallel with EPIC-02) · Food Safety template content: parallel with EPIC-04–08 development (template content and pipeline code can be built concurrently once schema is frozen) |

---

### EPIC-12: Connector Framework

| Attribute | Detail |
|---|---|
| **Objective** | Build the BaseConnector SDK, isolation model, and built-in connectors (REST, File, SharePoint, Dynamics) |
| **Architectural Components** | C-16 Connector Framework · `BaseConnector` abstract class (ADR-024) |
| **Dependencies** | EPIC-01 (Platform Foundation) |
| **Risks** | Connector isolation (separate Managed Identity, no direct data access) requires infrastructure work that could be under-scoped if treated as "just an interface" — this is also an infrastructure/deployment concern, not purely a code concern | 
| **Suggested Order** | SDK and inbound REST connector: 3rd (parallel with EPIC-03, since Evidence Intake needs the inbound connector interface) · Outbound connectors: parallel with EPIC-08 |

---

### EPIC-13: Deployment & Operations

| Attribute | Detail |
|---|---|
| **Objective** | Deliver Terraform IaC, all four deployment topologies, CI/CD pipeline, evaluation framework gate, and operations dashboard |
| **Architectural Components** | 5 Terraform modules · Single Tenant / Multi-Tenant / Gov Cloud / Sovereign topologies · Evaluation framework (ADR-028) · Operations dashboard |
| **Dependencies** | All epics (wraps the complete platform) — but the **Single Tenant Terraform module and CI/CD pipeline must exist from EPIC-01** to give every other epic a deployable target for testing |
| **Risks** | Evaluation framework as a mandatory gate (ADR-028) means no template can go live without ground truth data — this is a scope item that must be planned per template, not just once · Multi-tenant Cosmos DB throughput isolation model is an open architecture decision — cannot fully build Multi-Tenant topology until resolved · Sovereign topology validation requires access to Azure Stack Hub or equivalent test environment, which may not exist yet |
| **Suggested Order** | Terraform Single Tenant module + CI/CD: 2nd (parallel with EPIC-02, needed as a deployable target early) · Evaluation framework: parallel with EPIC-04 (needed to measure extraction accuracy as soon as extraction exists) · Multi-Tenant/Gov/Sovereign topologies: last, after Single Tenant is validated in production |

---

## Output 2 — Critical Path Analysis

### Foundational Capabilities (must exist before parallel work is safe)

1. **Durable Functions orchestrator skeleton** (EPIC-01) — every activity-based epic depends on this
2. **`shared/ai_client.py` token-tracking wrapper** (EPIC-01) — every LLM-calling epic depends on this
3. **Context Assembly Engine** (EPIC-02) — every LLM-calling epic (04, 05, 09) must route through this or retrofitting is required
4. **Template schema freeze** (EPIC-11) — every downstream epic (04–09) consumes template artifacts against this schema
5. **Audit event schema definition** (pulled forward from EPIC-10 into EPIC-01) — every epic that emits audit events needs the schema early
6. **Canonical evidence map schema** (defined during EPIC-04/05 boundary) — the contract between extraction and reconciliation/policy/risk/decision

### Blocking Dependencies (hard sequence, cannot parallelize)

```
EPIC-01 → EPIC-03 → EPIC-04 → EPIC-05 → EPIC-06 → EPIC-07 → EPIC-08 → EPIC-09
                                              └──────────────────────→ EPIC-10 (audit consumption)
```

This is the single longest dependency chain in the platform (8 epics deep) and defines the critical path for time-to-first-case-processed.

### Parallelizable Activities

| Can run in parallel with | Because |
|---|---|
| EPIC-02 (Token Efficiency) ∥ EPIC-11 schema/CI ∥ EPIC-12 SDK | All three depend only on EPIC-01, not on each other |
| EPIC-11 Food Safety template content ∥ EPIC-04 through EPIC-08 pipeline code | Template JSON authoring and platform code development are independent workstreams once schema is frozen |
| EPIC-13 Terraform/CI-CD ∥ EPIC-02, EPIC-11, EPIC-12 | Infrastructure work does not depend on pipeline business logic |
| EPIC-09 Human Review UI scaffolding ∥ EPIC-08 backend | Front-end scaffolding (FastAPI shell, chat UI) can begin before the decision engine is complete; full integration waits for EPIC-08 |
| EPIC-13 Evaluation framework ∥ EPIC-04 | Evaluation tooling can be built while extraction is being built, ready to measure accuracy the moment extraction produces results |

### Architecture Bottlenecks

| Bottleneck | Why It Constrains Delivery |
|---|---|
| **Document Intelligence Engine (EPIC-04)** | Largest single epic (5 sub-components: C-02 through C-06); every downstream epic waits on its output contract |
| **Template schema stability (EPIC-11)** | Six downstream epics (04–09) consume template artifacts; any schema change after epics begin consuming it cascades rework across all six |
| **Context Assembly Engine (EPIC-02, C-08)** | Single mandatory intermediary for all LLM calls (ADR-016) — if under-resourced, it becomes a shared-component queue that slows EPIC-04, EPIC-05, and EPIC-09 simultaneously |
| **Open architecture decisions** (from 11-Architecture-Input-Pack.md Section 13.3) | Multi-tenant throughput model, AI Search index versioning, and override authorization mechanism are unresolved — any epic that touches these areas (EPIC-07, EPIC-08, EPIC-13) risks rework if it proceeds before resolution |
| **Evaluation framework as mandatory gate (ADR-028)** | No template reaches production without passing evaluation — this makes ground truth data authoring a hard blocker for go-live, not just a nice-to-have |

---

## Output 3 — MVP Scope

The minimum deployable ARIA platform is defined as: **a single-tenant deployment that processes one industry template (Food Safety) end-to-end, from submission to auditable decision, with human review capability.**

### Must Have (MVP-blocking)

| Item | Epic |
|---|---|
| Durable Functions 5-activity orchestrator | EPIC-01 |
| `shared/ai_client.py` token tracking | EPIC-01 |
| Cosmos DB 6-container schema | EPIC-01 |
| Document normalization (Office → Markdown, PDF normalization) | EPIC-02 |
| Duplicate detection | EPIC-02 |
| Context Assembly Engine (baseline — Knowledge Pack + chunking integration) | EPIC-02 |
| Evidence Intake Engine (submission, integrity check, staging) | EPIC-03 |
| Dual-phase extraction (Azure DI + LLM gap-fill) | EPIC-04 |
| Cross-document validation (conflict detection, coherence score) | EPIC-05 |
| Policy Evaluation Engine — all 8 rule categories | EPIC-06 |
| Risk Assessment Engine — weighted scoring + HOLD logic | EPIC-07 |
| Decision Recommendation Engine — verdict, evidence chain, PII dual-tier write, HMAC delivery | EPIC-08 |
| Human Review Framework — grounded Q&A, override with rationale | EPIC-09 |
| Audit event stream (immutable, ETag pinning) | EPIC-10 |
| Template Framework — schema, CI gates, Food Safety template complete | EPIC-11 |
| Generic REST connector (inbound + outbound) | EPIC-12 |
| Single Tenant Terraform deployment | EPIC-13 |
| Evaluation framework — accuracy gate for Food Safety template | EPIC-13 |

### Should Have (high value, not MVP-blocking)

| Item | Epic |
|---|---|
| Semantic chunking for large documents (only needed if MVP documents exceed 10 pages) | EPIC-02 |
| Historical pattern integration via AI Search | EPIC-07 |
| File-based connector | EPIC-12 |
| Operations dashboard (throughput, cost, latency) | EPIC-13 |
| Prompt prefix caching optimization | EPIC-02 |
| Explainability report generation (Markdown export) | EPIC-10 |

### Could Have (post-MVP, second wave)

| Item | Epic |
|---|---|
| Additional industry templates (Customs, Healthcare, Licensing, Environmental, KYC/AML) | EPIC-11 |
| SharePoint and Dynamics 365 connectors | EPIC-12 |
| Multi-Tenant SaaS topology | EPIC-13 |
| Government Cloud topology | EPIC-13 |
| Sovereign/Air-Gapped topology | EPIC-13 |
| Per-tenant token billing attribution | EPIC-02, EPIC-13 |
| Copilot Studio integration for Review Assistant | EPIC-09 |

---

## Output 4 — Recommended Delivery Waves

### Wave 1 — Foundation

**Expected platform capabilities:**
- Durable Functions orchestrator operational (no-op pipeline runs end-to-end)
- `shared/ai_client.py` with token tracking live
- Cosmos DB 6-container schema deployed
- CI pipeline enforcing domain-neutrality and template quality gates
- Token Efficiency Layer core components (normalization, duplicate detection, Context Assembly Engine skeleton)
- Template schema frozen; Food Safety template artifacts authoring begins
- Connector SDK (`BaseConnector`) defined
- Single Tenant Terraform module — deployable empty pipeline
- Audit event schema defined (not full audit tooling)

**Epics involved:** EPIC-01, EPIC-02 (core), EPIC-11 (schema + CI), EPIC-12 (SDK), EPIC-13 (Terraform skeleton)

---

### Wave 2 — Core Decision Platform

**Expected platform capabilities:**
- End-to-end case processing: submission → extraction → reconciliation → policy → risk → decision → callback delivery
- Food Safety template fully operational with real PAFN-derived rules
- Dual-phase extraction with Azure DI + LLM gap-filling
- All 8 policy rule categories evaluating correctly with ETag pinning
- Risk scoring with HOLD escalation
- PII dual-tier write and HMAC-signed decision delivery
- Evaluation framework operational — Food Safety template passes ≥85% accuracy gate

**Epics involved:** EPIC-03, EPIC-04, EPIC-05, EPIC-06, EPIC-07, EPIC-08, EPIC-11 (content), EPIC-13 (evaluation framework)

---

### Wave 3 — Human Review & Governance

**Expected platform capabilities:**
- Grounded, retrieval-augmented Review Assistant Agent live
- Override workflow with rationale capture and authorization enforcement
- Full audit trail with point-in-time reproducibility
- Explainability reports (per-finding plain-language explanations)
- Azure AI Search case history indexing operational (both indexes)
- Operations dashboard showing throughput, decision distribution, latency, token cost

**Epics involved:** EPIC-09, EPIC-10, EPIC-07 (AI Search completion), EPIC-13 (dashboard)

---

### Wave 4 — Industry Templates

**Expected platform capabilities:**
- Customs Clearance template
- Healthcare Compliance template
- Licensing & Certification template
- Environmental Compliance template
- Financial Compliance (KYC/AML) template
- Each template validated through the evaluation framework gate before activation
- Cross-template proof: zero platform code changes required for new template onboarding

**Epics involved:** EPIC-11 (5 additional templates), EPIC-12 (additional connectors as needed per template), EPIC-13 (evaluation runs per template)

---

### Wave 5 — Scale & Enterprise Readiness

**Expected platform capabilities:**
- Multi-Tenant SaaS topology with per-tenant Cosmos DB, Blob, AI Search isolation
- Government Cloud topology validated (FedRAMP blueprint)
- Sovereign/Air-Gapped topology validated (2 env var substitution proven end-to-end)
- Per-tenant token consumption billing attribution
- Azure Marketplace packaging (Bicep conversion, metered billing)
- SharePoint and Dynamics 365 connectors production-ready
- Semantic chunking and prompt caching fully tuned across all templates

**Epics involved:** EPIC-13 (all remaining topologies), EPIC-02 (billing attribution), EPIC-12 (remaining connectors)

---

## Output 5 — Team Structure

| Team | Primary Epics | Composition Guidance |
|---|---|---|
| **Platform Team** | EPIC-01, EPIC-06, EPIC-13 | Senior Azure Functions/Durable Functions engineers · Cosmos DB specialist · Terraform/IaC engineer |
| **AI & Reasoning Team** | EPIC-02, EPIC-04, EPIC-05 | AI engineers with Azure OpenAI + Azure DI experience · prompt engineering specialist · token/cost optimization specialist |
| **Decision & Risk Team** | EPIC-07, EPIC-08 | Engineers with risk modeling / weighted scoring experience · integration engineer for callback delivery |
| **Governance Team** | EPIC-10, evaluation framework in EPIC-13 | Compliance-minded engineers · data quality / evaluation framework specialist · Responsible AI reviewer |
| **Front-End Team** | EPIC-09 | FastAPI/web engineers · conversational UX designer · Entra ID integration engineer |
| **Integration Team** | EPIC-03, EPIC-12 | API/connector engineers · APIM specialist · partner integration liaison |
| **Template & Domain Team** | EPIC-11 | Domain experts per industry (food safety, customs, healthcare, etc.) paired with a platform engineer for schema compliance review |

**Cross-cutting roles (not epic-specific):**
- **Architecture Governance Lead** — owns ADR catalog updates, resolves open architecture decisions as they arise
- **Security Reviewer** — validates Managed Identity, Private Endpoint, and PII dual-tier implementations across all epics
- **Technical Program Manager** — owns the wave plan, cross-team dependency tracking, and critical path monitoring

---

## Output 6 — Technical Risk Register

| # | Risk | Impact | Probability | Mitigation |
|---|---|---|---|---|
| 1 | Template schema changes after downstream epics (04–09) begin consuming it | High — cascading rework across 6 epics | Medium | Freeze template schema at end of Wave 1; require Architecture Governance Lead sign-off for any schema change after freeze |
| 2 | Context Assembly Engine becomes a shared-component bottleneck | Medium — slows EPIC-04, EPIC-05, EPIC-09 concurrently | Medium | Design for extensibility from day one (Wave 1); dedicate senior engineer ownership; load-test early with synthetic case volume |
| 3 | Azure DI prebuilt model coverage is lower than assumed for non-standard document types | Medium — increases LLM Phase 2 load, degrading token efficiency targets | Medium | Validate Azure DI model coverage against real Food Safety documents in Wave 1 spike before committing dual-phase extraction design |
| 4 | Open architecture decisions (multi-tenant throughput, AI Search versioning, override authorization) remain unresolved when dependent epics start | High — rework in EPIC-07, EPIC-08, EPIC-13 | High | Escalate all 8 open decisions from Architecture Readiness Checklist to Architecture Governance Lead before Wave 2 starts; resolve or explicitly defer with documented risk acceptance |
| 5 | PII field list (`pii_field_list.json`) incomplete for a template, causing unredacted PII exposure | Critical — data protection violation | Medium | Mandatory security review of every template's PII field list before evaluation gate sign-off; automated PII scanner as a secondary control |
| 6 | Evaluation ground truth data authoring is underestimated in effort per template | High — blocks go-live for Wave 4 templates | High | Scope ground truth authoring as an explicit, separately estimated task per template (minimum 20 cases); assign domain expert time budget in Wave 4 planning |
| 7 | Rule ETag pinning implemented incorrectly, breaking point-in-time audit reproducibility | High — undermines regulatory defensibility of the entire platform | Low | Dedicated test suite validating ETag capture and historical reconstruction before EPIC-06 is marked complete |
| 8 | GDPR right-to-erasure requirement conflicts with immutable audit trail design | Medium — legal/compliance exposure in EU deployments | Medium | Treat as an open architecture decision requiring resolution before any EU customer deployment; do not build erasure workaround without Architecture Governance Lead approval |
| 9 | Multi-agent boundaries (10 agents per ADR-022) add coordination overhead without proportional benefit if over-engineered | Medium — schedule risk | Low | Implement agents as lightweight Python classes (not microservices) per ADR-022; review after Wave 2 whether agent boundaries are adding value |
| 10 | Sovereign/Air-Gapped topology cannot be validated without access to Azure Stack Hub or equivalent test environment | Medium — Wave 5 delivery risk | Medium | Identify and provision sovereign test environment access during Wave 3, not Wave 5, to leave runway for issue resolution |
| 11 | Knowledge Pack regeneration race condition on concurrent rapid rule changes | Low — stale Knowledge Pack window | Low | Debounce logic (default 30s) per ADR-023; monitor Change Feed trigger latency in production |
| 12 | Connector isolation (separate Managed Identity per connector) underestimated as infrastructure effort | Medium — EPIC-12 schedule risk | Medium | Scope connector isolation as an infrastructure task co-owned by Platform Team and Integration Team, not solely a coding task |

---

## Output 7 — Engineering Readiness Assessment

| Dimension | Score (1–5) | Rationale |
|---|---|---|
| **Architecture Readiness** | **4 / 5** | 28 ADRs accepted, comprehensive component specifications (17 components), full data model and integration patterns documented. Deducted one point: 8 open architecture decisions remain unresolved (multi-tenant throughput, AI Search versioning, override authorization, Copilot Studio, GDPR erasure, evaluation CI gate policy, fan-out for large bundles, Marketplace Bicep conversion) — these are documented but not decided. |
| **Implementation Readiness** | **3 / 5** | Component specifications are detailed enough to begin engineering (Purpose/Inputs/Outputs/Dependencies/Extensibility/Token Impact documented per component). Deducted points: `src/platform/` folders are scaffolded with `.gitkeep` only — zero production code exists yet; Food Safety template has only 1 of 13 artifacts (`template.json` manifest) populated; extended field definition schema (ADR-002 implementation note: dataType/isPII/required/aliases) not yet implemented. |
| **Operational Readiness** | **2 / 5** | Terraform modules exist structurally (5 modules referenced) but Single Tenant deployment has not been executed end-to-end on Azure. No CI/CD pipeline currently enforces the domain-neutrality or template CI gates described in ADR-010/ADR-025 — these are architectural decisions awaiting implementation. Evaluation framework code exists in concept (`src/evaluation/`) but is not yet wired as a deployment gate. |
| **Enterprise Readiness** | **2 / 5** | Multi-tenant, Government Cloud, and Sovereign topologies are architecturally designed (Output 10 of Document 15) but unvalidated in any real environment. Azure Marketplace packaging (Bicep conversion, metered billing, `createUiDefinition.json`) has not started. Responsible AI `TRANSPARENCY_FAQ.md` referenced but not authored. GSI partner enablement program not yet defined. |

**Overall readiness summary:** ARIA has strong architectural and governance foundations (ADR catalog, component specifications, data model) but is at the pre-implementation stage for actual platform code, infrastructure validation, and enterprise packaging. The highest-leverage next action is closing the 8 open architecture decisions before Wave 2 begins, since several (multi-tenant throughput, override authorization) directly gate epics on the critical path.

---

## Output 8 — Epic Dependency Matrix

| Epic | Depends On | Enables |
|---|---|---|
| **EPIC-01** Platform Foundation | None | EPIC-02, EPIC-03, EPIC-11, EPIC-12, EPIC-13 |
| **EPIC-02** Token Efficiency Layer | EPIC-01 | EPIC-03 (OfficePreprocessor, DuplicateDetector) · EPIC-04 (ContextAssemblyEngine, SemanticChunker, PDFNormalizer) · EPIC-05 (ContextAssemblyEngine) · EPIC-09 (ContextAssemblyEngine) |
| **EPIC-03** Evidence Intake Engine | EPIC-01, EPIC-02, EPIC-12 (inbound connector) | EPIC-04 |
| **EPIC-04** Document Intelligence Engine | EPIC-02, EPIC-03 | EPIC-05 |
| **EPIC-05** Validation & Reconciliation | EPIC-02, EPIC-04 | EPIC-06 |
| **EPIC-06** Policy Evaluation Engine | EPIC-05, EPIC-11 (rules.json) | EPIC-07, EPIC-10 (ETag pinning) |
| **EPIC-07** Risk Assessment Engine | EPIC-06, EPIC-11 (risk weight matrix) | EPIC-08, EPIC-09 (AI Search indexes) |
| **EPIC-08** Decision Recommendation Engine | EPIC-05, EPIC-06, EPIC-07, EPIC-12 (outbound connector) | EPIC-09, EPIC-10 |
| **EPIC-09** Human Review Portal | EPIC-02, EPIC-07, EPIC-08 | (terminal — no downstream epic depends on this) |
| **EPIC-10** Governance & Audit | EPIC-06 (ETag), EPIC-08 (decision package) — schema defined in EPIC-01 | (terminal — no downstream epic depends on this) |
| **EPIC-11** Template Framework | EPIC-01, EPIC-02 (Knowledge Pack Generator) | EPIC-04 through EPIC-09 (all consume template artifacts) · EPIC-06 (rules), EPIC-07 (risk config), EPIC-08 (decision vocabulary, PII list) |
| **EPIC-12** Connector Framework | EPIC-01 | EPIC-03 (inbound), EPIC-08 (outbound) |
| **EPIC-13** Deployment & Operations | All epics (full scope); Terraform skeleton only depends on EPIC-01 | (wraps platform — enables production go-live for all epics) |

---

## Output 9 — Recommended First 90 Days Plan

### Days 1–20 — Foundation Sprint

1. Stand up Durable Functions orchestrator skeleton (5 no-op activities) — EPIC-01
2. Build `shared/ai_client.py` with token tracking wired to Application Insights — EPIC-01
3. Deploy Cosmos DB 6-container schema with correct partition keys — EPIC-01
4. Stand up CI pipeline: lint, unit test runner, domain-neutrality banned-word check skeleton — EPIC-01
5. Freeze template schema (`templates/_schema/template.schema.json`) — EPIC-11
6. Define audit event schema (pulled forward from EPIC-10) — cross-cutting
7. Define canonical evidence map schema (contract for EPIC-04/05/06/07/08 boundary) — cross-cutting
8. Escalate all 8 open architecture decisions to Architecture Governance Lead for resolution or documented deferral

### Days 21–40 — Parallel Enablement Sprint

9. Build `OfficePreprocessor`, `PDFNormalizer`, `DuplicateDetector` — EPIC-02
10. Build Context Assembly Engine (baseline: token budget enforcement, Knowledge Pack loading) — EPIC-02
11. Build `BaseConnector` SDK and Generic REST connector (inbound path) — EPIC-12
12. Build Single Tenant Terraform module — deployable empty pipeline target — EPIC-13
13. Begin Food Safety template content authoring (13 artifacts, using existing PAFN rule data) — EPIC-11
14. Build Evidence Intake Engine — submission, integrity check, staging — EPIC-03
15. Spike: validate Azure DI prebuilt model coverage against real Food Safety documents (mitigates Risk #3)

### Days 41–65 — Core Pipeline Sprint

16. Build Dual-Phase Extraction (Azure DI structured + LLM gap-fill) — EPIC-04
17. Build Semantic Chunking Service, integrate with extraction — EPIC-02/04
18. Build Data Reconciliation Engine (alias resolution, canonical map assembly) — EPIC-05
19. Build Cross-Document Validation Engine (conflict detection, coherence score) — EPIC-05
20. Begin Policy Evaluation Engine — start with 3–4 highest-priority rule categories (Mandatory Evidence, Field Completeness, Value Validation, Temporal Validity) — EPIC-06
21. Build Knowledge Pack Generator and Knowledge Pack Agent (Change Feed trigger) — EPIC-02/11

### Days 66–90 — Decision Path Completion Sprint

22. Complete remaining Policy Evaluation Engine rule categories (Cross-Evidence Comparison, Code Reference, Item-Level Quantitative, Signature/Stamp) — EPIC-06
23. Build Risk Assessment Engine — weighted scoring, HOLD logic (defer AI Search historical pattern integration to Wave 3 if AI Search index versioning decision is unresolved) — EPIC-07
24. Build Decision Recommendation Engine — verdict synthesis, evidence chain, PII dual-tier write, HMAC delivery — EPIC-08
25. Build Evaluation Framework core — ground truth loading, accuracy measurement against Food Safety template — EPIC-13
26. Run first end-to-end pipeline test: submission → extraction → reconciliation → policy → risk → decision → callback, on Food Safety test cases
27. Begin Human Review Portal scaffolding (FastAPI shell, agent tool definitions) in parallel — EPIC-09
28. Checkpoint: measure actual token consumption against the 50–70% reduction target (ADR-011) using real Food Safety cases

**90-day exit criteria:** End-to-end Food Safety case processing operational in a Single Tenant test environment, evaluation framework measuring extraction accuracy, and all 8 open architecture decisions either resolved or explicitly deferred with documented risk acceptance from the Architecture Governance Lead.

---

*End of ARIA Implementation Plan*
*Version 1.0 · 2026-08-10 · Microsoft Confidential — IP Strategy*
*Primary Inputs: 15-ARIA-Platform-Architecture.md · 16-ARIA-ADR-Catalog.md*
*Scope: Implementation planning only — no architecture redesign, no diagrams, no user stories*
