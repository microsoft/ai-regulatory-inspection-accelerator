"""
HS Code Rule Logic

Ported from PAFN's rules_engine/hs_code.py — unchanged (pure algorithm,
all HS code values come from the rule config).
"""


def _normalize_hs(hs_code: str) -> str:
    """Strip dots and trailing zeros for prefix comparison."""
    normalized = hs_code.replace(".", "").rstrip("0")
    return normalized if normalized else "0"


def check_rejected_hs_code(hs_code: str, item_code: str, rejected_lookup: list) -> list:
    """Return findings for a single HS code against the pre-normalized rejected lookup."""
    matches = []
    norm_input = _normalize_hs(hs_code)
    for norm_rejected, entry in rejected_lookup:
        if norm_input.startswith(norm_rejected):
            matches.append({
                "ruleCode": "REJECTED_HS_CODE",
                "result": "FAIL",
                "itemCode": item_code,
                "hsCode": hs_code,
                "matchedRejectedCode": entry["hsCode"],
                "section": entry.get("sectionDescription", ""),
                "chapter": entry.get("chapterDescription", ""),
                "description": entry.get("hsdescription", ""),
                "message": (
                    f"HS code '{hs_code}' matches rejected code "
                    f"{entry['hsCode']} | Section: {entry.get('sectionDescription', '')} | "
                    f"Chapter: {entry.get('chapterDescription', '')} | {entry.get('hsdescription', '')}"
                ),
            })
    return matches


def check_pafn_hs_code(hs_code: str, item_code: str, pafn_lookup: set) -> list:
    """Verify that the HS code belongs to the valid jurisdiction HS code list."""
    if not pafn_lookup:
        return []
    norm_hs = _normalize_hs(hs_code)
    if norm_hs not in pafn_lookup:
        return [{
            "ruleCode": "NON_PAFN_HS_CODE",
            "result": "FAIL",
            "itemCode": item_code,
            "hsCode": hs_code,
            "message": (
                f"HS code '{hs_code}' does not belong to the jurisdiction's valid code list, "
                "please check the items being imported."
            ),
        }]
    return []


def validate_hs_codes(rules: dict, payload: dict) -> list:
    """Check HS codes from payload items against rejected codes and the valid jurisdiction list."""
    findings = []

    rejected_lookup = [
        (_normalize_hs(entry["hsCode"]), entry)
        for entry in rules.get("rejectedCodes", [])
    ]

    pafn_lookup = {
        _normalize_hs(entry["hsCode"])
        for entry in rules.get("pafnCodes", [])
        if entry.get("hsCode")
    }

    for item in payload.get("items", []):
        hs = item.get("hsCode")
        if hs:
            hs_str = str(hs)
            item_code = item.get("itemCode", "")
            findings.extend(check_rejected_hs_code(hs_str, item_code, rejected_lookup))
            findings.extend(check_pafn_hs_code(hs_str, item_code, pafn_lookup))

    return findings
