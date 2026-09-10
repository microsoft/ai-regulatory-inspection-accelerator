"""Generic REST connector."""

from __future__ import annotations

from typing import Any

from connectors.sdk.base_connector import BaseConnector, ConnectorTransformError


class RestConnector(BaseConnector):
    """Map a generic REST submission to the ARIA submission contract."""

    def transform_submission(self, external_payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(external_payload, dict):
            raise ConnectorTransformError("The submission body must be a JSON object.")
        payload = dict(external_payload)
        if not payload.get("requestId") and payload.get("caseId"):
            payload["requestId"] = str(payload["caseId"])
        return payload

    def deliver_decision(self, aria_decision: dict[str, Any]) -> dict[str, Any]:
        return {"accepted": True, "requestId": aria_decision.get("requestId")}

    def report_status(
        self,
        case_id: str,
        status: str,
        error: dict[str, Any] | None = None,
    ) -> bool:
        return True