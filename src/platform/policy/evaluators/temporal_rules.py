"""
Logical Consistency Rule Logic

Pure algorithm; rule configuration comes from the LOGICAL_RULES rule document.
"""

from datetime import date, datetime, timezone

_LINE_ITEM_SOURCE_PRIORITY = ("Packing_List", "Stretching_List", "Invoice")

_ISSUE_DATE_FIELDS = (
    "issue_date",
    "certificate_issue_date",
    "license_issue_date",
    "license_start_date",
)

_EXPIRY_DATE_FIELDS = (
    "expiry_date",
    "certificate_expiry_date",
    "license_expiry_date",
    "certificate_valid_until",
)


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


def _li_expiry(line_item: dict) -> date | None:
    raw = line_item.get("expiry_date")
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


def validate_logical_rules(rule: dict, payload: dict, submission: list) -> list:
    """Evaluate logical consistency rules against the payload and normalized submission."""
    findings = []
    today = datetime.now(timezone.utc).date()

    doc_by_id: dict[str, dict] = {}
    for doc in submission:
        doc_id = str(doc.get("documentTypeId", ""))
        if doc_id:
            doc_by_id[doc_id] = doc

    for rule_entry in rule.get("logicalRules", []):
        rule_id = rule_entry.get("ruleId", "")
        applies_to = rule_entry.get("appliesTo")

        if rule_id == "FOOD_NOT_EXPIRED":
            li_sources = rule_entry.get("lineItemSources") or [
                {"documentType": dt, "documentTypeId": ""} for dt in _LINE_ITEM_SOURCE_PRIORITY
            ]
            source_line_items: dict[str, list] = {
                s["documentType"]: _get_line_items(doc_by_id, str(s.get("documentTypeId", "")))
                for s in li_sources
            }
            source_priority = [s["documentType"] for s in li_sources]

            for item in payload.get("items", []):
                item_code = item.get("itemCode", "")
                item_type = item.get("itemType", str(item_code))
                serial = item.get("serial", 1)
                li_idx = serial - 1

                expiry = _parse_date_safe(item.get("expiryDate"))
                source_label = "declaration"

                if expiry is None:
                    for dt in source_priority:
                        li_list = source_line_items[dt]
                        if 0 <= li_idx < len(li_list):
                            expiry = _li_expiry(li_list[li_idx])
                            if expiry is not None:
                                source_label = dt.replace("_", " ")
                                break

                if expiry is None:
                    findings.append({
                        "ruleCode": "FOOD_NOT_EXPIRED",
                        "result": "WARN",
                        "itemCode": item_code,
                        "message": (
                            f"Item '{item_type}' expiry date could not be verified "
                            "(not found in any document line items)."
                        ),
                    })
                    continue

                if expiry <= today:
                    findings.append({
                        "ruleCode": "FOOD_NOT_EXPIRED",
                        "result": "FAIL",
                        "itemCode": item_code,
                        "message": (
                            f"Item '{item_type}' has already expired "
                            f"(expiry date: {expiry.isoformat()}, source: {source_label})."
                        ),
                    })

        elif rule_id == "ISSUE_DATE_NOT_IN_FUTURE" and isinstance(applies_to, list):
            for entry in applies_to:
                doc, doc_type = _resolve_doc(entry, doc_by_id)
                if not doc:
                    continue
                issue_date = _first_date(doc.get("fields", {}), _ISSUE_DATE_FIELDS)
                if issue_date is None:
                    continue
                if issue_date > today:
                    findings.append({
                        "ruleCode": "ISSUE_DATE_NOT_IN_FUTURE",
                        "result": "FAIL",
                        "documentType": doc_type,
                        "message": (
                            f"{doc_type.replace('_', ' ')} has an issue date in the future "
                            f"({issue_date.isoformat()}). The document may be invalid."
                        ),
                    })

        elif rule_id == "CERTIFICATE_NOT_EXPIRED" and isinstance(applies_to, list):
            for entry in applies_to:
                doc, doc_type = _resolve_doc(entry, doc_by_id)
                if not doc:
                    continue
                expiry_date = _first_date(doc.get("fields", {}), _EXPIRY_DATE_FIELDS)
                if expiry_date is None:
                    continue
                if expiry_date <= today:
                    findings.append({
                        "ruleCode": "CERTIFICATE_NOT_EXPIRED",
                        "result": "FAIL",
                        "documentType": doc_type,
                        "message": (
                            f"{doc_type.replace('_', ' ')} has expired "
                            f"(expiry date: {expiry_date.isoformat()})."
                        ),
                    })

    return findings
