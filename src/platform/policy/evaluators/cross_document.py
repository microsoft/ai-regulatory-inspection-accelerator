"""
Cross-Document Rule Logic

Field comparison rules, the field-name sets that select a comparison strategy,
and any document substitutions all come from the CROSS_DOC_RULES rule document.
"""

import logging
import re
from datetime import datetime

from src.platform.policy.evaluators import llm_mapper

logger = logging.getLogger(__name__)

_MONTH_ABBR = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

VALUE_TYPE_COUNTRY = "country"
VALUE_TYPE_DATE = "date"


def _parse_numeric(value: str):
    cleaned = str(value).replace(",", "")
    match = re.search(r"\d+\.?\d*", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _normalize_date(value: str) -> str | None:
    value = value.strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
        return value
    m = re.match(r"^([A-Za-z]{3})[/\-](\d{1,2})[/\-](\d{4})$", value)
    if m:
        mon = m.group(1).lower()
        if mon in _MONTH_ABBR:
            return f"{m.group(3)}-{_MONTH_ABBR[mon]}-{int(m.group(2)):02d}"
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d",
                "%b %d %Y", "%B %d %Y", "%d %b %Y", "%d %B %Y"):
        try:
            parsed = datetime.strptime(value, fmt).date()  # noqa: DTZ007 - date-only value
            return parsed.isoformat()
        except ValueError:
            pass
    return None


def _digits_only(value: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", str(value))
    return digits if digits else None


def apply_document_fallbacks(
    rules: list,
    doc_field_index: dict,
    fallbacks: list,
    aliases: dict | None = None,
) -> list:
    """Substitute a stand-in document when none of the preferred ones were submitted."""
    for fallback in fallbacks:
        absent_group = set(fallback.get("whenAbsent", []))
        replacement = fallback.get("use")
        if not absent_group or not replacement:
            continue
        if any(d in doc_field_index for d in absent_group):
            continue
        if replacement not in doc_field_index:
            continue
        rewritten = []
        for rule in rules:
            documents = rule.get("documents", [])
            resolved = [llm_mapper.resolve_document_name(d, aliases) for d in documents]
            if any(d in absent_group for d in resolved):
                rule = {**rule, "documents": [
                    replacement
                    if llm_mapper.resolve_document_name(d, aliases) in absent_group
                    else d
                    for d in documents
                ]}
            rewritten.append(rule)
        rules = rewritten
    return rules


def _collect_field_values(
    rule: dict,
    doc_index: dict,
    field_resolution: dict,
    aliases: dict | None = None,
) -> dict:
    doc_values = {}
    for rule_doc_name in rule.get("documents", []):
        sub_doc_name = llm_mapper.resolve_document_name(rule_doc_name, aliases)
        fields = doc_index.get(sub_doc_name, {})
        value = llm_mapper.get_field_value(fields, rule["field"], field_resolution, sub_doc_name)
        if value:
            doc_values[sub_doc_name] = value
    return doc_values


def _value_type(rule: dict, country_fields: frozenset, date_fields: frozenset) -> str | None:
    """A rule may declare valueType directly, otherwise it is inferred from the field name."""
    declared = rule.get("valueType")
    if declared:
        return declared
    field = rule.get("field")
    if field in country_fields:
        return VALUE_TYPE_COUNTRY
    if field in date_fields:
        return VALUE_TYPE_DATE
    return None


def _check_exact(
    rule: dict,
    doc_values: dict,
    country_fields: frozenset = frozenset(),
    date_fields: frozenset = frozenset(),
) -> dict:
    rule_id = rule["ruleId"]
    if len(doc_values) < 2:
        return {
            "ruleId": rule_id, "result": "NOT_APPLICABLE",
            "message": f"Fewer than 2 documents provided a value for '{rule['field']}'. Documents checked: {list(doc_values.keys())}",
            "evidence": doc_values,
            "severity": rule.get("severity", "Warning"),
        }

    value_type = _value_type(rule, country_fields, date_fields)

    if value_type == VALUE_TYPE_COUNTRY:
        normalised = {k: llm_mapper.normalize_country(v) for k, v in doc_values.items()}
        unique = set(normalised.values())
        result = "PASS" if len(unique) == 1 else "FAIL"
        return {
            "ruleId": rule_id, "result": result,
            "message": rule.get("description", ""),
            "evidence": doc_values,
            "severity": rule.get("severity", "Warning"),
        }

    if value_type == VALUE_TYPE_DATE:
        normalised = {k: _normalize_date(v) for k, v in doc_values.items()}
        if all(v is not None for v in normalised.values()):
            unique = set(normalised.values())
            result = "PASS" if len(unique) == 1 else "FAIL"
            return {
                "ruleId": rule_id, "result": result,
                "message": rule.get("description", ""),
                "evidence": doc_values,
            }

    nums = {k: _parse_numeric(v) for k, v in doc_values.items()}
    if all(v is not None for v in nums.values()):
        unique = set(nums.values())
        if len(unique) > 1:
            digit_seqs = {k: _digits_only(v) for k, v in doc_values.items()}
            if all(d is not None for d in digit_seqs.values()) and len(set(digit_seqs.values())) == 1:
                unique = {next(iter(nums.values()))}
    else:
        unique = {v.strip().lower() for v in doc_values.values()}

    result = "PASS" if len(unique) == 1 else "FAIL"
    return {
        "ruleId": rule_id, "result": result,
        "message": rule.get("description", ""),
        "evidence": doc_values,
        "severity": rule.get("severity", "Warning"),
    }


def select_cross_document_rules(rules_input) -> tuple[dict | None, list]:
    """Return the CROSS_DOC_RULES document and its validated comparison rules."""
    if isinstance(rules_input, list):
        rule_doc = next((r for r in rules_input if r.get("id") == "CROSS_DOC_RULES"), None)
    else:
        rule_doc = rules_input if rules_input.get("id") == "CROSS_DOC_RULES" else None

    if rule_doc is None:
        return None, []

    def _is_valid(r: dict) -> bool:
        if not isinstance(r.get("field"), str):
            return False
        docs = r.get("documents", [])
        return isinstance(docs, list) and all(isinstance(d, str) for d in docs)

    return rule_doc, [r for r in rule_doc.get("crossDocumentRules", []) if _is_valid(r)]


def validate_cross_docs(
    payload: dict,
    rules_input,
    submission: list,
    reasoning: dict | None = None,
) -> dict:
    """Deterministic cross-document validation.

    Performs no LLM calls. ``reasoning`` is the Reasoning Agent's result; any
    comparison it resolved takes priority over the in-process comparison.
    """
    reasoning = reasoning or {}
    field_resolution = reasoning.get("field_resolution", {})
    llm_findings_by_rule = reasoning.get("comparison_findings", {})
    errors = list(reasoning.get("errors", []))

    rule_doc, cross_doc_rules = select_cross_document_rules(rules_input)
    if rule_doc is None:
        return {
            "requestId": payload.get("requestId"),
            "findings": [],
            "errors": [{"code": "MISSING_RULES", "severity": "error",
                        "message": "CROSS_DOC_RULES not found in rules_input."}],
        }

    request_id = payload.get("requestId", "unknown")

    aliases = rule_doc.get("documentAliases", {})
    country_fields = frozenset(rule_doc.get("countryFields", []))
    date_fields = frozenset(rule_doc.get("dateFields", []))

    logger.info("Cross-document validation | requestId=%s | docs=%d | rules=%d",
                request_id, len(submission), len(cross_doc_rules))

    doc_field_index = llm_mapper.build_doc_field_index(submission, min_confidence=0.8)
    cross_doc_rules = apply_document_fallbacks(
        cross_doc_rules, doc_field_index, rule_doc.get("documentFallbacks", []), aliases
    )

    # Deterministic exactMatch comparison
    in_process_findings = {}
    for rule in cross_doc_rules:
        if rule.get("comparisonType") != "exactMatch":
            continue
        doc_values = _collect_field_values(rule, doc_field_index, field_resolution, aliases)
        finding = _check_exact(rule, doc_values, country_fields, date_fields)
        in_process_findings[rule["ruleId"]] = finding

    # Step D
    ordered_findings = []
    for rule in cross_doc_rules:
        rule_id = rule["ruleId"]
        finding = (
            llm_findings_by_rule.get(rule_id)
            or in_process_findings.get(rule_id)
            or {
                "ruleId": rule_id,
                "result": "NOT_APPLICABLE",
                "message": f"No values resolved for field '{rule['field']}' in any submission document.",
                "evidence": {},
            }
        )
        ordered_findings.append(finding)

    return {
        "requestId": request_id,
        "findings": ordered_findings,
        "item_type_findings": list(reasoning.get("item_type_findings", [])),
        "errors": errors,
        "field_resolution": field_resolution,
    }
