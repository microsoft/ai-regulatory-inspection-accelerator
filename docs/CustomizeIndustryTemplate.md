---
title: Customize an Industry Template
description: Define and validate the fourteen artifacts in an ARIA industry template
author: ARIA Engineering
ms.date: 2026-08-24
ms.topic: how-to
---

The Core Platform consumes document definitions and normalization profiles from
the template. Rule lifecycle and activation tooling remain on the
[Roadmap](../README.md#roadmap).

## The 14 template artifacts

Every industry template is a directory under `templates/{industry-name}/` containing only JSON and Markdown - no executable code (enforced by CI once the domain-neutrality gate is active).

| Artifact | Purpose |
|---|---|
| `evidence_types.json` | Document types and field schemas for this industry |
| `normalization.json` | Content cleanup, quality thresholds, aliases, and field normalization behavior |
| `rules.json` | Compliance rule seed data |
| `reference_data.json` | Domain code lists and taxonomies |
| `submission_schema.json` | API gateway submission validation schema |
| `risk_weight_matrix.json` | Category risk weights |
| `risk_threshold_bands.json` | LOW/MEDIUM/HIGH/CRITICAL band thresholds |
| `alias_pairs.json` | Known field-name alias fast-path (e.g., multilingual synonyms) |
| `cross_validation_rules.json` | Cross-document comparison rules |
| `decision_vocabulary.json` | Outcome label mapping (e.g., PASS/HOLD/FAIL) |
| `pii_field_list.json` | PII field declarations |
| `chat_tools.json` | Domain-specific human review tools |
| `dashboard_config.json` | Domain KPI and alert thresholds |
| `evaluation/` | Ground truth test cases for the accuracy gate |

## Reference example

[`templates/food-safety/template.json`](../templates/food-safety/template.json) is
the populated reference manifest. Its `evidence_types.json` and
`normalization.json` files are consumed by the current Document Intelligence
pipeline. Use them as the starting shape for a new template.

## Add a template

1. Create `templates/{your-industry}/`
2. Author the 14 artifacts above
3. Validate against `templates/_schema/template.schema.json`
4. Run the template lifecycle tooling to seed rules to Cosmos DB and activate
5. Run the evaluation framework against your `evaluation/` ground truth set before enabling production traffic

## Today, you can

- Draft `evidence_types.json`, `normalization.json`, `decision_vocabulary.json`, and `pii_field_list.json` for your target industry
- Open an issue to discuss a new industry template before drafting it, to avoid duplicate work
