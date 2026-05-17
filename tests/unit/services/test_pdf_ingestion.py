from dataclasses import dataclass

import pytest

from packages.services.pdf_ingestion import (
    CorruptPdfError,
    EmptyPdfTextError,
    UnsupportedPdfError,
    extract_pdf_text,
)


@dataclass
class _FakePage:
    text: str | None

    def extract_text(self) -> str | None:
        return self.text


def test_extract_pdf_text_returns_normalized_text(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeReader:
        def __init__(self, _content: object) -> None:
            self.pages = [_FakePage("  Hello\n"), _FakePage("   world\tfrom   PDF  ")]

    monkeypatch.setattr("packages.services.pdf_ingestion.PdfReader", _FakeReader)

    result = extract_pdf_text(
        b"%PDF-1.7\nplaceholder",
        filename="sample.pdf",
        content_type="application/pdf",
    )

    assert result == "Hello world from PDF"


def test_extract_pdf_text_rejects_non_pdf_content_type() -> None:
    with pytest.raises(UnsupportedPdfError):
        extract_pdf_text(
            b"%PDF-1.7\nplaceholder",
            filename="sample.txt",
            content_type="text/plain",
        )


def test_extract_pdf_text_rejects_corrupt_pdf_bytes() -> None:
    with pytest.raises(CorruptPdfError):
        extract_pdf_text(
            b"%PDF-1.7\nthis-is-not-a-valid-pdf-structure",
            filename="broken.pdf",
            content_type="application/pdf",
        )


def test_extract_pdf_text_rejects_pdf_without_extractable_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeReader:
        def __init__(self, _content: object) -> None:
            self.pages = [_FakePage("   "), _FakePage(None)]

    monkeypatch.setattr("packages.services.pdf_ingestion.PdfReader", _FakeReader)

    with pytest.raises(EmptyPdfTextError):
        extract_pdf_text(
            b"%PDF-1.7\nplaceholder",
            filename="image-only.pdf",
            content_type="application/pdf",
        )
