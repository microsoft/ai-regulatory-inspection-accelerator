"""Unit tests for src/platform/policy/evaluators/minimum_fields.py"""

from typing import ClassVar

from src.platform.policy.evaluators.minimum_fields import _norm, validate_min_fields


class TestNorm:
    def test_basic(self):
        assert _norm("invoice_number") == "invoicenumber"

    def test_case_insensitive(self):
        assert _norm("InvoiceNumber") == _norm("invoice_number")

    def test_strips_hyphens(self):
        assert _norm("issue-date") == "issuedate"


class TestValidateMinFields:
    RULE: ClassVar[dict] = {
        "id": "MIN_FIELDS_RULES",
        "severity": "Warning",
        "minimumFieldsByDocuments": [
            {"documentName": "Invoice", "fields": ["invoice_number", "invoice_date"]},
        ],
    }
    # No patch needed — inject allowed_fields_by_doc directly (Core Platform improvement)
    ALLOWED: ClassVar[dict] = {"Invoice": ["invoice_number", "invoice_date", "amount"]}

    def test_all_fields_present(self):
        submission = [{"document": "Invoice", "fields": {
            "invoice_number": {"value": "INV-001", "confidence": 0.9},
            "invoice_date": {"value": "2025-01-01", "confidence": 0.9},
        }}]
        assert validate_min_fields(self.RULE, submission, self.ALLOWED) == []

    def test_missing_field(self):
        submission = [{"document": "Invoice", "fields": {
            "invoice_number": {"value": "INV-001", "confidence": 0.9},
        }}]
        findings = validate_min_fields(self.RULE, submission, self.ALLOWED)
        assert len(findings) == 1
        assert findings[0]["result"] == "WARN"
        assert "invoice date" in findings[0]["message"]

    def test_null_value_treated_as_missing(self):
        submission = [{"document": "Invoice", "fields": {
            "invoice_number": {"value": "INV-001", "confidence": 0.9},
            "invoice_date": {"value": None, "confidence": 0.0},
        }}]
        assert len(validate_min_fields(self.RULE, submission, self.ALLOWED)) == 1

    def test_empty_string_treated_as_missing(self):
        submission = [{"document": "Invoice", "fields": {
            "invoice_number": {"value": "", "confidence": 0.0},
            "invoice_date": {"value": "2025-01-01", "confidence": 0.9},
        }}]
        assert len(validate_min_fields(self.RULE, submission, self.ALLOWED)) == 1

    def test_no_rule_for_document(self):
        submission = [{"document": "Certificate_Of_Origin", "fields": {}}]
        assert validate_min_fields(self.RULE, submission, self.ALLOWED) == []

    def test_accepts_list_input(self):
        submission = [{"document": "Invoice", "fields": {
            "invoice_number": {"value": "INV-001", "confidence": 0.9},
            "invoice_date": {"value": "2025-01-01", "confidence": 0.9},
        }}]
        assert validate_min_fields([self.RULE], submission, self.ALLOWED) == []

    def test_none_rule_returns_empty(self):
        assert validate_min_fields([{"id": "OTHER"}], [], self.ALLOWED) == []

    def test_normalized_field_matching(self):
        """InvoiceNumber → invoicenumber should match invoice_number."""
        submission = [{"document": "Invoice", "fields": {
            "InvoiceNumber": {"value": "INV-001", "confidence": 0.9},
            "InvoiceDate": {"value": "2025-01-01", "confidence": 0.9},
        }}]
        assert validate_min_fields(self.RULE, submission, self.ALLOWED) == []

    def test_or_group_document_name(self):
        rule = {
            "id": "MIN_FIELDS_RULES",
            "severity": "Warning",
            "minimumFieldsByDocuments": [
                {"documentName": ["Packing_List", "Stretching_List"], "fields": ["invoice_number"]},
            ],
        }
        allowed = {"Packing_List": ["invoice_number"], "Stretching_List": ["invoice_number"]}
        submission = [{"document": "Packing_List", "fields": {
            "invoice_number": {"value": "INV-001", "confidence": 0.9},
        }}]
        assert validate_min_fields(rule, submission, allowed) == []

    def test_intersection_skips_field_not_in_template(self):
        """Field in rule but not in template → silently skipped."""
        rule = {
            "id": "MIN_FIELDS_RULES",
            "severity": "Warning",
            "minimumFieldsByDocuments": [
                {"documentName": "Invoice", "fields": ["invoice_number", "unknown_field"]},
            ],
        }
        allowed = {"Invoice": ["invoice_number"]}  # unknown_field not in template
        submission = [{"document": "Invoice", "fields": {
            "invoice_number": {"value": "INV-001", "confidence": 0.9},
        }}]
        assert validate_min_fields(rule, submission, allowed) == []

    def test_no_allowed_fields_by_doc_skips_intersection(self):
        """When allowed_fields_by_doc is None, all rule fields are checked."""
        submission = [{"document": "Invoice", "fields": {
            "invoice_number": {"value": "INV-001", "confidence": 0.9},
        }}]
        findings = validate_min_fields(self.RULE, submission, allowed_fields_by_doc=None)
        assert len(findings) == 1
