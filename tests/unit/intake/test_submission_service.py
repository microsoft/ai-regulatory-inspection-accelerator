"""Tests for the Evidence Intake Engine submission service."""

import asyncio
import hashlib
from datetime import datetime, timezone

from src.platform.intake.submission_service import submit


class FakeRepository:
    def __init__(self, case_status: str | None = None):
        self.case_status = case_status
        self.operations: list[str] = []
        self.inbound: dict | None = None
        self.case: dict | None = None
        self.events: list[dict] = []

    def get_case_status(self, request_id: str) -> str | None:
        return self.case_status

    def save_inbound(self, payload: dict) -> None:
        self.operations.append("save_inbound")
        self.inbound = payload

    def create_received_case(self, case: dict) -> None:
        self.operations.append("create_received_case")
        self.case = case

    def append_audit_event(self, event: dict) -> None:
        self.operations.append(event["eventType"])
        self.events.append(event)


class FakeOrchestrator:
    def __init__(self, repository: FakeRepository, status: str | None = None):
        self.repository = repository
        self.status = status
        self.started_payload: dict | None = None

    async def get_status(self, instance_id: str) -> str | None:
        return self.status

    async def start(self, instance_id: str, payload: dict) -> str:
        self.repository.operations.append("start")
        self.started_payload = payload
        return f"https://demo/status/{instance_id}"


def _payload(content: bytes, *, duplicate: bool = False) -> dict:
    checksum = hashlib.sha256(content).hexdigest()
    documents = [{
        "documentTypeId": "1",
        "documentType": "Invoice",
        "checksum": checksum,
        "fileSizeBytes": len(content),
        "mimeType": "application/pdf",
        "blobPath": "DEMO-1/invoice.pdf",
    }]
    if duplicate:
        documents.append({**documents[0], "documentTypeId": "2"})
    return {
        "requestId": "DEMO-1",
        "documents": documents,
        "attachmentTypes": ["Invoice"],
        "items": [{"id": "ITEM-1"}],
        "expectedDocumentCount": len(documents),
    }


def test_valid_submission_persists_received_before_starting_orchestration():
    content = b"demo evidence"
    repository = FakeRepository()
    orchestrator = FakeOrchestrator(repository)

    result = asyncio.run(submit(
        _payload(content),
        repository=repository,
        orchestrator=orchestrator,
        content_resolver=lambda _: content,
        now=lambda: datetime(2026, 9, 4, tzinfo=timezone.utc),
    ))

    assert result.status_code == 202
    assert result.body["instanceId"] == "DEMO-1"
    assert result.body["statusQueryUri"] == "https://demo/status/DEMO-1"
    assert repository.case is not None
    assert repository.case["status"] == "RECEIVED"
    assert repository.operations == [
        "save_inbound",
        "create_received_case",
        "INTAKE_RECEIVED",
        "start",
        "INTAKE_ACCEPTED",
    ]


def test_checksum_mismatch_is_rejected_and_audited_without_starting():
    repository = FakeRepository()
    orchestrator = FakeOrchestrator(repository)

    result = asyncio.run(submit(
        _payload(b"original"),
        repository=repository,
        orchestrator=orchestrator,
        content_resolver=lambda _: b"modified",
    ))

    assert result.status_code == 400
    assert any(error["code"] == "CHECKSUM_MISMATCH" for error in result.body["errors"])
    assert orchestrator.started_payload is None
    assert repository.events[-1]["eventType"] == "INTAKE_REJECTED"


def test_duplicate_is_removed_before_orchestration_and_reported():
    content = b"same evidence"
    repository = FakeRepository()
    orchestrator = FakeOrchestrator(repository)

    result = asyncio.run(submit(
        _payload(content, duplicate=True),
        repository=repository,
        orchestrator=orchestrator,
        content_resolver=lambda _: content,
    ))

    assert result.status_code == 202
    assert len(orchestrator.started_payload["documents"]) == 1
    assert result.body["warnings"][0]["ruleCode"] == "DUPLICATE_CHECKSUM"


def test_document_is_prepared_before_orchestration():
    content = b"office package"
    repository = FakeRepository()
    orchestrator = FakeOrchestrator(repository)

    result = asyncio.run(submit(
        _payload(content),
        repository=repository,
        orchestrator=orchestrator,
        content_resolver=lambda _: content,
        document_preparer=lambda request_id, document, _: {
            **document,
            "normalizedBlobPath": f"artifacts/{request_id}/normalized/1.md",
        },
    ))

    assert result.status_code == 202
    assert orchestrator.started_payload["documents"][0]["normalizedBlobPath"] == (
        "artifacts/DEMO-1/normalized/1.md"
    )


def test_in_progress_request_is_rejected_without_persistence():
    repository = FakeRepository()
    orchestrator = FakeOrchestrator(repository, status="Running")

    result = asyncio.run(submit(
        _payload(b"demo evidence"),
        repository=repository,
        orchestrator=orchestrator,
        content_resolver=lambda _: b"demo evidence",
    ))

    assert result.status_code == 409
    assert result.body["code"] == "DUPLICATE_IN_PROGRESS"
    assert repository.operations == []


def test_blob_path_must_belong_to_request():
    payload = _payload(b"demo evidence")
    payload["documents"][0]["blobPath"] = "OTHER-CASE/invoice.pdf"
    repository = FakeRepository()

    result = asyncio.run(submit(
        payload,
        repository=repository,
        orchestrator=FakeOrchestrator(repository),
        content_resolver=lambda _: b"demo evidence",
    ))

    assert result.status_code == 400
    assert result.body["code"] == "INVALID_BLOB_PATH"
    assert repository.operations == []


def test_request_id_rejects_cosmos_invalid_characters():
    payload = _payload(b"demo evidence")
    payload["requestId"] = "CASE/2026"
    repository = FakeRepository()

    result = asyncio.run(submit(
        payload,
        repository=repository,
        orchestrator=FakeOrchestrator(repository),
        content_resolver=lambda _: b"demo evidence",
    ))

    assert result.status_code == 400
    assert result.body["code"] == "INVALID_REQUEST_ID"


def test_request_id_rejects_values_over_durable_limit():
    payload = _payload(b"demo evidence")
    payload["requestId"] = "A" * 101
    repository = FakeRepository()

    result = asyncio.run(submit(
        payload,
        repository=repository,
        orchestrator=FakeOrchestrator(repository),
        content_resolver=lambda _: b"demo evidence",
    ))

    assert result.status_code == 400
    assert result.body["code"] == "INVALID_REQUEST_ID"


def test_request_id_must_be_string():
    payload = _payload(b"demo evidence")
    payload["requestId"] = 123
    repository = FakeRepository()

    result = asyncio.run(submit(
        payload,
        repository=repository,
        orchestrator=FakeOrchestrator(repository),
        content_resolver=lambda _: b"demo evidence",
    ))

    assert result.status_code == 400
    assert repository.operations == []


def test_normalization_failure_is_rejected_and_audited():
    content = b"invalid Office package"
    repository = FakeRepository()

    def fail_normalization(request_id: str, document: dict, data: bytes) -> dict:
        raise ValueError("invalid package")

    result = asyncio.run(submit(
        _payload(content),
        repository=repository,
        orchestrator=FakeOrchestrator(repository),
        content_resolver=lambda _: content,
        document_preparer=fail_normalization,
    ))

    assert result.status_code == 400
    assert result.body["code"] == "DOCUMENT_NORMALIZATION_FAILED"
    assert result.body["errors"][0]["affectedDocumentId"] == "1"
    assert repository.events[-1]["eventType"] == "INTAKE_REJECTED"