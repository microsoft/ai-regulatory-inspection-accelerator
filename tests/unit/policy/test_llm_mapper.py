"""Tests for template-injected country normalization."""

from src.platform.policy.evaluators.llm_mapper import normalize_country


def test_country_aliases_are_injected_by_the_template():
    assert normalize_country("الكويت") == "الكويت"
    assert normalize_country("الكويت", {"الكويت": "KW"}) == "KW"
    assert normalize_country("UAE", {"UAE": "AE"}) == "AE"


def test_iso_country_lookup_remains_domain_neutral():
    assert normalize_country("USA") == "US"
    assert normalize_country("GBR") == "GB"