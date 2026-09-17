"""
Rules Engine Executor

Dispatches each rule document to an evaluator by its ``category`` field rather
than through a fixed sequence of hardcoded rule IDs. A template declares only
the categories it needs; categories with no registered evaluator are treated as
reference data, and every step is independently skippable.

Register a new evaluator by adding an entry to ``EVALUATOR_REGISTRY`` and a
position in ``DEFAULT_EVALUATION_ORDER``.
"""

import inspect
import logging
import os
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.platform.policy.evaluators.classification_code import validate_classification_codes
from src.platform.policy.evaluators.cross_document import validate_cross_docs
from src.platform.policy.evaluators.expected_value import validate_expected_value
from src.platform.policy.evaluators.line_item_reconciliation import validate_line_items
from src.platform.policy.evaluators.mandatory_documents import validate_mandatory_docs
from src.platform.policy.evaluators.minimum_fields import validate_min_fields
from src.platform.policy.evaluators.signature_stamp import validate_signature_stamp
from src.platform.policy.evaluators.temporal_rules import validate_temporal_rules

logger = logging.getLogger(__name__)

CATEGORY_EXPECTED_VALUE = "ExpectedValue"
CATEGORY_MANDATORY_DOCUMENTS = "MandatoryDocuments"
CATEGORY_MINIMUM_FIELDS = "MinimumFields"
CATEGORY_CODE_VALIDATION = "ClassificationCodeValidation"
CATEGORY_CROSS_DOCUMENT = "CrossDocumentConsistency"
CATEGORY_ITEM_RECONCILIATION = "ItemReconciliation"
CATEGORY_SIGNATURE_STAMP = "SignatureStampVerification"
CATEGORY_TEMPORAL = "TemporalValidity"

DEFAULT_EVALUATION_ORDER: tuple[str, ...] = (
    CATEGORY_EXPECTED_VALUE,
    CATEGORY_MANDATORY_DOCUMENTS,
    CATEGORY_MINIMUM_FIELDS,
    CATEGORY_CODE_VALIDATION,
    CATEGORY_CROSS_DOCUMENT,
    CATEGORY_ITEM_RECONCILIATION,
    CATEGORY_SIGNATURE_STAMP,
    CATEGORY_TEMPORAL,
)

MANDATORY_RULE_ID = "MANDATORY_DOC_RULES"
MIN_FIELDS_RULE_ID = "MIN_FIELDS_RULES"
CODE_VALIDATION_RULE_ID = "DENIED_CODES"
CROSS_DOC_RULE_ID = "CROSS_DOC_RULES"
SIGNATURE_STAMP_RULE_ID = "SIGNATURE_STAMP_RULES"
TEMPORAL_RULE_ID = "TEMPORAL_RULES"
EXPECTED_VALUE_RULE_ID = "EXPECTED_VALUE_RULES"
ITEM_RECONCILIATION_RULE_ID = "ITEM_RECONCILIATION_RULES"

# Lets rule sets authored before `category` existed still dispatch correctly.
_LEGACY_ID_TO_CATEGORY = {
    EXPECTED_VALUE_RULE_ID: CATEGORY_EXPECTED_VALUE,
    "AGENCY_CODE_RULES": CATEGORY_EXPECTED_VALUE,
    MANDATORY_RULE_ID: CATEGORY_MANDATORY_DOCUMENTS,
    MIN_FIELDS_RULE_ID: CATEGORY_MINIMUM_FIELDS,
    CODE_VALIDATION_RULE_ID: CATEGORY_CODE_VALIDATION,
    "REJECTED_HS_CODES": CATEGORY_CODE_VALIDATION,
    CROSS_DOC_RULE_ID: CATEGORY_CROSS_DOCUMENT,
    ITEM_RECONCILIATION_RULE_ID: CATEGORY_ITEM_RECONCILIATION,
    SIGNATURE_STAMP_RULE_ID: CATEGORY_SIGNATURE_STAMP,
    TEMPORAL_RULE_ID: CATEGORY_TEMPORAL,
    "LOGICAL_RULES": CATEGORY_TEMPORAL,
}

FINDING_CONFIDENCE_THRESHOLD = float(
    os.environ.get("FINDING_CONFIDENCE_THRESHOLD", "0.5")
)


def _find_rule(rules_list: list, rule_id: str) -> dict | None:
    """Return the first rule dict with matching id, or None."""
    return next((r for r in rules_list if r.get("id") == rule_id), None)


def rule_category(rule: dict) -> str | None:
    """Return a rule's category, falling back to its legacy rule ID."""
    return rule.get("category") or _LEGACY_ID_TO_CATEGORY.get(rule.get("id"))


def group_rules_by_category(rules_list: list) -> dict[str, list[dict]]:
    """Bucket rule documents by category, preserving declaration order."""
    grouped: dict[str, list[dict]] = {}
    for rule in rules_list:
        category = rule_category(rule)
        if category:
            grouped.setdefault(category, []).append(rule)
    return grouped


@dataclass
class EvaluationContext:
    """State threaded through the evaluators for a single case."""

    payload: dict
    submission: list
    rules_list: list
    allowed_fields_by_doc: dict | None = None
    reasoning: dict | None = None
    extraction_confidence_threshold: float = 0.85


def _eval_expected_value(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    rule = next((r for r in rules if r.get("expectedValue")), None)
    if not rule:
        return []
    return validate_expected_value(
        ctx.submission,
        expected_value=str(rule["expectedValue"]),
        document_type=rule["documentType"],
        field_name=rule["fieldName"],
        missing_rule_code=rule.get("missingRuleCode", "EXPECTED_VALUE_MISSING"),
        mismatch_rule_code=rule.get("mismatchRuleCode", "EXPECTED_VALUE_MISMATCH"),
        confidence_threshold=ctx.extraction_confidence_threshold,
    )


def _eval_mandatory_documents(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    findings, normalized_submission = validate_mandatory_docs(
        ctx.rules_list, ctx.payload, ctx.submission
    )
    ctx.submission = normalized_submission
    return findings


def _eval_minimum_fields(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    return validate_min_fields(
        rules[0], ctx.submission, allowed_fields_by_doc=ctx.allowed_fields_by_doc
    )


def _eval_code_validation(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    primary = next(
        (r for r in rules if "deniedCodes" in r or r.get("inScopeRuleId")),
        None,
    )
    if primary is None:
        return []
    combined_rule = {**primary}
    in_scope_rule_id = primary.get("inScopeRuleId")
    in_scope_rule = (
        _find_rule(ctx.rules_list, in_scope_rule_id) if in_scope_rule_id else None
    )
    if in_scope_rule:
        combined_rule["inScopeCodes"] = in_scope_rule.get("acceptedCodes", [])
    return validate_classification_codes(combined_rule, ctx.payload)


def _eval_cross_document(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    result = validate_cross_docs(
        ctx.payload,
        rules[0],
        ctx.submission,
        reasoning=ctx.reasoning,
    )
    return [*result.get("findings", []), *result.get("item_type_findings", [])]


def _eval_item_reconciliation(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    return validate_line_items(rules[0], ctx.payload, ctx.submission)


def _eval_signature_stamp(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    return validate_signature_stamp(rules[0], ctx.submission)


def _eval_temporal(rules: list[dict], ctx: EvaluationContext) -> list[dict]:
    rule = rules[0]
    if str(rule.get("isActive", "True")).lower() == "false":
        logger.info("Skipping %s — rule is inactive", CATEGORY_TEMPORAL)
        return []
    return validate_temporal_rules(rule, ctx.payload, ctx.submission)


EVALUATOR_REGISTRY: dict[str, Callable[[list[dict], EvaluationContext], Any]] = {
    CATEGORY_EXPECTED_VALUE: _eval_expected_value,
    CATEGORY_MANDATORY_DOCUMENTS: _eval_mandatory_documents,
    CATEGORY_MINIMUM_FIELDS: _eval_minimum_fields,
    CATEGORY_CODE_VALIDATION: _eval_code_validation,
    CATEGORY_CROSS_DOCUMENT: _eval_cross_document,
    CATEGORY_ITEM_RECONCILIATION: _eval_item_reconciliation,
    CATEGORY_SIGNATURE_STAMP: _eval_signature_stamp,
    CATEGORY_TEMPORAL: _eval_temporal,
}


async def run_rules(
    rules_list: list,
    payload: dict,
    submission: list,
    allowed_fields_by_doc: dict | None = None,
    reasoning: dict | None = None,
    evaluation_order: tuple[str, ...] | None = None,
    extraction_confidence_threshold: float = 0.85,
) -> list:
    """Dispatch rules to evaluators by category and return a flat findings list.

    Args:
        rules_list:           List of rule dicts. Each should carry a "category";
                              legacy rule IDs are mapped for backwards compatibility.
        payload:              Case submission dict (requestId, items, documents).
        submission:           List of extracted document dicts.
        allowed_fields_by_doc: {doc_type: [field_name]} from TemplateLoader — forwarded
                               to validate_min_fields so field intersection uses the
                               template's evidence_types.json instead of a hardcoded file.
        reasoning:            Result from the Reasoning Agent. Evaluators are
                              deterministic and never call an LLM themselves.
        evaluation_order:     Overrides DEFAULT_EVALUATION_ORDER.
    """
    ctx = EvaluationContext(
        payload=payload,
        submission=submission,
        rules_list=rules_list,
        allowed_fields_by_doc=allowed_fields_by_doc,
        reasoning=reasoning,
        extraction_confidence_threshold=extraction_confidence_threshold,
    )

    findings: list = []
    rules_by_category = group_rules_by_category(rules_list)
    order = evaluation_order or DEFAULT_EVALUATION_ORDER

    for category in order:
        evaluator = EVALUATOR_REGISTRY.get(category)
        if evaluator is None:
            logger.warning("No evaluator registered for category %s", category)
            continue

        category_rules = rules_by_category.get(category)
        if not category_rules:
            logger.info("Skipping %s — no rule of this category configured", category)
            continue

        try:
            result = evaluator(category_rules, ctx)
            if inspect.isawaitable(result):
                result = await result
            findings.extend(result)
            logger.info("%s: %d finding(s)", category, len(result))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("%s FAILED | %s\n%s", category, exc, traceback.format_exc())

    reference_only = sorted(set(rules_by_category) - set(EVALUATOR_REGISTRY))
    if reference_only:
        logger.debug("Reference-data categories (no evaluator): %s", reference_only)

    # Normalize: copy ruleId → ruleCode when ruleCode is absent
    normalized = []
    for f in findings:
        if not f.get("ruleCode") and f.get("ruleId"):
            f = {**f, "ruleCode": f["ruleId"]}
        normalized.append(f)

    # Confidence cutoff: drop findings below threshold
    pre_filter_count = len(normalized)
    normalized = [
        f for f in normalized
        if "confidence" not in f or f["confidence"] >= FINDING_CONFIDENCE_THRESHOLD
    ]
    dropped = pre_filter_count - len(normalized)
    if dropped:
        logger.info(
            "Confidence cutoff (%.2f): dropped %d low-confidence finding(s)",
            FINDING_CONFIDENCE_THRESHOLD, dropped,
        )

    fail_count = sum(1 for f in normalized if f.get("result") == "FAIL")
    warn_count = sum(1 for f in normalized if f.get("result") == "WARN")
    logger.info(
        "run_rules complete | total=%d fail=%d warn=%d", len(normalized), fail_count, warn_count
    )
    return normalized
