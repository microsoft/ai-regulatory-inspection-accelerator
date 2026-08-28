"""
Mandatory Fields Rule Logic

Ported from PAFN's rules_engine/mandatory_documents.py. Personal-shipment and
conditional-document criteria are supplied by template rule configuration.
"""

import re

from src.platform.policy.evaluators import llm_mapper


def _norm(s: str) -> str:
    """Lowercase alphanumeric only — bridges casing and separator differences."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


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
    personal_config = rule.get("personalShipment", {})
    personal_prefixes = tuple(
        prefix.upper() for prefix in personal_config.get("declarationPrefixes", [])
    )
    is_personal = bool(personal_prefixes) and bayan_number.upper().startswith(
        personal_prefixes
    )

    if is_personal:
        for requirement in personal_config.get("requiredDocuments", []):
            req_id = _entry_id(requirement)
            req_type = _entry_type(requirement)
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
            for requirement in rule.get("conditionalRequirements", []):
                doc_type = requirement.get("documentType", "")
                hs_rule_id = requirement.get("hsCodeRuleId")
                hs_prefixes = _get_hs_prefixes(rules, hs_rule_id) if hs_rule_id else ()
                origin_countries = requirement.get("originCountries", [])
                hs_matches = bool(hs_prefixes) and _normalize_hs(hs_code).startswith(
                    hs_prefixes
                )
                country_matches = bool(origin_countries) and country in origin_countries
                if doc_type and (hs_matches or country_matches):
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
