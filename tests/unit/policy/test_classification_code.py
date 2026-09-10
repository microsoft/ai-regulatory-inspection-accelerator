"""Unit tests for src/platform/policy/evaluators/classification_code.py"""

from typing import ClassVar

from src.platform.policy.evaluators.classification_code import (
    _normalize_code,
    check_denied_code,
    check_in_scope_code,
    validate_classification_codes,
)


class TestNormalizeCode:
    def test_strips_separators_and_trailing_padding(self):
        assert _normalize_code("1602.90.10.00.00") == "16029010"

    def test_strips_separators_only(self):
        assert _normalize_code("0302.11") == "030211"

    def test_empty_returns_zero(self):
        assert _normalize_code("") == "0"

    def test_padding_segment_is_configurable(self):
        assert _normalize_code("A1-B2-XX", separator="-", padding_segment="XX") == "A1B2"

    def test_padding_stripping_can_be_disabled(self):
        assert _normalize_code("1602.00", padding_segment=None) == "160200"


class TestCheckDeniedCode:
    LOOKUP: ClassVar[list] = [("0301", {"code": "0301", "sectionDescription": "S", "chapterDescription": "C", "description": "D"})]

    def test_match_returns_finding(self):
        findings = check_denied_code("0301.10.00", "ITEM1", self.LOOKUP)
        assert len(findings) == 1
        assert findings[0]["ruleCode"] == "DENIED_CLASSIFICATION_CODE"
        assert findings[0]["result"] == "FAIL"

    def test_no_match_returns_empty(self):
        findings = check_denied_code("1602.90.10", "ITEM1", self.LOOKUP)
        assert findings == []

    def test_prefix_match(self):
        # 0301.99 starts with 0301 → match
        findings = check_denied_code("0301.99.00", "ITEM1", self.LOOKUP)
        assert len(findings) == 1


class TestCheckInScopeCode:
    IN_SCOPE_LOOKUP: ClassVar[set] = {"16029010", "0203"}

    def test_valid_code_passes(self):
        findings = check_in_scope_code(
            "1602.90.10.00", "ITEM1", self.IN_SCOPE_LOOKUP
        )
        assert findings == []

    def test_invalid_code_fails(self):
        findings = check_in_scope_code(
            "0901.21", "ITEM1", self.IN_SCOPE_LOOKUP, "OUTSIDE_SCOPE"
        )
        assert len(findings) == 1
        assert findings[0]["ruleCode"] == "OUTSIDE_SCOPE"

    def test_empty_in_scope_lookup_skips(self):
        findings = check_in_scope_code("1602.90", "ITEM1", set())
        assert findings == []


class TestValidateClassificationCodes:
    RULES: ClassVar[dict] = {
        "codeField": "hsCode",
        "deniedCodes": [
            {"code": "0301", "sectionDescription": "S", "chapterDescription": "C", "description": "D"}
        ],
        "inScopeCodes": [{"code": "16"}, {"code": "02"}],
        "outOfScopeRuleCode": "NON_FOOD_SAFETY_HS_CODE",
    }

    def test_denied_code_in_payload(self):
        payload = {"items": [{"hsCode": "0301.10.00", "itemCode": "IT1"}]}
        findings = validate_classification_codes(self.RULES, payload)
        assert any(f["ruleCode"] == "DENIED_CLASSIFICATION_CODE" for f in findings)

    def test_out_of_scope_code_in_payload(self):
        payload = {"items": [{"hsCode": "0901.21", "itemCode": "IT1"}]}
        findings = validate_classification_codes(self.RULES, payload)
        assert any(f["ruleCode"] == "NON_FOOD_SAFETY_HS_CODE" for f in findings)

    def test_valid_code_no_finding(self):
        payload = {"items": [{"hsCode": "1602.90.10", "itemCode": "IT1"}]}
        findings = validate_classification_codes(self.RULES, payload)
        assert findings == []

    def test_empty_payload_no_findings(self):
        assert validate_classification_codes(self.RULES, {"items": []}) == []

    def test_code_field_is_configurable(self):
        rules = {**self.RULES, "codeField": "diagnosisCode"}
        payload = {"items": [{"diagnosisCode": "0301.10", "itemCode": "IT1"}]}
        findings = validate_classification_codes(rules, payload)
        assert any(f["ruleCode"] == "DENIED_CLASSIFICATION_CODE" for f in findings)
