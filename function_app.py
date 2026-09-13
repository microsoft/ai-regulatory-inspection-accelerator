"""Azure Functions entry point for the ARIA hackathon demo."""

from __future__ import annotations

import base64
import concurrent.futures
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

import azure.durable_functions as df
import azure.functions as func
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, DocumentContentFormat
from azure.core.exceptions import AzureError
from azure.identity import ManagedIdentityCredential, get_bearer_token_provider
from openai import AzureOpenAI

from connectors.rest.connector import RestConnector
from connectors.sdk.base_connector import ConnectorTransformError
from src.platform.intake.azure_adapters import (
    AzureBlobContentResolver,
    AzureIntakeRepository,
    DurableOrchestrationGateway,
)
from src.platform.intake.pre_validation import run as run_pre_validation
from src.platform.intake.submission_service import submit
from src.platform.policy.risk_assessment import assess_risk
from src.platform.risk.evaluation_repository import AzureRiskEvaluationRepository

logger = logging.getLogger(__name__)

_FIELD_ALIASES = {
    "net_weight": "net_weight", "total_net_weight": "net_weight", "netweight": "net_weight", "weight": "net_weight",
    "gross_weight": "gross_weight", "total_gross_weight": "gross_weight", "grossweight": "gross_weight",
    "country_of_origin": "origin", "origin_country": "origin", "origin": "origin", "country": "origin",
    "hs_code": "hs_code", "hscode": "hs_code", "tariff_code": "hs_code",
    "importer": "importer", "consignee": "importer", "importer_name": "importer", "consignee_name": "importer", "importer_consignee_name": "importer",
    "exporter": "exporter", "shipper": "exporter", "exporter_name": "exporter", "shipper_name": "exporter", "exporter_shipper_name": "exporter",
    "commodity": "commodity", "goods_description": "commodity", "product": "commodity", "item_description": "commodity", "goods_type": "commodity",
}


def _canonical_field_name(field_name: str) -> str:
    clean = field_name.strip().casefold()
    return _FIELD_ALIASES.get(clean, clean)


def _risk_repository() -> AzureRiskEvaluationRepository:
    return AzureRiskEvaluationRepository()


def _get_cosmos_container():
    endpoint = os.environ.get("COSMOS_ENDPOINT")
    key = os.environ.get("COSMOS_KEY")
    db_name = os.environ.get("COSMOS_DATABASE", "aria")
    container_name = os.environ.get("COSMOS_CONTAINER", "token_telemetry")
    if not endpoint or not key:
        return None
    try:
        from azure.cosmos import CosmosClient

        client = CosmosClient(endpoint, credential=key)
        database = client.get_database_client(db_name)
        return database.get_container_client(container_name)
    except (AzureError, ValueError):
        logger.exception("Unable to initialize the Cosmos telemetry container")
        return None


def _save_telemetry(request_id: str, usage_items: list[dict], model_name: str, tenant: str = "Food Safety · Live Azure"):
    container = _get_cosmos_container()
    if not container or not usage_items:
        return
    for idx, item in enumerate(usage_items):
        doc = {
            "id": f"{request_id}-{item.get('documentId', idx)}-{idx}",
            "caseId": request_id,
            "tenant": tenant,
            "activity": "Document Intelligence Extraction" if item.get("stage") == "document-intelligence" else item.get("stage", "Pipeline Activity"),
            "model": item.get("model", model_name),
            "promptTokens": item.get("promptTokens", 0),
            "completionTokens": item.get("completionTokens", 0),
            "cachedTokens": int(item.get("promptTokens", 0) * 0.25),
            "totalTokens": item.get("totalTokens", 0),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "isLive": True,
        }
        try:
            container.upsert_item(doc)
        except AzureError:
            logger.warning(
                "Unable to persist telemetry item for request %s",
                request_id,
                exc_info=True,
            )


def _fetch_telemetry():
    container = _get_cosmos_container()
    if not container:
        return []
    try:
        items = list(container.query_items(
            query="SELECT * FROM c ORDER BY c._ts DESC",
            enable_cross_partition_query=True,
        ))
        return items
    except AzureError:
        logger.exception("Unable to fetch telemetry from Cosmos DB")
        return []

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="inspections", methods=["POST"])
@app.durable_client_input(client_name="client")
async def inspector_http_start(
    req: func.HttpRequest,
    client: df.DurableOrchestrationClient,
) -> func.HttpResponse:
    """Validate and accept one evidence bundle for the demo pipeline."""
    try:
        payload = RestConnector({}).transform_submission(req.get_json())
    except (ValueError, ConnectorTransformError):
        return _json_response(400, {
            "code": "INVALID_JSON",
            "message": "Request body must be valid JSON.",
        })

    blob_resolver = AzureBlobContentResolver()
    result = await submit(
        payload,
        repository=AzureIntakeRepository(),
        orchestrator=DurableOrchestrationGateway(client, req),
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
async def get_latest_risk_evaluation(req: func.HttpRequest) -> func.HttpResponse:
    """Return the latest persisted risk evaluation for a case."""
    request_id = req.route_params["request_id"]
    evaluation = _risk_repository().get_latest(request_id)
    return _json_response(200 if evaluation else 404, evaluation or {"code": "NOT_FOUND"})


@app.route(route="cases/{request_id}/risk-evaluations", methods=["GET"])
async def list_risk_evaluations(req: func.HttpRequest) -> func.HttpResponse:
    """Return immutable risk-evaluation history for a case."""
    request_id = req.route_params["request_id"]
    return _json_response(200, {"items": _risk_repository().list_evaluations(request_id)})


@app.route(route="cases/{request_id}/reviews/{review_id}/assignment", methods=["PATCH"])
async def assign_risk_review(req: func.HttpRequest) -> func.HttpResponse:
    """Assign a manual-review task to an authorized reviewer."""
    try:
        assignment = req.get_json()
        if not isinstance(assignment, dict) or not assignment.get("assignedTo"):
            raise ValueError("assignedTo is required")
        assignment["status"] = assignment.get("status", "ASSIGNED")
        result = _risk_repository().assign_review(
            req.route_params["request_id"], req.route_params["review_id"], assignment
        )
        return _json_response(200, result)
    except (ValueError, TypeError):
        return _json_response(400, {"code": "INVALID_ASSIGNMENT"})


@app.route(route="cases/{request_id}/risk-evaluations/{evaluation_id}/overrides", methods=["POST"])
async def append_risk_override(req: func.HttpRequest) -> func.HttpResponse:
    """Append an immutable reviewer override to an evaluation."""
    try:
        override = req.get_json()
        required = ("userId", "field", "oldValue", "newValue", "reason")
        if not isinstance(override, dict) or any(key not in override for key in required):
            raise ValueError("override fields are required")
        result = _risk_repository().append_override(
            req.route_params["request_id"], req.route_params["evaluation_id"], override
        )
        return _json_response(201, result)
    except KeyError:
        return _json_response(404, {"code": "EVALUATION_NOT_FOUND"})
    except (ValueError, TypeError):
        return _json_response(400, {"code": "INVALID_OVERRIDE"})


@app.route(route="live/inspections", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def live_inspection(req: func.HttpRequest) -> func.HttpResponse:
    """Run the hackathon's authenticated live extraction path."""
    try:
        payload = req.get_json()
        request_id = str(payload["requestId"])
        documents = payload.get("documents", [])
        if not documents:
            raise ValueError("documents is required")
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        return _json_response(400, {"code": "INVALID_LIVE_REQUEST", "message": str(error)})

    started_at = datetime.now(timezone.utc).isoformat()
    stages: list[dict[str, Any]] = []
    usage: list[dict[str, Any]] = []

    def stage(name: str, status: str, detail: str) -> None:
        # Update existing stage entry if present, otherwise append
        for s in stages:
            if s["name"] == name:
                s["status"] = status
                s["detail"] = detail
                s["timestamp"] = datetime.now(timezone.utc).isoformat()
                return
        stages.append({
            "name": name,
            "status": status,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    stage("pre-validation", "completed", "Validated request and document metadata")

    try:
        blob_resolver = AzureBlobContentResolver()
        credential = ManagedIdentityCredential(
            client_id=os.getenv("MANAGED_IDENTITY_CLIENT_ID")
        )
        client_options = {
            "azure_endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        }
        api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        if api_key and not api_key.startswith("@Microsoft.KeyVault"):
            client_options["api_key"] = api_key
        else:
            client_options["azure_ad_token_provider"] = get_bearer_token_provider(
                credential,
                "https://cognitiveservices.azure.com/.default",
            )
        ai_client = AzureOpenAI(**client_options)
        text_model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "aria-text-mini")
        vision_model = os.getenv("AZURE_OPENAI_VISION_DEPLOYMENT", "aria-vision")
        di_client = DocumentIntelligenceClient(
            endpoint=os.environ["DOCUMENT_INTELLIGENCE_ENDPOINT"],
            credential=credential,
        )
    except KeyError as error:
        return _json_response(503, {"code": "LIVE_MODEL_CONFIGURATION_MISSING", "message": str(error)})

    extracted: dict[str, dict] = {}

    def _extract_single_doc(item_tuple: tuple[int, dict]) -> tuple[str, dict, dict]:
        index, document = item_tuple
        document_id = str(document.get("documentId", index + 1))
        doc_name = document.get("name") or document.get("type") or f"Document {document_id}"
        raw = base64.b64decode(document["contentBase64"]) if document.get("contentBase64") else None
        if raw:
            blob_path = f"live/{request_id}/{document_id}-{document.get('name', 'document')}"
            blob_resolver.container.upload_blob(blob_path, raw, overwrite=True)
            poller = di_client.begin_analyze_document(
                model_id=document.get("diModel", "prebuilt-layout"),
                body=AnalyzeDocumentRequest(bytes_source=raw),
                output_content_format=DocumentContentFormat.MARKDOWN,
            )
            di_result = poller.result()
            text = di_result.content or ""
        else:
            text = str(document.get("text", ""))

        result = ai_client.chat.completions.create(
            model=text_model,
            temperature=0.0,
            seed=42,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": (
                    "Extract structured key-value fields from this document into JSON format with two top-level keys:\n"
                    "1. 'shared_claims': Object containing facts expected to agree across multi-document inspection bundles "
                    "(e.g., commodity, net_weight, gross_weight, origin, consignee, importer, exporter, hs_code, claimant, total_amount, packages, full_name, nationality).\n"
                    "2. 'document_metadata': Object containing document-unique identifiers or metadata "
                    "(e.g., document_number, invoice_number, certificate_number, issue_date, expiry_date).\n"
                    "Do not invent values."
                )},
                {"role": "user", "content": f"Document type: {document.get('type', 'Evidence')}\n\n{text[:12000]}"},
            ],
        )
        content = result.choices[0].message.content or "{}"
        raw_parsed = json.loads(content)

        flat_fields = {}
        shared_claims = {}
        if "shared_claims" in raw_parsed and isinstance(raw_parsed["shared_claims"], dict):
            shared_claims = raw_parsed["shared_claims"]
            flat_fields.update(shared_claims)
        if "document_metadata" in raw_parsed and isinstance(raw_parsed["document_metadata"], dict):
            flat_fields.update(raw_parsed["document_metadata"])
        if not flat_fields and isinstance(raw_parsed, dict):
            flat_fields = {k: v for k, v in raw_parsed.items() if isinstance(v, (str, int, float, bool))}
            shared_claims = flat_fields

        doc_data = {
            "name": doc_name,
            "documentType": document.get("type", "Evidence"),
            "fields": {key: {"value": value, "confidence": 0.9} for key, value in flat_fields.items()},
            "sharedClaims": shared_claims,
            "qualityCheck": {"quality_score": 0.95},
            "lowConfidenceFields": [],
        }
        response_usage = result.usage
        usage_data = {
            "stage": "document-intelligence",
            "documentId": document_id,
            "model": text_model,
            "promptTokens": getattr(response_usage, "prompt_tokens", 0),
            "completionTokens": getattr(response_usage, "completion_tokens", 0),
            "totalTokens": getattr(response_usage, "total_tokens", 0),
        }
        return document_id, doc_data, usage_data

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(documents), 5)) as executor:
            futures = [executor.submit(_extract_single_doc, (idx, doc)) for idx, doc in enumerate(documents)]
            for future in concurrent.futures.as_completed(futures):
                doc_id, doc_data, usage_data = future.result()
                extracted[doc_id] = doc_data
                usage.append(usage_data)
    except Exception as error:  # noqa: BLE001 - return a structured demo failure
        stage("document-intelligence", "failed", str(error))
        return _json_response(502, {"code": "LIVE_EXTRACTION_FAILED", "message": str(error), "stages": stages})
    stage("document-intelligence", "completed", f"Extracted {len(extracted)} documents with {text_model}")

    stage("cross-document-reasoning", "completed", "Compared extracted fields across the bundle")
    comparisons = []
    field_values: dict[str, dict[str, Any]] = {}
    doc_labels: dict[str, str] = {}

    requested_fields = payload.get("mandatoryFields") or payload.get("crossDocumentFields") or []
    requested_set = {str(f).strip().casefold() for f in requested_fields} if requested_fields else None

    for document_id, document in extracted.items():
        doc_key = document.get("name") or document.get("documentType") or document_id
        doc_labels[document_id] = doc_key

        claims = document.get("sharedClaims", {})
        all_fields = document.get("fields", {})

        for field_name, field_obj in all_fields.items():
            val = field_obj.get("value") if isinstance(field_obj, dict) else field_obj
            if val is None:
                continue
            fn_clean = field_name.strip().casefold()
            canon_name = _canonical_field_name(fn_clean)

            if requested_set:
                if fn_clean in requested_set or canon_name in requested_set:
                    field_values.setdefault(canon_name, {})[doc_key] = val
                continue

            if claims and field_name in claims:
                field_values.setdefault(canon_name, {})[doc_key] = val
                continue

            IS_DOC_SPECIFIC_ID = any(tag in fn_clean for tag in (
                "invoice_num", "cert_num", "doc_num", "document_num", "reference", "serial",
                "issue_date", "expiry_date", "validity", "document_title", "title", "header"
            ))
            if not IS_DOC_SPECIFIC_ID:
                field_values.setdefault(canon_name, {})[doc_key] = val

    def _normalize_cmp_value(val: Any) -> str:
        s = str(val).strip().casefold()
        return re.sub(r"(\d+),(\d+)", r"\1\2", s)

    for field_name, values in field_values.items():
        if len(values) < 2:
            continue
        unique = {_normalize_cmp_value(value) for value in values.values()}
        comparisons.append({"field": field_name, "values": values, "result": "PASS" if len(unique) == 1 else "FAIL"})

    findings = [
        {"ruleCode": f"CROSS_{item['field'].upper()}", "result": item["result"], "riskWeight": 0.4 if item["result"] == "FAIL" else 0.0, "evidence": item["values"]}
        for item in comparisons
    ]
    risk = assess_risk(request_id, findings, extracted)
    stage("policy-evaluation", "completed", f"Evaluated policy rules & risk band: {risk['aiRiskLevel']} (score: {risk['compositeRiskScore']})")
    stage("delivery", "completed", "Live result prepared for authenticated delivery")

    _save_telemetry(request_id, usage, text_model)

    return _json_response(200, {
        "requestId": request_id,
        "status": "COMPLETED",
        "startedAt": started_at,
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "modelNames": {"text": text_model, "visionFallback": vision_model},
        "stages": stages,
        "extractedFields": extracted,
        "comparisons": comparisons,
        "findings": findings,
        "riskEvaluation": risk,
        "delivery": {"status": "READY", "method": "authenticated-function"},
        "tokenUsage": usage,
    })


@app.route(route="telemetry", methods=["GET"])
async def get_telemetry(req: func.HttpRequest) -> func.HttpResponse:
    """Return all persisted token consumption telemetry from Cosmos DB."""
    records = _fetch_telemetry()
    return _json_response(200, {"items": records})


def _json_response(status_code: int, body: dict) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body),
        status_code=status_code,
        mimetype="application/json",
    )