"""Unit tests for category-based rule dispatch in rule_executor.

Covers the registry contract that lets a template declare only the rule
categories it needs, in any order, without platform code changes.
"""

import asyncio
from unittest.mock import patch

from src.platform.policy.rule_executor import (
    CATEGORY_EXPECTED_VALUE,
    CATEGORY_ITEM_RECONCILIATION,
    CATEGORY_SIGNATURE_STAMP,
    DEFAULT_EVALUATION_ORDER,
    EVALUATOR_REGISTRY,
    group_rules_by_category,
    rule_category,
    run_rules,
)

EXPECTED_VALUE_RULE = {
    "id": "EXPECTED_VALUE_RULES",
    "category": CATEGORY_EXPECTED_VALUE,
    "expectedValue": "7",
    "documentType": "Permit",
    "fieldName": "authority_id",
}

ITEM_RULE = {"id": "ITEM_RECONCILIATION_RULES", "category": CATEGORY_ITEM_RECONCILIATION}

SIGNATURE_RULE = {
    "id": "SIGNATURE_STAMP_RULES",
    "category": CATEGORY_SIGNATURE_STAMP,
    "requiredSignatureDocs": [],
    "informationalSignatureDocs": [],
}


def _run(rules_list, **kwargs):
    return asyncio.run(
        run_rules(
            rules_list=rules_list,
            payload={"requestId": "R1", "items": []},
            submission=[],
            **kwargs,
        )
    )


class TestRuleCategory:
    def test_explicit_category_wins(self):
        assert rule_category({"id": "ANYTHING", "category": "Custom"}) == "Custom"

    def test_falls_back_to_legacy_rule_id(self):
        assert rule_category({"id": "SIGNATURE_STAMP_RULES"}) == CATEGORY_SIGNATURE_STAMP

    def test_pre_rename_rule_ids_still_dispatch(self):
        assert rule_category({"id": "AGENCY_CODE_RULES"}) == CATEGORY_EXPECTED_VALUE
        assert rule_category({"id": "LOGICAL_RULES"}) == "TemporalValidity"

    def test_unknown_uncategorised_rule_returns_none(self):
        assert rule_category({"id": "SOMETHING_ELSE"}) is None


class TestGroupRulesByCategory:
    def test_groups_multiple_rules_under_one_category(self):
        rules = [
            {"id": "A", "category": "Shared"},
            {"id": "B", "category": "Shared"},
            {"id": "C", "category": "Other"},
        ]
        grouped = group_rules_by_category(rules)
        assert [r["id"] for r in grouped["Shared"]] == ["A", "B"]
        assert [r["id"] for r in grouped["Other"]] == ["C"]

    def test_uncategorised_rules_are_excluded(self):
        assert group_rules_by_category([{"id": "NO_CATEGORY_HERE"}]) == {}


class TestDispatch:
    def test_evaluator_runs_only_when_its_category_is_present(self):
        with patch(
            "src.platform.policy.rule_executor.validate_line_items", return_value=[]
        ) as item_check:
            _run([ITEM_RULE])
        item_check.assert_called_once()

    def test_item_reconciliation_is_skippable(self):
        """Regression: this step previously ran unconditionally."""
        with patch(
            "src.platform.policy.rule_executor.validate_line_items", return_value=[]
        ) as item_check:
            _run([EXPECTED_VALUE_RULE])
        item_check.assert_not_called()

    def test_reference_data_category_is_ignored(self):
        reference_rule = {"id": "SOME_CODE_LIST", "category": "ConditionalDocuments"}
        assert _run([reference_rule]) == []

    def test_evaluation_order_is_configurable(self):
        calls: list[str] = []

        def _record(name):
            def _evaluator(rules, ctx):
                calls.append(name)
                return []
            return _evaluator

        registry = {
            CATEGORY_EXPECTED_VALUE: _record(CATEGORY_EXPECTED_VALUE),
            CATEGORY_SIGNATURE_STAMP: _record(CATEGORY_SIGNATURE_STAMP),
        }
        with patch.dict(EVALUATOR_REGISTRY, registry, clear=False):
            _run(
                [EXPECTED_VALUE_RULE, SIGNATURE_RULE],
                evaluation_order=(CATEGORY_SIGNATURE_STAMP, CATEGORY_EXPECTED_VALUE),
            )
        assert calls == [CATEGORY_SIGNATURE_STAMP, CATEGORY_EXPECTED_VALUE]

    def test_one_failing_evaluator_does_not_stop_the_rest(self):
        def _boom(rules, ctx):
            raise RuntimeError("evaluator exploded")

        marker = [{"ruleCode": "REACHED", "result": "PASS"}]
        with patch.dict(
            EVALUATOR_REGISTRY,
            {
                CATEGORY_EXPECTED_VALUE: _boom,
                CATEGORY_SIGNATURE_STAMP: lambda rules, ctx: marker,
            },
            clear=False,
        ):
            findings = _run([EXPECTED_VALUE_RULE, SIGNATURE_RULE])
        assert [f["ruleCode"] for f in findings] == ["REACHED"]


class TestRegistryContract:
    def test_every_ordered_category_has_an_evaluator(self):
        missing = [c for c in DEFAULT_EVALUATION_ORDER if c not in EVALUATOR_REGISTRY]
        assert missing == []

    def test_every_registered_evaluator_is_ordered(self):
        unordered = sorted(set(EVALUATOR_REGISTRY) - set(DEFAULT_EVALUATION_ORDER))
        assert unordered == []
