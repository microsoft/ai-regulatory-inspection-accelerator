"""
ARIA — AI Regulatory Inspection Accelerator
Core Platform — Document Intelligence — Field Normalization

Value-level normalization for fields extracted by the DI Extraction Agent:
Arabic/BiDi numeral and date handling, currency code extraction, field-alias
resolution, and expiry-date computation. All functions here are pure
(no I/O, no LLM calls) and config-driven — no document-type assumptions or
field vocabulary are hardcoded.

Ported from PAFN's di/di_normalization.py, generalized:
  - Removed the hardcoded `FIELD_ALIASES` dict (customs/food-safety field
    names such as `bill_awb_manifest_number`, `net_weight`, `tin_number`).
    Field aliases are now a caller-supplied `alias_overrides` parameter —
    this is template config (see EPIC-11/Template Framework's
    `alias_pairs.json` artifact), not Core Platform content.
  - Removed the hardcoded `KNOWN_COUNTRIES` list (Gulf/Middle-East-biased).
    `extract_country` now requires the caller to supply the candidate
    country list.
  - Removed the hardcoded `_DATE_FIELDS` / `_NUMERIC_FIELDS` sets and
    `_ISSUE_DATE_FIELDS` tuple used by PAFN's rule-based normalization and
    expiry computation — these are now caller-supplied field-name
    collections, defaulting to empty (no-op) rather than assuming any
    particular document schema.
  - Removed direct `AzureOpenAI` client usage (`normalize_fields_with_llm`,
    `resolve_unmatched_fields_with_llm`). LLM-based field correction and
    semantic field mapping require a token-tracking AI client, which is a
    separate Core Platform component (see the AI client port issue) not yet
    available. `canonicalize_fields` accepts an optional injectable
    `semantic_resolver` callback with the same contract PAFN's LLM step
    used, so a template/deployment can wire in real LLM resolution later
    without changing this module.
  - Kept the currency-code allow-list as an overridable default (ISO 4217
    codes are a global standard, not customer-specific content) and the
    BiDi-mark-stripping logic (Unicode control characters, not business
    content).
"""

import re
from collections.abc import Callable
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# Arabic numeral / date / currency normalization (fully generic - no
# document-type or field-name assumptions)
# ---------------------------------------------------------------------------

_EASTERN_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

_DATE_PATTERN = re.compile(
    r"(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})|"
    r"(\d{4}[-/\.]\d{1,2}[-/\.]\d{1,2})|"
    r"(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4})|"
    r"(\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4})|"
    r"([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})"
)

# ISO 4217 codes for the currencies most traded/held as reserves globally
# (IMF SDR basket - USD, EUR, JPY, GBP, CNY - plus the next most common
# major-economy currencies). This default is deliberately NOT weighted
# toward any single region; a template whose documents use other
# currencies (e.g. Gulf, Latin American, African) should pass its own
# `currency_codes` set rather than relying on this default.
DEFAULT_CURRENCY_CODES = frozenset({
    "USD", "EUR", "JPY", "GBP", "CNY", "AUD", "CAD", "CHF", "INR",
})

# Unicode BiDi/directional control marks that can leak into OCR output for
# mixed-direction (RTL/LTR) documents and must be stripped from final values.
_BIDI_MARKS = re.compile(r"[\u200E\u200F\u200B\u202A-\u202E\u2066-\u2069]+")


def convert_arabic_numerals(value: str) -> str:
    """Convert Eastern Arabic digits (٠-٩) to Western digits (0-9), and
    normalize the Arabic decimal separator (٫ U+066B) to a period and the
    Arabic thousands separator (٬ U+066C) by stripping it."""
    if not value:
        return value
    result = value.translate(_EASTERN_ARABIC_DIGITS)
    result = result.replace("\u066B", ".")
    result = result.replace("\u066C", "")
    return result


def normalize_arabic_number(value: str) -> str | None:
    """Normalize an Arabic/mixed numeral string to a clean Western number.

    Handles Eastern Arabic digits, the Arabic decimal mark, and comma-vs-
    period thousands/decimal ambiguity. Returns the cleaned number string,
    or None if no digits are found.
    """
    if not value:
        return None

    cleaned = convert_arabic_numerals(value)
    cleaned = re.sub(r"[^\d.,-]", "", cleaned)
    if not cleaned or not re.search(r"\d", cleaned):
        return None

    if "," in cleaned and "." in cleaned:
        last_comma = cleaned.rfind(",")
        last_period = cleaned.rfind(".")
        if last_comma > last_period:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        last_part = parts[-1]
        if len(last_part) == 3 and len(parts) > 1:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")

    return cleaned


def normalize_arabic_date(value: str) -> str | None:
    """Normalize an Arabic/mixed-numeral date string to ISO-8601 (YYYY-MM-DD).

    Handles Eastern Arabic digits mixed with Western, and common
    slash/dash-separated date formats. Returns None if not parseable.
    """
    if not value:
        return None

    cleaned = convert_arabic_numerals(value)
    cleaned = re.sub(r"[^\d/-]", " ", cleaned).strip()

    date_match = re.search(r"(\d{1,4})[/-](\d{1,2})[/-](\d{1,4})", cleaned)
    if not date_match:
        return None

    a, b, c = int(date_match.group(1)), int(date_match.group(2)), int(date_match.group(3))

    if a > 31:
        year, month, day = a, b, c
    elif c > 31:
        day, month, year = a, b, c
    else:
        if len(date_match.group(1)) == 4:
            year, month, day = a, b, c
        elif len(date_match.group(3)) == 4:
            day, month, year = a, b, c
        else:
            return None

    if year < 100:
        year += 2000 if year < 50 else 1900

    if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100):
        return None

    return f"{year:04d}-{month:02d}-{day:02d}"


def normalize_date(value: str) -> str | None:
    """Extract a date substring from a value string, if present."""
    if not value:
        return None
    match = _DATE_PATTERN.search(value)
    return match.group(0).strip() if match else None


def normalize_currency(value: str, currency_codes: frozenset[str] | None = None) -> str | None:
    """Extract an ISO 4217 currency code from an amount value.

    Examples: '$54,064.57AUD' -> 'AUD', 'USD 1,234.56' -> 'USD', '€500' -> 'EUR'.
    """
    if not value:
        return None
    codes = currency_codes if currency_codes is not None else DEFAULT_CURRENCY_CODES

    value_upper = value.upper()
    code_pattern = r"\b(" + "|".join(sorted(codes)) + r")\b"
    code_match = re.search(code_pattern, value_upper)
    if code_match:
        return code_match.group(1)

    if "$" in value:
        if "AUD" in value_upper or "A$" in value:
            return "AUD"
        if "CAD" in value_upper or "C$" in value:
            return "CAD"
        if "NZD" in value_upper:
            return "NZD"
        if "HKD" in value_upper or "HK$" in value:
            return "HKD"
        if "SGD" in value_upper or "S$" in value:
            return "SGD"
        return "USD"
    if "€" in value:
        return "EUR"
    if "£" in value:
        return "GBP"
    if "¥" in value:
        return "JPY"

    return None


def strip_trailing_date_suffix(value: str) -> str:
    """Strip a trailing '/ DD.MM.YYYY'-style date suffix from an identifier.

    Example: '91993233/ 08.11.2024' -> '91993233'.
    """
    if not value:
        return value
    cleaned = re.sub(r"[/\s]+\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4}\s*$", "", value)
    return cleaned.strip() if cleaned.strip() else value


def unwrap_brackets(value: str) -> str:
    """Strip enclosing parentheses or square brackets from an identifier.

    Example: '(208563)' -> '208563'.
    """
    if not value:
        return value
    value = value.strip()
    if value.startswith("(") and value.endswith(")"):
        return value[1:-1].strip()
    if value.startswith("[") and value.endswith("]"):
        return value[1:-1].strip()
    return value


def extract_country(value: str, known_countries: list[str]) -> str | None:
    """Extract a country name from a value that may contain a city/address
    prefix (e.g. 'HYDERABAD ... INDIA' -> 'India').

    `known_countries` is caller-supplied (template config / reference data) -
    Core Platform has no built-in country list.
    """
    if not value or not known_countries:
        return None
    for country in known_countries:
        pattern = rf"[,.\s]+{re.escape(country)}\.?\s*$"
        if re.search(pattern, value, re.IGNORECASE):
            return country.title() if country.isupper() else country
    return None


def strip_bidi_marks(value: str) -> str:
    """Strip Unicode BiDi/directional control marks from a value.

    OCR of mixed-direction (RTL/LTR) documents can leave directional marks
    embedded in extracted text; these must not leak into final field values.
    """
    if not value:
        return value
    return _BIDI_MARKS.sub("", value).strip()


# ---------------------------------------------------------------------------
# Expiry computation from an issue date + validity period
# ---------------------------------------------------------------------------

_VALIDITY_PERIOD_RE = re.compile(r"(\d+)\s*(year|month|week|day)s?", re.IGNORECASE)


def _add_calendar_duration(dt: date, amount: int, unit: str) -> date | None:
    """Add a calendar duration (years/months/weeks/days) to a date using
    only the standard library (no python-dateutil dependency)."""
    if unit == "week":
        return dt + timedelta(weeks=amount)
    if unit == "day":
        return dt + timedelta(days=amount)
    if unit == "year":
        total_months = amount * 12
    elif unit == "month":
        total_months = amount
    else:
        return None

    month_index = dt.month - 1 + total_months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp day to the target month's last valid day (e.g. Jan 31 + 1 month -> Feb 28/29).
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day_of_month = (next_month_first - timedelta(days=1)).day
    day = min(dt.day, last_day_of_month)
    return dt.replace(year=year, month=month, day=day)


def compute_expiry_from_validity_period(
    fields: dict,
    issue_date_fields: tuple[str, ...] = ("issue_date",),
    validity_field_pattern: re.Pattern[str] | None = None,
    expiry_field: str = "expiry_date",
) -> dict:
    """Compute `expiry_field` from an issue date + a validity/duration
    expression found elsewhere in `fields`, if `expiry_field` is not already
    populated.

    Args:
        fields: dict of {field_name: {"value": ..., "confidence": ...}}.
        issue_date_fields: field names to check (in priority order) for an
            ISO-8601 issue date. Defaults to just "issue_date"; a template
            with multiple issue-date field names (e.g. certificate vs.
            license) should pass its own tuple.
        validity_field_pattern: compiled regex used to find a field *name*
            that holds a validity/duration expression (e.g. "2 years").
            Defaults to matching "validity"/"valid_until"/"valid_for".
        expiry_field: the field name to populate. Defaults to "expiry_date".

    Modifies `fields` in-place and returns it.
    """
    if fields.get(expiry_field, {}).get("value"):
        return fields

    issue_date_str = None
    issue_confidence = 0.0
    for field_name in issue_date_fields:
        entry = fields.get(field_name, {})
        val = entry.get("value")
        if val:
            issue_date_str = str(val)
            issue_confidence = entry.get("confidence", 0.85)
            break
    if not issue_date_str:
        return fields

    key_pattern = validity_field_pattern or re.compile(r"validity|valid_until|valid_for", re.IGNORECASE)
    period_text = None
    for key, entry in fields.items():
        if key_pattern.search(key) and entry.get("value"):
            period_text = str(entry["value"])
            break
    if not period_text:
        return fields

    match = _VALIDITY_PERIOD_RE.search(period_text)
    if not match:
        return fields

    amount = int(match.group(1))
    unit = match.group(2).lower()

    try:
        issue_date = date.fromisoformat(issue_date_str)
    except ValueError:
        return fields

    expiry_date = _add_calendar_duration(issue_date, amount, unit)
    if expiry_date is None:
        return fields
    fields[expiry_field] = {
        "value": expiry_date.strftime("%Y-%m-%d"),
        "confidence": round(issue_confidence * 0.90, 4),
    }
    return fields


# ---------------------------------------------------------------------------
# Field alias resolution and canonicalization (config-driven)
# ---------------------------------------------------------------------------

def normalize_key(key: str) -> str:
    """Normalize a key for approximate/fuzzy alias matching."""
    return re.sub(r"[^a-z0-9]+", "", key.lower())


def build_field_alias_maps(
    allowed_fields: list[str],
    alias_overrides: dict[str, list[str]] | None = None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Build exact and normalized alias maps to canonical allowed fields.

    `alias_overrides` is the caller-supplied field-name -> alias-list map
    (template config, e.g. `alias_pairs.json`). With no overrides, only the
    field name itself and its underscore/space variant are used as aliases.

    Fields are processed shortest-name-first so a more specific field name
    (e.g. "net_weight_total") wins over a shorter one ("net_weight") for any
    shared alias.
    """
    exact: dict[str, str] = {}
    normalized: dict[str, str] = {}
    overrides = alias_overrides or {}

    sorted_fields = sorted(allowed_fields, key=len)
    for field in sorted_fields:
        aliases = {field, field.replace("_", " ")}
        aliases.update(overrides.get(field, []))
        for alias in aliases:
            a = alias.strip().lower()
            if not a:
                continue
            exact[a] = field
            n = normalize_key(a)
            if n:
                normalized[n] = field

    return exact, normalized


SemanticResolver = Callable[[list[dict], list[str]], dict[str, str]]
"""Injectable LLM-based semantic field resolver.

Signature: `resolver(unmatched_kvs, unfilled_fields) -> {original_key: target_field}`
where `unmatched_kvs` is a list of `{"key": str, "value": str, "confidence": float}`
and `unfilled_fields` is the list of target field names still without a value.
Only successful, validated mappings should be returned. Supplying this is
optional - without it, canonicalization relies on exact/alias matching only.
"""


def canonicalize_fields(
    key_value_pairs: list[dict],
    allowed_fields: list[str],
    alias_overrides: dict[str, list[str]] | None = None,
    semantic_resolver: SemanticResolver | None = None,
    equivalent_field_groups: list[tuple[str, ...]] | None = None,
) -> dict:
    """Map raw extracted key/value pairs onto a document type's canonical
    field schema, using exact/alias matching first and an optional
    injectable LLM-based semantic resolver as a fallback.

    Args:
        key_value_pairs: list of `{"key": str, "value": str, "confidence": float,
            "canonical_field": str | None}` (canonical_field pre-resolved
            upstream, e.g. by the DI Extraction Agent).
        allowed_fields: the document type's full field schema (from template
            config) - every field will be present in the output, with
            `{"value": None}` if not extracted.
        alias_overrides: field name -> list of alias strings (template config).
        semantic_resolver: optional injectable callback for LLM-based
            fallback resolution of otherwise-unmatched key/value pairs.
        equivalent_field_groups: groups of field names that represent the
            same concept under different names (template config) - if one
            is populated and others are null, the value is copied over.

    Returns:
        dict of {field_name: {"value": ..., "confidence": ...}} covering
        every entry in `allowed_fields`.
    """
    exact_aliases, normalized_aliases = build_field_alias_maps(allowed_fields, alias_overrides)
    fields: dict = {field: {"value": None} for field in allowed_fields}
    matched_keys: set[str] = set()

    # 1) Primary mapping: pre-resolved canonical_field
    for kv in key_value_pairs:
        canonical = (kv.get("canonical_field") or "").strip()
        if canonical not in allowed_fields:
            continue
        value = (kv.get("value") or "").strip()
        if not value:
            continue
        matched_keys.add((kv.get("key") or "").strip())
        current = fields.get(canonical)
        new_conf = round(float(kv.get("confidence", 0.0)), 4)
        if current.get("value") is None or new_conf > current.get("confidence", 0):
            fields[canonical] = {"value": value, "confidence": new_conf}

    # 2) Fallback mapping: alias resolution on the raw key
    for kv in key_value_pairs:
        raw_key = (kv.get("key") or "").strip()
        if not raw_key or raw_key in matched_keys:
            continue
        candidate = exact_aliases.get(raw_key.lower()) or normalized_aliases.get(normalize_key(raw_key))
        if candidate is None:
            continue
        value = (kv.get("value") or "").strip()
        if not value:
            continue
        matched_keys.add(raw_key)
        current = fields.get(candidate)
        new_conf = round(float(kv.get("confidence", 0.0)), 4)
        if current.get("value") is None or new_conf > current.get("confidence", 0):
            fields[candidate] = {"value": value, "confidence": new_conf}

    # 3) Optional injectable semantic fallback for remaining unmatched pairs
    if semantic_resolver is not None:
        unmatched_kvs = [
            {"key": (kv.get("key") or "").strip(), "value": (kv.get("value") or "").strip(),
             "confidence": kv.get("confidence", 0.0)}
            for kv in key_value_pairs
            if (kv.get("key") or "").strip() not in matched_keys and (kv.get("value") or "").strip()
        ]
        unfilled_fields = [f for f in allowed_fields if fields[f].get("value") is None]
        if unmatched_kvs and unfilled_fields:
            semantic_map = semantic_resolver(unmatched_kvs, unfilled_fields)
            kv_by_key = {(kv.get("key") or "").strip(): kv for kv in key_value_pairs}
            for orig_key, target_field in semantic_map.items():
                kv = kv_by_key.get(orig_key)
                if kv is None or not (kv.get("value") or "").strip():
                    continue
                if target_field in fields and fields[target_field].get("value") is None:
                    fields[target_field] = {
                        "value": kv["value"].strip(),
                        "confidence": round(float(kv.get("confidence", 0.0)) * 0.95, 4),
                        "semantic_mapped": True,
                    }

    # 4) Propagate values across equivalent field groups
    for group in equivalent_field_groups or []:
        present = [f for f in group if f in fields and fields[f].get("value") is not None]
        if not present:
            continue
        source = fields[present[0]]
        for f in group:
            if f in fields and fields[f].get("value") is None:
                fields[f] = {**source}

    # 5) Strip BiDi marks from every string value
    for field_data in fields.values():
        v = field_data.get("value")
        if isinstance(v, str):
            field_data["value"] = strip_bidi_marks(v)

    return fields


def apply_rule_based_normalization(
    fields: dict,
    date_fields: frozenset[str] = frozenset(),
    numeric_fields: frozenset[str] = frozenset(),
) -> dict:
    """Apply Arabic-numeral/date normalization to configured field sets, and
    Eastern-Arabic-digit conversion to every other string field.

    `date_fields` and `numeric_fields` are caller-supplied (template config) -
    with no arguments, this only performs the universal digit conversion.
    Modifies `fields` in-place and returns it.
    """
    for field_name in date_fields:
        entry = fields.get(field_name)
        if not entry or not entry.get("value"):
            continue
        raw_val = str(entry["value"])
        has_eastern = any("\u0660" <= ch <= "\u0669" for ch in raw_val)
        has_slashes = "/" in raw_val
        is_already_iso = bool(re.match(r"^\d{4}-\d{2}-\d{2}$", raw_val))
        if (has_eastern or has_slashes) and not is_already_iso:
            normalized_date = normalize_arabic_date(raw_val)
            if normalized_date and normalized_date != raw_val:
                entry["value"] = normalized_date

    for field_name in numeric_fields:
        entry = fields.get(field_name)
        if not entry or not entry.get("value"):
            continue
        raw_val = str(entry["value"])
        normalized_num = normalize_arabic_number(raw_val)
        if normalized_num and normalized_num != raw_val:
            entry["value"] = normalized_num

    for field_name, entry in fields.items():
        if field_name in date_fields or field_name in numeric_fields:
            continue
        v = entry.get("value")
        if isinstance(v, str):
            converted = convert_arabic_numerals(v)
            if converted != v:
                entry["value"] = converted

    return fields
