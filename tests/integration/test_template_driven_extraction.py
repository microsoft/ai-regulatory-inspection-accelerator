"""
Integration test: configuration-only document type extensibility.

Acceptance criterion: a new document type can be added and used by the
extraction pipeline by editing ``evidence_types.json`` only — no Python
changes required.

Tests:
  1. A synthetic ``Lab_Report`` type added only in a temporary template's
     ``evidence_types.json`` is correctly resolved, has its model and fields
     used, and produces extraction results with those fields.
  2. An undeclared document type produces a clear ``"Other"`` fallback rather
     than a runtime error or silently returning wrong fields.
  3. Removing a document type from the JSON causes its fields to disappear
     from the extraction output.

All Azure service calls are faked; no credentials are required.
"""

import json
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.platform.document_intelligence.di_normalization import (
    canonicalize_fields_for_doc_type,
)
from src.platform.document_intelligence.schemas import ExtractedMetadata, KVPair
from src.platform.templates.template_loader import TemplateLoader, _load_evidence_types


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_loader(tmp_path: Path, template_id: str, evidence: dict) -> TemplateLoader:
    d = tmp_path / template_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "evidence_types.json").write_text(json.dumps(evidence), encoding="utf-8")
    _load_evidence_types.cache_clear()
    return TemplateLoader(template_id, tmp_path)


def _make_metadata(kv_pairs: list[dict]) -> ExtractedMetadata:
    kvs = [
        KVPair(
            key=kv["key"],
            value=kv["value"],
            confidence=kv.get("confidence", 0.90),
            canonical_field=kv.get("canonical_field", ""),
        )
        for kv in kv_pairs
    ]
    return ExtractedMetadata(key_value_pairs=kvs)


# ---------------------------------------------------------------------------
# Test: add a new document type via JSON only
# ---------------------------------------------------------------------------

class TestAddNewDocTypeViaConfig:
    EVIDENCE = {
        "doc_type_id_mapping": {
            "100": "Lab_Report",
        },
        "document_types": [
            {
                "doc_type": "Lab_Report",
                "di_model": "prebuilt-layout",
                "fields": ["lab_id", "test_date", "result", "laboratory_name"],
                "doc_notes": "Extract lab result codes verbatim.",
            },
            {
                "doc_type": "Other",
                "fields": ["company_name", "issue_date", "goods_description"],
            },
        ],
    }

    def test_new_type_resolves_from_id(self, tmp_path):
        loader = _make_loader(tmp_path, "lab-tmpl", self.EVIDENCE)
        assert loader.resolve_doc_type("100") == "Lab_Report"

    def test_new_type_has_correct_fields(self, tmp_path):
        loader = _make_loader(tmp_path, "lab-tmpl", self.EVIDENCE)
        fields = loader.get_fields("Lab_Report")
        assert "lab_id" in fields
        assert "test_date" in fields
        assert "result" in fields

    def test_new_type_uses_configured_di_model(self, tmp_path):
        loader = _make_loader(tmp_path, "lab-tmpl", self.EVIDENCE)
        assert loader.get_di_model("Lab_Report") == "prebuilt-layout"

    def test_new_type_has_doc_notes(self, tmp_path):
        loader = _make_loader(tmp_path, "lab-tmpl", self.EVIDENCE)
        notes = loader.get_doc_notes("Lab_Report")
        assert notes is not None
        assert "Extract lab result" in notes

    def test_extraction_uses_new_type_fields(self, tmp_path):
        """Canonicalize fields against the new Lab_Report type — verifies the
        extraction pipeline picks up the JSON-only addition."""
        loader = _make_loader(tmp_path, "lab-tmpl", self.EVIDENCE)
        allowed_fields = loader.get_fields("Lab_Report")
        line_item_fields = loader.get_line_item_fields("Lab_Report")

        metadata = _make_metadata([
            {"key": "Lab ID", "value": "LAB-999", "confidence": 0.95,
             "canonical_field": "lab_id"},
            {"key": "Test Date", "value": "2025-06-01", "confidence": 0.92,
             "canonical_field": "test_date"},
            {"key": "Laboratory", "value": "Al-Amal Labs", "confidence": 0.88,
             "canonical_field": "laboratory_name"},
        ])

        fields, line_items = canonicalize_fields_for_doc_type(
            metadata, "Lab_Report",
            openai_client=None,
            allowed_fields=allowed_fields,
            line_item_fields=line_item_fields,
        )

        assert fields["lab_id"]["value"] == "LAB-999"
        assert fields["test_date"]["value"] == "2025-06-01"
        assert fields["laboratory_name"]["value"] == "Al-Amal Labs"
        # All declared fields present (result may be null)
        assert "result" in fields

    def test_extraction_only_returns_declared_fields(self, tmp_path):
        """Fields not in the new type's schema must not appear in output."""
        loader = _make_loader(tmp_path, "lab-tmpl", self.EVIDENCE)
        allowed_fields = loader.get_fields("Lab_Report")
        line_item_fields = loader.get_line_item_fields("Lab_Report")

        metadata = _make_metadata([
            {"key": "invoice_number", "value": "INV-001", "confidence": 0.99,
             "canonical_field": "invoice_number"},  # not in Lab_Report schema
        ])

        fields, _ = canonicalize_fields_for_doc_type(
            metadata, "Lab_Report",
            openai_client=None,
            allowed_fields=allowed_fields,
            line_item_fields=line_item_fields,
        )

        assert "invoice_number" not in fields
        assert set(fields.keys()) == set(allowed_fields)


# ---------------------------------------------------------------------------
# Test: undeclared type falls back to "Other"
# ---------------------------------------------------------------------------

class TestUndeclaredTypeFallback:
    EVIDENCE = {
        "document_types": [
            {
                "doc_type": "Other",
                "fields": ["company_name", "issue_date", "goods_description"],
            },
        ],
    }

    def test_unknown_doc_type_returns_other_fields(self, tmp_path):
        loader = _make_loader(tmp_path, "fallback-tmpl", self.EVIDENCE)
        fields = loader.get_fields("NonExistentDocType")
        assert fields == loader.get_fields("Other")

    def test_unknown_doc_type_gets_default_di_model(self, tmp_path):
        loader = _make_loader(tmp_path, "fallback-tmpl", self.EVIDENCE)
        assert loader.get_di_model("NonExistentDocType") == "prebuilt-layout"

    def test_canonicalization_with_fallback_uses_other_fields(self, tmp_path):
        loader = _make_loader(tmp_path, "fallback-tmpl", self.EVIDENCE)
        allowed_fields = loader.get_fields("NonExistentDocType")  # → Other fields
        line_item_fields = loader.get_line_item_fields("NonExistentDocType")

        metadata = _make_metadata([
            {"key": "Company", "value": "Acme Corp", "confidence": 0.9,
             "canonical_field": "company_name"},
        ])

        fields, _ = canonicalize_fields_for_doc_type(
            metadata, "NonExistentDocType",
            openai_client=None,
            allowed_fields=allowed_fields,
            line_item_fields=line_item_fields,
        )

        assert fields["company_name"]["value"] == "Acme Corp"
        assert set(fields.keys()) == set(loader.get_fields("Other"))


# ---------------------------------------------------------------------------
# Test: removing a doc type removes its fields from extraction
# ---------------------------------------------------------------------------

class TestRemoveDocTypeClearsFields:
    EVIDENCE_WITH = {
        "document_types": [
            {"doc_type": "Lab_Report", "fields": ["lab_id", "result"]},
            {"doc_type": "Other", "fields": ["company_name", "issue_date"]},
        ],
    }
    EVIDENCE_WITHOUT = {
        "document_types": [
            {"doc_type": "Other", "fields": ["company_name", "issue_date"]},
        ],
    }

    def test_fields_absent_after_removal(self, tmp_path):
        # With Lab_Report
        loader_with = _make_loader(tmp_path / "with", "v1", self.EVIDENCE_WITH)
        assert "lab_id" in loader_with.get_fields("Lab_Report")

        # Without Lab_Report — "Other" fields used instead
        loader_without = _make_loader(tmp_path / "without", "v2", self.EVIDENCE_WITHOUT)
        fallback_fields = loader_without.get_fields("Lab_Report")
        assert "lab_id" not in fallback_fields
        assert "company_name" in fallback_fields  # Other fallback
