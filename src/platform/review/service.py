"""Provider-neutral, evidence-grounded human review service."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class ReviewAuthorizationError(PermissionError):
    """Raised when a reviewer lacks permission for a case operation."""


class ReviewRepository(Protocol):
    def get_latest(self, request_id: str) -> dict | None: ...
    def get_evaluation(self, request_id: str, evaluation_id: str) -> dict | None: ...
    def append_override(self, request_id: str, evaluation_id: str, override: dict) -> dict: ...
    def assign_review(self, request_id: str, review_id: str, assignment: dict) -> dict: ...


class ReviewService:
    """Expose bounded tools over persisted case evidence.

    The service returns stored evidence only. It does not use general knowledge
    or silently invent explanations; an LLM adapter can consume these tool
    results at the deployment boundary.
    """

    def __init__(
        self,
        repository: ReviewRepository,
        *,
        authorize: Callable[[str, str, str], bool] | None = None,
    ) -> None:
        self.repository = repository
        self.authorize = authorize or (lambda user_id, request_id, action: True)

    def _check(self, user_id: str, request_id: str, action: str) -> None:
        if not self.authorize(user_id, request_id, action):
            raise ReviewAuthorizationError(f"User is not authorized to {action} this case.")

    def get_case(self, user_id: str, request_id: str) -> dict:
        self._check(user_id, request_id, "read")
        evaluation = self.repository.get_latest(request_id)
        if evaluation is None:
            raise KeyError(request_id)
        return {
            "requestId": request_id,
            "status": evaluation.get("status"),
            "risk": {
                "caseRiskScore": evaluation.get("caseRiskScore", evaluation.get("compositeRiskScore")),
                "riskBand": evaluation.get("riskBand", evaluation.get("riskLevel")),
                "recommendation": evaluation.get("recommendation"),
            },
            "manualReview": evaluation.get("manualReview", {}),
            "documents": evaluation.get("documents", evaluation.get("documentAssessments", [])),
            "items": evaluation.get("items", evaluation.get("itemAssessments", [])),
        }

    def get_findings(self, user_id: str, request_id: str) -> list[dict]:
        self._check(user_id, request_id, "read")
        evaluation = self.repository.get_latest(request_id)
        if evaluation is None:
            raise KeyError(request_id)
        return list(evaluation.get("findings", evaluation.get("ruleEvaluations", [])))

    def compare_field_values(self, user_id: str, request_id: str, field: str) -> dict:
        self._check(user_id, request_id, "read")
        evaluation = self.repository.get_latest(request_id)
        if evaluation is None:
            raise KeyError(request_id)
        values: dict[str, Any] = {}
        for document in evaluation.get("documents", []):
            fields = document.get("fields", {})
            if field in fields:
                values[str(document.get("documentId", len(values)))] = fields[field]
        return {"requestId": request_id, "field": field, "values": values}

    def assign_review(self, user_id: str, request_id: str, review_id: str, assignment: dict) -> dict:
        self._check(user_id, request_id, "assign")
        return self.repository.assign_review(request_id, review_id, assignment)

    def record_feedback(self, user_id: str, request_id: str, feedback: dict) -> dict:
        self._check(user_id, request_id, "feedback")
        return {
            "requestId": request_id,
            "userId": user_id,
            "feedback": dict(feedback),
        }

    def override(self, user_id: str, request_id: str, evaluation_id: str, override: dict) -> dict:
        self._check(user_id, request_id, "override")
        required = {"field", "oldValue", "newValue", "reason"}
        if not required.issubset(override):
            raise ValueError("Override requires field, oldValue, newValue, and reason.")
        return self.repository.append_override(
            request_id,
            evaluation_id,
            {**override, "userId": user_id},
        )
