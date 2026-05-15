from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from packages.models.schemas import CreateDocumentRequest, DocumentSummary
from packages.services.document_service import DocumentService, PersistenceUnavailableError


class InMemoryRepository:
    def __init__(self) -> None:
        self.items: list[DocumentSummary] = []

    def create(self, payload: CreateDocumentRequest) -> DocumentSummary:
        item = DocumentSummary(
            id=uuid4(),
            doc_id=payload.doc_id,
            category=payload.category,
            subcategory=payload.subcategory,
            source=payload.source,
            url=payload.url,
            publication_date=payload.publication_date,
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


def test_create_document_returns_created_summary() -> None:
    service = DocumentService(InMemoryRepository())

    created = service.create_document(
        CreateDocumentRequest(
            doc_id="doc-001",
            category="grammar",
            subcategory="verbs",
            source="manual",
            url="https://example.com/doc-001",
            publication_date=date(2025, 1, 10),
        )
    )

    assert created.doc_id == "doc-001"
    assert created.category == "grammar"
    assert created.subcategory == "verbs"
    assert created.source == "manual"


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
            subcategory=None,
            source="manual",
            url=None,
            publication_date=None,
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
                subcategory=None,
                source="manual",
                url=None,
                publication_date=None,
            )
        )


def test_list_documents_raises_persistence_error_when_repository_fails() -> None:
    service = DocumentService(FailingRepository())

    with pytest.raises(PersistenceUnavailableError):
        service.list_documents()
