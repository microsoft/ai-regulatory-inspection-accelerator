"""Tests for deterministic three-component risk evaluation."""

from src.platform.policy.risk_assessment import assess_risk


def test_combines_quality_extraction_and_rule_components_once():
    result = assess_risk(
        "CASE-1",
        [
            {"ruleCode": "RULE-A", "result": "WARN", "riskWeight": 0.40},
            {"ruleCode": "RULE-B", "result": "FAIL", "riskWeight": 0.75},
        ],
        {
            "doc-1": {
                "qualityCheck": {"quality_score": 0.4},
                "lowConfidenceFields": ["ignored_because_quality_failed"],
            },
            "doc-2": {
                "qualityCheck": {"quality_score": 0.9},
                "lowConfidenceFields": ["invoice_number"],
            },
        },
        evaluated_at="2026-09-07T00:00:00+00:00",
    )

    assert result["compositeRiskScore"] == 1.0
    assert result["aiRiskLevel"] == "High"
    assert result["recommendation"] == "ACCEPT_WITH_WARNING"
    assert result["platformRecommendation"] == "HOLD"
    assert result["decisionBasis"] == "RISK_BAND"
    assert result["scoreBreakdown"] == {
        "caseQualityImpact": 0.6,
        "caseExtractionRisk": 0.45,
        "caseRuleSeverity": 0.75,
        "primaryRuleCode": "RULE-B",
    }


def test_low_quality_alone_retains_medium_recommendation():
    result = assess_risk(
        "CASE-2",
        [],
        {
            "doc-1": {
                "qualityCheck": {"quality_score": 0.4},
            }
        },
    )

    assert result["compositeRiskScore"] == 0.6
    assert result["aiRiskLevel"] == "Medium"
    assert result["recommendation"] == "ACCEPT_WITH_WARNING"
    assert result["recommendationLabel"] == "Accept with warnings"


def test_low_line_item_confidence_triggers_extraction_risk_without_ocr_average():
    result = assess_risk(
        "CASE-3",
        [],
        {
            "doc-1": {
                "qualityCheck": {"quality_score": 0.9},
                "ocrConfidence": 0.99,
                "lowConfidenceFields": [],
                "lineItems": [{"quantity": {"value": 10, "confidence": 0.60}}],
            }
        },
    )

    assert result["compositeRiskScore"] == 0.45
    assert result["documentAssessments"][0]["lowConfidenceFields"] == [
        "lineItems[0].quantity"
    ]


def test_item_risk_uses_maximum_linked_rule_weight():
    result = assess_risk(
        "CASE-4",
        [
            {"ruleCode": "MINOR", "result": "WARN", "riskWeight": 0.4, "itemCode": "3"},
            {"ruleCode": "CRITICAL", "result": "FAIL", "riskWeight": 0.9, "itemCode": "3"},
        ],
        {},
    )

    assert result["itemAssessments"] == [{
        "itemCode": "3",
        "itemRisk": 0.9,
        "ruleCodes": ["MINOR", "CRITICAL"],
    }]


def test_explicit_reject_action_is_required_for_fail_decision():
    result = assess_risk(
        "CASE-REJECT",
        [{
            "ruleCode": "PROHIBITED-CONDITION",
            "result": "FAIL",
            "riskWeight": 1.0,
            "riskAction": "REJECT",
        }],
        {},
    )

    assert result["aiRiskLevel"] == "High"
    assert result["recommendation"] == "REJECT"
    assert result["platformRecommendation"] == "FAIL"
    assert result["decisionBasis"] == "EXPLICIT_RULE_ACTION"
    assert result["explicitRejectRuleCodes"] == ["PROHIBITED-CONDITION"]


def test_template_rule_action_authorizes_rejection():
    result = assess_risk(
        "CASE-CONFIGURED-REJECT",
        [{"ruleCode": "DENY-RULE", "result": "FAIL", "riskWeight": 0.8}],
        {},
        config={"rule_actions": {"DENY-RULE": "REJECT"}},
    )

    assert result["platformRecommendation"] == "FAIL"
    assert result["explicitRejectRuleCodes"] == ["DENY-RULE"]


def test_risk_band_cannot_authorize_rejection():
    try:
        assess_risk(
            "CASE-INVALID-BAND",
            [{"ruleCode": "HIGH-RISK", "result": "FAIL", "riskWeight": 0.8}],
            {},
            config={
                "risk_bands": [{
                    "minimum": 0.0,
                    "risk_level": "High",
                    "recommendation": "REJECT",
                    "recommendation_label": "Reject",
                    "platform_recommendation": "FAIL",
                }],
            },
        )
    except ValueError as exc:
        assert "cannot authorize FAIL" in str(exc)
    else:
        raise AssertionError("Expected invalid direct-reject band to fail")


def test_repeated_low_confidence_documents_do_not_multiply_risk():
    documents = {
        f"doc-{index}": {
            "qualityCheck": {"quality_score": 0.9},
            "lowConfidenceFields": ["field"],
        }
        for index in range(3)
    }
    result = assess_risk("CASE-5", [], documents)

    assert result["compositeRiskScore"] == 0.45


def test_explicit_timestamp_makes_assessment_replay_stable():
    timestamp = "2026-09-07T12:00:00+00:00"
    first = assess_risk("CASE-6", [], {}, evaluated_at=timestamp)
    second = assess_risk("CASE-6", [], {}, evaluated_at=timestamp)

    assert first == second