"""
Agency Code Verification Rule

Agency value, source document, source field, and finding codes are supplied by
the active template's agency rule.
"""

import logging
import re

logger = logging.getLogger(__name__)

def _parse_agency_codes(raw: str) -> list[str]:
    return [tok.strip() for tok in re.split(r"[,/;\s]+", raw) if tok.strip()]


def validate_agency_code(
    submission: list[dict],
    agency_code: str,
    *,
    document_type: str,
    field_name: str,
    missing_rule_code: str = "AGENCY_CODE_MISSING",
    mismatch_rule_code: str = "AGENCY_CODE_MISMATCH",
) -> list[dict]:
    """Check that a configured document contains the expected agency code.

    Args:
        submission: List of extracted-document dicts.
        agency_code: Expected agency code.
        document_type: Document containing the agency field.
        field_name: Field containing one or more agency codes.
        missing_rule_code: Finding code when no agency value is present.
        mismatch_rule_code: Finding code when the expected value is absent.
    """
    declaration_doc = next(
        (d for d in submission if d.get("document") == document_type),
        None,
    )

    if declaration_doc is None:
        logger.debug("Agency code check skipped — %s not in submission", document_type)
        return []

    fields: dict = declaration_doc.get("fields", {})
    line_items: list = declaration_doc.get("lineItems", [])

    all_codes = []
    for item in line_items:
        raw = None
        if isinstance(item, dict):
            agency_field = item.get(field_name)
            if isinstance(agency_field, dict):
                raw = agency_field.get("value") or ""
            elif agency_field is not None:
                raw = str(agency_field)
        if raw and raw.strip():
            all_codes.extend(_parse_agency_codes(raw.strip()))

    if not all_codes:
        agency_field = fields.get(field_name, {})
        raw_value = (
            (agency_field.get("value") or "")
            if isinstance(agency_field, dict)
            else str(agency_field or "")
        )
        raw_value = raw_value.strip()
        if raw_value:
            all_codes = _parse_agency_codes(raw_value)

    if not all_codes:
        return [
            {
                "ruleCode": missing_rule_code,
                "result": "FAIL",
                "message": (
                    f"No agency code found in {document_type}. "
                    f"At least one agency code must be {agency_code} for this shipment "
                    "to be under jurisdiction."
                ),
            }
        ]

    logger.debug("Agency codes extracted from Declaration Document: %s", all_codes)

    if agency_code in all_codes:
        logger.debug("Agency code %s found — check passed", agency_code)
        return []

    return [
        {
            "ruleCode": mismatch_rule_code,
            "result": "FAIL",
            "message": (
                f"None of the agency codes in {document_type} "
                f"({', '.join(all_codes)}) is {agency_code}. "
                "None of the items in this shipment are related to this jurisdiction."
            ),
            "evidence": {"agencyCodes": all_codes},
        }
    ]
