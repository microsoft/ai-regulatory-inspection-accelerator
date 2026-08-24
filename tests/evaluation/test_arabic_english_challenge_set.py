"""Contract tests for the Arabic-English extraction challenge set."""

import json
from pathlib import Path

CORPUS_PATH = Path(__file__).with_name("arabic_english_challenge_set.json")
REQUIRED_CATEGORIES = {
    "modern_standard_arabic",
    "gulf_dialect",
    "regional_dialect",
    "arabizi",
    "ambiguity_abstention",
    "code_switching",
    "mixed_direction_text",
    "phonetic_transliteration",
}
VALID_ACTIONS = {"normalize", "preserve", "abstain"}


def _load_corpus() -> dict:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_corpus_has_required_language_slices():
    corpus = _load_corpus()
    categories = {case["category"] for case in corpus["cases"]}

    assert corpus["primary_languages"] == ["ar", "en"]
    assert REQUIRED_CATEGORIES <= categories


def test_cases_have_unique_ids_and_complete_expectations():
    cases = _load_corpus()["cases"]
    case_ids = [case["id"] for case in cases]

    assert len(case_ids) == len(set(case_ids))
    for case in cases:
        assert case["input"]["key"]
        assert case["input"]["value"]
        assert case["expectation"]["action"] in VALID_ACTIONS
        assert "canonical_field" in case["expectation"]
        assert case["expectation"]["value"]


def test_preservation_and_abstention_cases_do_not_rewrite_source_values():
    cases = _load_corpus()["cases"]

    for case in cases:
        expectation = case["expectation"]
        if expectation["action"] in {"preserve", "abstain"}:
            assert expectation["value"] == case["input"]["value"]
        if expectation["action"] == "abstain":
            assert expectation["canonical_field"] is None


def test_corpus_requires_independent_native_speaker_review():
    review = _load_corpus()["native_speaker_review"]

    assert review["required_reviewers"] >= 2
    assert "Modern Standard Arabic" in review["required_varieties"]
    assert "Gulf Arabic" in review["required_varieties"]
    assert review["status"] in {"pending", "approved", "changes_requested"}