# ARIA - AI Regulatory Inspection Accelerator

ARIA helps regulated teams review a group of related documents as one case. It extracts key facts, compares information across documents, applies configurable rules, and produces an explainable recommendation for a human reviewer.

Use ARIA when a decision depends on **several documents that must agree**, not when you only need OCR or extraction from one document.

> **Implementation Status:** ARIA is fully functional and includes both an **Enterprise Production Deployment Path** (Azure Durable Functions, Azure OpenAI, Document Intelligence, Cosmos DB, Key Vault Zero-Secrets Architecture, and APIM) and an **Interactive Hosted Hackathon Demo**.

<div align="center">

[**PRODUCTION DEPLOYMENT GUIDE**](docs/DeploymentGuide.md) | [**HACKATHON DEMO GUIDE**](docs/HackathonDemo.md) | [**SOLUTION OVERVIEW**](#solution-overview) | [**LOCAL DEV SETUP**](docs/LocalDevelopmentSetup.md) | [**ADOPTION PATH**](#adoption-path)

</div>

> With any AI solution built from this accelerator, you are responsible for assessing risks and complying with applicable laws, regulations, and organizational policies. See the [Responsible AI Transparency FAQ](TRANSPARENCY_FAQ.md).

---

## Getting Started

ARIA provides two distinct evaluation and deployment paths:

### 🚀 1. Enterprise Production Setup
For teams deploying ARIA into a production Azure environment with full infrastructure, zero-secrets security, and tokenomics governance:
- **[Enterprise Production Deployment Guide](docs/DeploymentGuide.md)** — Complete step-by-step instructions for provisioning Azure Durable Functions, Azure OpenAI (`aria-text-mini` & `aria-vision`), Document Intelligence, Cosmos DB, Key Vault, and API Management.
- **[Local Development & Testing Setup](docs/LocalDevelopmentSetup.md)** — Guide for running `pytest`, setting up Python virtual environments, and developing custom platform adapters.
- **[Troubleshooting & Diagnostics Guide](docs/TroubleshootingSteps.md)** — Diagnostic steps for production runtime issues, APIM policies, and quota limits.

---

### ⚡ 2. Quick Hackathon Demo
For evaluators looking to test the ARIA experience in 2 minutes without deploying Azure infrastructure:
- 🌐 **[Live Inspection Workbench](https://stariainfra.z13.web.core.windows.net/index.html)** — Interactive workbench with 5 multi-document scenario bundles (Food Safety English/Arabic, Customs, KYC, Insurance) and custom file upload.
- 📊 **[Live Token Analytics Dashboard](https://stariainfra.z13.web.core.windows.net/tokens.html)** — Real-time token consumption, 30-day forecast, model breakdown, and cost efficiency proof.
- **[Hackathon Demo & Walkthrough Guide](docs/HackathonDemo.md)** — Feature tour, synthetic vs. password-protected live mode switching (`aria2026`), and demo walkthrough steps.

---

## Solution overview

ARIA turns a multi-document evidence bundle into a reviewable recommendation:

1. **Validate** the submission and document references.
2. **Extract** structured facts from each document.
3. **Reconcile** facts across the complete bundle.
4. **Evaluate** configurable policy rules.
5. **Recommend** an outcome with reasons and evidence references.
6. **Escalate** uncertain or high-risk cases to a human reviewer.

### Solution architecture

![ARIA solution architecture showing the customer portal, Azure entry and orchestration, AI services, data services, processing agents, operations, and analytics](docs/images/architecture/reference-architecture.png)

The adopting system uploads documents and submits case metadata through an API. Azure Durable Functions coordinates the processing stages. Azure AI Document Intelligence and Azure OpenAI provide document extraction and reasoning capabilities. Azure Storage and Cosmos DB hold documents, case state, rules, and outcomes. The final recommendation is returned to the adopting system for human review.

For the detailed component design, security model, data architecture, and governing decisions, see the [Technical Architecture](docs/architecture/TechnicalArchitecture.md).

### Agentic framework

ARIA uses a coordinated set of agents. Each agent owns one clear part of the inspection, while Azure Durable Functions controls the sequence, retries, and case state.

![ARIA agentic framework showing the Durable Functions orchestrator, five specialized agents, adopting system, Azure AI services, data stores, platform operations, fault tolerance, and human review](docs/images/readme/agentic-framework.png)

[View the editable HTML diagram](docs/images/readme/agentic-framework.html).

| Agent | Responsibility | Main services |
|---|---|---|
| Pre-Validation Agent | Confirms that the case and document references are ready for processing | Blob Storage, Cosmos DB |
| Document Extraction Agent | Extracts and normalizes facts from each document | Azure AI Document Intelligence, Azure OpenAI |
| Reasoning Agent | Performs LLM-assisted semantic reasoning over normalized case evidence and produces a reviewer-readable evidence assessment | Azure OpenAI, Cosmos DB |
| Rules and Policy Agent | Applies deterministic policy rules and produces findings | Rules and reference data, Cosmos DB |
| Recommendation and Delivery Agent | Builds the explainable recommendation and returns it to the adopting system | Cosmos DB, callback/API integration |

The agents do not make the final regulated decision. They prepare a recommendation and evidence trace for the human reviewer.

---

## Business use case

A regulatory reviewer receives a case containing an application, invoices, declarations, certificates, and supporting evidence. A single case may contain different field names, languages, versions, and issuing authorities. The reviewer must confirm that the evidence is complete, compare key facts across the bundle, apply the latest policy, and explain the outcome.

Today, much of this work is performed manually. Reviewers open documents one by one, search for the same fields, reconcile differences, and consult separate rule sources. Review time and consistency depend heavily on individual experience, while the reasoning behind a decision can be difficult to reconstruct later.

ARIA processes the bundle as one case. It extracts relevant facts, identifies missing or conflicting evidence, applies configurable rules, and presents a recommendation with reasons for human review. Reviewers focus on exceptions and judgment rather than repetitive comparison.

![Business use case showing a multi-document evidence bundle flowing through ARIA extraction, reconciliation, and policy checks to an explainable recommendation reviewed by a human](docs/images/readme/business-use-case.png)

### Business value

- **Faster review** by automating repeated document comparison and rule checks
- **More consistent outcomes** by applying the same configured rules to every case
- **Clearer audit evidence** by linking findings to documents, fields, and rules
- **Faster policy updates** by changing configuration instead of application code
- **Human accountability** by keeping the reviewer responsible for the final decision

The first reference scenario is food import inspection. A shipment case contains an invoice, customs declaration, health certificate, certificate of origin, and sometimes a Halal certificate. ARIA can extract shipment facts, flag a weight or certificate mismatch, apply current inspection rules, and show the inspector why the case should pass, be held, or fail. The inspector remains responsible for the final decision.

---

## Where ARIA delivers value

ARIA delivers the most value when:

- A case contains multiple related documents.
- Reviewers repeatedly compare the same fields across those documents.
- Rules change more frequently than application code should.
- Every recommendation needs a clear reason and audit trail.
- A human must remain responsible for the final decision.
- Teams want to expand the same review pattern into additional regulated domains through configuration.

ARIA complements other Microsoft accelerators across the document-processing journey:

| Need | Recommended accelerator |
|---|---|
| Extract and map content from individual documents | [Content Processing Solution Accelerator](https://github.com/microsoft/content-processing-solution-accelerator) |
| Search, summarize, and chat over document collections | [Document Knowledge Mining Solution Accelerator](https://github.com/microsoft/Document-Knowledge-Mining-Solution-Accelerator) |
| Compare evidence, apply policy, and recommend a regulated decision | **ARIA** |

### Example use cases

| Use case | Typical evidence | Example outcome |
|---|---|---|
| Food import inspection | Invoice, declaration, health and Halal certificates | PASS, HOLD, FAIL |
| Customs clearance | Invoice, bill of lading, origin certificate, declaration | CLEAR, HOLD, DETAIN |
| KYC and AML review | Identity, ownership, and transaction records | APPROVE, REVIEW, REJECT |
| Healthcare authorization | Request form, clinical notes, policy evidence | AUTHORIZE, REVIEW, DENY |
| Licensing and certification | Application, credentials, prior certificates | APPROVE, PROVISIONAL, DENY |

---

## Adoption path

Use the [ARIA Adoption Guide](docs/AdoptionGuide.md) to move from an existing review workflow to a validated implementation.

1. **Prepare** - Confirm business ownership, Azure access, representative documents, and reviewer availability.
2. **Learn** - Complete the short learning module covering the evidence-to-decision flow, agent responsibilities, templates, integration, and human review.
3. **Assess** - Score the candidate workflow against document, rule, decision, integration, and governance criteria.
4. **Design** - Map the current process to ARIA components and identify adopter-specific configuration and connectors.
5. **Configure** - Define the industry template: evidence types, fields, aliases, rules, thresholds, PII, and decision vocabulary.
6. **Pilot** - Test representative happy paths, missing evidence, conflicts, low-quality documents, and technical failures against reviewer-approved outcomes.
7. **Operationalize** - Complete security, responsible AI, support, monitoring, cost, and production-readiness gates before deployment.

The repository is not currently a one-click deployable accelerator. The adoption guide can be used now for discovery, assessment, and pilot planning; production deployment depends on completion of the remaining platform and infrastructure work.

---

## Core concepts

### Core Platform

Domain-neutral processing code shared by every adoption: intake, extraction, reconciliation, rules, risk, recommendation, audit, and reporting.

### Industry Template

JSON and Markdown configuration that defines the evidence, fields, rules, thresholds, and decision vocabulary for one regulated domain.

### Reference Implementation

An isolated example that combines the Core Platform with an industry template and adopter-specific connectors. The first reference case is food import inspection.

```text
Core Platform + Industry Template + Connector = Adopted Solution
```

---

## Repository map

```text
src/platform/                 Domain-neutral processing components
templates/                    Industry configuration packages
connectors/                   Integration contracts and adapters
reference-implementations/    Isolated adopter examples and demos
infra/terraform/              Azure infrastructure work in progress
docs/                         Architecture, deployment, and customization guidance
tests/                        Unit and future integration tests
```

---

## Documentation

| Document | Use it when you need to |
|---|---|
| [ARIA Adoption Guide](docs/AdoptionGuide.md) | Learn the solution, assess a workflow, design the fit, and plan a pilot |
| [Technical Architecture](docs/architecture/TechnicalArchitecture.md) | Understand components, data flow, security, and Azure topology |
| [Customize an Industry Template](docs/CustomizeIndustryTemplate.md) | Define evidence types, fields, rules, and decisions for a new domain |
| [Deployment Guide](docs/DeploymentGuide.md) | Check deployment readiness and planned Azure setup |
| [Local Development Setup](docs/LocalDevelopmentSetup.md) | Check current local development readiness |
| [Phase 2 Backlog](docs/Phase2-Backlog.md) | Track post-hackathon production implementation and exit evidence |
| [Transparency FAQ](TRANSPARENCY_FAQ.md) | Review responsible AI considerations |
| [ARIA Risk Scoring Design](30-ARIA-Risk-Scoring-Design.md) | Review normalized scoring, persistence, review, and override behavior |
| [Reference 0-100 Risk Scoring](docs/reference/Reference-Risk-Scoring-Design.md) | Review the compatible 0-100 reference policy |
| [Contributing](CONTRIBUTING.md) | Contribute code, templates, tests, or documentation |

---

## Security and responsible use

The target architecture uses managed identity and Azure role-based access control for service-to-service access, Azure Key Vault for integration secrets, private networking where required, and an immutable audit trail for model calls, rule evaluations, and human actions.

ARIA produces recommendations, not autonomous high-stakes decisions. Adopters must define human-review thresholds, validate the solution with representative data, and complete security, privacy, responsible AI, and regulatory reviews before production use.

---

## Provide feedback

Have a question, find a bug, or want to request a feature? [Open an issue](https://github.com/microsoft/ai-regulatory-inspection-accelerator/issues).

## License

See [LICENSE](LICENSE) for terms.