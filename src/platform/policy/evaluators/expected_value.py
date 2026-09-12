"""
Expected Value Rule

Asserts that a configured document carries an expected value in a named field.
The field may hold several values separated by commas, slashes, semicolons or
whitespace; a match on any one of them satisfies the rule.

The expected value, source document, source field, and finding codes are all
supplied by the active template's rule.
"""

import logging
import re

logger = logging.getLogger(__name__)


def _parse_values(raw: str) -> list[str]:
    return [tok.strip() for tok in re.split(r"[,/;\s]+", raw) if tok.strip()]


def validate_expected_value(
    submission: list[dict],
    expected_value: str,
    *,
    document_type: str,
    field_name: str,
    missing_rule_code: str = "EXPECTED_VALUE_MISSING",
    mismatch_rule_code: str = "EXPECTED_VALUE_MISMATCH",
) -> list[dict]:
    """Check that a configured document contains the expected value.

    Args:
        submission: List of extracted-document dicts.
        expected_value: Value the field is required to contain.
        document_type: Document carrying the field.
        field_name: Field holding one or more values.
        missing_rule_code: Finding code when no value is present.
        mismatch_rule_code: Finding code when the expected value is absent.
    """
    source_doc = next(
        (d for d in submission if d.get("document") == document_type),
        None,
    )

    if source_doc is None:
        logger.debug("Expected-value check skipped — %s not in submission", document_type)
        return []

    fields: dict = source_doc.get("fields", {})
    line_items: list = source_doc.get("lineItems", [])

    all_values = []
    for item in line_items:
        raw = None
        if isinstance(item, dict):
            source_field = item.get(field_name)
            if isinstance(source_field, dict):
                raw = source_field.get("value") or ""
            elif source_field is not None:
                raw = str(source_field)
        if raw and raw.strip():
            all_values.extend(_parse_values(raw.strip()))

    if not all_values:
        source_field = fields.get(field_name, {})
        raw_value = (
            (source_field.get("value") or "")
            if isinstance(source_field, dict)
            else str(source_field or "")
        )
        raw_value = raw_value.strip()
        if raw_value:
            all_values = _parse_values(raw_value)

    if not all_values:
        return [
            {
                "ruleCode": missing_rule_code,
                "result": "FAIL",
                "message": (
                    f"No {field_name.replace('_', ' ')} found in {document_type}. "
                    f"At least one value must be {expected_value} for this case "
                    "to be in scope."
                ),
            }
        ]

    logger.debug("Values extracted from %s: %s", document_type, all_values)

    if expected_value in all_values:
        logger.debug("Expected value %s found — check passed", expected_value)
        return []

    return [
        {
            "ruleCode": mismatch_rule_code,
            "result": "FAIL",
            "message": (
                f"None of the {field_name.replace('_', ' ')} values in {document_type} "
                f"({', '.join(all_values)}) is {expected_value}. "
                "None of the items in this case are in scope."
            ),
            "evidence": {"values": all_values},
        }
    ]
