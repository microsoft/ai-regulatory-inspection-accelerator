"""Unit tests for the cross-document Reasoning Agent and the Stage/Agent boundary.

ADR-022: Agents perform LLM-driven reasoning; Stages are deterministic and never
call an LLM. These tests pin that separation.
"""

import asyncio
import inspect

from src.platform.cross_document import reasoning_agent
from src.platform.policy.evaluators.cross_document import validate_cross_docs

CROSS_DOC_RULES = {
    "id": "CROSS_DOC_RULES",
    "documentAliases": {"PackingList": "Packing_List"},
    "documentFallbacks": [{"whenAbsent": ["Packing_List"], "use": "Invoice"}],
    "lineItemSources": ["Packing_List", "Invoice"],
    "countryFields": ["country_of_origin"],
    "dateFields": ["invoice_date"],
    "crossDocumentRules": [
        {
            "ruleId": "CROSS_REF",
            "field": "reference_number",
            "documents": ["Invoice", "Certificate"],
            "comparisonType": "exactMatch",
            "severity": "Warning",
        },
        {
            "ruleId": "CROSS_DESCRIPTION",
            "field": "description",
            "documents": ["Invoice", "Certificate"],
            "comparisonType": "semanticMatch",
            "severity": "Warning",
        },
    ],
}


def _doc(name: str, fields: dict) -> dict:
    return {
        "document": name,
        "documentTypeId": name,
        "fields": {k: {"value": v, "confidence": 0.99} for k, v in fields.items()},
        "lineItems": [],
    }


SUBMISSION = [
    _doc("Invoice", {"reference_number": "REF-1", "description": "widgets"}),
    _doc("Certificate", {"reference_number": "REF-2", "description": "widgetry"}),
]
PAYLOAD = {"requestId": "R1", "items": []}


class TestStageAgentBoundary:
    def test_stage_is_not_a_coroutine(self):
        assert not inspect.iscoroutinefunction(validate_cross_docs)

    def test_stage_takes_no_llm_callables(self):
        params = set(inspect.signature(validate_cross_docs).parameters)
        assert "llm_comparison_fn" not in params
        assert "item_type_check_fn" not in params

    def test_agent_owns_the_llm_callables(self):
        params = set(inspect.signature(reasoning_agent.run).parameters)
        assert {"llm_comparison_fn", "item_type_check_fn"} <= params


class TestStageDeterminism:
    def test_exact_match_mismatch_fails_without_any_reasoning(self):
        result = validate_cross_docs(PAYLOAD, CROSS_DOC_RULES, SUBMISSION)
        by_rule = {f["ruleId"]: f for f in result["findings"]}
        assert by_rule["CROSS_REF"]["result"] == "FAIL"

    def test_reasoning_finding_takes_priority_over_in_process(self):
        reasoning = {
            "field_resolution": {},
            "comparison_findings": {
                "CROSS_REF": {"ruleId": "CROSS_REF", "result": "PASS", "message": "same"}
            },
            "item_type_findings": [],
            "errors": [],
        }
        result = validate_cross_docs(PAYLOAD, CROSS_DOC_RULES, SUBMISSION, reasoning=reasoning)
        by_rule = {f["ruleId"]: f for f in result["findings"]}
        assert by_rule["CROSS_REF"]["result"] == "PASS"

    def test_semantic_rule_is_not_applicable_without_reasoning(self):
        result = validate_cross_docs(PAYLOAD, CROSS_DOC_RULES, SUBMISSION)
        by_rule = {f["ruleId"]: f for f in result["findings"]}
        assert by_rule["CROSS_DESCRIPTION"]["result"] == "NOT_APPLICABLE"

    def test_reasoning_errors_are_surfaced(self):
        reasoning = {"errors": [{"code": "LLM_ERROR", "message": "boom"}]}
        result = validate_cross_docs(PAYLOAD, CROSS_DOC_RULES, SUBMISSION, reasoning=reasoning)
        assert result["errors"][0]["code"] == "LLM_ERROR"


class TestReasoningAgent:
    def test_returns_empty_result_without_callables(self):
        result = asyncio.run(
            reasoning_agent.run(PAYLOAD, SUBMISSION, CROSS_DOC_RULES)
        )
        assert result == reasoning_agent.empty_result()

    def test_maps_llm_findings_by_rule_id(self):
        async def fake_comparison(**kwargs):
            return {
                "success": True,
                "field_resolution": {"description": {"Invoice": "description"}},
                "comparison_findings": [
                    {"ruleId": "CROSS_DESCRIPTION", "result": "PASS", "explanation": "synonyms"}
                ],
            }

        result = asyncio.run(
            reasoning_agent.run(
                PAYLOAD, SUBMISSION, CROSS_DOC_RULES, llm_comparison_fn=fake_comparison
            )
        )
        assert result["comparison_findings"]["CROSS_DESCRIPTION"]["result"] == "PASS"
        assert result["comparison_findings"]["CROSS_DESCRIPTION"]["severity"] == "Warning"
        assert result["field_resolution"]["description"]["Invoice"] == "description"

    def test_llm_failure_is_captured_not_raised(self):
        async def failing_comparison(**kwargs):
            raise RuntimeError("model unavailable")

        result = asyncio.run(
            reasoning_agent.run(
                PAYLOAD, SUBMISSION, CROSS_DOC_RULES, llm_comparison_fn=failing_comparison
            )
        )
        assert result["errors"][0]["code"] == "LLM_ERROR"

    def test_auth_failure_is_raised(self):
        class AuthError(RuntimeError):
            status_code = 401

        async def auth_failing(**kwargs):
            raise AuthError("unauthorized")

        try:
            asyncio.run(
                reasoning_agent.run(
                    PAYLOAD, SUBMISSION, CROSS_DOC_RULES, llm_comparison_fn=auth_failing
                )
            )
        except RuntimeError as exc:
            assert "auth failure" in str(exc)
        else:
            raise AssertionError("expected an auth failure to propagate")

    def test_missing_rule_document_returns_empty(self):
        result = asyncio.run(reasoning_agent.run(PAYLOAD, SUBMISSION, []))
        assert result == reasoning_agent.empty_result()
