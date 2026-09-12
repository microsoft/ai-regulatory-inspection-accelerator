"""Tests for template-driven cross-document reconciliation."""

import asyncio

from src.platform.policy.evaluators.cross_document import validate_cross_docs


def test_exact_match_uses_template_document_aliases():
    result = asyncio.run(validate_cross_docs(
        {"requestId": "CASE-1", "items": []},
        {
            "id": "CROSS_DOC_RULES",
            "crossDocumentRules": [{
                "ruleId": "MATCH-NUMBER",
                "field": "reference_number",
                "documents": ["SourceOne", "SourceTwo"],
                "comparisonType": "exactMatch",
            }],
        },
        [
            {
                "document": "source_one",
                "fields": {"reference_number": {"value": "ABC-1", "confidence": 1.0}},
            },
            {
                "document": "source_two",
                "fields": {"reference_number": {"value": "ABC-1", "confidence": 1.0}},
            },
        ],
        document_aliases={"SourceOne": "source_one", "SourceTwo": "source_two"},
    ))

    assert result["findings"][0]["result"] == "PASS"
    assert result["findings"][0]["evidence"] == {
        "source_one": "ABC-1",
        "source_two": "ABC-1",
    }