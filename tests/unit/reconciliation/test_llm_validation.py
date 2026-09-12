"""Tests for template-driven LLM reconciliation."""

import asyncio
import json

from src.platform.reconciliation.llm_validation import (
    resolve_field_names,
    run_comparisons,
)
from src.platform.shared.ai_client import AIClient


def _response(payload: dict) -> dict:
    return {
        "model": "test-model",
        "choices": [{"message": {"content": json.dumps(payload)}}],
        "usage": {},
    }


def test_field_resolution_uses_config_then_batches_only_gaps():
    calls = []

    def complete_fn(**kwargs):
        calls.append(kwargs)
        return _response({"invoiceNumber__IN__Invoice": "invoice_no"})

    result = asyncio.run(resolve_field_names(
        AIClient(complete_fn),
        model="test-model",
        case_id="CASE-1",
        tenant_id="TENANT-1",
        prompt="Resolve fields",
        rule_fields=["importerName", "invoiceNumber"],
        doc_field_index={
            "Invoice": {"company_name": "Buyer", "invoice_no": "INV-1"}
        },
        field_aliases={"importerName": ["company_name"]},
    ))

    assert result["importerName"]["Invoice"] == "company_name"
    assert result["invoiceNumber"]["Invoice"] == "invoice_no"
    request = json.loads(calls[0]["messages"][1]["content"])
    assert list(request["requests"]) == ["invoiceNumber__IN__Invoice"]
    assert calls[0]["temperature"] == 0.0
    assert calls[0]["seed"] == 42


def test_field_resolution_rejects_invented_fields():
    result = asyncio.run(resolve_field_names(
        AIClient(lambda **kwargs: _response({"invoiceNumber__IN__Invoice": "invented"})),
        model="test-model",
        case_id="CASE-2",
        tenant_id="",
        prompt="Resolve fields",
        rule_fields=["invoiceNumber"],
        doc_field_index={"Invoice": {"invoice_no": "INV-1"}},
        field_aliases={},
    ))

    assert result["invoiceNumber"]["Invoice"] is None


def test_comparison_sanitizes_results_and_confidence():
    result = asyncio.run(run_comparisons(
        AIClient(lambda **kwargs: _response({
            "findings": [
                {"ruleId": "R1", "result": "MAYBE", "confidence": 3},
                {"result": "FAIL", "confidence": 1},
            ]
        })),
        model="test-model",
        case_id="CASE-3",
        tenant_id="",
        prompt="Compare",
        tasks=[{"ruleId": "R1"}],
    ))

    assert result == [{"ruleId": "R1", "result": "NOT_APPLICABLE", "confidence": 1.0}]