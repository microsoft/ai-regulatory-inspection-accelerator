"""
ARIA — AI Regulatory Inspection Accelerator
Connector SDK — Base Connector Contract

All connectors (platform built-in and customer-specific) must extend BaseConnector
and implement the three-interface contract.

USAGE
-----
from connectors.sdk.base_connector import BaseConnector

class MySystemConnector(BaseConnector):
    def transform_submission(self, external_payload: dict) -> dict:
        ...
    def deliver_decision(self, aria_decision: dict) -> dict:
        ...
    def report_status(self, case_id: str, status: str, error: dict | None) -> bool:
        ...
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseConnector(ABC):
    """
    Abstract base class for all ARIA connectors.

    Implements the three-interface connector contract:
      1. transform_submission  — Inbound: external payload → ARIA standard submission
      2. deliver_decision      — Outbound: ARIA decision → external system
      3. report_status         — Status: pipeline status → external system

    ISOLATION GUARANTEE
    -------------------
    Connectors interact with ARIA exclusively through the platform's published API.
    Connectors must NOT import from src.platform or access platform data stores directly.
    Connectors may import from connectors.sdk only.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the connector with its configuration.

        Args:
            config: Connector-specific configuration loaded from environment
                    variables or Key Vault references. Never hardcode secrets.
        """
        self.config = config
        self._validate_config(config)

    def _validate_config(self, config: dict[str, Any]) -> None:
        """
        Override to validate connector-specific required configuration keys.
        Raise ValueError if required keys are missing.
        """

    # ─── INTERFACE 1: INBOUND ─────────────────────────────────────────────────

    @abstractmethod
    def transform_submission(self, external_payload: dict[str, Any]) -> dict[str, Any]:
        """
        Transform an external system's submission payload into an ARIA-standard
        submission JSON document, validated against the active template's
        submission_schema.json.

        Args:
            external_payload: Raw payload from the external system.

        Returns:
            ARIA-standard submission dict conforming to the template's
            submission_schema.json.

        Raises:
            ConnectorTransformError: If the payload cannot be transformed.
        """

    # ─── INTERFACE 2: OUTBOUND ────────────────────────────────────────────────

    @abstractmethod
    def deliver_decision(self, aria_decision: dict[str, Any]) -> dict[str, Any]:
        """
        Deliver an ARIA-standard decision to the external system.

        The aria_decision dict contains the display evidence chain (PII-redacted).
        It never contains raw PII values.

        Args:
            aria_decision: ARIA-standard structured decision including:
                - caseId: str
                - verdict: str (domain vocabulary label)
                - confidenceScore: float (0.0-1.0)
                - riskGrade: str
                - topFindings: list[dict]
                - naturalLanguageSummary: str
                - displayEvidenceChain: dict

        Returns:
            External system acknowledgement dict.

        Raises:
            ConnectorDeliveryError: If delivery fails after connector-level retry.
        """

    # ─── INTERFACE 3: STATUS ──────────────────────────────────────────────────

    @abstractmethod
    def report_status(
        self,
        case_id: str,
        status: str,
        error: dict[str, Any] | None = None,
    ) -> bool:
        """
        Report pipeline status to the external system.

        Called at key pipeline lifecycle events:
          - RECEIVED          : Submission accepted, processing starting
          - PRE_VALIDATION_FAILED : Submission rejected at integrity check
          - PROCESSING        : Pipeline stages running
          - COMPLETED         : Decision delivered successfully
          - DELIVERY_FAILED   : Decision delivery failed after all retries

        Args:
            case_id: ARIA case identifier (instanceId).
            status: Pipeline status string.
            error: Structured error detail if status indicates failure.

        Returns:
            True if the external system acknowledged the status update.
        """

    # ─── OPTIONAL: HEALTH CHECK ───────────────────────────────────────────────

    def health_check(self) -> dict[str, Any]:
        """
        Optional: Test connectivity to the external system.
        Override to implement connector-specific health check.

        Returns:
            dict with 'status' ('healthy' | 'degraded' | 'unavailable')
            and optional 'detail' string.
        """
        return {"status": "healthy", "detail": "Health check not implemented"}


class ConnectorTransformError(Exception):
    """Raised when an inbound payload cannot be transformed to ARIA standard."""


class ConnectorDeliveryError(Exception):
    """Raised when a decision cannot be delivered to the external system."""
