"""
Pure data helpers for the Rules Engine.

All content (country maps, document name map) is domain-neutral algorithm data.
"""

import re as _re
from collections.abc import Mapping

import pycountry


def normalize_country(value: str, aliases: Mapping[str, str] | None = None) -> str:
    """Resolve a country value to ISO alpha-2 using injected aliases."""
    if not value:
        return value
    stripped = value.strip()
    upper = stripped.upper()
    country = (
        pycountry.countries.get(alpha_2=upper)
        or pycountry.countries.get(alpha_3=upper)
        or pycountry.countries.get(numeric=stripped)
    )
    if country:
        return country.alpha_2
    configured_aliases = {
        str(alias).strip().casefold(): str(code).strip().upper()
        for alias, code in (aliases or {}).items()
        if str(alias).strip() and str(code).strip()
    }
    alias_code = configured_aliases.get(stripped.casefold())
    if alias_code:
        return alias_code
    for alias, code in configured_aliases.items():
        if alias in stripped.casefold():
            return code
    tokens = _re.split(r"[\s\-,/]+", stripped)
    for token in tokens:
        tok_upper = token.upper().strip()
        if not tok_upper:
            continue
        c = (
            pycountry.countries.get(alpha_2=tok_upper)
            or pycountry.countries.get(alpha_3=tok_upper)
        )
        if c:
            return c.alpha_2
        token_alias = configured_aliases.get(tok_upper.casefold())
        if token_alias:
            return token_alias
    try:
        results = pycountry.countries.search_fuzzy(stripped)
        if results:
            return results[0].alpha_2
    except LookupError:
        pass
    return stripped.lower()


def resolve_document_name(rule_doc_name, aliases: dict | None = None) -> str:
    """Map a rule-side document name to its submission-side equivalent.

    ``aliases`` comes from the active template's ``doc_type_aliases``; without it
    the name is returned unchanged.
    """
    if not isinstance(rule_doc_name, str):
        return str(rule_doc_name)
    return (aliases or {}).get(rule_doc_name, rule_doc_name)


def build_doc_field_index(submission: list, min_confidence: float = 0.0) -> dict:
    """Flatten the submission list into {doc_name: {field_name: value_string}}."""
    index = {}
    for item in submission:
        doc_name = item.get("document", "")
        fields = item.get("fields", {})
        flat_fields = {}
        for k, v in fields.items():
            if isinstance(v, dict):
                confidence = v.get("confidence", 0.0)
                if confidence < min_confidence:
                    continue
                extracted = v.get("value")
            else:
                extracted = v
            if extracted is not None and str(extracted).lower() not in ("null", "") and str(extracted).strip():
                flat_fields[k] = str(extracted)
        index[doc_name] = flat_fields
    return index


def get_field_value(
    doc_fields: dict,
    rule_field: str,
    field_resolution: dict | None = None,
    doc_name: str | None = None,
) -> str | None:
    """Resolve a rule field name to its value in a document's extracted fields."""
    if field_resolution and doc_name:
        resolved = field_resolution.get(rule_field, {}).get(doc_name)
        if resolved and resolved in doc_fields:
            return doc_fields[resolved]
    if rule_field in doc_fields:
        return doc_fields[rule_field]
    return None
