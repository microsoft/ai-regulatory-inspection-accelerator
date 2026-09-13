"""Tests for evidence-grounded human review tools."""

from src.platform.review.service import ReviewAuthorizationError, ReviewService
from src.platform.risk.evaluation_repository import InMemoryRiskEvaluationRepository


def _service():
    repository = InMemoryRiskEvaluationRepository()
    repository.save_evaluation({
        "id": "CASE-1#1",
        "requestId": "CASE-1",
        "status": "COMPLETED",
        "caseRiskScore": 40,
        "riskBand": "Medium",
        "recommendation": "REVIEW_REQUIRED",
        "documents": [{"documentId": "doc-1", "fields": {"reference": {"value": "A"}}}],
        "findings": [{"ruleId": "RULE-1", "result": "WARN"}],
        "overrides": [],
    })
    return ReviewService(repository, authorize=lambda user, case, action: user == "reviewer")


def test_review_tools_are_evidence_bounded():
    service = _service()
    case = service.get_case("reviewer", "CASE-1")
    findings = service.get_findings("reviewer", "CASE-1")
    comparison = service.compare_field_values("reviewer", "CASE-1", "reference")

    assert case["risk"]["caseRiskScore"] == 40
    assert findings[0]["ruleId"] == "RULE-1"
    assert comparison["values"]["doc-1"]["value"] == "A"


def test_unauthorized_review_access_is_rejected():
    try:
        _service().get_case("anonymous", "CASE-1")
    except ReviewAuthorizationError:
        pass
    else:
        raise AssertionError("Expected unauthorized review access to fail")
