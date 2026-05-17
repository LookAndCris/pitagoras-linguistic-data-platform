from __future__ import annotations

from typing import Any

import httpx
import pytest

from apps.frontend.api.client import BackendApiError, BackendClient, build_subcategory_list


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
                "doc_id": "doc-1",
                "category": "linguistics",
                "subcategory": ["syntax"],
                "source": "manual",
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
