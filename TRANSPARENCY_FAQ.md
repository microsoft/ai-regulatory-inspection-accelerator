# Responsible AI Transparency FAQ

## What is the Document Inspection Agent?

The Document Inspection Agent is an AI Evidence-to-Decision Platform that processes multi-document submissions and generates structured, explainable compliance decisions.

## What can the system do?

The system ingests document bundles, extracts structured facts, validates cross-document consistency, evaluates configurable policy rules, and produces a recommendation with a complete evidence chain.

## What are the system's intended uses?

Regulatory inspection, customs clearance, KYC/AML onboarding, insurance claims adjudication, healthcare prior authorization, and any domain where high-stakes decisions are made on multi-document submissions.

## How was the system evaluated?

Using the included evaluation framework, which measures field-level extraction accuracy, cross-document validation precision, and decision accuracy against human-verified ground truth.

## What are the limitations?

- AI extraction accuracy is not 100%. Expected-value policy rules exclude fields below the active template's extraction-confidence threshold from deterministic PASS/FAIL evaluation. Confidence gating for other rule categories remains under implementation.
- The system produces AI-assisted recommendations, not autonomous legal decisions. Human review is a first-class capability.
- Accuracy varies by document quality, language, and domain.

## How are low-confidence expected values handled?

Expected-value rules use the extraction-confidence threshold from the active template's risk configuration (default: 0.85). A value at or above the threshold is eligible for deterministic comparison.

When a required value is present but below the threshold, the policy engine emits a `LOW_CONFIDENCE_EVIDENCE` warning instead of treating the value as a deterministic match, mismatch, or missing value. The extraction-risk assessment then routes the case to `HOLD` for human review. A genuinely absent value continues to use the template's configured missing-evidence rule.

This guardrail applies to both top-level document fields and line-item fields used by expected-value rules. If confident evidence satisfies the rule, an additional uncertain value does not override that result.

## How should the system be used responsibly?

- Always configure human review for HOLD decisions
- Validate extraction accuracy against domain-specific ground truth before go-live
- Do not rely on AI decisions without human oversight in high-stakes regulatory contexts
- Ensure compliance with local data protection regulations (GDPR, CCPA, etc.)