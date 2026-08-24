"""Unit tests for src/platform/policy/evaluators/signature_stamp.py"""

from src.platform.policy.evaluators.signature_stamp import validate_signature_stamp

RULE_DOC = {
    "id": "SIGNATURE_STAMP_RULES",
    "requiredSignatureDocs": ["Certificate_Of_Origin", "Signature_Authorization"],
    "informationalSignatureDocs": ["Invoice", "Packing_List"],
}


def _doc(doc_type: str, has_sig: bool) -> dict:
    return {
        "document": doc_type,
        "documentTypeId": f"id_{doc_type}",
        "fields": {"signature_detected": {"value": has_sig, "confidence": 0.9}},
    }


class TestValidateSignatureStamp:
    def test_required_doc_with_signature_passes(self):
        findings = validate_signature_stamp(RULE_DOC, [_doc("Certificate_Of_Origin", True)])
        assert len(findings) == 1
        assert findings[0]["ruleCode"] == "SIGNATURE_STAMP_VERIFIED"
        assert findings[0]["result"] == "PASS"

    def test_required_doc_missing_signature_warns(self):
        findings = validate_signature_stamp(RULE_DOC, [_doc("Certificate_Of_Origin", False)])
        assert len(findings) == 1
        assert findings[0]["ruleCode"] == "SIGNATURE_STAMP_MISSING"
        assert findings[0]["result"] == "WARN"

    def test_informational_doc_with_signature_passes(self):
        findings = validate_signature_stamp(RULE_DOC, [_doc("Invoice", True)])
        assert findings[0]["ruleCode"] == "SIGNATURE_STAMP_PRESENT"
        assert findings[0]["result"] == "PASS"

    def test_informational_doc_without_signature_not_applicable(self):
        findings = validate_signature_stamp(RULE_DOC, [_doc("Invoice", False)])
        assert findings[0]["ruleCode"] == "SIGNATURE_STAMP_NOT_DETECTED"
        assert findings[0]["result"] == "NOT_APPLICABLE"

    def test_untracked_doc_emits_no_finding(self):
        findings = validate_signature_stamp(RULE_DOC, [_doc("Declaration_Document", False)])
        assert findings == []

    def test_multiple_docs(self):
        submission = [
            _doc("Certificate_Of_Origin", True),
            _doc("Signature_Authorization", False),
            _doc("Invoice", False),
        ]
        findings = validate_signature_stamp(RULE_DOC, submission)
        codes = {f["ruleCode"] for f in findings}
        assert "SIGNATURE_STAMP_VERIFIED" in codes
        assert "SIGNATURE_STAMP_MISSING" in codes
        assert "SIGNATURE_STAMP_NOT_DETECTED" in codes
