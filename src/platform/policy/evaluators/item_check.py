"""
Item Check Rule Engine

Compares declared payload items against extracted document line items.
"""

import logging
import re
from datetime import date

from src.platform.policy.evaluators import llm_mapper

logger = logging.getLogger(__name__)

_SOURCE_DOC_PRIORITY = ["Packing_List", "Stretching_List", "Invoice"]
_TOLERANCE = 0.02
_CONDITIONAL_TOLERANCE = 0.05
_MT_THRESHOLD = 500.0
_MAX_REALISTIC_NW_KG = 1_000_000.0


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


def _numeric_match(a: float | None, b: float | None, tol: float = _TOLERANCE) -> bool:
    if a is None or b is None:
        return True
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 0.001
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def _weight_result(a: float | None, b: float | None) -> str:
    if a is None or b is None:
        return "PASS"
    if _numeric_match(a, b, _TOLERANCE):
        return "PASS"
    if _numeric_match(a, b, _CONDITIONAL_TOLERANCE):
        return "CONDITIONAL_PASS"
    return "FAIL"


def _to_kg(value: float, declared_kg: float | None) -> float:
    if declared_kg is not None and value < _MT_THRESHOLD and declared_kg >= _MT_THRESHOLD:
        return value * 1000
    return value


def _get_doc_line_items(submission: list, doc_type: str) -> list:
    for doc in submission:
        if doc.get("document") == doc_type:
            return doc.get("lineItems") or []
    return []


def _payload_net_weight_kg(item: dict) -> float | None:
    qty = item.get("itemQty")
    net_unit = item.get("netUnitWgt")
    if qty is None or net_unit is None:
        return None
    pack_size = float(item.get("pack") or 1)
    item_unit = (item.get("itemUnit") or "g").lower().strip()
    unit_wgt = float(net_unit)
    if item_unit == "g":
        unit_wgt /= 1000
    elif item_unit in ("mt", "t"):
        unit_wgt *= 1000
    return round(float(qty) * pack_size * unit_wgt, 3)


def _li_value(line_item: dict, *field_names: str):
    for name in field_names:
        entry = line_item.get(name)
        if isinstance(entry, dict):
            v = entry.get("value")
            if v is not None:
                return v
    return None


def _short_desc(desc: str | None, maxlen: int = 45) -> str:
    if not desc:
        return ""
    ascii_parts = re.findall(r'[A-Za-z0-9][A-Za-z0-9 ()\-./,]+', desc)
    if ascii_parts:
        best = max(ascii_parts, key=len).strip()
        if len(best) > 8:
            return (best[:maxlen] + "…") if len(best) > maxlen else best
    clean = desc.strip()
    return (clean[:maxlen] + "…") if len(clean) > maxlen else clean


def _fmt_date(s) -> str:
    if not s:
        return str(s or "")
    try:
        d = date.fromisoformat(str(s).strip()[:10])
        return f"{d.day} {d.strftime('%b')} {d.year}"
    except ValueError:
        return str(s)


def _find_source_doc(submission: list) -> tuple[str | None, list]:
    for doc_type in _SOURCE_DOC_PRIORITY:
        for doc in submission:
            if doc.get("document") == doc_type:
                line_items = doc.get("lineItems") or []
                if line_items:
                    return doc_type, line_items
    return None, []


def validate_item_checks(payload: dict, submission: list) -> list:
    """Compare each payload item against line items from Packing_List / Stretching_List / Invoice."""
    request_id = payload.get("requestId", "")
    items = payload.get("items", [])
    findings = []

    if not items:
        return findings

    source_doc_type, line_items = _find_source_doc(submission)

    all_source_docs: dict[str, list] = {
        dt: _get_doc_line_items(submission, dt)
        for dt in _SOURCE_DOC_PRIORITY
        if _get_doc_line_items(submission, dt)
    }

    if source_doc_type is None:
        logger.warning("[item_check] No packing/invoice document with line items | requestId=%s", request_id)
        return findings

    logger.info("[item_check] Using %s (%d line items) | requestId=%s", source_doc_type, len(line_items), request_id)

    for item in items:
        item_code = item.get("itemCode")
        serial = item.get("serial", 1)
        li_idx = serial - 1

        if li_idx < 0 or li_idx >= len(line_items):
            logger.debug("[item_check] No line item at index %d for itemCode=%s", li_idx, item_code)
            continue

        li = line_items[li_idx]
        doc_label = source_doc_type.replace("_", " ")
        li_desc_raw = _li_value(li, "item_description", "product_description", "goods_description")
        item_label = _short_desc(li_desc_raw) or f"Item {item_code}"

        net_unit_wgt = item.get("netUnitWgt")
        item_unit = (item.get("itemUnit") or "g").lower().strip()
        declared_nw_kg = _payload_net_weight_kg(item)

        if net_unit_wgt is None:
            findings.append({
                "ruleCode": f"ITEM_NW_MISSING_{serial:03d}",
                "result": "FAIL",
                "message": f"{item_label}: net unit weight is missing from the declaration.",
                "itemCode": item_code,
                "evidence": {"Payload_Declared": "missing"},
            })
        else:
            nw_raw = float(net_unit_wgt)
            nw_kg = nw_raw / 1000 if item_unit == "g" else nw_raw
            if nw_kg <= 0:
                findings.append({
                    "ruleCode": f"ITEM_NW_INVALID_{serial:03d}",
                    "result": "FAIL",
                    "message": f"{item_label}: declared net unit weight is {nw_raw} {item_unit}, which must be greater than zero.",
                    "itemCode": item_code,
                    "evidence": {"Payload_Declared": f"{nw_raw} {item_unit}"},
                })
            elif declared_nw_kg is not None and declared_nw_kg > _MAX_REALISTIC_NW_KG:
                findings.append({
                    "ruleCode": f"ITEM_NW_UNREALISTIC_{serial:03d}",
                    "result": "FAIL",
                    "message": (
                        f"{item_label}: computed net weight {declared_nw_kg:,.1f} kg is unrealistically high. "
                        f"Check that the declared unit is correct (currently '{item_unit}')."
                    ),
                    "itemCode": item_code,
                    "evidence": {"Payload_Declared": f"{declared_nw_kg:,.3f} kg"},
                })

        declared_qty = item.get("itemQty")
        li_qty_raw = _li_value(li, "quantity_or_number_of_packages", "quantity")
        li_qty = _parse_numeric(li_qty_raw)
        declared_qty_f = float(declared_qty) if declared_qty is not None else None

        if not _numeric_match(declared_qty_f, li_qty):
            findings.append({
                "ruleCode": f"ITEM_QTY_{serial:03d}",
                "result": "FAIL",
                "message": f"{item_label}: {doc_label} shows {li_qty_raw}, declaration says {declared_qty}",
                "itemCode": item_code,
                "evidence": {source_doc_type: li_qty_raw, "Payload_Declared": str(declared_qty)},
            })

        li_nw_raw = _li_value(li, "net_weight")
        li_nw = _parse_numeric(li_nw_raw)
        li_nw_kg = _to_kg(li_nw, declared_nw_kg) if li_nw is not None else None

        nw_result = _weight_result(declared_nw_kg, li_nw_kg)
        if nw_result != "PASS":
            findings.append({
                "ruleCode": f"ITEM_NW_{serial:03d}",
                "result": nw_result,
                "message": (
                    f"{item_label}: {doc_label} shows {li_nw_raw}, declaration says "
                    f"{declared_nw_kg:.3f} kg" if declared_nw_kg is not None
                    else f"{item_label}: {doc_label} shows {li_nw_raw}, declaration value missing"
                ),
                "itemCode": item_code,
                "evidence": {
                    source_doc_type: li_nw_raw,
                    "Payload_Declared": f"{declared_nw_kg:.3f} kg" if declared_nw_kg is not None else "N/A",
                },
            })

        nw_values: dict[str, float] = {}
        if li_nw_kg is not None:
            nw_values[source_doc_type] = li_nw_kg

        for other_doc_type, other_line_items in all_source_docs.items():
            if other_doc_type == source_doc_type:
                continue
            if li_idx >= len(other_line_items):
                continue
            other_li = other_line_items[li_idx]
            other_nw_raw = _li_value(other_li, "net_weight")
            other_nw = _parse_numeric(other_nw_raw)
            if other_nw is not None:
                nw_values[other_doc_type] = _to_kg(other_nw, declared_nw_kg)

        if len(nw_values) >= 2:
            nw_vals = list(nw_values.values())
            max_v, min_v = max(nw_vals), min(nw_vals)
            ref = max_v if max_v != 0 else 1
            deviation = (max_v - min_v) / ref
            if deviation > _CONDITIONAL_TOLERANCE:
                xdoc_result = "FAIL" if deviation > _TOLERANCE * 2 else "CONDITIONAL_PASS"
                findings.append({
                    "ruleCode": f"ITEM_NW_XDOC_{serial:03d}",
                    "result": xdoc_result,
                    "message": f"Item {item_code}: net weight inconsistency across documents (deviation {deviation:.1%}).",
                    "itemCode": item_code,
                    "evidence": {k: f"{v:.3f} kg" for k, v in nw_values.items()},
                })

        declared_coo = item.get("countryOfOrigin")
        li_coo_raw = _li_value(li, "country_of_origin_per_item", "country_of_origin")
        if declared_coo and li_coo_raw:
            declared_coo_norm = llm_mapper.normalize_country(str(declared_coo))
            li_coo_norm = llm_mapper.normalize_country(li_coo_raw)
            if declared_coo_norm and li_coo_norm and declared_coo_norm != li_coo_norm:
                findings.append({
                    "ruleCode": f"ITEM_COO_{serial:03d}",
                    "result": "FAIL",
                    "message": f"{item_label}: {doc_label} shows origin '{li_coo_raw}', declaration says '{declared_coo}'",
                    "itemCode": item_code,
                    "evidence": {source_doc_type: li_coo_raw, "Payload_Declared": str(declared_coo)},
                })

        declared_exp_raw = item.get("expiryDate")
        li_exp_raw = _li_value(li, "expiry_date")
        declared_exp = _parse_date(declared_exp_raw)
        li_exp = _parse_date(li_exp_raw)
        if declared_exp and li_exp and declared_exp != li_exp:
            findings.append({
                "ruleCode": f"ITEM_EXP_{serial:03d}",
                "result": "FAIL",
                "message": f"{item_label}: {doc_label} shows expiry {_fmt_date(li_exp_raw)}, declaration says {_fmt_date(declared_exp_raw)}",
                "itemCode": item_code,
                "evidence": {source_doc_type: li_exp_raw, "Payload_Declared": str(declared_exp_raw)},
            })

        declared_prod_raw = item.get("prodDate")
        li_prod_raw = _li_value(li, "production_date")
        declared_prod = _parse_date(declared_prod_raw)
        li_prod = _parse_date(li_prod_raw)
        if declared_prod and li_prod and declared_prod != li_prod:
            findings.append({
                "ruleCode": f"ITEM_PROD_{serial:03d}",
                "result": "FAIL",
                "message": f"{item_label}: {doc_label} shows production {_fmt_date(li_prod_raw)}, declaration says {_fmt_date(declared_prod_raw)}",
                "itemCode": item_code,
                "evidence": {source_doc_type: li_prod_raw, "Payload_Declared": str(declared_prod_raw)},
            })

    # Aggregate total net weight check against primary source document
    if source_doc_type:
        total_declared = sum(
            nw for item in items
            if (nw := _payload_net_weight_kg(item)) is not None
        )
        for doc in submission:
            if doc.get("document") == source_doc_type:
                fields = doc.get("fields", {})
                total_field = fields.get("total_net_weight") or fields.get("net_weight_total")
                if total_field:
                    total_val = total_field.get("value") if isinstance(total_field, dict) else total_field
                    doc_total = _parse_numeric(total_val)
                    if doc_total is not None:
                        doc_total_kg = _to_kg(doc_total, total_declared)
                        agg_result = _weight_result(total_declared, doc_total_kg)
                        if agg_result != "PASS":
                            findings.append({
                                "ruleCode": "ITEM_NW_TOTAL",
                                "result": agg_result,
                                "message": (
                                    f"Total declared net weight {total_declared:.3f} kg "
                                    f"vs {source_doc_type.replace('_', ' ')} total {total_val}."
                                ),
                                "evidence": {
                                    source_doc_type: total_val,
                                    "Payload_Declared": f"{total_declared:.3f} kg",
                                },
                            })
                break

    return findings
