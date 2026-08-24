"""
Mandatory Fields Rule Logic

Ported from PAFN's rules_engine/mandatory_documents.py.
GCC_COUNTRIES stays hardcoded — it is a PAFN/Kuwait-specific constant that
is not a template config concern per the accepted scope decision.
"""

import re

from src.platform.policy.evaluators import llm_mapper


def _norm(s: str) -> str:
    """Lowercase alphanumeric only — bridges casing and separator differences."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


GCC_COUNTRIES = ("SA", "AE", "KW", "QA", "BH", "OM")


def _normalize_hs(hs_code: str) -> str:
    normalized = hs_code.strip().replace(".", "").rstrip("0")
    return normalized if normalized else "0"


def _get_hs_prefixes(rules: list, rule_id: str) -> tuple:
    """Fetch and normalize HS code prefixes from a rule document by ID."""
    rule = next((r for r in rules if r.get("id") == rule_id), None)
    if rule is None:
        return ()
    return tuple(_normalize_hs(c) for c in rule.get("hsCodes", []) if c)


def validate_mandatory_docs(rules, payload, submission):
    """Validate mandatory document presence and normalize submission document names.

    Returns:
        (findings, normalized_submission)
    """
    findings = []
    rule = next(r for r in rules if r["id"] == "MANDATORY_DOC_RULES")

    halal_codes   = _get_hs_prefixes(rules, "HALAL_HS_CODES")
    fish_codes    = _get_hs_prefixes(rules, "FISH_HS_CODES")
    shrimp_codes  = _get_hs_prefixes(rules, "SHRIMP_HS_CODES")
    zubaidi_codes = _get_hs_prefixes(rules, "ZUBAIDI_HS_CODES")
    fresh_codes   = _get_hs_prefixes(rules, "FRESH_HS_CODES")

    # Name normalization: payload is authoritative
    payload_id_to_type = {
        d["documentTypeId"]: d["documentType"]
        for d in payload.get("documents", [])
    }

    normalized_submission = []
    for doc in submission:
        doc_id = doc.get("documentTypeId")
        payload_name = payload_id_to_type.get(doc_id)
        if payload_name and payload_name != doc.get("document"):
            doc = {**doc, "document": payload_name}
        normalized_submission.append(doc)

    payload_type_ids = {
        str(d["documentTypeId"])
        for d in payload.get("documents", [])
        if d.get("documentTypeId") is not None
    }
    submitted_doc_types = {d["document"] for d in normalized_submission}
    submitted_doc_types_norm = {_norm(t) for t in submitted_doc_types}

    def _entry_id(entry) -> str:
        return str(entry.get("documentTypeId", "")) if isinstance(entry, dict) else ""

    def _entry_type(entry) -> str:
        return entry["documentType"] if isinstance(entry, dict) else entry

    bayan_number = payload.get("bayanNumber", "") or ""
    is_personal = bayan_number.upper().startswith("TDR")

    if is_personal:
        for req_id, req_type in (("42", "Declaration_Document"), ("43", "Other_Documents")):
            if req_id not in payload_type_ids:
                findings.append({
                    "ruleCode": "MANDATORY_DOC_MISSING",
                    "result": "FAIL",
                    "message": f"{req_type.replace('_', ' ')} was not uploaded. Request this document from the importer before proceeding.",
                    "documentType": req_type,
                })
    else:
        for doc_req in rule["mandatoryDocuments"]:
            if isinstance(doc_req, str):
                if _norm(doc_req) not in submitted_doc_types_norm:
                    findings.append({
                        "ruleCode": "MANDATORY_DOC_MISSING",
                        "result": "FAIL",
                        "message": f"{doc_req.replace('_', ' ')} was not uploaded.",
                        "documentType": doc_req,
                    })
            elif isinstance(doc_req, dict):
                req_id = _entry_id(doc_req)
                req_type = _entry_type(doc_req)
                if req_id not in payload_type_ids:
                    findings.append({
                        "ruleCode": "MANDATORY_DOC_MISSING",
                        "result": "FAIL",
                        "message": f"{req_type.replace('_', ' ')} was not uploaded.",
                        "documentType": req_type,
                    })
            elif isinstance(doc_req, list):
                def _or_present(opt) -> bool:
                    if isinstance(opt, str):
                        return _norm(opt) in submitted_doc_types_norm
                    if isinstance(opt, dict):
                        eid = _entry_id(opt)
                        return bool(eid) and eid in payload_type_ids
                    return False

                valid_opts = [opt for opt in doc_req if isinstance(opt, (str, dict))]
                if not valid_opts:
                    continue
                if not any(_or_present(opt) for opt in valid_opts):
                    readable_types = " or ".join(_entry_type(opt).replace("_", " ") for opt in valid_opts)
                    findings.append({
                        "ruleCode": "MANDATORY_DOC_MISSING",
                        "result": "FAIL",
                        "message": f"One of the following must be uploaded: {readable_types}.",
                        "documentType": " or ".join(_entry_type(opt) for opt in valid_opts),
                    })

        _CONDITIONAL_CHECKS = [
            ("Halal_Slaughter_Certificate", lambda hs: bool(halal_codes) and _normalize_hs(hs).startswith(halal_codes)),
            ("Fish_Import_License",         lambda hs: bool(fish_codes) and _normalize_hs(hs).startswith(fish_codes)),
            ("Shrimp_Import_License",       lambda hs: bool(shrimp_codes) and _normalize_hs(hs).startswith(shrimp_codes)),
            ("Zubaidi_Import_License",      lambda hs: bool(zubaidi_codes) and _normalize_hs(hs).startswith(zubaidi_codes)),
            ("Invoice",                     lambda hs: bool(fresh_codes) and _normalize_hs(hs).startswith(fresh_codes)),
            ("Statistical_Declaration",     lambda country: country.strip() in GCC_COUNTRIES),
        ]

        cond_type_to_id: dict[str, str] = {}
        for entry in rule.get("conditionalDocuments", []):
            if isinstance(entry, dict):
                cond_type_to_id[_entry_type(entry)] = _entry_id(entry)
            elif isinstance(entry, list):
                for opt in entry:
                    if isinstance(opt, dict):
                        cond_type_to_id[_entry_type(opt)] = _entry_id(opt)

        conditionally_required: set = set()
        for item in payload.get("items", []):
            hs_code = str(item.get("hsCode", ""))
            country = llm_mapper.normalize_country(str(item.get("countryOfOrigin", "")))
            for doc_type, check_fn in _CONDITIONAL_CHECKS:
                value = country if doc_type == "Statistical_Declaration" else hs_code
                if value and check_fn(value):
                    conditionally_required.add(doc_type)

        for doc_type in conditionally_required:
            req_id = cond_type_to_id.get(doc_type, "")
            if (req_id and req_id in payload_type_ids) or (
                not req_id and _norm(doc_type) in submitted_doc_types_norm
            ):
                continue
            findings.append({
                "ruleCode": "MANDATORY_DOC_MISSING",
                "result": "FAIL",
                "message": (
                    f"{doc_type.replace('_', ' ')} was not uploaded. This document is required for this shipment's country of origin."
                ),
                "documentType": doc_type,
            })

    return findings, normalized_submission
