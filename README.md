<div align="center">

# ARIA - AI Regulatory Inspection Accelerator

<strong>Evidence to decision for regulated multi-document review.</strong><br>
Extract facts. Reconcile evidence. Apply policy. Explain the recommendation.

<br>

[**SOLUTION OVERVIEW**](#solution-overview) &nbsp;|&nbsp; [**TRY THE DEMO**](#try-the-demo) &nbsp;|&nbsp; [**BUSINESS USE CASES**](#business-use-cases) &nbsp;|&nbsp; [**ARCHITECTURE**](#agentic-framework) &nbsp;|&nbsp; [**GUARDRAILS**](#guardrails-security-and-responsible-ai) &nbsp;|&nbsp; [**SETUP**](#setup) &nbsp;|&nbsp; [**TEMPLATES**](#reference-templates)

</div>

ARIA turns a related evidence bundle into a reviewable recommendation. It extracts facts, reconciles them across documents, applies deterministic policy rules, scores risk, and preserves the evidence and timing trace for a human reviewer. Each review also produces governed signals that teams can use to improve reusable templates, rules, prompts, and delivery patterns.

The reference implementation supports English and Arabic documents, including mixed right-to-left content. Additional languages can be added through reviewed evaluation data, field aliases, normalization, and domain templates.

## Solution overview

ARIA treats the case, not the individual document, as the unit of review:

1. **Validate** the submission and mandatory evidence.
2. **Extract** structured facts from each document.
3. **Reconcile** shared fields across the bundle.
4. **Evaluate** deterministic policy rules and risk.
5. **Deliver** an explainable recommendation for human review.

The first reference implementation covers food import inspection with invoices, declarations, health certificates, certificates of origin, and Halal certificates. The platform packages these capabilities separately from domain configuration, allowing a proven implementation to become a reusable starting point rather than a one-off delivery.

Reviewer approvals, overrides, rework, processing time, quality outcomes, and token telemetry form a governed feedback loop. Teams can use those signals to refine reusable assets and compare successive runs, making improvements in quality and efficiency visible instead of resetting learning for each deployment.

The supplied solution architecture shows the broader Azure entry, AI, persistence, processing, monitoring, and analytics layers. Deployment-specific services can be selected or substituted by each adopter.

![ARIA Azure solution architecture across customer entry, orchestration, AI services, processing, persistence, operations, and analytics](docs/images/readme/solution-architecture.png)

## Try the demo

* [Open the hosted Inspection Workbench](https://stariainfra.z13.web.core.windows.net/index.html)
* [Open the hosted Token Analytics dashboard](https://stariainfra.z13.web.core.windows.net/tokens.html)
* [Read the demo walkthrough](docs/HackathonDemo.md)

<video controls preload="metadata" width="100%">
  <source src="media/ARIA-Demo-with-speech.mp4" type="video/mp4">
  Your browser does not support embedded video. [Watch or download the ARIA demo](media/ARIA-Demo-with-speech.mp4).
</video>

The current incremental demo runs on the project Azure deployment. Synthetic mode uses curated samples and projected analytics; Live Azure processes uploaded documents and displays provider-measured telemetry.

### Demo steps

1. Open the [hosted Inspection Workbench](https://stariainfra.z13.web.core.windows.net/index.html), or complete the [sample demo setup](#sample-demo-setup) for a local preview.
2. Keep **Synthetic** mode selected.
3. Choose a scenario, select **Load sample case**, and then select **Run inspection**.
4. Review the recommendation, findings, cross-document checks, confidence, and decision trace.
5. Open the [hosted Token Analytics dashboard](https://stariainfra.z13.web.core.windows.net/tokens.html) to compare projected and provider-measured operations views.

Synthetic mode is intentionally sample-only and does not inspect uploaded documents. Select **Live Azure** to process actual documents with the current Azure-backed demo. The hosted environment is an incremental demonstration, not a production service; adopters should deploy the solution into their own subscription for sustained use.

## Business use cases

ARIA is designed for decisions that depend on several documents agreeing:

| Domain | Evidence bundle | Reviewer outcome |
|--------|-----------------|------------------|
| Food import inspection | Invoice, declaration, health and Halal certificates | Pass, hold, or fail |
| Customs clearance | Bill of lading, declaration, invoice, origin certificate | Clear, hold, or detain |
| KYC and AML | Identity, ownership, address, and transaction records | Approve, review, or reject |
| Healthcare authorization | Request form, clinical notes, and policy evidence | Authorize, review, or deny |
| Licensing and certification | Application, credentials, and prior certificates | Approve, provision, or deny |

![ARIA business use case showing evidence flowing through extraction, reconciliation, and policy checks to a human-reviewed recommendation](docs/images/readme/business-use-case.png)

The Inspection Workbench brings source evidence, cross-document findings, policy results, risk, and the human-controlled recommendation into one review surface.

![ARIA Inspection Workbench showing a food inspection evidence bundle and a hold recommendation with linked findings](docs/images/readme/inspection-workbench.png)

The companion operations view makes token use, provider cache reuse, model cost, and telemetry coverage inspectable by case and processing stage.

![ARIA Token Analytics showing measured provider telemetry, cache reuse, and same-model cost comparison](docs/images/readme/token-analytics.png)

### Token and cache economics

The Token Analytics dashboard separates measured provider telemetry from modeled comparisons. For each Azure OpenAI call, ARIA records input, output, total, and provider-reported cached-input tokens, together with model, activity, latency, case, and timestamp metadata. Prompts, model responses, and document content are not stored in the telemetry container.

Azure OpenAI manages prompt caching. ARIA improves cache eligibility by placing stable instructions and schema context before variable evidence, then reads `prompt_tokens_details.cached_tokens` from the provider response. Cosmos DB persists that measurement so usage can be compared over time; it does not perform the model cache lookup.

The dashboard prices the observed workload at published model rates and compares it with the same model and token volume with caching disabled. Only records marked as provider-measured receive a cached-input discount. Historical estimates remain visible for audit context but are excluded from measured cache savings.

See [How Caching Works in ARIA](docs/architecture/TechnicalArchitecture.md#6-token-efficiency) for the platform strategy.

### Reusable capabilities across use cases

| Capability | ARIA outcome |
|------------|--------------|
| Evidence bundle | One case view across invoices, declarations, certificates, and supporting records |
| Document understanding | Azure AI Document Intelligence plus Azure OpenAI structured extraction |
| Cross-document integrity | Canonical fields, aliases, unit normalization, and conflict detection |
| Policy boundary | Deterministic rules and risk scoring remain outside the model |
| Explainability | Findings link values, documents, rules, actions, and stage timings |
| Human control | The system recommends; the reviewer decides and can override with a reason |
| Operational governance | Cosmos DB telemetry, token attribution, cost views, and auditable case history |
| Compounding reuse | Reviewer feedback and delivery telemetry guide improvements to shared templates, rules, prompts, and evaluation assets |

## Implementation

The tested reference implementation combines a domain-neutral platform, configurable industry templates, and isolated connectors:

* Python Azure Functions, Durable Functions, and Azure API Management
* Azure AI Document Intelligence and Azure OpenAI structured extraction
* Deterministic reconciliation, policy, risk, delivery, and audit components
* Industry configuration under `templates/` and integration contracts under `connectors/`

The live path extracts documents concurrently, reports per-document duration, and keeps telemetry persistence off the response critical path. Automated tests cover orchestration, extraction, reconciliation, policy, risk, telemetry, templates, delivery, and audit behavior.

Technical setup, security, deployment topology, and local development instructions are maintained in the [Technical Architecture](docs/architecture/TechnicalArchitecture.md), [Deployment Guide](docs/DeploymentGuide.md), and [Local Development Setup](docs/LocalDevelopmentSetup.md).

## Agentic framework

Azure Durable Functions coordinates five specialized processing agents and a separate risk-persistence activity. Each agent has a narrow responsibility, passes an inspectable contract to the next stage, and routes failures to delivery so the adopting system receives a traceable outcome.

![ARIA five-agent evidence-to-decision framework coordinated by Durable Functions](docs/images/readme/agentic-framework.png)

```mermaid
flowchart LR
  U[Adopting system] --> A[API Management]
  A --> O[Durable orchestrator]
  O --> I[Pre-validation agent]
  I --> E[Document extraction agent]
  E --> R[Reasoning and reconciliation agent]
  R --> P[Rules and policy agent]
  P --> RP[Risk persistence activity]
  RP --> C[(Cosmos DB)]
  P --> D[Recommendation and delivery agent]
  D --> H[Human reviewer]
  E --> DI[Azure AI Document Intelligence]
  E --> AO[Azure OpenAI]
  P --> T[Industry template]
  D --> C
  AO --> TM[Provider token metadata]
  TM --> C
  C --> AN[Token and operations analytics]
  H --> F[Governed feedback]
  F --> T
```

The detailed architecture, security model, data flow, and Azure topology are in the [Technical Architecture](docs/architecture/TechnicalArchitecture.md).

## Guardrails, security, and Responsible AI

ARIA embeds guardrails, security, and Responsible AI principles throughout the evidence-to-decision lifecycle. These measures help ensure that every recommendation is secure, explainable, auditable, and subject to meaningful human oversight.

### Responsible AI

Recommendations remain explainable and traceable to source evidence, deterministic rules, risk components, model and policy versions, timestamps, and reviewer actions. Before production use, adopters must evaluate representative languages, document types, demographic groups, and edge cases. Human oversight, bias evaluation, privacy assessment, security testing, continuous monitoring, and regulatory approval are mandatory deployment gates.

### Guardrails

ARIA separates probabilistic AI extraction from deterministic policy evaluation and risk scoring. It validates model outputs, applies confidence and document-quality thresholds, detects missing or conflicting evidence, and escalates uncertain cases for human review. Models are instructed not to invent values, and reviewers retain final decision authority with documented overrides.

### Security

The solution uses managed identities, role-based access control, encrypted communications, protected secrets, authenticated APIs, request validation, file-integrity checks, and least-privilege access to Azure resources. Rate and payload limits help protect AI services from misuse and cost exhaustion. Sensitive data is minimized, access-controlled, and retained according to applicable privacy and regulatory requirements.

### Accessibility

The reference web interfaces support skip navigation, keyboard-visible focus,
semantic status and progress announcements, accessible data tables and charts,
reduced-motion preferences, and keyboard-safe dialogs. Adopters must validate
their configured deployment against Microsoft accessibility guidance and
applicable WCAG 2.1 Level AA requirements before production use.

## Setup

### Sample demo setup

The hosted demo is available from the [Inspection Workbench](https://stariainfra.z13.web.core.windows.net/index.html). For a local preview, Python is required only as a static-file server. Synthetic mode uses no Azure resources and accepts no document uploads.

```powershell
git clone https://github.com/microsoft/ai-regulatory-inspection-accelerator.git
cd ai-regulatory-inspection-accelerator
python -m http.server 4173 --directory reference-implementations/food-inspection/ui
```

Open <http://localhost:4173/index.html>, choose a scenario, and select **Load sample case**.

### Deploy your own Azure environment

The repository currently points to the project Azure demo through public, non-secret APIM endpoints. For sustained use, deploy an environment in your Azure subscription:

1. Follow the [Deployment Guide](docs/DeploymentGuide.md) to provision the Azure resources in your subscription.
2. Create the Git-ignored local configuration at the path loaded by the workbench:

  ```powershell
  Copy-Item reference-implementations/food-inspection/ui/config.local.example.js reference-implementations/food-inspection/ui/config.local.js
  ```

  Open <http://localhost:4173/index.html?config=local> to load the local endpoint
  override.

3. Set `liveEndpoint` and `telemetryEndpoint` to your public APIM routes. Endpoint and resource names are not secrets.
4. Keep credentials, keys, and connection strings in Azure Key Vault, APIM named values, or server-side application settings. Never place them in browser configuration.
5. Serve the workbench locally. **Live Azure** and actual-document upload become available when the endpoint is configured.

For development prerequisites and local Function execution, see [Local Development Setup](docs/LocalDevelopmentSetup.md).

## Reference templates

An industry template separates reusable platform code from domain policy. The food-safety reference includes:

* `evidence_types.json` - mandatory and optional document types
* `submission_schema.json` - case and document submission contract
* `rules.json` - deterministic policy checks
* `rule_risk_scores.json` and `risk_scoring_thresholds.json` - severity and risk bands
* `normalization.json` - units, aliases, and canonical values
* `decision_vocabulary.json` - reviewer-facing outcomes
* `reference_data.json` and `knowledge_pack.json` - approved authorities and domain context

Use the same structure for customs, KYC, healthcare authorization, licensing, insurance, or another regulated workflow. Template schemas are under `templates/_schema/`.

Example mandatory evidence configuration:

```json
{
  "evidenceTypes": [
    { "id": "commercial_invoice", "required": true },
    { "id": "health_certificate", "required": true },
    { "id": "certificate_of_origin", "required": true },
    { "id": "halal_certificate", "required": false }
  ]
}
```

## Future scope

* A grounded case chatbot for reviewer questions, evidence citations, and reasoning exploration
* Reviewed multi-language packs with language-specific evaluation and abstention tests
* Longitudinal quality and efficiency curves across successive governed deployments
* Broader industry templates and connector implementations

## Repository map

```text
src/platform/                 Domain-neutral processing components
templates/                    Industry evidence, field, rule, and decision configuration
connectors/                   Integration contracts and adapters
reference-implementations/    Isolated adopter examples and workbench UI
media/                        Demo assets
infra/infra/                  Azure Terraform infrastructure
docs/                         Architecture, deployment, evaluation, and adoption material
tests/                        Automated platform and policy tests
```

## Documentation

* [Technical Architecture](docs/architecture/TechnicalArchitecture.md)
* [Arabic-English Evaluation Standard](docs/ArabicEnglishEvaluation.md)
* [Customize an Industry Template](docs/CustomizeIndustryTemplate.md)
* [Deployment Guide](docs/DeploymentGuide.md)
* [Demo Walkthrough](docs/HackathonDemo.md)
* [Local Development Setup](docs/LocalDevelopmentSetup.md)
* [Adoption Guide](docs/AdoptionGuide.md)
* [Responsible AI Transparency FAQ](TRANSPARENCY_FAQ.md)

## License

See [LICENSE](LICENSE) for terms.
