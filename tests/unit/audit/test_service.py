"""Tests for append-only audit events."""

from src.platform.audit.service import AuditService, InMemoryAuditEventStore


def test_audit_events_are_immutable_and_export_in_order():
    service = AuditService(InMemoryAuditEventStore())
    first = service.record("CASE-1", "RULE_EVALUATED", {"ruleId": "R1"})
    second = service.record("CASE-1", "DECISION_DELIVERED", {"recommendation": "PASS"})

    export = service.export_case("CASE-1")
    assert first.event_id != second.event_id
    assert len(export["events"]) == 2
    assert all(event["immutable"] is True for event in export["events"])
    assert export["events"][0]["eventType"] == "RULE_EVALUATED"
