"""Compact template Knowledge Pack generation."""

from __future__ import annotations

import json
from typing import Any

from src.platform.document_intelligence.content_normalization import count_tokens


class KnowledgePackGenerator:
    """Generate a compact, deterministic summary from template configuration."""

    def __init__(self, *, max_tokens: int = 350) -> None:
        self.max_tokens = max_tokens

    def generate(self, template: dict[str, Any]) -> str:
        pack = {
            "templateId": template.get("templateId", template.get("id", "")),
            "documentTypes": [
                item.get("doc_type")
                for item in template.get("document_types", template.get("documentTypes", []))
                if isinstance(item, dict) and item.get("doc_type")
            ],
            "rules": [
                {
                    "id": rule.get("ruleCode", rule.get("ruleId", rule.get("id", ""))),
                    "description": rule.get("description", ""),
                }
                for rule in template.get("rules", [])
                if isinstance(rule, dict)
            ],
            "decisionVocabulary": template.get("decision_vocabulary", template.get("decisionVocabulary", {})),
            "fieldAliases": template.get("field_aliases", template.get("fieldAliases", {})),
        }
        serialized = json.dumps(pack, ensure_ascii=False, separators=(",", ":"))
        token_count = count_tokens(serialized)
        if token_count > self.max_tokens:
            raise ValueError(f"Knowledge Pack uses {token_count} tokens, exceeding {self.max_tokens}.")
        return serialized
