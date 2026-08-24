"""Unit tests for src/platform/policy/evaluators/logical_rules.py"""

from datetime import date, timedelta

import pytest

from src.platform.policy.evaluators.logical_rules import validate_logical_rules


def _iso(d: date) -> str:
    return d.isoformat()


TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)
LAST_YEAR = TODAY.replace(year=TODAY.year - 1)
NEXT_YEAR = TODAY.replace(year=TODAY.year + 1)


LOGICAL_RULE = {
    "id": "LOGICAL_RULES",
    "isActive": "True",
    "logicalRules": [
        {
            "ruleId": "FOOD_NOT_EXPIRED",
            "appliesTo": "FoodItem",
            "lineItemSources": [
                {"documentType": "Packing_List", "documentTypeId": "48"},
                {"documentType": "Invoice", "documentTypeId": "50"},
            ],
        },
        {
            "ruleId": "ISSUE_DATE_NOT_IN_FUTURE",
            "appliesTo": [
                {"documentType": "Health_License", "documentTypeId": "40"}
            ],
        },
        {
            "ruleId": "CERTIFICATE_NOT_EXPIRED",
            "appliesTo": [
                {"documentType": "Health_License", "documentTypeId": "40"}
            ],
        },
    ],
}


def _payload_item(expiry: str | None, serial: int = 1) -> dict:
    return {"itemCode": f"IT{serial}", "serial": serial, "itemType": "food", "expiryDate": expiry}


def _submission_doc(doc_type: str, doc_id: str, fields: dict) -> dict:
    return {"document": doc_type, "documentTypeId": doc_id, "fields": fields, "lineItems": []}


class TestFoodNotExpired:
    def test_future_expiry_passes(self):
        payload = {"items": [_payload_item(_iso(TOMORROW))]}
        findings = validate_logical_rules(LOGICAL_RULE, payload, [])
        food_findings = [f for f in findings if f.get("ruleCode") == "FOOD_NOT_EXPIRED"]
        assert food_findings == []

    def test_expired_item_fails(self):
        payload = {"items": [_payload_item(_iso(YESTERDAY))]}
        findings = validate_logical_rules(LOGICAL_RULE, payload, [])
        food_findings = [f for f in findings if f.get("ruleCode") == "FOOD_NOT_EXPIRED"]
        assert len(food_findings) == 1
        assert food_findings[0]["result"] == "FAIL"

    def test_today_counts_as_expired(self):
        payload = {"items": [_payload_item(_iso(TODAY))]}
        findings = validate_logical_rules(LOGICAL_RULE, payload, [])
        food_findings = [f for f in findings if f.get("ruleCode") == "FOOD_NOT_EXPIRED"]
        assert len(food_findings) == 1
        assert food_findings[0]["result"] == "FAIL"

    def test_null_expiry_warns(self):
        payload = {"items": [_payload_item(None)]}
        findings = validate_logical_rules(LOGICAL_RULE, payload, [])
        food_findings = [f for f in findings if f.get("ruleCode") == "FOOD_NOT_EXPIRED"]
        assert len(food_findings) == 1
        assert food_findings[0]["result"] == "WARN"


class TestIssueDateNotInFuture:
    def test_past_issue_date_passes(self):
        sub = [_submission_doc("Health_License", "40", {
            "issue_date": {"value": _iso(LAST_YEAR), "confidence": 0.9}
        })]
        findings = validate_logical_rules(LOGICAL_RULE, {"items": []}, sub)
        assert not any(f["ruleCode"] == "ISSUE_DATE_NOT_IN_FUTURE" for f in findings)

    def test_future_issue_date_fails(self):
        sub = [_submission_doc("Health_License", "40", {
            "issue_date": {"value": _iso(NEXT_YEAR), "confidence": 0.9}
        })]
        findings = validate_logical_rules(LOGICAL_RULE, {"items": []}, sub)
        issue_findings = [f for f in findings if f["ruleCode"] == "ISSUE_DATE_NOT_IN_FUTURE"]
        assert len(issue_findings) == 1
        assert issue_findings[0]["result"] == "FAIL"


class TestCertificateNotExpired:
    def test_future_expiry_passes(self):
        sub = [_submission_doc("Health_License", "40", {
            "expiry_date": {"value": _iso(NEXT_YEAR), "confidence": 0.9}
        })]
        findings = validate_logical_rules(LOGICAL_RULE, {"items": []}, sub)
        assert not any(f["ruleCode"] == "CERTIFICATE_NOT_EXPIRED" for f in findings)

    def test_expired_cert_fails(self):
        sub = [_submission_doc("Health_License", "40", {
            "expiry_date": {"value": _iso(LAST_YEAR), "confidence": 0.9}
        })]
        findings = validate_logical_rules(LOGICAL_RULE, {"items": []}, sub)
        exp_findings = [f for f in findings if f["ruleCode"] == "CERTIFICATE_NOT_EXPIRED"]
        assert len(exp_findings) == 1
        assert exp_findings[0]["result"] == "FAIL"
