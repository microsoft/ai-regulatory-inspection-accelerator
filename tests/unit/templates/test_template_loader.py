"""
Unit tests for src/platform/templates/template_loader.py.

Tests cover:
  - Valid food-safety template loading
  - doc_type_id → doc_type resolution (including fallback and "Other" default)
  - DI model lookup (with and without di_model configured)
  - Field list, line-item field list, and doc_notes retrieval
  - Fallback to "Other" when doc_type is unknown
  - Error cases: missing template dir, missing evidence_types.json,
    invalid JSON, malformed structure, path traversal
"""

import json
from pathlib import Path

import pytest

from src.platform.templates.template_loader import TemplateLoader, _load_evidence_types

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

MINIMAL_EVIDENCE_TYPES = {
    "doc_type_id_mapping": {
        "10": "Alpha_Doc",
        "20": "Beta_Doc",
    },
    "document_types": [
        {
            "doc_type": "Alpha_Doc",
            "di_model": "prebuilt-invoice",
            "fields": ["field_a", "field_b"],
            "line_item_fields": ["item_desc", "quantity"],
            "doc_notes": "Alpha hint.",
        },
        {
            "doc_type": "Beta_Doc",
            "fields": ["field_x"],
        },
        {
            "doc_type": "Other",
            "fields": ["company_name", "issue_date", "goods_description"],
        },
    ],
}


def _make_template(tmpdir: Path, template_id: str, content: dict) -> TemplateLoader:
    """Write evidence_types.json and return a TemplateLoader rooted at tmpdir."""
    tdir = tmpdir / template_id
    tdir.mkdir(parents=True)
    (tdir / "evidence_types.json").write_text(
        json.dumps(content), encoding="utf-8"
    )
    (tdir / "knowledge_pack.json").write_text(
        json.dumps({"prompts": {"test": "Review {{document_type}} fields: {{fields}}"}}),
        encoding="utf-8",
    )
    # Clear lru_cache so each test starts fresh
    _load_evidence_types.cache_clear()
    return TemplateLoader(template_id, templates_root=tmpdir)


# ---------------------------------------------------------------------------
# Basic loading
# ---------------------------------------------------------------------------

class TestBasicLoading:
    def test_loads_valid_template(self, tmp_path):
        loader = _make_template(tmp_path, "test-tmpl", MINIMAL_EVIDENCE_TYPES)
        assert "Alpha_Doc" in loader.known_doc_types()
        assert "Beta_Doc" in loader.known_doc_types()

    def test_known_doc_types_excludes_duplicates(self, tmp_path):
        data = dict(MINIMAL_EVIDENCE_TYPES)
        data["document_types"] = [
            {"doc_type": "Dup", "fields": ["f1"]},
            {"doc_type": "Dup", "fields": ["f2"]},
        ]
        (tmp_path / "test-tmpl").mkdir(parents=True, exist_ok=True)
        (tmp_path / "test-tmpl" / "evidence_types.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
        _load_evidence_types.cache_clear()
        loader = TemplateLoader("test-tmpl", tmp_path)
        assert loader.known_doc_types().count("Dup") == 1


# ---------------------------------------------------------------------------
# resolve_doc_type
# ---------------------------------------------------------------------------

class TestResolveDocType:
    def test_resolves_known_id(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.resolve_doc_type("10") == "Alpha_Doc"

    def test_resolves_id_to_other_mapping(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.resolve_doc_type("20") == "Beta_Doc"

    def test_fallback_when_id_unknown(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.resolve_doc_type("99", fallback="Gamma_Doc") == "Gamma_Doc"

    def test_defaults_to_other_when_id_and_fallback_unknown(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.resolve_doc_type("99") == "Other"

    def test_string_id_coercion(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.resolve_doc_type("10") == "Alpha_Doc"


# ---------------------------------------------------------------------------
# get_di_model
# ---------------------------------------------------------------------------

class TestGetDiModel:
    def test_returns_configured_model(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_di_model("Alpha_Doc") == "prebuilt-invoice"

    def test_returns_default_when_no_model_configured(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_di_model("Beta_Doc") == "prebuilt-layout"

    def test_returns_default_for_unknown_doc_type(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_di_model("Unknown_Doc") == "prebuilt-layout"


# ---------------------------------------------------------------------------
# get_fields
# ---------------------------------------------------------------------------

class TestGetFields:
    def test_returns_correct_fields(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_fields("Alpha_Doc") == ["field_a", "field_b"]

    def test_falls_back_to_other(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        # Unknown doc type should fall back to "Other" fields
        other_fields = loader.get_fields("Other")
        fallback = loader.get_fields("NonExistentDoc")
        assert fallback == other_fields

    def test_returns_list_copy(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        fields = loader.get_fields("Alpha_Doc")
        fields.append("mutated")
        # Second call should return original
        assert "mutated" not in loader.get_fields("Alpha_Doc")


# ---------------------------------------------------------------------------
# get_line_item_fields
# ---------------------------------------------------------------------------

class TestGetLineItemFields:
    def test_returns_line_item_fields(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_line_item_fields("Alpha_Doc") == ["item_desc", "quantity"]

    def test_returns_empty_when_not_configured(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_line_item_fields("Beta_Doc") == []

    def test_returns_empty_for_unknown_type(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_line_item_fields("Unknown") == []


# ---------------------------------------------------------------------------
# get_doc_notes
# ---------------------------------------------------------------------------

class TestGetDocNotes:
    def test_returns_notes_when_present(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_doc_notes("Alpha_Doc") == "Alpha hint."

    def test_returns_none_when_absent(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_doc_notes("Beta_Doc") is None

    def test_returns_none_for_unknown_type(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)
        assert loader.get_doc_notes("Unknown") is None


class TestKnowledgePackPrompts:
    def test_renders_named_prompt(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)

        prompt = loader.get_prompt(
            "test",
            document_type="Alpha Doc",
            fields="field_a, field_b",
        )

        assert prompt == "Review Alpha Doc fields: field_a, field_b"

    def test_rejects_missing_prompt(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)

        with pytest.raises(KeyError, match="not defined"):
            loader.get_prompt("missing")

    def test_rejects_unresolved_placeholder(self, tmp_path):
        loader = _make_template(tmp_path, "t", MINIMAL_EVIDENCE_TYPES)

        with pytest.raises(ValueError, match="fields"):
            loader.get_prompt("test", document_type="Alpha Doc")


# ---------------------------------------------------------------------------
# Food-safety template (real file)
# ---------------------------------------------------------------------------

class TestFoodSafetyTemplate:
    """Smoke tests against the actual food-safety evidence_types.json."""

    _loader: TemplateLoader | None = None

    @classmethod
    def _get_loader(cls) -> TemplateLoader:
        if cls._loader is None:
            _load_evidence_types.cache_clear()
            cls._loader = TemplateLoader.for_template("food-safety")
        return cls._loader

    def test_invoice_uses_prebuilt_invoice_model(self):
        loader = self._get_loader()
        assert loader.get_di_model("Invoice") == "prebuilt-invoice"

    def test_invoice_has_fields(self):
        loader = self._get_loader()
        fields = loader.get_fields("Invoice")
        assert "invoice_number" in fields
        assert "invoice_date" in fields

    def test_invoice_has_line_item_fields(self):
        loader = self._get_loader()
        assert "quantity" in loader.get_line_item_fields("Invoice")

    def test_declaration_doc_has_notes(self):
        loader = self._get_loader()
        notes = loader.get_doc_notes("Declaration_Document")
        assert notes is not None and len(notes) > 10

    def test_id_50_resolves_to_invoice(self):
        loader = self._get_loader()
        assert loader.resolve_doc_type("50") == "Invoice"

    def test_unknown_id_falls_back_to_other(self):
        loader = self._get_loader()
        assert loader.resolve_doc_type("999") == "Other"

    def test_halal_cert_fields_non_empty(self):
        loader = self._get_loader()
        assert len(loader.get_fields("Halal_Slaughter_Certificate")) > 5

    def test_all_ids_resolve_to_known_doc_types(self):
        loader = self._get_loader()
        known = set(loader.known_doc_types())
        # Every ID mapping should resolve to a doc_type we actually define
        for _id_str, doc_type_name in loader._id_mapping.items():
            assert doc_type_name in known, (
                f"ID mapping '{_id_str}' → '{doc_type_name}' but that doc_type "
                "is not in document_types"
            )


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------

class TestErrorCases:
    def test_raises_on_missing_template_dir(self, tmp_path):
        _load_evidence_types.cache_clear()
        with pytest.raises(FileNotFoundError, match="Template directory not found"):
            TemplateLoader("nonexistent", tmp_path)

    def test_raises_on_missing_evidence_types(self, tmp_path):
        (tmp_path / "empty-tmpl").mkdir()
        _load_evidence_types.cache_clear()
        with pytest.raises(FileNotFoundError, match="evidence_types.json not found"):
            TemplateLoader("empty-tmpl", tmp_path)

    def test_raises_on_invalid_json(self, tmp_path):
        d = tmp_path / "bad-tmpl"
        d.mkdir()
        (d / "evidence_types.json").write_text("{not valid json", encoding="utf-8")
        _load_evidence_types.cache_clear()
        with pytest.raises(ValueError, match="invalid JSON"):
            TemplateLoader("bad-tmpl", tmp_path)

    def test_raises_on_missing_document_types_key(self, tmp_path):
        d = tmp_path / "no-dt"
        d.mkdir()
        (d / "evidence_types.json").write_text('{"doc_type_id_mapping": {}}', encoding="utf-8")
        _load_evidence_types.cache_clear()
        with pytest.raises(ValueError, match="'document_types' list"):
            TemplateLoader("no-dt", tmp_path)

    def test_rejects_unsafe_template_id(self, tmp_path):
        _load_evidence_types.cache_clear()
        with pytest.raises(ValueError, match="Invalid template_id"):
            TemplateLoader("../etc/passwd", tmp_path)

    def test_rejects_template_id_with_slash(self, tmp_path):
        _load_evidence_types.cache_clear()
        with pytest.raises(ValueError, match="Invalid template_id"):
            TemplateLoader("a/b", tmp_path)
