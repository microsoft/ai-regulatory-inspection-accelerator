"""Tests for template-driven decision delivery."""

import asyncio

from connectors.sdk.base_connector import BaseConnector, ConnectorDeliveryError
from src.platform.decision.delivery import build_decision, deliver_decision

VOCABULARY = {
    "PASS": {"recommendation": "ACCEPT", "label": "Accept"},
    "HOLD": {
        "recommendation": "ACCEPT_WITH_WARNING",
        "label": "Accept with warnings",
    },
    "FAIL": {"recommendation": "REJECT", "label": "Reject"},
}


class FakeConnector(BaseConnector):
    def __init__(self, failures: int = 0):
        self.failures = failures
        self.attempts = 0
        self.statuses = []
        self.decisions = []
        super().__init__({})

    def transform_submission(self, external_payload):
        return external_payload

    def deliver_decision(self, aria_decision):
        self.attempts += 1
        self.decisions.append(aria_decision)
        if self.attempts <= self.failures:
            raise RuntimeError("temporary failure")
        return {"accepted": True}

    def report_status(self, case_id, status, error=None):
        self.statuses.append((case_id, status, error))
        return True


def _input(recommendation="HOLD"):
    return {
        "payload": {"requestId": "CASE-1"},
        "status": "COMPLETED",
        "recommendation": recommendation,
        "summary": "Decision summary",
        "aiRiskLevel": "Medium",
        "compositeRiskScore": 0.45,
        "riskEvaluation": {"id": "CASE-1-risk"},
    }


def test_build_decision_uses_template_vocabulary():
    decision = build_decision(_input(), VOCABULARY)

    assert decision["recommendation"] == "ACCEPT_WITH_WARNING"
    assert decision["recommendationLabel"] == "Accept with warnings"
    assert decision["compositeRiskScore"] == 0.45


def test_delivery_retries_and_reports_status():
    connector = FakeConnector(failures=2)
    delays = []

    async def record_delay(delay):
        delays.append(delay)

    result = asyncio.run(deliver_decision(
        _input(),
        connector=connector,
        vocabulary=VOCABULARY,
        sleep=record_delay,
    ))

    assert result["delivered"] is True
    assert result["attempts"] == 3
    assert delays == [5.0, 30.0]
    assert [status for _, status, _ in connector.statuses] == ["DELIVERING", "COMPLETED"]


def test_delivery_failure_reports_terminal_status():
    connector = FakeConnector(failures=3)

    async def no_wait(delay):
        del delay

    try:
        asyncio.run(deliver_decision(
            _input("FAIL"),
            connector=connector,
            vocabulary=VOCABULARY,
            sleep=no_wait,
        ))
    except ConnectorDeliveryError:
        pass
    else:
        raise AssertionError("Expected ConnectorDeliveryError")

    assert connector.statuses[-1][1] == "DELIVERY_FAILED"