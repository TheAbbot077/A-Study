import io
import zipfile

from apps.content_processing.application.extraction_ports import SourceDocument
from apps.content_processing.domain.extraction import SourceFormat
from apps.content_processing.infrastructure.document_extraction import detect_source_format


def source(name, content, content_type=""):
    return SourceDocument("file", name, content_type, len(content), "checksum", content)


def test_pdf_detection_uses_signature_and_reports_extension_mismatch():
    detected, mime, warnings = detect_source_format(source("notes.docx", b"%PDF-1.7\n", "application/pdf"))
    assert detected == SourceFormat.PDF
    assert mime == "application/pdf"
    assert warnings[0]["code"] == "extension_signature_mismatch"


def test_docx_detection_verifies_ooxml_members():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as package:
        package.writestr("[Content_Types].xml", "<Types />")
        package.writestr("word/document.xml", "<document />")
    detected, _, _ = detect_source_format(source("notes.docx", payload.getvalue()))
    assert detected == SourceFormat.DOCX


def test_plain_zip_is_not_a_docx():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w") as package:
        package.writestr("notes.txt", "hello")
    detected, _, _ = detect_source_format(source("notes.docx", payload.getvalue()))
    assert detected == SourceFormat.UNKNOWN
