"""Unit tests for src/platform/policy/evaluators/line_item_reconciliation.py

The rule below is deliberately domain-neutral: it proves the evaluator carries no
knowledge of weights, shipments or any other vertical.
"""

from typing import ClassVar

from src.platform.policy.evaluators.line_item_reconciliation import (
    _derive_value,
    validate_line_items,
)

RULE: ClassVar[dict] = {
    "id": "ITEM_RECONCILIATION_RULES",
    "lineItemSources": ["Estimate", "Schedule"],
    "labelFields": ["line_description"],
    "tolerances": {"default": 0.02, "conditional": 0.05},
    "derivedValues": [
        {
            "name": "totalAmount",
            "operator": "product",
            "round": 2,
            "operands": [
                {"attribute": "unitCount"},
                {"attribute": "unitAmount", "unitAttribute": "amountUnit",
                 "defaultUnit": "major", "unitMultipliers": {"minor": 0.01, "major": 1}},
            ],
        }
    ],
    "sanityChecks": [
        {"id": "LINE_AMOUNT_MISSING", "attribute": "unitAmount", "check": "required", "label": "unit amount"},
        {"id": "LINE_AMOUNT_INVALID", "derived": "totalAmount", "check": "positive", "label": "total amount"},
        {"id": "LINE_AMOUNT_MAX", "derived": "totalAmount", "check": "maximum", "value": 100000.0, "label": "total amount"},
    ],
    "comparisons": [
        {
            "id": "LINE_COUNT",
            "type": "numeric",
            "declared": {"attribute": "unitCount"},
            "extracted": {"fields": ["quantity"]},
        },
        {
            "id": "LINE_AMOUNT",
            "type": "numeric",
            "declared": {"derived": "totalAmount"},
            "extracted": {"fields": ["amount"]},
            "conditionalTolerance": True,
        },
        {
            "id": "LINE_DATE",
            "type": "date",
            "declared": {"attribute": "serviceDate"},
            "extracted": {"fields": ["service_date"]},
        },
        {
            "id": "LINE_ORIGIN",
            "type": "country",
            "declared": {"attribute": "jurisdiction"},
            "extracted": {"fields": ["jurisdiction"]},
        },
    ],
}


def _li(**fields) -> dict:
    return {k: {"value": v, "confidence": 0.99} for k, v in fields.items()}


def _doc(name: str, line_items: list, fields: dict | None = None) -> dict:
    return {
        "document": name,
        "documentTypeId": name,
        "fields": {k: {"value": v} for k, v in (fields or {}).items()},
        "lineItems": line_items,
    }


def _item(**kwargs) -> dict:
    base = {"itemCode": "IT1", "serial": 1, "unitCount": 10, "unitAmount": 5, "amountUnit": "major"}
    base.update(kwargs)
    return base


class TestDerivedValues:
    def test_product_with_unit_multiplier(self):
        spec = RULE["derivedValues"][0]
        assert _derive_value(_item(), spec) == 50.0

    def test_minor_unit_is_scaled(self):
        spec = RULE["derivedValues"][0]
        assert _derive_value(_item(amountUnit="minor"), spec) == 0.5

    def test_default_is_used_for_absent_operand(self):
        spec = {
            "name": "x", "operator": "product",
            "operands": [{"attribute": "unitCount"}, {"attribute": "missing", "default": 3}],
        }
        assert _derive_value(_item(), spec) == 30.0

    def test_missing_operand_without_default_yields_none(self):
        spec = {"name": "x", "operator": "product", "operands": [{"attribute": "absent"}]}
        assert _derive_value(_item(), spec) is None

    def test_unsupported_operator_yields_none(self):
        spec = {"name": "x", "operator": "power", "operands": [{"attribute": "unitCount"}]}
        assert _derive_value(_item(), spec) is None


class TestComparisons:
    def test_matching_values_produce_no_findings(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="50")])]
        assert validate_line_items(RULE, {"items": [_item()]}, submission) == []

    def test_numeric_mismatch_fails(self):
        submission = [_doc("Estimate", [_li(quantity="12", amount="50")])]
        findings = validate_line_items(RULE, {"items": [_item()]}, submission)
        assert [f["ruleCode"] for f in findings] == ["LINE_COUNT_001"]
        assert findings[0]["result"] == "FAIL"

    def test_within_tolerance_passes(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="50.5")])]
        assert validate_line_items(RULE, {"items": [_item()]}, submission) == []

    def test_conditional_tolerance_yields_conditional_pass(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="52")])]
        findings = validate_line_items(RULE, {"items": [_item()]}, submission)
        assert findings[0]["ruleCode"] == "LINE_AMOUNT_001"
        assert findings[0]["result"] == "CONDITIONAL_PASS"

    def test_date_mismatch_fails(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="50", service_date="2026-01-02")])]
        findings = validate_line_items(
            RULE, {"items": [_item(serviceDate="2026-01-01")]}, submission
        )
        assert findings[0]["ruleCode"] == "LINE_DATE_001"

    def test_country_comparison_normalizes_aliases(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="50", jurisdiction="USA")])]
        findings = validate_line_items(
            RULE, {"items": [_item(jurisdiction="United States")]}, submission
        )
        assert findings == []

    def test_serial_selects_the_line_item(self):
        submission = [_doc("Estimate", [
            _li(quantity="10", amount="50"),
            _li(quantity="99", amount="50"),
        ])]
        findings = validate_line_items(RULE, {"items": [_item(serial=2)]}, submission)
        assert findings[0]["ruleCode"] == "LINE_COUNT_002"


class TestSourceSelection:
    def test_first_available_source_wins(self):
        submission = [
            _doc("Schedule", [_li(quantity="99", amount="50")]),
            _doc("Estimate", [_li(quantity="10", amount="50")]),
        ]
        assert validate_line_items(RULE, {"items": [_item()]}, submission) == []

    def test_no_source_document_yields_no_findings(self):
        submission = [_doc("Unrelated", [_li(quantity="99")])]
        assert validate_line_items(RULE, {"items": [_item()]}, submission) == []

    def test_no_items_yields_no_findings(self):
        submission = [_doc("Estimate", [_li(quantity="10")])]
        assert validate_line_items(RULE, {"items": []}, submission) == []


class TestSanityChecks:
    def test_required_attribute_missing(self):
        submission = [_doc("Estimate", [_li(quantity="10")])]
        item = _item()
        del item["unitAmount"]
        findings = validate_line_items(RULE, {"items": [item]}, submission)
        assert "LINE_AMOUNT_MISSING_001" in [f["ruleCode"] for f in findings]

    def test_non_positive_derived_value(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="0")])]
        findings = validate_line_items(RULE, {"items": [_item(unitAmount=0)]}, submission)
        assert "LINE_AMOUNT_INVALID_001" in [f["ruleCode"] for f in findings]

    def test_maximum_bound_exceeded(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="999999999")])]
        findings = validate_line_items(
            RULE, {"items": [_item(unitCount=1000000, unitAmount=1000)]}, submission
        )
        assert "LINE_AMOUNT_MAX_001" in [f["ruleCode"] for f in findings]


class TestAggregateAndCrossDocument:
    AGG_RULE: ClassVar[dict] = {
        **RULE,
        "aggregate": {"id": "LINE_TOTAL", "derived": "totalAmount", "fields": ["declared_total"]},
    }

    def test_aggregate_mismatch_fails(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="50")], {"declared_total": "999"})]
        findings = validate_line_items(self.AGG_RULE, {"items": [_item()]}, submission)
        assert "LINE_TOTAL" in [f["ruleCode"] for f in findings]

    def test_aggregate_match_passes(self):
        submission = [_doc("Estimate", [_li(quantity="10", amount="50")], {"declared_total": "50"})]
        findings = validate_line_items(self.AGG_RULE, {"items": [_item()]}, submission)
        assert "LINE_TOTAL" not in [f["ruleCode"] for f in findings]

    def test_cross_document_deviation_is_reported(self):
        rule = {
            **RULE,
            "crossDocumentComparison": {
                "id": "LINE_XDOC", "derived": "totalAmount", "fields": ["amount"]
            },
        }
        submission = [
            _doc("Estimate", [_li(quantity="10", amount="50")]),
            _doc("Schedule", [_li(quantity="10", amount="80")]),
        ]
        findings = validate_line_items(rule, {"items": [_item()]}, submission)
        assert "LINE_XDOC_001" in [f["ruleCode"] for f in findings]
