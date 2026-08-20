"""Unit tests for the centralized token-tracking AI client."""

import asyncio
from types import SimpleNamespace

import pytest

from src.platform.shared.ai_client import AIClient, TokenUsage


def _response(*, content="done", model="gpt-test", usage=None):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        model=model,
        usage=usage,
    )


class TestAIClient:
    def test_tracks_usage_attribution_and_cached_tokens(self):
        events = []
        usage = SimpleNamespace(
            prompt_tokens=120,
            completion_tokens=30,
            total_tokens=150,
            prompt_tokens_details=SimpleNamespace(cached_tokens=80),
        )
        times = iter((10.0, 10.125))
        client = AIClient(
            lambda **kwargs: _response(usage=usage),
            track_event=lambda name, **fields: events.append((name, fields)),
            clock=lambda: next(times),
        )

        result = asyncio.run(
            client.complete(
                messages=[{"role": "user", "content": "private prompt"}],
                activity="reasoning",
                case_id="CASE-1",
                tenant_id="TENANT-1",
                model="deployment-name",
                temperature=0,
            )
        )

        assert result.content == "done"
        assert result.model == "gpt-test"
        assert result.usage == TokenUsage(120, 30, 150, 80)
        assert result.latency_ms == 125
        assert events == [(
            "LLMCallCompleted",
            {
                "case_id": "CASE-1",
                "tenant_id": "TENANT-1",
                "activity": "reasoning",
                "model": "gpt-test",
                "prompt_tokens": 120,
                "completion_tokens": 30,
                "total_tokens": 150,
                "cached_tokens": 80,
                "latency_ms": 125,
            },
        )]
        assert "private prompt" not in repr(events)

    def test_supports_async_mapping_response_and_missing_usage(self):
        async def complete_fn(**kwargs):
            return {
                "choices": [{"message": {"content": "mapped"}}],
                "model": "mapped-model",
            }

        result = asyncio.run(
            AIClient(complete_fn).complete(
                messages=[],
                activity="quality_assessment",
                case_id="CASE-2",
                tenant_id="TENANT-2",
                model="fallback-model",
            )
        )

        assert result.content == "mapped"
        assert result.model == "mapped-model"
        assert result.usage == TokenUsage()

    def test_derives_total_when_provider_omits_it(self):
        usage = {"prompt_tokens": 7, "completion_tokens": 3}
        result = asyncio.run(
            AIClient(lambda **kwargs: _response(usage=usage)).complete(
                messages=[],
                activity="gap_filling",
                case_id="CASE-3",
                tenant_id="TENANT-3",
                model="model",
            )
        )

        assert result.usage.total_tokens == 10

    def test_propagates_failure_and_emits_safe_telemetry(self):
        events = []

        def complete_fn(**kwargs):
            raise RuntimeError("provider response contained private content")

        client = AIClient(
            complete_fn,
            track_event=lambda name, **fields: events.append((name, fields)),
        )

        with pytest.raises(RuntimeError):
            asyncio.run(
                client.complete(
                    messages=[{"role": "user", "content": "private prompt"}],
                    activity="reasoning",
                    case_id="CASE-4",
                    tenant_id="TENANT-4",
                    model="model",
                )
            )

        assert events[0][0] == "LLMCallFailed"
        assert events[0][1]["error_type"] == "RuntimeError"
        assert "private" not in repr(events)