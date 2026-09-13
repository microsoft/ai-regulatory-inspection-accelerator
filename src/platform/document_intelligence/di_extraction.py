"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — DI Extraction Activity

Four-step document processing pipeline:

  Step 0 – Image Quality Check (LLM Vision)
  Step 1 – Azure Document Intelligence (OCR + Layout → Markdown)
    Step 2 – LLM Metadata Extraction (economical text deployment)
  Step 3 – LLM Field Normalization + Rule-Based Normalization

Design notes:
  - DI model selection and document-type resolution come from
    ``TemplateLoader`` rather than hardcoded maps.
  - Metadata extraction prompts are built by the generic
    ``_build_metadata_extraction_prompt()`` helper from a ``TemplateLoader``.
  - Azure service clients (DI, OpenAI, Blob) are passed as parameters
    rather than being constructed internally so the function is testable
    without Azure credentials.
  - Persistence, PII redaction, and telemetry are the caller's concern. The
    caller receives a pure extraction result and is responsible for storing it.
  - ``allowed_fields`` and ``line_item_fields`` are passed explicitly to
    ``canonicalize_fields_for_doc_type``, ``normalize_all_fields``, and
    ``cross_validate_with_ocr`` so those functions read no config files.
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timezone

from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import (
    AnalyzeDocumentRequest,
    DocumentAnalysisFeature,
    DocumentContentFormat,
)
from azure.storage.blob.aio import BlobServiceClient
from openai import AzureOpenAI

from src.platform.document_intelligence.content_normalization import (
    ContentNormalizationOptions,
    normalize_markdown,
)
from src.platform.document_intelligence.di_normalization import (
    canonicalize_fields_for_doc_type,
    normalize_all_fields,
)
from src.platform.document_intelligence.quality_assessment import check_image_quality
from src.platform.document_intelligence.schemas import (
    DocumentInput,
    DocumentIntelligenceResult,
    ExtractedMetadata,
    KVPair,
    LineItem,
    TableData,
)
from src.platform.document_intelligence.vision_extraction import (
    cross_validate_with_ocr,
    extract_metadata_hybrid,
    extract_metadata_vision,
)
from src.platform.shared.ai_client import AIClient, as_ai_client
from src.platform.templates.template_loader import TemplateLoader

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (read from environment)
# ---------------------------------------------------------------------------

RAW_UPLOADS_CONTAINER = os.environ.get("RAW_UPLOADS_CONTAINER", "raw-uploads")
DI_CONFIDENCE_THRESHOLD = float(os.environ.get("DI_CONFIDENCE_THRESHOLD", "0.85"))
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "aria-text-mini")
AZURE_OPENAI_VISION_DEPLOYMENT = os.environ.get("AZURE_OPENAI_VISION_DEPLOYMENT", "aria-vision")

MAX_RETRIES = 3
RETRY_DELAY_SEC = 2
DI_EXTRACTION_CONCURRENCY = int(os.environ.get("DI_EXTRACTION_CONCURRENCY", "3"))

_SIGNATURE_KEYWORDS = (
    "signature", "signed", "authorized", "stamp",
    "توقيع", "ختم", "موقع",
)

_ARABIC_RUN_RE = re.compile(
    r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+'
    r'(?:\s+[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+)*'
)
_RTL_MARK = '\u200F'


# ---------------------------------------------------------------------------
# BiDi post-processing
# ---------------------------------------------------------------------------

def _add_bidi_marks(text: str) -> str:
    """Insert RTL marks around Arabic runs in mixed-script text."""
    if not text:
        return text
    return _ARABIC_RUN_RE.sub(lambda m: f'{_RTL_MARK}{m.group()}{_RTL_MARK}', text)


def _detect_languages_from_text(text: str) -> list[str]:
    """Heuristic language detection based on Unicode script analysis."""
    import unicodedata
    sample = text[:10_000]
    arabic_count = 0
    latin_count = 0
    for ch in sample:
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch, "")
        except ValueError:
            continue
        if name.startswith("ARABIC"):
            arabic_count += 1
        elif name.startswith("LATIN"):
            latin_count += 1

    detected: list[str] = []
    total = arabic_count + latin_count
    if total == 0:
        return detected
    if arabic_count / total > 0.05:
        detected.append("ar")
    if latin_count / total > 0.05:
        detected.append("en")
    if len(detected) == 2 and arabic_count > latin_count:
        detected = ["ar", "en"]
    elif len(detected) == 2:
        detected = ["en", "ar"]
    return detected


# ---------------------------------------------------------------------------
# Prompt building (uses TemplateLoader instead of document_type_fields.json)
# ---------------------------------------------------------------------------

def _build_metadata_extraction_prompt(doc_type: str, loader: TemplateLoader) -> str:
    """Build the system prompt from the active template Knowledge Pack."""
    fields = loader.get_fields(doc_type)
    fields_text = ", ".join(fields)
    display_name = doc_type.replace("_", " ")
    line_item_fields = loader.get_line_item_fields(doc_type)
    doc_notes = loader.get_doc_notes(doc_type)
    return loader.get_prompt(
        "metadata_extraction",
        document_type=display_name,
        fields=fields_text,
        document_notes=f"Document notes: {doc_notes}" if doc_notes else "",
        line_item_guidance=(
            f"LINE ITEM EXTRACTION fields: {', '.join(line_item_fields)}."
            if line_item_fields
            else ""
        ),
    )


def _build_user_message(filename: str, parent_folder: str, markdown_content: str) -> str:
    """Build the user-turn message for the LLM extraction call."""
    return (
        f"File: {filename}\n"
        f"Document category: {parent_folder}\n\n"
        f"Document content (OCR Markdown):\n\n{markdown_content}"
    )


# ---------------------------------------------------------------------------
# Step 1: Document Intelligence
# ---------------------------------------------------------------------------

async def run_document_intelligence(
    di_client: DocumentIntelligenceClient,
    blob_data: bytes,
    doc_type: str,
    file_name: str,
    loader: TemplateLoader,
) -> DocumentIntelligenceResult:
    """Analyse a single document with Azure Document Intelligence.

    The DI model is resolved per document type via ``loader.get_di_model()``.
    """
    model_id = loader.get_di_model(doc_type)

    try:
        poller = await di_client.begin_analyze_document(
            model_id=model_id,
            body=AnalyzeDocumentRequest(bytes_source=blob_data),
            output_content_format=DocumentContentFormat.MARKDOWN,
            features=[DocumentAnalysisFeature.LANGUAGES],
            locale="ar",
        )
        result = await poller.result()
    except Exception as exc:
        if getattr(exc, 'status_code', None) in (401, 403):
            raise RuntimeError(
                f"Document Intelligence auth failure (HTTP {exc.status_code}) — check "
                f"Managed Identity role assignment. Original error: {exc}"
            ) from exc
        logger.error("Document Intelligence failed for %s: %s", file_name, exc)
        return DocumentIntelligenceResult()

    normalization_config = loader.get_normalization_config(doc_type)
    markdown_content, content_report = normalize_markdown(
        result.content or "",
        ContentNormalizationOptions.from_dict(normalization_config.get("content")),
    )
    markdown_content = _add_bidi_marks(markdown_content)
    page_count = len(result.pages) if result.pages else 0

    languages: list[str] = []
    if result.languages:
        languages = [lang.locale for lang in result.languages if lang.locale]
    if not languages and markdown_content:
        languages = _detect_languages_from_text(markdown_content)

    has_handwriting = False
    if result.styles:
        for style in result.styles:
            if getattr(style, "is_handwritten", False):
                has_handwriting = True
                break

    lower_text = markdown_content.lower()
    has_signatures = any(kw in lower_text for kw in _SIGNATURE_KEYWORDS)

    word_confidences: list[float] = []
    if result.pages:
        for page in result.pages:
            if page.words:
                word_confidences.extend(
                    w.confidence for w in page.words if w.confidence is not None
                )
    ocr_confidence = (
        sum(word_confidences) / len(word_confidences) if word_confidences else 0.0
    )

    logger.info(
        "DI analysis finished | file=%s | model=%s | pages=%d | chars=%d | "
        "tokenReduction=%.1f%% | ocrConf=%.4f | languages=%s | handwriting=%s | signatures=%s",
        file_name, model_id, page_count, len(markdown_content),
        content_report.token_reduction_ratio * 100,
        ocr_confidence, languages, has_handwriting, has_signatures,
    )

    return DocumentIntelligenceResult(
        markdown_content=markdown_content,
        page_count=page_count,
        languages_detected=languages,
        has_handwriting=has_handwriting,
        has_signatures=has_signatures,
        ocr_confidence=round(ocr_confidence, 4),
    )


# ---------------------------------------------------------------------------
# Step 2: LLM metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata_llm(
    doc_input: DocumentInput,
    di_result: DocumentIntelligenceResult,
    openai_client: AzureOpenAI | AIClient,
    doc_type: str,
    loader: TemplateLoader,
    *,
    case_id: str = "unattributed",
    tenant_id: str = "unattributed",
) -> tuple[ExtractedMetadata, str]:
    """Extract structured metadata using the configured text deployment.

    The prompt is built via ``_build_metadata_extraction_prompt``, which
    sources document-type fields from the ``TemplateLoader``.
    """
    system_prompt = _build_metadata_extraction_prompt(doc_type, loader)
    user_message = _build_user_message(
        filename=doc_input.file_name,
        parent_folder=doc_input.source_category_folder,
        markdown_content=di_result.markdown_content,
    )

    for attempt in range(MAX_RETRIES):
        try:
            result = as_ai_client(openai_client).complete_sync(
                model=AZURE_OPENAI_DEPLOYMENT,
                activity="metadata_extraction",
                case_id=case_id,
                tenant_id=tenant_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
            raw = result.content.strip()

            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
            else:
                logger.warning(
                    "No JSON object in LLM response for %s: %s",
                    doc_input.file_name, raw[:200],
                )
                continue

            normalized_tables: list[TableData] = []
            for t in (data.get("tables_extracted") or []):
                if isinstance(t, dict):
                    cells = t.get("cells", [])
                    if not isinstance(cells, list):
                        cells = []
                    normalized_tables.append(
                        TableData(
                            page_number=int(t.get("page_number", 0) or 0),
                            row_count=int(t.get("row_count", 0) or 0),
                            column_count=int(t.get("column_count", 0) or 0),
                            cells=cells,
                        )
                    )
                elif isinstance(t, list):
                    coerced_rows: list[list[str]] = []
                    for row in t:
                        if isinstance(row, dict):
                            coerced_rows.append([f"{k}: {v}" for k, v in row.items()])
                        elif isinstance(row, list):
                            coerced_rows.append([str(c) for c in row])
                        else:
                            coerced_rows.append([str(row)])
                    normalized_tables.append(
                        TableData(
                            row_count=len(coerced_rows),
                            column_count=max((len(r) for r in coerced_rows), default=0),
                            cells=coerced_rows,
                        )
                    )
            data["tables_extracted"] = normalized_tables

            normalized_kv: list[KVPair] = []
            for kv in (data.get("key_value_pairs") or []):
                if not isinstance(kv, dict):
                    continue
                canonical_field = str(kv.get("canonical_field", "")).strip()
                raw_conf = float(kv.get("confidence", 0.0) or 0.0)
                normalized_kv.append(
                    KVPair(
                        key=str(kv.get("key", "")),
                        value=str(kv.get("value", "")),
                        confidence=max(0.0, min(1.0, raw_conf)),
                        canonical_field=canonical_field,
                    )
                )
            data["key_value_pairs"] = normalized_kv

            normalized_line_items: list[LineItem] = []
            for item in (data.get("line_items") or []):
                if not isinstance(item, dict):
                    continue
                raw_item_conf = float(item.get("confidence", 0.0) or 0.0)
                item_data = {
                    k: str(v) if v is not None else ""
                    for k, v in item.items()
                    if k != "confidence"
                }
                item_data["confidence"] = max(0.0, min(1.0, raw_item_conf))
                normalized_line_items.append(LineItem(**item_data))
            data["line_items"] = normalized_line_items

            data["signature_detected"] = bool(data.get("signature_detected", False))
            data.setdefault("language", "")

            metadata = ExtractedMetadata(**data)
            logger.info(
                "LLM extraction done | file=%s | docType=%s | kvPairs=%d | tables=%d | lineItems=%d",
                doc_input.file_name, doc_type,
                len(metadata.key_value_pairs),
                len(metadata.tables_extracted),
                len(metadata.line_items),
            )
            return metadata, raw

        except json.JSONDecodeError as exc:
            logger.warning(
                "JSON parse error for %s (attempt %d/%d): %s",
                doc_input.file_name, attempt + 1, MAX_RETRIES, exc,
            )
        except Exception as exc:
            if getattr(exc, 'status_code', None) in (401, 403):
                raise RuntimeError(
                    f"OpenAI auth failure (HTTP {exc.status_code}) — check Managed Identity "
                    f"role assignment on the OpenAI resource. Original error: {exc}"
                ) from exc
            logger.warning(
                "LLM call failed for %s (attempt %d/%d): %s",
                doc_input.file_name, attempt + 1, MAX_RETRIES, exc,
            )
            time.sleep(RETRY_DELAY_SEC * (attempt + 1))

    logger.error(
        "LLM extraction: all retries failed for %s (doc_type=%s)",
        doc_input.file_name, doc_type,
    )
    return ExtractedMetadata(), "{}"


# ---------------------------------------------------------------------------
# Handwriting preprocessing shim
# ---------------------------------------------------------------------------

def _is_pdf(file_name: str) -> bool:
    return file_name.lower().endswith(".pdf")


async def _preprocess_for_vision(blob_data: bytes, file_name: str) -> list[bytes]:
    """Rasterize PDF or lightly denoise images for the vision fallback.

    Requires ``pymupdf`` and ``opencv-python`` at runtime.  Returns empty
    list on failure; caller handles the fallback.
    """
    try:
        from src.platform.document_intelligence.handwriting_preprocessing import (
            preprocess_for_vision,
        )
        return await asyncio.to_thread(preprocess_for_vision, blob_data, file_name)
    except ImportError:
        logger.warning(
            "handwriting_preprocessing not available — skipping pre-processing | file=%s",
            file_name,
        )
        return []


# ---------------------------------------------------------------------------
# Main activity entry point
# ---------------------------------------------------------------------------

async def run(
    payload: dict,
    *,
    di_client: DocumentIntelligenceClient,
    openai_client: AzureOpenAI | AIClient,
    blob_service: BlobServiceClient,
    loader: TemplateLoader,
    confidence_threshold: float = DI_CONFIDENCE_THRESHOLD,
    max_retries: int = MAX_RETRIES,
    retry_delay_sec: int = RETRY_DELAY_SEC,
    concurrency: int = DI_EXTRACTION_CONCURRENCY,
) -> dict:
    """
    Run the DI extraction pipeline for all documents in a submission payload.

    Args:
        payload: Submission dict containing ``requestId`` and ``documents``.
        di_client: Authenticated Azure Document Intelligence async client.
        openai_client: Azure OpenAI sync client (used in thread pool).
        blob_service: Azure Blob Storage async client.
        loader: ``TemplateLoader`` for the active industry template.
        confidence_threshold: Min confidence to accept a field value.
        max_retries: LLM retry count.
        retry_delay_sec: Base retry delay.
        concurrency: Max parallel documents.

    Returns::

        {
            "success": bool,
            "extractedFields": {
                "<documentId>": {
                    "documentType": str,
                    "fields": {"<fieldName>": {"value": any, "confidence": float}},
                    "lineItems": [...],
                    "lowConfidenceFields": [str, ...],
                    "ocrConfidence": float,
                    "detectedLanguage": str | None,
                }
            },
            "errors": [{"code": str, "severity": str, "message": str,
                        "affectedDocumentId": str}]
        }
    """
    request_id: str = payload["requestId"]
    documents: list[dict] = payload.get("documents", [])
    errors: list[dict] = []
    extracted_fields: dict = {}
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    logger.info("Starting DI extraction | requestId=%s | docCount=%d", request_id, len(documents))

    semaphore = asyncio.Semaphore(concurrency)

    async def _process_single_doc(doc: dict) -> tuple[str, dict | None, dict | None]:
        doc_id: str = doc["documentTypeId"]
        doc_type: str = loader.resolve_doc_type(doc_id, fallback=doc.get("documentType"))
        blob_path: str = doc["blobPath"]
        file_name: str = blob_path.rsplit("/", 1)[-1] if "/" in blob_path else blob_path

        # Resolve field lists from template — replaces document_type_fields.json
        allowed_fields = loader.get_fields(doc_type)
        line_item_fields = loader.get_line_item_fields(doc_type)
        normalization_config = loader.get_normalization_config(doc_type)

        async with semaphore:
            try:
                # ── Download blob ─────────────────────────────────────────────
                container_client = blob_service.get_container_client(RAW_UPLOADS_CONTAINER)
                downloader = await container_client.get_blob_client(blob_path).download_blob()
                blob_data: bytes = await downloader.readall()

                logger.info(
                    "Blob downloaded | docId=%s | size=%d bytes", doc_id, len(blob_data)
                )

                # ── Step 0: Image Quality Check ───────────────────────────────
                quality_check_result = await asyncio.to_thread(
                    check_image_quality,
                    openai_client, blob_data, file_name, loader,
                    threshold=loader.get_quality_threshold(doc_type),
                    deployment=AZURE_OPENAI_VISION_DEPLOYMENT,
                    max_retries=max_retries,
                    retry_delay_sec=retry_delay_sec,
                    case_id=request_id,
                    tenant_id=str(payload.get("tenantId", "unattributed")),
                )

                logger.info(
                    "Quality check done | docId=%s | score=%.2f | issues=%s",
                    doc_id, quality_check_result.quality_score, quality_check_result.issues,
                )

                if not quality_check_result.passed:
                    logger.warning(
                        "Quality check failed — skipping DI+LLM | docId=%s | score=%.2f",
                        doc_id, quality_check_result.quality_score,
                    )
                    _quality_entry = {
                        "runId": run_id,
                        "documentType": doc_type,
                        "fields": {},
                        "lineItems": [],
                        "lowConfidenceFields": [],
                        "ocrConfidence": 0.0,
                        "detectedLanguage": "unknown",
                        "qualityCheck": quality_check_result.to_dict(),
                        "qualityFinding": (
                            "Manual review is required — document does not meet "
                            "minimum quality standards "
                            f"(score {quality_check_result.quality_score:.2f}). "
                            f"Issues: {', '.join(quality_check_result.issues) or 'unspecified'}."
                        ),
                        "requiresHumanReview": True,
                    }
                    return (doc_id, _quality_entry, None)

                # ── Step 1: Document Intelligence (OCR + Layout) ──────────────
                di_result = await run_document_intelligence(
                    di_client, blob_data, doc_type, file_name, loader
                )

                # ── Routing: detect handwritten Arabic ───────────────────────
                is_arabic = any("ar" in lang for lang in di_result.languages_detected)
                is_handwritten = di_result.has_handwriting

                doc_input = DocumentInput(
                    file_path=blob_path,
                    file_name=file_name,
                    file_extension=file_name.rsplit(".", 1)[-1] if "." in file_name else "",
                    source_category_folder=doc_type,
                )

                if is_handwritten and is_arabic:
                    OCR_CONFIDENCE_MIXED_THRESHOLD = 0.5
                    is_mixed = di_result.ocr_confidence >= OCR_CONFIDENCE_MIXED_THRESHOLD

                    vision_pages = await _preprocess_for_vision(blob_data, file_name)

                    use_vision_path = True
                    if not vision_pages:
                        if _is_pdf(file_name):
                            logger.warning(
                                "PDF rasterization failed for handwritten Arabic doc — "
                                "falling back to OCR+LLM | docId=%s",
                                doc_id,
                            )
                            use_vision_path = False
                        else:
                            vision_pages = [blob_data]

                    if use_vision_path:
                        vision_input: bytes | list[bytes] = (
                            vision_pages[0] if len(vision_pages) == 1 else vision_pages
                        )
                        if is_mixed:
                            logger.info(
                                "Mixed Arabic — hybrid extraction | docId=%s", doc_id
                            )
                            metadata, _llm_raw = await asyncio.to_thread(
                                extract_metadata_hybrid,
                                openai_client, doc_input, vision_input,
                                di_result.markdown_content, doc_type,
                                allowed_fields,
                                loader=loader,
                                deployment=AZURE_OPENAI_VISION_DEPLOYMENT,
                                max_retries=max_retries,
                                retry_delay_sec=retry_delay_sec,
                                case_id=request_id,
                                tenant_id=str(payload.get("tenantId", "unattributed")),
                            )
                        else:
                            logger.info(
                                "Handwritten Arabic — vision extraction | docId=%s", doc_id
                            )
                            metadata, _llm_raw = await asyncio.to_thread(
                                extract_metadata_vision,
                                openai_client, doc_input, vision_input, doc_type,
                                allowed_fields,
                                loader=loader,
                                deployment=AZURE_OPENAI_VISION_DEPLOYMENT,
                                max_retries=max_retries,
                                retry_delay_sec=retry_delay_sec,
                                case_id=request_id,
                                tenant_id=str(payload.get("tenantId", "unattributed")),
                            )
                    else:
                        if not di_result.markdown_content:
                            logger.warning(
                                "DI returned empty content and PDF rasterization failed — "
                                "storing null fields | docId=%s", doc_id,
                            )
                            metadata, _llm_raw = ExtractedMetadata(), "{}"
                        else:
                            metadata, _llm_raw = await asyncio.to_thread(
                                extract_metadata_llm,
                                doc_input, di_result, openai_client, doc_type, loader,
                                case_id=request_id,
                                tenant_id=str(payload.get("tenantId", "unattributed")),
                            )
                else:
                    if not di_result.markdown_content:
                        logger.warning(
                            "DI returned empty content — storing null fields | docId=%s", doc_id,
                        )
                        metadata, _llm_raw = ExtractedMetadata(), "{}"
                    else:
                        metadata, _llm_raw = await asyncio.to_thread(
                            extract_metadata_llm,
                            doc_input, di_result, openai_client, doc_type, loader,
                            case_id=request_id,
                            tenant_id=str(payload.get("tenantId", "unattributed")),
                        )

                # ── Canonicalize fields (template-driven, not file-driven) ────
                fields, line_items = canonicalize_fields_for_doc_type(
                    metadata, doc_type, openai_client,
                    loader=loader,
                    allowed_fields=allowed_fields,
                    line_item_fields=line_item_fields,
                    normalization_config=normalization_config,
                    deployment=AZURE_OPENAI_DEPLOYMENT,
                    case_id=request_id,
                    tenant_id=str(payload.get("tenantId", "unattributed")),
                )

                # ── OCR cross-validation (handwritten Arabic only) ────────────
                ocr_xval_log: list[str] = []
                if is_handwritten and is_arabic and di_result.markdown_content:
                    fields, ocr_xval_log = await asyncio.to_thread(
                        cross_validate_with_ocr,
                        openai_client, fields, di_result.markdown_content, doc_type,
                        allowed_fields,
                        loader=loader,
                        deployment=AZURE_OPENAI_DEPLOYMENT,
                        case_id=request_id,
                        tenant_id=str(payload.get("tenantId", "unattributed")),
                    )

                # ── Step 3: LLM + Rule-Based Normalization ────────────────────
                fields, line_items, normalization_log = await asyncio.to_thread(
                    normalize_all_fields,
                    openai_client, fields, line_items, doc_type, file_name,
                    loader=loader,
                    allowed_fields=allowed_fields,
                    normalization_config=normalization_config,
                    deployment=AZURE_OPENAI_DEPLOYMENT,
                    max_retries=max_retries,
                    retry_delay_sec=retry_delay_sec,
                    case_id=request_id,
                    tenant_id=str(payload.get("tenantId", "unattributed")),
                )

                # ── Metrics ───────────────────────────────────────────────────
                low_confidence = [
                    name for name, fv in fields.items()
                    if fv.get("confidence", 0) < confidence_threshold
                ]
                confidence_values = [
                    fv.get("confidence", 0) for fv in fields.values()
                    if fv.get("value") is not None
                ]
                for item in line_items:
                    confidence_values.extend(
                        fv.get("confidence", 0) for fv in item.values()
                        if fv.get("value") is not None
                    )
                avg_confidence = (
                    round(sum(confidence_values) / len(confidence_values), 4)
                    if confidence_values else 0.0
                )

                detected_language = metadata.language or (
                    ", ".join(di_result.languages_detected)
                    if di_result.languages_detected else None
                )

                # Propagate LLM-based signature detection into fields
                sig_llm = getattr(metadata, "signature_detected", False)
                fields["signature_detected"] = {
                    "value": bool(sig_llm),
                    "confidence": 0.9 if sig_llm else 0.0,
                }

                result_entry = {
                    "runId": run_id,
                    "documentType": doc_type,
                    "fields": fields,
                    "lineItems": line_items,
                    "lowConfidenceFields": low_confidence,
                    "ocrConfidence": avg_confidence,
                    "qualityCheck": quality_check_result.to_dict(),
                    "detectedLanguage": detected_language,
                    "normalization": normalization_log,
                    "ocrCrossValidation": ocr_xval_log if ocr_xval_log else None,
                }
                return (doc_id, result_entry, None)

            except Exception as exc:
                logger.exception("Unrecoverable error processing docId=%s", doc_id)
                error = {
                    "code": "OCR_EXTRACTION_FAILED",
                    "severity": "error",
                    "message": str(exc),
                    "affectedDocumentId": doc_id,
                }
                return (doc_id, None, error)

    tasks = [_process_single_doc(doc) for doc in documents]
    results = await asyncio.gather(*tasks)

    for doc_id, result_entry, error in results:
        if error:
            errors.append(error)
        if result_entry is not None:
            extracted_fields[doc_id] = result_entry

    success = len(errors) == 0
    logger.info(
        "DI extraction complete | requestId=%s | success=%s | docs=%d | errors=%d",
        request_id, success, len(extracted_fields), len(errors),
    )
    return {
        "success": success,
        "extractedFields": extracted_fields,
        "errors": errors,
    }
