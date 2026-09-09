"""
HS Code Rule Logic

Pure algorithm; all HS code values come from the rule config.
"""


def _normalize_hs(hs_code: str) -> str:
    """Strip separators and trailing ``00`` classification segments."""
    segments = hs_code.split(".")
    while len(segments) > 1 and segments[-1] == "00":
        segments.pop()
    normalized = "".join(segments)
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


def check_jurisdiction_hs_code(
    hs_code: str,
    item_code: str,
    jurisdiction_lookup: set,
    rule_code: str = "OUTSIDE_JURISDICTION_HS_CODE",
) -> list:
    """Verify that the HS code belongs to the valid jurisdiction HS code list."""
    if not jurisdiction_lookup:
        return []
    norm_hs = _normalize_hs(hs_code)
    if not any(norm_hs.startswith(prefix) for prefix in jurisdiction_lookup):
        return [{
            "ruleCode": rule_code,
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

    jurisdiction_lookup = {
        _normalize_hs(entry["hsCode"])
        for entry in rules.get("jurisdictionCodes", [])
        if entry.get("hsCode")
    }
    jurisdiction_rule_code = rules.get(
        "outsideJurisdictionRuleCode", "OUTSIDE_JURISDICTION_HS_CODE"
    )

    for item in payload.get("items", []):
        hs = item.get("hsCode")
        if hs:
            hs_str = str(hs)
            item_code = item.get("itemCode", "")
            findings.extend(check_rejected_hs_code(hs_str, item_code, rejected_lookup))
            findings.extend(
                check_jurisdiction_hs_code(
                    hs_str,
                    item_code,
                    jurisdiction_lookup,
                    jurisdiction_rule_code,
                )
            )

    return findings
