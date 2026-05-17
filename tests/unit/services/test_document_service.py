from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from packages.models.schemas import CreateDocumentRequest, DocumentSummary
from packages.services.document_service import (
    DocumentService,
    DocumentValidationError,
    DuplicateDocumentError,
    PersistenceUnavailableError,
)


class InMemoryRepository:
    def __init__(self) -> None:
        self.items: list[DocumentSummary] = []
        self.last_payload: CreateDocumentRequest | None = None

    def create(self, payload: CreateDocumentRequest) -> DocumentSummary:
        self.last_payload = payload
        item = DocumentSummary(
            id=uuid4(),
            doc_id=payload.doc_id,
            category=payload.category,
            subcategory=payload.subcategory,
            source=payload.source,
            url=payload.url,
            publication_date=payload.publication_date,
            word_count=len(payload.raw_text.split(" ")),
            created_at=datetime.now(UTC),
        )
        self.items.append(item)
        return item

    def list(self) -> list[DocumentSummary]:
        return list(self.items)


class FailingRepository:
    def create(self, payload: CreateDocumentRequest) -> DocumentSummary:  # pragma: no cover
        raise RuntimeError("db down")

    def list(self) -> list[DocumentSummary]:
        raise RuntimeError("db down")


class DuplicateFailingRepository:
    def create(self, payload: CreateDocumentRequest) -> DocumentSummary:  # pragma: no cover
        raise DuplicateDocumentError("Document with this doc_id already exists")

    def list(self) -> list[DocumentSummary]:
        return []


def test_create_document_returns_created_summary() -> None:
    repository = InMemoryRepository()
    service = DocumentService(repository)

    created = service.create_document(
        CreateDocumentRequest(
            doc_id="doc-001",
            category="grammar",
            subcategory=["  verbs  ", "mood"],
            source="manual",
            url="https://example.com/doc-001",
            publication_date=date(2025, 1, 10),
            raw_text="  Uno   dos\n\ttres  ",
        )
    )

    assert created.doc_id == "doc-001"
    assert created.category == "grammar"
    assert created.subcategory == ["verbs", "mood"]
    assert created.source == "manual"
    assert created.word_count == 3
    assert repository.last_payload is not None
    assert repository.last_payload.subcategory == ["verbs", "mood"]
    assert repository.last_payload.raw_text == "Uno dos tres"


def test_list_documents_returns_empty_collection() -> None:
    service = DocumentService(InMemoryRepository())

    listed = service.list_documents()

    assert listed == []


def test_list_documents_returns_existing_documents() -> None:
    repository = InMemoryRepository()
    service = DocumentService(repository)
    service.create_document(
        CreateDocumentRequest(
            doc_id="doc-002",
            category="phonetics",
            subcategory=["vowels"],
            source="manual",
            url=None,
            publication_date=None,
            raw_text="uno dos",
        )
    )

    listed = service.list_documents()

    assert len(listed) == 1
    assert listed[0].doc_id == "doc-002"


def test_create_document_raises_persistence_error_when_repository_fails() -> None:
    service = DocumentService(FailingRepository())

    with pytest.raises(PersistenceUnavailableError):
        service.create_document(
            CreateDocumentRequest(
                doc_id="doc-003",
                category="grammar",
                subcategory=["verbs"],
                source="manual",
                url=None,
                publication_date=None,
                raw_text="uno",
            )
        )


def test_create_document_raises_validation_error_for_blank_raw_text() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError):
        service.create_document(
            CreateDocumentRequest(
                doc_id="doc-004",
                category="grammar",
                subcategory=["verbs"],
                source="manual",
                raw_text="   \n\t",
            )
        )


def test_create_document_raises_validation_error_for_empty_subcategory_items() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError):
        service.create_document(
            CreateDocumentRequest(
                doc_id="doc-005",
                category="grammar",
                subcategory=["  ", ""],
                source="manual",
                raw_text="uno dos",
            )
        )


def test_create_document_raises_duplicate_error_when_repository_reports_duplicate() -> None:
    service = DocumentService(DuplicateFailingRepository())

    with pytest.raises(DuplicateDocumentError):
        service.create_document(
            CreateDocumentRequest(
                doc_id="doc-001",
                category="grammar",
                subcategory=["verbs"],
                source="manual",
                raw_text="uno dos",
            )
        )


def test_create_document_rejects_datetime_publication_date_as_invalid_value() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError):
        service.create_document(
            CreateDocumentRequest.model_construct(
                doc_id="doc-006",
                category="grammar",
                subcategory=["verbs"],
                source="manual",
                raw_text="uno dos",
                publication_date=datetime.now(UTC),
            )
        )


def test_list_documents_raises_persistence_error_when_repository_fails() -> None:
    service = DocumentService(FailingRepository())

    with pytest.raises(PersistenceUnavailableError):
        service.list_documents()
