<!-- INTERNAL ENGINEERING DEEP-REFERENCE -->
<!-- Not required reading for adopters. See ../TechnicalArchitecture.md for the short "Key decisions" table most readers need. -->
<!-- Full 28-ADR catalog for engineering teams doing deep implementation or governance review work. -->

# ARIA - Architecture Decision Record Catalog (Internal Engineering Deep-Reference)

**Document:** 16-ARIA-ADR-Catalog.md
**Version:** 1.0
**Date:** 2026-08-10
**Status:** Reference architecture - Core Platform implementation not yet started
**Governance Role:** Architecture Governance Lead and ADR Reviewer
**Primary Source:** 15-ARIA-Platform-Architecture.md
**Supporting Sources:** 11-Architecture-Input-Pack.md · 04-Architecture-Decision-Records.md
**Scope:** Internal engineering and architecture governance reference - not required reading for adopters
**Audience:** Engineering only (deep governance reference - see [TechnicalArchitecture.md](../TechnicalArchitecture.md#key-decisions) for the short summary)

> This catalog supersedes and extends 04-Architecture-Decision-Records.md.
> ADRs 001-008 are reproduced in summary form (originals in Document 04).
> ADRs 009-028 are new formal records derived from the platform architecture in Document 15.
> No architecture has been redesigned. This document only governs and formalizes decisions already present.

---

## Output 1 - ADR Inventory

### 1.1 Complete ADR Register

| ADR ID | Title | Status | Category | Source |
|---|---|---|---|---|
| ADR-001 | Azure Durable Functions for Pipeline Orchestration | **Accepted** | Platform / Orchestration | Document 04 |
| ADR-002 | Configuration-Driven Document Type Schema | **Accepted** | Platform / Extensibility | Document 04 |
| ADR-003 | Cosmos DB for Rules Engine and Case Store | **Accepted** | Platform / Data | Document 04 |
| ADR-004 | Azure Managed Identity Zero-Secrets Architecture | **Accepted** | Security / Identity | Document 04 |
| ADR-005 | LLM Cross-Document Reasoning Pattern | **Accepted** | AI / Reasoning | Document 04 |
| ADR-006 | Private Endpoint Network Topology | **Accepted** | Security / Network | Document 04 |
| ADR-007 | Tool-Calling Agent Architecture for Human Review | **Accepted** (tool-calling pattern is built as the reference deployment's SCEN-02 Chat Agent; less tested/validated than the Delivery Agent) | AI / Agent | Document 04 |
| ADR-008 | Async Callback Delivery Pattern | **Accepted** | Integration / Delivery | Document 04 |
| ADR-009 | Three-Tier Product Model | **Accepted - Design** | Platform / Architecture | Document 15 |
| ADR-010 | Domain Neutrality Enforcement via CI | **Accepted - Design** | Platform / Governance | Document 15 |
| ADR-011 | Token Efficiency as First-Class Architectural Concern | **Accepted - Design** | AI / Cost | Document 15 |
| ADR-012 | Document Normalization Before LLM Processing | **Accepted** | AI / Pre-Processing | Document 15 |
| ADR-013 | Dual-Phase Extraction Strategy | **Accepted** | AI / Extraction | Document 15 |
| ADR-014 | Semantic Chunking for Large Document Processing | **Accepted - Design** | AI / Context Management | Document 15 |
| ADR-015 | Knowledge Pack Strategy for Domain Context Compression | **Accepted - Design** | AI / Context Management | Document 15 |
| ADR-016 | Context Assembly Engine Pattern | **Accepted - Design** | AI / Context Management | Document 15 |
| ADR-017 | Retrieval-Augmented Human Review | **Proposed** (the reference chat engine uses direct Cosmos DB tool lookups, not Azure AI Search retrieval - this design is not implemented) | AI / Human Review | Document 15 |
| ADR-018 | Azure OpenAI Prompt Prefix Caching | **Accepted - Design** | AI / Cost | Document 15 |
| ADR-019 | Azure API Management as Submission Gateway | **Accepted** | Integration / Gateway | Document 15 |
| ADR-020 | Azure AI Search for Semantic Case History Retrieval | **Accepted** | Platform / Search | Document 15 |
| ADR-021 | PII Redaction Architecture (single-tier default; dual-tier optional) | **Accepted - Design** | Security / Privacy | Document 15 |
| ADR-022 | Agent and Stage Orchestration Architecture | **Accepted - Design** | AI / Agent | Document 15 |
| ADR-023 | Knowledge Pack Stage as Event-Driven Background Process | **Accepted - Design** | AI / Agent | Document 15 |
| ADR-024 | Connector Isolation Model | **Accepted - Design** | Platform / Extensibility | Document 15 |
| ADR-025 | Template CI Enforcement | **Accepted - Design** | Platform / Governance | Document 15 |
| ADR-026 | Sovereign Deployment via Environment Variable Substitution | **Proposed** | Platform / Deployment | Document 15 |
| ADR-027 | Duplicate Detection Before AI Processing | **Accepted** | AI / Pre-Processing | Document 15 |
| ADR-028 | Evaluation Framework as Mandatory Deployment Gate | **Accepted** | Platform / Quality | Document 15 |

**Total ADRs:** 28 (8 original + 20 new)

---

### 1.2 ADR Category Summary

| Category | Count | ADR IDs |
|---|---|---|
| Platform / Architecture | 2 | 009, 010 |
| Platform / Data | 1 | 003 |
| Platform / Extensibility | 2 | 002, 024 |
| Platform / Governance | 2 | 010, 025 |
| Platform / Orchestration | 1 | 001 |
| Platform / Deployment | 1 | 026 |
| Platform / Quality | 1 | 028 |
| Platform / Search | 1 | 020 |
| AI / Agent | 3 | 007, 022, 023 |
| AI / Context Management | 3 | 014, 015, 016 |
| AI / Cost | 2 | 011, 018 |
| AI / Extraction | 1 | 013 |
| AI / Human Review | 1 | 017 |
| AI / Pre-Processing | 2 | 012, 027 |
| AI / Reasoning | 1 | 005 |
| Integration / Delivery | 1 | 008 |
| Integration / Gateway | 1 | 019 |
| Security / Identity | 1 | 004 |
| Security / Network | 1 | 006 |
| Security / Privacy | 1 | 021 |

---

### 1.3 ADR Status Summary

Status reflects maturity, not just approval - three tiers distinguish decisions that are implemented from decisions that are architecturally sound but unbuilt.

| Status | Count | Notes |
|---|---|---|
| **Accepted** | 14 | Implemented in the reference deployment (ADR-001 through 008, 012, 013, 019, 020, 027, 028) |
| **Accepted - Design** | 12 | Architecturally decided, sound reasoning, not yet built or measured (ADR-009, 010, 011, 014-016, 018, 021-025) |
| **Proposed** | 2 | No path to validation without further work (ADR-017: the reference Chat Agent does not use this retrieval design; ADR-026: no path to validation without a real deployment) |
| Deprecated | 0 | No decisions deprecated |
| Superseded | 0 | No decisions superseded |

---

### 1.4 Original ADR Summaries (ADR-001 to ADR-008)

These ADRs are documented in full in 04-Architecture-Decision-Records.md. Summaries below for governance reference.

| ADR | One-Line Summary |
|---|---|
| ADR-001 | Five-activity sequential pipeline orchestrated by Azure Durable Functions, with separate Reasoning and Rules & Policy activities; checkpoint-based state persistence; no external workflow engine |
| ADR-002 | All document type definitions in `evidence_types.json`; extraction prompt auto-generated from field list; zero code for new document types |
| ADR-003 | Cosmos DB NoSQL for runtime rules (no restart on change), case lifecycle, artifacts, verdicts, audit, and feedback; Change Feed for indexing |
| ADR-004 | All service-to-service access via User-Assigned Managed Identity + RBAC; no connection strings or API keys anywhere; secrets in Key Vault |
| ADR-005 | LLM semantic alias resolution for cross-vocabulary field name mapping; LLM cross-document consistency check at bundle level; temp=0.0, seed=42 |
| ADR-006 | Private Endpoints for all data services; no public internet egress from pipeline; VNet integration; NSG inbound from APIM only |
| ADR-007 | Review Assistant is a tool-calling grounded agent; answers cite only case evidence via tool calls; minimum 5 core tools; no general knowledge |
| ADR-008 | HMAC-SHA256 signed HTTP POST delivery; exponential backoff retry (default ×3); every attempt logged to Cosmos DB callback-log |

---

## Output 2 - New Architecture Decision Records (ADR-009 to ADR-028)

---

## ADR-009: Three-Tier Product Model

**Date:** 2026-08-10
**Status:** Accepted - Design (conceptual model for the generalized platform)
**Category:** Platform / Architecture
**Deciders:** Principal Product Manager · Principal Enterprise Architect
**Source:** Document 15, Output 1 (Reusability Strategy) and Output 7 (Template Framework)

### Context

ARIA must be deployable across many unrelated industries (food safety, customs, KYC, insurance, healthcare, environmental, licensing) without requiring platform engineering for each deployment. Earlier single-customer implementations entangled adopter-specific logic (case-management connector, domain rules, localized UI) with reusable platform logic, making it impossible to tell where the platform ended and the customer began. A clear product model was needed to enforce separation.

The core tension: domain experts must be able to configure the platform for their industry without engineering involvement, while platform engineers must be able to evolve the core without affecting customer-specific code. These goals conflict unless the product is structured to separate their concerns explicitly.

### Decision

ARIA is structured as a three-tier product model:

- **Tier 1 - Core Platform:** All domain-neutral engines, frameworks, and pipeline logic. Lives in `src/platform/`. Contains zero industry vocabulary. Deployed once per ARIA instance. Modified only by platform engineers.
- **Tier 2 - Industry Templates:** Configuration packages of 13 JSON artifacts per decision workflow. Lives in `templates/{name}/`. Contains no executable code. Authored by domain experts. Deployed per industry vertical.
- **Tier 3 - Reference Implementations:** Complete customer deployments with customer-specific connectors, UI, and infrastructure. Lives in `reference-implementations/{name}/`. Completely isolated from Tier 1 and Tier 2. Owned by the customer or delivery partner.

No tier may import from a lower tier's directory in reverse (e.g., `src/platform/` must not import anything from `templates/` or `reference-implementations/`).

### Rationale

**Clean separation of concerns by ownership:** Tier 1 is owned by platform engineers. Tier 2 is owned by domain experts. Tier 3 is owned by customers. The tier boundaries map directly to ownership and responsibility. When a compliance rule changes, only a Tier 2 artifact changes. When a new customer is onboarded, only a Tier 3 deployment changes. The platform is never touched.

**Reusability scales correctly:** A new industry requires only Tier 2 authoring (13 JSON files). A new customer requires only Tier 3 deployment (infrastructure + connectors). Neither requires Tier 1 modification. This makes ARIA's reusability claim arithmetically verifiable.

**IP governance clarity:** Microsoft's IP is in Tier 1. Tier 2 and Tier 3 artifacts are customer-configurable. This separation is essential for IP licensing, Marketplace listing, and partner delivery models.

**Classification outcome:** Applying the three-tier model to the reference deployment classifies 26 components as Tier 1 (Core Platform), 7 as Tier 2 (Industry Template), and 5 as Tier 3 / Customer-Specific.

### Alternatives Considered

**Two-tier model (Platform + Customer):** No template tier - domain configuration embedded in customer deployments. Rejected because it recreates the original problem: every new customer starts from scratch. The template tier enables partner-led delivery without Microsoft CSE involvement.

**Single tier (fully generic platform):** All configuration at runtime via API. Rejected because it requires engineering work to add any new domain, contradicting the "domain experts configure, not engineers" principle.

**Plugin model (platform + plugins):** Domain logic delivered as executable plugins. Rejected because executable plugins cannot be safely authored by domain experts, introduce security risk, and violate the "templates contain no code" constraint required for partner ecosystem safety.

### Consequences

**Positive:**
- New industry vertical: zero platform engineering, 13 JSON files only
- New customer: zero platform engineering, Tier 3 deployment only
- IP audit: every component classifiable as Tier 1/2/3
- Partner delivery: GSI partners can deliver ARIA without Microsoft engineering access to Tier 1

**Negative / Trade-offs:**
- Template authoring requires discipline: incorrectly placing executable logic in a template violates the model
- Tier boundary enforcement requires CI tooling (ADR-025) to be effective
- Tier 3 isolation means customer connectors cannot share code with platform connectors - duplication may occur for common patterns

---

## ADR-010: Domain Neutrality Enforcement via CI

**Date:** 2026-08-10
**Status:** Accepted - Design (CI enforcement not yet built)
**Category:** Platform / Governance
**Deciders:** Principal Enterprise Architect · Engineering Lead
**Source:** Document 15, Output 7 (Template Framework CI Enforcement)

### Context

Architecture Principle AP-01 requires that `src/platform/` contains zero industry vocabulary. Without automated enforcement, this principle degrades over time as engineers add domain-specific shortcuts, variable names, or conditionals into platform code. Manual code review is insufficient - reviewers may not recognize domain vocabulary in all supported industries.

Similarly, Industry Templates (Tier 2) must contain no executable code. A template with a `.py` file would be executable by domain experts, creating a security risk and a maintenance liability. Without CI enforcement, violations accumulate silently.

### Decision

The CI pipeline enforces four hard constraints on every pull request:

1. **Domain vocabulary ban in `src/platform/`:** A configurable banned-word list (seeded with food safety, customs, healthcare, insurance, and KYC vocabulary) is applied to all Python files in `src/platform/`. Any match fails the PR.

2. **Executable code ban in `templates/`:** CI rejects any PR that adds `.py`, `.js`, `.sh`, `.ps1`, or any other executable file type to any `templates/{name}/` directory. JSON and Markdown only.

3. **Template JSON schema validation:** All template artifacts are validated against `templates/_schema/template.schema.json` on every PR. Invalid JSON or schema violations fail the PR.

4. **Cross-tier import analysis:** CI analyzes import graphs to detect any `import` statement in `src/platform/` that references `templates/` or `reference-implementations/`, and vice versa. Detected violations fail the PR.

### Rationale

Domain neutrality is a claim, not a property - unless CI enforces it. Automated enforcement converts a design principle into a measurable, verifiable invariant. This is required for IP governance: the claim that "Tier 1 is domain-neutral" must be demonstrably true, not aspirationally stated.

The banned-word list is intentionally configurable because new industries introduce new vocabulary. When a new template is authored for a previously unseen vertical, its vocabulary is added to the banned list to ensure it never leaks into platform code.

### Alternatives Considered

**Manual review only:** Insufficient. Human reviewers miss vocabulary collisions, especially in variable names and comments. Cannot scale across a partner ecosystem.

**Namespace isolation (Python packages):** Using Python package boundaries to enforce separation. Partially effective but does not prevent vocabulary appearing in variable names, string literals, or comments.

### Consequences

**Positive:**
- Domain neutrality claim is verifiable by any reviewer by reading the CI report
- Template security: domain experts cannot accidentally (or intentionally) add executable logic
- IP governance: any PR that introduces domain coupling is rejected before merge

**Negative / Trade-offs:**
- Banned-word list requires maintenance as new industries are onboarded
- False positives are possible (e.g., a utility function named `validate_invoice` may be flagged)
- Import graph analysis adds CI runtime overhead (~30–60 seconds per PR)

---

## ADR-011: Token Efficiency as First-Class Architectural Concern

**Date:** 2026-08-10
**Status:** Accepted - Design (principle is sound; the 50-70% target is a projection, not a measured result)
**Category:** AI / Cost
**Deciders:** Principal Enterprise Architect · AI Systems Architect
**Source:** Document 15, Output 6 (Token Efficiency Architecture) and Architecture Principle AP-05

### Context

Azure OpenAI input and output tokens are the dominant variable cost in every ARIA deployment. An unoptimized implementation that sends raw documents to LLMs produces a cost profile that scales poorly: more documents, more pages, more complexity → quadratically higher LLM costs. For a government customer processing 10,000 cases/day with 5 documents per case, this becomes a commercially critical concern.

Early prototypes sent full document OCR output directly to the LLM for field extraction. Token consumption was approximately 5–8× what a structured approach would require. At scale, this cost profile would make ARIA economically non-viable in price-sensitive markets.

Token efficiency must be an architectural property, not an operational practice. If it is left to individual developers to "try to use fewer tokens," the property will not hold across the codebase over time.

### Decision

Token efficiency is declared a first-class architectural concern, equal in priority to security and reliability. This decision has the following concrete consequences:

- Every component specification includes a **Token Impact** attribute documenting the component's effect on LLM token consumption
- The **Context Assembly Engine** (ADR-016) is a mandatory architectural component that all LLM calls must route through
- The platform targets **50–70% reduction** in LLM token consumption per case compared to an unoptimized approach sending raw documents to LLMs
- Token usage is tracked, attributed, and reported per case and per tenant (ADR-018 supports this via Application Insights)
- No LLM call may be made outside the `shared/ai_client.py` wrapper - all calls route through the token-tracking client

The following strategies are architectural requirements, not suggestions (each has its own ADR):
- Document normalization before LLM processing (ADR-012)
- Dual-phase extraction (ADR-013)
- Semantic chunking for large documents (ADR-014)
- Knowledge Packs for policy context (ADR-015)
- Context Assembly Engine enforcement (ADR-016)
- Retrieval-augmented human review (ADR-017)
- Prompt prefix caching (ADR-018)
- Duplicate detection before processing (ADR-027)

### Rationale

Token cost is a product characteristic that affects commercial viability, partner margin, and competitive positioning. ARIA's value proposition (6–10 week deployment, lower cost than bespoke build) depends on having a defensible per-case cost profile. A platform that costs $5 per case in LLM tokens is commercially unviable for high-volume government deployments.

Making token efficiency architectural means it cannot be removed by a developer under time pressure. The CI enforcement of the `shared/ai_client.py` wrapper ensures all calls are tracked, and architectural review of any new LLM interaction requires documenting the token impact.

### Alternatives Considered

**Token efficiency as operational guidance:** Documented as best practices in a style guide. Rejected because style guides are not enforced and degrade over time without accountability.

**Token monitoring only:** Track tokens without architectural controls. Rejected because monitoring after the fact does not prevent over-consumption.

### Consequences

**Positive:**
- Commercially defensible per-case cost profile
- Token consumption is visible, measurable, and attributable per tenant
- Architectural review gate prevents new LLM-heavy patterns from being introduced without documented justification

**Negative / Trade-offs:**
- All LLM calls must route through a shared wrapper - adds coupling to a shared component
- Token optimization adds implementation complexity (pre-processing pipeline, chunking, Knowledge Packs)
- Target (50–70% reduction) requires measurement across representative case sets to verify

---

## ADR-012: Document Normalization Before LLM Processing

**Date:** 2026-08-10
**Status:** Accepted (`di_extraction.py` normalizes to Markdown before LLM processing)
**Category:** AI / Pre-Processing
**Deciders:** AI Systems Architect · Principal Enterprise Architect
**Source:** Document 15, Output 6, Strategy 6.2 (DOCX to Markdown) and 6.3 (PDF Normalization)

### Context

Regulated industries submit documents in heterogeneous formats: Word documents (DOCX), Excel spreadsheets (XLSX), PowerPoint (PPTX), PDF, and images. Raw binary formats contain substantial non-semantic overhead: XML namespace declarations, revision history, formatting tags, embedded objects, headers/footers, bounding box coordinates, and layout markers.

A raw DOCX file for a 2-page document may be 30–50 KB of XML, containing 5–8× more tokens than the semantic content. Sending raw DOCX to an LLM is architecturally wrong - it wastes tokens on non-semantic XML noise and may cause the LLM to reason about formatting rather than content.

Similarly, Azure Document Intelligence Markdown output contains page layout markers, column separators, and repeated headers/footers that add 20–35% token overhead without contributing to field extraction accuracy.

### Decision

All documents are normalized to clean Markdown before any LLM interaction. Normalization is performed by the **Document Normalization Engine** (C-04) as part of Activity 1, before any AI service call.

**For Office formats (DOCX, XLSX, PPTX):** The `OfficePreprocessor` class converts to Markdown using python-docx, openpyxl, and python-pptx respectively. Conversion strips: XML namespace declarations, revision marks, comments, formatting metadata, embedded object references. Conversion preserves: headings, paragraphs, tables, list structure, text content.

**For PDF and image formats:** Azure Document Intelligence (prebuilt-layout) produces Markdown output. The `PDFNormalizer` post-processor then strips: repeated page headers/footers, excessive blank lines, DI form field markers (`:selected:`, `:unselected:`), column layout artifacts. The normalized Markdown is stored in Azure Blob (`artifacts/{caseId}/normalized/`) for reuse.

**Rule:** No component downstream of the normalization step may access the raw document binary or un-normalized Azure DI output for LLM processing.

### Rationale

Token reduction is linear with document normalization quality. A 60–75% reduction in Office document tokens (from XML noise removal) is deterministic and does not depend on LLM model version, prompt engineering, or case content. It is the highest-certainty token optimization available.

Normalization also improves LLM extraction quality by eliminating distracting formatting noise. An LLM processing clean Markdown extracts fields more accurately than one processing XML-wrapped content where the field value may be surrounded by formatting tags.

Normalized Markdown is stored in Blob Storage, enabling reuse if the same document appears in multiple pipeline stages (extraction, cross-document reasoning, explainability) without re-normalizing.

### Alternatives Considered

**Send raw documents to LLM:** Simplest implementation. Rejected due to 5–8× token overhead and reduced extraction quality.

**Use only Azure DI output without post-processing:** Acceptable for simple cases. Rejected because DI output includes 20–35% layout overhead that reduces LLM context efficiency.

**Per-document-type normalization only for known formats:** Reject unknown formats. Rejected because ARIA must be resilient to unexpected document formats - a fallback to raw text extraction is preferable to rejection.

### Consequences

**Positive:**
- Deterministic 60–75% token reduction for Office documents
- 20–35% reduction for PDF documents
- Improved LLM extraction accuracy (less noise = better focus)
- Normalized Markdown reusable across pipeline stages (no re-normalization)

**Negative / Trade-offs:**
- Normalization adds latency to Activity 1 (~0.5–2 seconds per Office document)
- python-docx, openpyxl, python-pptx are additional dependencies
- Complex Office features (embedded charts, pivot tables, macros) may lose fidelity in Markdown conversion - acceptable for field extraction purposes

---

## ADR-013: Dual-Phase Extraction Strategy

**Date:** 2026-08-10
**Status:** Accepted (matches the `di_extraction.py` 8-step process)
**Category:** AI / Extraction
**Deciders:** AI Systems Architect · Principal Enterprise Architect
**Source:** Document 15, Output 6, Strategy 6.4 (Structured Pre-Extraction)

### Context

For many regulated document types (invoices, receipts, identity documents), Azure Document Intelligence prebuilt models already extract structured fields with high accuracy and at lower cost than LLM extraction. Sending the entire document to the LLM to re-extract fields that Azure DI has already extracted is pure token waste with no accuracy benefit.

However, for custom document types (Halal certificates, environmental impact assessments, specialist medical reports), Azure DI prebuilt models do not cover all required fields. LLM extraction is needed for the uncovered fields.

### Decision

Activity 2 (DI Extraction Agent) implements a dual-phase extraction strategy:

**Phase 1 - Azure DI Structured Extraction:**
- Azure DI prebuilt model (configurable per document type in `evidence_types.json` via `diModel` field) extracts structured fields
- Output: `{fieldName: {value, confidence}}` for all fields covered by the prebuilt model
- Cost: Azure DI API call only (no LLM tokens)
- High-confidence Phase 1 results (confidence ≥ configurable threshold, default 0.85) are marked as `extractionMethod: "azure_di_structured"`

**Phase 2 - Selective LLM Gap-Filling:**
- The gap list = all fields in `evidence_types.json` MINUS Phase 1 covered fields
- LLM extraction prompt contains only the gap field list + relevant document sections
- Output: `{fieldName: {value, confidence}}` for uncovered fields
- Cost: LLM tokens for gap fields only (40–60% reduction versus full extraction)
- Phase 2 results marked as `extractionMethod: "llm_extraction"`

**Merge:** Phase 1 and Phase 2 results are merged into the final per-document extraction artifact.

### Rationale

Azure DI prebuilt models are purpose-built for common document types (invoices, receipts, IDs) and provide higher accuracy at lower cost than LLM extraction for those fields. Using LLM only for uncovered fields captures the cost benefit of Azure DI while retaining LLM flexibility for custom fields.

The `diModel` field in `evidence_types.json` makes the Phase 1 model selection domain-expert-configurable. If no prebuilt model applies, Phase 1 produces zero results and Phase 2 covers all fields - identical to the original single-phase approach.

### Alternatives Considered

**LLM-only extraction (original approach):** All fields extracted by LLM from normalized document. Simpler implementation. Rejected because it wastes tokens on fields that Azure DI can extract more cheaply and accurately.

**Azure DI-only extraction:** Only extract what Azure DI can extract; skip LLM entirely. Rejected because custom document types (Halal certificates, medical reports, legal compliance documents) are not covered by prebuilt models.

**Fine-tuned Azure DI custom models per document type:** Higher accuracy for custom types. Rejected because custom model training requires labeled training data, significantly increases onboarding time, and does not reduce LLM calls for cross-document reasoning which is always required.

### Consequences

**Positive:**
- 40–60% reduction in LLM extraction tokens for documents with applicable Azure DI prebuilt models
- Higher accuracy for pre-populated fields (Azure DI structured extraction > LLM extraction for standard forms)
- Zero-code Phase 1 model selection (configurable per document type in template)

**Negative / Trade-offs:**
- Two-phase extraction adds implementation complexity (`DualPhaseExtractor` class required)
- Phase 1/Phase 2 merge logic must handle confidence score aggregation correctly
- For completely custom document types, Phase 1 produces no results - same cost as single-phase

---

## ADR-014: Semantic Chunking for Large Document Processing

**Date:** 2026-08-10
**Status:** Accepted - Design (not yet built; unvalidated at realistic document sizes)
**Category:** AI / Context Management
**Deciders:** AI Systems Architect
**Source:** Document 15, Output 6, Strategy 6.5 (Semantic Chunking)

### Context

Regulated submissions frequently include large documents: environmental impact assessments (30–100 pages), legal contracts (50–200 pages), medical records (20–60 pages), comprehensive audit reports (40–80 pages). Sending the full document to an LLM for field extraction is estimated to waste 80–90% of tokens on pages that contain no target fields - this is a projection based on document structure, not a measurement against a production case set.

The target fields for extraction are typically concentrated in specific sections (executive summary, certification section, signature block, itemized tables). A 30-page environmental assessment may contain the required fields on 2–4 pages.

### Decision

Documents exceeding `CHUNKING_THRESHOLD_PAGES` (configurable, default 10 pages) are chunked by the **Semantic Chunking Service** (C-06) before LLM extraction.

**Chunking strategies (in priority order per document, configurable per template):**
1. **Header-based chunking:** Split on Markdown H1/H2/H3 headers (preserved by Azure DI prebuilt-layout). Most reliable for structured documents with defined sections.
2. **Page-window chunking:** Sliding window of configurable page count (default 3 pages, stride 1 page). Fallback when no headers detected.
3. **Semantic similarity chunking:** Embed field names and document chunks via text-embedding-3-small; select top-K chunks by cosine similarity. Most accurate, highest compute cost; used only when configured.

**Chunk selection:** For each target field group, the top-K chunks (configurable, default top-3) most relevant to those fields are selected. Only selected chunks are sent to the LLM.

**Threshold:** Documents ≤ `CHUNKING_THRESHOLD_PAGES` skip chunking entirely (zero overhead for short documents like certificates and invoices).

### Rationale

Focused context is both cheaper and more accurate than full-document context. An LLM processing the 3 most relevant pages of a 30-page document is less likely to hallucinate, more likely to find the target fields, and is projected to consume 80–90% fewer tokens than processing the full document - pending measurement against real case data.

Header-based chunking is preferred because it is deterministic, fast (no embedding call required), and reliable for structured regulatory documents that typically follow standard section conventions.

### Alternatives Considered

**Fixed-size chunking (character/token count):** Simple to implement. Rejected because fixed-size chunks cut through sentences and tables, losing semantic coherence.

**Send full document always:** No chunking. Rejected because 80–90% token waste on large documents is architecturally unacceptable under ADR-011.

**Chunk only for the largest documents (>50 pages):** Too conservative. Rejected because even 15-page documents waste significant tokens without chunking.

### Consequences

**Positive:**
- Projected 60–80% token reduction for documents >10 pages (estimate, not yet measured)
- Reduced hallucination risk (focused context → more grounded extraction)
- Chunk map recorded in extraction artifacts (audit: which chunk covered which fields)

**Negative / Trade-offs:**
- Semantic similarity chunking requires embedding API call (adds ~0.2–0.5 seconds per large document)
- Chunk selection may miss a field if it appears in an unexpected section - mitigated by overlap parameter and fallback to full document if confidence is low
- Threshold parameter requires tuning per industry (healthcare documents may warrant lower threshold)

---

## ADR-015: Knowledge Pack Strategy for Domain Context Compression

**Date:** 2026-08-10
**Status:** Accepted - Design (not yet built; unvalidated at a ~47-rule scale)
**Category:** AI / Context Management
**Deciders:** AI Systems Architect · Principal Enterprise Architect
**Source:** Document 15, Output 6, Strategy 6.6 (Knowledge Packs)

### Context

The Chat Agent (ADR-007, built in the SCEN-02 reference deployment) and the Reasoning Agent both benefit from domain context - a compressed representation of the relevant rules, known aliases, decision vocabulary, and risk thresholds for the current template. Without this, either: (a) no domain context is provided (reducing answer quality), or (b) the full rule set is injected into LLM context (20,000+ tokens).

A food safety deployment has ~47 active rules. Loading all 47 rules as JSON context for every LLM call in the human review session is 20,000+ tokens per call - commercially catastrophic at scale.

### Decision

The **Knowledge Pack Generator** (C-07) pre-generates a compressed Knowledge Pack per template. The Knowledge Pack is a structured JSON document containing only the information an LLM needs for domain context, without raw rule documents.

**Knowledge Pack contents (~280–350 tokens):**
- `applicableRulesSummary[]`: Rule ID, category, one-sentence summary, target fields (not full rule logic)
- `aliasQuickMap`: Known field name alias pairs for fast-path resolution
- `decisionVocabulary`: Domain verdict labels
- `riskBands`: Threshold values for LOW/MEDIUM/HIGH/CRITICAL
- `holdThreshold`: HOLD escalation score threshold
- `referenceDataCategories`: Summary of applicable code lists (not the lists themselves)

**Generation trigger:** Knowledge Pack is generated on template activation and regenerated on any rule change (via Cosmos DB Change Feed trigger on the `rules` container). Not generated per case.

**Storage:** `knowledge-packs/{templateId}/current.json` in Azure Blob Storage. Loaded by Context Assembly Engine at pipeline invocation time.

### Rationale

A Knowledge Pack is generated once and used across millions of cases. Its marginal cost per case is effectively zero (one Blob read). Its token savings are projected at 70–85% per LLM call that previously required full rule context (~19,700 tokens estimated saved per call) - this is a calculation based on rule-set size, not a measurement against a running deployment.

The Knowledge Pack is a read-only context artifact - it does not replace the Cosmos DB rules engine (which evaluates rules deterministically). It provides LLMs with a compressed understanding of the domain for reasoning tasks where deterministic evaluation is insufficient.

### Alternatives Considered

**Full rule set in LLM context:** Every LLM call includes all active rules. Rejected due to 20,000+ token overhead per call.

**No domain context for LLM calls:** LLM reasons without domain knowledge. Rejected because cross-document reasoning and human review quality degrades significantly without domain vocabulary and rule awareness.

**Dynamic rule selection per call:** Select only the rules relevant to the current case at call time. More targeted than full Knowledge Pack. Deferred: requires per-case rule relevance scoring, adds latency. Knowledge Pack is the pragmatic first-generation solution.

### Consequences

**Positive:**
- Projected 70–85% reduction in policy context tokens per LLM call (estimate, not yet measured)
- Knowledge Pack is version-stamped - supports future comparison of decisions made under different template versions
- Change Feed trigger ensures Knowledge Pack is always current - no stale context risk

**Negative / Trade-offs:**
- Knowledge Pack is a compressed summary - detailed rule logic is not present; LLM may not correctly interpret edge cases
- Knowledge Pack must be regenerated when rule set changes significantly - regeneration adds ~2–5 seconds when triggered
- Knowledge Pack for very large rule sets (>200 rules) may still exceed 300 tokens - schema may need to compress further

---

## ADR-016: Context Assembly Engine Pattern

**Date:** 2026-08-10
**Status:** Accepted - Design (not yet built)
**Category:** AI / Context Management
**Deciders:** AI Systems Architect · Engineering Lead
**Source:** Document 15, Output 4, Component C-08 (Context Assembly Engine)

### Context

Without a centralized context assembly mechanism, individual developers construct LLM prompts ad-hoc, inconsistently applying token efficiency strategies. Some calls use full document context; others use chunks; some include Knowledge Packs; others do not. The result is unpredictable token consumption, inconsistent context quality, and violation of ADR-011 (token efficiency as first-class concern).

A pattern was needed to enforce consistent, minimum-context assembly across all LLM calls regardless of which engineer implements them.

### Decision

The **Context Assembly Engine** (C-08) is a mandatory intermediary between business logic and LLM API calls. No component may call the LLM directly without routing through the Context Assembly Engine.

The Context Assembly Engine:
1. Accepts a processing step identifier (extraction · reconciliation · cross-document · human review)
2. Retrieves appropriate Knowledge Pack (from Blob cache)
3. Retrieves semantic chunks (from Semantic Chunking Service if applicable)
4. Assembles the minimum viable context: `{systemPrompt, contextWindow, userPrompt}`
5. Estimates token count (via tiktoken) before submission
6. Enforces a per-call token budget (configurable, default 8,192 context tokens)
7. Records context composition (which Knowledge Pack version, which chunks) in audit metadata
8. Routes to `shared/ai_client.py` for the actual LLM call with token tracking

All prompt construction logic lives in the Context Assembly Engine - no prompt strings are constructed in activity functions.

### Rationale

Centralizing context assembly creates a single enforcement point for all token efficiency strategies. Adding a new optimization strategy (e.g., a new context compression technique) requires only a change to the Context Assembly Engine - not changes to every component that calls LLMs.

The per-call token budget acts as a circuit breaker: if the assembled context exceeds the budget, the Context Assembly Engine compresses further (fewer chunks, shorter Knowledge Pack prefix) before proceeding. This prevents runaway token consumption from mis-configured templates or unusually large documents.

### Alternatives Considered

**Distributed prompt construction:** Each component builds its own prompts. Simpler architecture. Rejected because token efficiency cannot be consistently enforced without a central assembly point.

**Prompt library (shared strings module):** Shared string constants for prompt templates. Rejected because it solves only the template consistency problem, not the context assembly and budget enforcement problem.

### Consequences

**Positive:**
- Single point of enforcement for all token efficiency strategies
- Token budget circuit breaker prevents cost overruns from any single call
- Context composition logged to audit metadata (traceability for LLM call reproducibility)
- New optimization strategies require only Context Assembly Engine changes

**Negative / Trade-offs:**
- All LLM calls must route through Context Assembly Engine - adds coupling to a shared component
- Context Assembly Engine becomes a critical dependency - its availability directly affects pipeline availability
- tiktoken pre-estimation adds ~5–10 ms latency per LLM call

---

## ADR-017: Retrieval-Augmented Human Review

**Date:** 2026-08-10
**Status:** Proposed - the reference Chat Agent (SCEN-02) uses direct Cosmos DB tool lookups (`get_case_verdict`, `get_extracted_fields`, `get_finding_evidence`, `get_rule_definition`), not Azure AI Search retrieval-augmented generation. This ADR describes a design under consideration, not the as-built system - open question, to be revisited.
**Category:** AI / Human Review
**Deciders:** AI Systems Architect · Principal Enterprise Architect
**Source:** Document 15, Output 6, Strategy 6.7 (Retrieval-Augmented Human Review)

### Context

The Chat Agent (ADR-007, built in the SCEN-02 reference deployment) provides a conversational agent for reviewers. Naive implementation would inject the full case record into the LLM context for every reviewer query - giving the LLM complete visibility but consuming 10,000+ tokens per query. For a reviewer session with 20 queries on a complex case (typical for HOLD/FAIL decisions), this is 200,000+ tokens per session.

A reviewer asking "Why was the weight flagged?" needs the 2–3 most relevant findings, not the entire case record. The LLM does not need all 10,000 tokens of context to answer accurately - it needs the right 1,500 tokens.

### Decision

**Note:** This retrieval-augmented design is proposed, not yet implemented - the reference Chat Agent answers reviewer queries via direct Cosmos DB tool lookups instead. The Chat Agent would implement **retrieval-augmented generation (RAG)** for every reviewer query if this design is adopted:

1. The reviewer's query is embedded using text-embedding-3-small
2. Azure AI Search performs hybrid vector + keyword retrieval against the case's indexed evidence (using `caseId` as filter)
3. Top-3 retrieved evidence chunks are returned (configurable K)
4. The Context Assembly Engine assembles: Knowledge Pack (~300 tokens) + top-3 chunks (~1,200 tokens) + system prompt (~300 tokens) + user query (~50 tokens) = ~1,850 tokens total
5. The LLM answers using only the assembled context
6. Every answer must cite source document, page, and extracted field value - no uncited claims permitted

The `EvidenceRetriever` class in `src/platform/human_review/` encapsulates the retrieval step.

### Rationale

Retrieval-augmented generation achieves 80–90% token reduction per query (from ~11,550 tokens full-case to ~1,850 tokens retrieved) while maintaining or improving answer accuracy. Focused context reduces hallucination risk - the LLM cannot generate claims about evidence it has not been shown.

The mandatory citation requirement (source document, page, field value) ensures that every answer is evidence-grounded and auditable. If the retrieved chunks do not contain the answer, the agent must say so - it cannot draw on general knowledge.

### Alternatives Considered

**Full-case context injection per query:** Complete case record in every query. Rejected due to 80–90% token waste and no accuracy improvement over retrieval-augmented.

**Keyword-only retrieval:** No vector embeddings; keyword search only. Rejected because reviewer queries often use synonyms and paraphrases that keyword search misses.

**Conversation history accumulation:** Include all previous turns in context. Rejected because conversation history growth makes late-session queries prohibitively expensive.

### Consequences

**Positive:**
- 80–90% token reduction per reviewer query (1,850 vs 11,550 tokens)
- 84% reduction over a 20-query review session (36,600 vs 231,000 tokens)
- Reduced hallucination risk from focused context
- Mandatory citations make every answer auditable

**Negative / Trade-offs:**
- Retrieval adds ~20–50 ms latency per query (acceptable for human review workflows)
- Retrieval may miss relevant evidence if case indexing is incomplete (mitigated by evaluation framework)
- Top-K selection may exclude relevant evidence for unusual reviewer queries - configurable K allows tuning

---

## ADR-018: Azure OpenAI Prompt Prefix Caching

**Date:** 2026-08-10
**Status:** Accepted - Design (not confirmed as implemented today)
**Category:** AI / Cost
**Deciders:** AI Systems Architect · Engineering Lead
**Source:** Document 15, Output 6, Strategy 6.8 (Prompt Template Caching)

### Context

LLM extraction prompts have a static prefix (system prompt + field list template) and a variable suffix (document content). The static prefix is identical across all cases of the same document type. Azure OpenAI (GPT-5.4 or later) supports prompt prefix caching: if the prompt prefix (≥ 1,024 tokens) is identical to a recent call, the cached prefix tokens are charged at 50% of the standard input token price.

Without deliberate prompt structuring, prompts may place variable content before the static prefix, disabling cache eligibility.

### Decision

All LLM extraction prompts are structured to place the static prefix first and the variable content last, ensuring the static prefix meets the minimum caching threshold of 1,024 tokens:

```
[System prompt - static, ~200 tokens] (cached)
[Field list template - static per document type, ~800 tokens] (cached)
[Separator instruction - static, ~24 tokens] (cached)
----
[Document content - variable, ~1,000–4,000 tokens] (not cached)
```

If the static prefix is shorter than 1,024 tokens (e.g., for document types with few fields), the Knowledge Pack summary is appended to the static prefix section to meet the threshold.

`shared/ai_client.py` logs `cached_tokens` from `response.usage.prompt_tokens_details.cached_tokens` and reports cache hit rate to Application Insights.

On template activation, a cache warm-up call is performed per document type to pre-populate the Azure OpenAI prompt cache.

### Rationale

Prompt prefix caching is a zero-code-change cost reduction once prompts are structured correctly. For a deployment processing 1,000 cases/day × 5 documents × 800 cached template tokens = 4M cached template tokens/day → ~2M tokens/day saved at 50% cache pricing. At $0.01 per 1K input tokens (illustrative pricing for GPT-5.4), this represents ~$20/day or ~$7,300/year in savings per 1,000-case/day deployment.

### Alternatives Considered

**No prompt caching:** Accept full token pricing. Rejected because prompt caching is zero-effort savings once prompts are structured correctly.

**Semantic caching (cache LLM responses):** Cache LLM outputs for identical inputs. More aggressive savings but requires a separate cache store and invalidation logic. Deferred to future optimization - prompt prefix caching is simpler and immediate.

### Consequences

**Positive:**
- 40–50% cost reduction on static prefix tokens per LLM call
- Zero latency impact (caching is transparent at the Azure OpenAI API level)
- Cache hit rate surfaced in Application Insights dashboard

**Negative / Trade-offs:**
- Prompt structure must be maintained across all prompt builders - any change that moves variable content before static prefix breaks cache eligibility
- Minimum 1,024 token prefix threshold requires padding for short field lists
- Cache invalidation when field list changes requires one cache warm-up call per document type per deployment

---

## ADR-019: Azure API Management as Submission Gateway

**Date:** 2026-08-10
**Status:** Accepted (the reference deployment routes submissions through APIM)
**Category:** Integration / Gateway
**Deciders:** Principal Enterprise Architect
**Source:** Document 15, Output 11 (Azure Reference Architecture)

### Context

ARIA receives multi-document submission bundles from external systems. These submissions must be authenticated, rate-limited, schema-validated, and routed to the Durable Functions pipeline. Without a dedicated gateway layer, the Function App HTTP trigger must implement all of these concerns inline - coupling business logic with infrastructure concerns.

Additionally, the submission schema varies by industry template (`submission_schema.json`). The gateway must apply the correct schema validation policy for each template deployment.

### Decision

Azure API Management (APIM) is the submission gateway for all inbound case submissions. APIM handles:

- **Authentication:** API subscription key (standard deployments) or Microsoft Entra ID Bearer token (enterprise/government deployments)
- **Rate limiting:** Per-subscription throttling policy (configurable by deployment tier)
- **Schema validation:** Inbound JSON schema validation against `submission_schema.json` loaded from the active template; invalid submissions rejected at the gateway with HTTP 400 before any Azure compute is consumed
- **Routing:** All validated submissions routed to the Durable Functions HTTP starter endpoint

APIM is deployed in the Application Landing Zone subnet with VNet integration. The Durable Functions HTTP trigger is not exposed publicly - only accessible via APIM's private VNet path.

### Rationale

APIM is the established Microsoft enterprise API gateway pattern. Placing schema validation at the gateway eliminates the cost of loading invalid submissions into the pipeline (preventing wasted Azure DI and Azure OpenAI calls). Rate limiting at the gateway prevents a single submitter from consuming all pipeline capacity.

Schema validation at the gateway also provides an early, structured error response to submitters - they receive a detailed validation failure immediately rather than waiting for the pipeline to reject the submission internally.

### Alternatives Considered

**Azure Application Gateway:** Handles L7 routing and TLS termination but does not provide API management features (subscription management, schema validation, developer portal). Rejected as insufficient for enterprise API management requirements.

**Direct Function App HTTP trigger (no gateway):** Simpler infrastructure. Rejected because schema validation, authentication, and rate limiting would need to be implemented in application code, coupling business logic with infrastructure concerns.

**Azure Front Door:** Global load balancing with WAF capability. Overkill for single-region deployments. APIM provides all required features without the additional complexity of a global routing layer.

### Consequences

**Positive:**
- Schema validation at gateway prevents invalid submissions from consuming AI compute budget
- Subscription key management enables per-tenant API key isolation (SaaS topology)
- APIM developer portal available for external system integrators
- Rate limiting policy protects pipeline from submission flood

**Negative / Trade-offs:**
- APIM adds infrastructure cost and operational overhead (additional service to deploy and monitor)
- Schema validation policy must be updated when `submission_schema.json` changes (automation required)
- APIM adds ~50–100 ms gateway latency to the submission path (acceptable: initial 202 response only)

---

## ADR-020: Azure AI Search for Semantic Case History Retrieval

**Date:** 2026-08-10
**Status:** Accepted (the reference deployment has `case_document_indexer.py` and `case_summary_indexer.py`)
**Category:** Platform / Search
**Deciders:** Principal Enterprise Architect · AI Systems Architect
**Source:** Document 15, Output 11 (Azure Reference Architecture) and Output 4, Component C-13

### Context

ARIA's human review agent must answer queries like "what did previous cases with similar documents decide?" and "are there precedents for this type of conflict?". The risk assessment engine uses historical case patterns to calibrate risk scoring. These features require semantic search across a growing corpus of case evidence and decision narratives.

Simple Cosmos DB queries (keyword or field equality) cannot answer semantic similarity queries. A full-text search capability is required.

### Decision

Azure AI Search (Standard tier, semantic ranker enabled) provides all case history indexing and retrieval. Two indexes are maintained:

- **`case-document-index`:** Per-document extracted facts, indexed per case. Proposed for evidence retrieval by the Chat Agent (ADR-017, not yet implemented) and used by the Reasoning Agent for historical field value lookup.
- **`case-summary-index`:** Per-case decision narrative (GPT-generated plain-language summary). Used by the Risk Assessment Engine for historical pattern matching and by the Human Review Agent for precedent search.

Both indexes use hybrid search (vector similarity + BM25 keyword). All vectors use `text-embedding-3-small` for cost-effective semantic encoding.

Index population is event-driven: Cosmos DB Change Feed triggers the Case Document Indexer and Case Summary Indexer when a case reaches COMPLETED status (no polling, no message queue).

Queries include `caseId` and `templateId` filters to ensure case isolation and template relevance.

### Rationale

Azure AI Search is the native Azure semantic search service. Hybrid search (vector + keyword) outperforms either approach alone for regulatory document queries, which often mix exact regulatory code terms (benefiting from keyword) with semantic paraphrases (benefiting from vector search). Semantic ranker (available on Standard tier) improves relevance ranking for longer natural language queries.

Change Feed-triggered indexing is consistent with ADR-003 (Cosmos DB for case store) - no additional messaging infrastructure is required.

### Alternatives Considered

**Cosmos DB full-text search:** Available but limited - no vector search, no semantic ranking. Insufficient for natural language query quality required by the Human Review Agent.

**Elasticsearch:** Powerful semantic search capability. Rejected because it is not natively Azure-managed, adds operational complexity, and lacks private endpoint support comparable to Azure AI Search.

**Azure Cognitive Search (older name):** Same service - Azure AI Search is the current product name.

### Consequences

**Positive:**
- Hybrid vector + keyword search covers both exact regulatory code queries and natural language queries
- Event-driven indexing (Change Feed) adds no additional infrastructure
- Standard tier semantic ranker improves relevance for complex natural language queries

**Negative / Trade-offs:**
- Standard tier is required for semantic ranker - higher cost than Basic tier
- Per-case index population adds ~1–3 seconds post-completion latency before case is searchable in history
- Index schema changes when template evolves (open decision: versioning strategy documented in Architecture Readiness Checklist, ADR-009 of architecture input pack)

---

## ADR-021: PII Redaction Architecture (Single-Tier Default; Dual-Tier Optional)

**Date:** 2026-08-10
**Status:** Accepted - Design (the reference implementation uses a simpler, single-tier redact-at-write-boundary pattern - see Context)
**Category:** Security / Privacy
**Deciders:** Principal Enterprise Architect · CISO
**Source:** Document 15, Output 1 (Architecture Principle AP-04) and Output 4, Component C-12

### Context

Evidence documents submitted to ARIA may contain PII: names, identification numbers, financial figures, health information, addresses. The Delivery Agent (C-12) assembles a complete evidence chain that includes extracted field values - many of which are PII.

The reference implementation's `shared/pii_redaction.py` solves this with a simpler pattern: PII fields are redacted before the Cosmos write boundary, and no un-redacted tier is ever persisted. The pipeline uses full data in memory during processing; only the redacted version is stored. This has a smaller risk surface than storing raw PII anywhere.

A dual-tier write (a second, un-redacted "secured" container for auditors) is a materially different design - it persists raw PII, which is a larger risk surface than the single-tier approach. That trade-off should only be made if a specific customer or regulatory requirement demands auditors see raw PII values rather than field-level citations. No such requirement has been documented for any current or planned ARIA deployment.

### Decision

**Default (single-tier):** The platform redacts PII at the write boundary. A single evidence store is written per case, with PII field values replaced by `[REDACTED: {fieldName}]` labels. No un-redacted tier is persisted. PII field declarations live in the template's `pii_field_list.json` - platform applies redaction automatically based on template configuration.

**Optional dual-tier extension:** If a specific customer's compliance requirement mandates auditor access to raw PII values (documented and cited here before enabling), the platform may additionally write a second, access-restricted container containing the un-redacted evidence chain. This is a per-template, per-customer opt-in - never a platform-wide default.

The PII field map (which fields in which documents contain PII) is generated during extraction (Activity 2) and stored in the extraction artifacts. The Delivery Agent uses this map to perform redaction without re-processing the documents.

### Rationale

The single-tier pattern as the default minimizes risk surface - there is no scenario where raw PII sits in storage waiting to be queried or exfiltrated. The template-declared PII field list means domain experts (not platform engineers) control what is considered PII in their domain. Healthcare PII fields differ from financial PII fields differ from immigration PII fields - the platform should not hardcode this.

The dual-tier extension remains available for the rare case where a real regulatory or contractual requirement forces auditor access to raw values, but it must be justified per-deployment rather than assumed as architecture.

### Alternatives Considered

**Dual-tier write as the default (original decision):** Write both a secured (with PII) and display (redacted) evidence store for every deployment. Rejected as the default because it persists raw PII with no demonstrated requirement forcing it, and it doubles storage cost and attack surface for every deployment regardless of need.

**Single store with field-level encryption:** Encrypt PII fields at rest; decrypt only for authorized queries. Technically feasible but adds complexity: key management per field, query performance impact, decryption at display time. Rejected in favor of the simpler redact-at-write-boundary pattern.

**Single store with access control at query time:** All evidence in one container; access control filters PII fields in query results. Rejected because query-level PII filtering is error-prone - a single unguarded query path exposes PII. Redaction at write time is safer than filtering at read time.

**No PII protection:** Accept that reviewers see all field values. Rejected - violates GDPR, data protection law, and government procurement requirements in virtually all target markets.

### Consequences

**Positive:**
- Matches the implemented single-tier pattern - no new risk introduced by default
- No raw PII persisted anywhere by default - smaller attack surface than the dual-tier design
- Template-controlled PII field list enables domain-specific PII handling without platform changes
- Dual-tier extension remains available, but only when a documented requirement justifies it

**Negative / Trade-offs:**
- If a future customer genuinely needs auditor access to raw PII, the dual-tier extension must be built and justified per-deployment rather than existing as a ready-made default
- PII field list in template must be kept current - missing a PII field means it appears unredacted in storage
- GDPR right-to-erasure creates tension with the immutable audit trail requirement (open decision in Architecture Readiness Checklist)

---

## ADR-022: Agent and Stage Orchestration Architecture

**Date:** 2026-08-10
**Status:** Accepted - Design (target model; not yet implemented as separate component classes)
**Category:** AI / Agent
**Deciders:** AI Systems Architect · Principal Enterprise Architect
**Source:** Document 15, Output 5 (Agent Architecture)

### Context

ARIA's pipeline involves multiple processing steps, some AI-driven (document extraction, field classification and canonicalization, cross-document validation, human review) and some purely deterministic (intake validation, policy evaluation, risk scoring). Each step has distinct input/output contracts and distinct failure modes. A monolithic approach - one large LLM call for all processing - would lose traceability, mix concerns, and produce unpredictable outputs.

A bounded-component architecture distributes responsibilities across explicit interfaces, mapped onto the existing Durable Functions orchestration (ADR-001) without introducing a separate agent framework.

### Decision

ARIA implements an 8-component pipeline of Agents and Stages: five Agent/Stage components sequenced across four Durable Functions activities, plus three that run asynchronously or in the background. Each component is a bounded processing unit responsible for a specific pipeline step. Agents perform LLM-driven reasoning; Stages perform deterministic, rule-based processing. All components communicate through structured output contracts passed as Durable Functions activity inputs.

**Component roster:**
- **Sequential (5 components / 5 activities):** Pre-Validation Agent (Activity 1) · DI Extraction Agent (Activity 2 - includes field canonicalization and PII classification) · Reasoning Agent (Activity 3) · Rules & Policy Agent (Activity 4 - includes risk scoring and HOLD determination) · Delivery Agent (Activity 5)
- **Async / background (3):** Chat Agent (async, built in the reference deployment) · Audit Log (cross-cutting) · Knowledge Pack Stage (event-driven background)

Each component:
- Has a single, well-defined responsibility
- Consumes structured input and produces structured output
- Operates independently - components do not share mutable state
- Agents route LLM calls through the Context Assembly Engine (ADR-016); Stages never call an LLM

**Implementation:** Agents and Stages are not separate microservices or containers. They are Python classes with a single `process(input) -> output` interface, called by Durable Functions activities. This preserves the simplicity of the Durable Functions orchestration while achieving component-level separation of concerns.

### Rationale

Component-level boundaries make the pipeline testable in isolation: each component can be unit-tested with mock inputs without spinning up the full Durable Functions orchestrator. The explicit input/output contracts prevent implicit data coupling - a component that needs a value must receive it explicitly in its input, not read from shared state.

The model also enables future parallelization: the Durable Functions fan-out pattern (ADR-001) can parallelize multiple component instances for large document bundles without changing the contract.

### Alternatives Considered

**Single monolithic LLM prompt (all processing in one call):** Simplest implementation. Rejected because a single LLM call for intake + extraction + reconciliation + validation is not reliable, not traceable, and not independently testable.

**Calling every component "Agent" regardless of processing type:** Simplest naming. Rejected in favor of distinguishing LLM-driven components (Agents) from deterministic rule-based components (Stages), which better reflects each component's actual function.

**Separate microservices per component:** Highest isolation. Rejected because Durable Functions activities already provide isolation without the operational overhead of microservice deployment, service discovery, and inter-service communication.

**External agent framework (AutoGen, Semantic Kernel Agent):** Framework-managed agent orchestration. Rejected because it adds an external framework dependency, obscures the Durable Functions state persistence model, and introduces a learning curve without material benefit for ARIA's sequential pipeline.

### Consequences

**Positive:**
- Each component independently unit-testable
- Explicit input/output contracts prevent implicit data coupling
- Future parallelization possible without contract changes
- Clear ownership: each component has a named engineering owner

**Negative / Trade-offs:**
- 8 component classes add code surface area
- Input/output contract schema evolution requires coordinated change across components
- Component boundaries impose serialization overhead (Durable Functions serializes activity inputs to Azure Storage)

---

## ADR-023: Knowledge Pack Stage as Event-Driven Background Process

**Date:** 2026-08-10
**Status:** Accepted - Design (not yet built)
**Category:** AI / Agent
**Deciders:** AI Systems Architect
**Source:** Document 15, Output 5 (Agent Architecture) and Output 4, Component C-07

### Context

Knowledge Packs (ADR-015) must be current - stale Knowledge Packs containing outdated rule summaries could mislead LLM reasoning. They must also be available before any case processing begins - a Knowledge Pack generated on-demand per case would add latency and duplicate generation cost.

The Knowledge Pack is regenerated whenever: (a) a template is activated, or (b) the rule set changes (any Cosmos DB rules document is inserted or modified). Both triggers are events, not schedules. Generation is deterministic compression and serialization of existing data.

### Decision

The **Knowledge Pack Stage** operates as an event-driven background process, entirely independent of case processing:

- **Trigger 1 - Template activation:** When `install_template.py` is run, it explicitly invokes the Knowledge Pack Stage to generate the initial Knowledge Pack for the new template
- **Trigger 2 - Rule change:** Cosmos DB Change Feed on the `rules` container triggers the Knowledge Pack Stage when any rule document is created or modified (configurable: only trigger on `active: true` rule changes)

The Knowledge Pack Stage reads the full rule set, template artifacts, and alias pairs from Cosmos DB and template storage, compresses them into the Knowledge Pack JSON schema, and writes the result to `knowledge-packs/{templateId}/current.json` in Azure Blob, overwriting the previous version.

The Knowledge Pack Stage runs as a separate Azure Function (Change Feed trigger), isolated from the case processing pipeline Functions.

### Rationale

Event-driven generation ensures Knowledge Packs are always current without periodic polling or per-case generation. The Change Feed trigger provides exactly-once processing semantics - a rule change triggers exactly one Knowledge Pack regeneration, regardless of how many case-processing Functions are running concurrently.

Isolation from the case processing pipeline ensures that a slow or failed Knowledge Pack regeneration does not affect in-flight case processing - the previous Knowledge Pack remains available until the new one is written.

### Alternatives Considered

**Per-case Knowledge Pack generation:** Generate the Knowledge Pack at the start of each case. Rejected due to duplicated computation (same Knowledge Pack for every case in the same template) and added per-case latency.

**Scheduled regeneration (e.g., hourly):** Periodic refresh regardless of rule changes. Rejected because it creates stale-Knowledge-Pack windows between rule change and scheduled regeneration.

**Manual regeneration only:** Admin-triggered Knowledge Pack update. Rejected because it requires operational discipline that cannot be enforced automatically.

### Consequences

**Positive:**
- Knowledge Pack is always current within seconds of a rule change (Change Feed delay: typically <5 seconds)
- Zero per-case Knowledge Pack generation overhead
- Isolated from case processing pipeline - regeneration failures do not affect case processing

**Negative / Trade-offs:**
- Change Feed trigger adds one additional Azure Function deployment
- Concurrent rule changes (many rules updated rapidly) may trigger multiple Knowledge Pack regenerations in quick succession - mitigated by debounce logic (configurable delay before regeneration, default 30 seconds)
- Knowledge Pack overwrite is not atomic - a case processing Function reading the Knowledge Pack during a write may get a partial file (mitigated by write-then-rename pattern in Blob Storage)

---

## ADR-024: Connector Isolation Model

**Date:** 2026-08-10
**Status:** Accepted - Design (target model; adopter-specific logic is still embedded directly in `pre_validation.py` and `agency_code.py` today - see Context)
**Category:** Platform / Extensibility
**Deciders:** Principal Enterprise Architect · Engineering Lead
**Source:** Document 15, Output 1 (Reusability Strategy) and Output 4, Component C-16

### Context

External system integration is required in every ARIA deployment: inbound submission sources (SharePoint, workflow engines, CRMs, custom portals) and outbound decision delivery targets (customs management systems, healthcare claim systems, CRMs, case management platforms). Each customer has a different external system. If connector logic lives in the platform pipeline, adding a new connector requires platform engineering.

**Current state:** Adopter-specific logic is still embedded directly in `pre_validation.py` and `agency_code.py` rather than isolated behind a connector boundary - this ADR describes the target isolation model, not the as-built state. Migrating it into a standalone connector under `reference-implementations/` is outstanding work, not a completed correction.

### Decision

The Connector Framework enforces three isolation rules:

1. **Three-interface contract:** Every connector must implement `BaseConnector` from `connectors/sdk/base_connector.py`. The three interfaces are: `transformSubmission(external_payload) → ARIA_JSON`, `deliverDecision(aria_decision) → acknowledgement`, `reportStatus(case_id, status, error) → bool`. No other platform interfaces are available to connectors.

2. **Deployment unit isolation:** Each connector is a separate deployment unit with its own Managed Identity, its own network scope, and no direct access to the platform's Cosmos DB, Blob Storage, or AI Search. Connectors interact with the platform only through the submission REST API and the decision callback.

3. **Directory isolation:** Platform-reusable connectors live in `connectors/{name}/`. Customer-specific connectors live in `reference-implementations/{customerName}/connectors/{name}/`. CI enforcement (ADR-010) prevents cross-tier imports.

**Built-in connectors (platform-provided, in `connectors/`):** Generic REST, File-based (Blob/SFTP), SharePoint (Graph API), Dynamics 365 (Dataverse).

**Customer connectors (in `reference-implementations/`):** case-management system adapters, any customer-specific integration.

### Rationale

Connector isolation means adding a new external system requires only connector development - no platform engineering, no platform review, no platform deployment. This enables partner-delivered connectors without Microsoft engineering involvement.

The Managed Identity isolation prevents connector security vulnerabilities from compromising the platform data layer. A compromised connector cannot read Cosmos DB verdicts or Blob artifacts - it can only call the public API.

### Alternatives Considered

**Platform-embedded connectors:** Connector logic in platform pipeline activities. Rejected because every new external system requires platform engineering and deployment - eliminating the extensibility benefit.

**Plugin model (dynamically loaded connector code):** Connector code loaded at runtime. Rejected due to security risk (arbitrary code execution in the platform process) and the complexity of safe dynamic loading.

**Webhook-only connector model:** Connectors are just webhook endpoints with no transformation logic. Rejected because transformation logic (mapping external submission formats to ARIA standard) is necessary for every integration and cannot always be expressed as a simple webhook.

### Consequences

**Positive:**
- New connector requires only connector code - zero platform changes
- Managed Identity isolation prevents connector compromise from reaching platform data
- Customer connectors in `reference-implementations/` are excluded from platform IP claims

**Negative / Trade-offs:**
- Three-interface contract limits connector design flexibility - complex integrations must be expressed within the three methods
- Connector deployment unit isolation adds operational overhead (separate deployment pipeline per connector)
- Connectors cannot access platform internals - advanced integrations (e.g., real-time case status subscriptions) require the platform to expose additional APIs

---

## ADR-025: Template CI Enforcement

**Date:** 2026-08-10
**Status:** Accepted - Design (CI gates not yet built)
**Category:** Platform / Governance
**Deciders:** Engineering Lead · Architecture Governance Lead
**Source:** Document 15, Output 7 (Template Framework CI Enforcement Rules)

### Context

Industry Templates (Tier 2) must satisfy two properties to be safe for partner ecosystem delivery:
1. **No executable code:** Domain experts must be able to author templates without engineering oversight. If templates could contain executable code, a malicious or misconfigured template could compromise the platform.
2. **Valid schema:** Templates that fail schema validation produce runtime errors during case processing - a PR-time failure is far preferable to a production failure.

Without CI enforcement, neither property can be reliably maintained as the template ecosystem grows across multiple partner teams.

### Decision

The CI pipeline enforces four template quality gates on every pull request that touches the `templates/` directory:

1. **Executable code ban:** Any file in `templates/{name}/` with extension `.py`, `.js`, `.ts`, `.sh`, `.ps1`, `.exe`, `.dll`, or `.so` fails the PR. JSON and Markdown files only.

2. **JSON schema validation:** All 13 required template artifacts are validated against `templates/_schema/template.schema.json`. Missing required files or invalid JSON structure fails the PR.

3. **Required artifact completeness check:** All 13 template artifacts must be present in a complete template directory. Incomplete templates (e.g., missing `pii_field_list.json`) fail the PR.

4. **Cross-tier import check:** No Python file in `src/platform/` or `src/api/` may `import` from a template directory path. No template artifact may contain a Python import path reference.

### Rationale

CI gates convert template quality from a convention (enforced by human review) to a constraint (enforced automatically). Partner teams delivering templates for new industries may not know all quality requirements. CI gates catch violations immediately, before they reach production.

The executable code ban is a security gate: it prevents a template from becoming an attack vector for injecting malicious code into the platform process.

### Alternatives Considered

**Manual review only:** Human reviewers check template quality in PR review. Rejected because it requires reviewers to know all quality rules, creates inconsistency across reviewers, and does not scale with partner ecosystem growth.

**Runtime validation only:** Validate templates when they are installed, not on PR. Rejected because runtime failures in production are significantly more costly than PR-time failures.

### Consequences

**Positive:**
- Template quality enforced automatically - no reviewer expertise required for quality gate
- Executable code ban prevents security risk from partner-authored templates
- Schema validation prevents runtime errors from malformed templates

**Negative / Trade-offs:**
- CI validation adds ~10–20 seconds to PR pipelines touching template directories
- Schema must be kept current as template format evolves - outdated schema causes false-positive failures
- Completeness check requires all 13 artifacts - partial templates (during authoring) cannot be committed mid-work

---

## ADR-026: Sovereign Deployment via Environment Variable Substitution

**Date:** 2026-08-10
**Status:** Proposed (not yet validated against any deployment; endpoint substitution is architecturally sound but unverified in practice)
**Category:** Platform / Deployment
**Deciders:** Principal Enterprise Architect
**Source:** Document 15, Output 10 (Topology 4: Sovereign/Air-Gapped)

### Context

Classified government, defense, and critical infrastructure customers require deployments with zero public internet connectivity (air-gapped) and data that never leaves a physically controlled environment. These requirements conflict with the use of Azure OpenAI (cloud-hosted LLM) and Azure Document Intelligence (cloud-hosted OCR) - both standard services in the ARIA reference architecture.

The sovereign requirement cannot be satisfied by cloud-hosted AI services. However, creating a separate code branch for sovereign deployments would create maintenance split - any platform change would require dual updates.

### Decision

ARIA achieves sovereign deployment through **endpoint substitution via two environment variables only**, with zero code changes:

- `AZURE_OPENAI_ENDPOINT`: Set to a local LLM endpoint (Azure OpenAI on Azure Stack Hub, open-weight model such as Phi-4 or Mistral served via local inference, or ONNX runtime) instead of the Azure public endpoint
- `AZURE_DI_ENDPOINT`: Set to a local OCR service endpoint (Azure Document Intelligence on Azure Stack Hub or Tesseract-based local service) instead of the Azure public endpoint

The platform code calls these endpoints identically regardless of their value - the platform does not know whether it is calling a cloud service or a local endpoint. All other platform behavior (Durable Functions, Cosmos DB, Blob Storage, AI Search) uses Azure Stack Hub equivalents or locally hosted services, configured identically via existing Terraform module parameters.

**No code fork is created.** The same platform codebase serves all five deployment topologies.

### Rationale

A single codebase serving all topologies is essential for Microsoft-scale IP maintenance. If sovereign deployment required a code fork, every platform update would require dual testing and dual release - a maintenance burden that scales poorly as ARIA is deployed across more customers.

The two-endpoint substitution pattern works because ARIA's AI service clients are abstracted behind environment variable configuration (following ADR-004 - no hardcoded endpoints). This was not designed specifically for sovereign deployment; it is a consequence of clean dependency management. Sovereign deployment is a "free" property of good configuration hygiene.

### Alternatives Considered

**Separate sovereign code branch:** Maintain a separate codebase for sovereign deployments. Rejected because of dual-maintenance overhead and the risk of sovereign and standard codebases diverging.

**Conditional compilation / feature flags:** Platform code checks `IS_SOVEREIGN_DEPLOYMENT` flag and routes to different service clients. Rejected because it couples sovereign-awareness into platform code - violating the principle that the platform is deployment-topology-agnostic.

**Container-based service substitution (sidecar pattern):** Local AI proxy container that intercepts cloud-bound calls. Technically feasible. Deferred: adds container infrastructure complexity without benefit over environment variable substitution for the current architecture.

### Consequences

**Positive:**
- Sovereign deployment is a two-variable configuration change - no engineering involvement required
- Single codebase for all five topologies reduces maintenance overhead
- Government cloud and sovereign customers can use the same Terraform modules with different parameter values

**Negative / Trade-offs:**
- Local LLM models may not have feature parity with Azure OpenAI (GPT-5.4 or later capabilities) - sovereign deployments may have lower extraction accuracy
- Local Azure DI may not support all prebuilt models available in cloud
- Sovereign infrastructure (Azure Stack Hub) is the customer's responsibility - ARIA provides the configuration, not the sovereign infrastructure

---

## ADR-027: Duplicate Detection Before AI Processing

**Date:** 2026-08-10
**Status:** Accepted (`pre_validation.py` deduplicates by checksum)
**Category:** AI / Pre-Processing
**Deciders:** AI Systems Architect · Engineering Lead
**Source:** Document 15, Output 6, Strategy 6.7 (Duplicate Detection)

### Context

Submitters frequently include duplicate documents in evidence bundles - the same invoice submitted as both a digital PDF and a scanned TIFF, or two versions of the same certificate with minor formatting differences. Processing duplicate documents wastes 100% of the AI compute cost (Azure DI + LLM extraction) for the duplicate, produces identical extraction results, and may artificially increase cross-document conflict detection if the same values appear with minor formatting differences.

Approximately 3–5% of submitted documents are expected to be duplicates. For a 1,000-case/day deployment at 5 documents per case = 5,000 documents/day → 150–250 duplicate document processing events saved per day.

### Decision

Activity 1 (Pre-Validation Agent) performs duplicate detection before any document is routed to Activity 2 (DI Extraction Agent).

**Exact duplicate detection (primary):** SHA-256 hash is computed for each submitted document blob. The hash is compared against all other document hashes in the same submission and against the case's document hash store in Cosmos DB. Exact duplicates are flagged and skipped - they are recorded in the extraction artifacts with `extractionMethod: "skipped_duplicate"` and do not consume AI compute.

**Near-duplicate detection (optional, configurable):** MinHash or SimHash for structural similarity detection (same document, minor formatting differences). Configurable similarity threshold (default: 0.95 similarity = treated as duplicate). Enabled via `ENABLE_NEAR_DUPLICATE_DETECTION=true` environment variable.

Duplicate flags are included in the audit event stream - reviewers can see which documents were identified as duplicates and why.

### Rationale

SHA-256 duplicate detection is O(1) per document (hash comparison) with zero AI compute cost. It eliminates 100% of the tokens, latency, and cost for exact duplicate documents. The implementation cost is minimal; the benefit at scale is material.

Near-duplicate detection adds compute cost (MinHash construction) but catches the common case of the same document in different digital formats (PDF and TIFF of the same certificate). This is configurable because the compute cost may not be justified for all deployments.

### Alternatives Considered

**No duplicate detection:** Process all submitted documents regardless of duplication. Rejected because duplicate processing is pure waste - identical inputs produce identical outputs with no additional decision quality.

**Post-extraction deduplication:** Extract all documents, then de-duplicate results. Rejected because duplication is caught after the expensive AI processing has already occurred.

**Human review flagging only:** Let reviewers flag duplicates. Rejected because human flagging is slower and less consistent than automated hash comparison.

### Consequences

**Positive:**
- 100% savings for exact duplicate documents (Azure DI + LLM cost)
- Reduces false cross-document conflicts (same values in duplicate documents appear as agreement, not conflict)
- Duplicate detection results recorded in audit trail

**Negative / Trade-offs:**
- Near-duplicate detection adds latency and implementation complexity
- SHA-256 hash is computed on the raw blob - a document reformatted (different PDF compression) will not be detected as a duplicate by hash alone
- Near-duplicate false positives (documents flagged as duplicates that are actually different versions) could suppress important evidence - configurable threshold allows tuning

---

## ADR-028: Evaluation Framework as Mandatory Deployment Gate

**Date:** 2026-08-10
**Status:** Accepted (a working evaluation framework exists - `run_evaluation.py`, ground truth data, accuracy thresholds)
**Category:** Platform / Quality
**Deciders:** Principal Enterprise Architect · Architecture Governance Lead
**Source:** Document 15, Architecture Principle AP-10 and Output 1, Extensibility Model

### Context

ARIA's decision quality depends on the accuracy of LLM field extraction. If extraction accuracy is below threshold (e.g., critical fields are consistently mis-extracted), subsequent pipeline stages (cross-document validation, policy evaluation, risk assessment) produce incorrect results regardless of how correct their logic is. A decision based on wrong extracted values is wrong, regardless of rule correctness.

Without a mandatory accuracy gate, ARIA deployments could go to production with unacceptably low extraction accuracy - generating incorrect AI decisions at scale in regulated environments where incorrect decisions have legal consequences.

Additionally, each new industry template introduces new document types and new field extraction requirements. Template authors may not know whether their `evidence_types.json` field definitions produce accurate extraction until tested against real documents.

### Decision

The Evaluation Framework is a mandatory deployment gate: no ARIA template deployment may proceed to a production environment without passing an accuracy evaluation.

**Minimum accuracy threshold:** ≥ 85% exact match on target fields, measured across a ground truth dataset of ≥ 20 cases (configurable thresholds per deployment).

**Evaluation artifacts (per template):** Ground truth test cases live in `templates/{name}/evaluation/`. Each test case contains: the document bundle (as blob references), the expected field extraction results (human-verified), and the expected verdict (if full pipeline evaluation is included).

**Evaluation process:** `src/evaluation/` platform code runs extraction against all ground truth cases, compares results to expected values using exact match (for codes and identifiers) and normalized match (for numeric values with configurable tolerance). Results are reported as accuracy percentage per document type, per field, and overall.

**CI integration:** Template changes that include evaluation data trigger evaluation runs in CI. Evaluation failures (accuracy below threshold) fail the PR. This prevents template regressions from reaching production.

**Responsible AI gate:** The evaluation framework is also the Responsible AI gate - it produces the accuracy evidence required for ARIA's TRANSPARENCY_FAQ.md and for government procurement AI transparency requirements.

### Rationale

Architecture Principle AP-10 ("measurable accuracy before production") reflects a fundamental product responsibility: ARIA's decisions affect real people in regulated contexts (food safety, immigration, healthcare). Deploying a system with unknown or insufficient accuracy is an IP liability and a customer harm risk.

The 85% threshold is a working baseline - at 85% field extraction accuracy, the cross-document validation and policy evaluation stages catch the remaining ambiguities and route cases to human review appropriately. Below 85%, the rate of incorrect AI decisions rises to unacceptable levels.

### Alternatives Considered

**Optional evaluation framework:** Run evaluations when convenient. Rejected because optional gates are routinely skipped under delivery pressure.

**Post-production accuracy monitoring only:** Monitor extraction accuracy in production and remediate. Rejected because production errors in regulated environments have legal and reputational consequences that cannot be remediated retroactively.

**Fixed 85% threshold for all deployments:** A single threshold for all document types and industries. Partially accepted as the default - but the threshold is configurable per template because some document types (handwritten forms, low-quality scans) may have inherently lower achievable accuracy that is still acceptable for the use case.

### Consequences

**Positive:**
- AI decision quality is measurable and verified before production deployment
- Template regressions caught at PR time (CI evaluation gate)
- Evaluation results provide Responsible AI evidence for procurement and regulatory transparency requirements

**Negative / Trade-offs:**
- Ground truth dataset authoring requires domain expert time and real document samples - this is the most significant onboarding cost for new templates
- 85% threshold may require iteration on `evidence_types.json` field definitions before a template achieves go-live - this is by design (the gate forces template quality improvement)
- CI evaluation runs add pipeline time (evaluation against 20+ cases may take 5–10 minutes per CI run)

---

## ADR Catalog Summary

**Total ADRs in catalog:** 28
**Date range:** ADR-001 through ADR-008 (2026-08-07) · ADR-009 through ADR-028 (2026-08-10)
**Status breakdown:** 14 Accepted · 12 Accepted - Design · 2 Proposed

**Decisions by impact area:**
- **Token efficiency:** ADR-011 · ADR-012 · ADR-013 · ADR-014 · ADR-015 · ADR-016 · ADR-017 · ADR-018 · ADR-027 (9 decisions)
- **Platform architecture and governance:** ADR-001 · ADR-002 · ADR-009 · ADR-010 · ADR-024 · ADR-025 · ADR-028 (7 decisions)
- **Security:** ADR-004 · ADR-006 · ADR-021 (3 decisions)
- **AI and agent design:** ADR-005 · ADR-007 · ADR-022 · ADR-023 (4 decisions)
- **Data and infrastructure:** ADR-003 · ADR-019 · ADR-020 (3 decisions)
- **Integration and delivery:** ADR-008 (1 decision)
- **Deployment:** ADR-026 (1 decision)

---

*End of ARIA ADR Catalog*
*Version 1.0 · 2026-08-10*
*Architecture Governance Lead sign-off required before publishing to partner ecosystem*
*Next review: when any open decision from 11-Architecture-Input-Pack.md Section 13 is resolved*
