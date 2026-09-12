"""Unit tests for src/platform/policy/rule_executor.py — deterministic helpers."""

import asyncio
from typing import ClassVar
from unittest.mock import patch

from src.platform.policy.rule_executor import (
    _find_rule,
    run_rules,
)


class TestFindRule:
    RULES: ClassVar[list] = [
        {"id": "MANDATORY_DOC_RULES", "data": "mandatory"},
        {"id": "CROSS_DOC_RULES", "data": "cross_doc"},
    ]

    def test_found(self):
        result = _find_rule(self.RULES, "MANDATORY_DOC_RULES")
        assert result is not None
        assert result["data"] == "mandatory"

    def test_not_found(self):
        assert _find_rule(self.RULES, "NONEXISTENT") is None

    def test_empty_list(self):
        assert _find_rule([], "MANDATORY_DOC_RULES") is None


class TestRunRules:
    """Integration-style tests with mocked individual validators."""

    AGENCY_RULE: ClassVar[dict] = {
        "id": "AGENCY_CODE_RULES",
        "expectedValue": "7",
        "documentType": "Permit",
        "fieldName": "authority_id",
    }

    def _run(self, rules_list, payload, submission):
        return asyncio.run(
            run_rules(rules_list=rules_list, payload=payload, submission=submission)
        )

    def test_empty_rules_list_runs_no_evaluators(self):
        with patch("src.platform.policy.rule_executor.validate_expected_value") as agency, \
             patch("src.platform.policy.rule_executor.validate_line_items") as item_check:
            findings = self._run(
                rules_list=[],
                payload={"requestId": "R1", "items": []},
                submission=[],
            )
        assert findings == []
        agency.assert_not_called()
        item_check.assert_not_called()

    def test_confidence_cutoff_drops_low_confidence_findings(self):
        low_conf_finding = {
            "ruleCode": "TEST_RULE",
            "result": "FAIL",
            "message": "test",
            "confidence": 0.1,
        }
        high_conf_finding = {
            "ruleCode": "TEST_RULE_2",
            "result": "PASS",
            "message": "test2",
            "confidence": 0.9,
        }
        with patch("src.platform.policy.rule_executor.validate_expected_value", return_value=[low_conf_finding, high_conf_finding]), \
             patch("src.platform.policy.rule_executor.validate_line_items", return_value=[]):
            findings = self._run(
                [self.AGENCY_RULE], {"requestId": "R1", "items": []}, []
            )
        codes = [f["ruleCode"] for f in findings]
        assert "TEST_RULE" not in codes      # dropped (0.1 < 0.5)
        assert "TEST_RULE_2" in codes        # kept

    def test_rule_id_copied_to_rule_code(self):
        finding_with_only_rule_id = {
            "ruleId": "SOME_RULE",
            "result": "WARN",
            "message": "test",
        }
        with patch("src.platform.policy.rule_executor.validate_expected_value", return_value=[finding_with_only_rule_id]), \
             patch("src.platform.policy.rule_executor.validate_line_items", return_value=[]):
            findings = self._run(
                [self.AGENCY_RULE], {"requestId": "R1", "items": []}, []
            )
        assert findings[0]["ruleCode"] == "SOME_RULE"

    def test_agency_code_read_from_agency_code_rules(self):
        """AGENCY_CODE_RULES doc supplies the agency code instead of hardcoded '2'."""
        captured = {}

        def capturing_validator(submission, expected_value, **config):
            captured.update(expected_value=expected_value, **config)
            return []

        with patch("src.platform.policy.rule_executor.validate_expected_value", side_effect=capturing_validator), \
             patch("src.platform.policy.rule_executor.validate_line_items", return_value=[]):
            self._run(
                rules_list=[{
                    "id": "AGENCY_CODE_RULES",
                    "expectedValue": "7",
                    "documentType": "Permit",
                    "fieldName": "authority_id",
                }],
                payload={"requestId": "R1", "items": []},
                submission=[],
            )
        assert captured["expected_value"] == "7"
        assert captured["document_type"] == "Permit"
        assert captured["field_name"] == "authority_id"

    def test_allowed_fields_forwarded_to_min_fields(self):
        """allowed_fields_by_doc parameter is passed through to validate_min_fields."""
        captured = {}

        def capturing_min_fields(rules_input, submission, allowed_fields_by_doc=None):
            captured["allowed_fields_by_doc"] = allowed_fields_by_doc
            return []

        rules_list = [{"id": "MIN_FIELDS_RULES", "minimumFieldsByDocuments": []}]
        allowed = {"Invoice": ["invoice_number"]}

        with patch("src.platform.policy.rule_executor.validate_expected_value", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_line_items", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_min_fields", side_effect=capturing_min_fields):
            self._run(rules_list, {"requestId": "R1", "items": []}, [])

        # Without passing allowed_fields_by_doc to run_rules: it defaults to None
        # Test that the plumbing works when explicitly provided
        captured.clear()

        async def _run_with_param():
            return await run_rules(
                rules_list=rules_list,
                payload={"requestId": "R1", "items": []},
                submission=[],
                allowed_fields_by_doc=allowed,
            )

        with patch("src.platform.policy.rule_executor.validate_expected_value", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_line_items", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_min_fields", side_effect=capturing_min_fields):
            asyncio.run(_run_with_param())

        assert captured["allowed_fields_by_doc"] == allowed
