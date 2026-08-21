---
title: ARIA Adoption Guide
description: Guided learning, workflow assessment, solution-fit design, pilot planning, and production-readiness checks for adopting ARIA
author: Microsoft
ms.date: 2026-08-21
ms.topic: how-to
keywords:
  - ARIA
  - adoption
  - assessment
  - regulatory inspection
  - evidence-to-decision
estimated_reading_time: 12
---

## Purpose

Use this guide to decide whether ARIA fits an existing product or operational workflow and to define the work required for a safe pilot. The process starts with the business decision, not the technology.

The expected outputs are:

- A documented candidate workflow and business owner
- A scored fit assessment
- A target solution map
- An industry-template backlog
- An integration plan
- A representative evaluation set
- Pilot success measures and production-readiness gates

## Prerequisites

Before starting the assessment, identify:

| Prerequisite | What you need |
|---|---|
| Business owner | Person accountable for the review workflow and business outcome |
| Domain reviewers | People who perform or supervise the current review |
| Candidate cases | At least 20 representative cases, including failures and edge cases |
| Document inventory | Document types, formats, languages, sources, and typical bundle size |
| Decision policy | Current rules, reference data, thresholds, and outcome vocabulary |
| Integration owner | Team responsible for the source portal, case system, or API |
| Governance owner | Security, privacy, responsible AI, records, and compliance stakeholders |
| Azure sponsor | Subscription, identity, networking, quota, and cost ownership for a future pilot |

Do not use production personal or regulated data during discovery unless the required approvals and controls are already in place.

## Learning module

Complete this module before the assessment workshop. It should take 45 to 60 minutes.

### Lesson 1: Understand the problem ARIA solves

ARIA supports decisions that depend on a bundle of related evidence. It is designed for workflows where reviewers must extract facts, compare documents, apply policy, and explain a recommendation.

Review:

- [Solution overview](../README.md#solution-overview)
- [Business use case](../README.md#business-use-case)
- [Where ARIA delivers value](../README.md#where-aria-delivers-value)

### Lesson 2: Understand the agentic workflow

Learn how the Pre-Validation, Document Extraction, Reasoning, Rules and Policy, and Recommendation and Delivery agents cooperate under Durable Functions orchestration.

Review:

- [Agentic framework](../README.md#agentic-framework)
- [Technical Architecture](architecture/TechnicalArchitecture.md)

### Lesson 3: Understand what changes for an adopter

The Core Platform stays domain-neutral. Adoption work belongs primarily in:

- The industry template
- Source-system and callback connectors
- Security and network configuration
- Evaluation data and acceptance thresholds
- Operational ownership and human-review procedures

Review:

- [Customize an Industry Template](CustomizeIndustryTemplate.md)
- [Connector contract](../connectors/sdk/base_connector.py)

### Lesson 4: Experience the target workflow

Open the [Inspection Workbench](../reference-implementations/pafn-food-inspection/ui/index.html), load the sample case, and run the inspection. Review the evidence viewer, recommendation, findings, and decision trace.

The browser demo is synthetic and does not execute the Azure backend.

## Workflow assessment

Score each statement from 0 to 2:

- `0` - Not true or unknown
- `1` - Partly true or requires significant work
- `2` - Clearly true and supported by evidence

| Area | Assessment statement | Score |
|---|---|---:|
| Case structure | Each review starts with a clearly identified case or request | 0-2 |
| Evidence bundle | A repeatable set of related documents supports the decision | 0-2 |
| Extraction | Reviewers repeatedly locate the same fields or entities | 0-2 |
| Reconciliation | Facts must agree across two or more documents | 0-2 |
| Policy | Documented rules or reference data influence the outcome | 0-2 |
| Decision | The workflow has clear recommendation or outcome labels | 0-2 |
| Explainability | Reviewers must explain why an outcome was recommended | 0-2 |
| Human review | A named role remains accountable for the final decision | 0-2 |
| Data quality | Representative historical cases and expected outcomes are available | 0-2 |
| Integration | A source system can upload documents and exchange case status | 0-2 |
| Governance | Security, privacy, records, and responsible AI owners are engaged | 0-2 |
| Scale | Current volume or review effort justifies automation | 0-2 |

### Interpret the score

| Score | Guidance |
|---|---|
| 19-24 | Strong pilot candidate. Proceed to target design and evaluation planning. |
| 13-18 | Potential fit. Resolve the lowest-scoring prerequisites before implementation. |
| 0-12 | Do not start implementation. Clarify the workflow, policy, data, or ownership first. |

A high score does not replace security, responsible AI, legal, or regulatory review.

## Product and project fit

Map the current workflow to the target solution:

| Current workflow element | ARIA target | Adoption decision |
|---|---|---|
| Portal or case-management system | Adopting system | Keep, extend, or replace only the integration surface |
| Document repository | Blob upload connector | Define upload ownership, paths, identity, and retention |
| Submission metadata | Intake API | Define the case identifier, document metadata, and callback contract |
| Manual field lookup | Document Extraction Agent | Define fields, aliases, formats, and confidence thresholds |
| Manual comparison | Reasoning Agent | Define evidence relationships and expected semantic assessment |
| Policy checklist | Rules and Policy Agent | Convert approved rules and reference data into configuration |
| Reviewer recommendation | Recommendation and Delivery Agent | Define decision vocabulary, reasons, and evidence trace |
| Existing audit process | Audit and telemetry | Define events, retention, access, and reconstruction requirements |
| Reviewer workstation | Existing portal or reference UI | Decide where recommendations and evidence will be reviewed |

### Keep adopter-specific behavior outside the Core Platform

The following should normally remain in templates, connectors, or deployment configuration:

- Organization and product names
- Document and field vocabulary
- Policy rules and code lists
- Decision labels
- Portal URLs and callback behavior
- Tenant-specific credentials and network settings
- Data retention and records policy

## Pilot design

### Define the template backlog

Document:

- Evidence types and mandatory combinations
- Target fields and expected formats
- Known aliases and language variations
- Cross-evidence relationships
- Policy rules and reference sources
- Risk and human-review thresholds
- Recommendation labels and reason codes
- PII and sensitive-field classifications

Start with the [food safety template](../templates/food-safety/template.json) as a structural example.

### Define integration responsibilities

Agree who owns:

- Document upload and confirmation
- Case submission and idempotency
- Callback or status retrieval
- Authentication and authorization
- Network access and private endpoints
- Error handling and retry behavior
- Reconciliation and support escalation

### Build the evaluation set

Include:

- Normal passing cases
- Valid cases requiring human judgment
- Missing mandatory evidence
- Conflicting values across documents
- Expired or invalid certificates
- Low-quality and unreadable documents
- Bilingual or multilingual evidence
- Technical submission and processing failures

For each case, record the reviewer-approved extraction, findings, recommendation, and reason.

## Pilot success measures

Define targets before implementation:

| Measure | Example question |
|---|---|
| Extraction accuracy | Are critical fields extracted correctly? |
| Conflict detection | Are known discrepancies found without excessive false alerts? |
| Rule accuracy | Do deterministic findings match approved policy? |
| Recommendation agreement | How often does the recommendation match the approved reviewer outcome? |
| Review efficiency | Does ARIA reduce handling time for routine and exception cases? |
| Explainability | Can reviewers understand and verify each reason? |
| Reliability | Are retries, failures, and reconciliation handled without lost cases? |
| Cost | Is Azure consumption acceptable at expected case volume? |

## Production-readiness gates

Do not move from pilot to production until all applicable gates are approved:

- Business owner accepts the workflow and operating model
- Domain owner approves rules, reference data, and decision vocabulary
- Evaluation meets documented accuracy and quality thresholds
- Human-review and override procedures are tested
- Security architecture and threat model are approved
- Privacy, PII, records, and retention requirements are implemented
- Responsible AI assessment and transparency obligations are complete
- Integration retries, reconciliation, and support ownership are tested
- Monitoring, token usage, cost, and operational alerts are configured
- Rollback, incident response, and change-management procedures are documented

## Next steps

1. Run a 60- to 90-minute assessment workshop using the scoring table.
2. Select one bounded workflow and 20 representative cases.
3. Create the target solution map and template backlog.
4. Record open decisions, owners, and acceptance measures.
5. Track platform readiness in [GitHub Issues](https://github.com/microsoft/ai-regulatory-inspection-accelerator/issues) before committing to deployment.