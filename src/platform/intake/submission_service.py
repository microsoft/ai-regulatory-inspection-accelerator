"""Application service for the Evidence Intake Engine submission boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from src.platform.intake.pre_validation import run as run_pre_validation
from src.platform.orchestration.submission import SubmissionDecision, evaluate_submission


class IntakeRepository(Protocol):
    """Persistence operations required by the demo intake path."""

    def get_case_status(self, request_id: str) -> str | None: ...

    def save_inbound(self, payload: dict) -> None: ...

    def create_received_case(self, case: dict) -> None: ...

    def append_audit_event(self, event: dict) -> None: ...


class OrchestrationGateway(Protocol):
    """Durable orchestration operations required by the demo intake path."""

    async def get_status(self, instance_id: str) -> str | None: ...

    async def start(self, instance_id: str, payload: dict) -> str: ...


@dataclass(frozen=True)
class SubmissionResult:
    """Transport-neutral result returned to an HTTP adapter."""

    status_code: int
    body: dict


async def submit(
    payload: dict,
    *,
    repository: IntakeRepository,
    orchestrator: OrchestrationGateway,
    content_resolver: Callable[[dict], bytes],
    document_preparer: Callable[[str, dict, bytes], dict] | None = None,
    now: Callable[[], datetime] | None = None,
) -> SubmissionResult:
    """Validate, initialize, and start one evidence submission."""
    request_id = str(payload.get("requestId", "")).strip()
    if not request_id:
        return SubmissionResult(400, _error_body("MISSING_REQUEST_ID", "requestId is required."))

    decision = evaluate_submission(
        await orchestrator.get_status(request_id),
        repository.get_case_status(request_id),
    )
    if decision is not SubmissionDecision.ACCEPT:
        code = (
            "DUPLICATE_IN_PROGRESS"
            if decision is SubmissionDecision.DUPLICATE_IN_PROGRESS
            else "ALREADY_COMPLETED"
        )
        return SubmissionResult(409, _error_body(code, "The request has already been submitted."))

    timestamp = (now or _utc_now)().isoformat()
    repository.save_inbound(payload)

    validation = run_pre_validation(payload, content_resolver=content_resolver)
    if not validation["passed"]:
        repository.append_audit_event({
            "id": f"{request_id}:rejected:{timestamp}",
            "requestId": request_id,
            "eventType": "INTAKE_REJECTED",
            "timestamp": timestamp,
            "errors": validation["errors"],
        })
        return SubmissionResult(400, {
            "code": "PRE_VALIDATION_FAILED",
            "message": "The evidence bundle failed pre-validation.",
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        })

    accepted_documents = validation["documents"]
    if document_preparer is not None:
        accepted_documents = [
            document_preparer(request_id, document, content_resolver(document))
            for document in accepted_documents
        ]
    accepted_payload = {**payload, "documents": accepted_documents}
    repository.create_received_case({
        "id": request_id,
        "requestId": request_id,
        "status": "RECEIVED",
        "receivedAt": timestamp,
        "documentCount": len(accepted_documents),
        "warnings": validation["warnings"],
    })
    repository.append_audit_event({
        "id": f"{request_id}:received:{timestamp}",
        "requestId": request_id,
        "eventType": "INTAKE_RECEIVED",
        "timestamp": timestamp,
        "warnings": validation["warnings"],
    })
    status_query_uri = await orchestrator.start(request_id, accepted_payload)
    repository.append_audit_event({
        "id": f"{request_id}:accepted:{timestamp}",
        "requestId": request_id,
        "eventType": "INTAKE_ACCEPTED",
        "timestamp": timestamp,
        "instanceId": request_id,
    })

    return SubmissionResult(202, {
        "instanceId": request_id,
        "statusQueryUri": status_query_uri,
        "status": "RECEIVED",
        "warnings": validation["warnings"],
    })


def _error_body(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)