"""
Minimum Fields Rule Logic

Required-field lists are supplied via an explicit `allowed_fields_by_doc`
parameter; callers source this from TemplateLoader so no file path is hardcoded.
"""

import logging
import re

logger = logging.getLogger(__name__)


def _norm(s: str) -> str:
    """Lowercase alphanumeric only — bridges casing and separator differences."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def validate_min_fields(
    rules_input,
    submission: list,
    allowed_fields_by_doc: dict[str, list[str]] | None = None,
) -> list:
    """For each document in submission, verify all required fields are present.

    Only fields that appear in BOTH rules_input AND allowed_fields_by_doc are
    checked. Fields in only one source are silently skipped.

    Args:
        rules_input:          The MIN_FIELDS_RULES dict, OR a list containing it.
        submission:           DI submission list — each item has 'document' and 'fields'.
        allowed_fields_by_doc: {doc_type: [field_name, ...]} sourced from TemplateLoader.
                               When None, intersection filtering is skipped (all rule
                               fields are checked).
    """
    if isinstance(rules_input, list):
        rule = next((r for r in rules_input if r.get("id") == "MIN_FIELDS_RULES"), None)
    else:
        rule = rules_input if rules_input.get("id") == "MIN_FIELDS_RULES" else None

    if rule is None:
        return []

    required_by_doc: dict = {}
    for entry in rule.get("minimumFieldsByDocuments", []):
        fields = entry.get("fields", [])
        if not fields:
            continue
        doc_name_raw = entry.get("documentName")
        if isinstance(doc_name_raw, list):
            doc_names = [n for n in doc_name_raw if isinstance(n, str)]
        elif isinstance(doc_name_raw, str):
            doc_names = [doc_name_raw]
        else:
            continue
        for name in doc_names:
            required_by_doc[_norm(name)] = fields

    # Intersect with allowed_fields_by_doc when provided
    if allowed_fields_by_doc is not None:
        config_fields = {_norm(k): v for k, v in allowed_fields_by_doc.items()}
        for doc_name, rule_fields in list(required_by_doc.items()):
            known = set(config_fields.get(doc_name, []))
            if not known:
                continue
            intersected = [f for f in rule_fields if f in known]
            skipped = set(rule_fields) - set(intersected)
            if skipped:
                logger.debug(
                    "min_fields: skipping fields not in template config for %s: %s",
                    doc_name, sorted(skipped),
                )
            required_by_doc[doc_name] = intersected

    severity = rule.get("severity", "Warning")
    findings = []
    for doc in submission:
        doc_name = doc.get("document", "")
        required_fields = required_by_doc.get(_norm(doc_name))
        if not required_fields:
            continue

        raw_fields = doc.get("fields", {})
        norm_lookup: dict = {_norm(k): k for k in raw_fields}

        missing_fields = []
        for field in required_fields:
            original_key = norm_lookup.get(_norm(field))
            raw = raw_fields.get(original_key) if original_key else None
            value = raw.get("value") if isinstance(raw, dict) else raw
            if value is None or str(value).strip().lower() in ("null", ""):
                missing_fields.append(field)

        if missing_fields:
            readable_name = doc_name.replace("_", " ")
            readable_fields = [f.replace("_", " ").lower() for f in missing_fields]
            if len(readable_fields) == 1:
                fields_list = readable_fields[0]
            elif len(readable_fields) == 2:
                fields_list = f"{readable_fields[0]} and {readable_fields[1]}"
            else:
                fields_list = ", ".join(readable_fields[:-1]) + f", and {readable_fields[-1]}"
            findings.append({
                "ruleId": "MIN_FIELDS_RULES",
                "documentName": doc_name,
                "result": "WARN",
                "severity": severity,
                "message": f"{readable_name} doesn't have {fields_list}.",
            })

    return findings
