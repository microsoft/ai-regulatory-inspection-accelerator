---
title: Arabic-English Evaluation Standard
description: Evaluation protocol for reliable Arabic-English document extraction in ARIA
author: ARIA Engineering
ms.date: 2026-08-24
ms.topic: reference
keywords:
  - Arabic
  - English
  - evaluation
  - dialect
  - transliteration
  - document intelligence
estimated_reading_time: 6
---

## Scope

ARIA targets verified Arabic-English bilingual document extraction. Model support
for additional languages does not constitute application support until those
languages have their own reviewed corpus and measured results.

The challenge set at
`tests/evaluation/arabic_english_challenge_set.json` covers:

* Modern Standard Arabic
* Gulf Arabic, including Kuwait-relevant wording
* Selected Egyptian, Levantine, and Maghrebi contrast cases
* Arabizi and phonetic transliteration
* Arabic-English code-switching
* Mixed right-to-left and left-to-right text
* Ambiguous inputs where the correct behavior is abstention

The examples are synthetic. No text from a copyrighted book or commercial
dataset is reproduced.

## Quality policy

Zero failure cannot be inferred from a finite corpus. The enforceable safety
target is zero critical errors on the approved evaluation set. A critical error
is any fabricated value, unsupported translation, corruption of an identifier,
or high-confidence interpretation of ambiguous source text.

Every release evaluation must report results by category rather than only as an
aggregate score. Use these measures:

* Canonical-field exact-match accuracy
* Normalized-value exact-match accuracy
* Source-value preservation rate
* Correct abstention rate
* Critical-error count
* Accuracy by dialect and writing-system category

A release fails when the critical-error count is nonzero. Other thresholds must
be set from an approved baseline and raised through measured model improvements.

## Review requirements

Two independent native Arabic reviewers must approve each corpus version. At
least one reviewer must understand Gulf Arabic. Reviewers verify meaning,
naturalness, regional attribution, spelling, and the expected preserve,
normalize, or abstain behavior.

Dialect examples are contrast tests, not a complete representation of all
speakers or regions. Add real failure cases only after removing personal,
commercial, and regulatory-sensitive information.

## Evaluation procedure

1. Pin the Document Intelligence and language-model versions.
2. Run every case with deterministic settings where the provider supports them.
3. Record the extracted canonical field, value, confidence, and model version.
4. Compare output with the expected action and value.
5. Have reviewers inspect every mismatch and every high-confidence output on an
   abstention case.
6. Publish category-level results and the critical-error count.
7. Add minimized regression cases for confirmed production failures.

The pytest contract verifies corpus structure and coverage. It does not claim
model quality. Model quality is established only by running the pinned model
against the reviewed corpus.

## Authoritative references

Use standards as orthographic and encoding references. Do not treat them as a
substitute for native-speaker review of dialect or domain meaning.

* [Unicode Standard, Chapter 9: Middle Eastern Scripts](https://www.unicode.org/versions/latest/core-spec/chapter-9/)
* [Unicode Standard Annex 9: Bidirectional Algorithm](https://www.unicode.org/reports/tr9/)
* [Unicode CLDR Arabic locale data](https://cldr.unicode.org/)
* [Library of Congress Arabic romanization table](https://www.loc.gov/catdir/cpso/romanization/arabic.pdf)

The Library of Congress table provides a recognized romanization reference.
Arabizi and regional slang are living language practices, so they require
reviewed empirical cases rather than a single official book.