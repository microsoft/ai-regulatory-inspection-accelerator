"""Persistence contract for immutable risk evaluations and review events."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Protocol

class RiskEvaluationRepository(Protocol):
    """Repository contract used by scoring and review APIs."""

    def save_evaluation(self, evaluation: dict) -> dict: ...
    def get_latest(self, request_id: str) -> dict | None: ...
    def get_evaluation(self, request_id: str, evaluation_id: str) -> dict | None: ...
    def list_evaluations(self, request_id: str) -> list[dict]: ...
    def assign_review(self, request_id: str, review_id: str, assignment: dict) -> dict: ...
    def append_override(self, request_id: str, evaluation_id: str, override: dict) -> dict: ...


class InMemoryRiskEvaluationRepository:
    """Deterministic repository for tests and local development."""

    def __init__(self) -> None:
        self._evaluations: dict[str, list[dict]] = {}
        self._reviews: dict[str, dict] = {}

    def save_evaluation(self, evaluation: dict) -> dict:
        item = {**evaluation, "id": evaluation.get("id", evaluation["requestId"]), "immutable": True}
        self._evaluations.setdefault(item["requestId"], []).append(item)
        return item

    def get_latest(self, request_id: str) -> dict | None:
        values = self._evaluations.get(request_id, [])
        return values[-1] if values else None

    def get_evaluation(self, request_id: str, evaluation_id: str) -> dict | None:
        return next((item for item in self._evaluations.get(request_id, []) if item["id"] == evaluation_id), None)

    def list_evaluations(self, request_id: str) -> list[dict]:
        return list(self._evaluations.get(request_id, []))

    def assign_review(self, request_id: str, review_id: str, assignment: dict) -> dict:
        review = {"requestId": request_id, "reviewId": review_id, **assignment}
        self._reviews[f"{request_id}:{review_id}"] = review
        return review

    def append_override(self, request_id: str, evaluation_id: str, override: dict) -> dict:
        evaluation = self.get_evaluation(request_id, evaluation_id)
        if evaluation is None:
            raise KeyError(evaluation_id)
        event = {"overrideId": override.get("overrideId", f"{evaluation_id}-override"), **override}
        evaluation.setdefault("overrides", []).append(event)
        evaluation["effectiveDecision"] = {
            "recommendation": event.get("newValue") if event.get("field") == "recommendation" else evaluation.get("recommendation"),
            "caseRiskScore": event.get("newValue") if event.get("field") == "caseRiskScore" else evaluation.get("caseRiskScore"),
        }
        return event


class AzureRiskEvaluationRepository:
    """Cosmos implementation for the logical ``risk-evaluations`` store."""

    def __init__(self, container: Any | None = None) -> None:
        if container is not None:
            self._container = container
            return
        from azure.cosmos import CosmosClient
        from azure.identity import ManagedIdentityCredential

        credential = ManagedIdentityCredential(client_id=os.getenv("MANAGED_IDENTITY_CLIENT_ID"))
        client = CosmosClient(os.environ["COSMOS_DB_ENDPOINT"], credential=credential)
        database = client.get_database_client(os.environ["COSMOS_DB_DATABASE"])
        self._container = database.get_container_client(os.getenv("COSMOS_DB_RISK_EVALUATIONS_CONTAINER", "risk-evaluations"))

    def save_evaluation(self, evaluation: dict) -> dict:
        return self._container.create_item({**evaluation, "immutable": True})

    def get_latest(self, request_id: str) -> dict | None:
        rows = list(self._container.query_items(
            query="SELECT TOP 1 * FROM c WHERE c.requestId = @requestId ORDER BY c.createdAt DESC",
            parameters=[{"name": "@requestId", "value": request_id}],
            partition_key=request_id,
        ))
        return rows[0] if rows else None

    def get_evaluation(self, request_id: str, evaluation_id: str) -> dict | None:
        try:
            return self._container.read_item(f"{request_id}#{evaluation_id}", partition_key=request_id)
        except Exception:
            return None

    def list_evaluations(self, request_id: str) -> list[dict]:
        return list(self._container.query_items(
            query="SELECT * FROM c WHERE c.requestId = @requestId ORDER BY c.createdAt DESC",
            parameters=[{"name": "@requestId", "value": request_id}],
            partition_key=request_id,
        ))

    def assign_review(self, request_id: str, review_id: str, assignment: dict) -> dict:
        return self._container.upsert_item({"id": f"{request_id}#review#{review_id}", "requestId": request_id, "reviewId": review_id, **assignment})

    def append_override(self, request_id: str, evaluation_id: str, override: dict) -> dict:
        evaluation = self.get_evaluation(request_id, evaluation_id)
        if evaluation is None:
            raise KeyError(evaluation_id)
        event = {"overrideId": override.get("overrideId", f"{evaluation_id}-override"), "timestamp": datetime.now(timezone.utc).isoformat(), **override}
        evaluation.setdefault("overrides", []).append(event)
        evaluation["modifiedAt"] = event["timestamp"]
        self._container.replace_item(evaluation["id"], evaluation)
        return event
