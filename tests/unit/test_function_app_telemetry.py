"""Tests for Function App token telemetry persistence."""

import asyncio
import json
from unittest.mock import Mock

import function_app


def test_save_telemetry_persists_provider_cache_provenance(monkeypatch):
    container = Mock()
    monkeypatch.setattr(function_app, "_get_cosmos_container", lambda: container)

    function_app._save_telemetry(
        "case-1",
        [{
            "documentId": "document-1",
            "stage": "document-intelligence",
            "model": "gpt-4.1-nano-2025-04-14",
            "promptTokens": 250,
            "completionTokens": 75,
            "cachedTokens": 62,
            "cacheMeasurement": "provider",
            "totalTokens": 325,
            "durationMs": 120,
        }],
        "fallback-model",
    )

    document = container.upsert_item.call_args.args[0]
    assert document["cachedTokens"] == 62
    assert document["cacheMeasurement"] == "provider"
    assert document["telemetrySchemaVersion"] == 2


def test_save_telemetry_marks_missing_cache_metadata_unavailable(monkeypatch):
    container = Mock()
    monkeypatch.setattr(function_app, "_get_cosmos_container", lambda: container)

    function_app._save_telemetry(
        "case-2",
        [{
            "documentId": "document-2",
            "stage": "document-intelligence",
            "promptTokens": 100,
            "completionTokens": 25,
            "cachedTokens": 0,
            "totalTokens": 125,
        }],
        "gpt-4.1-nano-2025-04-14",
    )

    document = container.upsert_item.call_args.args[0]
    assert document["cachedTokens"] == 0
    assert document["cacheMeasurement"] == "unavailable"
    assert document["telemetrySchemaVersion"] == 2


def test_get_telemetry_returns_service_unavailable_for_cosmos_failure(monkeypatch):
    def raise_unavailable():
        raise function_app._TelemetryUnavailableError("Cosmos telemetry query failed")

    monkeypatch.setattr(function_app, "_fetch_telemetry", raise_unavailable)

    response = asyncio.run(function_app.get_telemetry(Mock()))

    assert response.status_code == 503
    assert json.loads(response.get_body())["code"] == "TELEMETRY_UNAVAILABLE"


def test_get_telemetry_returns_success_for_valid_empty_result(monkeypatch):
    monkeypatch.setattr(function_app, "_fetch_telemetry", lambda: [])

    response = asyncio.run(function_app.get_telemetry(Mock()))

    assert response.status_code == 200
    assert json.loads(response.get_body()) == {"items": []}