---
title: ARIA Phase 2 Backlog
description: Post-hackathon implementation backlog for production hardening and platform completeness
ms.date: 2026-09-12
ms.topic: roadmap
keywords:
  - ARIA
  - Phase 2
  - backlog
  - production readiness
---

## Purpose

The hackathon scope demonstrates the ARIA evidence-to-decision flow with
synthetic scenarios, deterministic policy behavior, risk scoring, review
primitives, audit primitives, and Azure-hosted browser delivery. The following
work remains in Phase 2 and is intentionally not represented as complete in
the hackathon demo.

## Phase 2 work items

| Epic | Workstream | Phase 2 deliverable | Exit evidence |
|---|---|---|---|
| #10 | Document Intelligence | Persist the full extraction artifact set, integrate measured Azure DI accuracy, and run labelled dual-phase token benchmarks | Corpus report, artifact replay, and approved accuracy threshold |
| #11 | Reconciliation | Add labelled conflict/coherence evaluation, production indexing, and canonical evidence lineage | Conflict precision/recall report and replayable evidence map |
| #12 | Policy Evaluation | Load rules at runtime from Cosmos with ETag pinning, seed templates, and persist every finding | Rule replay test with pinned ETags and eight-category coverage |
| #13 | Risk Assessment | Calibrate thresholds/weights, add historical indexing where approved, and validate risk/recommendation distributions | Approved calibration set and policy-owner sign-off |
| #14 | Decision Recommendation | Complete evidence-chain assembly, PII display/secured projections, callback audit, and live connector verification | Signed delivery integration test and audit package |
| #15 | Human Review | Add grounded conversational adapter, AI Search retrieval, template chat tools, reviewer queue, feedback, and role enforcement | Reviewer workflow test with citations and authorization cases |
| #16 | Governance and Audit | Wire all state, LLM, rule, delivery, and human events into durable audit storage with retention and export | End-to-end audit export and point-in-time reconstruction |
| #17 | Template Framework | Complete schema/completeness CI, install/activate/version/deactivate tooling, Knowledge Pack activation, and compatibility checks | New industry onboarded without platform code changes |
| #18 | Connector Framework | Add file, SharePoint, and Dynamics adapters, manifests, registration, isolation checks, and connector CI | Connector contract suite and one end-to-end external-system test |
| #19 | Deployment and Operations | Complete deployment topologies, evaluation gate, monitoring dashboards, private networking, and operational runbooks | Repeatable deployment and approved operations readiness review |

## Hackathon boundary

The hosted demo at
<https://stariainfra.z13.web.core.windows.net/> remains a deterministic,
browser-local walkthrough. It uses synthetic English, Arabic, customs, KYC,
and insurance scenarios. Its public configuration points to the deployed APIM
and Function App endpoints, but live authenticated submission is a Phase 2
integration path.

The hybrid document strategy is intentional: deterministic preprocessing and
Azure Document Intelligence are the common path; AI vision is reserved for
handwriting, mixed-script, poor-quality, or ambiguous evidence.

## Completion rule

An epic moves from Phase 2 to complete only when its exit evidence exists and
is linked from the issue. A passing unit test alone does not close a workstream
that requires Azure integration, labelled-case measurement, security approval,
or operational validation.
