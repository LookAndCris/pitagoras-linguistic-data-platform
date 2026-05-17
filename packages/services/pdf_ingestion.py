from io import BytesIO

from pypdf import PdfReader


class PdfUploadError(Exception):
    pass


class UnsupportedPdfError(PdfUploadError):
    pass


class CorruptPdfError(PdfUploadError):
    pass


class EmptyPdfTextError(PdfUploadError):
    pass


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def extract_pdf_text(content: bytes, *, filename: str | None, content_type: str | None) -> str:
    del filename

    if content_type != "application/pdf":
        raise UnsupportedPdfError("Uploaded file must be a PDF")

    if not content.startswith(b"%PDF-"):
        raise UnsupportedPdfError("Uploaded file must be a valid PDF")

    try:
        reader = PdfReader(BytesIO(content))
    except Exception as exc:  # noqa: BLE001
        raise CorruptPdfError("Uploaded PDF is corrupt or unreadable") from exc

    extracted = " ".join(page.extract_text() or "" for page in reader.pages)
    normalized = _normalize_whitespace(extracted)

    if not normalized:
        raise EmptyPdfTextError("PDF has no extractable text; OCR is not supported")

    return normalized
