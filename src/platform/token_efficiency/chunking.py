"""Configurable semantic-style chunking for large normalized documents."""

from __future__ import annotations

from dataclasses import dataclass

from src.platform.document_intelligence.content_normalization import count_tokens


@dataclass(frozen=True)
class SemanticChunk:
    text: str
    index: int
    token_count: int
    page_start: int | None = None
    page_end: int | None = None
    field_hints: tuple[str, ...] = ()


class SemanticChunker:
    """Split Markdown by headings and token windows while preserving context."""

    def __init__(self, *, max_tokens: int = 1200, overlap_tokens: int = 120) -> None:
        if max_tokens <= 0 or overlap_tokens < 0 or overlap_tokens >= max_tokens:
            raise ValueError("max_tokens must be positive and overlap_tokens must be smaller")
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, content: str, field_hints: list[str] | None = None) -> list[SemanticChunk]:
        if not content.strip():
            return []
        paragraphs = [part.strip() for part in content.split("\n\n") if part.strip()]
        chunks: list[SemanticChunk] = []
        current: list[str] = []
        current_tokens = 0
        index = 0
        for paragraph in paragraphs:
            paragraph_tokens = count_tokens(paragraph)
            if current and current_tokens + paragraph_tokens > self.max_tokens:
                text = "\n\n".join(current)
                chunks.append(SemanticChunk(text, index, count_tokens(text), field_hints=tuple(field_hints or [])))
                index += 1
                overlap: list[str] = []
                overlap_count = 0
                for prior in reversed(current):
                    prior_tokens = count_tokens(prior)
                    if overlap_count + prior_tokens > self.overlap_tokens:
                        break
                    overlap.insert(0, prior)
                    overlap_count += prior_tokens
                current = overlap
                current_tokens = overlap_count
            current.append(paragraph)
            current_tokens += paragraph_tokens
        if current:
            text = "\n\n".join(current)
            chunks.append(SemanticChunk(text, index, count_tokens(text), field_hints=tuple(field_hints or [])))
        return chunks
