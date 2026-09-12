"""Tests for immutable evaluation persistence and overrides."""

from src.platform.risk.evaluation_repository import InMemoryRiskEvaluationRepository


def test_evaluation_history_and_override_are_append_only():
    repository = InMemoryRiskEvaluationRepository()
    evaluation = repository.save_evaluation({
        "id": "CASE-1-risk-1",
        "requestId": "CASE-1",
        "caseRiskScore": 75,
        "recommendation": "ACCEPT_WITH_WARNING",
        "overrides": [],
    })

    assert evaluation["immutable"] is True
    assert repository.get_latest("CASE-1")["id"] == "CASE-1-risk-1"
    override = repository.append_override(
        "CASE-1",
        "CASE-1-risk-1",
        {
            "userId": "reviewer@example.org",
            "field": "recommendation",
            "oldValue": "ACCEPT_WITH_WARNING",
            "newValue": "ACCEPT",
            "reason": "Evidence verified",
        },
    )

    assert override["newValue"] == "ACCEPT"
    persisted = repository.get_evaluation("CASE-1", "CASE-1-risk-1")
    assert persisted["recommendation"] == "ACCEPT_WITH_WARNING"
    assert persisted["effectiveDecision"]["recommendation"] == "ACCEPT"
    assert len(persisted["overrides"]) == 1


def test_review_assignment_is_persisted():
    repository = InMemoryRiskEvaluationRepository()

    assignment = repository.assign_review(
        "CASE-2", "review-1", {"assignedTo": "reviewer@example.org", "status": "ASSIGNED"}
    )

    assert assignment["requestId"] == "CASE-2"
    assert assignment["assignedTo"] == "reviewer@example.org"
