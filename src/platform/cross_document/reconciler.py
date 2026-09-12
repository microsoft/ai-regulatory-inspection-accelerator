"""Template-configured adapter for cross-document LLM reconciliation."""

from __future__ import annotations

from src.platform.policy.evaluators import llm_mapper
from src.platform.reconciliation.llm_validation import (
    resolve_field_names,
    run_comparisons,
    run_item_type_checks,
)
from src.platform.shared.ai_client import AIClient
from src.platform.templates.template_loader import TemplateLoader


class CrossDocumentReconciler:
    """Provide policy-compatible LLM callables from one template and AI client."""

    def __init__(
        self,
        ai_client: AIClient,
        template: TemplateLoader,
        *,
        model: str,
        tenant_id: str = "",
    ) -> None:
        self._ai_client = ai_client
        self._template = template
        self._model = model
        self._tenant_id = tenant_id

    @property
    def document_aliases(self) -> dict[str, str]:
        """Return aliases required by deterministic cross-document checks."""
        return self._template.get_document_aliases()

    async def compare(
        self,
        *,
        payload: dict,
        cross_doc_rules: list,
        submission: list,
        managed_identity_client_id: str = "",
    ) -> dict:
        """Resolve field gaps and execute semantic comparisons."""
        del managed_identity_client_id
        case_id = str(payload.get("requestId", "unknown"))
        doc_field_index = llm_mapper.build_doc_field_index(submission)
        valid_rules = [
            rule for rule in cross_doc_rules
            if isinstance(rule.get("field"), str)
            and isinstance(rule.get("documents", []), list)
        ]
        fields = list(dict.fromkeys(rule["field"] for rule in valid_rules))
        field_resolution = await resolve_field_names(
            self._ai_client,
            model=self._model,
            case_id=case_id,
            tenant_id=self._tenant_id,
            prompt=self._template.get_prompt("cross_document_field_resolution"),
            rule_fields=fields,
            doc_field_index=doc_field_index,
            field_aliases=self._template.get_field_aliases(),
        )
        tasks = llm_mapper.build_comparison_tasks(
            valid_rules,
            doc_field_index,
            field_resolution,
            self.document_aliases,
        )
        findings = await run_comparisons(
            self._ai_client,
            model=self._model,
            case_id=case_id,
            tenant_id=self._tenant_id,
            prompt=self._template.get_prompt("cross_document_comparison"),
            tasks=tasks,
        )
        return {
            "success": True,
            "field_resolution": field_resolution,
            "comparison_findings": findings,
            "errors": [],
        }

    async def compare_item_types(
        self,
        *,
        items: list,
        source_doc_type: str,
        line_items: list,
        managed_identity_client_id: str = "",
    ) -> list[dict]:
        """Run template-configured item type comparisons."""
        del managed_identity_client_id
        case_id = str(items[0].get("requestId", "unknown")) if items else "unknown"
        return await run_item_type_checks(
            self._ai_client,
            model=self._model,
            case_id=case_id,
            tenant_id=self._tenant_id,
            prompt=self._template.get_prompt("item_type_comparison"),
            items=items,
            source_doc_type=source_doc_type,
            line_items=line_items,
            description_fields=self._template.get_item_description_fields(),
        )