"""Tests for the PAFN-compatible 0-100 risk model."""

from src.platform.policy.pafn_risk_assessment import assess_pafn_risk


def test_pafn_scores_document_item_rule_and_case_maxima():
    result = assess_pafn_risk(
        "CASE-100",
        [{
            "documentId": "doc-1",
            "qualityScore": 0.90,
            "fields": {
                "a": {"value": "A", "confidence": 0.95},
                "b": {"value": "B", "confidence": 0.60},
            },
        }],
        [
            {"ruleCode": "ITEM_WEIGHT", "result": "FAIL", "itemNumber": 1, "riskScore": 75},
            {"ruleCode": "WARNING", "result": "WARN", "riskScore": 40},
        ],
    )

    assert result["documents"][0]["documentConfidenceScore"] == 50.0
    assert result["documents"][0]["documentRiskScore"] == 0
    assert result["overallItemRiskScore"] == 75
    assert result["overallRuleRiskScore"] == 40
    assert result["caseRiskScore"] == 75
    assert result["recommendation"] == "ACCEPT_WITH_WARNING"


def test_explicit_reject_rule_overrides_score_based_warning():
    result = assess_pafn_risk(
        "CASE-REJECT",
        [],
        [{"ruleCode": "REJECTED_HS_CODE", "result": "FAIL"}],
    )

    assert result["caseRiskScore"] == 100
    assert result["recommendation"] == "REJECT"


def test_low_quality_requires_manual_review_without_rejection():
    result = assess_pafn_risk(
        "CASE-QUALITY",
        [{"documentId": "doc-1", "qualityScore": 0.50, "fields": {}}],
        [],
    )

    assert result["caseRiskScore"] == 40
    assert result["recommendation"] == "ACCEPT_WITH_WARNING"
    assert result["manualReview"]["required"] is True
