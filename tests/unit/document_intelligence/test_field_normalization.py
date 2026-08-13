"""
Unit tests for src/platform/document_intelligence/field_normalization.py.
"""

from src.platform.document_intelligence.field_normalization import (
    apply_rule_based_normalization,
    build_field_alias_maps,
    canonicalize_fields,
    compute_expiry_from_validity_period,
    convert_arabic_numerals,
    extract_country,
    normalize_arabic_date,
    normalize_arabic_number,
    normalize_currency,
    normalize_date,
    strip_bidi_marks,
    strip_trailing_date_suffix,
    unwrap_brackets,
)


class TestArabicNumeralConversion:
    def test_converts_eastern_arabic_digits(self):
        assert convert_arabic_numerals("١٢٣") == "123"

    def test_converts_decimal_and_thousands_marks(self):
        assert convert_arabic_numerals("١٬٢٣٤٫٥") == "1234.5"

    def test_empty_value_returns_unchanged(self):
        assert convert_arabic_numerals("") == ""


class TestNormalizeArabicNumber:
    def test_normalizes_eastern_arabic_digits(self):
        assert normalize_arabic_number("٢٥٫٨٩٤") == "25.894"

    def test_comma_as_thousands_separator(self):
        assert normalize_arabic_number("25,894") == "25894"

    def test_comma_as_decimal_separator(self):
        assert normalize_arabic_number("24,07") == "24.07"

    def test_no_digits_returns_none(self):
        assert normalize_arabic_number("abc") is None


class TestNormalizeArabicDate:
    def test_year_first_format(self):
        assert normalize_arabic_date("2024/03/15") == "2024-03-15"

    def test_day_first_format(self):
        assert normalize_arabic_date("15/03/2024") == "2024-03-15"

    def test_eastern_arabic_digits(self):
        assert normalize_arabic_date("٢٠٢٤/٠٣/١٥") == "2024-03-15"

    def test_unparseable_returns_none(self):
        assert normalize_arabic_date("not a date") is None


class TestNormalizeDate:
    def test_extracts_date_substring(self):
        assert normalize_date("Issued on 15/03/2024 at the office") == "15/03/2024"

    def test_no_date_returns_none(self):
        assert normalize_date("no date here") is None


class TestNormalizeCurrency:
    def test_explicit_code(self):
        assert normalize_currency("USD 1,234.56") == "USD"

    def test_dollar_sign_defaults_to_usd(self):
        assert normalize_currency("$500") == "USD"

    def test_euro_symbol(self):
        assert normalize_currency("€500") == "EUR"

    def test_custom_currency_codes_override(self):
        assert normalize_currency("XCD 500", currency_codes=frozenset({"XCD"})) == "XCD"

    def test_no_currency_found(self):
        assert normalize_currency("500 widgets") is None


class TestStringCleanup:
    def test_strip_trailing_date_suffix(self):
        assert strip_trailing_date_suffix("91993233/ 08.11.2024") == "91993233"

    def test_strip_trailing_date_suffix_no_match_unchanged(self):
        assert strip_trailing_date_suffix("91993233") == "91993233"

    def test_unwrap_parentheses(self):
        assert unwrap_brackets("(208563)") == "208563"

    def test_unwrap_square_brackets(self):
        assert unwrap_brackets("[208563]") == "208563"

    def test_no_brackets_unchanged(self):
        assert unwrap_brackets("208563") == "208563"


class TestExtractCountry:
    def test_extracts_known_country_suffix(self):
        assert extract_country("HYDERABAD, INDIA", known_countries=["India"]) == "India"

    def test_no_known_countries_returns_none(self):
        assert extract_country("HYDERABAD, INDIA", known_countries=[]) is None

    def test_no_match_returns_none(self):
        assert extract_country("Some address", known_countries=["India"]) is None


class TestStripBidiMarks:
    def test_strips_rtl_lrm_marks(self):
        assert strip_bidi_marks("\u200fHello\u200e") == "Hello"

    def test_no_marks_unchanged(self):
        assert strip_bidi_marks("Hello") == "Hello"


class TestComputeExpiryFromValidityPeriod:
    def test_computes_expiry_from_years(self):
        fields = {
            "issue_date": {"value": "2024-01-15", "confidence": 0.9},
            "validity_period": {"value": "2 years", "confidence": 0.8},
        }
        result = compute_expiry_from_validity_period(fields)
        assert result["expiry_date"]["value"] == "2026-01-15"

    def test_computes_expiry_from_months_with_clamping(self):
        fields = {
            "issue_date": {"value": "2024-01-31", "confidence": 0.9},
            "validity_period": {"value": "1 month", "confidence": 0.8},
        }
        result = compute_expiry_from_validity_period(fields)
        # Jan 31 + 1 month -> Feb 29 (2024 is a leap year), clamped.
        assert result["expiry_date"]["value"] == "2024-02-29"

    def test_already_present_expiry_untouched(self):
        fields = {
            "issue_date": {"value": "2024-01-15"},
            "validity_period": {"value": "2 years"},
            "expiry_date": {"value": "2099-01-01"},
        }
        result = compute_expiry_from_validity_period(fields)
        assert result["expiry_date"]["value"] == "2099-01-01"

    def test_no_issue_date_no_op(self):
        fields = {"validity_period": {"value": "2 years"}}
        result = compute_expiry_from_validity_period(fields)
        assert "expiry_date" not in result

    def test_custom_issue_date_fields_and_expiry_field(self):
        fields = {
            "license_issue_date": {"value": "2024-06-01", "confidence": 0.9},
            "validity_period": {"value": "6 months"},
        }
        result = compute_expiry_from_validity_period(
            fields, issue_date_fields=("license_issue_date",), expiry_field="license_expiry_date",
        )
        assert result["license_expiry_date"]["value"] == "2024-12-01"


class TestBuildFieldAliasMaps:
    def test_field_name_itself_is_an_alias(self):
        exact, _ = build_field_alias_maps(["net_weight"])
        assert exact["net_weight"] == "net_weight"

    def test_underscore_to_space_variant(self):
        exact, _ = build_field_alias_maps(["net_weight"])
        assert exact["net weight"] == "net_weight"

    def test_alias_overrides_applied(self):
        exact, _ = build_field_alias_maps(["net_weight"], alias_overrides={"net_weight": ["poids net"]})
        assert exact["poids net"] == "net_weight"

    def test_more_specific_field_wins_shared_alias(self):
        exact, _ = build_field_alias_maps(
            ["net_weight", "net_weight_total"],
            alias_overrides={
                "net_weight": ["weight"],
                "net_weight_total": ["weight"],
            },
        )
        assert exact["weight"] == "net_weight_total"


class TestCanonicalizeFields:
    def test_maps_via_pre_resolved_canonical_field(self):
        kvs = [{"key": "Net Wt", "value": "100", "confidence": 0.9, "canonical_field": "net_weight"}]
        result = canonicalize_fields(kvs, allowed_fields=["net_weight"])
        assert result["net_weight"]["value"] == "100"

    def test_maps_via_alias_fallback(self):
        kvs = [{"key": "Net Wt", "value": "100", "confidence": 0.9, "canonical_field": None}]
        result = canonicalize_fields(
            kvs, allowed_fields=["net_weight"], alias_overrides={"net_weight": ["net wt"]},
        )
        assert result["net_weight"]["value"] == "100"

    def test_unmatched_fields_default_to_none(self):
        result = canonicalize_fields([], allowed_fields=["net_weight", "gross_weight"])
        assert result == {"net_weight": {"value": None}, "gross_weight": {"value": None}}

    def test_semantic_resolver_used_for_unmatched(self):
        kvs = [{"key": "Unusual Label", "value": "42", "confidence": 0.7, "canonical_field": None}]

        def resolver(unmatched_kvs, unfilled_fields):
            return {"Unusual Label": "net_weight"}

        result = canonicalize_fields(
            kvs, allowed_fields=["net_weight"], semantic_resolver=resolver,
        )
        assert result["net_weight"]["value"] == "42"
        assert result["net_weight"]["semantic_mapped"] is True

    def test_equivalent_field_group_propagation(self):
        kvs = [{"key": "expiry_date", "value": "2025-01-01", "confidence": 0.9, "canonical_field": "expiry_date"}]
        result = canonicalize_fields(
            kvs,
            allowed_fields=["expiry_date", "expiration_date"],
            equivalent_field_groups=[("expiry_date", "expiration_date")],
        )
        assert result["expiration_date"]["value"] == "2025-01-01"

    def test_bidi_marks_stripped_from_values(self):
        kvs = [{"key": "field", "value": "\u200fHello\u200e", "confidence": 0.9, "canonical_field": "field"}]
        result = canonicalize_fields(kvs, allowed_fields=["field"])
        assert result["field"]["value"] == "Hello"


class TestApplyRuleBasedNormalization:
    def test_date_field_normalized(self):
        fields = {"issue_date": {"value": "٢٠٢٤/٠٣/١٥"}}
        result = apply_rule_based_normalization(fields, date_fields=frozenset({"issue_date"}))
        assert result["issue_date"]["value"] == "2024-03-15"

    def test_numeric_field_normalized(self):
        fields = {"net_weight": {"value": "٢٥٫٨"}}
        result = apply_rule_based_normalization(fields, numeric_fields=frozenset({"net_weight"}))
        assert result["net_weight"]["value"] == "25.8"

    def test_other_fields_get_digit_conversion_only(self):
        fields = {"notes": {"value": "ref ١٢٣"}}
        result = apply_rule_based_normalization(fields)
        assert result["notes"]["value"] == "ref 123"

    def test_no_config_is_safe_no_op_for_unlisted_fields(self):
        fields = {"description": {"value": "plain text"}}
        result = apply_rule_based_normalization(fields)
        assert result["description"]["value"] == "plain text"
