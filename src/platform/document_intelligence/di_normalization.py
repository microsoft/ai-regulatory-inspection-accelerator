"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — DI Field Normalization

LLM-backed field canonicalization and normalization on top of the
rule-based functions in ``field_normalization.py``.

Both files are intentionally present and serve distinct layers:
  - ``field_normalization.py`` — pure, generic, no I/O, no LLM, no hardcoded
    domain vocabulary. All primitives (Arabic numeral/date conversion, alias
    maps, canonicalization, rule-based normalization) are config-driven and
    have no food-safety assumptions.
  - ``di_normalization.py`` (this file) — PAFN-faithful LLM wrapper. Imports
    the shared primitives from ``field_normalization`` and adds:
      • ``FIELD_ALIASES`` (food-safety / customs multilingual synonyms)
      • ``KNOWN_COUNTRIES`` (for country extraction)
      • ``COMPANY_INDICATORS`` / ``ADDRESS_INDICATORS`` (company-name heuristic)
      • ``_PAFN_CURRENCY_CODES`` (expanded Gulf + global set)
      • LLM prompt constants and LLM-call functions
      • ``canonicalize_fields_for_doc_type`` (handles Pydantic models, line items)
      • ``normalize_all_fields`` (rule-based → expiry → LLM pipeline)

No function is duplicated between the two files.
"""

import json
import logging
import re
import time

from openai import AzureOpenAI

from src.platform.document_intelligence.field_normalization import (
    build_field_alias_maps as _build_alias_maps,
    compute_expiry_from_validity_period as _compute_expiry,
    convert_arabic_numerals,
    extract_country as _extract_country_generic,
    normalize_arabic_date,
    normalize_arabic_number,
    normalize_currency as _normalize_currency_generic,
    normalize_date,
    normalize_key,
    strip_bidi_marks,
    strip_trailing_date_suffix,
    unwrap_brackets,
)
from src.platform.document_intelligence.schemas import ExtractedMetadata, KVPair, LineItem

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# LLM prompt constants
# ---------------------------------------------------------------------------

LLM_NORMALIZATION_PROMPT = """You are a document field correction expert. Your task is to review and correct extracted field values from documents.

Given the extracted fields and their values, apply intelligent corrections:

1. **OCR Error Correction**: Fix common OCR mistakes (0/O, 1/l/I, etc.)
2. **Format Standardization**:
   - Dates: Standardize to ISO-8601 (YYYY-MM-DD) when the date is clear.
     For Arabic-format dates (YYYY/MM/DD or DD/MM/YYYY), preserve the
     original month and day — do NOT swap them.
   - Numbers: Remove extra spaces, fix decimal separators.
     The Arabic decimal mark (٫) is a DECIMAL POINT (not a comma).
     Example: ٢٥٫٨٩٤.٨٧ → 25894.87 (NOT 25,894,870).
   - Currency: Ensure proper ISO code format
3. **Noise Removal**: Remove artifacts like random characters, repeated punctuation
4. **Language Preservation**:
   - KEEP Arabic text in Arabic. Do NOT translate Arabic names, addresses,
     descriptions, or any other Arabic values to English.
   - Arabic company names, person names, product descriptions, and authority
     names must remain in their original Arabic script.
   - Only fix OCR errors in Arabic text (e.g. broken characters, wrong dots).

IMPORTANT RULES:
- Only modify values that have CLEAR errors or need standardization
- Do NOT change values that are already correct
- Do NOT hallucinate or guess missing information
- Do NOT fabricate, guess, or invent corrections. Only correct values where
  the error is clearly evident from the surrounding context.
- Never change a value to something not supported by the original document text.
- NEVER translate Arabic to English. This is the most critical rule.
- Preserve original meaning, intent, and LANGUAGE of every value
- If uncertain about ANY correction, keep the original value unchanged

Respond in JSON format with ONLY the fields that need correction:
{
    "corrections": {
        "field_name": {
            "original": "original value",
            "corrected": "corrected value",
            "reason": "brief reason for correction"
        }
    },
    "no_changes_needed": ["field1", "field2"]
}

If no corrections are needed, return:
{
    "corrections": {},
    "no_changes_needed": ["all field names"]
}"""


LLM_SEMANTIC_FIELD_MAPPING_PROMPT = """You are a multilingual semantic field mapper for customs and trade documents.

You will receive:
1. A list of UNMATCHED key-value pairs extracted from a document (keys may be in Arabic, English, or mixed).
2. A list of TARGET field names that still need values.

Your task: for each unmatched key, determine which target field (if any) it semantically corresponds to.

Consider:
- The key may be in Arabic while the target field is in English (e.g. "رقم البيان" → "declaration_number")
- The key may be abbreviated or use different phrasing (e.g. "DEC NO." → "declaration_number")
- The key may contain form labels, numbers, or extra text (e.g. "1 رقم البيان DEC NO." → "declaration_number")
- Some keys may not match ANY target field — return null for those

Rules:
- Only map when the semantic meaning clearly aligns
- Return null when uncertain — do NOT force a match
- Each target field should be mapped at most once
- Do NOT invent field names beyond the provided target list

Return ONLY valid JSON — no markdown, no prose:
{
    "mappings": {
        "original_key_1": "target_field_name",
        "original_key_2": null,
        "original_key_3": "another_target_field"
    }
}"""


# ---------------------------------------------------------------------------
# PAFN-specific domain constants
# ---------------------------------------------------------------------------

FIELD_ALIASES: dict[str, list[str]] = {
    "certificate_number": [
        "certificate no", "certificate number", "cert no", "cert number", "no", "编号",
    ],
    "issue_date": [
        "issue date", "date of issue", "date issued", "签证日期", "发货日期", "date of despatch",
    ],
    "expiry_date": [
        "expiry date", "expiration date", "valid until",
    ],
    "issuing_authority": [
        "issuing authority", "authority", "entry-exit inspection", "检验检疫",
    ],
    "country_of_origin": [
        "country of origin", "origin country", "原产国",
    ],
    "country_of_destination": [
        "country of destination", "destination", "到达国家", "country and place of destination",
    ],
    "exporter_name": [
        "exporter", "consignor", "name and address of consignor", "发货人名称",
    ],
    "exporter_address": [
        "exporter address", "consignor address", "发货人地址",
    ],
    "consignee_name": [
        "consignee", "name and address of consignee", "收货人名称",
    ],
    "consignee_address": [
        "consignee address", "收货人地址",
    ],
    "goods_description": [
        "description of goods", "goods description", "品名",
    ],
    "quantity": [
        "quantity", "quantity declared", "报检数量", "数量",
    ],
    "gross_weight": [
        "gross weight", "weight", "报检重量", "重量",
        "gross weight (total)", "gross weight total", "total gross weight",
    ],
    "net_weight": [
        "net weight", "net weight (total)", "net weight total", "total net weight",
    ],
    "gross_weight_total": [
        "gross weight total", "total gross weight", "gross weight (total)",
    ],
    "net_weight_total": [
        "net weight total", "total net weight", "net weight (total)",
    ],
    "quantity_or_number_of_packages": [
        "quantity or number of packages", "number of cartons", "number of cartons (total)",
        "number of packages", "number of packages (total)", "no of cartons",
        "no of packages", "quantity",
    ],
    "package_count": [
        "package count", "number of packages", "包装数量", "packages",
    ],
    "package_type": [
        "package type", "type of packages", "包装种类",
    ],
    "inspection_details": [
        "results of inspection", "inspection details", "检验结果",
    ],
    "additional_declaration": [
        "additional declaration", "conclusion",
    ],
    "temperature_during_treatment": [
        "temperature during storage and transport", "贮藏和运输温度",
    ],
    "declaration_number": [
        "dec no", "declaration number", "رقم البيان",
    ],
    "declaration_date": [
        "dec date", "declaration date", "تاريخ البيان",
    ],
    "declaration_type": [
        "dec type", "declaration type", "نوع البيان",
    ],
    "port_type": [
        "port type", "نوع المنفذ",
    ],
    "delivery_order_number": [
        "delivery order no", "delivery order number", "رقم إذن التسليم",
    ],
    "importer_or_exporter_name": [
        "importer", "exporter", "المستورد", "المصدر",
    ],
    "commercial_registration_number": [
        "commercial registration", "registration number", "السجل التجاري",
    ],
    "bill_awb_manifest_number": [
        "bill of lading", "awb", "manifest number", "رقم بوليصة الشحن",
    ],
    "carrier_name": [
        "carrier", "captain", "driver", "الناقلة", "القبطان", "السائق",
    ],
    "voyage_or_flight_number": [
        "voyage no", "flight no", "voyage number", "flight number", "رقم الرحلة",
    ],
    "tin_number": [
        "tin no", "tin number", "الرقم الضريبي", "الرقم الضريبى",
    ],
    "total_net_weight": [
        "net weight", "total net weight", "net weight total", "net weight (total)", "الوزن الصافي",
    ],
    "total_gross_weight": [
        "gross weight", "total gross weight", "gross weight total", "gross weight (total)", "الوزن القائم",
    ],
    "total_number_of_packages": [
        "no of packages", "number of packages", "total packages", "عدد الطرود",
    ],
    "total_duty": [
        "total duty", "اجمالي الرسوم",
    ],
    "destination": [
        "destination", "جهة المقصد",
    ],
    "port_of_discharge": [
        "port of discharge", "ميناء التفريغ",
    ],
    "port_of_loading": [
        "port of loading", "ميناء الشحن",
    ],
}

COMPANY_INDICATORS = re.compile(
    r'\b(Ltd|Limited|Inc|Corp|Corporation|Co\.|Company|LLC|LLP|PLC|'
    r'V\.O\.F\.|B\.V\.|N\.V\.|GmbH|AG|S\.A\.|S\.L\.|Pty|Processors|'
    r'Trading|Transport|ذ\.?م\.?م|شركة)\b',
    re.IGNORECASE
)

ADDRESS_INDICATORS = re.compile(
    r'\b(Street|St\.|Road|Rd\.|Avenue|Ave\.|Box|PO Box|P\.O\.|'
    r'Floor|Building|Bldg|Suite|Block|Plot|Area|City|'
    r'\d{4,6})\b',
    re.IGNORECASE
)

KNOWN_COUNTRIES = [
    "Australia", "New Zealand", "India", "Pakistan", "Kenya", "Brazil",
    "United States", "USA", "UK", "United Kingdom", "China", "Japan",
    "Thailand", "Indonesia", "Malaysia", "Philippines", "Vietnam",
    "Saudi Arabia", "UAE", "Kuwait", "Qatar", "Bahrain", "Oman",
    "Egypt", "Turkey", "Jordan", "Lebanon", "Syria", "Iraq", "Iran",
    "France", "Germany", "Italy", "Spain", "Netherlands", "Belgium",
]

# Gulf + global currency set — wider than field_normalization's DEFAULT_CURRENCY_CODES.
_PAFN_CURRENCY_CODES = frozenset({
    "USD", "AUD", "EUR", "GBP", "JPY", "CAD", "CHF", "CNY", "HKD",
    "NZD", "SEK", "KRW", "SGD", "NOK", "MXN", "INR",
    "AED", "SAR", "KWD", "BHD", "OMR", "QAR",
})

# PAFN date and numeric field sets used by apply_rule_based_normalization.
_DATE_FIELDS = frozenset({
    "issue_date", "expiry_date", "invoice_date", "production_date",
    "slaughter_date", "packing_date", "inspection_date",
    "certificate_validity_date", "license_issue_date",
    "license_expiry_date", "renewal_date", "date_of_departure",
    "certificate_issue_date", "certificate_expiry_date",
    "license_start_date", "authorization_effective_date",
    "payment_date", "receipt_date", "release_date",
    "entered_date", "actual_arrival_date",
})

_NUMERIC_FIELDS = frozenset({
    "gross_weight", "net_weight", "weight", "quantity",
    "quantity_or_weight", "total_net_weight", "total_gross_weight",
    "gross_weight_total", "net_weight_total",
    "invoice_total_amount", "unit_price", "line_amount",
    "vat_amount", "excise_tax", "freight_amount",
    "number_of_packages", "item_qty",
})

# Issue-date fields in PAFN priority order for expiry computation.
_ISSUE_DATE_FIELDS = ("issue_date", "certificate_issue_date", "license_issue_date")


# ---------------------------------------------------------------------------
# Thin wrappers — supply PAFN defaults to field_normalization primitives
# ---------------------------------------------------------------------------

def build_field_alias_maps(allowed_fields: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Build alias maps using FIELD_ALIASES as the default alias_overrides."""
    return _build_alias_maps(allowed_fields, alias_overrides=FIELD_ALIASES)


def _extract_country(value: str) -> str | None:
    return _extract_country_generic(value, KNOWN_COUNTRIES)


def _normalize_currency(value: str) -> str | None:
    return _normalize_currency_generic(value, _PAFN_CURRENCY_CODES)


def compute_expiry_from_validity_period(fields: dict) -> dict:
    """Compute expiry_date using the PAFN issue-date field priority order."""
    return _compute_expiry(fields, issue_date_fields=_ISSUE_DATE_FIELDS)


# ---------------------------------------------------------------------------
# PAFN-specific rule-based normalization
# (delegates pure math to imported functions from field_normalization)
# ---------------------------------------------------------------------------

def apply_rule_based_normalization(fields: dict) -> dict:
    """Apply PAFN-specific rule-based cleanup and Arabic normalization.

    The ``_DATE_FIELDS`` and ``_NUMERIC_FIELDS`` sets are algorithm content
    (they define which fields receive specialized normalization).  All math
    functions are imported from ``field_normalization``; no logic is duplicated.
    """
    if "invoice_number" in fields and fields["invoice_number"].get("value"):
        original = str(fields["invoice_number"]["value"])
        cleaned = strip_trailing_date_suffix(original)
        if cleaned != original:
            fields["invoice_number"]["value"] = cleaned
            if "confidence" in fields["invoice_number"]:
                fields["invoice_number"]["confidence"] = round(
                    fields["invoice_number"]["confidence"] * 0.98, 4
                )

    if "certificate_number" in fields and fields["certificate_number"].get("value"):
        original = str(fields["certificate_number"]["value"])
        cleaned = unwrap_brackets(original)
        if cleaned != original:
            fields["certificate_number"]["value"] = cleaned

    if "issue_date" in fields and fields["issue_date"].get("value"):
        value = str(fields["issue_date"]["value"])
        extracted_date = normalize_date(value)
        if extracted_date and extracted_date != value:
            fields["issue_date"]["value"] = extracted_date
            if "confidence" in fields["issue_date"]:
                fields["issue_date"]["confidence"] = round(
                    fields["issue_date"]["confidence"] * 0.98, 4
                )

    if "country_of_origin" in fields and fields["country_of_origin"].get("value"):
        value = str(fields["country_of_origin"]["value"])
        extracted_country = _extract_country(value)
        if extracted_country:
            fields["country_of_origin"]["value"] = extracted_country

    if "currency" in fields and "invoice_amount" in fields:
        currency_value = fields["currency"].get("value")
        amount_value = fields["invoice_amount"].get("value")
        if not currency_value and amount_value:
            inferred_currency = _normalize_currency(str(amount_value))
            if inferred_currency:
                amount_confidence = fields["invoice_amount"].get("confidence", 0.85)
                fields["currency"] = {
                    "value": inferred_currency,
                    "confidence": round(amount_confidence * 0.95, 4),
                }

    for field_name in _DATE_FIELDS:
        if field_name in fields and fields[field_name].get("value"):
            raw_val = str(fields[field_name]["value"])
            has_eastern = any("\u0660" <= ch <= "\u0669" for ch in raw_val)
            has_slashes = "/" in raw_val
            is_already_iso = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", raw_val))
            if (has_eastern or has_slashes) and not is_already_iso:
                normalized_date = normalize_arabic_date(raw_val)
                if normalized_date and normalized_date != raw_val:
                    fields[field_name]["value"] = normalized_date

    for field_name in _NUMERIC_FIELDS:
        if field_name in fields and fields[field_name].get("value"):
            raw_val = str(fields[field_name]["value"])
            normalized_num = normalize_arabic_number(raw_val)
            if normalized_num and normalized_num != raw_val:
                fields[field_name]["value"] = normalized_num

    for field_name, fv in fields.items():
        if field_name in _DATE_FIELDS or field_name in _NUMERIC_FIELDS:
            continue
        if fv.get("value") and isinstance(fv["value"], str):
            converted = convert_arabic_numerals(fv["value"])
            if converted != fv["value"]:
                fv["value"] = converted

    return fields


# ---------------------------------------------------------------------------
# LLM-based semantic field mapping
# ---------------------------------------------------------------------------

def resolve_unmatched_fields_with_llm(
    openai_client: AzureOpenAI,
    unmatched_kvs: list[dict],
    unfilled_fields: list[str],
    doc_type: str,
    *,
    deployment: str = "gpt-5.4",
) -> dict[str, str]:
    """Use an LLM call to semantically map unmatched KV keys to target fields.

    Ported unchanged from PAFN's di_normalization.py.
    """
    if not unmatched_kvs or not unfilled_fields:
        return {}

    user_message = json.dumps({
        "document_type": doc_type,
        "unmatched_keys": [kv["key"] for kv in unmatched_kvs],
        "target_fields": unfilled_fields,
    }, ensure_ascii=False, indent=2)

    try:
        response = openai_client.chat.completions.create(
            model=deployment,
            temperature=0.0,
            seed=42,
            max_completion_tokens=1000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": LLM_SEMANTIC_FIELD_MAPPING_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        data = json.loads(response.choices[0].message.content.strip())
        mappings = data.get("mappings", {})
        unfilled_set = set(unfilled_fields)
        used_targets: set[str] = set()
        valid: dict[str, str] = {}
        for key, target in mappings.items():
            if target and target in unfilled_set and target not in used_targets:
                valid[key] = target
                used_targets.add(target)
        if valid:
            logging.info(
                "Semantic field mapping | doc_type=%s | resolved=%d/%d: %s",
                doc_type, len(valid), len(unmatched_kvs), valid,
            )
        return valid
    except Exception as exc:
        logging.warning("Semantic field mapping failed for doc_type=%s: %s", doc_type, exc)
        return {}


# ---------------------------------------------------------------------------
# Field canonicalization
# ---------------------------------------------------------------------------

def canonicalize_fields_for_doc_type(
    metadata: ExtractedMetadata,
    doc_type: str,
    openai_client: AzureOpenAI | None = None,
    *,
    allowed_fields: list[str],
    line_item_fields: list[str],
    deployment: str = "gpt-5.4",
) -> tuple[dict, list[dict]]:
    """Map raw extracted KV pairs onto the document type's canonical field schema.

    Ported from PAFN's di_normalization.py.  The sole change is that
    ``allowed_fields`` and ``line_item_fields`` are now explicit parameters
    (sourced from the active ``TemplateLoader``) instead of being looked up
    from ``document_type_fields.json``.

    Args:
        metadata: Structured metadata from the LLM extraction step.
        doc_type: Document type key (for LLM context messages).
        openai_client: Optional LLM client for semantic field mapping.
        allowed_fields: Canonical field names for this document type.
        line_item_fields: Per-row field names for line-item tables.
        deployment: Azure OpenAI deployment name.

    Returns:
        Tuple of (fields dict, line_items list).
    """
    exact_aliases, normalized_aliases = build_field_alias_maps(allowed_fields)
    fields: dict = {field: {"value": None} for field in allowed_fields}
    standalone_value_fields = {"company_name", "invoice_number"}

    # 1) Primary: canonical_field provided by LLM
    for kv in metadata.key_value_pairs:
        canonical = (kv.canonical_field or "").strip()
        if canonical not in allowed_fields:
            continue
        key_text = (kv.key or "").strip()
        value_text = (kv.value or "").strip()

        value = value_text
        if canonical in standalone_value_fields:
            if not value and key_text:
                value = key_text
            elif canonical == "company_name" and key_text and value:
                key_is_company = bool(COMPANY_INDICATORS.search(key_text))
                value_is_address = bool(ADDRESS_INDICATORS.search(value))
                if key_is_company and value_is_address:
                    value = key_text

        if not value:
            continue

        current = fields.get(canonical)
        new_conf = round(float(kv.confidence), 4)
        if current.get("value") is None or new_conf > current.get("confidence", 0):
            fields[canonical] = {"value": value, "confidence": new_conf}

    # 2) Fallback: alias resolution on the raw key
    for kv in metadata.key_value_pairs:
        if (kv.canonical_field or "").strip() in allowed_fields:
            continue
        raw_key = (kv.key or "").strip()
        if not raw_key:
            continue
        candidate = exact_aliases.get(raw_key.lower())
        if candidate is None:
            candidate = normalized_aliases.get(normalize_key(raw_key))
        if candidate is None:
            continue
        if not (kv.value or "").strip():
            continue
        current = fields.get(candidate)
        new_conf = round(float(kv.confidence), 4)
        if current.get("value") is None or new_conf > current.get("confidence", 0):
            fields[candidate] = {"value": kv.value, "confidence": new_conf}

    # 2b) LLM semantic fallback
    if openai_client is not None:
        matched_keys: set[str] = set()
        for kv in metadata.key_value_pairs:
            canonical = (kv.canonical_field or "").strip()
            raw_key = (kv.key or "").strip()
            if canonical in allowed_fields:
                matched_keys.add(raw_key)
                continue
            candidate = exact_aliases.get(raw_key.lower())
            if candidate is None:
                candidate = normalized_aliases.get(normalize_key(raw_key))
            if candidate is not None:
                matched_keys.add(raw_key)

        unmatched_kvs = [
            {"key": (kv.key or "").strip(), "value": (kv.value or "").strip(),
             "confidence": kv.confidence}
            for kv in metadata.key_value_pairs
            if (kv.key or "").strip() not in matched_keys and (kv.value or "").strip()
        ]
        unfilled_fields = [f for f in allowed_fields if fields[f].get("value") is None]

        if unmatched_kvs and unfilled_fields:
            semantic_map = resolve_unmatched_fields_with_llm(
                openai_client, unmatched_kvs, unfilled_fields, doc_type,
                deployment=deployment,
            )
            kv_by_key = {(kv.key or "").strip(): kv for kv in metadata.key_value_pairs}
            for orig_key, target_field in semantic_map.items():
                kv = kv_by_key.get(orig_key)
                if kv is None or not (kv.value or "").strip():
                    continue
                current = fields.get(target_field)
                new_conf = round(float(kv.confidence) * 0.95, 4)
                if current is not None and current.get("value") is None:
                    fields[target_field] = {
                        "value": kv.value.strip(),
                        "confidence": new_conf,
                        "semantic_mapped": True,
                    }

    # 3) Propagate equivalent field groups
    _EQUIVALENT_GROUPS = [
        ("expiry_date", "expiration_date", "certificate_validity_date"),
    ]
    for group in _EQUIVALENT_GROUPS:
        present = [f for f in group if f in fields and fields[f].get("value") is not None]
        if not present:
            continue
        source = fields[present[0]]
        for f in group:
            if f in fields and fields[f].get("value") is None:
                fields[f] = {**source}

    # 4) Process line items
    line_items: list[dict] = []
    if line_item_fields and metadata.line_items:
        for item in metadata.line_items:
            line_item_dict = {field: {"value": None} for field in line_item_fields}
            for field_name in line_item_fields:
                value = getattr(item, field_name, "")
                if value:
                    line_item_dict[field_name] = {
                        "value": str(value),
                        "confidence": round(item.confidence, 4),
                    }
            line_items.append(line_item_dict)

    # 5) Strip BiDi control marks using imported strip_bidi_marks
    for field_data in fields.values():
        v = field_data.get("value")
        if isinstance(v, str):
            field_data["value"] = strip_bidi_marks(v)
    for item in line_items:
        for field_data in item.values():
            v = field_data.get("value")
            if isinstance(v, str):
                field_data["value"] = strip_bidi_marks(v)

    return fields, line_items


# ---------------------------------------------------------------------------
# LLM field normalization
# ---------------------------------------------------------------------------

def normalize_fields_with_llm(
    openai_client: AzureOpenAI,
    fields: dict,
    line_items: list[dict],
    doc_type: str,
    file_name: str,
    *,
    allowed_fields: list[str],
    deployment: str = "gpt-5.4",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
) -> tuple[dict, list[dict], dict]:
    """Apply LLM-based intelligent field normalization.

    Ported from PAFN's di_normalization.py.  The sole change is that
    ``allowed_fields`` is now an explicit parameter (sourced from
    ``TemplateLoader``) instead of being fetched from
    ``document_type_fields.json``.
    """
    fields_summary = {
        k: v.get("value") for k, v in fields.items() if v.get("value") is not None
    }

    if not fields_summary:
        return fields, line_items, {"skipped": "no fields to normalize"}

    user_message = (
        f"Document Type: {doc_type}\nFile: {file_name}\n\n"
        f"Extracted Fields:\n{json.dumps(fields_summary, indent=2, ensure_ascii=False)}\n\n"
        "Please review and correct any errors in these extracted values."
    )

    for attempt in range(max_retries):
        try:
            response = openai_client.chat.completions.create(
                model=deployment,
                temperature=0.0,
                seed=42,
                max_completion_tokens=1500,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": LLM_NORMALIZATION_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            raw_response = response.choices[0].message.content.strip()
            data = json.loads(raw_response)
            corrections = data.get("corrections", {})
            correction_log = {
                "corrections_applied": [],
                "no_changes_needed": data.get("no_changes_needed", []),
            }
            allowed_set = set(allowed_fields)
            for field_name, correction in corrections.items():
                if field_name not in allowed_set:
                    logging.warning(
                        "LLM normalization suggested correction for unknown field %r — skipping",
                        field_name,
                    )
                    continue
                if field_name in fields and fields[field_name].get("value") is not None:
                    original = fields[field_name]["value"]
                    corrected = correction.get("corrected")
                    if corrected and corrected != original:
                        fields[field_name]["value"] = corrected
                        fields[field_name]["llm_corrected"] = True
                        correction_log["corrections_applied"].append({
                            "field": field_name,
                            "original": original,
                            "corrected": corrected,
                            "reason": correction.get("reason", "LLM correction"),
                        })
            logging.info(
                "LLM normalization completed | file=%s | corrections=%d",
                file_name, len(correction_log["corrections_applied"])
            )
            return fields, line_items, correction_log

        except json.JSONDecodeError as e:
            logging.warning(
                "LLM normalization JSON error for %s (attempt %d/%d): %s",
                file_name, attempt + 1, max_retries, e
            )
        except Exception as exc:
            logging.warning(
                "LLM normalization failed for %s (attempt %d/%d): %s",
                file_name, attempt + 1, max_retries, exc
            )
            time.sleep(retry_delay_sec * (attempt + 1))

    logging.warning(
        "LLM normalization: all retries failed for %s, using original values", file_name
    )
    return fields, line_items, {"error": "LLM normalization failed", "llm_normalization_skipped": True}


def normalize_all_fields(
    openai_client: AzureOpenAI,
    fields: dict,
    line_items: list[dict],
    doc_type: str,
    file_name: str,
    *,
    allowed_fields: list[str],
    deployment: str = "gpt-5.4",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
) -> tuple[dict, list[dict], dict]:
    """Apply rule-based normalization then LLM-based correction.

    Ported from PAFN's di_normalization.py.  ``allowed_fields`` is now an
    explicit parameter instead of being fetched from
    ``document_type_fields.json``.
    """
    normalization_log: dict = {}
    fields = apply_rule_based_normalization(fields)
    normalization_log["rule_based"] = "applied"
    fields = compute_expiry_from_validity_period(fields)

    fields, line_items, llm_log = normalize_fields_with_llm(
        openai_client, fields, line_items, doc_type, file_name,
        allowed_fields=allowed_fields,
        deployment=deployment,
        max_retries=max_retries,
        retry_delay_sec=retry_delay_sec,
    )
    normalization_log["llm"] = llm_log
    return fields, line_items, normalization_log
