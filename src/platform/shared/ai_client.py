"""Centralized AI completion wrapper with token usage attribution.

The Core Platform does not construct provider SDK clients here. Deployments
inject a completion callable, keeping authentication and provider setup at the
deployment boundary while ensuring every LLM call reports usage consistently.
"""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TokenUsage:
    """Normalized token counts reported by an AI provider."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cached_tokens: int = 0


@dataclass(frozen=True)
class AIResult:
    """Completion content and attributed provider usage."""

    content: str
    model: str
    usage: TokenUsage
    latency_ms: int


class AIClient:
    """Route an AI completion through one token-tracking boundary."""

    def __init__(
        self,
        complete_fn: Callable[..., Any],
        track_event: Callable[..., None] | None = None,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._complete_fn = complete_fn
        self._track_event = track_event
        self._clock = clock

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        activity: str,
        case_id: str,
        tenant_id: str,
        model: str,
        **provider_options: Any,
    ) -> AIResult:
        """Execute one completion and emit attributed usage telemetry.

        The injected callable may be synchronous or asynchronous and should
        return an OpenAI-compatible response object or mapping.
        """
        started_at = self._clock()
        try:
            response = self._complete_fn(
                messages=messages,
                model=model,
                **provider_options,
            )
            if inspect.isawaitable(response):
                response = await response

            latency_ms = max(0, round((self._clock() - started_at) * 1000))
            usage = _extract_usage(_value(response, "usage"))
            result = AIResult(
                content=_extract_content(response),
                model=str(_value(response, "model") or model),
                usage=usage,
                latency_ms=latency_ms,
            )
            self._emit(
                "LLMCallCompleted",
                activity=activity,
                case_id=case_id,
                tenant_id=tenant_id,
                model=result.model,
                usage=usage,
                latency_ms=latency_ms,
            )
            return result
        except Exception as exc:
            latency_ms = max(0, round((self._clock() - started_at) * 1000))
            if self._track_event is not None:
                self._track_event(
                    "LLMCallFailed",
                    case_id=case_id,
                    tenant_id=tenant_id,
                    activity=activity,
                    model=model,
                    error_type=type(exc).__name__,
                    latency_ms=latency_ms,
                )
            raise

    def _emit(
        self,
        event_name: str,
        *,
        activity: str,
        case_id: str,
        tenant_id: str,
        model: str,
        usage: TokenUsage,
        latency_ms: int,
    ) -> None:
        if self._track_event is None:
            return
        self._track_event(
            event_name,
            case_id=case_id,
            tenant_id=tenant_id,
            activity=activity,
            model=model,
            prompt_tokens=usage.prompt_tokens,
            completion_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            cached_tokens=usage.cached_tokens,
            latency_ms=latency_ms,
        )


def _value(value: Any, name: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _extract_usage(raw_usage: Any) -> TokenUsage:
    prompt_tokens = int(_value(raw_usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(_value(raw_usage, "completion_tokens", 0) or 0)
    total_tokens = int(
        _value(raw_usage, "total_tokens", prompt_tokens + completion_tokens)
        or prompt_tokens + completion_tokens
    )
    prompt_details = _value(raw_usage, "prompt_tokens_details")
    cached_tokens = int(_value(prompt_details, "cached_tokens", 0) or 0)
    return TokenUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cached_tokens=cached_tokens,
    )


def _extract_content(response: Any) -> str:
    choices = _value(response, "choices", []) or []
    if not choices:
        return ""
    message = _value(choices[0], "message")
    return str(_value(message, "content", "") or "")