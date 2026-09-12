"""Deterministic three-component case risk evaluation."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

DEFAULT_RISK_CONFIG = {
    "policy_version": "enhanced-risk-v1",
    "quality": {"threshold": 0.75, "impact": 0.60},
    "extraction": {"threshold": 0.85, "impact": 0.45},
    "rule_weights": {
        "MANDATORY_DOC_MISSING": 1.00,
        "REJECTED_HS_CODE": 1.00,
        "DEACTIVATED_HALAL_BODY": 1.00,
        "CRITICAL_MISMATCH": 0.90,
        "NON_FOOD_ITEM": 0.90,
        "MIN_FIELDS_MISSING": 0.85,
        "CERTIFICATE_EXPIRED": 0.80,
        "DO_WEIGHT_MISMATCH": 0.75,
        "MINOR_VARIANCE": 0.40,
    },
    "rule_actions": {
        "REJECTED_HS_CODE": "REJECT",
    },
    "risk_bands": [
        {
            "minimum": 0.75,
            "risk_level": "High",
            "recommendation": "ACCEPT_WITH_WARNING",
            "recommendation_label": "Accept with warnings",
            "platform_recommendation": "HOLD",
        },
        {
            "minimum": 0.40,
            "risk_level": "Medium",
            "recommendation": "ACCEPT_WITH_WARNING",
            "recommendation_label": "Accept with warnings",
            "platform_recommendation": "HOLD",
        },
        {
            "minimum": 0.00,
            "risk_level": "Low",
            "recommendation": "ACCEPT",
            "recommendation_label": "Accept",
            "platform_recommendation": "PASS",
        },
    ],
    "explicit_reject": {
        "recommendation": "REJECT",
        "recommendation_label": "Reject",
        "platform_recommendation": "FAIL",
    },
}


def _merge_config(base: dict, override: dict | None) -> dict:
    merged = deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_config(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _quality_score(document: dict) -> float | None:
    quality = document.get("qualityCheck") or {}
    raw_score = quality.get("quality_score", quality.get("qualityScore"))
    return None if raw_score is None else _clamp(float(raw_score))


def _low_confidence_line_item_fields(document: dict, threshold: float) -> list[str]:
    affected: list[str] = []
    for item_index, line_item in enumerate(document.get("lineItems") or []):
        if not isinstance(line_item, dict):
            continue
        for field_name, field in line_item.items():
            if not isinstance(field, dict) or field.get("value") in (None, ""):
                continue
            confidence = field.get("confidence")
            if confidence is not None and float(confidence) < threshold:
                affected.append(f"lineItems[{item_index}].{field_name}")
    return affected


def _document_assessments(extracted_fields: dict, config: dict) -> list[dict]:
    assessments: list[dict] = []
    quality_threshold = float(config["quality"]["threshold"])
    quality_value = float(config["quality"]["impact"])
    extraction_threshold = float(config["extraction"]["threshold"])
    extraction_value = float(config["extraction"]["impact"])

    for document_type_id, document in extracted_fields.items():
        quality_score = _quality_score(document)
        quality_failed = quality_score is not None and quality_score < quality_threshold
        canonical_fields = list(document.get("lowConfidenceFields") or [])
        line_item_fields = _low_confidence_line_item_fields(document, extraction_threshold)
        affected_fields = canonical_fields + line_item_fields
        quality_impact = quality_value if quality_failed else 0.0
        extraction_risk = extraction_value if not quality_failed and affected_fields else 0.0
        assessments.append({
            "documentTypeId": str(document_type_id),
            "documentType": document.get("documentType", ""),
            "qualityScore": quality_score,
            "lowConfidenceFields": affected_fields,
            "qualityImpact": quality_impact,
            "extractionRisk": extraction_risk,
            "documentRisk": quality_impact or extraction_risk,
            "processingOutcome": (
                "NOT_PROCESSED_LOW_QUALITY" if quality_failed else "PROCESSED"
            ),
        })
    return assessments


def _finding_weight(finding: dict, config: dict) -> float:
    explicit_weight = finding.get("riskWeight", finding.get("weight"))
    if explicit_weight is not None:
        return _clamp(float(explicit_weight))
    return _clamp(float(config["rule_weights"].get(str(finding.get("ruleCode", "")), 0.0)))


def _finding_action(finding: dict, config: dict) -> str | None:
    rule_code = str(finding.get("ruleCode", ""))
    raw_action = finding.get("riskAction")
    if raw_action is None:
        raw_action = config.get("rule_actions", {}).get(rule_code)
    if raw_action is None:
        return None
    action = str(raw_action).upper()
    if action not in ("REVIEW", "REJECT"):
        raise ValueError(
            f"Unsupported risk action {raw_action!r} for rule {rule_code!r}."
        )
    return action


def _rule_assessments(findings: list[dict], config: dict) -> tuple[list[dict], list[dict]]:
    violated: list[dict] = []
    item_weights: dict[str, list[dict]] = {}
    for finding in findings:
        if str(finding.get("result", "")).upper() not in ("FAIL", "WARN"):
            continue
        weight = _finding_weight(finding, config)
        contribution = {
            "ruleCode": str(finding.get("ruleCode", "")),
            "result": str(finding.get("result", "")).upper(),
            "weight": weight,
            "action": _finding_action(finding, config),
            "documentType": finding.get("documentType"),
            "itemCode": finding.get("itemCode"),
        }
        violated.append(contribution)
        if finding.get("itemCode") not in (None, ""):
            item_weights.setdefault(str(finding["itemCode"]), []).append(contribution)

    item_assessments = [
        {
            "itemCode": item_code,
            "itemRisk": max(item["weight"] for item in contributions),
            "ruleCodes": [item["ruleCode"] for item in contributions],
        }
        for item_code, contributions in item_weights.items()
    ]
    return violated, item_assessments


def _risk_band(score: float, bands: list[dict]) -> dict:
    ordered = sorted(bands, key=lambda band: float(band["minimum"]), reverse=True)
    for band in ordered:
        if score >= float(band["minimum"]):
            return band
    raise ValueError("risk_bands must include a band with minimum 0.0")


def assess_risk(
    case_id: str,
    findings: list[dict],
    extracted_fields: dict,
    *,
    config: dict | None = None,
    evaluated_at: str | None = None,
) -> dict:
    """Build one replayable three-component risk evaluation for a request."""
    active = _merge_config(DEFAULT_RISK_CONFIG, config)
    document_assessments = _document_assessments(extracted_fields, active)
    rule_assessments, item_assessments = _rule_assessments(findings, active)
    quality_impact = max(
        (item["qualityImpact"] for item in document_assessments), default=0.0
    )
    extraction_risk = max(
        (item["extractionRisk"] for item in document_assessments), default=0.0
    )
    rule_severity = max((item["weight"] for item in rule_assessments), default=0.0)
    score = round(_clamp(quality_impact + extraction_risk + rule_severity), 2)
    band = _risk_band(score, active["risk_bands"])
    explicit_reject_rule_codes = [
        item["ruleCode"] for item in rule_assessments
        if item["action"] == "REJECT"
    ]
    if (
        not explicit_reject_rule_codes
        and str(band.get("platform_recommendation", "")).upper() == "FAIL"
    ):
        raise ValueError(
            "risk_bands cannot authorize FAIL; configure an explicit REJECT rule action."
        )
    decision = (
        active["explicit_reject"] if explicit_reject_rule_codes else band
    )
    failed_count = sum(1 for finding in findings if finding.get("result") == "FAIL")
    warning_count = sum(1 for finding in findings if finding.get("result") == "WARN")
    evaluated_count = sum(
        1 for finding in findings
        if finding.get("result") in ("PASS", "FAIL", "WARN", "NOT_APPLICABLE")
    )

    return {
        "id": f"{case_id}-risk",
        "requestId": case_id,
        "compositeRiskScore": score,
        "aiRiskLevel": str(band["risk_level"]),
        "recommendation": str(decision["recommendation"]),
        "recommendationLabel": str(decision["recommendation_label"]),
        "platformRecommendation": str(decision["platform_recommendation"]),
        "decisionBasis": (
            "EXPLICIT_RULE_ACTION" if explicit_reject_rule_codes else "RISK_BAND"
        ),
        "explicitRejectRuleCodes": explicit_reject_rule_codes,
        "scoreBreakdown": {
            "caseQualityImpact": quality_impact,
            "caseExtractionRisk": extraction_risk,
            "caseRuleSeverity": rule_severity,
            "primaryRuleCode": next(
                (
                    item["ruleCode"] for item in rule_assessments
                    if item["weight"] == rule_severity and rule_severity > 0.0
                ),
                None,
            ),
        },
        "documentAssessments": document_assessments,
        "itemAssessments": item_assessments,
        "ruleAssessments": rule_assessments,
        "evaluatedRulesCount": evaluated_count,
        "failedRulesCount": failed_count,
        "warningRulesCount": warning_count,
        "policyVersion": str(active["policy_version"]),
        "configurationSnapshot": active,
        "evaluatedAt": evaluated_at or datetime.now(timezone.utc).isoformat(),
    }