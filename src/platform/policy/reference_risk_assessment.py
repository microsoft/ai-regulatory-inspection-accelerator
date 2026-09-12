"""Reference 0-100 risk scoring policy.

This module preserves the configurable reference model separately from ARIA's
normalized 0.00-1.00 platform scorer. It is deterministic and policy-driven.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from typing import Any

DEFAULT_REFERENCE_POLICY = {
    "id": "RISK_SCORING_THRESHOLDS",
    "version": "1.0",
    "qualityScoreThreshold": 0.75,
    "fieldConfidenceThreshold": 0.85,
    "documentConfidenceThreshold": None,
    "findingConfidenceThreshold": 0.50,
    "riskBands": [
        {"name": "Low", "minimum": 0, "maximum": 39},
        {"name": "Medium", "minimum": 40, "maximum": 74},
        {"name": "High", "minimum": 75, "maximum": 100},
    ],
}

DEFAULT_RULE_RISK_POLICY = {
    "id": "RULE_RISK_SCORES",
    "version": "1.0",
    "rules": [
        {"rulePattern": "CROSS_*", "riskScore": 40, "recommendation": "ACCEPT_WITH_WARNING"},
        {"ruleId": "MIN_FIELDS_RULES", "riskScore": 40, "recommendation": "ACCEPT_WITH_WARNING"},
        {"ruleId": "MANDATORY_DOC_MISSING", "riskScore": 75, "recommendation": "ACCEPT_WITH_WARNING"},
        {"rulePattern": "ITEM_*", "riskScore": 75, "recommendation": "ACCEPT_WITH_WARNING"},
        {"ruleId": "REJECTED_HS_CODE", "riskScore": 100, "recommendation": "REJECT"},
    ],
}


@dataclass(frozen=True)
class ReferenceRiskPolicy:
    thresholds: dict[str, Any]
    rule_scores: dict[str, Any]


def _rule_config(rule_code: str, policy: dict) -> dict | None:
    for rule in policy.get("rules", []):
        if rule.get("ruleId") == rule_code:
            return rule
        if rule.get("rulePattern") and fnmatchcase(rule_code, rule["rulePattern"]):
            return rule
    return None


def _document_score(document: dict, thresholds: dict) -> dict:
    quality = document.get("qualityScore", document.get("quality_score"))
    quality = float(quality) if quality is not None else None
    fields = document.get("fields") or {}
    populated = [
        field for field in fields.values()
        if isinstance(field, dict) and field.get("value") not in (None, "")
    ]
    passed = sum(
        1 for field in populated
        if float(field.get("confidence", 0.0)) >= float(thresholds["fieldConfidenceThreshold"])
    )
    confidence_score = round(100 * passed / len(populated), 2) if populated else 0.0
    manual_reason = None
    if quality is not None and quality < float(thresholds["qualityScoreThreshold"]):
        manual_reason = "LOW_DOCUMENT_QUALITY"
    elif not populated:
        manual_reason = "NO_POPULATED_FIELDS"
    elif thresholds.get("documentConfidenceThreshold") is not None and confidence_score < float(
        thresholds["documentConfidenceThreshold"]
    ):
        manual_reason = "LOW_DOCUMENT_CONFIDENCE"
    return {
        "documentId": str(document.get("documentId", document.get("documentTypeId", ""))),
        "qualityScore": quality,
        "populatedFieldCount": len(populated),
        "passedFieldCount": passed,
        "documentConfidenceScore": confidence_score,
        "documentRiskScore": 40 if manual_reason else 0,
        "manualReviewReason": manual_reason,
    }


def _band(score: int, thresholds: dict) -> str:
    for band in sorted(thresholds["riskBands"], key=lambda item: item["minimum"], reverse=True):
        if score >= band["minimum"]:
            return str(band["name"])
    raise ValueError("riskBands must include a band with minimum 0")


def assess_reference_risk(
    request_id: str,
    documents: list[dict],
    findings: list[dict],
    *,
    thresholds: dict | None = None,
    rule_scores: dict | None = None,
    evaluated_at: str | None = None,
) -> dict:
    """Calculate reference document, item, rule, and case scores."""
    threshold_policy = deepcopy(DEFAULT_REFERENCE_POLICY)
    threshold_policy.update(thresholds or {})
    rule_policy = deepcopy(DEFAULT_RULE_RISK_POLICY)
    rule_policy.update(rule_scores or {})
    document_scores = [_document_score(document, threshold_policy) for document in documents]

    items: dict[str, dict] = {}
    rule_scores_by_finding: list[dict] = []
    reject_rules: list[str] = []
    overall_rule_score = 0
    for finding in findings:
        if str(finding.get("result", "")).upper() not in {"FAIL", "WARN"}:
            continue
        rule_code = str(finding.get("ruleCode", finding.get("ruleId", "")))
        config = _rule_config(rule_code, rule_policy)
        score = int(finding.get("riskScore", config.get("riskScore", 0) if config else 0))
        recommendation = str(config.get("recommendation", "ACCEPT_WITH_WARNING")) if config else "ACCEPT_WITH_WARNING"
        result = {"ruleId": rule_code, "riskScore": score, "recommendation": recommendation}
        rule_scores_by_finding.append(result)
        if recommendation == "REJECT":
            reject_rules.append(rule_code)
        if finding.get("itemNumber") is not None:
            item_key = str(finding["itemNumber"])
            items.setdefault(item_key, {"itemNumber": finding["itemNumber"], "violatedRules": [], "itemRiskScore": 0})
            items[item_key]["violatedRules"].append(result)
            items[item_key]["itemRiskScore"] = max(items[item_key]["itemRiskScore"], score)
        else:
            overall_rule_score = max(overall_rule_score, score)

    max_document_score = max((item["documentRiskScore"] for item in document_scores), default=0)
    overall_item_score = max((item["itemRiskScore"] for item in items.values()), default=0)
    case_score = max(max_document_score, overall_item_score, overall_rule_score)
    recommendation = "REJECT" if reject_rules else ("ACCEPT_WITH_WARNING" if case_score >= 40 else "ACCEPT")
    manual_reasons = [item["manualReviewReason"] for item in document_scores if item["manualReviewReason"]]
    return {
        "id": f"{request_id}-risk",
        "requestId": request_id,
        "caseRiskScore": case_score,
        "riskBand": _band(case_score, threshold_policy),
        "recommendation": recommendation,
        "documents": document_scores,
        "items": list(items.values()),
        "overallItemRiskScore": overall_item_score,
        "overallRuleRiskScore": overall_rule_score,
        "ruleEvaluations": rule_scores_by_finding,
        "manualReview": {"required": bool(manual_reasons), "reasons": manual_reasons},
        "policyVersions": {"thresholds": threshold_policy["version"], "ruleScores": rule_policy["version"]},
        "createdAt": evaluated_at or datetime.now(timezone.utc).isoformat(),
    }
