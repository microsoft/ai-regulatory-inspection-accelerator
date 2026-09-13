"""Append-only audit event service and case export."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    request_id: str
    event_type: str
    timestamp: str
    payload: dict[str, Any]


class AuditEventStore(Protocol):
    def append(self, event: dict[str, Any]) -> dict[str, Any]: ...
    def list_for_case(self, request_id: str) -> list[dict[str, Any]]: ...


class InMemoryAuditEventStore:
    """Append-only store used by tests and local deployments."""

    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        stored = dict(event)
        stored["immutable"] = True
        self._events.append(stored)
        return stored

    def list_for_case(self, request_id: str) -> list[dict[str, Any]]:
        return [event for event in self._events if event.get("requestId") == request_id]


class AuditService:
    """Record state, LLM, rule, delivery, and human-action events."""

    def __init__(self, store: AuditEventStore) -> None:
        self.store = store

    def record(self, request_id: str, event_type: str, payload: dict[str, Any]) -> AuditEvent:
        event = AuditEvent(
            event_id=f"{request_id}:{event_type}:{len(self.store.list_for_case(request_id)) + 1}",
            request_id=request_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=dict(payload),
        )
        self.store.append({
            "id": event.event_id,
            "requestId": event.request_id,
            "eventType": event.event_type,
            "timestamp": event.timestamp,
            "payload": event.payload,
        })
        return event

    def export_case(self, request_id: str) -> dict[str, Any]:
        events = sorted(self.store.list_for_case(request_id), key=lambda event: event.get("timestamp", ""))
        return {"requestId": request_id, "events": events}
