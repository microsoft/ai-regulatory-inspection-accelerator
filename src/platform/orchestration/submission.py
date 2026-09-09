"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Orchestration — Submission Guard

Pure decision logic for whether a new pipeline submission should be accepted,
rejected as a duplicate in-flight request, or rejected because the case was
already completed. Decoupled from the Azure Functions HTTP request/response
types and the Durable Functions client SDK so it can be unit tested without
either dependency, and reused by any connector's HTTP starter.

Idempotency checks only - schema validation and the HTTP response construction
are connector/API-layer concerns, not orchestration.
"""

from enum import Enum


class SubmissionDecision(str, Enum):
    ACCEPT = "ACCEPT"
    DUPLICATE_IN_PROGRESS = "DUPLICATE_IN_PROGRESS"
    ALREADY_COMPLETED = "ALREADY_COMPLETED"


# Orchestration runtime statuses (mirrors
# azure.durable_functions.OrchestrationRuntimeStatus) that indicate an
# existing orchestration instance is still in flight for this request ID.
IN_PROGRESS_STATUSES = frozenset({"Pending", "Running", "ContinuedAsNew"})

# Case status indicating the pipeline has already delivered a final decision
# for this request ID.
COMPLETED_STATUS = "COMPLETED"


def evaluate_submission(
    existing_orchestration_status: str | None,
    existing_case_status: str | None,
) -> SubmissionDecision:
    """
    Decide whether to start a new pipeline orchestration for this request ID.

    This is the restart-resume safety guard: if the same request ID is
    resubmitted while an orchestration instance is already in flight (e.g.
    the caller retried after a network timeout, or a Durable Functions host
    restarted and resumed the original instance), the resubmission is
    rejected rather than starting a second, conflicting orchestration
    instance for the same case. If the case already completed, resubmission
    is also rejected - the caller should read the existing verdict instead.

    Args:
        existing_orchestration_status: The `runtime_status` of an existing
            Durable Functions orchestration instance with this request ID as
            its instance ID (e.g. from `client.get_status(request_id)`), or
            None if no instance exists yet.
        existing_case_status: The `status` field of an existing case record
            for this request ID (e.g. from a case store lookup), or None if
            no case record exists yet.

    Returns:
        SubmissionDecision.ACCEPT - safe to start a new orchestration instance.
        SubmissionDecision.DUPLICATE_IN_PROGRESS - an instance is already running.
        SubmissionDecision.ALREADY_COMPLETED - the case already has a final decision.
    """
    if existing_orchestration_status in IN_PROGRESS_STATUSES:
        return SubmissionDecision.DUPLICATE_IN_PROGRESS
    if existing_case_status == COMPLETED_STATUS:
        return SubmissionDecision.ALREADY_COMPLETED
    return SubmissionDecision.ACCEPT
