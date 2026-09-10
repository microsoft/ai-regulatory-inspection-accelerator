"""
Line Item Reconciliation

Compares declared payload items against line items extracted from documents.

Every attribute name, source-document priority, tolerance, unit multiplier and
finding code comes from the active template's rule. Derived values are declared
as data (an operator plus operands), never as an expression, so a template stays
free of executable logic.
"""

import logging
import re
from datetime import date

from src.platform.policy.evaluators import llm_mapper

logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 0.02
DEFAULT_CONDITIONAL_TOLERANCE = 0.05

COMPARISON_NUMERIC = "numeric"
COMPARISON_DATE = "date"
COMPARISON_COUNTRY = "country"
COMPARISON_TEXT = "text"


def _parse_date(s) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None


def _parse_numeric(s) -> float | None:
    if s is None:
        return None
    cleaned = re.sub(r"[, ]", "", str(s))
    match = re.search(r"\d+\.?\d*", cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _numeric_match(a: float | None, b: float | None, tol: float) -> bool:
    if a is None or b is None:
        return True
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 0.001
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def _li_value(line_item: dict, field_names) -> object | None:
    for name in field_names:
        entry = line_item.get(name)
        if isinstance(entry, dict):
            value = entry.get("value")
            if value is not None:
                return value
        elif entry is not None:
            return entry
    return None


def _doc_line_items(submission: list, doc_type: str) -> list:
    for doc in submission:
        if doc.get("document") == doc_type:
            return doc.get("lineItems") or []
    return []


def _scale_to_reference(value: float, reference: float | None, inference: dict | None) -> float:
    """Promote a value to the reference's magnitude when the units clearly differ."""
    if not inference or reference is None:
        return value
    threshold = inference.get("threshold")
    multiplier = inference.get("multiplier", 1)
    if threshold is None:
        return value
    if value < threshold <= reference:
        return value * multiplier
    return value


def _derive_value(item: dict, spec: dict) -> float | None:
    """Evaluate a declarative derived value. Only the `product` operator is supported."""
    if spec.get("operator") != "product":
        logger.warning("Unsupported derived value operator: %s", spec.get("operator"))
        return None

    total = 1.0
    for operand in spec.get("operands", []):
        raw = item.get(operand["attribute"], operand.get("default"))
        if raw is None:
            return None
        value = _parse_numeric(raw)
        if value is None:
            return None
        unit_attribute = operand.get("unitAttribute")
        if unit_attribute:
            unit = str(item.get(unit_attribute) or operand.get("defaultUnit") or "").lower().strip()
            multipliers = operand.get("unitMultipliers", {})
            value *= multipliers.get(unit, 1)
        total *= value

    precision = spec.get("round")
    return round(total, precision) if precision is not None else total


def _resolve_declared(item: dict, spec: dict, derived: dict):
    if "derived" in spec:
        return derived.get(spec["derived"])
    return item.get(spec.get("attribute"))


def _label(line_item: dict, label_fields, fallback: str) -> str:
    raw = _li_value(line_item, label_fields)
    if not raw:
        return fallback
    text = str(raw).strip()
    return (text[:45] + "…") if len(text) > 45 else text


def _compare(comparison: dict, declared, extracted_raw, tolerance: float, conditional: float) -> str:
    kind = comparison.get("type", COMPARISON_TEXT)

    if kind == COMPARISON_NUMERIC:
        declared_num = _parse_numeric(declared)
        extracted_num = _parse_numeric(extracted_raw)
        if extracted_num is not None:
            extracted_num = _scale_to_reference(
                extracted_num, declared_num, comparison.get("unitInference")
            )
        if _numeric_match(declared_num, extracted_num, tolerance):
            return "PASS"
        if comparison.get("conditionalTolerance") and _numeric_match(
            declared_num, extracted_num, conditional
        ):
            return "CONDITIONAL_PASS"
        return comparison.get("failResult", "FAIL")

    if kind == COMPARISON_DATE:
        declared_date = _parse_date(declared)
        extracted_date = _parse_date(extracted_raw)
        if declared_date is None or extracted_date is None:
            return "PASS"
        return "PASS" if declared_date == extracted_date else comparison.get("failResult", "FAIL")

    if kind == COMPARISON_COUNTRY:
        if not declared or not extracted_raw:
            return "PASS"
        left = llm_mapper.normalize_country(str(declared))
        right = llm_mapper.normalize_country(str(extracted_raw))
        if not left or not right:
            return "PASS"
        return "PASS" if left == right else comparison.get("failResult", "FAIL")

    if declared is None or extracted_raw is None:
        return "PASS"
    left = str(declared).strip().lower()
    right = str(extracted_raw).strip().lower()
    return "PASS" if left == right else comparison.get("failResult", "FAIL")


def _sanity_findings(rule: dict, item: dict, derived: dict, serial: int, item_code, label: str) -> list:
    findings = []
    for check in rule.get("sanityChecks", []):
        kind = check.get("check")
        value = _resolve_declared(item, check, derived)

        if kind == "required" and value is None:
            findings.append({
                "ruleCode": f"{check['id']}_{serial:03d}",
                "result": check.get("failResult", "FAIL"),
                "itemCode": item_code,
                "message": f"{label}: {check.get('label', check['id'])} is missing from the submission.",
                "evidence": {"Declared": "missing"},
            })
            continue

        numeric = _parse_numeric(value)
        if numeric is None:
            continue

        if kind == "positive" and numeric <= 0:
            findings.append({
                "ruleCode": f"{check['id']}_{serial:03d}",
                "result": check.get("failResult", "FAIL"),
                "itemCode": item_code,
                "message": f"{label}: {check.get('label', check['id'])} is {numeric}, which must be greater than zero.",
                "evidence": {"Declared": str(numeric)},
            })
        elif kind == "maximum" and check.get("value") is not None and numeric > check["value"]:
            findings.append({
                "ruleCode": f"{check['id']}_{serial:03d}",
                "result": check.get("failResult", "FAIL"),
                "itemCode": item_code,
                "message": (
                    f"{label}: {check.get('label', check['id'])} is {numeric:,.3f}, "
                    f"above the configured maximum of {check['value']:,.0f}."
                ),
                "evidence": {"Declared": f"{numeric:,.3f}"},
            })
    return findings


def validate_line_items(rule: dict, payload: dict, submission: list) -> list:
    """Reconcile declared payload items against extracted document line items."""
    items = payload.get("items", [])
    findings: list = []
    if not items or not rule:
        return findings

    sources = rule.get("lineItemSources", [])
    label_fields = rule.get("labelFields", [])
    tolerances = rule.get("tolerances", {})
    tolerance = tolerances.get("default", DEFAULT_TOLERANCE)
    conditional = tolerances.get("conditional", DEFAULT_CONDITIONAL_TOLERANCE)
    derived_specs = rule.get("derivedValues", [])
    comparisons = rule.get("comparisons", [])

    available = {dt: _doc_line_items(submission, dt) for dt in sources}
    available = {dt: li for dt, li in available.items() if li}

    source_doc_type = next((dt for dt in sources if dt in available), None)
    if source_doc_type is None:
        logger.info("No source document with line items for reconciliation")
        return findings

    line_items = available[source_doc_type]
    doc_label = source_doc_type.replace("_", " ")

    for item in items:
        item_code = item.get("itemCode")
        serial = item.get("serial", 1)
        index = serial - 1
        if index < 0 or index >= len(line_items):
            continue

        line_item = line_items[index]
        derived = {
            spec["name"]: _derive_value(item, spec)
            for spec in derived_specs
        }
        label = _label(line_item, label_fields, f"Item {item_code}")

        findings.extend(_sanity_findings(rule, item, derived, serial, item_code, label))

        for comparison in comparisons:
            declared = _resolve_declared(item, comparison.get("declared", {}), derived)
            extracted_raw = _li_value(line_item, comparison.get("extracted", {}).get("fields", []))
            result = _compare(comparison, declared, extracted_raw, tolerance, conditional)
            if result == "PASS":
                continue
            findings.append({
                "ruleCode": f"{comparison['id']}_{serial:03d}",
                "result": result,
                "itemCode": item_code,
                "message": (
                    f"{label}: {doc_label} shows {extracted_raw}, submission says {declared}"
                ),
                "evidence": {source_doc_type: extracted_raw, "Declared": str(declared)},
            })

        findings.extend(
            _cross_document_findings(rule, available, source_doc_type, index, serial, item_code, derived, conditional, tolerance)
        )

    findings.extend(_aggregate_findings(rule, items, submission, source_doc_type, derived_specs, tolerance, conditional))
    return findings


def _cross_document_findings(
    rule, available, source_doc_type, index, serial, item_code, derived, conditional, tolerance
) -> list:
    spec = rule.get("crossDocumentComparison")
    if not spec:
        return []

    reference = derived.get(spec.get("derived"))
    values: dict[str, float] = {}
    for doc_type, doc_line_items in available.items():
        if index >= len(doc_line_items):
            continue
        raw = _li_value(doc_line_items[index], spec.get("fields", []))
        numeric = _parse_numeric(raw)
        if numeric is not None:
            values[doc_type] = _scale_to_reference(numeric, reference, spec.get("unitInference"))

    if len(values) < 2:
        return []

    max_v, min_v = max(values.values()), min(values.values())
    ref = max_v if max_v != 0 else 1
    deviation = (max_v - min_v) / ref
    if deviation <= conditional:
        return []

    result = "FAIL" if deviation > tolerance * 2 else "CONDITIONAL_PASS"
    return [{
        "ruleCode": f"{spec['id']}_{serial:03d}",
        "result": result,
        "itemCode": item_code,
        "message": f"Item {item_code}: value inconsistency across documents (deviation {deviation:.1%}).",
        "evidence": {k: f"{v:.3f}" for k, v in values.items()},
    }]


def _aggregate_findings(
    rule, items, submission, source_doc_type, derived_specs, tolerance, conditional
) -> list:
    spec = rule.get("aggregate")
    if not spec:
        return []

    derived_spec = next((d for d in derived_specs if d["name"] == spec.get("derived")), None)
    if derived_spec is None:
        return []

    total_declared = 0.0
    for item in items:
        value = _derive_value(item, derived_spec)
        if value is not None:
            total_declared += value

    for doc in submission:
        if doc.get("document") != source_doc_type:
            continue
        fields = doc.get("fields", {})
        raw = _li_value(fields, spec.get("fields", []))
        doc_total = _parse_numeric(raw)
        if doc_total is None:
            return []
        doc_total = _scale_to_reference(doc_total, total_declared, spec.get("unitInference"))
        if _numeric_match(total_declared, doc_total, tolerance):
            return []
        result = (
            "CONDITIONAL_PASS"
            if _numeric_match(total_declared, doc_total, conditional)
            else "FAIL"
        )
        return [{
            "ruleCode": spec["id"],
            "result": result,
            "message": (
                f"Total declared {total_declared:.3f} "
                f"vs {source_doc_type.replace('_', ' ')} total {raw}."
            ),
            "evidence": {source_doc_type: raw, "Declared": f"{total_declared:.3f}"},
        }]
    return []
