from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from apps.backend.app.main import create_app
from packages.core.settings import Settings


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path}"


def _upgrade_to_head(database_url: str) -> None:
    alembic_cfg = Config("apps/backend/alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


def test_create_document_metadata_returns_created_item(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-create.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    payload = {
        "doc_id": "doc-100",
        "category": "grammar",
        "subcategory": "verbs",
        "source": "manual",
        "url": "https://example.com/doc-100",
        "publication_date": str(date(2024, 12, 1)),
    }

    with TestClient(app) as client:
        response = client.post("/documents", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["doc_id"] == "doc-100"
    assert body["category"] == "grammar"
    assert body["source"] == "manual"


def test_list_documents_returns_empty_items_when_no_records(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-empty.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_list_documents_returns_persisted_items(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-list.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    payload = {
        "doc_id": "doc-101",
        "category": "phonetics",
        "subcategory": None,
        "source": "manual",
        "url": None,
        "publication_date": None,
    }

    with TestClient(app) as client:
        create_response = client.post("/documents", json=payload)
        list_response = client.get("/documents")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["doc_id"] == "doc-101"


def test_create_document_rejects_invalid_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "documents-invalid.sqlite"
    database_url = _sqlite_url(db_path)
    _upgrade_to_head(database_url)
    app = create_app(Settings(database_url=database_url))

    with TestClient(app) as client:
        response = client.post(
            "/documents",
            json={
                "category": "grammar",
                "source": "manual",
            },
        )
        list_response = client.get("/documents")

    assert response.status_code == 422
    assert list_response.status_code == 200
    assert list_response.json() == {"items": []}


def test_documents_endpoints_fail_when_persistence_is_unavailable(tmp_path: Path) -> None:
    unreachable_url = _sqlite_url(tmp_path / "missing" / "db.sqlite")
    app = create_app(Settings(database_url=unreachable_url))

    with TestClient(app) as client:
        create_response = client.post(
            "/documents",
            json={
                "doc_id": "doc-999",
                "category": "grammar",
                "subcategory": None,
                "source": "manual",
                "url": None,
                "publication_date": None,
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
        "doc_id": "doc-pg-001",
        "category": "syntax",
        "subcategory": "clauses",
        "source": "manual",
        "url": "https://example.com/doc-pg-001",
        "publication_date": str(date(2025, 1, 15)),
    }

    with TestClient(app) as client:
        create_response = client.post("/documents", json=payload)
        list_response = client.get("/documents")

    assert create_response.status_code == 201
    assert list_response.status_code == 200
    items = list_response.json()["items"]
    assert len(items) == 1
    assert items[0]["doc_id"] == "doc-pg-001"
