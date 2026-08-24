"""
Activity: Rules & Policy Engine

Ported from PAFN's activities/rules_policy.py.
Changes from PAFN:
  - Removed Cosmos DB, telemetry, and PII redaction infrastructure.
  - All infrastructure (rules_list, track_event, PII data) is now injected
    by the caller, matching the Core Platform dependency injection pattern
    established by pipeline.py and quality_assessment.py.
  - run() returns the full result dict; caller handles delivery/storage.

Verdict escalation, confidence computation, AI risk level, and summary
text are identical to PAFN production.
"""

import logging

from src.platform.policy.rule_executor import run_rules

logger = logging.getLogger(__name__)

_VERDICT_PRIORITY = {"FAIL": 3, "HOLD": 2, "PASS": 1}


async def run(
    payload: dict,
    extracted_fields: dict,
    rules_list: list,
    *,
    allowed_fields_by_doc: dict | None = None,
    llm_comparison_fn=None,
    item_type_check_fn=None,
    managed_identity_client_id: str = "",
    track_event=None,
) -> dict:
    """Run the rules & policy engine and return a verdict dict.

    Args:
        payload:               Submission dict (requestId, items, documents).
        extracted_fields:      DI extraction result keyed by documentTypeId.
        rules_list:            Rule documents loaded from Cosmos DB or rules.json.
        allowed_fields_by_doc: {doc_type: [field_name]} from TemplateLoader.
                               Forwarded to validate_min_fields for field intersection.
        llm_comparison_fn:     Injectable async callable for cross-doc LLM checks.
        item_type_check_fn:    Injectable async callable for LLM item type checks.
        managed_identity_client_id: Passed through to LLM injectable callables.
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
    findings: list[dict] = []
    verdict = "PASS"

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
            managed_identity_client_id=managed_identity_client_id,
            llm_comparison_fn=llm_comparison_fn,
            item_type_check_fn=item_type_check_fn,
            allowed_fields_by_doc=allowed_fields_by_doc,
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
        verdict = _escalate(verdict, "HOLD")

    logger.info("Rule executor returned %d finding(s)", len(executor_findings))

    for f in executor_findings:
        findings.append(f)
        if f.get("ruleCode") == "REJECTED_HS_CODE":
            verdict = _escalate(verdict, "FAIL")
        elif f.get("result") in ("FAIL", "WARN"):
            verdict = _escalate(verdict, "HOLD")

    confidence = _compute_confidence(findings)
    ai_risk_level = _compute_ai_risk_level(findings, confidence)
    summary = _build_summary(verdict, findings)
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
            measurements={"confidence": confidence},
        )

    return {
        "recommendation": verdict,
        "confidence": confidence,
        "aiRiskLevel": ai_risk_level,
        "summary": summary,
        "findings": findings,
        "verdictId": verdict_id,
    }


# ---------------------------------------------------------------------------
# Helpers (identical to PAFN)
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


def _compute_ai_risk_level(findings: list[dict], confidence: float) -> str:
    has_fail = any(f.get("result") == "FAIL" for f in findings)
    has_warn = any(f.get("result") == "WARN" for f in findings)
    if has_fail:
        return "High"
    if has_warn:
        return "Medium"
    if confidence <= 0.4:
        return "High"
    if confidence <= 0.7:
        return "Medium"
    return "Low"


def _build_summary(verdict: str, findings: list[dict]) -> str:
    fail_count = sum(1 for f in findings if f.get("result") == "FAIL")
    warn_count = sum(1 for f in findings if f.get("result") == "WARN")
    if verdict == "PASS":
        return "All inspection checks passed. Shipment may proceed to clearance."
    if verdict == "FAIL":
        return (
            f"Inspection failed with {fail_count} blocking issue(s)"
            + (f" and {warn_count} document warning(s)" if warn_count > 0 else "")
            + ". Shipment has been rejected. See findings for details."
        )
    return (
        f"Shipment held for manual inspector review "
        f"({warn_count} warning(s) require human judgement)."
    )
