"""Azure adapters for the intake stage."""

from __future__ import annotations

import json
import os
from typing import Any

from azure.core.exceptions import ResourceNotFoundError
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.identity import ManagedIdentityCredential
from azure.storage.blob import BlobServiceClient

from src.platform.intake.office_normalization import OFFICE_MIME_TYPES, normalize_office_document


class AzureIntakeRepository:
    """Store demo intake state in the existing Cosmos DB containers."""

    def __init__(self) -> None:
        credential = ManagedIdentityCredential(client_id=os.getenv("MANAGED_IDENTITY_CLIENT_ID"))
        client = CosmosClient(os.environ["COSMOS_DB_ENDPOINT"], credential=credential)
        database = client.get_database_client(os.environ["COSMOS_DB_DATABASE"])
        self._cases = database.get_container_client(os.getenv("COSMOS_DB_CONTAINER", "inspections"))
        self._inbound = database.get_container_client(
            os.getenv("COSMOS_DB_INBOUND_CONTAINER", "inbound-requests")
        )
        self._audit = database.get_container_client(
            os.getenv("COSMOS_DB_CALLBACK_LOG_CONTAINER", "callback-log")
        )

    def get_case_status(self, request_id: str) -> str | None:
        try:
            case = self._cases.read_item(item=request_id, partition_key=request_id)
        except CosmosResourceNotFoundError:
            return None
        return case.get("status")

    def save_inbound(self, payload: dict) -> None:
        self._inbound.upsert_item({**payload, "id": payload["requestId"]})

    def create_received_case(self, case: dict) -> None:
        self._cases.upsert_item(case)

    def append_audit_event(self, event: dict) -> None:
        self._audit.upsert_item(event)


class AzureBlobContentResolver:
    """Read staged evidence bytes from the existing raw uploads container."""

    def __init__(self) -> None:
        credential = ManagedIdentityCredential(client_id=os.getenv("MANAGED_IDENTITY_CLIENT_ID"))
        self.container = BlobServiceClient(
            account_url=os.environ["RAW_UPLOADS_STORAGE_URL"],
            credential=credential,
        ).get_container_client(os.getenv("RAW_UPLOADS_CONTAINER", "raw-uploads"))

    def __call__(self, document: dict) -> bytes:
        try:
            return self.container.download_blob(document["blobPath"]).readall()
        except ResourceNotFoundError as error:
            raise FileNotFoundError(document["blobPath"]) from error

    def prepare(self, request_id: str, document: dict, content: bytes) -> dict:
        mime_type = document.get("mimeType", "")
        if mime_type not in OFFICE_MIME_TYPES:
            return document
        markdown = normalize_office_document(content, mime_type)
        document_id = str(document["documentTypeId"])
        checksum = str(document["checksum"]).lower()
        normalized_path = f"artifacts/{request_id}/normalized/{document_id}-{checksum}.md"
        self.container.upload_blob(normalized_path, markdown.encode("utf-8"), overwrite=True)
        return {**document, "normalizedBlobPath": normalized_path}


class DurableOrchestrationGateway:
    """Adapt an Azure Durable client to the intake service contract."""

    def __init__(self, client: Any, request: Any) -> None:
        self._client = client
        self._request = request

    async def get_status(self, instance_id: str) -> str | None:
        status = await self._client.get_status(instance_id)
        if status is None:
            return None
        runtime_status = status.runtime_status
        return getattr(runtime_status, "value", str(runtime_status))

    async def start(self, instance_id: str, payload: dict) -> str:
        started_id = await self._client.start_new(
            "evidence_intake_orchestrator",
            instance_id=instance_id,
            client_input=payload,
        )
        response = self._client.create_check_status_response(self._request, started_id)
        response_body = json.loads(response.get_body())
        return response_body["statusQueryGetUri"]