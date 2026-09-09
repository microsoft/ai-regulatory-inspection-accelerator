"""
Cross-Document Rule Logic

Field comparison rules come from the CROSS_DOC_RULES rule document.
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

_COUNTRY_FIELDS = frozenset({
    "country_of_origin", "countryOfOrigin",
    "port_of_loading", "port_of_discharge",
})

_DATE_FIELDS = frozenset({
    "invoice_date", "issue_date", "declaration_date",
    "expiry_date", "production_date", "slaughter_date",
})


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


def _apply_document_fallbacks(rules: list, doc_field_index: dict) -> list:
    """Substitute Invoice when Packing_List / Stretching_List are absent."""
    _PACKING_DOCS = {"Packing_List", "Stretching_List"}
    has_packing = any(d in doc_field_index for d in _PACKING_DOCS)
    has_invoice = "Invoice" in doc_field_index
    if has_packing or not has_invoice:
        return rules
    result = []
    for rule in rules:
        resolved = [llm_mapper.resolve_document_name(d) for d in rule.get("documents", [])]
        if any(d in _PACKING_DOCS for d in resolved):
            new_docs = [
                "Invoice" if llm_mapper.resolve_document_name(d) in _PACKING_DOCS else d
                for d in rule.get("documents", [])
            ]
            rule = {**rule, "documents": new_docs}
        result.append(rule)
    return result


def _collect_field_values(rule: dict, doc_index: dict, field_resolution: dict) -> dict:
    doc_values = {}
    for rule_doc_name in rule.get("documents", []):
        sub_doc_name = llm_mapper.resolve_document_name(rule_doc_name)
        fields = doc_index.get(sub_doc_name, {})
        value = llm_mapper.get_field_value(fields, rule["field"], field_resolution, sub_doc_name)
        if value:
            doc_values[sub_doc_name] = value
    return doc_values


def _check_exact(rule: dict, doc_values: dict) -> dict:
    rule_id = rule["ruleId"]
    if len(doc_values) < 2:
        return {
            "ruleId": rule_id, "result": "NOT_APPLICABLE",
            "message": f"Fewer than 2 documents provided a value for '{rule['field']}'. Documents checked: {list(doc_values.keys())}",
            "evidence": doc_values,
            "severity": rule.get("severity", "Warning"),
        }

    if rule.get("field") in _COUNTRY_FIELDS:
        normalised = {k: llm_mapper.normalize_country(v) for k, v in doc_values.items()}
        unique = set(normalised.values())
        result = "PASS" if len(unique) == 1 else "FAIL"
        return {
            "ruleId": rule_id, "result": result,
            "message": rule.get("description", ""),
            "evidence": doc_values,
            "severity": rule.get("severity", "Warning"),
        }

    if rule.get("field") in _DATE_FIELDS:
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


async def validate_cross_docs(
    payload: dict,
    rules_input,
    submission: list,
    managed_identity_client_id: str = "",
    llm_comparison_fn=None,
    item_type_check_fn=None,
) -> dict:
    """Full cross-document validation orchestrator.

    Steps:
      A: Build flat doc field index; apply Packing/Stretching → Invoice fallback.
      B: LLM field resolution + fuzzy/semantic comparison (injectable).
      C: exactMatch rules — deterministic in-process comparison.
      D: Merge: one finding per rule (LLM result takes priority over in-process).
      E: LLM item type semantic check (injectable).
    """
    if isinstance(rules_input, list):
        rule_doc = next((r for r in rules_input if r.get("id") == "CROSS_DOC_RULES"), None)
    else:
        rule_doc = rules_input if rules_input.get("id") == "CROSS_DOC_RULES" else None

    if rule_doc is None:
        return {
            "requestId": payload.get("requestId"),
            "findings": [],
            "errors": [{"code": "MISSING_RULES", "severity": "error",
                        "message": "CROSS_DOC_RULES not found in rules_input."}],
        }

    cross_doc_rules = rule_doc.get("crossDocumentRules", [])

    def _is_valid(r: dict) -> bool:
        if not isinstance(r.get("field"), str):
            return False
        docs = r.get("documents", [])
        return isinstance(docs, list) and all(isinstance(d, str) for d in docs)

    cross_doc_rules = [r for r in cross_doc_rules if _is_valid(r)]
    request_id = payload.get("requestId", "unknown")
    errors = []

    logger.info("Cross-document validation | requestId=%s | docs=%d | rules=%d",
                request_id, len(submission), len(cross_doc_rules))

    # Step A
    doc_field_index = llm_mapper.build_doc_field_index(submission, min_confidence=0.8)
    cross_doc_rules = _apply_document_fallbacks(cross_doc_rules, doc_field_index)

    # Step B
    field_resolution = {}
    llm_findings_by_rule = {}
    if llm_comparison_fn is None:
        logger.warning("No llm_comparison_fn provided — skipping LLM checks")
    else:
        try:
            llm_result = await llm_comparison_fn(
                payload=payload,
                cross_doc_rules=cross_doc_rules,
                submission=submission,
                managed_identity_client_id=managed_identity_client_id,
            )
            if not llm_result.get("success"):
                errors.extend(llm_result.get("errors", []))
            else:
                field_resolution = llm_result.get("field_resolution", {})
                rule_severity_map = {r["ruleId"]: r.get("severity", "Warning") for r in cross_doc_rules}
                for f in llm_result.get("comparison_findings", []):
                    llm_findings_by_rule[f["ruleId"]] = {
                        "ruleId": f["ruleId"],
                        "result": f.get("result", "NOT_APPLICABLE"),
                        "message": f.get("explanation", ""),
                        "evidence": f.get("evidence", ""),
                        "affectedDocs": f.get("affectedDocs", []),
                        "confidence": f.get("confidence"),
                        "severity": rule_severity_map.get(f["ruleId"], "Warning"),
                    }
        except Exception as exc:
            if getattr(exc, "status_code", None) in (401, 403):
                raise RuntimeError(
                    f"OpenAI auth failure (HTTP {exc.status_code}) during cross-document checks. "
                    f"Original error: {exc}"
                ) from exc
            logger.error("LLM cross-doc checks failed: %s", exc)
            errors.append({"code": "LLM_ERROR", "severity": "error", "message": str(exc)})

    # Step C
    in_process_findings = {}
    for rule in cross_doc_rules:
        if rule.get("comparisonType") != "exactMatch":
            continue
        doc_values = _collect_field_values(rule, doc_field_index, field_resolution)
        finding = _check_exact(rule, doc_values)
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

    # Step E
    item_type_findings = []
    if item_type_check_fn is not None:
        items = payload.get("items", [])
        _SOURCE_PRIORITY = ["Packing_List", "Stretching_List", "Invoice"]
        source_doc_type = None
        source_line_items = []
        for doc_type in _SOURCE_PRIORITY:
            for doc in submission:
                if doc.get("document") == doc_type and doc.get("lineItems"):
                    source_doc_type = doc_type
                    source_line_items = doc["lineItems"]
                    break
            if source_doc_type:
                break
        if source_doc_type and items:
            try:
                item_type_findings = await item_type_check_fn(
                    items=items,
                    source_doc_type=source_doc_type,
                    line_items=source_line_items,
                    managed_identity_client_id=managed_identity_client_id,
                )
            except Exception as exc:  # noqa: BLE001 - optional LLM check must not abort rules
                logger.error("LLM item type checks failed: %s", exc)

    return {
        "requestId": request_id,
        "findings": ordered_findings,
        "item_type_findings": item_type_findings,
        "errors": errors,
        "field_resolution": field_resolution,
    }
