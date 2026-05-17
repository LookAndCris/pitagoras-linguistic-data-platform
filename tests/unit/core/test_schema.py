from sqlalchemy import Integer, String, Text

from packages.core.schema import DocumentMetadata


def test_document_metadata_includes_manual_ingestion_columns() -> None:
    columns = DocumentMetadata.__table__.c

    assert "raw_text" in columns
    assert "word_count" in columns
    assert isinstance(columns.raw_text.type, Text)
    assert isinstance(columns.word_count.type, Integer)


def test_document_metadata_stores_subcategory_as_required_text() -> None:
    subcategory = DocumentMetadata.__table__.c.subcategory

    assert isinstance(subcategory.type, Text)
    assert type(subcategory.type) is Text
    assert subcategory.nullable is False
