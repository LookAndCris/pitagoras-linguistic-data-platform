from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path}"


def _alembic_config(database_url: str) -> Config:
    cfg = Config("apps/backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def _upgrade(database_url: str, revision: str) -> None:
    command.upgrade(_alembic_config(database_url), revision)


def test_initial_migration_creates_documents_table(tmp_path: Path) -> None:
    db_path = tmp_path / "bootstrap.sqlite"
    database_url = _sqlite_url(db_path)

    _upgrade(database_url, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    columns = {column["name"] for column in inspector.get_columns("documents")}

    assert {
        "id",
        "doc_id",
        "category",
        "subcategory",
        "source",
        "url",
        "publication_date",
        "created_at",
        "updated_at",
    }.issubset(columns)


def test_fresh_database_has_no_documents_table_before_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "premigration.sqlite"
    database_url = _sqlite_url(db_path)
    engine = create_engine(database_url)
    inspector = inspect(engine)

    assert "documents" not in inspector.get_table_names()


def test_postgres_readiness_prerequisite_fails_before_upgrade(
    postgres_database_url: str,
) -> None:
    engine = create_engine(postgres_database_url)
    inspector = inspect(engine)

    assert "documents" not in inspector.get_table_names()


def test_postgres_readiness_prerequisite_passes_after_upgrade(
    migrated_postgres_database_url: str,
) -> None:
    engine = create_engine(migrated_postgres_database_url)
    inspector = inspect(engine)

    assert "documents" in inspector.get_table_names()


def test_head_migration_adds_manual_ingestion_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "manual-ingestion-columns.sqlite"
    database_url = _sqlite_url(db_path)

    _upgrade(database_url, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("documents")}

    assert "raw_text" in columns
    assert "word_count" in columns
    assert columns["subcategory"]["nullable"] is False


def test_head_migration_converts_legacy_scalar_subcategory_to_json_array(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-subcategory-scalar.sqlite"
    database_url = _sqlite_url(db_path)

    _upgrade(database_url, "0001_document_metadata")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO documents (
                    id, doc_id, category, subcategory, source, url, publication_date, created_at, updated_at
                ) VALUES (
                    :id, :doc_id, :category, :subcategory, :source, :url, :publication_date, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "doc_id": "doc-legacy-1",
                "category": "grammar",
                "subcategory": "verbs",
                "source": "manual",
                "url": None,
                "publication_date": None,
            },
        )

    _upgrade(database_url, "head")

    with engine.begin() as connection:
        migrated = connection.execute(
            text("SELECT subcategory FROM documents WHERE doc_id = :doc_id"),
            {"doc_id": "doc-legacy-1"},
        ).scalar_one()

    assert migrated == '["verbs"]'


def test_head_migration_backfills_null_subcategory_to_default_json_array(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy-subcategory-null.sqlite"
    database_url = _sqlite_url(db_path)

    _upgrade(database_url, "0001_document_metadata")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO documents (
                    id, doc_id, category, subcategory, source, url, publication_date, created_at, updated_at
                ) VALUES (
                    :id, :doc_id, :category, :subcategory, :source, :url, :publication_date, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "doc_id": "doc-legacy-2",
                "category": "grammar",
                "subcategory": None,
                "source": "manual",
                "url": None,
                "publication_date": None,
            },
        )

    _upgrade(database_url, "head")

    with engine.begin() as connection:
        migrated = connection.execute(
            text("SELECT subcategory FROM documents WHERE doc_id = :doc_id"),
            {"doc_id": "doc-legacy-2"},
        ).scalar_one()

    assert migrated == '["unspecified"]'
