# Troubleshooting Steps

**Status: Planned.** There is no deployed environment yet, so there are no real-world failure modes to document today. This guide will be filled in once the [Core Platform implementation](../README.md#roadmap) lands and the first deployments happen.

## What this guide will cover

- Common deployment failures (Terraform apply errors, quota/region availability issues)
- Pipeline failures (orchestrator stuck, activity retries exhausted)
- Extraction quality issues (low-confidence fields, Azure DI model mismatches)
- Token/cost anomalies (see the [Reporting Framework](architecture/TechnicalArchitecture.md#4-component-reference))
- Common misconfiguration of a new industry template (see [Customize Industry Template](CustomizeIndustryTemplate.md))

## Today, you can

- [Submit an issue](https://github.com/microsoft/dstoolkit-document-inspection-agent/issues) if something in the documentation itself is unclear or incorrect
