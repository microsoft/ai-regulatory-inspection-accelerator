"""Unit tests for src/platform/policy/evaluators/hs_code.py"""

from typing import ClassVar

from src.platform.policy.evaluators.hs_code import (
    _normalize_hs,
    check_jurisdiction_hs_code,
    check_rejected_hs_code,
    validate_hs_codes,
)


class TestNormalizeHs:
    def test_strips_dots_and_trailing_zeros(self):
        assert _normalize_hs("1602.90.10.00.00") == "16029010"

    def test_strips_dots_only(self):
        assert _normalize_hs("0302.11") == "030211"

    def test_empty_returns_zero(self):
        assert _normalize_hs("") == "0"


class TestCheckRejectedHsCode:
    LOOKUP: ClassVar[list] = [("0301", {"hsCode": "0301", "sectionDescription": "S", "chapterDescription": "C", "hsdescription": "D"})]

    def test_match_returns_finding(self):
        findings = check_rejected_hs_code("0301.10.00", "ITEM1", self.LOOKUP)
        assert len(findings) == 1
        assert findings[0]["ruleCode"] == "REJECTED_HS_CODE"
        assert findings[0]["result"] == "FAIL"

    def test_no_match_returns_empty(self):
        findings = check_rejected_hs_code("1602.90.10", "ITEM1", self.LOOKUP)
        assert findings == []

    def test_prefix_match(self):
        # 0301.99 starts with 0301 → match
        findings = check_rejected_hs_code("0301.99.00", "ITEM1", self.LOOKUP)
        assert len(findings) == 1


class TestCheckJurisdictionHsCode:
    JURISDICTION_LOOKUP: ClassVar[set] = {"16029010", "0203"}

    def test_valid_code_passes(self):
        findings = check_jurisdiction_hs_code(
            "1602.90.10.00", "ITEM1", self.JURISDICTION_LOOKUP
        )
        assert findings == []

    def test_invalid_code_fails(self):
        findings = check_jurisdiction_hs_code(
            "0901.21", "ITEM1", self.JURISDICTION_LOOKUP, "OUTSIDE_SCOPE"
        )
        assert len(findings) == 1
        assert findings[0]["ruleCode"] == "OUTSIDE_SCOPE"

    def test_empty_jurisdiction_lookup_skips(self):
        findings = check_jurisdiction_hs_code("1602.90", "ITEM1", set())
        assert findings == []


class TestValidateHsCodes:
    RULES: ClassVar[dict] = {
        "rejectedCodes": [
            {"hsCode": "0301", "sectionDescription": "S", "chapterDescription": "C", "hsdescription": "D"}
        ],
        "jurisdictionCodes": [{"hsCode": "16"}, {"hsCode": "02"}],
        "outsideJurisdictionRuleCode": "NON_FOOD_SAFETY_HS_CODE",
    }

    def test_rejected_code_in_payload(self):
        payload = {"items": [{"hsCode": "0301.10.00", "itemCode": "IT1"}]}
        findings = validate_hs_codes(self.RULES, payload)
        assert any(f["ruleCode"] == "REJECTED_HS_CODE" for f in findings)

    def test_outside_jurisdiction_code_in_payload(self):
        payload = {"items": [{"hsCode": "0901.21", "itemCode": "IT1"}]}
        findings = validate_hs_codes(self.RULES, payload)
        assert any(f["ruleCode"] == "NON_FOOD_SAFETY_HS_CODE" for f in findings)

    def test_valid_code_no_finding(self):
        payload = {"items": [{"hsCode": "1602.90.10", "itemCode": "IT1"}]}
        findings = validate_hs_codes(self.RULES, payload)
        assert findings == []

    def test_empty_payload_no_findings(self):
        assert validate_hs_codes(self.RULES, {"items": []}) == []
