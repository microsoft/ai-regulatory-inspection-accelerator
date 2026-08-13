"""Unit tests for src.platform.orchestration.submission

Ported from PAFN's function_app.py::inspector_http_start idempotency checks
(duplicate in-flight orchestration + already-completed case guards).
"""

from src.platform.orchestration.submission import SubmissionDecision, evaluate_submission


class TestAcceptedSubmissions:
    def test_no_existing_orchestration_or_case(self):
        assert evaluate_submission(None, None) == SubmissionDecision.ACCEPT

    def test_existing_orchestration_completed_status_not_in_progress_set(self):
        """'Completed' (terminal) runtime_status does not block a resubmission
        by itself - only Pending/Running/ContinuedAsNew do."""
        assert evaluate_submission("Completed", None) == SubmissionDecision.ACCEPT

    def test_existing_orchestration_failed_status(self):
        assert evaluate_submission("Failed", None) == SubmissionDecision.ACCEPT

    def test_existing_case_status_not_completed(self):
        assert evaluate_submission(None, "RECEIVED") == SubmissionDecision.ACCEPT


class TestDuplicateInProgress:
    def test_pending(self):
        assert evaluate_submission("Pending", None) == SubmissionDecision.DUPLICATE_IN_PROGRESS

    def test_running(self):
        assert evaluate_submission("Running", None) == SubmissionDecision.DUPLICATE_IN_PROGRESS

    def test_continued_as_new(self):
        assert evaluate_submission("ContinuedAsNew", None) == SubmissionDecision.DUPLICATE_IN_PROGRESS

    def test_in_progress_takes_priority_over_completed_case(self):
        """If (unusually) both signals are present, in-flight orchestration
        wins - matches PAFN's original check order (orchestration status
        checked before case status)."""
        assert evaluate_submission("Running", "COMPLETED") == SubmissionDecision.DUPLICATE_IN_PROGRESS


class TestAlreadyCompleted:
    def test_completed_case_no_orchestration_conflict(self):
        assert evaluate_submission(None, "COMPLETED") == SubmissionDecision.ALREADY_COMPLETED

    def test_completed_case_with_terminal_orchestration_status(self):
        assert evaluate_submission("Completed", "COMPLETED") == SubmissionDecision.ALREADY_COMPLETED
