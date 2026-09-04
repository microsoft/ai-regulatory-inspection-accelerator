"""Azure Functions entry point for the ARIA hackathon demo."""

from __future__ import annotations

import json

import azure.durable_functions as df
import azure.functions as func

from connectors.rest.connector import RestConnector
from connectors.sdk.base_connector import ConnectorTransformError
from src.platform.intake.azure_adapters import (
    AzureBlobContentResolver,
    AzureIntakeRepository,
    DurableOrchestrationGateway,
)
from src.platform.intake.pre_validation import run as run_pre_validation
from src.platform.intake.submission_service import submit

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="inspections", methods=["POST"])
@app.durable_client_input(client_name="client")
async def inspector_http_start(
    request: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    """Validate and accept one evidence bundle for the demo pipeline."""
    try:
        payload = RestConnector({}).transform_submission(request.get_json())
    except (ValueError, ConnectorTransformError):
        return _json_response(400, {
            "code": "INVALID_JSON",
            "message": "Request body must be valid JSON.",
        })

    blob_resolver = AzureBlobContentResolver()
    result = await submit(
        payload,
        repository=AzureIntakeRepository(),
        orchestrator=DurableOrchestrationGateway(client, request),
        content_resolver=blob_resolver,
        document_preparer=blob_resolver.prepare,
    )
    return _json_response(result.status_code, result.body)


@app.orchestration_trigger(context_name="context")
def evidence_intake_orchestrator(context: df.DurableOrchestrationContext):
    """Run Activity 1 and stop at the boundary before AI extraction."""
    payload = context.get_input()
    validation = yield context.call_activity("pre_validation_activity", payload)
    return {
        "requestId": payload["requestId"],
        "status": "READY_FOR_EXTRACTION" if validation["passed"] else "PRE_VALIDATION_FAILED",
        "errors": validation["errors"],
        "warnings": validation["warnings"],
    }


@app.activity_trigger(input_name="payload")
def pre_validation_activity(payload: dict) -> dict:
    """Repeat deterministic metadata checks inside Durable execution."""
    return run_pre_validation(payload)


def _json_response(status_code: int, body: dict) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
    )