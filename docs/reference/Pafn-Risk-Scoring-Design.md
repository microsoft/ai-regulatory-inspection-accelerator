---
title: PAFN Risk Scoring Design Reference
description: Reference implementation of deterministic 0-100 document, item, rule, and case risk scoring
ms.date: 2026-09-12
ms.topic: reference
---

## Purpose

This document preserves the PAFN reference policy that informed ARIA. It is
not a platform default. ARIA uses a normalized 0.00-1.00 model; the PAFN
compatibility implementation is available in
`src/platform/policy/pafn_risk_assessment.py`.

## Threshold policy

The reference policy is versioned as `RISK_SCORING_THRESHOLDS` in the rules
store:

```json
{
  "id": "RISK_SCORING_THRESHOLDS",
  "version": "1.0",
  "qualityScoreThreshold": 0.75,
  "fieldConfidenceThreshold": 0.85,
  "documentConfidenceThreshold": null,
  "findingConfidenceThreshold": 0.50,
  "riskBands": [
    {"name": "Low", "minimum": 0, "maximum": 39},
    {"name": "Medium", "minimum": 40, "maximum": 74},
    {"name": "High", "minimum": 75, "maximum": 100}
  ]
}
```

## Document scoring

For populated fields:

```text
FieldPass = 1 when FieldConfidence >= 0.85; otherwise 0
DocumentConfidenceScore = 100 * PassedFieldCount / PopulatedFieldCount
```

`DocumentRiskScore` is 40 when quality is below 0.75, when quality passes but
no fields are populated, or when the configured document-confidence threshold
is not met. Otherwise it is zero. The maximum document score is used across
the case. Low quality requires manual review and never rejects by itself.

## Cross-document behavior

Matching values pass when at least one occurrence meets the confidence
threshold. Differing values use the configured mismatch rule. If all
occurrences are below the confidence threshold, the conflict is unconfirmed
and manual review is required. Low confidence alone never rejects.

## Item and rule scoring

```text
ItemRiskScore = maximum violated item-rule score for the item
OverallItemRiskScore = maximum ItemRiskScore across items
OverallRuleRiskScore = maximum violated non-item rule score
CaseRiskScore = maximum(MaxDocumentRiskScore, OverallItemRiskScore, OverallRuleRiskScore)
```

Warnings or conditional mismatches may score 40. Material mismatches and
failed item checks may score 75. A prohibited rule explicitly configured with
`REJECT` may score 100.

## Recommendation

1. If a violated rule is explicitly configured with `REJECT`, return `REJECT`.
2. Otherwise, if `CaseRiskScore >= 40`, return `ACCEPT_WITH_WARNING`.
3. Otherwise, return `ACCEPT`.

## Audit record

Persist one immutable `risk-evaluations` record per request containing
per-document scores, per-item scores, maximum rule components, case score,
risk band, recommendation, policy versions, policy snapshot, review reasons,
and evaluated rule outcomes. Review assignments and overrides are append-only
records. The original computed values remain unchanged.

## Open policy decisions

The document-confidence threshold, denominator selection, warning-versus-
material tolerances, rule scores, manual-review SLA, and ownership model
require domain approval and calibration against labelled cases.
