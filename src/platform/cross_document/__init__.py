"""Cross-document validation boundary."""

from src.platform.cross_document.reconciler import CrossDocumentReconciler
from src.platform.policy.evaluators.cross_document import validate_cross_docs

__all__ = ["CrossDocumentReconciler", "validate_cross_docs"]