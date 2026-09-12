"""Deterministic exact duplicate detection before AI processing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class DuplicateMatch:
    """A duplicate document and the document it duplicates."""

    document_id: str
    duplicate_of: str
    checksum: str


class DuplicateDetector:
    """Detect exact content duplicates using SHA-256."""

    def __init__(self) -> None:
        self._first_by_checksum: dict[str, str] = {}

    @staticmethod
    def checksum(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def check(self, document_id: str, content: bytes) -> DuplicateMatch | None:
        digest = self.checksum(content)
        first = self._first_by_checksum.setdefault(digest, document_id)
        if first == document_id:
            return None
        return DuplicateMatch(document_id=document_id, duplicate_of=first, checksum=digest)

    def check_many(self, documents: list[tuple[str, bytes]]) -> list[DuplicateMatch]:
        return [match for document_id, content in documents if (match := self.check(document_id, content))]
