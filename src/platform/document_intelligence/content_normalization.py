"""Domain-neutral normalization for Azure DI Markdown before LLM processing."""

import re
from dataclasses import asdict, dataclass
from functools import lru_cache

import tiktoken

_PAGE_BREAK = "<!-- PageBreak -->"
_SELECTION_MARKS_RE = re.compile(r":(?:un)?selected:", re.IGNORECASE)
_DUPLICATE_SEPARATOR_RE = re.compile(r"(?:\n\s*---\s*){2,}")
_EXCESS_BLANK_LINES_RE = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ContentNormalizationOptions:
    """Template-configurable Markdown cleanup options."""

    strip_selection_marks: bool = True
    collapse_blank_lines: bool = True
    collapse_page_separators: bool = True
    remove_repeated_headers: bool = True
    repeated_line_min_pages: int = 2
    repeated_line_max_length: int = 120

    @classmethod
    def from_dict(cls, values: dict | None) -> "ContentNormalizationOptions":
        supported = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in (values or {}).items() if key in supported})


@dataclass(frozen=True)
class NormalizationReport:
    """Measured content reduction produced by one normalization pass."""

    characters_before: int
    characters_after: int
    tokens_before: int
    tokens_after: int
    token_reduction_ratio: float
    repeated_lines_removed: int

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=1)
def _tokenizer():
    return tiktoken.get_encoding("o200k_base")


def count_tokens(content: str) -> int:
    """Count tokens with the tokenizer used by current Azure OpenAI models."""
    return len(_tokenizer().encode(content)) if content else 0


def _remove_repeated_page_lines(
    content: str,
    options: ContentNormalizationOptions,
) -> tuple[str, int]:
    pages = content.split(_PAGE_BREAK)
    if len(pages) < options.repeated_line_min_pages:
        return content, 0

    page_lines = []
    for page in pages:
        eligible = [
            line.strip()
            for line in page.splitlines()
            if 3 < len(line.strip()) <= options.repeated_line_max_length
            and not line.lstrip().startswith(("|", "<!--"))
        ]
        page_lines.append(set(eligible[:2] + eligible[-2:]))
    occurrences: dict[str, int] = {}
    for lines in page_lines:
        for line in lines:
            occurrences[line] = occurrences.get(line, 0) + 1

    repeated = {
        line
        for line, count in occurrences.items()
        if count >= options.repeated_line_min_pages
    }
    if not repeated:
        return content, 0

    removed = 0
    normalized_pages = []
    for page in pages:
        kept_lines = []
        for line in page.splitlines():
            if line.strip() in repeated:
                removed += 1
            else:
                kept_lines.append(line.rstrip())
        normalized_pages.append("\n".join(kept_lines))
    return f"\n{_PAGE_BREAK}\n".join(normalized_pages), removed


def normalize_markdown(
    content: str,
    options: ContentNormalizationOptions | None = None,
) -> tuple[str, NormalizationReport]:
    """Remove structural noise from DI Markdown while preserving evidence text."""
    options = options or ContentNormalizationOptions()
    tokens_before = count_tokens(content)
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")

    if options.strip_selection_marks:
        normalized = _SELECTION_MARKS_RE.sub("", normalized)

    repeated_lines_removed = 0
    if options.remove_repeated_headers:
        normalized, repeated_lines_removed = _remove_repeated_page_lines(normalized, options)

    if options.collapse_page_separators:
        normalized = _DUPLICATE_SEPARATOR_RE.sub("\n\n---", normalized)
    if options.collapse_blank_lines:
        normalized = _EXCESS_BLANK_LINES_RE.sub("\n\n", normalized)

    normalized = "\n".join(line.rstrip() for line in normalized.splitlines()).strip()
    tokens_after = count_tokens(normalized)
    reduction = (tokens_before - tokens_after) / tokens_before if tokens_before else 0.0
    report = NormalizationReport(
        characters_before=len(content),
        characters_after=len(normalized),
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        token_reduction_ratio=round(reduction, 4),
        repeated_lines_removed=repeated_lines_removed,
    )
    return normalized, report