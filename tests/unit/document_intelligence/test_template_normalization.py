"""Tests proving document normalization is controlled by template configuration."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from src.platform.document_intelligence.di_normalization import (
    canonicalize_fields_for_doc_type,
    normalize_all_fields,
)
from src.platform.document_intelligence.schemas import ExtractedMetadata, KVPair
from src.platform.templates.template_loader import (
    TemplateLoader,
    _load_evidence_types,
    _load_normalization_config,
)


def _loader(tmp_path: Path, template_id: str, profile: dict) -> TemplateLoader:
    template_path = tmp_path / template_id
    template_path.mkdir()
    (template_path / "evidence_types.json").write_text(
        json.dumps({
            "document_types": [
                {"doc_type": "Application", "fields": ["submitted_on", "amount"]}
            ]
        }),
        encoding="utf-8",
    )
    (template_path / "normalization.json").write_text(
        json.dumps({"defaults": profile, "document_types": {}}),
        encoding="utf-8",
    )
    _load_evidence_types.cache_clear()
    _load_normalization_config.cache_clear()
    return TemplateLoader(template_id, tmp_path)


def _openai_client() -> MagicMock:
    client = MagicMock()
    response = type("Response", (), {
        "choices": [type("Choice", (), {
            "message": type("Message", (), {
                "content": '{"corrections": {}, "no_changes_needed": []}'
            })()
        })()]
    })()
    client.chat.completions.create.return_value = response
    return client


def test_aliases_are_selected_by_template_only(tmp_path):
    metadata = ExtractedMetadata(
        key_value_pairs=[KVPair(key="Submission Date", value="2026-08-24", confidence=0.9)]
    )
    configured = _loader(
        tmp_path,
        "configured",
        {"field_aliases": {"submitted_on": ["Submission Date"]}},
    )
    unconfigured = _loader(tmp_path, "unconfigured", {})

    configured_fields, _ = canonicalize_fields_for_doc_type(
        metadata,
        "Application",
        allowed_fields=configured.get_fields("Application"),
        line_item_fields=[],
        normalization_config=configured.get_normalization_config("Application"),
    )
    unconfigured_fields, _ = canonicalize_fields_for_doc_type(
        metadata,
        "Application",
        allowed_fields=unconfigured.get_fields("Application"),
        line_item_fields=[],
        normalization_config=unconfigured.get_normalization_config("Application"),
    )

    assert configured_fields["submitted_on"]["value"] == "2026-08-24"
    assert unconfigured_fields["submitted_on"]["value"] is None


def test_date_and_numeric_branches_are_selected_by_template(tmp_path):
    loader = _loader(
        tmp_path,
        "application",
        {"date_fields": ["submitted_on"], "numeric_fields": ["amount"]},
    )
    fields = {
        "submitted_on": {"value": "٢٠٢٦/٠٨/٢٤"},
        "amount": {"value": "١٢٥٫٥"},
    }

    normalized, _, _ = normalize_all_fields(
        _openai_client(),
        fields,
        [],
        "Application",
        "application.pdf",
        allowed_fields=loader.get_fields("Application"),
        normalization_config=loader.get_normalization_config("Application"),
    )

    assert normalized["submitted_on"]["value"] == "2026-08-24"
    assert normalized["amount"]["value"] == "125.5"


def test_quality_threshold_supports_document_override(tmp_path):
    template_path = tmp_path / "quality"
    template_path.mkdir()
    (template_path / "evidence_types.json").write_text(
        json.dumps({"document_types": [{"doc_type": "Other", "fields": ["value"]}]}),
        encoding="utf-8",
    )
    (template_path / "normalization.json").write_text(
        json.dumps({
            "defaults": {"quality_threshold": 0.7},
            "document_types": {"Other": {"quality_threshold": 0.9}},
        }),
        encoding="utf-8",
    )
    _load_evidence_types.cache_clear()
    _load_normalization_config.cache_clear()
    loader = TemplateLoader("quality", tmp_path)

    assert loader.get_quality_threshold("Other") == 0.9