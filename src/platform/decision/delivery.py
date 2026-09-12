"""Template-driven decision construction and connector delivery."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from connectors.sdk.base_connector import BaseConnector, ConnectorDeliveryError

RETRY_DELAYS_SECONDS = (5.0, 30.0, 120.0)


def build_decision(delivery_input: dict, vocabulary: dict) -> dict:
    """Build a connector-neutral public decision from the policy result."""
    payload = delivery_input["payload"]
    internal = str(delivery_input.get("recommendation") or "HOLD")
    mapped = vocabulary.get(internal)
    if not isinstance(mapped, dict):
        raise ValueError(f"Decision vocabulary does not define '{internal}'.")
    risk_evaluation = delivery_input.get("riskEvaluation") or delivery_input.get(
        "riskAssessment", {}
    )
    return {
        "requestId": str(payload["requestId"]),
        "status": delivery_input.get("status", "COMPLETED"),
        "recommendation": str(mapped["recommendation"]),
        "recommendationLabel": str(mapped["label"]),
        "summary": delivery_input.get("summary", ""),
        "aiRiskLevel": delivery_input.get("aiRiskLevel"),
        "compositeRiskScore": delivery_input.get(
            "compositeRiskScore", delivery_input.get("riskScore")
        ),
        "confidence": delivery_input.get("confidence"),
        "verdictId": delivery_input.get("verdictId"),
        "riskEvaluation": risk_evaluation,
        "findings": delivery_input.get("findings", []),
        "documentChecks": delivery_input.get("documentChecks", []),
        "errors": delivery_input.get("errors", []),
    }


async def _await_if_needed(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


async def deliver_decision(
    delivery_input: dict,
    *,
    connector: BaseConnector,
    vocabulary: dict,
    max_attempts: int = 3,
    retry_delays: tuple[float, ...] = RETRY_DELAYS_SECONDS,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict:
    """Deliver a public decision with bounded retries and status reporting."""
    decision = build_decision(delivery_input, vocabulary)
    request_id = decision["requestId"]
    await _await_if_needed(connector.report_status(request_id, "DELIVERING"))

    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            acknowledgement = await _await_if_needed(connector.deliver_decision(decision))
            await _await_if_needed(
                connector.report_status(request_id, decision["status"])
            )
            return {
                "delivered": True,
                "deliveryMethod": "connector",
                "attempts": attempt,
                "acknowledgement": acknowledgement,
                "decision": decision,
            }
        except Exception as exc:  # noqa: BLE001 - connector errors are retried uniformly
            last_error = exc
            if attempt < max_attempts:
                delay = retry_delays[min(attempt - 1, len(retry_delays) - 1)]
                await sleep(delay)

    error = {
        "code": "DELIVERY_FAILED",
        "message": str(last_error) if last_error else "Decision delivery failed.",
    }
    await _await_if_needed(connector.report_status(request_id, "DELIVERY_FAILED", error))
    raise ConnectorDeliveryError(error["message"]) from last_error