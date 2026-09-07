"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — Vision Extraction

Vision-based field extraction for handwritten Arabic documents.

Ported from PAFN's ``di/vision_extraction.py``.  The sole change is that
``get_fields_for_doc_type(doc_type)`` calls in the prompt-builder
functions are replaced by an explicit ``fields: list[str]`` parameter
propagated from the caller (which sources the list from
``TemplateLoader``).  All algorithm logic, prompt text, retry semantics,
JSON parsing, ensemble merge strategy, and cross-validation LLM call are
identical to the PAFN production implementation.

Provides three extraction modes:
  1. Pure vision  — for fully handwritten docs where OCR is useless.
  2. Hybrid       — for mixed docs (printed + handwritten); sends both
                    partial OCR text and the image to the LLM.
  3. Ensemble     — runs both pure-vision and hybrid, merges results by
                    taking the highest-confidence value per canonical field.
"""

import base64
import json
import logging
import re
import time

from openai import AzureOpenAI

from src.platform.document_intelligence.schemas import (
    DocumentInput,
    ExtractedMetadata,
    KVPair,
    LineItem,
    TableData,
)
from src.platform.shared.ai_client import AIClient, as_ai_client
from src.platform.templates.template_loader import TemplateLoader

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers (ported unchanged)
# ---------------------------------------------------------------------------

def _detect_media_type(file_name: str) -> str:
    lower = file_name.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    if lower.endswith((".tiff", ".tif")):
        return "image/tiff"
    return "image/png"


def _normalize_response(data: dict) -> dict:
    """Normalize raw LLM JSON into typed model fields (ported unchanged)."""
    normalized_kv: list[KVPair] = []
    for kv in (data.get("key_value_pairs") or []):
        if not isinstance(kv, dict):
            continue
        raw_conf = float(kv.get("confidence", 0.0) or 0.0)
        normalized_kv.append(
            KVPair(
                key=str(kv.get("key", "")),
                value=str(kv.get("value", "")),
                confidence=max(0.0, min(1.0, raw_conf)),
                canonical_field=str(kv.get("canonical_field", "")).strip(),
            )
        )
    data["key_value_pairs"] = normalized_kv

    normalized_tables: list[TableData] = []
    for t in (data.get("tables_extracted") or []):
        if isinstance(t, dict):
            normalized_tables.append(
                TableData(
                    page_number=int(t.get("page_number", 0) or 0),
                    row_count=int(t.get("row_count", 0) or 0),
                    column_count=int(t.get("column_count", 0) or 0),
                    cells=t.get("cells", []),
                )
            )
    data["tables_extracted"] = normalized_tables

    normalized_line_items: list[LineItem] = []
    for item in (data.get("line_items") or []):
        if not isinstance(item, dict):
            continue
        raw_item_conf = float(item.get("confidence", 0.0) or 0.0)
        normalized_line_items.append(
            LineItem(
                goods_description=str(item.get("goods_description", "")),
                quantity=str(item.get("quantity", "")),
                weight=str(item.get("weight", "")),
                weight_unit=str(item.get("weight_unit", "")),
                hs_code=str(item.get("hs_code", "")),
                expiry_date=str(item.get("expiry_date", "")),
                confidence=max(0.0, min(1.0, raw_item_conf)),
            )
        )
    data["line_items"] = normalized_line_items
    data["signature_detected"] = bool(data.get("signature_detected", False))
    data.setdefault("language", "ar")
    return data


# ---------------------------------------------------------------------------
# Prompt builders (ported; get_fields_for_doc_type → fields parameter)
# ---------------------------------------------------------------------------

def _build_vision_extraction_prompt(doc_type: str, fields: list[str]) -> str:
    """Build system prompt for pure-vision field extraction.

    Changed from PAFN: ``fields`` is now an explicit parameter instead of
    being fetched from ``document_type_fields.json`` via
    ``get_fields_for_doc_type(doc_type)``.
    """
    fields_text = ", ".join(fields)
    display_name = doc_type.replace("_", " ")

    return f"""You are a bilingual (Arabic / English) document analysis expert with \
specialized capability in reading handwritten Arabic documents.

You extract structured metadata from customs, trade, and food-safety documents
used by Kuwait Customs / PAFN (Public Authority for Food and Nutrition).

The document type is already known: **{display_name}**

═══════════════════════════════════════════════════════════════
TASK: VISUAL FIELD EXTRACTION (HANDWRITTEN DOCUMENT)
═══════════════════════════════════════════════════════════════

This document contains handwritten Arabic text. Read the image directly and
extract the following target fields:
    {fields_text}

Rules:
- Read text directly from the image — do NOT rely on any OCR transcription.
- For Arabic handwriting, read carefully — characters may be joined or unclear.
- Extract key-value evidence and return it in key_value_pairs.
- For each extracted pair, set canonical_field to ONE exact field name from the
  target list above when the pair maps to a target field.
- If a key-value pair does not map to a target field, set canonical_field to "".
- Do NOT invent canonical field names beyond the target list.
- Keep source keys in their original language/text in key.
- Dates should be ISO-8601 (YYYY-MM-DD) when possible.
- Confidence should reflect your certainty reading the handwriting (0.0-1.0).
  Lower confidence for unclear strokes.
- Do NOT invent or fabricate values. If you cannot read a field, omit it or
  set confidence to 0.0.
- If you can partially read a value, include what you can read and set
  confidence proportionally.

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

Respond with a SINGLE JSON object (no markdown, no extra text):

{{{{
  "tables_extracted": [],
  "key_value_pairs": [
    {{{{
      "key": "رقم الشهادة",
      "value": "ABC-123",
      "confidence": 0.85,
      "canonical_field": "certificate_number"
    }}}}
  ],
  "line_items": [],
  "signature_detected": false,
  "language": "ar"
}}}}

IMPORTANT:
- Return ONLY the JSON object, no surrounding text or markdown fences.
- Confidence should be between 0.0 and 1.0.
- Use empty lists [] for list fields with no data.
- signature_detected: set to true ONLY if you can visually see an actual
  handwritten signature, ink stamp, rubber stamp, embossed seal, or official
  certification mark in the document image. Text labels like "Authorized
  Signatory:" or mentions of "stamp" do NOT count — there must be a visible
  ink/stamp FIGURE or handwritten mark present on the document.
"""


def _build_hybrid_extraction_prompt(doc_type: str, fields: list[str]) -> str:
    """Build system prompt for hybrid OCR+vision extraction.

    Changed from PAFN: ``fields`` is now an explicit parameter.
    """
    fields_text = ", ".join(fields)
    display_name = doc_type.replace("_", " ")

    return f"""You are a bilingual (Arabic / English) document analysis expert specialized \
in reading documents that contain BOTH printed and handwritten text.

You extract structured metadata from customs, trade, and food-safety documents
used by Kuwait Customs / PAFN (Public Authority for Food and Nutrition).

The document type is already known: **{display_name}**

═══════════════════════════════════════════════════════════════
TASK: HYBRID FIELD EXTRACTION (PRINTED + HANDWRITTEN)
═══════════════════════════════════════════════════════════════

You are given TWO sources of information:
1. **OCR text** — extracted by an OCR engine. Printed/typed text is
   usually accurate here. Handwritten portions may be missing, garbled, or wrong.
2. **The original document image** — use this to read handwritten fields and
   verify/correct the OCR where it seems wrong.

STRATEGY (CRITICAL — follow this order):
- **Step 1: Parse the OCR structure first.** Arabic government documents use
  numbered field labels (e.g. ١ - المصدر, ٢ - المنتج, ٣ - المستورد).
  Use these numbers and labels to identify WHICH value belongs to WHICH field.
  The OCR text usually gets the STRUCTURE right even when individual
  characters are garbled.
- **Step 2: For each numbered field**, read the value from the OCR text.
  If the OCR value looks clean and complete, use it (high confidence).
- **Step 3: Only consult the image** to fill in values the OCR missed,
  or to correct specific characters where the OCR is clearly garbled.
- **Step 4: If OCR and image disagree on a specific value**, prefer the OCR
  when the OCR text is structurally intact (e.g. appears inside a table cell
  or next to a clear label). Prefer the image only when the OCR text is
  clearly garbled (random characters, missing text).

IMPORTANT — ARABIC DOCUMENT STRUCTURE:
Arabic government/trade documents typically use numbered field labels
(e.g. ١ - LABEL, ٢ - LABEL, etc.). The field labels are in Arabic and
the values may be handwritten in Arabic.

To correctly assign values to canonical fields:
- Read the Arabic label text next to each number in the OCR.
- Use the MEANING of the Arabic label to decide which target field it
  corresponds to. For example, a label meaning "exporter" maps to the
  exporter field, a label meaning "importer" maps to the importer field.
- Do NOT rely on field position/order alone — always use the label text.
- Pay special attention to fields that sound similar (e.g. exporter vs
  importer, producer vs goods description). Read the Arabic label carefully.
- If the OCR shows a value next to a specific numbered label, trust that
  structural association over visual proximity in the image.

Target fields for this document type:
    {fields_text}

Rules:
- Extract key-value evidence and return it in key_value_pairs.
- For each pair, set canonical_field to ONE exact field name from the target
  list above when it maps to a target field.
- If a key-value pair does not map to a target field, set canonical_field to "".
- Do NOT invent canonical field names beyond the target list.
- Keep source keys in their original language/text in key.
- Keep Arabic values in Arabic. Do NOT translate Arabic text to English.
- Dates should be ISO-8601 (YYYY-MM-DD) when possible. Arabic dates are
  usually YYYY/MM/DD — convert slashes to dashes but preserve month/day order.
- For Arabic numerals (٠-٩), convert to Western digits (0-9) in values.
  The Arabic decimal mark (٫) is a decimal point, NOT a comma.
- Confidence should reflect your certainty:
    - 0.9+ for clearly printed text confirmed by OCR
    - 0.7-0.9 for legible handwriting
    - 0.4-0.7 for partially unclear handwriting
    - Below 0.4 for guesses (prefer omitting instead)
- Do NOT fabricate values. If you cannot read a field from either source,
  omit it or set confidence to 0.0.

═══════════════════════════════════════════════════════════════
OUTPUT FORMAT
═══════════════════════════════════════════════════════════════

Respond with a SINGLE JSON object (no markdown, no extra text):

{{{{
  "tables_extracted": [],
  "key_value_pairs": [
    {{{{
      "key": "Certificate No.",
      "value": "ABC-123",
      "confidence": 0.95,
      "canonical_field": "certificate_number"
    }}}}
  ],
  "line_items": [],
  "signature_detected": false,
  "language": "ar+en"
}}}}

IMPORTANT:
- Return ONLY the JSON object.
- Confidence between 0.0 and 1.0.
- Use empty lists [] for list fields with no data.
- signature_detected: set to true ONLY if you can visually see an actual
  handwritten signature, ink stamp, rubber stamp, embossed seal, or official
  certification mark in the document image. Text labels like "Authorized
  Signatory:" or mentions of "stamp" do NOT count — there must be a visible
  ink/stamp FIGURE or handwritten mark present on the document.
"""


# ---------------------------------------------------------------------------
# Multi-page image block builder (ported unchanged)
# ---------------------------------------------------------------------------

def _build_image_blocks(pages: list[bytes], file_name: str) -> list[dict]:
    """Build vision-API image_url content blocks (ported unchanged)."""
    blocks: list[dict] = []
    for page_bytes in pages:
        b64 = base64.b64encode(page_bytes).decode("utf-8")
        media_type = _detect_media_type(file_name) if len(pages) == 1 else "image/png"
        blocks.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{b64}",
                    "detail": "high",
                },
            }
        )
    return blocks


# ---------------------------------------------------------------------------
# Pure vision extraction (ported; fields parameter added)
# ---------------------------------------------------------------------------

def extract_metadata_vision(
    openai_client: AzureOpenAI | AIClient,
    doc_input: DocumentInput,
    image_data: bytes | list[bytes],
    doc_type: str,
    fields: list[str],
    *,
    loader: TemplateLoader | None = None,
    deployment: str = "gpt-5.4",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[ExtractedMetadata, str]:
    """Extract structured metadata from a document image using GPT-5.4 vision.

    Changed from PAFN: ``fields`` is now an explicit parameter (sourced from
    ``TemplateLoader``) instead of being fetched from
    ``document_type_fields.json``.  All algorithm logic is identical.
    """
    loader = loader or TemplateLoader.for_template("food-safety")
    system_prompt = loader.get_prompt(
        "vision_extraction",
        document_type=doc_type.replace("_", " "),
        fields=", ".join(fields),
    )
    pages = image_data if isinstance(image_data, list) else [image_data]
    image_blocks = _build_image_blocks(pages, doc_input.file_name)

    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"Extract all fields from this handwritten Arabic document.\n"
                f"File: {doc_input.file_name}\n"
                f"Document type: {doc_type.replace('_', ' ')}\n"
                f"Category folder: {doc_input.source_category_folder}\n"
                f"Pages: {len(pages)}"
            ),
        },
        *image_blocks,
    ]

    for attempt in range(max_retries):
        try:
            result = as_ai_client(openai_client).complete_sync(
                model=deployment,
                activity="vision_extraction",
                case_id=case_id,
                tenant_id=tenant_id,
                max_completion_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            raw = result.content.strip()
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning(
                    "No JSON in vision LLM response for %s: %s",
                    doc_input.file_name, raw[:200],
                )
                data = {}

            data = _normalize_response(data)
            metadata = ExtractedMetadata(**data)
            logger.info(
                "Vision extraction done | file=%s | docType=%s | kvPairs=%d",
                doc_input.file_name, doc_type, len(metadata.key_value_pairs),
            )
            return metadata, raw

        except json.JSONDecodeError as exc:
            logger.warning(
                "Vision extraction JSON error for %s (attempt %d/%d): %s",
                doc_input.file_name, attempt + 1, max_retries, exc,
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) in (401, 403):
                raise RuntimeError(
                    f"OpenAI auth failure (HTTP {exc.status_code}) — check Managed Identity "
                    f"role assignment on the OpenAI resource. Original error: {exc}"
                ) from exc
            logger.warning(
                "Vision extraction failed for %s (attempt %d/%d): %s",
                doc_input.file_name, attempt + 1, max_retries, exc,
            )
            time.sleep(retry_delay_sec * (attempt + 1))

    logger.error(
        "Vision extraction: all retries failed for %s (doc_type=%s)",
        doc_input.file_name, doc_type,
    )
    return ExtractedMetadata(language="ar"), "{}"


# ---------------------------------------------------------------------------
# Hybrid extraction (ported; fields parameter added)
# ---------------------------------------------------------------------------

def extract_metadata_hybrid(
    openai_client: AzureOpenAI | AIClient,
    doc_input: DocumentInput,
    image_data: bytes | list[bytes],
    ocr_markdown: str,
    doc_type: str,
    fields: list[str],
    *,
    loader: TemplateLoader | None = None,
    deployment: str = "gpt-5.4",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[ExtractedMetadata, str]:
    """Hybrid extraction: partial OCR text + image sent together to the LLM.

    Changed from PAFN: ``fields`` is now an explicit parameter.
    All algorithm logic is identical.
    """
    loader = loader or TemplateLoader.for_template("food-safety")
    system_prompt = loader.get_prompt(
        "hybrid_extraction",
        document_type=doc_type.replace("_", " "),
        fields=", ".join(fields),
    )
    pages = image_data if isinstance(image_data, list) else [image_data]
    image_blocks = _build_image_blocks(pages, doc_input.file_name)
    truncated_ocr = ocr_markdown[:6000]

    user_content: list[dict] = [
        {
            "type": "text",
            "text": (
                f"File: {doc_input.file_name}\n"
                f"Document type: {doc_type.replace('_', ' ')}\n"
                f"Category folder: {doc_input.source_category_folder}\n"
                f"Pages: {len(pages)}\n\n"
                f"--- PARTIAL OCR TEXT (printed portions) ---\n"
                f"{truncated_ocr}\n\n"
                f"--- END OCR TEXT ---\n\n"
                f"The OCR above may be incomplete — handwritten portions are likely "
                f"missing or garbled. Use the image(s) below to read handwritten fields "
                f"and verify/correct the OCR output."
            ),
        },
        *image_blocks,
    ]

    for attempt in range(max_retries):
        try:
            result = as_ai_client(openai_client).complete_sync(
                model=deployment,
                activity="hybrid_extraction",
                case_id=case_id,
                tenant_id=tenant_id,
                max_completion_tokens=4096,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
            )
            raw = result.content.strip()
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning(
                    "No JSON in hybrid LLM response for %s: %s",
                    doc_input.file_name, raw[:200],
                )
                data = {}

            data = _normalize_response(data)
            metadata = ExtractedMetadata(**data)
            logger.info(
                "Hybrid extraction done | file=%s | docType=%s | kvPairs=%d",
                doc_input.file_name, doc_type, len(metadata.key_value_pairs),
            )
            return metadata, raw

        except json.JSONDecodeError as exc:
            logger.warning(
                "Hybrid extraction JSON error for %s (attempt %d/%d): %s",
                doc_input.file_name, attempt + 1, max_retries, exc,
            )
        except Exception as exc:
            if getattr(exc, "status_code", None) in (401, 403):
                raise RuntimeError(
                    f"OpenAI auth failure (HTTP {exc.status_code}) — check Managed Identity "
                    f"role assignment on the OpenAI resource. Original error: {exc}"
                ) from exc
            logger.warning(
                "Hybrid extraction failed for %s (attempt %d/%d): %s",
                doc_input.file_name, attempt + 1, max_retries, exc,
            )
            time.sleep(retry_delay_sec * (attempt + 1))

    logger.error(
        "Hybrid extraction: all retries failed for %s (doc_type=%s)",
        doc_input.file_name, doc_type,
    )
    return ExtractedMetadata(language="ar"), "{}"


# ---------------------------------------------------------------------------
# Ensemble merge helper (ported unchanged)
# ---------------------------------------------------------------------------

def _merge_metadata(
    vision_meta: ExtractedMetadata,
    hybrid_meta: ExtractedMetadata,
) -> ExtractedMetadata:
    """Merge two extraction results, keeping highest-confidence value per field."""
    best_by_field: dict[str, KVPair] = {}
    extra_pairs: list[KVPair] = []

    for kv in list(vision_meta.key_value_pairs) + list(hybrid_meta.key_value_pairs):
        cf = kv.canonical_field.strip()
        if cf:
            existing = best_by_field.get(cf)
            if existing is None or kv.confidence > existing.confidence:
                best_by_field[cf] = kv
        else:
            extra_pairs.append(kv)

    seen: set[tuple[str, str]] = set()
    deduped_extras: list[KVPair] = []
    for kv in extra_pairs:
        sig = (kv.key.strip(), kv.value.strip())
        if sig not in seen:
            seen.add(sig)
            deduped_extras.append(kv)

    merged_kv = list(best_by_field.values()) + deduped_extras
    tables = (
        vision_meta.tables_extracted
        if len(vision_meta.tables_extracted) >= len(hybrid_meta.tables_extracted)
        else hybrid_meta.tables_extracted
    )
    line_items = (
        vision_meta.line_items
        if len(vision_meta.line_items) >= len(hybrid_meta.line_items)
        else hybrid_meta.line_items
    )
    return ExtractedMetadata(
        tables_extracted=tables,
        key_value_pairs=merged_kv,
        line_items=line_items,
        signature_detected=(vision_meta.signature_detected or hybrid_meta.signature_detected),
        language=vision_meta.language or hybrid_meta.language or "ar",
    )


# ---------------------------------------------------------------------------
# Ensemble extraction (ported; fields parameter added)
# ---------------------------------------------------------------------------

def extract_metadata_ensemble(
    openai_client: AzureOpenAI | AIClient,
    doc_input: DocumentInput,
    image_data: bytes | list[bytes],
    ocr_markdown: str,
    doc_type: str,
    fields: list[str],
    *,
    loader: TemplateLoader | None = None,
    deployment: str = "gpt-5.4",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
    confidence_threshold: float = 0.6,
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[ExtractedMetadata, str]:
    """Dual-pass ensemble extraction for difficult handwritten Arabic documents.

    Changed from PAFN: ``fields`` is now an explicit parameter.
    All algorithm logic is identical.
    """
    vision_meta, _ = extract_metadata_vision(
        openai_client, doc_input, image_data, doc_type, fields,
        loader=loader,
        deployment=deployment,
        max_retries=max_retries,
        retry_delay_sec=retry_delay_sec,
        case_id=case_id,
        tenant_id=tenant_id,
    )

    confs = [kv.confidence for kv in vision_meta.key_value_pairs if kv.confidence > 0]
    avg_conf = sum(confs) / len(confs) if confs else 0.0

    if avg_conf >= confidence_threshold and len(confs) > 0:
        logger.info(
            "Ensemble: vision-only sufficient | file=%s | avgConf=%.2f",
            doc_input.file_name, avg_conf,
        )
        return vision_meta, f"ensemble:vision-only(avgConf={avg_conf:.2f})"

    logger.info(
        "Ensemble: vision avgConf=%.2f < %.2f — running hybrid pass | file=%s",
        avg_conf, confidence_threshold, doc_input.file_name,
    )
    hybrid_meta, _ = extract_metadata_hybrid(
        openai_client, doc_input, image_data, ocr_markdown, doc_type, fields,
        loader=loader,
        deployment=deployment,
        max_retries=max_retries,
        retry_delay_sec=retry_delay_sec,
        case_id=case_id,
        tenant_id=tenant_id,
    )

    merged = _merge_metadata(vision_meta, hybrid_meta)
    merged_confs = [kv.confidence for kv in merged.key_value_pairs if kv.confidence > 0]
    merged_avg = sum(merged_confs) / len(merged_confs) if merged_confs else 0.0

    logger.info(
        "Ensemble: merged | file=%s | visionKV=%d | hybridKV=%d | mergedKV=%d | mergedAvgConf=%.2f",
        doc_input.file_name,
        len(vision_meta.key_value_pairs),
        len(hybrid_meta.key_value_pairs),
        len(merged.key_value_pairs),
        merged_avg,
    )
    return merged, f"ensemble:merged(visionAvg={avg_conf:.2f},mergedAvg={merged_avg:.2f})"


# ---------------------------------------------------------------------------
# OCR cross-validation (ported; allowed_fields parameter added)
# ---------------------------------------------------------------------------

def cross_validate_with_ocr(
    openai_client: AzureOpenAI | AIClient,
    fields: dict,
    ocr_markdown: str,
    doc_type: str,
    allowed_fields: list[str],
    *,
    loader: TemplateLoader | None = None,
    deployment: str = "gpt-5.4",
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[dict, list[str]]:
    """Cross-validate vision/hybrid extraction against OCR markdown.

    Changed from PAFN: ``allowed_fields`` is now an explicit parameter
    (sourced from ``TemplateLoader``) instead of being fetched via
    ``get_fields_for_doc_type(doc_type)``.  All algorithm logic is identical.
    """
    if not ocr_markdown or not fields:
        return fields, []

    fields_summary: dict[str, str | None] = {}
    for fname in allowed_fields:
        fval = fields.get(fname)
        if fval is not None:
            fields_summary[fname] = fval.get("value")
        else:
            fields_summary[fname] = None

    truncated_ocr = ocr_markdown[:5000]

    loader = loader or TemplateLoader.for_template("food-safety")
    system_prompt = loader.get_prompt("ocr_cross_validation")

    user_msg = (
        f"Document type: {doc_type.replace('_', ' ')}\n\n"
        f"EXTRACTED FIELDS:\n{json.dumps(fields_summary, ensure_ascii=False, indent=2)}\n\n"
        f"RAW OCR TEXT:\n{truncated_ocr}"
    )

    corrections: list[str] = []
    try:
        completion = as_ai_client(openai_client).complete_sync(
            model=deployment,
            activity="ocr_cross_validation",
            case_id=case_id,
            tenant_id=tenant_id,
            max_completion_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = completion.content.strip()
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            logger.warning("Cross-validation: no JSON in LLM response")
            return fields, []

        result = json.loads(json_match.group())
        correction_map = result.get("corrections", {})
        allowed_set = set(allowed_fields)

        for fname, correction in correction_map.items():
            if fname not in allowed_set:
                continue
            if not isinstance(correction, dict) or "value" not in correction:
                continue
            new_value = correction["value"]
            reason = correction.get("reason", "")
            current = fields.get(fname)
            current_value = current.get("value") if current else None
            if new_value and new_value != current_value:
                fields[fname] = {
                    "value": new_value,
                    "confidence": 0.88,
                    "ocr_validated": True,
                }
                action = "filled null" if current_value is None else "corrected"
                corrections.append(f"{fname}: {action} → {reason}")

    except Exception as exc:  # noqa: BLE001 - optional LLM validation must not abort extraction
        logger.warning("Cross-validation LLM call failed: %s", exc)
        return fields, []

    if corrections:
        logger.info(
            "OCR cross-validation applied %d corrections | docType=%s",
            len(corrections), doc_type,
        )

    return fields, corrections
