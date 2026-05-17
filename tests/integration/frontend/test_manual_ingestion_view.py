from __future__ import annotations

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


class _ManualClientSuccess:
    def __init__(self) -> None:
        self.last_payload: dict[str, Any] | None = None

    def get_metadata_options(self) -> dict[str, list[str]]:
        return APPROVED_METADATA_OPTIONS

    def create_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.last_payload = payload
        return {
            "id": "5d5b6270-6582-4f8a-ae6e-4db228a7e754",
            "doc_id": "doc_generated",
            "category": payload["category"],
            "subcategory": payload["subcategory"],
            "source": payload["source"],
            "url": payload.get("url"),
            "publication_date": "2026-01-01" if payload.get("publication_year") else None,
            "word_count": 12,
            "created_at": "2026-05-17T10:10:10Z",
        }


class _ManualClientError:
    def __init__(self, error: BackendApiError) -> None:
        self.error = error

    def get_metadata_options(self) -> dict[str, list[str]]:
        return APPROVED_METADATA_OPTIONS

    def create_document(self, payload: dict[str, Any]) -> dict[str, Any]:
        raise self.error


def _patch_manual_streamlit(
    monkeypatch: pytest.MonkeyPatch,
    manual_module: Any,
    *,
    category: str = "Tecnología",
    subcategory_raw: str = "syntax, morphology",
    source: str = "papers",
    url: str = "https://example.com/doc-123",
    publication_year: int = 2026,
    raw_text: str = "This is sample text.",
    submit: bool = True,
) -> dict[str, list[Any]]:
    calls: dict[str, list[Any]] = {"warning": [], "error": [], "success": [], "json": []}

    monkeypatch.setattr(manual_module.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        manual_module.st,
        "selectbox",
        lambda label, options, **_kwargs: category if label == "Category" else source,
    )
    monkeypatch.setattr(
        manual_module.st,
        "text_input",
        lambda label, **_kwargs: {
            "Subcategory (comma-separated)": subcategory_raw,
            "URL (optional)": url,
        }[label],
    )
    monkeypatch.setattr(manual_module.st, "number_input", lambda *_args, **_kwargs: publication_year)
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

    manual_ingestion.render_manual_ingestion_view(client, APPROVED_METADATA_OPTIONS)

    assert client.last_payload is not None
    assert client.last_payload["category"] == "Tecnología"
    assert client.last_payload["raw_text"] == "This is sample text."
    assert client.last_payload["subcategory"] == ["syntax", "morphology"]
    assert client.last_payload["source"] == "papers"
    assert client.last_payload["publication_year"] == 2026
    assert "doc_id" not in client.last_payload
    assert calls["success"]
    assert calls["json"]
    assert calls["json"][0]["doc_id"] == "doc_generated"
    assert not calls["error"]


def test_manual_ingestion_publication_year_input_disallows_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.views import manual_ingestion

    captured: dict[str, Any] = {}

    monkeypatch.setattr(manual_ingestion.st, "subheader", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        manual_ingestion.st,
        "selectbox",
        lambda label, options, **_kwargs: "Tecnología" if label == "Category" else "papers",
    )
    monkeypatch.setattr(
        manual_ingestion.st,
        "text_input",
        lambda label, **_kwargs: "syntax" if label == "Subcategory (comma-separated)" else "",
    )
    monkeypatch.setattr(
        manual_ingestion.st,
        "number_input",
        lambda *args, **kwargs: captured.update({"args": args, "kwargs": kwargs}) or None,
    )
    monkeypatch.setattr(manual_ingestion.st, "text_area", lambda *_args, **_kwargs: "sample text")
    monkeypatch.setattr(manual_ingestion.st, "button", lambda *_args, **_kwargs: False)

    manual_ingestion.render_manual_ingestion_view(_ManualClientSuccess(), APPROVED_METADATA_OPTIONS)

    assert captured["args"][0] == "Publication year (optional)"
    assert captured["kwargs"]["min_value"] == 1
    assert captured["kwargs"]["max_value"] == 9999
    assert captured["kwargs"]["value"] is None


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

    manual_ingestion.render_manual_ingestion_view(client, APPROVED_METADATA_OPTIONS)

    assert calls["error"]
    assert expected_fragment in calls["error"][0]
    assert detail in calls["error"][0]
    assert not calls["success"]
