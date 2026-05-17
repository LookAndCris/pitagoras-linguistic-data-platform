import pytest

import apps.frontend.main
from apps.frontend.api.client import BackendApiError
from apps.frontend.main import get_supported_flows
from apps.frontend.ui.feedback import build_error_message, format_error_detail


def test_shell_exposes_only_supported_flows() -> None:
    flows = get_supported_flows()

    assert flows == ["Manual ingestion", "PDF upload", "Document list"]


def test_shell_does_not_expose_out_of_scope_flows() -> None:
    flows = get_supported_flows()

    assert "Login" not in flows
    assert "Search" not in flows
    assert "Pagination" not in flows
    assert "Document detail" not in flows


def test_format_error_detail_handles_detail_lists() -> None:
    detail = [{"loc": ["body", "subcategory"], "msg": "Field required"}]

    message = format_error_detail(detail)

    assert "subcategory" in message
    assert "Field required" in message


def test_build_error_message_includes_status_context() -> None:
    error = BackendApiError(status_code=415, detail="Unsupported file type")

    message = build_error_message(error)

    assert "Unsupported media type" in message
    assert "Unsupported file type" in message


def test_render_shell_routes_manual_ingestion_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"manual": 0, "pdf": 0, "list": 0}

    monkeypatch.setattr(apps.frontend.main.st, "set_page_config", lambda **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st, "title", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st.sidebar, "radio", lambda *_args, **_kwargs: "Manual ingestion")
    monkeypatch.setattr(
        apps.frontend.main,
        "render_manual_ingestion_view",
        lambda _client: calls.__setitem__("manual", calls["manual"] + 1),
    )
    monkeypatch.setattr(
        apps.frontend.main,
        "render_pdf_upload_view",
        lambda _client: calls.__setitem__("pdf", calls["pdf"] + 1),
    )
    monkeypatch.setattr(
        apps.frontend.main,
        "render_document_list_view",
        lambda _client: calls.__setitem__("list", calls["list"] + 1),
    )

    apps.frontend.main.render_shell()

    assert calls == {"manual": 1, "pdf": 0, "list": 0}


def test_render_shell_routes_pdf_upload_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"manual": 0, "pdf": 0, "list": 0}

    monkeypatch.setattr(apps.frontend.main.st, "set_page_config", lambda **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st, "title", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st.sidebar, "radio", lambda *_args, **_kwargs: "PDF upload")
    monkeypatch.setattr(
        apps.frontend.main,
        "render_manual_ingestion_view",
        lambda _client: calls.__setitem__("manual", calls["manual"] + 1),
    )
    monkeypatch.setattr(
        apps.frontend.main,
        "render_pdf_upload_view",
        lambda _client: calls.__setitem__("pdf", calls["pdf"] + 1),
    )
    monkeypatch.setattr(
        apps.frontend.main,
        "render_document_list_view",
        lambda _client: calls.__setitem__("list", calls["list"] + 1),
    )

    apps.frontend.main.render_shell()

    assert calls == {"manual": 0, "pdf": 1, "list": 0}


def test_render_shell_routes_document_list_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"manual": 0, "pdf": 0, "list": 0}

    monkeypatch.setattr(apps.frontend.main.st, "set_page_config", lambda **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st, "title", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st, "caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(apps.frontend.main.st.sidebar, "radio", lambda *_args, **_kwargs: "Document list")
    monkeypatch.setattr(
        apps.frontend.main,
        "render_manual_ingestion_view",
        lambda _client: calls.__setitem__("manual", calls["manual"] + 1),
    )
    monkeypatch.setattr(
        apps.frontend.main,
        "render_pdf_upload_view",
        lambda _client: calls.__setitem__("pdf", calls["pdf"] + 1),
    )
    monkeypatch.setattr(
        apps.frontend.main,
        "render_document_list_view",
        lambda _client: calls.__setitem__("list", calls["list"] + 1),
    )

    apps.frontend.main.render_shell()

    assert calls == {"manual": 0, "pdf": 0, "list": 1}


def test_render_created_document_summary_renders_success_and_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.ui import feedback

    calls: dict[str, list[object]] = {"success": [], "json": []}
    monkeypatch.setattr(feedback.st, "success", lambda message, **_kwargs: calls["success"].append(message))
    monkeypatch.setattr(feedback.st, "json", lambda payload, **_kwargs: calls["json"].append(payload))

    feedback.render_created_document_summary("Created", {"doc_id": "doc-1"})

    assert calls["success"] == ["Created"]
    assert calls["json"] == [{"doc_id": "doc-1"}]


def test_render_created_document_summary_accepts_nested_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.frontend.ui import feedback

    calls: dict[str, list[object]] = {"success": [], "json": []}
    monkeypatch.setattr(feedback.st, "success", lambda message, **_kwargs: calls["success"].append(message))
    monkeypatch.setattr(feedback.st, "json", lambda payload, **_kwargs: calls["json"].append(payload))

    payload = {"doc_id": "doc-2", "subcategory": ["syntax"], "meta": {"source": "manual"}}
    feedback.render_created_document_summary("Created from upload", payload)

    assert calls["success"] == ["Created from upload"]
    assert calls["json"] == [payload]
