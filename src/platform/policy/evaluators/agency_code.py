"""
Agency Code Verification Rule

Ported from PAFN's rules_engine/agency_code.py.
Change from PAFN: PAFN_AGENCY_CODE is now a parameter instead of a module-level
constant so any template can configure the expected agency code via AGENCY_CODE_RULES.
"""

import logging
import re

logger = logging.getLogger(__name__)

_DECLARATION_DOC_TYPE = "Declaration_Document"


def _parse_agency_codes(raw: str) -> list[str]:
    return [tok.strip() for tok in re.split(r"[,/;\s]+", raw) if tok.strip()]


def validate_agency_code(
    submission: list[dict],
    agency_code: str = "2",
) -> list[dict]:
    """Check that the Declaration Document contains the expected agency code.

    Args:
        submission:   List of extracted-document dicts.
        agency_code:  Expected agency code (default "2" for PAFN).
                      Callers source this from the AGENCY_CODE_RULES rule document.
    """
    declaration_doc = next(
        (d for d in submission if d.get("document") == _DECLARATION_DOC_TYPE),
        None,
    )

    if declaration_doc is None:
        logger.debug("Agency code check skipped — Declaration_Document not in submission")
        return []

    fields: dict = declaration_doc.get("fields", {})
    line_items: list = declaration_doc.get("lineItems", [])

    all_codes = []
    for item in line_items:
        raw = None
        if isinstance(item, dict):
            agency_field = item.get("agency_code")
            if isinstance(agency_field, dict):
                raw = agency_field.get("value") or ""
            elif agency_field is not None:
                raw = str(agency_field)
        if raw and raw.strip():
            all_codes.extend(_parse_agency_codes(raw.strip()))

    if not all_codes:
        agency_field = fields.get("agency_code", {})
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
                "ruleCode": "AGENCY_CODE_MISSING",
                "result": "FAIL",
                "message": (
                    "No agency code found in Declaration Document. "
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
            "ruleCode": "AGENCY_CODE_NOT_PAFN",
            "result": "FAIL",
            "message": (
                f"None of the agency codes in the Declaration Document "
                f"({', '.join(all_codes)}) is {agency_code}. "
                "None of the items in this shipment are related to this jurisdiction."
            ),
            "evidence": {"agencyCodes": all_codes},
        }
    ]
