"""
Unit tests for src/platform/intake/pre_validation.py (Pre-Validation Agent).

All tests exercise the pure, metadata-only checks documented in the module:
document count, duplicate detection, MIME type, missing checksum, attachment
type consistency, and empty items. Storage-backed checks (blob existence,
checksum recomputation, etc.) are intentionally out of scope for this module
and therefore not tested here.
"""

from src.platform.intake.pre_validation import run


def _doc(**overrides) -> dict:
    base = {
        "documentTypeId": "1",
        "documentType": "Invoice",
        "checksum": "abc123",
        "mimeType": "application/pdf",
    }
    base.update(overrides)
    return base


class TestDocumentCount:
    def test_passes_when_count_matches(self):
        payload = {"documents": [_doc()], "attachmentTypes": ["Invoice"], "items": [{"id": 1}]}
        result = run(payload)
        assert result["passed"] is True
        assert result["errors"] == []

    def test_fails_when_declared_count_mismatches_received(self):
        payload = {
            "documents": [_doc()],
            "attachmentTypes": ["Invoice"],
            "items": [{"id": 1}],
            "expectedDocumentCount": 2,
        }
        result = run(payload)
        assert result["passed"] is False
        assert any(e["code"] == "DOCUMENT_COUNT_MISMATCH" for e in result["errors"])


class TestDuplicateDetection:
    def test_duplicate_checksum_deduplicated_and_warned_not_errored(self):
        payload = {
            "documents": [
                _doc(documentTypeId="1", checksum="same"),
                _doc(documentTypeId="2", checksum="same"),
            ],
            "attachmentTypes": ["Invoice"],
            "items": [{"id": 1}],
        }
        result = run(payload)
        assert result["passed"] is True
        assert len(result["documents"]) == 1
        assert result["documents"][0]["documentTypeId"] == "1"
        assert len(result["warnings"]) == 1
        assert result["warnings"][0]["ruleCode"] == "DUPLICATE_CHECKSUM"

    def test_distinct_checksums_not_deduplicated(self):
        payload = {
            "documents": [
                _doc(documentTypeId="1", checksum="aaa"),
                _doc(documentTypeId="2", checksum="bbb"),
            ],
            "attachmentTypes": ["Invoice"],
            "items": [{"id": 1}],
        }
        result = run(payload)
        assert len(result["documents"]) == 2
        assert result["warnings"] == []


class TestMimeType:
    def test_unsupported_mime_type_fails(self):
        payload = {
            "documents": [_doc(mimeType="application/zip")],
            "attachmentTypes": ["Invoice"],
            "items": [{"id": 1}],
        }
        result = run(payload)
        assert result["passed"] is False
        assert any(e["code"] == "UNSUPPORTED_MIME_TYPE" for e in result["errors"])

    def test_custom_allow_list_permits_otherwise_unsupported_type(self):
        payload = {
            "documents": [_doc(mimeType="application/zip")],
            "attachmentTypes": ["Invoice"],
            "items": [{"id": 1}],
        }
        result = run(payload, allowed_mime_types=frozenset({"application/zip"}))
        assert result["passed"] is True


class TestMissingChecksum:
    def test_missing_checksum_fails(self):
        payload = {
            "documents": [_doc(checksum="")],
            "attachmentTypes": ["Invoice"],
            "items": [{"id": 1}],
        }
        result = run(payload)
        assert result["passed"] is False
        assert any(e["code"] == "MISSING_CHECKSUM" for e in result["errors"])


class TestAttachmentTypeConsistency:
    def test_document_type_not_in_attachment_types_fails(self):
        payload = {
            "documents": [_doc(documentType="Invoice")],
            "attachmentTypes": ["Packing_List"],
            "items": [{"id": 1}],
        }
        result = run(payload)
        assert result["passed"] is False
        codes = [e["code"] for e in result["errors"]]
        assert codes.count("ATTACHMENT_TYPE_MISMATCH") == 2  # doc not in list + list entry has no doc

    def test_attachment_type_without_document_fails(self):
        payload = {
            "documents": [_doc(documentType="Invoice")],
            "attachmentTypes": ["Invoice", "Certificate_Of_Origin"],
            "items": [{"id": 1}],
        }
        result = run(payload)
        assert result["passed"] is False
        assert any(e["code"] == "ATTACHMENT_TYPE_MISMATCH" for e in result["errors"])


class TestEmptyItems:
    def test_empty_items_fails(self):
        payload = {"documents": [_doc()], "attachmentTypes": ["Invoice"], "items": []}
        result = run(payload)
        assert result["passed"] is False
        assert any(e["code"] == "EMPTY_ITEMS" for e in result["errors"])

    def test_missing_items_key_treated_as_empty_and_fails(self):
        """A missing items key defaults to an empty list, so it fails the same as an explicit []."""
        payload = {"documents": [_doc()], "attachmentTypes": ["Invoice"]}
        result = run(payload)
        assert any(e["code"] == "EMPTY_ITEMS" for e in result["errors"])


class TestMultipleDocuments:
    def test_all_checks_pass_for_well_formed_multi_document_submission(self):
        payload = {
            "documents": [
                _doc(documentTypeId="1", documentType="Invoice", checksum="aaa"),
                _doc(documentTypeId="2", documentType="Packing_List", checksum="bbb", mimeType="image/png"),
            ],
            "attachmentTypes": ["Invoice", "Packing_List"],
            "items": [{"id": 1}],
        }
        result = run(payload)
        assert result["passed"] is True
        assert result["errors"] == []
        assert len(result["documents"]) == 2
