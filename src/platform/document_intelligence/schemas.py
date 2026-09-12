"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — Schemas

Pydantic models shared across the DI extraction pipeline.

The ``LineItem`` and ``ExtractedMetadata`` models use ``extra='allow'`` so that
different document types can define their own field sets in
``evidence_types.json`` without requiring code changes to the model layer.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class KVPair(BaseModel):
    """A key-value pair extracted by Document Intelligence or an LLM."""

    key: str = ""
    value: str = ""
    confidence: float = 0.0
    canonical_field: str = ""


class TableData(BaseModel):
    """A single table extracted by Document Intelligence."""

    page_number: int = 0
    row_count: int = 0
    column_count: int = 0
    cells: list[list[str]] = Field(default_factory=list)


class LineItem(BaseModel):
    """A repeating product/goods row extracted from a document.

    ``extra='allow'`` lets each document type define its own line-item
    fields in ``evidence_types.json`` without code changes here.
    """

    model_config = ConfigDict(extra="allow")

    confidence: float = 0.0


class DocumentInput(BaseModel):
    """Metadata about a single document being processed."""

    file_path: str
    file_name: str
    file_extension: str
    file_size_bytes: int = 0
    ground_truth_category_no: str = ""
    ground_truth_category_name: str = ""
    source_category_folder: str = ""


class DocumentIntelligenceResult(BaseModel):
    """Markdown-formatted output from Azure Document Intelligence."""

    markdown_content: str = ""
    page_count: int = 0
    languages_detected: list[str] = Field(default_factory=list)
    has_handwriting: bool = False
    has_signatures: bool = False
    ocr_confidence: float = 0.0


class ExtractedMetadata(BaseModel):
    """Structured metadata produced by the LLM extraction step.

    ``extra='allow'`` is required because the set of domain-specific fields
    varies per document type and is driven by ``evidence_types.json``, not
    by the model definition.
    """

    model_config = ConfigDict(extra="allow")

    tables_extracted: list[TableData] = Field(default_factory=list)
    key_value_pairs: list[KVPair] = Field(default_factory=list)
    line_items: list[LineItem] = Field(default_factory=list)
    signature_detected: bool = False
    language: str = ""


def dump_metadata(model: ExtractedMetadata) -> dict:
    """Serialize extracted metadata while preserving legacy key ordering."""
    data = model.model_dump(exclude_none=True)
    trailing_keys = ("tables_extracted", "key_value_pairs")
    trailing = {key: data.pop(key) for key in trailing_keys if key in data}
    data.update(trailing)
    return data
