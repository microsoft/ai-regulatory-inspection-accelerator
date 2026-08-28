"""
Rules Engine Executor

Ported from PAFN's rules_engine/rule_executor.py.
Changes from PAFN:
  - Removed shared.telemetry and shared.pii_redaction imports.
  - All imports changed from rules_engine.X to src.platform.policy.evaluators.X.
  - run_rules() gains an optional `allowed_fields_by_doc` parameter that is
    forwarded to validate_min_fields() so callers can source field lists from
    TemplateLoader instead of document_type_fields.json.
    - Agency and jurisdiction HS values are sourced from template rule documents.

Logic, step ordering, confidence cutoff, and finding normalization are
identical to PAFN production.
"""

import logging
import os
import traceback

from src.platform.policy.evaluators.agency_code import validate_agency_code
from src.platform.policy.evaluators.cross_document import validate_cross_docs
from src.platform.policy.evaluators.hs_code import validate_hs_codes
from src.platform.policy.evaluators.item_check import validate_item_checks
from src.platform.policy.evaluators.logical_rules import validate_logical_rules
from src.platform.policy.evaluators.mandatory_documents import validate_mandatory_docs
from src.platform.policy.evaluators.minimum_fields import validate_min_fields
from src.platform.policy.evaluators.signature_stamp import validate_signature_stamp

logger = logging.getLogger(__name__)

MANDATORY_RULE_ID = "MANDATORY_DOC_RULES"
MIN_FIELDS_RULE_ID = "MIN_FIELDS_RULES"
HS_CODE_RULE_ID = "REJECTED_HS_CODES"
CROSS_DOC_RULE_ID = "CROSS_DOC_RULES"
SIGNATURE_STAMP_RULE_ID = "SIGNATURE_STAMP_RULES"
LOGICAL_RULE_ID = "LOGICAL_RULES"
AGENCY_CODE_RULE_ID = "AGENCY_CODE_RULES"

FINDING_CONFIDENCE_THRESHOLD = float(
    os.environ.get("FINDING_CONFIDENCE_THRESHOLD", "0.5")
)


def _find_rule(rules_list: list, rule_id: str) -> dict | None:
    """Return the first rule dict with matching id, or None."""
    return next((r for r in rules_list if r.get("id") == rule_id), None)


async def run_rules(
    rules_list: list,
    payload: dict,
    submission: list,
    managed_identity_client_id: str = "",
    llm_comparison_fn=None,
    item_type_check_fn=None,
    allowed_fields_by_doc: dict | None = None,
) -> list:
    """Execute the rule pipeline in a fixed order and return a flat findings list.

    Args:
        rules_list:           List of rule dicts (each with an "id" key).
                              Loaded from Cosmos DB or a template's rules.json.
        payload:              Importer declaration dict (requestId, items, documents).
        submission:           List of DI-extracted document dicts.
        managed_identity_client_id: Azure Managed Identity client ID (for LLM calls).
        llm_comparison_fn:    Injectable async callable for cross-doc fuzzy/semantic checks.
        item_type_check_fn:   Injectable async callable for LLM item type checks.
        allowed_fields_by_doc: {doc_type: [field_name]} from TemplateLoader — forwarded
                               to validate_min_fields so field intersection uses the
                               template's evidence_types.json instead of a hardcoded file.
    """
    findings = []
    normalized_submission = submission

    agency_rule = _find_rule(rules_list, AGENCY_CODE_RULE_ID)

    # Step 0: Agency code check
    if agency_rule and agency_rule.get("agencyCode"):
        try:
            result = validate_agency_code(
                submission,
                agency_code=str(agency_rule["agencyCode"]),
                document_type=agency_rule["documentType"],
                field_name=agency_rule["fieldName"],
                missing_rule_code=agency_rule.get("missingRuleCode", "AGENCY_CODE_MISSING"),
                mismatch_rule_code=agency_rule.get(
                    "mismatchRuleCode", "AGENCY_CODE_MISMATCH"
                ),
            )
            findings.extend(result)
            logger.info("agency_code: %d finding(s)", len(result))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("Step 0 agency_code FAILED | %s\n%s", exc, traceback.format_exc())
    else:
        logger.warning("Skipping agency_code — %s not configured", AGENCY_CODE_RULE_ID)

    # Step 1: Mandatory documents + name normalization
    rule = _find_rule(rules_list, MANDATORY_RULE_ID)
    if rule:
        try:
            result, normalized_submission = validate_mandatory_docs(rules_list, payload, submission)
            findings.extend(result)
            logger.info("mandatory: %d finding(s)", len(result))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("Step 1 mandatory_documents FAILED | %s\n%s", exc, traceback.format_exc())
    else:
        logger.warning("Skipping mandatory — %s not in rules_list", MANDATORY_RULE_ID)

    # Step 2: Minimum fields per document
    rule = _find_rule(rules_list, MIN_FIELDS_RULE_ID)
    if rule:
        try:
            result = validate_min_fields(rule, normalized_submission, allowed_fields_by_doc=allowed_fields_by_doc)
            findings.extend(result)
            logger.info("minimum_fields: %d finding(s)", len(result))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("Step 2 minimum_fields FAILED | %s\n%s", exc, traceback.format_exc())
    else:
        logger.warning("Skipping minimum_fields — %s not in rules_list", MIN_FIELDS_RULE_ID)

    # Step 3: HS code validation
    rule = _find_rule(rules_list, HS_CODE_RULE_ID)
    if rule:
        try:
            combined_rule = {**rule}
            jurisdiction_rule_id = rule.get("validJurisdictionRuleId")
            jurisdiction_rule = (
                _find_rule(rules_list, jurisdiction_rule_id)
                if jurisdiction_rule_id
                else None
            )
            if jurisdiction_rule:
                combined_rule["jurisdictionCodes"] = jurisdiction_rule.get(
                    "acceptedCodes", []
                )
            result = validate_hs_codes(combined_rule, payload)
            findings.extend(result)
            logger.info("hs_code: %d finding(s)", len(result))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("Step 3 hs_code FAILED | %s\n%s", exc, traceback.format_exc())
    else:
        logger.warning("Skipping hs_code — %s not in rules_list", HS_CODE_RULE_ID)

    # Step 4: Cross-document consistency
    rule = _find_rule(rules_list, CROSS_DOC_RULE_ID)
    if rule:
        try:
            result = await validate_cross_docs(
                payload, rule, normalized_submission,
                managed_identity_client_id, llm_comparison_fn, item_type_check_fn,
            )
            cross_findings = result.get("findings", [])
            findings.extend(cross_findings)
            findings.extend(result.get("item_type_findings", []))
            logger.info("cross_document: %d finding(s)", len(cross_findings))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("Step 4 cross_document FAILED | %s\n%s", exc, traceback.format_exc())
    else:
        logger.warning("Skipping cross_document — %s not in rules_list", CROSS_DOC_RULE_ID)

    # Step 5: Item checks (payload vs document line items)
    try:
        item_findings = validate_item_checks(payload, normalized_submission)
        findings.extend(item_findings)
        logger.info("item_check: %d finding(s)", len(item_findings))
    except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
        logger.error("Step 5 item_check FAILED | %s\n%s", exc, traceback.format_exc())

    # Step 6: Signature / stamp verification
    rule = _find_rule(rules_list, SIGNATURE_STAMP_RULE_ID)
    if rule:
        try:
            result = validate_signature_stamp(rule, normalized_submission)
            findings.extend(result)
            logger.info("signature_stamp: %d finding(s)", len(result))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("Step 6 signature_stamp FAILED | %s\n%s", exc, traceback.format_exc())
    else:
        logger.warning("Skipping signature_stamp — %s not in rules_list", SIGNATURE_STAMP_RULE_ID)

    # Step 7: Logical consistency (date-based validity)
    rule = _find_rule(rules_list, LOGICAL_RULE_ID)
    if rule and str(rule.get("isActive", "True")).lower() != "false":
        try:
            result = validate_logical_rules(rule, payload, normalized_submission)
            findings.extend(result)
            logger.info("logical_rules: %d finding(s)", len(result))
        except Exception as exc:  # noqa: BLE001 - isolate independent rule failures
            logger.error("Step 7 logical_rules FAILED | %s\n%s", exc, traceback.format_exc())
    else:
        logger.warning("Skipping logical_rules — %s not in rules_list or inactive", LOGICAL_RULE_ID)

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
