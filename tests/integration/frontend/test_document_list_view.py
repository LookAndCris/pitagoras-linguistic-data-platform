from __future__ import annotations

from typing import Any

import pytest

from apps.frontend.api.client import BackendApiError


class _ListClientSuccess:
    def __init__(self, items: list[dict[str, Any]]) -> None:
        self.items = items
        self.calls = 0

    def list_documents(self) -> dict[str, Any]:
        self.calls += 1
        return {"items": self.items}


class _ListClientError:
    def __init__(self, error: BackendApiError) -> None:
        self.error = error
        self.calls = 0

    def list_documents(self) -> dict[str, Any]:
        self.calls += 1
        raise self.error


def _patch_list_streamlit(
    monkeypatch: pytest.MonkeyPatch,
    list_module: Any,
    *,
    refresh_clicked: bool,
) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"info": [], "error": [], "dataframe": []}

    monkeypatch.setattr(list_module.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(list_module.st, "button", lambda *_args, **_kwargs: refresh_clicked)
    monkeypatch.setattr(list_module.st, "info", lambda message, **_kwargs: calls["info"].append(message))
    monkeypatch.setattr(list_module.st, "error", lambda message, **_kwargs: calls["error"].append(message))
    monkeypatch.setattr(
        list_module.st,
        "dataframe",
        lambda payload, **_kwargs: calls["dataframe"].append(payload),
    )

    return calls


def test_document_list_renders_rows_when_backend_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.views import document_list

    calls = _patch_list_streamlit(monkeypatch, document_list, refresh_clicked=False)
    client = _ListClientSuccess(
        items=[
            {
                "id": "a6adf7da-35c4-40e8-8a5a-345dd5702225",
                "doc_id": "doc-001",
                "category": "linguistics",
                "subcategory": ["syntax", "morphology"],
                "source": "manual",
                "url": None,
                "publication_date": None,
                "word_count": 25,
                "created_at": "2026-05-17T13:10:00Z",
            }
        ]
    )

    document_list.render_document_list_view(client)

    assert client.calls == 1
    assert calls["dataframe"]
    assert calls["dataframe"][0][0]["doc_id"] == "doc-001"
    assert not calls["error"]


def test_document_list_renders_empty_state_when_no_items(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.views import document_list

    calls = _patch_list_streamlit(monkeypatch, document_list, refresh_clicked=False)
    client = _ListClientSuccess(items=[])

    document_list.render_document_list_view(client)

    assert client.calls == 1
    assert calls["info"]
    assert "No documents found" in calls["info"][0]
    assert not calls["dataframe"]
    assert not calls["error"]


def test_document_list_renders_service_unavailable_error_on_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.views import document_list

    calls = _patch_list_streamlit(monkeypatch, document_list, refresh_clicked=True)
    client = _ListClientError(BackendApiError(status_code=503, detail="Document persistence is unavailable"))

    document_list.render_document_list_view(client)

    assert client.calls == 1
    assert calls["error"]
    assert "Service unavailable (503):" in calls["error"][0]
    assert "Document persistence is unavailable" in calls["error"][0]
    assert not calls["dataframe"]
