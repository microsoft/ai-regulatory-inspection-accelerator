---
title: ARIA Risk Scoring Design
description: Generalized deterministic risk scoring, persistence, review, and override policy for ARIA
ms.date: 2026-09-12
ms.topic: concept
---

## Status and scope

ARIA provides a domain-neutral normalized risk model. Templates own
thresholds, rule scores, actions, bands, and public recommendations.

The canonical ARIA score is `0.00` to `1.00`:

```text
caseQualityImpact = max(document quality impacts, default 0.00)
caseExtractionRisk = max(document extraction risks, default 0.00)
caseRuleSeverity = max(violated rule weights, default 0.00)
compositeRiskScore = min(1.00, caseQualityImpact + caseExtractionRisk + caseRuleSeverity)
```

Risk classification is separate from disposition. `HOLD` is the default for
review-band or uncertain evidence. Only an applicable violated rule with an
explicit `REJECT` action can produce `FAIL`.

## Template policy

Templates provide `risk_weight_matrix.json`, `risk_threshold_bands.json`, and
`decision_vocabulary.json`. Policy is versioned and copied into every persisted
evaluation. The platform must never infer rejection from score magnitude alone.

The default components are configurable:

* Quality Impact when quality is below the configured quality threshold
* Extraction Risk when a configured field or populated item field is below the
  field-confidence threshold
* Rule Severity from the maximum violated rule weight

Passed and not-applicable rules contribute zero. Repeated documents, items, or
findings do not multiply a component.

## Document and item attribution

Each document records quality, populated field count, low-confidence fields,
quality impact, extraction risk, and review reasons. Each item records its
maximum linked violated-rule weight and contributing rule identifiers. Item
risk is attribution data and is not added a second time to the case score.

Cross-evidence comparisons use the highest-confidence occurrence when values
match. When all occurrences are below the confidence threshold, the conflict
remains unconfirmed and the case requires review.

## Persistence contract

The canonical logical store is `risk-evaluations`, partitioned by
`/requestId`. Each immutable record contains:

* Composite score, component breakdown, risk level, and internal decision
* Per-document and per-item assessments
* Findings and rule actions
* Manual-review state and reasons
* Template, threshold, band, and rule-policy versions
* The complete policy snapshot used for calculation
* Computed decision and any later effective decision projection
* Immutable override events

The durable pipeline persists the evaluation before completed decision delivery.
The physical Cosmos container is configurable as
`COSMOS_DB_RISK_EVALUATIONS_CONTAINER`, defaulting to `risk-evaluations`.

## Review and override API

The platform exposes these authenticated case operations:

* `GET /api/cases/{requestId}/risk-evaluations/latest`
* `GET /api/cases/{requestId}/risk-evaluations`
* `PATCH /api/cases/{requestId}/reviews/{reviewId}/assignment`
* `POST /api/cases/{requestId}/risk-evaluations/{evaluationId}/overrides`

An override requires actor identity, field, old value, new value, rationale,
and authorization. It appends an immutable event and never changes the
computed score or policy snapshot.

## Reference 0-100 model

The configurable reference model is implemented separately in
`src/platform/policy/reference_risk_assessment.py`. It retains the exact
0-100 reference semantics:

```text
DocumentConfidenceScore = 100 * PassedFieldCount / PopulatedFieldCount
DocumentRiskScore = 40 for low quality, no populated fields, or failed document confidence
ItemRiskScore = maximum violated item-rule score
OverallItemRiskScore = maximum item score
OverallRuleRiskScore = maximum violated non-item rule score
CaseRiskScore = maximum(MaxDocumentRiskScore, OverallItemRiskScore, OverallRuleRiskScore)
```

Rule actions are explicit. An explicit `REJECT` rule returns `REJECT`;
otherwise a score of 40 or greater returns `ACCEPT_WITH_WARNING`, and zero
returns `ACCEPT`. This compatibility scorer is deterministic and does not
replace ARIA's normalized platform score.

## Validation requirements

Every template must test clean evidence, quality-only review,
extraction-only review, combined uncertainty, warning and material findings,
explicit rejection, repeated records, cross-evidence confidence, boundary
scores, policy replay, review assignment, and authorized and unauthorized
overrides.

Numeric defaults require domain-owner approval and calibration before
production use.
