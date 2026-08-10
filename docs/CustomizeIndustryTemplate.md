# Customize: Add a New Industry Template

**Status: Schema defined, engine not yet implemented.** The 13-artifact template contract below is architecturally fixed (see [Technical Architecture, Section 7](architecture/TechnicalArchitecture.md#7-template-framework)) and you can start drafting these artifacts today. The Core Platform engine that consumes them (`src/platform/`) has not been built yet, so a drafted template cannot be activated or run until that lands - see the [Roadmap](../README.md#roadmap).

## The 13 template artifacts

Every industry template is a directory under `templates/{industry-name}/` containing only JSON and Markdown - no executable code (enforced by CI once the domain-neutrality gate is active).

| Artifact | Purpose |
|---|---|
| `evidence_types.json` | Document types and field schemas for this industry |
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

[`templates/food-safety/template.json`](../templates/food-safety/template.json) is the only populated template today - currently a manifest declaring which artifacts are required, not yet the full artifact set. Use it as the starting shape for `template.json` itself; the 13 artifacts above still need to be authored for any template, including `food-safety`.

## Steps once the engine exists

1. Create `templates/{your-industry}/`
2. Author the 13 artifacts above
3. Validate against `templates/_schema/template.schema.json`
4. Run the template lifecycle tooling (planned - see [Deployment Guide](DeploymentGuide.md)) to seed rules to Cosmos DB and activate
5. Run the evaluation framework against your `evaluation/` ground truth set before enabling production traffic

## Today, you can

- Draft `evidence_types.json`, `decision_vocabulary.json`, and `pii_field_list.json` for your target industry - these have no runtime dependency and can be reviewed/refined now
- Open an issue to discuss a new industry template before drafting it, to avoid duplicate work
