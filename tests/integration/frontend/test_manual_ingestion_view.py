from __future__ import annotations

from typing import Any

import pytest

from apps.frontend.api.client import BackendApiError


class _ManualClientSuccess:
    def __init__(self) -> None:
        self.last_payload: dict[str, Any] | None = None

    def create_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.last_payload = payload
        return {
            "id": "5d5b6270-6582-4f8a-ae6e-4db228a7e754",
            "doc_id": payload["doc_id"],
            "category": payload["category"],
            "subcategory": payload["subcategory"],
            "source": payload["source"],
            "url": payload.get("url"),
            "publication_date": payload.get("publication_date"),
            "word_count": 12,
            "created_at": "2026-05-17T10:10:10Z",
        }


class _ManualClientError:
    def __init__(self, error: BackendApiError) -> None:
        self.error = error

    def create_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise self.error


def _patch_manual_streamlit(
    monkeypatch: pytest.MonkeyPatch,
    manual_module: Any,
    *,
    doc_id: str = "doc-123",
    category: str = "linguistics",
    subcategory_raw: str = "syntax, morphology",
    source: str = "manual",
    url: str = "https://example.com/doc-123",
    publication_date: str = "2026-05-17",
    raw_text: str = "This is sample text.",
    submit: bool = True,
) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"warning": [], "error": [], "success": [], "json": []}

    text_values = {
        "Document ID": doc_id,
        "Category": category,
        "Subcategory (comma-separated)": subcategory_raw,
        "Source": source,
        "URL (optional)": url,
        "Publication date (optional, YYYY-MM-DD)": publication_date,
    }

    monkeypatch.setattr(manual_module.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(manual_module.st, "text_input", lambda label, **_kwargs: text_values[label])
    monkeypatch.setattr(manual_module.st, "text_area", lambda *_args, **_kwargs: raw_text)
    monkeypatch.setattr(manual_module.st, "button", lambda *_args, **_kwargs: submit)
    monkeypatch.setattr(manual_module.st, "warning", lambda message, **_kwargs: calls["warning"].append(message))
    monkeypatch.setattr(manual_module.st, "error", lambda message, **_kwargs: calls["error"].append(message))
    monkeypatch.setattr(manual_module.st, "success", lambda message, **_kwargs: calls["success"].append(message))
    monkeypatch.setattr(manual_module.st, "json", lambda payload, **_kwargs: calls["json"].append(payload))

    return calls


def test_manual_ingestion_submits_payload_and_renders_created_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.views import manual_ingestion

    calls = _patch_manual_streamlit(monkeypatch, manual_ingestion)
    client = _ManualClientSuccess()

    manual_ingestion.render_manual_ingestion_view(client)

    assert client.last_payload is not None
    assert client.last_payload["raw_text"] == "This is sample text."
    assert client.last_payload["subcategory"] == ["syntax", "morphology"]
    assert calls["success"]
    assert calls["json"]
    assert not calls["error"]


@pytest.mark.parametrize(
    ("status_code", "detail", "expected_fragment"),
    [
        (409, "Document already exists", "Conflict (409):"),
        (422, "raw_text is required", "Validation error (422):"),
        (503, "Document persistence is unavailable", "Service unavailable (503):"),
    ],
)
def test_manual_ingestion_renders_expected_backend_errors(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    detail: str,
    expected_fragment: str,
) -> None:
    from apps.frontend.views import manual_ingestion

    calls = _patch_manual_streamlit(monkeypatch, manual_ingestion)
    client = _ManualClientError(BackendApiError(status_code=status_code, detail=detail))

    manual_ingestion.render_manual_ingestion_view(client)

    assert calls["error"]
    assert expected_fragment in calls["error"][0]
    assert detail in calls["error"][0]
    assert not calls["success"]
