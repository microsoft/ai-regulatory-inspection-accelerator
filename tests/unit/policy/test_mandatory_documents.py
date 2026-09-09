"""Unit tests for src/platform/policy/evaluators/mandatory_documents.py"""

from typing import ClassVar

from src.platform.policy.evaluators.mandatory_documents import (
    _get_hs_prefixes,
    _norm,
    validate_mandatory_docs,
)


class TestNorm:
    def test_case_variants_match(self):
        assert _norm("Health_Certificate_Country_of_Origin") == _norm("Health_Certificate_Country_Of_Origin")

    def test_strips_spaces_and_underscores(self):
        assert _norm("House Bill") == _norm("House_Bill")


class TestGetHsPrefixes:
    RULES: ClassVar[list] = [{"id": "HALAL_HS_CODES", "hsCodes": ["0201", "0202.10.00"]}]

    def test_returns_normalized(self):
        prefixes = _get_hs_prefixes(self.RULES, "HALAL_HS_CODES")
        assert "0201" in prefixes
        assert "02021" in prefixes

    def test_missing_rule_returns_empty_tuple(self):
        assert _get_hs_prefixes(self.RULES, "NONEXISTENT") == ()


class TestValidateMandatoryDocs:
    MANDATORY_RULE: ClassVar[dict] = {
        "id": "MANDATORY_DOC_RULES",
        "mandatoryDocuments": [
            {"documentType": "Invoice", "documentTypeId": "50"},
            {"documentType": "Certificate_Of_Origin", "documentTypeId": "51"},
        ],
        "conditionalDocuments": [],
        "personalShipment": {
            "declarationPrefixes": ["TDR"],
            "requiredDocuments": [
                {"documentType": "Declaration_Document", "documentTypeId": "42"},
                {"documentType": "Other_Documents", "documentTypeId": "43"},
            ],
        },
    }

    def _rules(self, extra=None):
        rules = [self.MANDATORY_RULE]
        if extra:
            rules.extend(extra)
        return rules

    def _payload(self, doc_ids, items=None, declaration="TIM/1234/SHU25"):
        return {
            "requestId": "REQ-001",
            "declarationNumber": declaration,
            "documents": [{"documentTypeId": did, "documentType": f"Type_{did}"} for did in doc_ids],
            "items": items or [],
        }

    def _submission(self, doc_types):
        return [{"documentTypeId": f"id_{dt}", "document": dt, "fields": {}} for dt in doc_types]

    def test_all_mandatory_present(self):
        payload = self._payload(["50", "51"])
        findings, _ = validate_mandatory_docs(self._rules(), payload, self._submission(["Invoice", "Certificate_Of_Origin"]))
        assert not any(f["ruleCode"] == "MANDATORY_DOC_MISSING" for f in findings)

    def test_missing_mandatory_fails(self):
        payload = self._payload(["50"])
        findings, _ = validate_mandatory_docs(self._rules(), payload, self._submission(["Invoice"]))
        missing = [f for f in findings if f["ruleCode"] == "MANDATORY_DOC_MISSING"]
        assert len(missing) == 1

    def test_personal_tdr(self):
        payload = self._payload(["42", "43"], declaration="TDR/5678/KWI26")
        findings, _ = validate_mandatory_docs(self._rules(), payload, self._submission(["Declaration_Document", "Other_Documents"]))
        assert not any(f["ruleCode"] == "MANDATORY_DOC_MISSING" for f in findings)

    def test_or_group_one_present(self):
        rule = {
            "id": "MANDATORY_DOC_RULES",
            "mandatoryDocuments": [
                [{"documentType": "Packing_List", "documentTypeId": "48"}, {"documentType": "Stretching_List", "documentTypeId": "49"}]
            ],
            "conditionalDocuments": [],
        }
        payload = self._payload(["48"])
        findings, _ = validate_mandatory_docs([rule], payload, self._submission(["Packing_List"]))
        assert not any(f["ruleCode"] == "MANDATORY_DOC_MISSING" for f in findings)

    def test_or_group_none_present(self):
        rule = {
            "id": "MANDATORY_DOC_RULES",
            "mandatoryDocuments": [
                [{"documentType": "Packing_List", "documentTypeId": "48"}, {"documentType": "Stretching_List", "documentTypeId": "49"}]
            ],
            "conditionalDocuments": [],
        }
        payload = self._payload(["50"])
        findings, _ = validate_mandatory_docs([rule], payload, self._submission(["Invoice"]))
        assert any(f["ruleCode"] == "MANDATORY_DOC_MISSING" for f in findings)

    def test_name_normalization(self):
        payload = {
            "requestId": "R1", "declarationNumber": "T/1/S",
            "documents": [{"documentTypeId": "50", "documentType": "Invoice"}, {"documentTypeId": "51", "documentType": "Certificate_Of_Origin"}],
            "items": [],
        }
        submission = [
            {"documentTypeId": "50", "document": "InvoiceDoc", "fields": {}},
            {"documentTypeId": "51", "document": "Certificate_Of_Origin", "fields": {}},
        ]
        _, norm_sub = validate_mandatory_docs(self._rules(), payload, submission)
        doc_names = [d["document"] for d in norm_sub]
        assert "Invoice" in doc_names

    def test_halal_conditional_required_when_hs_matches(self):
        rules = [
            {
                "id": "MANDATORY_DOC_RULES",
                "mandatoryDocuments": [],
                "conditionalDocuments": [{"documentType": "Halal_Slaughter_Certificate", "documentTypeId": "21"}],
                "conditionalRequirements": [
                    {"documentType": "Halal_Slaughter_Certificate", "hsCodeRuleId": "HALAL_HS_CODES"}
                ],
            },
            {"id": "HALAL_HS_CODES", "hsCodes": ["0202"]},
        ]
        payload = {
            "requestId": "R1", "declarationNumber": "T/1/S",
            "documents": [{"documentTypeId": "50", "documentType": "Invoice"}],
            "items": [{"hsCode": "0202.10.00", "countryOfOrigin": "AE"}],
        }
        findings, _ = validate_mandatory_docs(rules, payload, [{"documentTypeId": "50", "document": "Invoice", "fields": {}}])
        assert any(f["documentType"] == "Halal_Slaughter_Certificate" for f in findings if f["ruleCode"] == "MANDATORY_DOC_MISSING")

    def test_origin_country_trigger_is_template_driven(self):
        rule = {
            "id": "MANDATORY_DOC_RULES",
            "mandatoryDocuments": [],
            "conditionalDocuments": [
                {"documentType": "Regional_Declaration", "documentTypeId": "90"}
            ],
            "conditionalRequirements": [
                {"documentType": "Regional_Declaration", "originCountries": ["NZ"]}
            ],
        }
        payload = self._payload(
            ["50"],
            items=[{"hsCode": "9999", "countryOfOrigin": "New Zealand"}],
        )

        findings, _ = validate_mandatory_docs([rule], payload, self._submission(["Invoice"]))

        assert any(f["documentType"] == "Regional_Declaration" for f in findings)
