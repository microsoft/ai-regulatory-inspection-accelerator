"""
Activity: Rules & Policy Engine

All infrastructure (rules_list, track_event, PII data) is injected by the
caller, matching the Core Platform dependency injection pattern established by
pipeline.py and quality_assessment.py. run() returns the full result dict; the
caller handles delivery/storage.
"""

import logging

from src.platform.policy.rule_executor import run_rules
from src.platform.risk import assess_risk

logger = logging.getLogger(__name__)

_VERDICT_PRIORITY = {"FAIL": 3, "HOLD": 2, "PASS": 1}


async def run(
    payload: dict,
    extracted_fields: dict,
    rules_list: list,
    *,
    reasoning_findings: list[dict] | None = None,
    reasoning_document_checks: list[dict] | None = None,
    reasoning: dict | None = None,
    allowed_fields_by_doc: dict | None = None,
    risk_config: dict | None = None,
    evaluated_at: str | None = None,
    track_event=None,
) -> dict:
    """Run the rules & policy engine and return a verdict dict.

    Args:
        payload:               Submission dict (requestId, items, documents).
        extracted_fields:      DI extraction result keyed by documentTypeId.
        rules_list:            Rule documents loaded from Cosmos DB or rules.json.
        reasoning_findings:    Generic findings produced by the Reasoning Agent.
        reasoning_document_checks: Per-document checks produced by the Reasoning Agent.
        reasoning:             Cross-document reasoning result from the Reasoning Agent
                               (see src/platform/cross_document/reasoning_agent.py).
        allowed_fields_by_doc: {doc_type: [field_name]} from TemplateLoader.
                               Forwarded to validate_min_fields for field intersection.
        track_event:           Optional telemetry callback
                               (name, request_id=..., properties=..., measurements=...).

    Returns::

        {
            "recommendation": "PASS" | "FAIL" | "HOLD",
            "confidence": float,
            "aiRiskLevel": "Low" | "Medium" | "High",
            "summary": str,
            "findings": [...],
            "verdictId": str,
        }
    """
    request_id: str = payload["requestId"]
    findings: list[dict] = list(reasoning_findings or [])
    document_checks = list(reasoning_document_checks or [])

    logger.info(
        "Starting rules engine | requestId=%s | itemCount=%d | ruleDocs=%d",
        request_id, len(payload.get("items", [])), len(rules_list),
    )

    submission = [
        {
            "documentTypeId": doc_id,
            "document": doc_data.get("documentType", ""),
            "fields": doc_data.get("fields", {}),
            "lineItems": doc_data.get("lineItems", []),
            "lowConfidenceFields": doc_data.get("lowConfidenceFields", []),
            "ocrConfidence": doc_data.get("ocrConfidence", 0.0),
            "detectedLanguage": doc_data.get("detectedLanguage"),
        }
        for doc_id, doc_data in extracted_fields.items()
    ]

    try:
        executor_findings = await run_rules(
            rules_list, payload, submission,
            allowed_fields_by_doc=allowed_fields_by_doc,
            reasoning=reasoning,
        )
    except Exception as exc:  # noqa: BLE001 - convert executor failure to a HOLD verdict
        logger.error("run_rules failed unexpectedly | %s", exc)
        executor_findings = []
        findings.append({
            "ruleCode": "RULES_ENGINE_ERROR",
            "result": "FAIL",
            "severity": "high",
            "message": f"Rules engine encountered an unexpected error: {exc}",
        })

    logger.info("Rule executor returned %d finding(s)", len(executor_findings))

    for f in executor_findings:
        findings.append(f)
    confidence = _compute_confidence(findings)
    risk_evaluation = assess_risk(
        request_id,
        findings,
        extracted_fields,
        config=risk_config,
        evaluated_at=evaluated_at,
    )
    verdict = risk_evaluation["platformRecommendation"]
    ai_risk_level = risk_evaluation["aiRiskLevel"]
    summary = _build_summary(verdict, findings, risk_evaluation)
    verdict_id = f"{request_id}-verdict"

    fail_count = sum(1 for f in findings if f.get("result") == "FAIL")
    warn_count = sum(1 for f in findings if f.get("result") == "WARN")
    pass_count = sum(1 for f in findings if f.get("result") == "PASS")
    logger.info(
        "Rules engine complete | verdict=%s | aiRiskLevel=%s | confidence=%.3f "
        "| findings=%d (fail=%d warn=%d pass=%d)",
        verdict, ai_risk_level, confidence,
        len(findings), fail_count, warn_count, pass_count,
    )

    if track_event is not None:
        track_event(
            "RulesEngineCompleted",
            request_id=request_id,
            properties={
                "verdict": verdict,
                "verdictId": verdict_id,
                "findingsCount": str(len(findings)),
                "failCount": str(fail_count),
                "warnCount": str(warn_count),
            },
            measurements={
                "confidence": confidence,
                "riskScore": risk_evaluation["compositeRiskScore"],
            },
        )

    return {
        "recommendation": verdict,
        "publicRecommendation": risk_evaluation["recommendation"],
        "recommendationLabel": risk_evaluation["recommendationLabel"],
        "recommendationStatus": "ELIGIBLE",
        "confidence": confidence,
        "aiRiskLevel": ai_risk_level,
        "compositeRiskScore": risk_evaluation["compositeRiskScore"],
        "riskScore": risk_evaluation["compositeRiskScore"],
        "riskEvaluation": risk_evaluation,
        "riskAssessment": risk_evaluation,
        "summary": summary,
        "findings": findings,
        "documentChecks": document_checks,
        "verdictId": verdict_id,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _escalate(current: str, candidate: str) -> str:
    return (
        candidate
        if _VERDICT_PRIORITY.get(candidate, 0) > _VERDICT_PRIORITY.get(current, 0)
        else current
    )


def _compute_confidence(findings: list[dict]) -> float:
    if not findings:
        return 0.5
    deterministic = sum(
        1 for f in findings if f.get("result") in ("PASS", "FAIL", "WARN")
    )
    return round(deterministic / len(findings), 4)


def _build_summary(verdict: str, findings: list[dict], risk_evaluation: dict) -> str:
    fail_count = sum(1 for f in findings if f.get("result") == "FAIL")
    warn_count = sum(1 for f in findings if f.get("result") == "WARN")
    if verdict == "PASS":
        return "All checks passed. The case may proceed."
    if verdict == "FAIL":
        return (
            f"Inspection failed with {fail_count} blocking issue(s)"
            + (f" and {warn_count} document warning(s)" if warn_count > 0 else "")
            + ". The case has been rejected. See findings for details."
        )
    return (
        f"Case held for manual reviewer attention "
        f"({warn_count} warning(s) require human judgement)."
    )
