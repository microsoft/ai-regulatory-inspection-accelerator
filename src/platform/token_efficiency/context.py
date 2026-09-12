"""Bounded context assembly for provider-neutral LLM calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.platform.document_intelligence.content_normalization import count_tokens


class ContextAssemblyError(ValueError):
    """Raised when assembled context exceeds the configured token budget."""


@dataclass(frozen=True)
class AssembledContext:
    messages: list[dict[str, Any]]
    token_count: int
    budget: int


class ContextAssemblyEngine:
    """Build minimum-context messages and enforce a hard token budget."""

    def __init__(self, *, token_budget: int = 3500) -> None:
        if token_budget <= 0:
            raise ValueError("token_budget must be positive")
        self.token_budget = token_budget

    def assemble(
        self,
        *,
        system_prompt: str,
        evidence: str,
        knowledge_pack: str = "",
        selected_chunks: list[str] | None = None,
    ) -> AssembledContext:
        context = "\n\n".join(part for part in [knowledge_pack, evidence, *(selected_chunks or [])] if part)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
        ]
        token_count = count_tokens(system_prompt) + count_tokens(context)
        if token_count > self.token_budget:
            raise ContextAssemblyError(
                f"Context uses {token_count} tokens, exceeding budget {self.token_budget}."
            )
        return AssembledContext(messages=messages, token_count=token_count, budget=self.token_budget)
