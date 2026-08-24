"""
Integration test: same rule evaluation produces identical findings on the reference case.

Loads templates/food-safety/rules.json and runs run_rules() against the reference
payload (cosmos_seed_data/payload.json) with a minimal submission (documents present
but empty fields). Verifies the deterministic findings match expected values.

This is the acceptance criterion: "Same rule evaluation produces identical findings
on the reference case."
"""

import asyncio
import json
from pathlib import Path

import pytest

from src.platform.policy.rule_executor import run_rules

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).resolve().parent.parent.parent
RULES_JSON = WORKSPACE / "templates" / "food-safety" / "rules.json"
PAYLOAD_JSON = WORKSPACE / "pafn-inspection-agent" / "cosmos_seed_data" / "payload.json"


@pytest.fixture(scope="module")
def food_safety_rules() -> list:
    with open(RULES_JSON, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reference_payload() -> dict:
    with open(PAYLOAD_JSON, encoding="utf-8") as f:
        return json.load(f)


def _minimal_submission(payload: dict) -> list:
    """Build a submission with all declared documents but empty fields."""
    return [
        {
            "documentTypeId": doc["documentTypeId"],
            "document": doc["documentType"],
            "fields": {},
            "lineItems": [],
        }
        for doc in payload.get("documents", [])
    ]


def _run_rules_sync(rules_list, payload, submission) -> list:
    return asyncio.get_event_loop().run_until_complete(
        run_rules(rules_list=rules_list, payload=payload, submission=submission)
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRulesJsonLoads:
    def test_rules_json_is_valid_list(self, food_safety_rules):
        assert isinstance(food_safety_rules, list)
        assert len(food_safety_rules) > 0

    def test_all_required_rule_ids_present(self, food_safety_rules):
        rule_ids = {r["id"] for r in food_safety_rules}
        expected = {
            "AGENCY_CODE_RULES",
            "MANDATORY_DOC_RULES",
            "MIN_FIELDS_RULES",
            "REJECTED_HS_CODES",
            "PAFN_HS_CODES",
            "HALAL_HS_CODES",
            "FISH_HS_CODES",
            "SHRIMP_HS_CODES",
            "SIGNATURE_STAMP_RULES",
            "CROSS_DOC_RULES",
            "LOGICAL_RULES",
        }
        missing = expected - rule_ids
        assert not missing, f"Missing rule IDs in rules.json: {missing}"

    def test_agency_code_rules_has_agency_code(self, food_safety_rules):
        rule = next(r for r in food_safety_rules if r["id"] == "AGENCY_CODE_RULES")
        assert rule["agencyCode"] == "2"


class TestReferenceCase:
    """Reference case: 2-item frozen chicken shipment with 5 documents.

    Expected deterministic findings:
    - AGENCY_CODE_MISSING: Declaration_Document has no agency_code field (empty fields)
    - MANDATORY_DOC_MISSING: Many mandatory docs are missing from the 5-doc submission
    - HS code 1602.90.10.00.00 should be in PAFN codes (chapter 16) → no PAFN rejection
    - No REJECTED_HS_CODE for chapter 16
    - FOOD_NOT_EXPIRED: items have future expiry dates → should PASS or WARN (no FAIL)
    """

    def test_run_rules_returns_list(self, food_safety_rules, reference_payload):
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        assert isinstance(findings, list)

    def test_mandatory_docs_missing(self, food_safety_rules, reference_payload):
        """Reference payload has only 5 docs; mandatory list requires ~10."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        mandatory_missing = [f for f in findings if f.get("ruleCode") == "MANDATORY_DOC_MISSING"]
        # At minimum, docs like House_Bill, Delivery_Orders, Packing_List etc. are missing
        assert len(mandatory_missing) > 0, "Expected MANDATORY_DOC_MISSING findings for absent docs"

    def test_chicken_hs_code_not_rejected(self, food_safety_rules, reference_payload):
        """HS code 1602.90.10.00.00 (processed chicken) should not be in the rejected list."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        rejected = [f for f in findings if f.get("ruleCode") == "REJECTED_HS_CODE"]
        assert rejected == [], f"Unexpected REJECTED_HS_CODE findings: {rejected}"

    def test_chicken_hs_code_is_valid_pafn_code(self, food_safety_rules, reference_payload):
        """HS code 1602.x should match PAFN chapter 16 prefix → no NON_PAFN_HS_CODE."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        non_pafn = [f for f in findings if f.get("ruleCode") == "NON_PAFN_HS_CODE"]
        assert non_pafn == [], f"Unexpected NON_PAFN_HS_CODE findings: {non_pafn}"

    def test_food_items_have_future_expiry_dates(self, food_safety_rules, reference_payload):
        """Reference payload has future expiry dates → FOOD_NOT_EXPIRED should not FAIL."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        food_fail = [f for f in findings if f.get("ruleCode") == "FOOD_NOT_EXPIRED" and f.get("result") == "FAIL"]
        # Items have expiryDate 2027-02-04 and 2027-02-07 — should not be expired
        assert food_fail == [], f"Unexpected FOOD_NOT_EXPIRED FAIL findings: {food_fail}"

    def test_all_findings_have_rule_code(self, food_safety_rules, reference_payload):
        """Post-normalization: every finding must have ruleCode."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        missing_code = [f for f in findings if not f.get("ruleCode")]
        assert missing_code == [], f"Findings without ruleCode: {missing_code}"

    def test_all_findings_have_result(self, food_safety_rules, reference_payload):
        """Every finding must have a result field."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        missing_result = [f for f in findings if not f.get("result")]
        assert missing_result == [], f"Findings without result: {missing_result}"

    def test_halal_cert_required_for_chicken(self, food_safety_rules, reference_payload):
        """HS code 1602.90.10 matches HALAL_HS_CODES chapter 16 → Halal cert required."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        halal_missing = [
            f for f in findings
            if f.get("ruleCode") == "MANDATORY_DOC_MISSING"
            and "Halal" in f.get("documentType", "")
        ]
        assert len(halal_missing) > 0, (
            "Expected MANDATORY_DOC_MISSING for Halal_Slaughter_Certificate "
            "given HS code 1602.90.10.00.00 matches HALAL_HS_CODES"
        )
