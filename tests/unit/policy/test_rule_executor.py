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
        "agencyCode": "7",
        "documentType": "Permit",
        "fieldName": "authority_id",
    }

    def _run(self, rules_list, payload, submission):
        return asyncio.run(
            run_rules(rules_list=rules_list, payload=payload, submission=submission)
        )

    def test_empty_rules_list_only_runs_item_check_and_agency(self):
        with patch("src.platform.policy.rule_executor.validate_agency_code", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_item_checks", return_value=[]):
            findings = self._run(
                rules_list=[],
                payload={"requestId": "R1", "items": []},
                submission=[],
            )
        assert isinstance(findings, list)

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
        with patch("src.platform.policy.rule_executor.validate_agency_code", return_value=[low_conf_finding, high_conf_finding]), \
             patch("src.platform.policy.rule_executor.validate_item_checks", return_value=[]):
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
        with patch("src.platform.policy.rule_executor.validate_agency_code", return_value=[finding_with_only_rule_id]), \
             patch("src.platform.policy.rule_executor.validate_item_checks", return_value=[]):
            findings = self._run(
                [self.AGENCY_RULE], {"requestId": "R1", "items": []}, []
            )
        assert findings[0]["ruleCode"] == "SOME_RULE"

    def test_agency_code_read_from_agency_code_rules(self):
        """AGENCY_CODE_RULES doc supplies the agency code instead of hardcoded '2'."""
        captured = {}

        def capturing_validator(submission, agency_code, **config):
            captured.update(agency_code=agency_code, **config)
            return []

        with patch("src.platform.policy.rule_executor.validate_agency_code", side_effect=capturing_validator), \
             patch("src.platform.policy.rule_executor.validate_item_checks", return_value=[]):
            self._run(
                rules_list=[{
                    "id": "AGENCY_CODE_RULES",
                    "agencyCode": "7",
                    "documentType": "Permit",
                    "fieldName": "authority_id",
                }],
                payload={"requestId": "R1", "items": []},
                submission=[],
            )
        assert captured["agency_code"] == "7"
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

        with patch("src.platform.policy.rule_executor.validate_agency_code", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_item_checks", return_value=[]), \
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

        with patch("src.platform.policy.rule_executor.validate_agency_code", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_item_checks", return_value=[]), \
             patch("src.platform.policy.rule_executor.validate_min_fields", side_effect=capturing_min_fields):
            asyncio.run(_run_with_param())

        assert captured["allowed_fields_by_doc"] == allowed
