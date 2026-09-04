"""Application service for the Evidence Intake Engine submission boundary."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from src.platform.intake.pre_validation import run as run_pre_validation
from src.platform.orchestration.submission import SubmissionDecision, evaluate_submission

REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


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
    if not request_id or REQUEST_ID_PATTERN.fullmatch(request_id) is None:
        return SubmissionResult(400, _error_body(
            "INVALID_REQUEST_ID",
            "requestId must contain only letters, numbers, periods, underscores, colons, or hyphens.",
        ))

    invalid_blob_paths = [
        document for document in payload.get("documents", [])
        if not _is_case_blob_path(request_id, document.get("blobPath"))
    ]
    if invalid_blob_paths:
        return SubmissionResult(400, _error_body(
            "INVALID_BLOB_PATH",
            "Each blobPath must belong to the submitted requestId.",
        ))

    decision = evaluate_submission(
        await orchestrator.get_status(request_id),
        await asyncio.to_thread(repository.get_case_status, request_id),
    )
    if decision is not SubmissionDecision.ACCEPT:
        code = (
            "DUPLICATE_IN_PROGRESS"
            if decision is SubmissionDecision.DUPLICATE_IN_PROGRESS
            else "ALREADY_COMPLETED"
        )
        return SubmissionResult(409, _error_body(code, "The request has already been submitted."))

    timestamp = (now or _utc_now)().isoformat()
    await asyncio.to_thread(repository.save_inbound, payload)

    content_cache: dict[str, bytes] = {}

    def cached_content(document: dict) -> bytes:
        blob_path = document["blobPath"]
        if blob_path not in content_cache:
            content_cache[blob_path] = content_resolver(document)
        return content_cache[blob_path]

    validation = await asyncio.to_thread(
        run_pre_validation,
        payload,
        content_resolver=cached_content,
    )
    if not validation["passed"]:
        await asyncio.to_thread(repository.append_audit_event, {
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
        try:
            accepted_documents = [
                await asyncio.to_thread(
                    document_preparer,
                    request_id,
                    document,
                    cached_content(document),
                )
                for document in accepted_documents
            ]
        except ValueError:
            error = {
                "code": "DOCUMENT_NORMALIZATION_FAILED",
                "severity": "error",
                "shortDescription": "An Office document could not be normalized.",
                "longDescription": "The submitted Office package is invalid or unsupported.",
                "affectedDocumentId": None,
            }
            await asyncio.to_thread(repository.append_audit_event, {
                "id": f"{request_id}:rejected:{timestamp}",
                "requestId": request_id,
                "eventType": "INTAKE_REJECTED",
                "timestamp": timestamp,
                "errors": [error],
            })
            return SubmissionResult(400, {
                "code": "DOCUMENT_NORMALIZATION_FAILED",
                "message": "An Office document could not be normalized.",
                "errors": [error],
                "warnings": validation["warnings"],
            })
    accepted_payload = {**payload, "documents": accepted_documents}
    await asyncio.to_thread(repository.create_received_case, {
        "id": request_id,
        "requestId": request_id,
        "status": "RECEIVED",
        "receivedAt": timestamp,
        "documentCount": len(accepted_documents),
        "warnings": validation["warnings"],
    })
    await asyncio.to_thread(repository.append_audit_event, {
        "id": f"{request_id}:received:{timestamp}",
        "requestId": request_id,
        "eventType": "INTAKE_RECEIVED",
        "timestamp": timestamp,
        "warnings": validation["warnings"],
    })
    status_query_uri = await orchestrator.start(request_id, accepted_payload)
    await asyncio.to_thread(repository.append_audit_event, {
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


def _is_case_blob_path(request_id: str, blob_path: object) -> bool:
    if not isinstance(blob_path, str) or "\\" in blob_path:
        return False
    parts = blob_path.split("/")
    return len(parts) > 1 and parts[0] == request_id and all(part not in {"", ".", ".."} for part in parts)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)