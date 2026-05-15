from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def _sqlite_url(db_path: Path) -> str:
    return f"sqlite+pysqlite:///{db_path}"


def _alembic_config(database_url: str) -> Config:
    cfg = Config("apps/backend/alembic.ini")
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def test_initial_migration_creates_documents_table(tmp_path: Path) -> None:
    db_path = tmp_path / "bootstrap.sqlite"
    database_url = _sqlite_url(db_path)

    command.upgrade(_alembic_config(database_url), "head")

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
