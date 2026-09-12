"""
Classification Code Rule Logic

Prefix-matches hierarchical, dot-segmented classification codes against
denied and in-scope lists supplied by the active template. The algorithm is
code-system agnostic — any taxonomy with a dotted hierarchy works.
"""

DEFAULT_SEPARATOR = "."
DEFAULT_PADDING_SEGMENT = "00"


def _normalize_code(
    code: str,
    separator: str = DEFAULT_SEPARATOR,
    padding_segment: str | None = DEFAULT_PADDING_SEGMENT,
) -> str:
    """Strip separators and trailing padding segments so prefixes compare cleanly."""
    segments = code.split(separator)
    while padding_segment and len(segments) > 1 and segments[-1] == padding_segment:
        segments.pop()
    normalized = "".join(segments)
    return normalized if normalized else "0"


def check_denied_code(code: str, item_code: str, denied_lookup: list) -> list:
    """Return findings for a single code against the pre-normalized denied lookup."""
    matches = []
    norm_input = _normalize_code(code)
    for norm_denied, entry in denied_lookup:
        if norm_input.startswith(norm_denied):
            matches.append({
                "ruleCode": "DENIED_CLASSIFICATION_CODE",
                "result": "FAIL",
                "itemCode": item_code,
                "classificationCode": code,
                "matchedDeniedCode": entry["code"],
                "section": entry.get("sectionDescription", ""),
                "chapter": entry.get("chapterDescription", ""),
                "description": entry.get("description", ""),
                "message": (
                    f"Classification code '{code}' matches denied code "
                    f"{entry['code']} | Section: {entry.get('sectionDescription', '')} | "
                    f"Chapter: {entry.get('chapterDescription', '')} | {entry.get('description', '')}"
                ),
            })
    return matches


def check_in_scope_code(
    code: str,
    item_code: str,
    in_scope_lookup: set,
    rule_code: str = "OUT_OF_SCOPE_CLASSIFICATION_CODE",
) -> list:
    """Verify that the code falls within the configured in-scope code list."""
    if not in_scope_lookup:
        return []
    norm_code = _normalize_code(code)
    if not any(norm_code.startswith(prefix) for prefix in in_scope_lookup):
        return [{
            "ruleCode": rule_code,
            "result": "FAIL",
            "itemCode": item_code,
            "classificationCode": code,
            "message": (
                f"Classification code '{code}' is not in the configured in-scope "
                "code list; check the items on this case."
            ),
        }]
    return []


def validate_classification_codes(rules: dict, payload: dict) -> list:
    """Check item classification codes against the denied and in-scope lists."""
    findings = []
    code_field = rules.get("codeField", "classificationCode")

    denied_lookup = [
        (_normalize_code(entry["code"]), entry)
        for entry in rules.get("deniedCodes", [])
    ]

    in_scope_lookup = {
        _normalize_code(entry["code"])
        for entry in rules.get("inScopeCodes", [])
        if entry.get("code")
    }
    out_of_scope_rule_code = rules.get(
        "outOfScopeRuleCode", "OUT_OF_SCOPE_CLASSIFICATION_CODE"
    )

    for item in payload.get("items", []):
        code = item.get(code_field)
        if code:
            code_str = str(code)
            item_code = item.get("itemCode", "")
            findings.extend(check_denied_code(code_str, item_code, denied_lookup))
            findings.extend(
                check_in_scope_code(
                    code_str,
                    item_code,
                    in_scope_lookup,
                    out_of_scope_rule_code,
                )
            )

    return findings
