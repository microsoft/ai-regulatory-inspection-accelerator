"""Tests for the generic Reasoning-to-Policy handoff."""

import asyncio

from src.platform.policy.rules_policy import run


def test_reasoning_outputs_are_preserved_and_escalate_to_hold():
    reasoning_finding = {
        "ruleCode": "EVIDENCE_CONFLICT",
        "result": "FAIL",
        "severity": "high",
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