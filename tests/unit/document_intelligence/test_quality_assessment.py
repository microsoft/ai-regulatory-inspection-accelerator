"""
Unit tests for src/platform/document_intelligence/quality_assessment.py.
"""

from src.platform.document_intelligence.quality_assessment import (
    DEFAULT_QUALITY_SCORE_THRESHOLD,
    QualityCheckResult,
    assess_quality,
    evaluate_quality_response,
)


class TestEvaluateQualityResponse:
    def test_score_above_threshold_passes(self):
        result = evaluate_quality_response({"quality_score": 0.9, "issues": [], "recommendation": "Proceed"})
        assert result.passed is True
        assert result.quality_score == 0.9

    def test_score_below_threshold_fails_even_if_model_says_passed(self):
        """PAFN regression: the model's own `passed` field is untrustworthy -
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
