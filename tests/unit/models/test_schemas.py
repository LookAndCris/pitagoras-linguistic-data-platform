from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.models.schemas import (
    CreateDocumentRequest,
    DocumentSummary,
    MetadataOptionsResponse,
    PdfUploadMetadata,
)


def test_create_document_request_requires_raw_text_and_list_subcategory() -> None:
    with pytest.raises(ValidationError):
        CreateDocumentRequest(
            category="Noticias",
            source="noticias",
            raw_text="texto",
        )

    with pytest.raises(ValidationError):
        CreateDocumentRequest(
            category="Noticias",
            subcategory="verbs",
            source="noticias",
            raw_text="texto",
        )


def test_create_document_request_forbids_legacy_fields() -> None:
    with pytest.raises(ValidationError):
        CreateDocumentRequest(
            doc_id="doc-001",
            category="Noticias",
            subcategory=["verbs"],
            source="noticias",
            raw_text="texto",
        )

    with pytest.raises(ValidationError):
        CreateDocumentRequest(
            category="Noticias",
            subcategory=["verbs"],
            source="noticias",
            publication_date="2024-12-01",
            raw_text="texto",
        )


def test_create_document_request_accepts_publication_year_and_raw_text() -> None:
    payload = CreateDocumentRequest(
        category="Tecnología",
        subcategory=["verbs", "conjugation"],
        source="blogs",
        url="https://example.com/documents/1",
        publication_year=2024,
        raw_text="Uno dos tres",
    )

    assert payload.subcategory == ["verbs", "conjugation"]
    assert payload.publication_year == 2024
    assert payload.raw_text == "Uno dos tres"


def test_document_summary_requires_word_count_and_list_subcategory() -> None:
    with pytest.raises(ValidationError):
        DocumentSummary(
            id=uuid4(),
            doc_id="doc-001",
            category="Noticias",
            subcategory=["verbs"],
            source="noticias",
            url="https://example.com/doc-001",
            publication_date=date(2024, 12, 1),
            created_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError):
        DocumentSummary(
            id=uuid4(),
            doc_id="doc-001",
            category="Noticias",
            subcategory="verbs",
            source="noticias",
            url="https://example.com/doc-001",
            publication_date=date(2024, 12, 1),
            word_count=3,
            created_at=datetime.now(UTC),
        )


def test_metadata_options_response_requires_lists() -> None:
    payload = MetadataOptionsResponse(categories=["Noticias", "Ciencia"], sources=["noticias", "papers"])

    assert payload.categories == ["Noticias", "Ciencia"]
    assert payload.sources == ["noticias", "papers"]


def test_pdf_upload_metadata_to_create_document_request_maps_fields() -> None:
    metadata = PdfUploadMetadata(
        category="Tecnología",
        subcategory=["verbs", "tense"],
        source="blogs",
        url="https://example.com/documents/7",
        publication_year=2024,
    )

    payload = metadata.to_create_document_request(raw_text="Extracted PDF text")

    assert isinstance(payload, CreateDocumentRequest)
    assert payload.category == "Tecnología"
    assert payload.subcategory == ["verbs", "tense"]
    assert payload.source == "blogs"
    assert str(payload.url) == "https://example.com/documents/7"
    assert payload.publication_year == 2024
    assert payload.raw_text == "Extracted PDF text"


def test_pdf_upload_metadata_requires_list_subcategory() -> None:
    with pytest.raises(ValidationError):
        PdfUploadMetadata(
            category="Noticias",
            subcategory="verbs",
            source="noticias",
        )


def test_pdf_upload_metadata_forbids_legacy_doc_id_field() -> None:
    with pytest.raises(ValidationError):
        PdfUploadMetadata(
            doc_id="doc-008",
            category="Noticias",
            subcategory=["verbs"],
            source="noticias",
        )
