"""
Pure data helpers for the Rules Engine.

Ported from PAFN's rules_engine/llm_mapper.py.
Changes from PAFN: removed shared.telemetry dependency.
All content (country maps, document name map) is domain-neutral algorithm data.
"""

import re as _re

import pycountry

_ARABIC_COUNTRY_MAP: dict[str, str] = {
    "الإمارات": "AE",
    "الإمارات العربية المتحدة": "AE",
    "امارات": "AE",
    "السعودية": "SA",
    "المملكة العربية السعودية": "SA",
    "الكويت": "KW",
    "البحرين": "BH",
    "عمان": "OM",
    "قطر": "QA",
    "العراق": "IQ",
    "مصر": "EG",
    "الأردن": "JO",
    "لبنان": "LB",
    "سوريا": "SY",
    "اليمن": "YE",
    "تركيا": "TR",
    "الهند": "IN",
    "الصين": "CN",
    "برازيل": "BR",
    "ألمانيا": "DE",
    "فرنسا": "FR",
    "إيطاليا": "IT",
    "أستراليا": "AU",
    "باكستان": "PK",
    "إيران": "IR",
    "تايلاند": "TH",
    "أمريكا": "US",
}

_ENGLISH_ALIAS_MAP: dict[str, str] = {
    "UAE": "AE",
    "KSA": "SA",
    "USA": "US",
    "UK": "GB",
}

DOCUMENT_NAME_MAP = {
    "HouseBill": "House_Bill",
    "DeliveryOrders": "Delivery_Orders",
    "PackingList": "Packing_List",
    "StretchingList": "Stretching_List",
    "Invoice": "Invoice",
    "CertificateOfOrigin": "Certificate_Of_Origin",
    "IssuingCountryOfOriginCertificate": "Issuing_Country_Of_Origin_Certificate",
    "HealthCertificateFromCountryOfOrigin": "Health_Certificate_from_Country_of_Origin",
    "HealthLicense": "Health_License",
    "HalalSlaughterCertificate": "Halal_Slaughter_Certificate",
    "StatisticalDeclarationGCC": "Statistical_Declaration",
    "GCCDeclaration": "GCC_Declaration",
    "CommercialLicense": "Commercial_License",
    "ImportLicense": "Import_License",
    "SignatureAuthorization": "Signature_Authorization",
    "FishImportLicense": "Fish_Import_License",
    "ShrimpImportLicense": "Shrimp_Import_License",
    "ZubaidiImportLicense": "Zubaidi_Import_License",
}


def normalize_country(value: str) -> str:
    """Resolve a country value to a canonical ISO alpha-2 code."""
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
    if upper in _ENGLISH_ALIAS_MAP:
        return _ENGLISH_ALIAS_MAP[upper]
    for arabic_name, code in _ARABIC_COUNTRY_MAP.items():
        if arabic_name in stripped:
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
        if tok_upper in _ENGLISH_ALIAS_MAP:
            return _ENGLISH_ALIAS_MAP[tok_upper]
    try:
        results = pycountry.countries.search_fuzzy(stripped)
        if results:
            return results[0].alpha_2
    except LookupError:
        pass
    return stripped.lower()


def resolve_document_name(rule_doc_name) -> str:
    """Map a rule-side document name (PascalCase) to its submission-side equivalent."""
    if not isinstance(rule_doc_name, str):
        return str(rule_doc_name)
    return DOCUMENT_NAME_MAP.get(rule_doc_name, rule_doc_name)


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


def build_comparison_tasks(cross_doc_rules: list, doc_field_index: dict, field_resolution: dict) -> list:
    """Build a list of comparison tasks for fuzzy/semantic LLM checks."""
    tasks = []
    for rule in cross_doc_rules:
        if rule.get("comparisonType") not in ("fuzzyMatch", "semanticMatch"):
            continue
        doc_values = {}
        for rule_doc_name in rule.get("documents", []):
            sub_doc_name = resolve_document_name(rule_doc_name)
            fields = doc_field_index.get(sub_doc_name, {})
            value = get_field_value(fields, rule["field"], field_resolution, sub_doc_name)
            if value:
                doc_values[sub_doc_name] = value
        if len(doc_values) >= 2:
            tasks.append({
                "ruleId": rule["ruleId"],
                "field": rule["field"],
                "comparisonType": rule["comparisonType"],
                "threshold": rule.get("threshold", 0.85),
                "severity": rule.get("severity", "Warning"),
                "description": rule.get("description", ""),
                "docValues": doc_values,
            })
    return tasks
