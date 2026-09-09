"""
Integration test: same rule evaluation produces identical findings on the reference case.

Loads templates/food-safety/rules.json and runs run_rules() against a self-contained
reference payload with a minimal submission (documents present but empty fields).
Verifies the deterministic findings match expected values.

This is the acceptance criterion: "Same rule evaluation produces identical findings
on the reference case."
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.platform.orchestration.pipeline import DEFAULT_ACTIVITY_NAMES, run_pipeline
from src.platform.policy.rule_executor import run_rules
from src.platform.policy.rules_policy import run as run_policy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WORKSPACE = Path(__file__).resolve().parent.parent.parent
RULES_JSON = WORKSPACE / "templates" / "food-safety" / "rules.json"

EXPECTED_FINDING_PROJECTION = [
    ("AGENCY_CODE_MISSING", "FAIL", None, None, None),
    ("CROSS_COUNTRY_OF_ORIGIN", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_EXPORTER_NAME", "NOT_APPLICABLE", None, None, None),
    ("CROSS_GROSS_WEIGHT", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_HS_CODE", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_IMPORTER_NAME", "NOT_APPLICABLE", None, None, None),
    ("CROSS_INVOICE_DATE", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_INVOICE_NUMBER", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_ITEM_DESCRIPTION", "NOT_APPLICABLE", None, None, None),
    ("CROSS_NET_WEIGHT", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_PACKAGING", "NOT_APPLICABLE", None, None, None),
    ("CROSS_PORT_OF_DISCHARGE", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_PORT_OF_LOADING", "NOT_APPLICABLE", None, None, "Warning"),
    ("CROSS_QUANTITY", "NOT_APPLICABLE", None, None, "Warning"),
    ("MANDATORY_DOC_MISSING", "FAIL", "Commercial_License", None, None),
    ("MANDATORY_DOC_MISSING", "FAIL", "Delivery_Orders", None, None),
    ("MANDATORY_DOC_MISSING", "FAIL", "Halal_Slaughter_Certificate", None, None),
    ("MANDATORY_DOC_MISSING", "FAIL", "House_Bill", None, None),
    ("MANDATORY_DOC_MISSING", "FAIL", "Import_License", None, None),
    ("MANDATORY_DOC_MISSING", "FAIL", "Packing_List or Stretching_List", None, None),
    ("MANDATORY_DOC_MISSING", "FAIL", "Signature_Authorization", None, None),
    ("MIN_FIELDS_RULES", "WARN", None, None, "Warning"),
    ("MIN_FIELDS_RULES", "WARN", None, None, "Warning"),
    ("MIN_FIELDS_RULES", "WARN", None, None, "Warning"),
    ("MIN_FIELDS_RULES", "WARN", None, None, "Warning"),
    ("MIN_FIELDS_RULES", "WARN", None, None, "Warning"),
    ("SIGNATURE_STAMP_MISSING", "WARN", None, None, "Warning"),
    ("SIGNATURE_STAMP_NOT_DETECTED", "NOT_APPLICABLE", None, None, "Info"),
]


@pytest.fixture(scope="module")
def food_safety_rules() -> list:
    with open(RULES_JSON, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def reference_payload() -> dict:
    return {
        "requestId": "REFERENCE-CHICKEN-001",
        "declarationNumber": "TIM/1234/SHU25",
        "items": [
            {
                "itemCode": "CHICKEN-001",
                "itemType": "Frozen chicken",
                "serial": 1,
                "hsCode": "1602.90.10.00.00",
                "expiryDate": "2027-02-04",
            },
            {
                "itemCode": "CHICKEN-002",
                "itemType": "Frozen chicken",
                "serial": 2,
                "hsCode": "1602.90.10.00.00",
                "expiryDate": "2027-02-07",
            },
        ],
        "documents": [
            {"documentTypeId": "20", "documentType": "Declaration_Document"},
            {"documentTypeId": "40", "documentType": "Health_License"},
            {"documentTypeId": "27", "documentType": "Health_Certificate_Country_of_Origin"},
            {"documentTypeId": "50", "documentType": "Invoice"},
            {"documentTypeId": "51", "documentType": "Certificate_Of_Origin"},
        ],
    }


def _minimal_submission(payload: dict) -> list:
    """Build a submission with all declared documents but empty fields."""
    return [
        {
            "documentTypeId": doc["documentTypeId"],
            "document": doc["documentType"],
            "fields": {},
            "lineItems": [],
        }
        for doc in payload.get("documents", [])
    ]


def _run_rules_sync(rules_list, payload, submission) -> list:
    return asyncio.run(run_rules(rules_list=rules_list, payload=payload, submission=submission))


class _PipelineContext:
    def __init__(self, payload: dict):
        self.payload = payload
        self.is_replaying = False
        self.current_utc_datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)
        self.calls: list[tuple[str, dict]] = []

    def get_input(self) -> dict:
        return self.payload

    def call_activity_with_retry(self, name: str, retry_policy, input: dict):
        self.calls.append((name, input))
        return object()


def _drive_pipeline(generator, results: list[dict]) -> None:
    next(generator)
    for result in results:
        try:
            generator.send(result)
        except StopIteration:
            return


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRulesJsonLoads:
    def test_rules_json_is_valid_list(self, food_safety_rules):
        assert isinstance(food_safety_rules, list)
        assert len(food_safety_rules) > 0

    def test_all_required_rule_ids_present(self, food_safety_rules):
        rule_ids = {r["id"] for r in food_safety_rules}
        expected = {
            "AGENCY_CODE_RULES",
            "MANDATORY_DOC_RULES",
            "MIN_FIELDS_RULES",
            "REJECTED_HS_CODES",
            "FOOD_SAFETY_HS_CODES",
            "HALAL_HS_CODES",
            "FISH_HS_CODES",
            "SHRIMP_HS_CODES",
            "SIGNATURE_STAMP_RULES",
            "CROSS_DOC_RULES",
            "LOGICAL_RULES",
        }
        missing = expected - rule_ids
        assert not missing, f"Missing rule IDs in rules.json: {missing}"

    def test_agency_code_rules_has_agency_code(self, food_safety_rules):
        rule = next(r for r in food_safety_rules if r["id"] == "AGENCY_CODE_RULES")
        assert rule["agencyCode"] == "2"


class TestReferenceCase:
    """Reference case: 2-item frozen chicken shipment with 5 documents.

    Expected deterministic findings:
    - AGENCY_CODE_MISSING: Declaration_Document has no agency_code field (empty fields)
    - MANDATORY_DOC_MISSING: Many mandatory docs are missing from the 5-doc submission
    - HS code 1602.90.10.00.00 should be in the in-scope codes (chapter 16) → no jurisdiction rejection
    - No REJECTED_HS_CODE for chapter 16
    - FOOD_NOT_EXPIRED: items have future expiry dates → should PASS or WARN (no FAIL)
    """

    def test_run_rules_returns_list(self, food_safety_rules, reference_payload):
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        assert isinstance(findings, list)

    def test_complete_finding_projection_matches_baseline(
        self, food_safety_rules, reference_payload
    ):
        findings = _run_rules_sync(
            food_safety_rules,
            reference_payload,
            _minimal_submission(reference_payload),
        )
        projection = sorted(
            (
                finding.get("ruleCode"),
                finding.get("result"),
                finding.get("documentType"),
                finding.get("itemCode"),
                finding.get("severity"),
            )
            for finding in findings
        )

        assert projection == EXPECTED_FINDING_PROJECTION

    def test_mandatory_docs_missing(self, food_safety_rules, reference_payload):
        """Reference payload has only 5 docs; mandatory list requires ~10."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        mandatory_missing = [f for f in findings if f.get("ruleCode") == "MANDATORY_DOC_MISSING"]
        # At minimum, docs like House_Bill, Delivery_Orders, Packing_List etc. are missing
        assert len(mandatory_missing) > 0, "Expected MANDATORY_DOC_MISSING findings for absent docs"

    def test_chicken_hs_code_not_rejected(self, food_safety_rules, reference_payload):
        """HS code 1602.90.10.00.00 (processed chicken) should not be in the rejected list."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        rejected = [f for f in findings if f.get("ruleCode") == "REJECTED_HS_CODE"]
        assert rejected == [], f"Unexpected REJECTED_HS_CODE findings: {rejected}"

    def test_chicken_hs_code_is_within_jurisdiction(self, food_safety_rules, reference_payload):
        """HS code 1602.x should match the in-scope chapter 16 prefix → no NON_FOOD_SAFETY_HS_CODE."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        out_of_scope = [f for f in findings if f.get("ruleCode") == "NON_FOOD_SAFETY_HS_CODE"]
        assert out_of_scope == [], f"Unexpected NON_FOOD_SAFETY_HS_CODE findings: {out_of_scope}"

    def test_food_items_have_future_expiry_dates(self, food_safety_rules, reference_payload):
        """Reference payload has future expiry dates → FOOD_NOT_EXPIRED should not FAIL."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        food_fail = [f for f in findings if f.get("ruleCode") == "FOOD_NOT_EXPIRED" and f.get("result") == "FAIL"]
        # Items have expiryDate 2027-02-04 and 2027-02-07 — should not be expired
        assert food_fail == [], f"Unexpected FOOD_NOT_EXPIRED FAIL findings: {food_fail}"

    def test_all_findings_have_rule_code(self, food_safety_rules, reference_payload):
        """Post-normalization: every finding must have ruleCode."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        missing_code = [f for f in findings if not f.get("ruleCode")]
        assert missing_code == [], f"Findings without ruleCode: {missing_code}"

    def test_all_findings_have_result(self, food_safety_rules, reference_payload):
        """Every finding must have a result field."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        missing_result = [f for f in findings if not f.get("result")]
        assert missing_result == [], f"Findings without result: {missing_result}"

    def test_halal_cert_required_for_chicken(self, food_safety_rules, reference_payload):
        """HS code 1602.90.10 matches HALAL_HS_CODES chapter 16 → Halal cert required."""
        submission = _minimal_submission(reference_payload)
        findings = _run_rules_sync(food_safety_rules, reference_payload, submission)
        halal_missing = [
            f for f in findings
            if f.get("ruleCode") == "MANDATORY_DOC_MISSING"
            and "Halal" in f.get("documentType", "")
        ]
        assert len(halal_missing) > 0, (
            "Expected MANDATORY_DOC_MISSING for Halal_Slaughter_Certificate "
            "given HS code 1602.90.10.00.00 matches HALAL_HS_CODES"
        )

    def test_generic_five_stage_pipeline_preserves_reference_findings(
        self, food_safety_rules, reference_payload
    ):
        extracted_fields = {
            document["documentTypeId"]: {
                "documentType": document["documentType"],
                "fields": {},
                "lineItems": [],
            }
            for document in reference_payload["documents"]
        }
        direct_findings = _run_rules_sync(
            food_safety_rules,
            reference_payload,
            _minimal_submission(reference_payload),
        )
        policy_result = asyncio.run(
            run_policy(reference_payload, extracted_fields, food_safety_rules)
        )
        context = _PipelineContext(reference_payload)

        _drive_pipeline(
            run_pipeline(context, retry_policy=object()),
            [
                {"passed": True, "errors": [], "warnings": [], "documents": None},
                {"success": True, "extractedFields": extracted_fields},
                {
                    "success": True,
                    "evidenceMap": extracted_fields,
                    "findings": [],
                    "documentChecks": [],
                },
                policy_result,
                {},
            ],
        )

        assert [name for name, _input in context.calls] == list(
            DEFAULT_ACTIVITY_NAMES.values()
        )
        assert context.calls[-1][1]["findings"] == direct_findings
        assert context.calls[-1][1]["recommendation"] == policy_result["recommendation"]
        assert all(
            domain_name not in " ".join(DEFAULT_ACTIVITY_NAMES.values()).lower()
            for domain_name in ("food", "halal", "customs")
        )
