import os
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.backend.app.main import create_app
from packages.core.settings import Settings
from packages.services.pdf_ingestion import CorruptPdfError, EmptyPdfTextError


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path}"


def _upgrade_to_head(database_url: str) -> None:
    env_snapshot = {key: value for key, value in os.environ.items() if key.startswith("PITAGORAS_")}
    alembic_cfg = Config("apps/backend/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    try:
        command.upgrade(alembic_cfg, "head")
    finally:
        current_keys = [key for key in os.environ if key.startswith("PITAGORAS_")]
        for key in current_keys:
            os.environ.pop(key, None)
        os.environ.update(env_snapshot)


def _pdf_bytes() -> bytes:
    return b"%PDF-1.7\nminimal-placeholder"


def _empty_list_response() -> dict[str, object]:
    return {
        "items": [],
        "summary": {
            "sample_count": 0,
            "total_words": 0,
            "categories": [],
        },
    }


def test_get_metadata_options_returns_canonical_sets(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-metadata-options.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.get("/documents/metadata-options")

    assert response.status_code == 200
    assert response.json() == {
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


def test_create_document_metadata_returns_created_item(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-create.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    payload = {
        "category": "Tecnología",
        "subcategory": [" Verbs ", "Mood"],
        "source": "blogs",
        "url": "https://example.com/doc-100",
        "publication_year": 2024,
        "raw_text": "uno dos tres",
    }

    with TestClient(app) as client:
        response = client.post("/documents", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["doc_id"].startswith("doc_")
    assert body["category"] == "Tecnología"
    assert body["subcategory"] == ["verbs", "mood"]
    assert body["source"] == "blogs"
    assert body["publication_date"] == str(date(2024, 1, 1))
    assert body["word_count"] == 3


def test_list_documents_returns_empty_items_when_no_records(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-empty.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == _empty_list_response()


def test_list_documents_returns_persisted_items(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-list.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    payload = {
        "category": "Ciencia",
        "subcategory": ["vowels"],
        "source": "papers",
        "url": None,
        "publication_year": None,
        "raw_text": "uno dos",
    }

    with TestClient(app) as client:
        create_response = client.post("/documents", json=payload)
        list_response = client.get("/documents")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    body = list_response.json()
    items = body["items"]
    assert len(items) == 1
    assert items[0]["doc_id"].startswith("doc_")
    assert items[0]["subcategory"] == ["vowels"]
    assert items[0]["word_count"] == 2
    assert body["summary"] == {
        "sample_count": 1,
        "total_words": 2,
        "categories": [
            {
                "category": "Ciencia",
                "total_words": 2,
                "percentage": 100.0,
            }
        ],
    }


def test_create_document_rejects_invalid_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "Noticias",
                "source": "noticias",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_create_document_rejects_legacy_doc_id_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-legacy-doc-id.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "doc_id": "doc-legacy",
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
                "raw_text": "uno dos",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_create_document_rejects_blank_subcategory_values_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid-subcategory.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "Noticias",
                "subcategory": ["  ", ""],
                "source": "noticias",
                "raw_text": "uno dos",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_create_document_rejects_blank_raw_text_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid-raw-text.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
                "raw_text": " \n\t ",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_create_document_rejects_noncanonical_category_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid-category.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "Invalid Category",
                "subcategory": ["clauses"],
                "source": "noticias",
                "raw_text": "uno dos",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_create_document_rejects_noncanonical_source_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid-source.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "Tecnología",
                "subcategory": ["verbs"],
                "source": "manual",
                "raw_text": "uno dos",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_create_document_rejects_non_exact_category_label_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid-category-casing.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "tecnología",
                "subcategory": ["clauses"],
                "source": "blogs",
                "raw_text": "uno dos",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_create_document_rejects_non_exact_source_label_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid-source-casing.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "Tecnología",
                "subcategory": ["clauses"],
                "source": "Blogs",
                "raw_text": "uno dos",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_documents_endpoints_fail_when_persistence_is_unavailable(tmp_path: Path) -> None:
    unreachable_url = _sqlite_url(tmp_path / "missing" / "db.sqlite")
    app = create_app(Settings(database_url=unreachable_url))

    with TestClient(app) as client:
        create_response = client.post(
            "/documents",
            json={
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
                "url": None,
                "publication_year": None,
                "raw_text": "uno",
            },
        )
        list_response = client.get("/documents")

    assert create_response.status_code == 503
    assert list_response.status_code == 503


def test_documents_create_and_list_on_postgres_when_available(
    migrated_postgres_database_url: str,
) -> None:
    app = create_app(Settings(database_url=migrated_postgres_database_url))

    payload = {
        "category": "Literatura",
        "subcategory": ["Clauses", "DEPENDENT"],
        "source": "novelas",
        "url": "https://example.com/doc-pg-001",
        "publication_year": 2025,
        "raw_text": "uno dos tres cuatro",
    }

    with TestClient(app) as client:
        create_response = client.post("/documents", json=payload)
        list_response = client.get("/documents")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["doc_id"].startswith("doc_")
    assert items[0]["subcategory"] == ["clauses", "dependent"]
    assert items[0]["publication_date"] == str(date(2025, 1, 1))
    assert items[0]["word_count"] == 4


def test_documents_detail_route_is_not_available(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-no-detail-route.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.get("/documents/some-id")

    assert response.status_code == 404


def test_upload_pdf_creates_document_from_extracted_text_without_auth(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "documents-upload-success.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    def _fake_extract_pdf_text(
        content: bytes,
        *,
        filename: str | None,
        content_type: str | None,
    ) -> str:
        assert content == _pdf_bytes()
        assert filename == "sample.pdf"
        assert content_type == "application/pdf"
        return "uno dos tres"

    monkeypatch.setattr(
        "apps.backend.app.api.routes.documents.extract_pdf_text",
        _fake_extract_pdf_text,
    )

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "category": "Tecnología",
                "subcategory": ["Verbs", "Mood"],
                "source": "blogs",
                "url": "https://example.com/doc-upload-001",
                "publication_year": "2025",
            },
            files={"file": ("sample.pdf", _pdf_bytes(), "application/pdf")},
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 201
    body = upload_response.json()
    assert body["doc_id"].startswith("doc_")
    assert body["subcategory"] == ["verbs", "mood"]
    assert body["publication_date"] == str(date(2025, 1, 1))
    assert body["word_count"] == 3
    assert "file" not in body
    assert "file_reference" not in body
    assert "original_file" not in body
    assert list_response.status_code == 200
    assert len(list_response.json()["items"]) == 1


def test_upload_pdf_rejects_wrong_media_type_without_partial_persistence(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "documents-upload-wrong-media.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
            },
            files={"file": ("sample.txt", b"plain text", "text/plain")},
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 415
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_upload_pdf_rejects_missing_file_without_partial_persistence(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-upload-missing-file.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
            },
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_upload_pdf_rejects_corrupt_pdf_without_partial_persistence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "documents-upload-corrupt.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    def _raise_corrupt_pdf_error(
        _content: bytes,
        *,
        filename: str | None,
        content_type: str | None,
    ) -> str:
        assert filename == "broken.pdf"
        assert content_type == "application/pdf"
        raise CorruptPdfError("Uploaded PDF is corrupt or unreadable")

    monkeypatch.setattr(
        "apps.backend.app.api.routes.documents.extract_pdf_text",
        _raise_corrupt_pdf_error,
    )

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
            },
            files={"file": ("broken.pdf", _pdf_bytes(), "application/pdf")},
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_upload_pdf_rejects_empty_extraction_without_partial_persistence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "documents-upload-empty.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    def _raise_empty_pdf_text_error(
        _content: bytes,
        *,
        filename: str | None,
        content_type: str | None,
    ) -> str:
        assert filename == "image-only.pdf"
        assert content_type == "application/pdf"
        raise EmptyPdfTextError("PDF has no extractable text; OCR is not supported")

    monkeypatch.setattr(
        "apps.backend.app.api.routes.documents.extract_pdf_text",
        _raise_empty_pdf_text_error,
    )

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
            },
            files={"file": ("image-only.pdf", _pdf_bytes(), "application/pdf")},
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_upload_pdf_rejects_legacy_doc_id_without_partial_persistence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "documents-upload-legacy-doc-id.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    monkeypatch.setattr(
        "apps.backend.app.api.routes.documents.extract_pdf_text",
        lambda *_args, **_kwargs: "uno dos",
    )

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "doc_id": "doc-upload-legacy",
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
            },
            files={"file": ("first.pdf", _pdf_bytes(), "application/pdf")},
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_upload_pdf_rejects_invalid_metadata_without_partial_persistence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "documents-upload-invalid-metadata.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    monkeypatch.setattr(
        "apps.backend.app.api.routes.documents.extract_pdf_text",
        lambda *_args, **_kwargs: "uno dos",
    )

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "category": "Noticias",
                "subcategory": ["  ", ""],
                "source": "noticias",
            },
            files={"file": ("sample.pdf", _pdf_bytes(), "application/pdf")},
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()


def test_upload_pdf_rejects_unexpected_form_fields_without_partial_persistence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "documents-upload-unexpected-field.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    monkeypatch.setattr(
        "apps.backend.app.api.routes.documents.extract_pdf_text",
        lambda *_args, **_kwargs: "uno dos",
    )

    with TestClient(app) as client:
        upload_response = client.post(
            "/documents/upload-pdf",
            data={
                "category": "Noticias",
                "subcategory": ["verbs"],
                "source": "noticias",
                "publication_date": "2025-03-10",
            },
            files={"file": ("sample.pdf", _pdf_bytes(), "application/pdf")},
        )
        list_response = client.get("/documents")

    assert upload_response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == _empty_list_response()
