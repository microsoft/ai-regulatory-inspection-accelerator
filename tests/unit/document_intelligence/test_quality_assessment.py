"""
Unit tests for src/platform/document_intelligence/quality_assessment.py.
"""

import json
from unittest.mock import MagicMock

from src.platform.document_intelligence.quality_assessment import (
    DEFAULT_QUALITY_SCORE_THRESHOLD,
    QualityCheckResult,
    assess_quality,
    check_image_quality,
    evaluate_quality_response,
)
from src.platform.templates.template_loader import TemplateLoader

LOADER = TemplateLoader.for_template("food-safety")


class TestEvaluateQualityResponse:
    def test_score_above_threshold_passes(self):
        result = evaluate_quality_response({"quality_score": 0.9, "issues": [], "recommendation": "Proceed"})
        assert result.passed is True
        assert result.quality_score == 0.9

    def test_score_below_threshold_fails_even_if_model_says_passed(self):
        """Regression: the model's own `passed` field is untrustworthy -
        only the score-vs-threshold comparison determines the result."""
        result = evaluate_quality_response({"passed": True, "quality_score": 0.1, "issues": ["Very Blurry Scan"]})
        assert result.passed is False

    def test_score_exactly_at_threshold_passes(self):
        result = evaluate_quality_response({"quality_score": DEFAULT_QUALITY_SCORE_THRESHOLD})
        assert result.passed is True

    def test_custom_threshold(self):
        result = evaluate_quality_response({"quality_score": 0.6}, threshold=0.5)
        assert result.passed is True
        result2 = evaluate_quality_response({"quality_score": 0.6}, threshold=0.7)
        assert result2.passed is False

    def test_missing_fields_default_safely(self):
        result = evaluate_quality_response({})
        assert result.passed is False
        assert result.quality_score == 0.0
        assert result.issues == []
        assert result.recommendation == ""

    def test_to_dict(self):
        result = QualityCheckResult(passed=True, quality_score=0.9, issues=[], recommendation="Proceed")
        assert result.to_dict() == {
            "passed": True, "quality_score": 0.9, "issues": [], "recommendation": "Proceed",
        }


class TestAssessQuality:
    def test_delegates_to_injected_vision_check_fn(self):
        captured = {}

        def fake_vision_check(image_data, file_name):
            captured["image_data"] = image_data
            captured["file_name"] = file_name
            return {"quality_score": 0.85, "issues": [], "recommendation": "Proceed with extraction"}

        result = assess_quality(fake_vision_check, b"fake-bytes", "invoice.pdf")
        assert result.passed is True
        assert captured["image_data"] == b"fake-bytes"
        assert captured["file_name"] == "invoice.pdf"

    def test_custom_threshold_passed_through(self):
        def fake_vision_check(image_data, file_name):
            return {"quality_score": 0.6}

        result = assess_quality(fake_vision_check, b"bytes", "scan.png", threshold=0.5)
        assert result.passed is True


class TestCheckImageQuality:
    def test_applies_template_threshold_instead_of_model_boolean(self):
        client = MagicMock()
        response = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {
                    "content": json.dumps({
                        "passed": True,
                        "quality_score": 0.65,
                        "issues": ["Low Contrast"],
                    })
                })()
            })()]
        })()
        client.chat.completions.create.return_value = response

        result = check_image_quality(
            client,
            b"image-bytes",
            "document.png",
            LOADER,
            threshold=0.7,
            retry_delay_sec=0,
        )

        assert result.passed is False
        assert result.quality_score == 0.65

    def test_provider_failure_remains_a_soft_check(self):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("unavailable")

        result = check_image_quality(
            client,
            b"image-bytes",
            "document.png",
            LOADER,
            threshold=0.8,
            max_retries=2,
            retry_delay_sec=0,
        )

        assert result.passed is True
        assert result.quality_score == 0.8
        assert client.chat.completions.create.call_count == 2

    def test_uses_deterministic_json_options(self):
        client = MagicMock()
        client.chat.completions.create.return_value = type("Response", (), {
            "choices": [type("Choice", (), {
                "message": type("Message", (), {
                    "content": json.dumps({"quality_score": 0.9, "issues": []})
                })()
            })()]
        })()

        check_image_quality(client, b"image-bytes", "document.png", LOADER)

        call = client.chat.completions.create.call_args.kwargs
        assert call["temperature"] == 0.0
        assert call["seed"] == 42
        assert call["response_format"] == {"type": "json_object"}
