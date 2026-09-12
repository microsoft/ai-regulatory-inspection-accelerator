"""Tests for the generic Reasoning-to-Policy handoff."""

import asyncio

from src.platform.policy.rules_policy import run


def test_reasoning_outputs_are_preserved_and_escalate_to_hold():
    reasoning_finding = {
        "ruleCode": "EVIDENCE_CONFLICT",
        "result": "FAIL",
        "riskWeight": 0.75,
        "message": "Two submitted documents disagree.",
    }
    document_check = {
        "field": "applicant_name",
        "result": "FAIL",
        "documents": ["application", "identity_document"],
    }

    result = asyncio.run(
        run(
            {"requestId": "GENERIC-CASE-1", "items": [], "documents": []},
            {},
            [],
            reasoning_findings=[reasoning_finding],
            reasoning_document_checks=[document_check],
        )
    )

    assert result["recommendation"] == "HOLD"
    assert result["riskScore"] == 0.75
    assert result["riskEvaluation"]["scoreBreakdown"]["caseRuleSeverity"] == 0.75
    assert result["publicRecommendation"] == "ACCEPT_WITH_WARNING"
    assert reasoning_finding in result["findings"]
    assert result["documentChecks"] == [document_check]


def test_empty_reasoning_outputs_preserve_existing_policy_behavior():
    result = asyncio.run(
        run(
            {"requestId": "GENERIC-CASE-2", "items": [], "documents": []},
            {},
            [],
        )
    )

    assert result["recommendation"] == "PASS"
    assert result["findings"] == []
    assert result["documentChecks"] == []


def test_low_quality_evidence_produces_warning_recommendation():
    result = asyncio.run(
        run(
            {"requestId": "GENERIC-CASE-3", "items": [], "documents": []},
            {
                "doc-1": {
                    "qualityCheck": {"quality_score": 0.2},
                    "fields": {},
                }
            },
            [],
        )
    )

    assert result["recommendation"] == "HOLD"
    assert result["publicRecommendation"] == "ACCEPT_WITH_WARNING"
    assert result["recommendationStatus"] == "ELIGIBLE"


def test_configured_rule_weight_produces_rejection():
    result = asyncio.run(
        run(
            {"requestId": "GENERIC-CASE-4", "items": [], "documents": []},
            {},
            [],
            reasoning_findings=[{
                "ruleCode": "GENERIC-BLOCK",
                "result": "FAIL",
                "riskWeight": 1.0,
                "riskAction": "REJECT",
            }],
        )
    )

    assert result["recommendation"] == "FAIL"


def test_low_quality_does_not_suppress_adverse_rule_recommendation():
    result = asyncio.run(
        run(
            {"requestId": "GENERIC-CASE-5", "items": [], "documents": []},
            {
                "doc-1": {
                    "qualityCheck": {"quality_score": 0.2},
                    "fields": {},
                }
            },
            [],
            reasoning_findings=[{
                "ruleCode": "GENERIC-BLOCK",
                "result": "FAIL",
                "riskWeight": 1.0,
                "riskAction": "REJECT",
            }],
        )
    )

    assert result["riskEvaluation"]["scoreBreakdown"]["caseRuleSeverity"] == 1.0
    assert result["recommendation"] == "FAIL"
    assert result["recommendationStatus"] == "ELIGIBLE"