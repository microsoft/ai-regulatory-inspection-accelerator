"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Orchestration — Pipeline Orchestrator

Sequences the five pipeline activities as a Durable Functions orchestrator:

    Pre-Validation -> Extraction -> Reasoning -> Rules & Policy -> Delivery

This module is decorator-free and has zero dependency on azure-functions /
azure-durable-functions - it only relies on the DurableOrchestrationContext
duck-typed interface (get_input, call_activity_with_retry, is_replaying,
current_utc_datetime). This keeps the orchestration sequencing logic:
  - Unit-testable without the Azure Functions runtime installed
  - Deterministic (no direct I/O, no randomness, no async SDK calls),
    which Durable Functions requires for safe replay on restart-resume
  - Reusable by any template - activity names are the only industry-specific
    detail, and even those are pipeline-stage names, not literal document or
    business-rule content (see ADR-022: Agent and Stage orchestration
    architecture).

The actual delivery mechanism is connector-specific - see
connectors/sdk/base_connector.py - the orchestrator itself never constructs or
sends a callback, it only invokes the Delivery Agent activity.
"""

from collections.abc import Callable, Generator
from typing import Any

# Default Durable Functions activity names for the five pipeline agents.
# A reference implementation's function_app.py registers its activities
# under these names by default; override via `activity_names` if a
# deployment needs different Durable Functions activity names.
DEFAULT_ACTIVITY_NAMES: dict[str, str] = {
    "pre_validation": "pre_validation_activity",
    "di_extraction": "di_extraction_activity",
    "reasoning": "reasoning_activity",
    "rules_policy": "rules_policy_activity",
    "delivery": "delivery_activity",
}


def run_pipeline(
    context: Any,
    activity_names: dict[str, str] | None = None,
    retry_policy: Any = None,
    track_event: Callable[..., None] | None = None,
) -> Generator[Any, Any, None]:
    """
    Durable Functions orchestrator generator for the Core Platform's
    inspection pipeline.

    Args:
        context: A DurableOrchestrationContext (or a duck-typed equivalent
            exposing get_input(), call_activity_with_retry(name, retry_policy,
            input), is_replaying, and current_utc_datetime). All activity
            calls are made via `yield context.call_activity_with_retry(...)`
            so the Durable Functions runtime can checkpoint and safely
            resume this orchestration after a host restart.
        activity_names: Optional override of the five Durable Functions
            activity names (see DEFAULT_ACTIVITY_NAMES): pre_validation,
            di_extraction, reasoning, rules_policy, delivery. The underlying
            activity implementations are template/deployment-specific.
        retry_policy: Passed through unchanged to every
            call_activity_with_retry call. Typically an
            azure.durable_functions.RetryOptions instance; accepted here as
            an opaque object so this module has no azure-functions dependency.
        track_event: Optional telemetry callback, called as
            track_event(name, request_id=..., properties=..., measurements=...)
            only when `not context.is_replaying` (so telemetry fires exactly
            once per real execution, never on replay).

    Sequence:
    Pre-Validation -> Extraction -> Reasoning -> Rules & Policy -> Delivery

    On any stage failure, Delivery is still invoked so the adopting system
    always receives a decision callback regardless of outcome (see
    connectors/sdk/base_connector.py deliver_decision).
    """
    names = {**DEFAULT_ACTIVITY_NAMES, **(activity_names or {})}
    payload: dict = context.get_input()
    request_id: str = payload["requestId"]
    pipeline_started_at: str = context.current_utc_datetime.isoformat()

    def _emit(event_name: str, **kwargs) -> None:
        if track_event is not None and not context.is_replaying:
            track_event(event_name, request_id=request_id, **kwargs)

    # ── Pre-Validation Agent ─────────────────────────────────────────────
    pre_validation_result: dict = yield context.call_activity_with_retry(
        names["pre_validation"], retry_policy, payload
    )

    if not pre_validation_result["passed"]:
        _emit("PreValidationFailed", properties={"errorCount": str(len(pre_validation_result.get("errors", [])))})
        yield context.call_activity_with_retry(
            names["delivery"], retry_policy,
            {
                "payload": payload,
                "status": "PRE_VALIDATION_FAILED",
                "findings": [],
                "errors": pre_validation_result["errors"],
                "recommendation": "FAIL",
                "confidence": None,
                "summary": "Submission failed pre-validation. See errors for details.",
                "verdictId": None,
                "pipelineStartedAt": pipeline_started_at,
            }
        )
        return

    # Apply deduplicated document list for all downstream agents.
    # The adopting system's connector cannot always prevent duplicate
    # submissions upstream - we strip them here and warn in the verdict.
    dup_warnings: list[dict] = pre_validation_result.get("warnings", [])
    if pre_validation_result.get("documents") is not None:
        payload = {**payload, "documents": pre_validation_result["documents"]}

    # ── DI Extraction Agent ───────────────────────────────────────────────
    di_extraction_result: dict = yield context.call_activity_with_retry(
        names["di_extraction"], retry_policy, payload
    )

    if not di_extraction_result["success"]:
        _emit("DIExtractionFailed", properties={"errorCount": str(len(di_extraction_result.get("errors", [])))})
        yield context.call_activity_with_retry(
            names["delivery"], retry_policy,
            {
                "payload": payload,
                "status": "PIPELINE_ERROR",
                "findings": [],
                "errors": di_extraction_result["errors"],
                "recommendation": "HOLD",
                "confidence": None,
                "summary": "Document extraction failed. Manual review required.",
                "verdictId": None,
                "pipelineStartedAt": pipeline_started_at,
            }
        )
        return

    # ── Reasoning Agent ───────────────────────────────────────────────────
    reasoning_result: dict = yield context.call_activity_with_retry(
        names["reasoning"], retry_policy,
        {
            "payload": payload,
            "extractedFields": di_extraction_result["extractedFields"],
        }
    )

    if not reasoning_result["success"]:
        _emit(
            "ReasoningFailed",
            properties={"errorCount": str(len(reasoning_result.get("errors", [])))},
        )
        yield context.call_activity_with_retry(
            names["delivery"], retry_policy,
            {
                "payload": payload,
                "status": "PIPELINE_ERROR",
                "findings": [],
                "errors": reasoning_result.get("errors", []),
                "recommendation": "HOLD",
                "confidence": None,
                "summary": "Evidence reasoning failed. Manual review required.",
                "verdictId": None,
                "pipelineStartedAt": pipeline_started_at,
            }
        )
        return

    # ── Rules & Policy Agent ──────────────────────────────────────────────
    rules_policy_result: dict = yield context.call_activity_with_retry(
        names["rules_policy"], retry_policy,
        {
            "payload": payload,
            "extractedFields": di_extraction_result["extractedFields"],
            "evidenceMap": reasoning_result.get(
                "evidenceMap", di_extraction_result["extractedFields"]
            ),
            "reasoningFindings": reasoning_result.get("findings", []),
            "reasoningDocumentChecks": reasoning_result.get("documentChecks", []),
        }
    )

    # ── Delivery Agent ─────────────────────────────────────────────────────
    yield context.call_activity_with_retry(
        names["delivery"], retry_policy,
        {
            "payload": payload,
            "status": "COMPLETED",
            "findings": dup_warnings + rules_policy_result["findings"],
            "documentChecks": rules_policy_result.get("documentChecks", []),
            "errors": [],
            "recommendation": rules_policy_result["recommendation"],
            "confidence": rules_policy_result["confidence"],
            "aiRiskLevel": rules_policy_result.get("aiRiskLevel"),
            "summary": rules_policy_result["summary"],
            "verdictId": rules_policy_result.get("verdictId"),
            "pipelineStartedAt": pipeline_started_at,
        }
    )

    _emit(
        "PipelineCompleted",
        properties={
            "recommendation": rules_policy_result.get("recommendation", ""),
            "findingsCount": str(len(rules_policy_result.get("findings", []))),
        },
        measurements={"confidence": rules_policy_result.get("confidence", 0.0)},
    )
