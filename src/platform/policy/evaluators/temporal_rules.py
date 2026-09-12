"""
Temporal Validity Rule Logic

Evaluates date relationships declared by the active template. Rules are data,
not expressions: each declares an operator from COMPARATORS, the fields to read,
and what to emit. No rule identifier or field name is hardcoded here.
"""

from datetime import date, datetime, timezone

# Each comparator answers "does this rule PASS?" for (value, reference).
COMPARATORS = {
    "before": lambda value, reference: value < reference,
    "notAfter": lambda value, reference: value <= reference,
    "after": lambda value, reference: value > reference,
    "notBefore": lambda value, reference: value >= reference,
}

SCOPE_ITEM = "item"
SCOPE_DOCUMENT = "document"


def _parse_date_safe(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except (ValueError, TypeError):
        return None


def _first_date(fields: dict, candidates: tuple) -> date | None:
    for name in candidates:
        entry = fields.get(name)
        if not entry:
            continue
        val = entry.get("value") if isinstance(entry, dict) else entry
        parsed = _parse_date_safe(val)
        if parsed:
            return parsed
    return None


def _get_line_items(doc_by_id: dict, doc_id: str) -> list:
    doc = doc_by_id.get(doc_id)
    if not doc:
        return []
    return doc.get("line_items") or []


def _li_date(line_item: dict, field_name: str) -> date | None:
    raw = line_item.get(field_name)
    if raw is None:
        return None
    val = raw.get("value") if isinstance(raw, dict) else raw
    return _parse_date_safe(val)


def _resolve_doc(entry, doc_by_id: dict) -> tuple[dict | None, str]:
    if isinstance(entry, dict):
        doc_id = str(entry.get("documentTypeId", ""))
        doc_type = entry.get("documentType", doc_id)
        doc = doc_by_id.get(doc_id) if doc_id else None
        return doc, doc_type
    return None, str(entry)


def _format(template: str, **values) -> str:
    for name, value in values.items():
        template = template.replace("{" + name + "}", str(value))
    return template


def _eval_document_scope(rule_entry: dict, doc_by_id: dict, reference: date) -> list:
    findings: list = []
    compare = COMPARATORS[rule_entry["operator"]]
    rule_id = rule_entry.get("ruleId", "")
    fields = tuple(rule_entry.get("fields", []))
    fail_message = rule_entry.get(
        "failMessage", "{documentType} failed {ruleId} (date: {value})."
    )

    for entry in rule_entry.get("appliesTo", []):
        doc, doc_type = _resolve_doc(entry, doc_by_id)
        if not doc:
            continue
        value = _first_date(doc.get("fields", {}), fields)
        if value is None or compare(value, reference):
            continue
        findings.append({
            "ruleCode": rule_id,
            "result": rule_entry.get("failResult", "FAIL"),
            "documentType": doc_type,
            "message": _format(
                fail_message,
                documentType=doc_type.replace("_", " "),
                ruleId=rule_id,
                value=value.isoformat(),
            ),
        })
    return findings


def _eval_item_scope(rule_entry: dict, payload: dict, doc_by_id: dict, reference: date) -> list:
    findings: list = []
    compare = COMPARATORS[rule_entry["operator"]]
    rule_id = rule_entry.get("ruleId", "")
    value_field = rule_entry.get("valueField", "")
    line_item_field = rule_entry.get("lineItemField", value_field)
    label_field = rule_entry.get("labelField", "itemCode")
    fail_message = rule_entry.get(
        "failMessage", "Item '{item}' failed {ruleId} (date: {value}, source: {source})."
    )
    missing_message = rule_entry.get(
        "missingMessage", "Item '{item}' has no {ruleId} date to verify."
    )

    sources = rule_entry.get("lineItemSources", [])
    source_line_items = {
        s["documentType"]: _get_line_items(doc_by_id, str(s.get("documentTypeId", "")))
        for s in sources
    }

    for item in payload.get("items", []):
        item_code = item.get("itemCode", "")
        label = item.get(label_field, str(item_code))
        li_idx = item.get("serial", 1) - 1

        value = _parse_date_safe(item.get(value_field))
        source_label = "submission"

        if value is None:
            for source in sources:
                li_list = source_line_items[source["documentType"]]
                if 0 <= li_idx < len(li_list):
                    value = _li_date(li_list[li_idx], line_item_field)
                    if value is not None:
                        source_label = source["documentType"].replace("_", " ")
                        break

        if value is None:
            findings.append({
                "ruleCode": rule_id,
                "result": rule_entry.get("missingResult", "WARN"),
                "itemCode": item_code,
                "message": _format(missing_message, item=label, ruleId=rule_id),
            })
            continue

        if not compare(value, reference):
            findings.append({
                "ruleCode": rule_id,
                "result": rule_entry.get("failResult", "FAIL"),
                "itemCode": item_code,
                "message": _format(
                    fail_message,
                    item=label,
                    ruleId=rule_id,
                    value=value.isoformat(),
                    source=source_label,
                ),
            })

    return findings


def validate_temporal_rules(rule: dict, payload: dict, submission: list) -> list:
    """Evaluate template-declared temporal rules against the payload and submission."""
    findings = []
    today = datetime.now(timezone.utc).date()

    doc_by_id: dict[str, dict] = {}
    for doc in submission:
        doc_id = str(doc.get("documentTypeId", ""))
        if doc_id:
            doc_by_id[doc_id] = doc

    for rule_entry in rule.get("temporalRules", []):
        operator = rule_entry.get("operator")
        if operator not in COMPARATORS:
            continue

        # "today" is the only reference the platform resolves; others are literal dates.
        raw_reference = rule_entry.get("reference", "today")
        reference = today if raw_reference == "today" else _parse_date_safe(raw_reference)
        if reference is None:
            continue

        scope = rule_entry.get("scope", SCOPE_DOCUMENT)
        if scope == SCOPE_ITEM:
            findings.extend(_eval_item_scope(rule_entry, payload, doc_by_id, reference))
        elif scope == SCOPE_DOCUMENT:
            findings.extend(_eval_document_scope(rule_entry, doc_by_id, reference))

    return findings
