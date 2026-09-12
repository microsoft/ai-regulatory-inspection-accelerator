"""Minimal OOXML-to-Markdown normalization."""

from __future__ import annotations

from io import BytesIO
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

WORD_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
POWERPOINT_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
OFFICE_MIME_TYPES = frozenset({WORD_MIME, EXCEL_MIME, POWERPOINT_MIME})
MAX_XML_BYTES = 50 * 1024 * 1024


def normalize_office_document(content: bytes, mime_type: str) -> str:
    """Extract readable Markdown from a DOCX, XLSX, or PPTX OOXML package."""
    try:
        with ZipFile(BytesIO(content)) as package:
            xml_size = sum(
                entry.file_size for entry in package.infolist()
                if entry.filename.endswith(".xml")
            )
            if xml_size > MAX_XML_BYTES:
                raise ValueError("The Office document exceeds the normalization limit.")
            if mime_type == WORD_MIME:
                return _normalize_word(package)
            if mime_type == EXCEL_MIME:
                return _normalize_excel(package)
            if mime_type == POWERPOINT_MIME:
                return _normalize_powerpoint(package)
    except (BadZipFile, KeyError, IndexError, ElementTree.ParseError) as error:
        raise ValueError("The Office document could not be normalized.") from error
    raise ValueError(f"Unsupported Office MIME type: {mime_type}")


def _normalize_word(package: ZipFile) -> str:
    root = ElementTree.fromstring(package.read("word/document.xml"))
    paragraphs = []
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t")).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs) + "\n"


def _normalize_excel(package: ZipFile) -> str:
    shared_strings = _shared_strings(package)
    sections = []
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    sheet_names = sorted(
        name for name in package.namelist()
        if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
    )
    for index, name in enumerate(sheet_names, start=1):
        root = ElementTree.fromstring(package.read(name))
        rows = []
        for row in root.iter(f"{namespace}row"):
            values = []
            for cell in row:
                if cell.get("t") == "inlineStr":
                    text = "".join(node.text or "" for node in cell.iter(f"{namespace}t"))
                else:
                    value = cell.find(f"{namespace}v")
                    text = "" if value is None else value.text or ""
                    if cell.get("t") == "s" and text.isdigit():
                        text = shared_strings[int(text)]
                values.append(text)
            rows.append(" | ".join(values))
        sections.append(f"## Sheet {index}\n\n" + "\n".join(rows))
    return "\n\n".join(sections).strip() + "\n"


def _shared_strings(package: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in package.namelist():
        return []
    root = ElementTree.fromstring(package.read("xl/sharedStrings.xml"))
    namespace = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t"
    return ["".join(node.text or "" for node in item.iter(namespace)) for item in root]


def _normalize_powerpoint(package: ZipFile) -> str:
    sections = []
    namespace = "{http://schemas.openxmlformats.org/drawingml/2006/main}t"
    slide_names = sorted(
        name for name in package.namelist()
        if name.startswith("ppt/slides/slide") and name.endswith(".xml")
    )
    for index, name in enumerate(slide_names, start=1):
        root = ElementTree.fromstring(package.read(name))
        text = "\n".join(node.text or "" for node in root.iter(namespace) if node.text)
        sections.append(f"## Slide {index}\n\n{text}")
    return "\n\n".join(sections).strip() + "\n"