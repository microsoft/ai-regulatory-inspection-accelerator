"""
Signature / Stamp Verification Rule

Ported from PAFN's rules_engine/signature_stamp.py — unchanged (pure algorithm,
document lists come from the SIGNATURE_STAMP_RULES rule document).
"""

import logging

logger = logging.getLogger(__name__)


def validate_signature_stamp(
    rule_doc: dict,
    submission: list[dict],
) -> list[dict]:
    """Run signature/stamp verification against all submitted documents.

    Args:
        rule_doc:   The SIGNATURE_STAMP_RULES document.
                    Keys: requiredSignatureDocs (list[str]), informationalSignatureDocs (list[str]).
        submission: List of extracted-document dicts with 'document' and 'fields'.
    """
    required_types: set[str] = set(rule_doc.get("requiredSignatureDocs", []))
    informational_types: set[str] = set(rule_doc.get("informationalSignatureDocs", []))
    findings: list[dict] = []

    for doc in submission:
        doc_type: str = doc.get("document", "")
        doc_id: str = doc.get("documentTypeId", doc_type)
        fields: dict = doc.get("fields", {})

        sig_field = fields.get("signature_detected", {})
        has_signature: bool = bool(sig_field.get("value", False))

        if doc_type in required_types:
            if has_signature:
                findings.append({
                    "ruleCode": "SIGNATURE_STAMP_VERIFIED",
                    "result": "PASS",
                    "severity": "Info",
                    "message": f"Signature or stamp detected on {doc_type} — document authorization verified.",
                    "documentName": doc_type,
                    "documentTypeId": doc_id,
                })
            else:
                findings.append({
                    "ruleCode": "SIGNATURE_STAMP_MISSING",
                    "result": "WARN",
                    "severity": "Warning",
                    "message": (
                        f"No signature or stamp detected on {doc_type}. "
                        "Document authorization could not be verified — manual review recommended."
                    ),
                    "documentName": doc_type,
                    "documentTypeId": doc_id,
                })
        elif doc_type in informational_types:
            if has_signature:
                findings.append({
                    "ruleCode": "SIGNATURE_STAMP_PRESENT",
                    "result": "PASS",
                    "severity": "Info",
                    "message": f"Signature or stamp detected on {doc_type}.",
                    "documentName": doc_type,
                    "documentTypeId": doc_id,
                })
            else:
                findings.append({
                    "ruleCode": "SIGNATURE_STAMP_NOT_DETECTED",
                    "result": "NOT_APPLICABLE",
                    "severity": "Info",
                    "message": (
                        f"No signature or stamp detected on {doc_type}. "
                        "This is informational only — no action required."
                    ),
                    "documentName": doc_type,
                    "documentTypeId": doc_id,
                })

    logger.info(
        "signature_stamp: checked %d doc(s), emitted %d finding(s)",
        len(submission), len(findings),
    )
    return findings
