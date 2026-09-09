"""
Unit tests for the DI extraction pipeline:
  - Prompt building via TemplateLoader (field list, line-item notes, doc_notes)
  - run_document_intelligence: DI model selection comes from loader, not DI_MODEL_MAP
  - extract_metadata_llm: retries, JSON normalisation, empty metadata on exhaustion
  - Field-structure check: given the same raw OCR markdown and fake LLM response,
    ``extract_metadata_llm`` produces the expected field structure (field names,
    confidence, canonical_field).

All tests are offline — Azure DI, Blob, and OpenAI calls are faked.
"""

import json
from unittest.mock import MagicMock

import pytest

from src.platform.document_intelligence.di_extraction import (
    _build_metadata_extraction_prompt,
    extract_metadata_llm,
)
from src.platform.document_intelligence.schemas import (
    DocumentInput,
    DocumentIntelligenceResult,
    ExtractedMetadata,
)
from src.platform.shared.ai_client import AIClient
from src.platform.templates.template_loader import TemplateLoader, _load_evidence_types

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def loader(tmp_path) -> TemplateLoader:
    evidence = {
        "doc_type_id_mapping": {"50": "Invoice"},
        "document_types": [
            {
                "doc_type": "Invoice",
                "di_model": "prebuilt-invoice",
                "doc_notes": "Extract every product row as a separate line_item.",
                "fields": ["invoice_number", "invoice_date", "net_weight"],
                "line_item_fields": ["item_description", "quantity"],
            },
            {
                "doc_type": "Health_Certificate",
                "fields": ["certificate_number", "issue_date"],
            },
            {
                "doc_type": "Other",
                "fields": ["company_name", "issue_date", "goods_description"],
            },
        ],
    }
    (tmp_path / "food-test").mkdir()
    (tmp_path / "food-test" / "evidence_types.json").write_text(
        json.dumps(evidence), encoding="utf-8"
    )
    (tmp_path / "food-test" / "knowledge_pack.json").write_text(
        json.dumps({
            "prompts": {
                "metadata_extraction": (
                    "You are an Arabic and English bilingual extraction expert. "
                    "Use Modern Standard Arabic, dialectal wording, Arabizi, and "
                    "code-switching. Preserve text and lower the confidence when "
                    "uncertain. Document: {{document_type}}. Fields: {{fields}}. "
                    "{{document_notes}} {{line_item_guidance}} Return key_value_pairs JSON."
                )
            }
        }),
        encoding="utf-8",
    )
    _load_evidence_types.cache_clear()
    return TemplateLoader("food-test", tmp_path)


@pytest.fixture()
def doc_input() -> DocumentInput:
    return DocumentInput(
        file_path="uploads/inv.pdf",
        file_name="inv.pdf",
        file_extension="pdf",
        source_category_folder="Invoice",
    )


@pytest.fixture()
def di_result() -> DocumentIntelligenceResult:
    return DocumentIntelligenceResult(
        markdown_content="# Invoice\n\nInvoice No: INV-001\nDate: 2024-03-15",
        page_count=1,
        languages_detected=["en"],
        has_handwriting=False,
        has_signatures=False,
        ocr_confidence=0.97,
    )


class _FakeChoice:
    def __init__(self, content: str):
        self.message = type("M", (), {"content": content})()


class _FakeCompletion:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


def _make_openai_client(response: str) -> MagicMock:
    client = MagicMock()
    client.chat.completions.create.return_value = _FakeCompletion(response)
    return client


VALID_LLM_RESPONSE = json.dumps({
    "tables_extracted": [],
    "key_value_pairs": [
        {"key": "Invoice No", "value": "INV-001", "confidence": 0.96,
         "canonical_field": "invoice_number"},
        {"key": "Date", "value": "2024-03-15", "confidence": 0.93,
         "canonical_field": "invoice_date"},
    ],
    "line_items": [],
    "signature_detected": False,
    "language": "en",
})


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

class TestBuildMetadataExtractionPrompt:
    def test_contains_all_fields(self, loader):
        prompt = _build_metadata_extraction_prompt("Invoice", loader)
        assert "invoice_number" in prompt
        assert "invoice_date" in prompt
        assert "net_weight" in prompt

    def test_prompt_is_domain_neutral(self, loader):
        prompt = _build_metadata_extraction_prompt("Invoice", loader).lower()
        assert all(term not in prompt for term in ("food-safety", "pafn", "kuwait", "raqeb", "bayan"))

    def test_prompt_targets_verified_bilingual_behavior(self, loader):
        prompt = _build_metadata_extraction_prompt("Invoice", loader).lower()
        assert "arabic and english bilingual" in prompt
        assert "modern standard arabic" in prompt
        assert "dialectal" in prompt
        assert "arabizi" in prompt
        assert "code-switching" in prompt
        assert "multilingual" not in prompt
        assert "lower the confidence" in prompt

    def test_contains_doc_notes(self, loader):
        prompt = _build_metadata_extraction_prompt("Invoice", loader)
        assert "Extract every product row" in prompt

    def test_contains_line_item_section(self, loader):
        prompt = _build_metadata_extraction_prompt("Invoice", loader)
        assert "LINE ITEM EXTRACTION" in prompt
        assert "item_description" in prompt

    def test_no_line_item_section_when_not_configured(self, loader):
        prompt = _build_metadata_extraction_prompt("Health_Certificate", loader)
        assert "LINE ITEM EXTRACTION" not in prompt

    def test_includes_doc_type_display_name(self, loader):
        prompt = _build_metadata_extraction_prompt("Invoice", loader)
        assert "Invoice" in prompt


# ---------------------------------------------------------------------------
# extract_metadata_llm
# ---------------------------------------------------------------------------

class TestExtractMetadataLLM:
    def test_routes_through_ai_client_and_tracks_usage(self, doc_input, di_result, loader):
        events = []
        response = _FakeCompletion(VALID_LLM_RESPONSE)
        response.model = "gpt-test"
        response.usage = {
            "prompt_tokens": 20,
            "completion_tokens": 5,
            "prompt_tokens_details": {"cached_tokens": 8},
        }
        client = AIClient(
            lambda **kwargs: response,
            track_event=lambda name, **fields: events.append((name, fields)),
        )

        extract_metadata_llm(
            doc_input,
            di_result,
            client,
            "Invoice",
            loader,
            case_id="CASE-24",
            tenant_id="TENANT-24",
        )

        assert events[0][0] == "LLMCallCompleted"
        assert events[0][1]["case_id"] == "CASE-24"
        assert events[0][1]["cached_tokens"] == 8

    def test_returns_extracted_metadata(self, doc_input, di_result, loader):
        client = _make_openai_client(VALID_LLM_RESPONSE)
        meta, _raw = extract_metadata_llm(doc_input, di_result, client, "Invoice", loader)
        assert isinstance(meta, ExtractedMetadata)

    def test_parses_kv_pairs_correctly(self, doc_input, di_result, loader):
        client = _make_openai_client(VALID_LLM_RESPONSE)
        meta, _ = extract_metadata_llm(doc_input, di_result, client, "Invoice", loader)
        keys = {kv.canonical_field for kv in meta.key_value_pairs}
        assert "invoice_number" in keys
        assert "invoice_date" in keys

    def test_confidence_clamped_0_to_1(self, doc_input, di_result, loader):
        response = json.dumps({
            "tables_extracted": [],
            "key_value_pairs": [
                {"key": "k", "value": "v", "confidence": 1.5, "canonical_field": "invoice_number"},
            ],
            "line_items": [],
            "signature_detected": False,
            "language": "en",
        })
        client = _make_openai_client(response)
        meta, _ = extract_metadata_llm(doc_input, di_result, client, "Invoice", loader)
        assert meta.key_value_pairs[0].confidence <= 1.0

    def test_returns_empty_metadata_after_all_retries(self, doc_input, di_result, loader):
        client = _make_openai_client("not json")
        meta, _raw = extract_metadata_llm(
            doc_input, di_result, client, "Invoice", loader
        )
        # Expect empty / default metadata after retry exhaustion
        assert isinstance(meta, ExtractedMetadata)
        assert meta.key_value_pairs == []

    def test_retries_on_json_error(self, doc_input, di_result, loader):
        responses = ["bad json", "bad json", VALID_LLM_RESPONSE]
        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            resp = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            return _FakeCompletion(resp)

        client = MagicMock()
        client.chat.completions.create.side_effect = fake_create

        meta, _ = extract_metadata_llm(doc_input, di_result, client, "Invoice", loader)
        assert call_count == 3
        assert len(meta.key_value_pairs) > 0


# ---------------------------------------------------------------------------
# DI model selection parity
# ---------------------------------------------------------------------------

class TestDIModelSelection:
    """Verify that Invoice → prebuilt-invoice (was DI_MODEL_MAP; now TemplateLoader)."""

    def test_invoice_gets_prebuilt_invoice_model(self, loader):
        assert loader.get_di_model("Invoice") == "prebuilt-invoice"

    def test_unknown_type_gets_default_layout_model(self, loader):
        assert loader.get_di_model("SomeOtherDoc") == "prebuilt-layout"

    def test_health_cert_gets_default_layout_model(self, loader):
        assert loader.get_di_model("Health_Certificate") == "prebuilt-layout"


# ---------------------------------------------------------------------------
# resolve_doc_type parity
# ---------------------------------------------------------------------------

class TestResolveDocTypeParity:
    """``loader.resolve_doc_type`` must resolve IDs, names, and unknown values."""

    def test_known_id_resolved(self, loader):
        assert loader.resolve_doc_type("50") == "Invoice"

    def test_unknown_id_uses_fallback(self, loader):
        assert loader.resolve_doc_type("999", fallback="Invoice") == "Invoice"

    def test_unknown_id_no_fallback_returns_other(self, loader):
        assert loader.resolve_doc_type("999") == "Other"
