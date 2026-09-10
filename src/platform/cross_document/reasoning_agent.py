"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Cross-Document — Reasoning Agent

The Reasoning Agent (pipeline Activity 3) owns every LLM-driven cross-document
judgement: semantic field resolution, fuzzy/semantic value comparison, and item
type checks. It runs before the Rules & Policy Stage and hands that Stage a
plain data result.

This separation is what keeps the Rules & Policy Stage deterministic — per
ADR-022, Agents reason with an LLM and Stages never call one.

The LLM callables are injected, so this module has no provider dependency.
"""

import logging

from src.platform.policy.evaluators import llm_mapper
from src.platform.policy.evaluators.cross_document import (
    apply_document_fallbacks,
    select_cross_document_rules,
)

logger = logging.getLogger(__name__)


def empty_result() -> dict:
    """A result shaped like run()'s, for pipelines with no Reasoning Agent."""
    return {
        "field_resolution": {},
        "comparison_findings": {},
        "item_type_findings": [],
        "errors": [],
    }


async def run(
    payload: dict,
    submission: list,
    rules_input,
    *,
    llm_comparison_fn=None,
    item_type_check_fn=None,
    managed_identity_client_id: str = "",
) -> dict:
    """Produce LLM-derived cross-document reasoning for the Rules & Policy Stage.

    Returns a dict with ``field_resolution``, ``comparison_findings`` keyed by
    ruleId, ``item_type_findings`` and ``errors``.
    """
    result = empty_result()

    rule_doc, cross_doc_rules = select_cross_document_rules(rules_input)
    if rule_doc is None:
        return result

    aliases = rule_doc.get("documentAliases", {})
    doc_field_index = llm_mapper.build_doc_field_index(submission, min_confidence=0.8)
    cross_doc_rules = apply_document_fallbacks(
        cross_doc_rules,
        doc_field_index,
        rule_doc.get("documentFallbacks", []),
        aliases,
    )

    if llm_comparison_fn is not None:
        try:
            llm_result = await llm_comparison_fn(
                payload=payload,
                cross_doc_rules=cross_doc_rules,
                submission=submission,
                managed_identity_client_id=managed_identity_client_id,
            )
            if not llm_result.get("success"):
                result["errors"].extend(llm_result.get("errors", []))
            else:
                result["field_resolution"] = llm_result.get("field_resolution", {})
                severity_by_rule = {
                    r["ruleId"]: r.get("severity", "Warning") for r in cross_doc_rules
                }
                for f in llm_result.get("comparison_findings", []):
                    result["comparison_findings"][f["ruleId"]] = {
                        "ruleId": f["ruleId"],
                        "result": f.get("result", "NOT_APPLICABLE"),
                        "message": f.get("explanation", ""),
                        "evidence": f.get("evidence", ""),
                        "affectedDocs": f.get("affectedDocs", []),
                        "confidence": f.get("confidence"),
                        "severity": severity_by_rule.get(f["ruleId"], "Warning"),
                    }
        except Exception as exc:
            if getattr(exc, "status_code", None) in (401, 403):
                raise RuntimeError(
                    f"OpenAI auth failure (HTTP {exc.status_code}) during cross-document "
                    f"reasoning. Original error: {exc}"
                ) from exc
            logger.error("LLM cross-document comparison failed: %s", exc)
            result["errors"].append(
                {"code": "LLM_ERROR", "severity": "error", "message": str(exc)}
            )

    if item_type_check_fn is not None:
        items = payload.get("items", [])
        source_doc_type = None
        source_line_items = []
        for doc_type in rule_doc.get("lineItemSources", []):
            for doc in submission:
                if doc.get("document") == doc_type and doc.get("lineItems"):
                    source_doc_type = doc_type
                    source_line_items = doc["lineItems"]
                    break
            if source_doc_type:
                break
        if source_doc_type and items:
            try:
                result["item_type_findings"] = await item_type_check_fn(
                    items=items,
                    source_doc_type=source_doc_type,
                    line_items=source_line_items,
                    managed_identity_client_id=managed_identity_client_id,
                )
            except Exception as exc:  # noqa: BLE001 - optional check must not abort reasoning
                logger.error("LLM item type checks failed: %s", exc)

    return result
