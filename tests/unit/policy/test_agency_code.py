"""Unit tests for src/platform/policy/evaluators/agency_code.py"""

from src.platform.policy.evaluators.agency_code import validate_agency_code


def _submission(agency_codes_in_line_items=None, top_level_value=None, doc_type="Declaration_Document"):
    line_items = []
    if agency_codes_in_line_items:
        for code in agency_codes_in_line_items:
            line_items.append({"agency_code": {"value": code, "confidence": 0.9}})
    fields = {}
    if top_level_value is not None:
        fields["agency_code"] = {"value": top_level_value, "confidence": 0.9}
    return [{"document": doc_type, "documentTypeId": "20", "fields": fields, "lineItems": line_items}]


class TestValidateAgencyCode:
    def test_passes_when_pafn_code_present_in_line_items(self):
        result = validate_agency_code(_submission(agency_codes_in_line_items=["2"]))
        assert result == []

    def test_passes_when_pafn_code_in_comma_separated_list(self):
        result = validate_agency_code(_submission(agency_codes_in_line_items=["2, 5"]))
        assert result == []

    def test_fails_when_no_pafn_code(self):
        result = validate_agency_code(_submission(agency_codes_in_line_items=["5"]))
        assert len(result) == 1
        assert result[0]["ruleCode"] == "AGENCY_CODE_NOT_PAFN"
        assert result[0]["result"] == "FAIL"

    def test_fails_when_no_agency_code_at_all(self):
        result = validate_agency_code(_submission())
        assert len(result) == 1
        assert result[0]["ruleCode"] == "AGENCY_CODE_MISSING"

    def test_skips_when_no_declaration_doc(self):
        result = validate_agency_code(_submission(doc_type="Invoice"))
        assert result == []

    def test_fallback_to_top_level_field(self):
        result = validate_agency_code(_submission(top_level_value="2"))
        assert result == []

    def test_configurable_agency_code(self):
        """Core Platform change: agency code is now a parameter."""
        result = validate_agency_code(
            _submission(agency_codes_in_line_items=["7"]),
            agency_code="7",
        )
        assert result == []

    def test_configurable_code_fails_with_wrong_code(self):
        result = validate_agency_code(
            _submission(agency_codes_in_line_items=["2"]),
            agency_code="7",
        )
        assert result[0]["ruleCode"] == "AGENCY_CODE_NOT_PAFN"
