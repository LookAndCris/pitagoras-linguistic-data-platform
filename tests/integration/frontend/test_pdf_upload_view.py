from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from apps.frontend.api.client import BackendApiError


APPROVED_METADATA_OPTIONS = {
    "categories": [
        "Noticias",
        "Tecnología",
        "Negocios",
        "Ciencia",
        "Salud",
        "Deportes",
        "Entretenimiento",
        "Literatura",
        "Redes Sociales",
        "Lifestyle",
        "Política",
        "Académico",
    ],
    "sources": [
        "papers",
        "noticias",
        "blogs",
        "redes sociales",
        "entrevistas",
        "podcasts",
        "documentación",
        "novelas",
    ],
}


@dataclass
class _UploadedFile:
    name: str
    type: str
    _content: bytes

    def getvalue(self) -> bytes:
        return self._content


class _PdfClientSuccess:
    def __init__(self) -> None:
        self.last_metadata: dict[str, Any] | None = None
        self.last_file: tuple[str, bytes, str] | None = None

    def get_metadata_options(self) -> dict[str, list[str]]:
        return APPROVED_METADATA_OPTIONS

    def upload_pdf_document(
        self,
        metadata: dict[str, Any],
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        self.last_metadata = metadata
        self.last_file = (filename, content, content_type)
        return {
            "id": "b4b9c38b-5500-43fb-91cf-a66ff7d3df6d",
            "doc_id": "doc_generated",
            "category": metadata["category"],
            "subcategory": metadata["subcategory"],
            "source": metadata["source"],
            "word_count": 99,
            "created_at": "2026-05-17T10:11:00Z",
        }


class _PdfClientError:
    def __init__(self, error: BackendApiError) -> None:
        self.error = error

    def get_metadata_options(self) -> dict[str, list[str]]:
        return APPROVED_METADATA_OPTIONS

    def upload_pdf_document(
        self,
        metadata: dict[str, Any],
        *,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        raise self.error


def _patch_pdf_streamlit(
    monkeypatch: pytest.MonkeyPatch,
    pdf_module: Any,
    *,
    category: str = "Tecnología",
    subcategory_raw: str = "syntax, morphology",
    source: str = "papers",
    url: str = "https://example.com/pdf-123",
    publication_year: int = 2026,
    uploaded_file: _UploadedFile | None = None,
    submit: bool = True,
) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"warning": [], "error": [], "success": [], "json": []}

    file_value = uploaded_file or _UploadedFile(
        name="sample.pdf",
        type="application/pdf",
        _content=b"%PDF-1.7\nplaceholder",
    )

    monkeypatch.setattr(pdf_module.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        pdf_module.st,
        "selectbox",
        lambda label, options, **_kwargs: category if label == "Category" else source,
    )
    monkeypatch.setattr(
        pdf_module.st,
        "text_input",
        lambda label, **_kwargs: {
            "Subcategory (comma-separated)": subcategory_raw,
            "URL (optional)": url,
        }[label],
    )
    monkeypatch.setattr(pdf_module.st, "number_input", lambda *_args, **_kwargs: publication_year)
    monkeypatch.setattr(pdf_module.st, "file_uploader", lambda *_args, **_kwargs: file_value)
    monkeypatch.setattr(pdf_module.st, "button", lambda *_args, **_kwargs: submit)
    monkeypatch.setattr(pdf_module.st, "warning", lambda message, **_kwargs: calls["warning"].append(message))
    monkeypatch.setattr(pdf_module.st, "error", lambda message, **_kwargs: calls["error"].append(message))
    monkeypatch.setattr(pdf_module.st, "success", lambda message, **_kwargs: calls["success"].append(message))
    monkeypatch.setattr(pdf_module.st, "json", lambda payload, **_kwargs: calls["json"].append(payload))

    return calls


def test_pdf_upload_submits_multipart_payload_and_renders_created_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.views import pdf_upload

    calls = _patch_pdf_streamlit(monkeypatch, pdf_upload)
    client = _PdfClientSuccess()

    pdf_upload.render_pdf_upload_view(client, APPROVED_METADATA_OPTIONS)

    assert client.last_metadata is not None
    assert client.last_metadata["category"] == "Tecnología"
    assert client.last_metadata["subcategory"] == ["syntax", "morphology"]
    assert client.last_metadata["source"] == "papers"
    assert client.last_metadata["publication_year"] == 2026
    assert "doc_id" not in client.last_metadata
    assert client.last_file == ("sample.pdf", b"%PDF-1.7\nplaceholder", "application/pdf")
    assert calls["success"]
    assert calls["json"]
    assert calls["json"][0]["doc_id"] == "doc_generated"
    assert not calls["error"]


def test_pdf_upload_publication_year_input_disallows_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.views import pdf_upload

    captured: dict[str, Any] = {}

    monkeypatch.setattr(pdf_upload.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        pdf_upload.st,
        "selectbox",
        lambda label, options, **_kwargs: "Tecnología" if label == "Category" else "papers",
    )
    monkeypatch.setattr(
        pdf_upload.st,
        "text_input",
        lambda label, **_kwargs: "syntax" if label == "Subcategory (comma-separated)" else "",
    )
    monkeypatch.setattr(
        pdf_upload.st,
        "number_input",
        lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs}) or None,
    )
    monkeypatch.setattr(pdf_upload.st, "file_uploader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(pdf_upload.st, "button", lambda *_args, **_kwargs: False)

    pdf_upload.render_pdf_upload_view(_PdfClientSuccess(), APPROVED_METADATA_OPTIONS)

    assert captured["args"][0] == "Publication year (optional)"
    assert captured["kwargs"]["min_value"] == 1
    assert captured["kwargs"]["max_value"] == 9999
    assert captured["kwargs"]["value"] is None


@pytest.mark.parametrize(
    ("status_code", "detail", "expected_fragment"),
    [
        (415, "Unsupported media type", "Unsupported media type (415):"),
        (422, "Invalid PDF payload", "Validation error (422):"),
        (409, "Document already exists", "Conflict (409):"),
        (503, "Document persistence is unavailable", "Service unavailable (503):"),
    ],
)
def test_pdf_upload_renders_expected_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    detail: str,
    expected_fragment: str,
) -> None:
    from apps.frontend.views import pdf_upload

    calls = _patch_pdf_streamlit(monkeypatch, pdf_upload)
    client = _PdfClientError(BackendApiError(status_code=status_code, detail=detail))

    pdf_upload.render_pdf_upload_view(client, APPROVED_METADATA_OPTIONS)

    assert calls["error"]
    assert expected_fragment in calls["error"][0]
    assert detail in calls["error"][0]
    assert not calls["success"]
