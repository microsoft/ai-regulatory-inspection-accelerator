"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Template Loader

Generic loader for the ARIA template contract.  Given a template ID
(e.g. "food-safety"), loads ``evidence_types.json`` and the optional
``normalization.json`` profile from the template directory. It provides
document-type field and normalization lookups that replace hardcoded
configuration.

The caller is responsible for providing a ``template_root`` path (defaults
to the ``templates/`` directory adjacent to this package's workspace root).

Design notes:
  - ``_DOC_TYPE_ID_TO_NAME`` dict migrated to ``doc_type_id_mapping``
    inside ``evidence_types.json`` so adding a new ID requires only a
    JSON edit, no code change.
  - ``DI_MODEL_MAP`` migrated to the optional ``di_model`` field on each
    document type entry in ``evidence_types.json``.
  - ``_load_config()`` hardcoded path replaced by ``TemplateLoader`` which
    accepts a template ID and resolves the artifact path safely (no path
    traversal).
  - Caching retained via ``functools.lru_cache`` on the parsed config, so
    repeated calls within a single process pay only one file read.
"""

import json
import logging
import re
from copy import deepcopy
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_DI_MODEL = "prebuilt-layout"
_DEFAULT_FIELDS = ["company_name", "issue_date", "goods_description"]

# Template ID must be a safe kebab-case identifier (no path separators or dots).
_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _templates_root() -> Path:
    """Return the absolute path to the ``templates/`` directory.

    Walks up from this file to the workspace root (the directory that
    contains both ``src/`` and ``templates/``).
    """
    here = Path(__file__).resolve()
    # Climb: templates/template_loader.py → platform → src → workspace root
    workspace = here.parent.parent.parent.parent
    return workspace / "templates"


@lru_cache(maxsize=16)
def _load_evidence_types(template_id: str, templates_root: Path) -> dict:
    """Load and cache the evidence_types.json for a given template.

    Args:
        template_id: Validated kebab-case template identifier.
        templates_root: Absolute path to the templates directory.

    Returns:
        Parsed dict with keys ``doc_type_id_mapping`` and ``document_types``.

    Raises:
        FileNotFoundError: Template directory or evidence_types.json missing.
        ValueError: File contains invalid JSON or missing required keys.
    """
    template_dir = templates_root / template_id
    evidence_path = template_dir / "evidence_types.json"

    if not template_dir.is_dir():
        raise FileNotFoundError(
            f"Template directory not found: {template_dir}"
        )
    if not evidence_path.is_file():
        raise FileNotFoundError(
            f"evidence_types.json not found for template '{template_id}': {evidence_path}"
        )

    try:
        with open(evidence_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"evidence_types.json for template '{template_id}' contains invalid JSON: {exc}"
        ) from exc

    if "document_types" not in data or not isinstance(data["document_types"], list):
        raise ValueError(
            f"evidence_types.json for template '{template_id}' must contain a "
            "'document_types' list."
        )

    return data


@lru_cache(maxsize=16)
def _load_normalization_config(template_id: str, templates_root: Path) -> dict:
    """Load an optional template-owned normalization profile."""
    config_path = templates_root / template_id / "normalization.json"
    if not config_path.is_file():
        return {}
    try:
        with open(config_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"normalization.json for template '{template_id}' contains invalid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise TypeError(
            f"normalization.json for template '{template_id}' must contain an object."
        )
    return data


@lru_cache(maxsize=16)
def _load_knowledge_pack(template_id: str, templates_root: Path) -> dict:
    """Load an optional template-owned Knowledge Pack."""
    knowledge_pack_path = templates_root / template_id / "knowledge_pack.json"
    if not knowledge_pack_path.is_file():
        return {}
    try:
        with open(knowledge_pack_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"knowledge_pack.json for template '{template_id}' contains invalid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get("prompts", {}), dict):
        raise TypeError(
            f"knowledge_pack.json for template '{template_id}' must contain a 'prompts' object."
        )
    return data


def _merge_dicts(base: dict, override: dict) -> dict:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


class TemplateLoader:
    """Provides field-schema lookups backed by a template's ``evidence_types.json``.

    Usage::

        loader = TemplateLoader.for_template("my-template")
        doc_type = loader.resolve_doc_type("50", fallback="Invoice")
        fields = loader.get_fields(doc_type)
        di_model = loader.get_di_model(doc_type)

    All public methods are pure (no I/O after construction) and safe to call
    concurrently.
    """

    def __init__(self, template_id: str, templates_root: Path | None = None) -> None:
        if not _SAFE_ID_RE.match(template_id):
            raise ValueError(
                f"Invalid template_id {template_id!r}. "
                "Must be kebab-case (a-z, 0-9, hyphens only)."
            )
        self._template_id = template_id
        root = templates_root or _templates_root()
        self._data = _load_evidence_types(template_id, root)
        self._normalization = _load_normalization_config(template_id, root)
        self._knowledge_pack = _load_knowledge_pack(template_id, root)
        self._id_mapping: dict[str, str] = self._data.get("doc_type_id_mapping") or {}
        # Index document_types by doc_type key for O(1) lookups.
        self._by_type: dict[str, dict] = {}
        for entry in self._data["document_types"]:
            dt = entry.get("doc_type", "")
            if dt and dt not in self._by_type:
                self._by_type[dt] = entry
            elif dt in self._by_type:
                logger.warning(
                    "Duplicate doc_type '%s' in evidence_types.json for template '%s' — "
                    "first definition wins.",
                    dt, template_id,
                )

    @classmethod
    def for_template(
        cls, template_id: str, templates_root: Path | None = None
    ) -> "TemplateLoader":
        """Convenience factory that constructs a ``TemplateLoader`` for the
        given template ID, resolving ``templates_root`` automatically."""
        return cls(template_id, templates_root)

    # ------------------------------------------------------------------
    # Public query interface
    # ------------------------------------------------------------------

    def resolve_doc_type(self, doc_type_id: str, fallback: str | None = None) -> str:
        """Return the canonical ``doc_type`` name for a submission's
        ``documentTypeId``.

        Checks the template's ``doc_type_id_mapping`` first.  Falls back
        to ``fallback`` (typically the client-supplied ``documentType``
        string) if the ID is unknown, then to ``"Other"``.

        This replaces the hardcoded ``_DOC_TYPE_ID_TO_NAME`` dict in
        ``shared/prompts.py``.
        """
        canonical = self._id_mapping.get(str(doc_type_id))
        if canonical:
            return canonical
        if fallback:
            return fallback
        logger.warning(
            "doc_type_id '%s' not in template '%s' id mapping and no fallback provided — "
            "defaulting to 'Other'.",
            doc_type_id, self._template_id,
        )
        return "Other"

    def get_di_model(self, doc_type: str) -> str:
        """Return the Azure DI model ID for a document type.

        Falls back to ``DEFAULT_DI_MODEL`` (``prebuilt-layout``) when the
        document type has no explicit ``di_model`` configured.  This
        replaces the hardcoded ``DI_MODEL_MAP`` dict in
        ``activities/di_extraction.py``.
        """
        entry = self._by_type.get(doc_type)
        if entry:
            model = entry.get("di_model")
            if model:
                return model
        return DEFAULT_DI_MODEL

    def get_fields(self, doc_type: str) -> list[str]:
        """Return the ordered list of canonical field names for a document type.

        Falls back to the ``Other`` type, then to a minimal default.
        This replaces ``get_fields_for_doc_type()`` from ``shared/prompts.py``.
        """
        entry = self._by_type.get(doc_type)
        if entry is not None:
            return list(entry.get("fields") or _DEFAULT_FIELDS)

        logger.warning(
            "doc_type '%s' not found in template '%s' — falling back to 'Other' fields.",
            doc_type, self._template_id,
        )
        other = self._by_type.get("Other")
        if other:
            return list(other.get("fields") or _DEFAULT_FIELDS)
        return list(_DEFAULT_FIELDS)

    def get_line_item_fields(self, doc_type: str) -> list[str]:
        """Return the list of per-row line-item field names for a document type.

        Returns an empty list when the type defines no line-item fields.
        This replaces ``get_line_item_fields_for_doc_type()`` from
        ``shared/prompts.py``.
        """
        entry = self._by_type.get(doc_type)
        if entry:
            return list(entry.get("line_item_fields") or [])
        return []

    def get_doc_notes(self, doc_type: str) -> str | None:
        """Return the optional extraction-hint string for a document type.

        Returns ``None`` when the type has no notes.
        This replaces ``get_doc_notes_for_doc_type()`` from
        ``shared/prompts.py``.
        """
        entry = self._by_type.get(doc_type)
        if entry:
            return entry.get("doc_notes")
        return None

    def get_normalization_config(self, doc_type: str) -> dict:
        """Return global normalization settings merged with document overrides."""
        defaults = self._normalization.get("defaults", {})
        overrides = self._normalization.get("document_types", {}).get(doc_type, {})
        return _merge_dicts(defaults, overrides)

    def get_quality_threshold(self, doc_type: str) -> float:
        """Return the template-configured OCR quality threshold for a document type."""
        config = self.get_normalization_config(doc_type)
        threshold = float(config.get("quality_threshold", 0.75))
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"quality_threshold for '{doc_type}' must be between 0.0 and 1.0."
            )
        return threshold

    def get_prompt(self, prompt_name: str, **values: str) -> str:
        """Render a named system prompt from the template Knowledge Pack."""
        prompt = self._knowledge_pack.get("prompts", {}).get(prompt_name)
        if not isinstance(prompt, str) or not prompt.strip():
            raise KeyError(
                f"Prompt '{prompt_name}' is not defined in the Knowledge Pack "
                f"for template '{self._template_id}'."
            )
        for name, value in values.items():
            prompt = prompt.replace(f"{{{{{name}}}}}", value)
        unresolved = re.findall(r"\{\{([a-z_][a-z0-9_]*)\}\}", prompt)
        if unresolved:
            raise ValueError(
                f"Prompt '{prompt_name}' is missing values for: {', '.join(sorted(set(unresolved)))}"
            )
        return prompt

    def known_doc_types(self) -> list[str]:
        """Return the list of all doc_type keys defined in this template."""
        return list(self._by_type.keys())
