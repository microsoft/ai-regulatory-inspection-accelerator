"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — Vision Extraction

Vision-based field extraction for handwritten Arabic documents.

Prompts are sourced from the active template's Knowledge Pack via
``TemplateLoader``; the platform ships no domain-specific prompt text.

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
# Shared helpers
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
    """Normalize raw LLM JSON into typed model fields."""
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
        # LineItem allows extra fields, so the template's own line-item schema passes through.
        fields = {k: v for k, v in item.items() if k != "confidence"}
        normalized_line_items.append(
            LineItem(confidence=max(0.0, min(1.0, raw_item_conf)), **fields)
        )
    data["line_items"] = normalized_line_items
    data["signature_detected"] = bool(data.get("signature_detected", False))
    data.setdefault("language", "ar")
    return data


# ---------------------------------------------------------------------------
# Multi-page image block builder
# ---------------------------------------------------------------------------

def _require_loader(loader: TemplateLoader | None) -> TemplateLoader:
    """Reject an absent loader rather than defaulting to a particular domain."""
    if loader is None:
        raise ValueError(
            "A TemplateLoader is required — prompts are sourced from the active "
            "template's Knowledge Pack, so the platform cannot pick a default."
        )
    return loader


def _build_image_blocks(pages: list[bytes], file_name: str) -> list[dict]:
    """Build vision-API image_url content blocks."""
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
# Pure vision extraction
# ---------------------------------------------------------------------------

def extract_metadata_vision(
    openai_client: AzureOpenAI | AIClient,
    doc_input: DocumentInput,
    image_data: bytes | list[bytes],
    doc_type: str,
    fields: list[str],
    *,
    loader: TemplateLoader | None = None,
    deployment: str = "aria-vision",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[ExtractedMetadata, str]:
    """Extract structured metadata from a document image using the vision fallback.

    ``fields`` is sourced from ``TemplateLoader`` by the caller.
    """
    loader = _require_loader(loader)
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
# Hybrid extraction
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
    deployment: str = "aria-vision",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[ExtractedMetadata, str]:
    """Hybrid extraction: partial OCR text + image sent together to the LLM."""
    loader = _require_loader(loader)
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
# Ensemble merge helper
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
# Ensemble extraction
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
    deployment: str = "aria-vision",
    max_retries: int = 3,
    retry_delay_sec: int = 2,
    confidence_threshold: float = 0.6,
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[ExtractedMetadata, str]:
    """Dual-pass ensemble extraction for difficult handwritten Arabic documents."""
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
# OCR cross-validation
# ---------------------------------------------------------------------------

def cross_validate_with_ocr(
    openai_client: AzureOpenAI | AIClient,
    fields: dict,
    ocr_markdown: str,
    doc_type: str,
    allowed_fields: list[str],
    *,
    loader: TemplateLoader | None = None,
    deployment: str = "aria-vision",
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[dict, list[str]]:
    """Cross-validate vision/hybrid extraction against OCR markdown.

    ``allowed_fields`` is sourced from ``TemplateLoader`` by the caller.
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

    loader = _require_loader(loader)
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
