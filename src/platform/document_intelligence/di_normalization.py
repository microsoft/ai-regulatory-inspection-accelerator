"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — DI Field Normalization

LLM-backed field canonicalization and normalization on top of the
rule-based functions in ``field_normalization.py``.

All document-type assumptions are supplied through the active template's
normalization profile. This module contains only the LLM orchestration and
Pydantic/line-item integration around the generic field primitives.
"""

import json
import logging
import time

from openai import AzureOpenAI

from src.platform.document_intelligence.field_normalization import (
    apply_rule_based_normalization as _apply_rule_based_normalization,
)
from src.platform.document_intelligence.field_normalization import (
    build_field_alias_maps as _build_alias_maps,
)
from src.platform.document_intelligence.field_normalization import (
    compute_expiry_from_validity_period as _compute_expiry,
)
from src.platform.document_intelligence.field_normalization import (
    extract_country as _extract_country_generic,
)
from src.platform.document_intelligence.field_normalization import (
    normalize_currency as _normalize_currency_generic,
)
from src.platform.document_intelligence.field_normalization import (
    normalize_key,
    strip_bidi_marks,
    strip_trailing_date_suffix,
    unwrap_brackets,
)
from src.platform.document_intelligence.schemas import ExtractedMetadata

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


LLM_SEMANTIC_FIELD_MAPPING_PROMPT = """You are a multilingual semantic field mapper for regulated documents.

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


def build_field_alias_maps(
    allowed_fields: list[str],
    alias_overrides: dict[str, list[str]] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build alias maps from the active template profile."""
    return _build_alias_maps(allowed_fields, alias_overrides=alias_overrides)


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
            logger.info(
                "Semantic field mapping | doc_type=%s | resolved=%d/%d: %s",
                doc_type, len(valid), len(unmatched_kvs), valid,
            )
        return valid
    except Exception as exc:  # noqa: BLE001 - optional LLM mapping must not abort extraction
        logger.warning("Semantic field mapping failed for doc_type=%s: %s", doc_type, exc)
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
    normalization_config: dict | None = None,
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
    normalization_config = normalization_config or {}
    exact_aliases, normalized_aliases = build_field_alias_maps(
        allowed_fields,
        alias_overrides=normalization_config.get("field_aliases", {}),
    )
    fields: dict = {field: {"value": None} for field in allowed_fields}
    standalone_value_fields = set(normalization_config.get("standalone_value_fields", []))

    # 1) Primary: canonical_field provided by LLM
    for kv in metadata.key_value_pairs:
        canonical = (kv.canonical_field or "").strip()
        if canonical not in allowed_fields:
            continue
        key_text = (kv.key or "").strip()
        value_text = (kv.value or "").strip()

        value = value_text
        if canonical in standalone_value_fields and not value and key_text:
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
    for group in normalization_config.get("equivalent_field_groups", []):
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
                    logger.warning(
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
            logger.info(
                "LLM normalization completed | file=%s | corrections=%d",
                file_name, len(correction_log["corrections_applied"])
            )
            return fields, line_items, correction_log

        except json.JSONDecodeError as e:
            logger.warning(
                "LLM normalization JSON error for %s (attempt %d/%d): %s",
                file_name, attempt + 1, max_retries, e
            )
        except Exception as exc:  # noqa: BLE001 - retry arbitrary SDK failures
            logger.warning(
                "LLM normalization failed for %s (attempt %d/%d): %s",
                file_name, attempt + 1, max_retries, exc
            )
            time.sleep(retry_delay_sec * (attempt + 1))

    logger.warning(
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
    normalization_config: dict | None = None,
    deployment: str = "gpt-5.4",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
) -> tuple[dict, list[dict], dict]:
    """Apply rule-based normalization then LLM-based correction.

    Ported from PAFN's di_normalization.py.  ``allowed_fields`` is now an
    explicit parameter instead of being fetched from
    ``document_type_fields.json``.
    """
    normalization_config = normalization_config or {}
    normalization_log: dict = {}
    fields = _apply_rule_based_normalization(
        fields,
        date_fields=frozenset(normalization_config.get("date_fields", [])),
        numeric_fields=frozenset(normalization_config.get("numeric_fields", [])),
    )

    for field_name in normalization_config.get("strip_trailing_date_suffix_fields", []):
        entry = fields.get(field_name)
        if entry and entry.get("value"):
            entry["value"] = strip_trailing_date_suffix(str(entry["value"]))

    for field_name in normalization_config.get("unwrap_bracket_fields", []):
        entry = fields.get(field_name)
        if entry and entry.get("value"):
            entry["value"] = unwrap_brackets(str(entry["value"]))

    known_countries = normalization_config.get("known_countries", [])
    for field_name in normalization_config.get("country_fields", []):
        entry = fields.get(field_name)
        if entry and entry.get("value") and known_countries:
            country = _extract_country_generic(str(entry["value"]), known_countries)
            if country:
                entry["value"] = country

    currency_field = normalization_config.get("currency_field")
    currency_codes = normalization_config.get("currency_codes", [])
    if currency_field and currency_codes and not fields.get(currency_field, {}).get("value"):
        for source_field in normalization_config.get("currency_source_fields", []):
            source = fields.get(source_field, {})
            if source.get("value"):
                currency = _normalize_currency_generic(
                    str(source["value"]), frozenset(currency_codes)
                )
                if currency:
                    fields[currency_field] = {
                        "value": currency,
                        "confidence": round(source.get("confidence", 0.85) * 0.95, 4),
                    }
                    break

    normalization_log["rule_based"] = "applied"
    fields = _compute_expiry(
        fields,
        issue_date_fields=tuple(normalization_config.get("issue_date_fields", ["issue_date"])),
        expiry_field=normalization_config.get("expiry_field", "expiry_date"),
    )

    fields, line_items, llm_log = normalize_fields_with_llm(
        openai_client, fields, line_items, doc_type, file_name,
        allowed_fields=allowed_fields,
        deployment=deployment,
        max_retries=max_retries,
        retry_delay_sec=retry_delay_sec,
    )
    normalization_log["llm"] = llm_log
    return fields, line_items, normalization_log
