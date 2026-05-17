from __future__ import annotations

from typing import Any

import httpx
import pytest

from apps.frontend.api.client import BackendApiError, BackendClient, build_subcategory_list


APPROVED_CATEGORIES = [
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
]

APPROVED_SOURCES = [
    "papers",
    "noticias",
    "blogs",
    "redes sociales",
    "entrevistas",
    "podcasts",
    "documentación",
    "novelas",
]


def test_build_subcategory_list_trims_and_splits_comma_separated_values() -> None:
    result = build_subcategory_list(" grammar,  syntax , , morphology ")

    assert result == ["grammar", "syntax", "morphology"]


def test_build_subcategory_list_accepts_list_input_and_strips_items() -> None:
    result = build_subcategory_list([" grammar ", "", "syntax", "   ", "morphology"])

    assert result == ["grammar", "syntax", "morphology"]


def test_normalize_http_error_handles_string_detail() -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)
    request = httpx.Request("POST", "http://localhost:8000/documents")
    response = httpx.Response(status_code=409, json={"detail": "Document already exists"}, request=request)
    error = httpx.HTTPStatusError("Conflict", request=request, response=response)

    normalized = client.normalize_http_error(error)

    assert normalized.status_code == 409
    assert normalized.detail == "Document already exists"


def test_normalize_http_error_handles_list_detail() -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)
    request = httpx.Request("POST", "http://localhost:8000/documents")
    response = httpx.Response(
        status_code=422,
        json={"detail": [{"loc": ["body", "raw_text"], "msg": "Field required"}]},
        request=request,
    )
    error = httpx.HTTPStatusError("Unprocessable", request=request, response=response)

    normalized = client.normalize_http_error(error)

    assert normalized.status_code == 422
    assert "raw_text" in normalized.detail
    assert "Field required" in normalized.detail


def test_normalize_transport_error_returns_service_unavailable() -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)
    request = httpx.Request("GET", "http://localhost:8000/documents")
    error = httpx.ConnectError("Connection refused", request=request)

    normalized = client.normalize_transport_error(error)

    assert normalized.status_code == 503
    assert "Could not reach backend service" in normalized.detail


def test_create_document_raises_normalized_backend_error_on_http_status(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)

    def fake_request(*_: Any, **__: Any) -> dict[str, Any]:
        raise BackendApiError(status_code=422, detail="raw_text is required")

    monkeypatch.setattr(client, "request_json", fake_request)

    with pytest.raises(BackendApiError) as exc_info:
        client.create_document(
            {
                "category": "Académico",
                "subcategory": ["syntax"],
                "source": "papers",
                "raw_text": "text",
            }
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "raw_text is required"


def test_list_documents_uses_get_documents_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)

    captured: dict[str, Any] = {}

    def fake_request(method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        captured["method"] = method
        captured["path"] = path
        captured["json_body"] = json_body
        return {"items": [{"doc_id": "doc-1"}]}

    monkeypatch.setattr(client, "request_json", fake_request)

    response = client.list_documents()

    assert captured == {"method": "GET", "path": "/documents", "json_body": None}
    assert response["items"][0]["doc_id"] == "doc-1"


def test_get_metadata_options_uses_backend_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)

    captured: dict[str, Any] = {}

    def fake_request(method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        captured["method"] = method
        captured["path"] = path
        captured["json_body"] = json_body
        return {"categories": APPROVED_CATEGORIES, "sources": APPROVED_SOURCES}

    monkeypatch.setattr(client, "request_json", fake_request)

    response = client.get_metadata_options()

    assert captured == {"method": "GET", "path": "/documents/metadata-options", "json_body": None}
    assert response == {"categories": APPROVED_CATEGORIES, "sources": APPROVED_SOURCES}


def test_create_document_omits_doc_id_and_serializes_publication_year(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)

    captured: dict[str, Any] = {}

    def fake_request(method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        captured["method"] = method
        captured["path"] = path
        captured["json_body"] = json_body
        return {"doc_id": "doc_generated"}

    monkeypatch.setattr(client, "request_json", fake_request)

    response = client.create_document(
        {
            "category": "Tecnología",
            "subcategory": ["syntax"],
            "source": "papers",
            "raw_text": "text",
            "publication_year": 2026,
        }
    )

    assert captured == {
        "method": "POST",
        "path": "/documents",
        "json_body": {
            "category": "Tecnología",
            "subcategory": ["syntax"],
            "source": "papers",
            "raw_text": "text",
            "publication_year": 2026,
        },
    }
    assert response == {"doc_id": "doc_generated"}


def test_upload_pdf_document_omits_doc_id_and_sends_publication_year(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)

    class _FakeResponse:
        def __init__(self) -> None:
            self.content = b'{"doc_id": "doc_generated"}'

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"doc_id": "doc_generated"}

    class _FakeHttpClient:
        captured: dict[str, Any] = {}

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeHttpClient":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def post(self, *, url: str, data: list[tuple[str, str]], files: dict[str, tuple[str, bytes, str]]) -> _FakeResponse:
            self.captured["url"] = url
            self.captured["data"] = data
            self.captured["files"] = files
            return _FakeResponse()

    monkeypatch.setattr("apps.frontend.api.client.httpx.Client", _FakeHttpClient)

    response = client.upload_pdf_document(
        {
            "category": "Tecnología",
            "subcategory": ["Syntax", "Morphology"],
            "source": "papers",
            "publication_year": 2026,
            "url": "https://example.com/doc.pdf",
        },
        filename="sample.pdf",
        content=b"pdf",
        content_type="application/pdf",
    )

    assert _FakeHttpClient.captured["url"] == "http://localhost:8000/documents/upload-pdf"
    assert ("doc_id", "doc-1") not in _FakeHttpClient.captured["data"]
    assert ("category", "Tecnología") in _FakeHttpClient.captured["data"]
    assert ("source", "papers") in _FakeHttpClient.captured["data"]
    assert ("subcategory", "syntax") in _FakeHttpClient.captured["data"]
    assert ("subcategory", "morphology") in _FakeHttpClient.captured["data"]
    assert ("publication_year", "2026") in _FakeHttpClient.captured["data"]
    assert ("url", "https://example.com/doc.pdf") in _FakeHttpClient.captured["data"]
    assert response == {"doc_id": "doc_generated"}


def test_upload_pdf_document_preserves_zero_publication_year(monkeypatch: pytest.MonkeyPatch) -> None:
    client = BackendClient(base_url="http://localhost:8000", timeout_seconds=5.0)

    class _FakeResponse:
        def __init__(self) -> None:
            self.content = b'{"doc_id": "doc_generated"}'

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"doc_id": "doc_generated"}

    class _FakeHttpClient:
        captured: dict[str, Any] = {}

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def __enter__(self) -> "_FakeHttpClient":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

        def post(self, *, url: str, data: list[tuple[str, str]], files: dict[str, tuple[str, bytes, str]]) -> _FakeResponse:
            self.captured["url"] = url
            self.captured["data"] = data
            self.captured["files"] = files
            return _FakeResponse()

    monkeypatch.setattr("apps.frontend.api.client.httpx.Client", _FakeHttpClient)

    client.upload_pdf_document(
        {
            "category": "Tecnología",
            "subcategory": ["Syntax"],
            "source": "papers",
            "publication_year": 0,
        },
        filename="sample.pdf",
        content=b"pdf",
        content_type="application/pdf",
    )

    assert ("publication_year", "0") in _FakeHttpClient.captured["data"]
