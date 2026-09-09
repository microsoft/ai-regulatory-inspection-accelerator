"""Token-reduction benchmark for representative DI Markdown."""

from src.platform.document_intelligence.content_normalization import normalize_markdown


def _representative_di_markdown() -> str:
    pages = []
    for page_number in range(1, 6):
        pages.append(
            "\n".join(
                [
                    "PUBLIC AUTHORITY FOR FOOD AND NUTRITION",
                    "Import Inspection Submission - Confidential",
                    f"Page {page_number} of 5",
                    "",
                    "",
                    ":selected: Verified by issuing authority",
                    ":unselected: Manual correction required",
                    "",
                    "## Shipment Evidence",
                    f"Document reference: REF-{page_number:03d}",
                    "Importer: Example Trading Company",
                    "Country of origin: Brazil",
                    "Net weight: 1250 kg",
                    "",
                    "---",
                    "",
                    "---",
                    "PUBLIC AUTHORITY FOR FOOD AND NUTRITION",
                    "Import Inspection Submission - Confidential",
                ]
            )
        )
    return "\n<!-- PageBreak -->\n".join(pages)


def test_representative_di_markdown_reduces_tokens_by_at_least_twenty_percent():
    normalized, report = normalize_markdown(_representative_di_markdown())

    assert report.token_reduction_ratio >= 0.20
    assert "Document reference: REF-001" in normalized
    assert "Net weight: 1250 kg" in normalized
    assert "PUBLIC AUTHORITY FOR FOOD AND NUTRITION" not in normalized