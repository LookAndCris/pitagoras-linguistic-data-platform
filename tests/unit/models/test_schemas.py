from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from packages.models.schemas import CreateDocumentRequest, DocumentSummary, PdfUploadMetadata


def test_create_document_request_requires_raw_text_and_list_subcategory() -> None:
    with pytest.raises(ValidationError):
        CreateDocumentRequest(
            doc_id="doc-001",
            category="grammar",
            source="manual",
            raw_text="texto",
        )

    with pytest.raises(ValidationError):
        CreateDocumentRequest(
            doc_id="doc-001",
            category="grammar",
            subcategory="verbs",
            source="manual",
            raw_text="texto",
        )


def test_create_document_request_accepts_list_subcategory_and_raw_text() -> None:
    payload = CreateDocumentRequest(
        doc_id="doc-001",
        category="grammar",
        subcategory=["verbs", "conjugation"],
        source="manual",
        url="https://example.com/doc-001",
        publication_date=date(2024, 12, 1),
        raw_text="Uno dos tres",
    )

    assert payload.subcategory == ["verbs", "conjugation"]
    assert payload.raw_text == "Uno dos tres"


def test_document_summary_requires_word_count_and_list_subcategory() -> None:
    with pytest.raises(ValidationError):
        DocumentSummary(
            id=uuid4(),
            doc_id="doc-001",
            category="grammar",
            subcategory=["verbs"],
            source="manual",
            url="https://example.com/doc-001",
            publication_date=date(2024, 12, 1),
            created_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError):
        DocumentSummary(
            id=uuid4(),
            doc_id="doc-001",
            category="grammar",
            subcategory="verbs",
            source="manual",
            url="https://example.com/doc-001",
            publication_date=date(2024, 12, 1),
            word_count=3,
            created_at=datetime.now(UTC),
        )


def test_pdf_upload_metadata_to_create_document_request_maps_fields() -> None:
    metadata = PdfUploadMetadata(
        doc_id="doc-007",
        category="grammar",
        subcategory=["verbs", "tense"],
        source="uploaded-pdf",
        url="https://example.com/doc-007",
        publication_date=date(2024, 1, 10),
    )

    payload = metadata.to_create_document_request(raw_text="Extracted PDF text")

    assert isinstance(payload, CreateDocumentRequest)
    assert payload.doc_id == "doc-007"
    assert payload.category == "grammar"
    assert payload.subcategory == ["verbs", "tense"]
    assert payload.source == "uploaded-pdf"
    assert str(payload.url) == "https://example.com/doc-007"
    assert payload.publication_date == date(2024, 1, 10)
    assert payload.raw_text == "Extracted PDF text"


def test_pdf_upload_metadata_requires_list_subcategory() -> None:
    with pytest.raises(ValidationError):
        PdfUploadMetadata(
            doc_id="doc-008",
            category="grammar",
            subcategory="verbs",
            source="uploaded-pdf",
        )
