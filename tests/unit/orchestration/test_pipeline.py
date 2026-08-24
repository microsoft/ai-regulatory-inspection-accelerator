"""Unit tests for src.platform.orchestration.pipeline.run_pipeline

Ported/derived from PAFN's function_app.py::inspector_orchestrator behavior.
PAFN has no direct unit tests for the orchestrator itself (Durable Functions
orchestrators are hard to unit test without driving the generator manually),
so this test suite is new - it drives the orchestrator generator directly
with a FakeContext, asserting the exact sequence and payload of
call_activity_with_retry calls without requiring azure-functions or
azure-durable-functions to be installed.
"""

from datetime import datetime, timezone

from src.platform.orchestration.pipeline import DEFAULT_ACTIVITY_NAMES, run_pipeline


class FakeContext:
    """Duck-typed stand-in for azure.durable_functions.DurableOrchestrationContext."""

    def __init__(self, payload: dict, is_replaying: bool = False):
        self._payload = payload
        self.is_replaying = is_replaying
        self.current_utc_datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.calls: list[tuple[str, object, dict]] = []
        self.replay_flags: list[bool] = []

    def get_input(self) -> dict:
        return self._payload

    def call_activity_with_retry(self, name: str, retry_policy, input: dict):
        self.calls.append((name, retry_policy, input))
        self.replay_flags.append(self.is_replaying)
        return object()  # placeholder Task; the test driver injects the real result via gen.send()


def _drive(gen, *results):
    """Manually step an orchestrator generator, sending each activity result in turn."""
    next(gen)  # prime to the first yield
    for result in results[:-1]:
        gen.send(result)
    try:
        gen.send(results[-1])
    except StopIteration:
        pass


_RETRY_POLICY = object()
_PAYLOAD = {"requestId": "REQ-1", "items": [], "documents": [{"documentTypeId": "1", "checksum": "a"}]}
_REASONING_RESULT = {
    "success": True,
    "evidenceMap": {"field": {"value": "value", "confidence": 0.95}},
    "findings": [],
    "documentChecks": [],
}


class TestSuccessPath:
    def test_all_five_activities_called_in_order(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)

        pre_result = {"passed": True, "errors": [], "warnings": [], "documents": None}
        extraction_result = {"success": True, "extractedFields": {"doc1": {"field": "value"}}}
        policy_result = {
            "findings": [{"ruleCode": "R1", "result": "PASS"}],
            "documentChecks": [],
            "recommendation": "PASS",
            "confidence": 0.95,
            "aiRiskLevel": "LOW",
            "summary": "All checks passed.",
            "verdictId": "V-1",
        }
        _drive(gen, pre_result, extraction_result, _REASONING_RESULT, policy_result, {})

        names = [c[0] for c in ctx.calls]
        assert names == [
            DEFAULT_ACTIVITY_NAMES["pre_validation"],
            DEFAULT_ACTIVITY_NAMES["di_extraction"],
            DEFAULT_ACTIVITY_NAMES["reasoning"],
            DEFAULT_ACTIVITY_NAMES["rules_policy"],
            DEFAULT_ACTIVITY_NAMES["delivery"],
        ]

    def test_delivery_payload_on_success(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)

        pre_result = {"passed": True, "errors": [], "warnings": [{"code": "DUP_WARN"}], "documents": None}
        extraction_result = {"success": True, "extractedFields": {}}
        policy_result = {
            "findings": [{"ruleCode": "R1", "result": "PASS"}],
            "documentChecks": [{"code": "DC1"}],
            "recommendation": "PASS",
            "confidence": 0.9,
            "aiRiskLevel": "LOW",
            "summary": "OK",
            "verdictId": "V-1",
        }
        _drive(gen, pre_result, extraction_result, _REASONING_RESULT, policy_result, {})

        delivery_call = ctx.calls[-1]
        assert delivery_call[0] == DEFAULT_ACTIVITY_NAMES["delivery"]
        delivery_input = delivery_call[2]
        assert delivery_input["status"] == "COMPLETED"
        assert delivery_input["recommendation"] == "PASS"
        assert delivery_input["confidence"] == 0.9
        assert delivery_input["verdictId"] == "V-1"
        # Pre-validation warnings and policy findings are merged
        assert delivery_input["findings"] == [{"code": "DUP_WARN"}, {"ruleCode": "R1", "result": "PASS"}]
        assert delivery_input["documentChecks"] == [{"code": "DC1"}]
        assert "pipelineStartedAt" in delivery_input

    def test_retry_policy_passed_through_unchanged_to_every_call(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)
        _drive(
            gen,
            {"passed": True, "errors": [], "warnings": [], "documents": None},
            {"success": True, "extractedFields": {}},
            _REASONING_RESULT,
            {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
            {},
        )
        assert all(call[1] is _RETRY_POLICY for call in ctx.calls)

    def test_normalized_documents_propagated_to_downstream_activities(self):
        """When pre-validation returns a deduplicated document list, all
        downstream activities receive the updated payload, not the original."""
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)
        deduped_docs = [{"documentTypeId": "1", "checksum": "a"}]
        _drive(
            gen,
            {"passed": True, "errors": [], "warnings": [], "documents": deduped_docs},
            {"success": True, "extractedFields": {}},
            _REASONING_RESULT,
            {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
            {},
        )
        extraction_input = ctx.calls[1][2]
        assert extraction_input["documents"] == deduped_docs

    def test_reasoning_output_passed_to_rules_policy(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)
        extracted_fields = {"doc1": {"fields": {"invoice_number": "INV-1"}}}
        reasoning_result = {
            "success": True,
            "evidenceMap": {"invoice_number": {"value": "INV-1"}},
            "findings": [{"ruleCode": "EVIDENCE_CONFLICT", "result": "WARN"}],
            "documentChecks": [{"field": "invoice_number", "consistent": True}],
        }
        _drive(
            gen,
            {"passed": True, "errors": [], "warnings": [], "documents": None},
            {"success": True, "extractedFields": extracted_fields},
            reasoning_result,
            {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
            {},
        )

        reasoning_input = ctx.calls[2][2]
        assert reasoning_input == {"payload": _PAYLOAD, "extractedFields": extracted_fields}
        policy_input = ctx.calls[3][2]
        assert policy_input["evidenceMap"] == reasoning_result["evidenceMap"]
        assert policy_input["reasoningFindings"] == reasoning_result["findings"]
        assert policy_input["reasoningDocumentChecks"] == reasoning_result["documentChecks"]


class TestPreValidationFailure:
    def test_short_circuits_to_delivery_only(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)
        pre_result = {"passed": False, "errors": [{"code": "MISSING_DOC"}], "warnings": []}
        _drive(gen, pre_result)

        names = [c[0] for c in ctx.calls]
        assert names == [DEFAULT_ACTIVITY_NAMES["pre_validation"], DEFAULT_ACTIVITY_NAMES["delivery"]]

        delivery_input = ctx.calls[-1][2]
        assert delivery_input["status"] == "PRE_VALIDATION_FAILED"
        assert delivery_input["recommendation"] == "FAIL"
        assert delivery_input["confidence"] is None
        assert delivery_input["errors"] == [{"code": "MISSING_DOC"}]
        assert delivery_input["findings"] == []


class TestExtractionFailure:
    def test_short_circuits_to_delivery_only(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)
        pre_result = {"passed": True, "errors": [], "warnings": [], "documents": None}
        extraction_result = {"success": False, "errors": [{"code": "OCR_FAILED"}]}
        _drive(gen, pre_result, extraction_result)

        names = [c[0] for c in ctx.calls]
        assert names == [
            DEFAULT_ACTIVITY_NAMES["pre_validation"],
            DEFAULT_ACTIVITY_NAMES["di_extraction"],
            DEFAULT_ACTIVITY_NAMES["delivery"],
        ]

        delivery_input = ctx.calls[-1][2]
        assert delivery_input["status"] == "PIPELINE_ERROR"
        assert delivery_input["recommendation"] == "HOLD"
        assert delivery_input["confidence"] is None
        assert delivery_input["errors"] == [{"code": "OCR_FAILED"}]


class TestReasoningFailure:
    def test_short_circuits_to_delivery_with_hold(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)
        reasoning_errors = [{"code": "REASONING_UNAVAILABLE"}]
        _drive(
            gen,
            {"passed": True, "errors": [], "warnings": [], "documents": None},
            {"success": True, "extractedFields": {}},
            {"success": False, "errors": reasoning_errors},
        )

        assert [call[0] for call in ctx.calls] == [
            DEFAULT_ACTIVITY_NAMES["pre_validation"],
            DEFAULT_ACTIVITY_NAMES["di_extraction"],
            DEFAULT_ACTIVITY_NAMES["reasoning"],
            DEFAULT_ACTIVITY_NAMES["delivery"],
        ]
        delivery_input = ctx.calls[-1][2]
        assert delivery_input["status"] == "PIPELINE_ERROR"
        assert delivery_input["recommendation"] == "HOLD"
        assert delivery_input["errors"] == reasoning_errors


class TestActivityNameOverride:
    def test_custom_activity_names_used(self):
        ctx = FakeContext(_PAYLOAD)
        custom_names = {
            "pre_validation": "custom_pre_validation",
            "di_extraction": "custom_extraction",
            "reasoning": "custom_reasoning",
            "rules_policy": "custom_policy",
            "delivery": "custom_delivery",
        }
        gen = run_pipeline(ctx, activity_names=custom_names, retry_policy=_RETRY_POLICY)
        _drive(
            gen,
            {"passed": True, "errors": [], "warnings": [], "documents": None},
            {"success": True, "extractedFields": {}},
            _REASONING_RESULT,
            {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
            {},
        )
        names = [c[0] for c in ctx.calls]
        assert names == [
            "custom_pre_validation",
            "custom_extraction",
            "custom_reasoning",
            "custom_policy",
            "custom_delivery",
        ]

    def test_default_names_are_domain_neutral(self):
        names = " ".join(DEFAULT_ACTIVITY_NAMES.values()).lower()
        assert all(term not in names for term in ("food", "pafn", "customs", "halal"))

    def test_partial_override_falls_back_to_defaults(self):
        ctx = FakeContext(_PAYLOAD)
        gen = run_pipeline(ctx, activity_names={"delivery": "custom_delivery"}, retry_policy=_RETRY_POLICY)
        pre_result = {"passed": False, "errors": [], "warnings": []}
        _drive(gen, pre_result)
        names = [c[0] for c in ctx.calls]
        assert names == [DEFAULT_ACTIVITY_NAMES["pre_validation"], "custom_delivery"]


class TestTelemetryReplaySafety:
    def test_track_event_called_when_not_replaying(self):
        events = []
        ctx = FakeContext(_PAYLOAD, is_replaying=False)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY, track_event=lambda name, **kw: events.append(name))
        _drive(
            gen,
            {"passed": True, "errors": [], "warnings": [], "documents": None},
            {"success": True, "extractedFields": {}},
            _REASONING_RESULT,
            {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
            {},
        )
        assert "PipelineCompleted" in events

    def test_track_event_not_called_when_replaying(self):
        """Restart-resume safety: telemetry must not fire again during replay."""
        events = []
        ctx = FakeContext(_PAYLOAD, is_replaying=True)
        gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY, track_event=lambda name, **kw: events.append(name))
        _drive(
            gen,
            {"passed": True, "errors": [], "warnings": [], "documents": None},
            {"success": True, "extractedFields": {}},
            _REASONING_RESULT,
            {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
            {},
        )
        assert events == []

    def test_deterministic_replay_produces_identical_activity_calls(self):
        """Running the orchestrator twice with identical input must produce
        an identical sequence of activity calls - required for Durable
        Functions to safely replay history after a host restart."""
        def run_once():
            ctx = FakeContext(_PAYLOAD)
            gen = run_pipeline(ctx, retry_policy=_RETRY_POLICY)
            _drive(
                gen,
                {"passed": True, "errors": [], "warnings": [], "documents": None},
                {"success": True, "extractedFields": {}},
                _REASONING_RESULT,
                {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
                {},
            )
            return [(name, input) for name, _retry, input in ctx.calls]

        assert run_once() == run_once()

    def test_resume_from_each_checkpoint_replays_history_then_continues(self):
        results = [
            {"passed": True, "errors": [], "warnings": [], "documents": None},
            {"success": True, "extractedFields": {}},
            _REASONING_RESULT,
            {"findings": [], "recommendation": "PASS", "confidence": 1.0, "summary": "OK"},
            {},
        ]
        expected_names = list(DEFAULT_ACTIVITY_NAMES.values())

        for completed_count in range(1, len(results) + 1):
            events = []
            ctx = FakeContext(_PAYLOAD, is_replaying=True)
            gen = run_pipeline(
                ctx,
                retry_policy=_RETRY_POLICY,
                track_event=lambda name, events=events, **kwargs: events.append(name),
            )
            next(gen)
            for index, result in enumerate(results):
                if index + 1 == completed_count and completed_count < len(results):
                    ctx.is_replaying = False
                try:
                    gen.send(result)
                except StopIteration:
                    break

            assert [call[0] for call in ctx.calls] == expected_names
            assert ctx.replay_flags[:completed_count] == [True] * completed_count
            assert ctx.replay_flags[completed_count:] == [False] * (
                len(results) - completed_count
            )
            assert events == ([] if completed_count == len(results) else ["PipelineCompleted"])
