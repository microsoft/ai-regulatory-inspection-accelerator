"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Intake — Pre-Validation Agent

Structural pre-validation for a submitted case, run before the DI Extraction
Agent. Verifies the submission is well-formed and internally consistent
(declared metadata matches expectations) before committing extraction/LLM
cost to it. On failure, the orchestrator (see
src/platform/orchestration/pipeline.py) short-circuits straight to the
Delivery Agent with status "PRE_VALIDATION_FAILED".

Generalized from a domain-specific intake validator:
  - Removed case-identifier parsing and the request-type classification derived
    from it (business content, not reusable platform logic). Submission
    classification is a template-specific concern; a template that needs it can
    layer its own check on top of this module's result.
  - Removed direct Azure Blob Storage / Cosmos DB SDK calls (`get_blob_client`,
    `upsert_case_status`, `persist_inbound_request`). Core Platform has no
    dependency on a specific storage backend. Storage-backed checks (blob
    existence, SHA-256 checksum recomputation, empty-blob detection, actual
    vs. declared file size) require downloading/inspecting real blob content
    and are therefore a connector/template-layer concern, not a pure
    Core Platform check — see the module docstring section below for the
    exact contract a template should use to merge those errors back in.
  - Removed the hardcoded RAW_UPLOADS_CONTAINER env var (storage location is
    a connector/deployment concern).
  - Mandatory-document-set validation is intentionally NOT performed here —
    it is the Policy Agent's job (config-driven `requiredWhen` rules), not
    pre-validation's.

Checks performed by this module (all pure / metadata-only — no I/O, no
external service dependency, fully deterministic):
  1. Document count       — declared count vs. received count
  2. Duplicate documents  — identical checksum, deduplicated (first kept,
                             remainder surfaced as non-blocking warnings)
  3. MIME type            — against a configurable allow-list
  4. Missing checksum     — checksum field presence (not recomputed)
  5. Attachment type consistency — each document's declared type must appear
                             in the submission's attachment-type list, and
                             vice versa
  6. Empty items          — items[] must be non-empty

Storage-backed checks are enabled when the caller supplies `content_resolver`.
The resolver keeps storage I/O outside this pure module while allowing the
validator to verify Blob existence, SHA-256, empty content, and declared size.
"""

import hashlib
from collections.abc import Callable

DEFAULT_ALLOWED_MIME_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/tiff",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)


def run(
    payload: dict,
    allowed_mime_types: frozenset[str] | None = None,
    content_resolver: Callable[[dict], bytes] | None = None,
) -> dict:
    """
    Run structural pre-validation on a submitted case payload.

    Args:
        payload: The submission payload. Expected shape:
            {
                "requestId": str,
                "documents": [{"documentTypeId": str, "documentType": str,
                                "checksum": str, "mimeType": str, ...}, ...],
                "attachmentTypes": [str, ...],
                "items": [...],
                "expectedDocumentCount": int (optional, defaults to
                    len(documents) if omitted),
            }
        allowed_mime_types: Optional override of the allowed MIME type
            allow-list (see DEFAULT_ALLOWED_MIME_TYPES). Templates with
            different accepted document formats should override this.
        content_resolver: Optional function that returns the stored bytes for
            a document. Enables content-backed checksum and size validation.

    Returns:
        {
            "passed": bool,
            "errors": [...],     # hard errors that block the pipeline
            "warnings": [...],   # non-blocking findings (duplicate docs)
            "documents": [...],  # deduplicated document list for downstream agents
        }
    """
    errors: list[dict] = []
    mime_allow_list = allowed_mime_types if allowed_mime_types is not None else DEFAULT_ALLOWED_MIME_TYPES

    raw_documents: list[dict] = payload.get("documents", [])
    expected_count: int = payload.get("expectedDocumentCount", len(raw_documents))
    attachment_types: list[str] = payload.get("attachmentTypes", [])
    items: list = payload.get("items", [])

    # Check 2: Duplicate deduplication (identical checksum only). Upstream
    # systems may have no control over duplicate submissions — deduplicate
    # silently, keep the first occurrence, and surface warnings rather than
    # failing the pipeline.
    dup_warnings, documents = _deduplicate_documents(raw_documents)

    # Check 1: Document count — raw received vs. declared count. Compared
    # against raw_documents (before dedup) since expectedDocumentCount
    # reflects what was submitted, including any upstream duplicates.
    if len(raw_documents) != expected_count:
        errors.append(_error(
            "DOCUMENT_COUNT_MISMATCH",
            "Document count does not match the declared number of documents.",
            f"The submission declared {expected_count} documents but {len(raw_documents)} were received. "
            "One or more uploads may have failed silently. Verify all documents were uploaded before resubmitting.",
        ))

    # Check 3: MIME type (metadata-only)
    errors.extend(_check_mime_types(documents, mime_allow_list))

    # Check 4: Missing checksum (metadata presence, not recomputed)
    errors.extend(_check_missing_checksums(documents))

    # Check 5: attachmentTypes <-> documentType consistency
    errors.extend(_check_attachment_type_consistency(documents, attachment_types))

    # Check 6: Empty items array
    if isinstance(items, list) and len(items) == 0:
        errors.append(_error(
            "EMPTY_ITEMS",
            "No items were provided in the submission. At least one item is required.",
            "The items[] array in the submission payload is empty. The pipeline requires at least one "
            "declared item to perform cross-document validation and rules evaluation. "
            "Add item data and resubmit.",
        ))

    if content_resolver is not None:
        errors.extend(_check_document_content(documents, content_resolver))

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "warnings": dup_warnings,
        "documents": documents,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _error(code: str, short_description: str, long_description: str, affected_document_id: str | None = None) -> dict:
    return {
        "code": code,
        "severity": "error",
        "shortDescription": short_description,
        "longDescription": long_description,
        "affectedDocumentId": affected_document_id,
    }


def _doc_label(doc: dict) -> str:
    doc_id = str(doc.get("documentTypeId", ""))
    doc_type = doc.get("documentType", "Document")
    return f"{doc_type.replace('_', ' ')} ({doc_id})"


def _deduplicate_documents(documents: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Deduplicate documents by checksum (identical file content only).

    Upstream systems may have no control over what a source system sends —
    duplicates are treated as an upstream data-quality issue, not a
    submission error. The first occurrence of each document is kept;
    subsequent duplicates are dropped and surfaced as warnings rather than
    blocking the pipeline.

    Returns:
        (warnings, deduplicated_documents)
    """
    warnings: list[dict] = []
    deduplicated: list[dict] = []
    seen_checksums: dict[str, str] = {}  # checksum -> doc_label of first occurrence

    for doc in documents:
        checksum = doc.get("checksum", "")
        if checksum and checksum in seen_checksums:
            warnings.append({
                "ruleCode": "DUPLICATE_CHECKSUM",
                "result": "WARN",
                "message": (
                    f"{_doc_label(doc)} has identical content to {seen_checksums[checksum]} "
                    "(same checksum). The duplicate was excluded from processing."
                ),
                "documentType": doc.get("documentType", ""),
                "affectedDocumentId": str(doc.get("documentTypeId", "")),
            })
        else:
            deduplicated.append(doc)
            if checksum:
                seen_checksums[checksum] = _doc_label(doc)

    return warnings, deduplicated


def _check_mime_types(documents: list[dict], allowed_mime_types: frozenset[str]) -> list[dict]:
    errors: list[dict] = []
    for doc in documents:
        mime_type = doc.get("mimeType", "")
        if mime_type and mime_type not in allowed_mime_types:
            errors.append(_error(
                "UNSUPPORTED_MIME_TYPE",
                f"The {_doc_label(doc)} is in an unsupported format.",
                f"The {_doc_label(doc)} was submitted with MIME type '{mime_type}', which is not in the "
                f"allowed list ({', '.join(sorted(allowed_mime_types))}). Convert the document to an "
                "accepted format and re-upload.",
                str(doc.get("documentTypeId", "")),
            ))
    return errors


def _check_missing_checksums(documents: list[dict]) -> list[dict]:
    errors: list[dict] = []
    for doc in documents:
        if not doc.get("checksum", ""):
            errors.append(_error(
                "MISSING_CHECKSUM",
                f"The {_doc_label(doc)} is missing a security checksum. Please re-upload.",
                f"No checksum was provided in the metadata for the {_doc_label(doc)}. The checksum is "
                "required to verify document integrity during transfer. Ensure the checksum is computed "
                "at upload time and included in the submission payload.",
                str(doc.get("documentTypeId", "")),
            ))
    return errors


def _check_document_content(
    documents: list[dict],
    content_resolver: Callable[[dict], bytes],
) -> list[dict]:
    errors: list[dict] = []
    for doc in documents:
        try:
            content = content_resolver(doc)
        except (FileNotFoundError, KeyError):
            errors.append(_error(
                "DOCUMENT_NOT_FOUND",
                f"The {_doc_label(doc)} could not be found in staging.",
                "The submitted document does not exist at its declared staging location.",
                str(doc.get("documentTypeId", "")),
            ))
            continue

        if not content:
            errors.append(_error(
                "EMPTY_DOCUMENT",
                f"The {_doc_label(doc)} is empty.",
                "The staged document contains zero bytes and cannot be processed.",
                str(doc.get("documentTypeId", "")),
            ))
            continue

        declared_checksum = str(doc.get("checksum", "")).lower()
        actual_checksum = hashlib.sha256(content).hexdigest()
        if declared_checksum and actual_checksum != declared_checksum:
            errors.append(_error(
                "CHECKSUM_MISMATCH",
                f"The {_doc_label(doc)} failed integrity verification.",
                "The staged document SHA-256 checksum does not match the submitted checksum.",
                str(doc.get("documentTypeId", "")),
            ))

        declared_size = doc.get("fileSizeBytes")
        if declared_size is not None and len(content) != declared_size:
            errors.append(_error(
                "FILE_SIZE_MISMATCH",
                f"The {_doc_label(doc)} size does not match its metadata.",
                f"The submission declared {declared_size} bytes but the staged document contains "
                f"{len(content)} bytes.",
                str(doc.get("documentTypeId", "")),
            ))

    return errors


def _check_attachment_type_consistency(documents: list[dict], attachment_types: list[str]) -> list[dict]:
    """
    Verify that each document's documentType appears in the attachmentTypes
    list and vice versa.
    """
    errors: list[dict] = []
    doc_types_from_docs = [doc.get("documentType", "") for doc in documents]

    for doc in documents:
        doc_type = doc.get("documentType", "")
        if doc_type and doc_type not in attachment_types:
            errors.append(_error(
                "ATTACHMENT_TYPE_MISMATCH",
                f"The {_doc_label(doc)} type is not listed in the expected attachment types.",
                f"The {_doc_label(doc)} type is not present in the submission's expected attachment "
                "types list. Either the document metadata is incorrect or the attachment types list is "
                "incomplete. Correct the mismatch and resubmit.",
                str(doc.get("documentTypeId", "")),
            ))

    for att_type in attachment_types:
        if att_type not in doc_types_from_docs:
            errors.append(_error(
                "ATTACHMENT_TYPE_MISMATCH",
                f"The expected attachment type '{att_type.replace('_', ' ')}' has no corresponding document.",
                f"The submission declared '{att_type}' as an expected attachment type, but no document "
                "with that type was received. Upload the missing document and resubmit.",
                None,
            ))

    return errors
