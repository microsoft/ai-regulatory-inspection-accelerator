"""Tests for lightweight Office document normalization."""

from io import BytesIO
from zipfile import ZipFile

import pytest

from src.platform.intake.office_normalization import (
    EXCEL_MIME,
    MAX_XML_BYTES,
    POWERPOINT_MIME,
    WORD_MIME,
    normalize_office_document,
)


def test_docx_text_is_normalized_to_markdown_paragraphs():
    document_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Inspection summary</w:t></w:r></w:p>
    <w:p><w:r><w:t>Evidence verified</w:t></w:r></w:p>
  </w:body>
</w:document>"""
    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    markdown = normalize_office_document(package.getvalue(), WORD_MIME)

    assert markdown == "Inspection summary\n\nEvidence verified\n"


def test_xlsx_cells_are_normalized_to_markdown_rows():
    worksheet_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData><row><c><v>Item</v></c><c><v>42</v></c></row></sheetData>
</worksheet>"""
    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    markdown = normalize_office_document(package.getvalue(), EXCEL_MIME)

    assert markdown == "## Sheet 1\n\nItem | 42\n"


def test_xlsx_inline_strings_are_preserved():
    worksheet_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData><row><c t="inlineStr"><is><t>Inspection</t></is></c></row></sheetData>
</worksheet>"""
    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    markdown = normalize_office_document(package.getvalue(), EXCEL_MIME)

    assert markdown == "## Sheet 1\n\nInspection\n"


def test_xlsx_invalid_shared_string_reference_is_rejected():
    worksheet_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData><row><c t="s"><v>4</v></c></row></sheetData>
</worksheet>"""
    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)

    with pytest.raises(ValueError, match="could not be normalized"):
        normalize_office_document(package.getvalue(), EXCEL_MIME)


def test_office_package_over_xml_budget_is_rejected():
    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr("word/document.xml", b" " * (MAX_XML_BYTES + 1))

    with pytest.raises(ValueError, match="exceeds the normalization limit"):
        normalize_office_document(package.getvalue(), WORD_MIME)


def test_pptx_text_is_normalized_by_slide():
    slide_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><a:t>Evidence intake</a:t><a:t>Demo ready</a:t></p:cSld>
</p:sld>"""
    package = BytesIO()
    with ZipFile(package, "w") as archive:
        archive.writestr("ppt/slides/slide1.xml", slide_xml)

    markdown = normalize_office_document(package.getvalue(), POWERPOINT_MIME)

    assert markdown == "## Slide 1\n\nEvidence intake\nDemo ready\n"