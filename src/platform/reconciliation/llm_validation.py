"""Provider-neutral LLM gap filling and semantic comparison logic."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

from src.platform.shared.ai_client import AIClient

logger = logging.getLogger(__name__)

_VALID_RESULTS = {"PASS", "FAIL", "WARN", "NOT_APPLICABLE"}


def _configured_match(
    semantic_field: str,
    actual_fields: dict,
    field_aliases: dict[str, list[str]],
) -> str | None:
    candidates = actual_fields.keys()
    if semantic_field in actual_fields:
        return semantic_field
    aliases = field_aliases.get(semantic_field, [])
    return next((alias for alias in aliases if alias in candidates), None)


async def resolve_field_names(
    ai_client: AIClient,
    *,
    model: str,
    case_id: str,
    tenant_id: str,
    prompt: str,
    rule_fields: list[str],
    doc_field_index: dict[str, dict],
    field_aliases: dict[str, list[str]],
    max_retries: int = 3,
    retry_delay_seconds: float = 2.0,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> dict[str, dict[str, str | None]]:
    """Resolve semantic rule fields using config first and one batched LLM gap fill."""
    result: dict[str, dict[str, str | None]] = {}
    lookup_request: dict[str, list[str]] = {}

    for rule_field in rule_fields:
        for document_name, fields in doc_field_index.items():
            configured = _configured_match(rule_field, fields, field_aliases)
            result.setdefault(rule_field, {})[document_name] = configured
            if configured is None:
                lookup_request[f"{rule_field}__IN__{document_name}"] = list(fields.keys())

    if not lookup_request:
        return result

    user_payload = {
        "fieldVocabulary": field_aliases,
        "requests": lookup_request,
    }
    for attempt in range(max_retries):
        try:
            response = await ai_client.complete(
                messages=[
                    {"role": "system", "content": prompt.strip()},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    },
                ],
                activity="cross_document_field_resolution",
                case_id=case_id,
                tenant_id=tenant_id,
                model=model,
                max_completion_tokens=4096,
            )
            resolved = json.loads(response.content or "{}")
            for composite_key, matched_field in resolved.items():
                if "__IN__" not in composite_key:
                    continue
                rule_field, document_name = composite_key.split("__IN__", 1)
                actual_fields = doc_field_index.get(document_name, {})
                if matched_field not in actual_fields:
                    matched_field = None
                result.setdefault(rule_field, {})[document_name] = matched_field
            return result
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning(
                "Field resolution attempt %d/%d failed: %s",
                attempt + 1,
                max_retries,
                exc,
            )
            if attempt + 1 < max_retries:
                await sleep(retry_delay_seconds * (attempt + 1))

    return result


def sanitize_findings(findings: list) -> list[dict]:
    """Validate result values and confidence before policy evaluation."""
    sanitized: list[dict] = []
    for finding in findings:
        if not isinstance(finding, dict) or not finding.get("ruleId"):
            continue
        item = dict(finding)
        if item.get("result") not in _VALID_RESULTS:
            item["result"] = "NOT_APPLICABLE"
        try:
            item["confidence"] = max(0.0, min(1.0, float(item.get("confidence", 0.0))))
        except (TypeError, ValueError):
            item["confidence"] = 0.0
        sanitized.append(item)
    return sanitized


async def run_comparisons(
    ai_client: AIClient,
    *,
    model: str,
    case_id: str,
    tenant_id: str,
    prompt: str,
    tasks: list[dict],
) -> list[dict]:
    """Run all fuzzy and semantic comparison tasks in one deterministic call."""
    if not tasks:
        return []
    response = await ai_client.complete(
        messages=[
            {"role": "system", "content": prompt.strip()},
            {
                "role": "user",
                "content": json.dumps({"tasks": tasks}, ensure_ascii=False),
            },
        ],
        activity="cross_document_comparison",
        case_id=case_id,
        tenant_id=tenant_id,
        model=model,
        max_completion_tokens=2048,
    )
    payload = json.loads(response.content or '{"findings": []}')
    return sanitize_findings(payload.get("findings", []))


async def run_item_type_checks(
    ai_client: AIClient,
    *,
    model: str,
    case_id: str,
    tenant_id: str,
    prompt: str,
    items: list[dict],
    source_doc_type: str,
    line_items: list[dict],
    description_fields: list[str],
) -> list[dict]:
    """Compare declared item types with configured document description fields."""
    tasks: list[dict] = []
    for item in items:
        serial = int(item.get("serial", 1))
        line_index = serial - 1
        if line_index < 0 or line_index >= len(line_items):
            continue
        declared_type = str(item.get("itemType") or "").strip()
        line_item = line_items[line_index]
        description = next(
            (
                field.get("value")
                for field_name in description_fields
                if isinstance((field := line_item.get(field_name)), dict)
                and field.get("value") not in (None, "")
            ),
            None,
        )
        if declared_type and description:
            tasks.append({
                "ruleId": f"ITEM_TYPE_{serial:03d}",
                "itemCode": item.get("itemCode"),
                "serial": serial,
                "declaredItemType": declared_type,
                "documentName": source_doc_type,
                "productDescription": description,
            })

    if not tasks:
        return []
    response = await ai_client.complete(
        messages=[
            {"role": "system", "content": prompt.strip()},
            {
                "role": "user",
                "content": json.dumps({"tasks": tasks}, ensure_ascii=False),
            },
        ],
        activity="item_type_comparison",
        case_id=case_id,
        tenant_id=tenant_id,
        model=model,
        max_completion_tokens=1024,
    )
    payload = json.loads(response.content or '{"findings": []}')
    task_by_rule = {task["ruleId"]: task for task in tasks}
    findings: list[dict] = []
    for finding in sanitize_findings(payload.get("findings", [])):
        if finding["result"] not in ("FAIL", "WARN"):
            continue
        task = task_by_rule.get(finding["ruleId"], {})
        findings.append({
            "ruleCode": finding["ruleId"],
            "result": finding["result"],
            "message": finding.get("explanation", "Item type requires review."),
            "itemCode": finding.get("itemCode", task.get("itemCode")),
            "confidence": finding["confidence"],
            "evidence": {
                source_doc_type: task.get("productDescription", ""),
                "Payload_Declared": task.get("declaredItemType", ""),
            },
        })
    return findings