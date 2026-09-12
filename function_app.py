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
from src.platform.risk.evaluation_repository import AzureRiskEvaluationRepository


def _risk_repository() -> AzureRiskEvaluationRepository:
    return AzureRiskEvaluationRepository()

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


@app.activity_trigger(input_name="input_data")
def risk_persistence_activity(input_data: dict) -> dict:
    """Persist one immutable risk evaluation before delivery."""
    evaluation = input_data.get("riskEvaluation")
    if not evaluation:
        return {"persisted": False, "reason": "risk evaluation unavailable"}
    return {"persisted": True, "evaluation": _risk_repository().save_evaluation(evaluation)}


@app.route(route="cases/{request_id}/risk-evaluations/latest", methods=["GET"])
async def get_latest_risk_evaluation(request: func.HttpRequest) -> func.HttpResponse:
    """Return the latest persisted risk evaluation for a case."""
    request_id = request.route_params["request_id"]
    evaluation = _risk_repository().get_latest(request_id)
    return _json_response(200 if evaluation else 404, evaluation or {"code": "NOT_FOUND"})


@app.route(route="cases/{request_id}/risk-evaluations", methods=["GET"])
async def list_risk_evaluations(request: func.HttpRequest) -> func.HttpResponse:
    """Return immutable risk-evaluation history for a case."""
    request_id = request.route_params["request_id"]
    return _json_response(200, {"items": _risk_repository().list_evaluations(request_id)})


@app.route(route="cases/{request_id}/reviews/{review_id}/assignment", methods=["PATCH"])
async def assign_risk_review(request: func.HttpRequest) -> func.HttpResponse:
    """Assign a manual-review task to an authorized reviewer."""
    try:
        assignment = request.get_json()
        if not isinstance(assignment, dict) or not assignment.get("assignedTo"):
            raise ValueError("assignedTo is required")
        assignment["status"] = assignment.get("status", "ASSIGNED")
        result = _risk_repository().assign_review(
            request.route_params["request_id"], request.route_params["review_id"], assignment
        )
        return _json_response(200, result)
    except (ValueError, TypeError):
        return _json_response(400, {"code": "INVALID_ASSIGNMENT"})


@app.route(route="cases/{request_id}/risk-evaluations/{evaluation_id}/overrides", methods=["POST"])
async def append_risk_override(request: func.HttpRequest) -> func.HttpResponse:
    """Append an immutable reviewer override to an evaluation."""
    try:
        override = request.get_json()
        required = ("userId", "field", "oldValue", "newValue", "reason")
        if not isinstance(override, dict) or any(key not in override for key in required):
            raise ValueError("override fields are required")
        result = _risk_repository().append_override(
            request.route_params["request_id"], request.route_params["evaluation_id"], override
        )
        return _json_response(201, result)
    except KeyError:
        return _json_response(404, {"code": "EVALUATION_NOT_FOUND"})
    except (ValueError, TypeError):
        return _json_response(400, {"code": "INVALID_OVERRIDE"})


def _json_response(status_code: int, body: dict) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
    )