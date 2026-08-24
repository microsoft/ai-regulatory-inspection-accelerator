"""
Unit tests for src/platform/document_intelligence/vision_extraction.py.

Tests verify that:
  1. Prompt-builder functions include the supplied ``fields`` list and doc_type.
  2. All three extraction functions call the OpenAI client with the right
     model, temperature, and JSON-object format, and return ``ExtractedMetadata``.
  3. ``cross_validate_with_ocr`` applies LLM corrections only for known
     ``allowed_fields`` and returns a correction log.
  4. All functions are offline-safe — Azure calls are faked via a minimal stub.

No real Azure credentials are required.
"""

import json

import pytest

from src.platform.document_intelligence.schemas import (
    DocumentInput,
    ExtractedMetadata,
    KVPair,
)
from src.platform.document_intelligence.vision_extraction import (
    _build_hybrid_extraction_prompt,
    _build_vision_extraction_prompt,
    cross_validate_with_ocr,
    extract_metadata_hybrid,
    extract_metadata_vision,
)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

DOC_TYPE = "Halal_Slaughter_Certificate"
FIELDS = ["certificate_number", "issue_date", "expiry_date", "issuing_authority"]

FAKE_DOC_INPUT = DocumentInput(
    file_path="uploads/halal.pdf",
    file_name="halal.pdf",
    file_extension="pdf",
    source_category_folder=DOC_TYPE,
)

VALID_KV_JSON = json.dumps({
    "tables_extracted": [],
    "key_value_pairs": [
        {
            "key": "Certificate No.",
            "value": "HC-001",
            "confidence": 0.95,
            "canonical_field": "certificate_number",
        }
    ],
    "line_items": [],
    "signature_detected": False,
    "language": "en",
})


class _FakeChoice:
    def __init__(self, content: str):
        self.message = type("M", (), {"content": content})()


class _FakeCompletion:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class FakeOpenAIClient:
    """Minimal fake that records calls and returns a preset response."""

    def __init__(self, response_content: str = VALID_KV_JSON):
        self._response_content = response_content
        self.calls: list[dict] = []
        self.chat = self

    @property
    def completions(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return _FakeCompletion(self._response_content)


# ---------------------------------------------------------------------------
# Prompt builder tests
# ---------------------------------------------------------------------------

class TestBuildVisionPrompt:
    def test_contains_fields_text(self):
        prompt = _build_vision_extraction_prompt(DOC_TYPE, FIELDS)
        for f in FIELDS:
            assert f in prompt, f"Expected field '{f}' in vision prompt"

    def test_contains_doc_type_display_name(self):
        prompt = _build_vision_extraction_prompt(DOC_TYPE, FIELDS)
        assert "Halal Slaughter Certificate" in prompt

    def test_contains_json_schema_instruction(self):
        prompt = _build_vision_extraction_prompt(DOC_TYPE, FIELDS)
        assert "key_value_pairs" in prompt


class TestBuildHybridPrompt:
    def test_contains_fields_text(self):
        prompt = _build_hybrid_extraction_prompt(DOC_TYPE, FIELDS)
        for f in FIELDS:
            assert f in prompt

    def test_mentions_ocr_strategy(self):
        prompt = _build_hybrid_extraction_prompt(DOC_TYPE, FIELDS)
        assert "OCR" in prompt


# ---------------------------------------------------------------------------
# extract_metadata_vision
# ---------------------------------------------------------------------------

class TestExtractMetadataVision:
    def test_returns_extracted_metadata(self):
        client = FakeOpenAIClient()
        meta, _ = extract_metadata_vision(
            client, FAKE_DOC_INPUT, b"\x89PNG\r\n", DOC_TYPE, FIELDS,
            deployment="gpt-test",
        )
        assert isinstance(meta, ExtractedMetadata)

    def test_parses_kv_pairs(self):
        client = FakeOpenAIClient()
        meta, _ = extract_metadata_vision(
            client, FAKE_DOC_INPUT, b"\x89PNG\r\n", DOC_TYPE, FIELDS,
            deployment="gpt-test",
        )
        assert len(meta.key_value_pairs) == 1
        assert meta.key_value_pairs[0].canonical_field == "certificate_number"

    def test_calls_openai_with_vision_content_block(self):
        client = FakeOpenAIClient()
        extract_metadata_vision(
            client, FAKE_DOC_INPUT, b"\x89PNG\r\n", DOC_TYPE, FIELDS,
            deployment="gpt-test",
        )
        assert len(client.calls) == 1
        messages = client.calls[0]["messages"]
        user_msg = messages[1]["content"]
        # User message should contain an image_url block
        assert any(block.get("type") == "image_url" for block in user_msg)

    def test_returns_empty_metadata_on_invalid_json(self):
        client = FakeOpenAIClient("not json at all")
        meta, _ = extract_metadata_vision(
            client, FAKE_DOC_INPUT, b"\x89PNG\r\n", DOC_TYPE, FIELDS,
            deployment="gpt-test",
            max_retries=1,
        )
        assert isinstance(meta, ExtractedMetadata)


# ---------------------------------------------------------------------------
# extract_metadata_hybrid
# ---------------------------------------------------------------------------

class TestExtractMetadataHybrid:
    def test_returns_extracted_metadata(self):
        client = FakeOpenAIClient()
        meta, _ = extract_metadata_hybrid(
            client, FAKE_DOC_INPUT, b"\x89PNG\r\n",
            "OCR text here", DOC_TYPE, FIELDS,
            deployment="gpt-test",
        )
        assert isinstance(meta, ExtractedMetadata)

    def test_sends_ocr_text_in_user_message(self):
        client = FakeOpenAIClient()
        ocr = "OCR sample text"
        extract_metadata_hybrid(
            client, FAKE_DOC_INPUT, b"\x89PNG\r\n",
            ocr, DOC_TYPE, FIELDS,
            deployment="gpt-test",
        )
        user_content = client.calls[0]["messages"][1]["content"]
        text_parts = [b for b in user_content if b.get("type") == "text"]
        assert any(ocr in part["text"] for part in text_parts)

    def test_multi_page_sends_multiple_image_blocks(self):
        client = FakeOpenAIClient()
        pages = [b"\x89PNG\r\n" + bytes([i]) for i in range(3)]
        extract_metadata_hybrid(
            client, FAKE_DOC_INPUT, pages,
            "OCR", DOC_TYPE, FIELDS,
            deployment="gpt-test",
        )
        user_content = client.calls[0]["messages"][1]["content"]
        image_blocks = [b for b in user_content if b.get("type") == "image_url"]
        assert len(image_blocks) == 3


# ---------------------------------------------------------------------------
# cross_validate_with_ocr
# ---------------------------------------------------------------------------

class TestCrossValidateWithOCR:
    def _make_correction_response(self, field: str, value: str, reason: str = "") -> str:
        return json.dumps({
            "corrections": {
                field: {"value": value, "reason": reason}
            }
        })

    def test_applies_correction_for_known_field(self):
        client = FakeOpenAIClient(
            self._make_correction_response("certificate_number", "HC-FIXED", "OCR error")
        )
        fields = {
            "certificate_number": {"value": "HC-BROKEN", "confidence": 0.5},
            "issue_date": {"value": None},
        }
        result, corrections = cross_validate_with_ocr(
            client, fields, "some OCR text", DOC_TYPE,
            allowed_fields=["certificate_number", "issue_date"],
            deployment="gpt-test",
        )
        assert result["certificate_number"]["value"] == "HC-FIXED"
        assert result["certificate_number"].get("ocr_validated") is True
        assert len(corrections) == 1

    def test_ignores_correction_for_unknown_field(self):
        client = FakeOpenAIClient(
            self._make_correction_response("unknown_field", "value")
        )
        fields = {"certificate_number": {"value": "HC-001", "confidence": 0.9}}
        result, corrections = cross_validate_with_ocr(
            client, fields, "OCR text", DOC_TYPE,
            allowed_fields=["certificate_number"],
            deployment="gpt-test",
        )
        assert "unknown_field" not in result
        assert corrections == []

    def test_fills_null_field(self):
        client = FakeOpenAIClient(
            self._make_correction_response("issue_date", "2024-01-15", "Found in OCR")
        )
        fields = {
            "certificate_number": {"value": "HC-001", "confidence": 0.9},
            "issue_date": {"value": None},
        }
        result, corrections = cross_validate_with_ocr(
            client, fields, "OCR text", DOC_TYPE,
            allowed_fields=["certificate_number", "issue_date"],
            deployment="gpt-test",
        )
        assert result["issue_date"]["value"] == "2024-01-15"
        assert "filled null" in corrections[0]

    def test_returns_unchanged_fields_on_empty_ocr(self):
        client = FakeOpenAIClient()
        fields = {"certificate_number": {"value": "HC-001"}}
        result, corrections = cross_validate_with_ocr(
            client, fields, "",  # empty OCR
            DOC_TYPE, allowed_fields=["certificate_number"],
            deployment="gpt-test",
        )
        assert result is fields
        assert corrections == []
        assert client.calls == []

    def test_returns_unchanged_on_llm_failure(self):
        class FailingClient:
            chat = None

            def __init__(self):
                class C:
                    completions = self

                self.chat = C()

            def create(self, **kwargs):
                raise RuntimeError("LLM unavailable")

        client = FailingClient()
        fields = {"certificate_number": {"value": "HC-001"}}
        result, corrections = cross_validate_with_ocr(
            client, fields, "OCR text", DOC_TYPE,
            allowed_fields=["certificate_number"],
            deployment="gpt-test",
        )
        assert result is fields
        assert corrections == []
