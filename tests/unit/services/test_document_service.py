import re
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from packages.models.schemas import CreateDocumentRequest, DocumentSummary
from packages.services.document_service import (
    CANONICAL_CATEGORIES,
    CANONICAL_SOURCES,
    DocumentService,
    DocumentValidationError,
    DuplicateDocumentError,
    PersistenceUnavailableError,
    generate_doc_id,
)


class InMemoryRepository:
    def __init__(self) -> None:
        self.items: list[DocumentSummary] = []
        self.last_payload = None

    def create(self, payload) -> DocumentSummary:
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
    def create(self, payload) -> DocumentSummary:  # pragma: no cover
        raise RuntimeError("db down")

    def list(self) -> list[DocumentSummary]:
        raise RuntimeError("db down")


class DuplicateFailingRepository:
    def create(self, payload) -> DocumentSummary:  # pragma: no cover
        raise DuplicateDocumentError("Document with this doc_id already exists")

    def list(self) -> list[DocumentSummary]:
        return []


def test_generate_doc_id_returns_prefixed_ulid_shape() -> None:
    generated = generate_doc_id()

    assert re.fullmatch(r"doc_[0-9A-HJKMNP-TV-Z]{26}", generated) is not None


def test_create_document_returns_created_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "packages.services.document_service.generate_doc_id",
        lambda: "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV",
    )
    repository = InMemoryRepository()
    service = DocumentService(repository)

    created = service.create_document(
        CreateDocumentRequest(
            category="Tecnología",
            subcategory=["  Verbs  ", "Mood"],
            source="blogs",
            url="https://example.com/doc-001",
            publication_year=2025,
            raw_text="  Uno   dos\n\ttres  ",
        )
    )

    assert created.doc_id == "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert created.category == "Tecnología"
    assert created.subcategory == ["verbs", "mood"]
    assert created.source == "blogs"
    assert created.publication_date == date(2025, 1, 1)
    assert created.word_count == 3
    assert repository.last_payload is not None
    assert repository.last_payload.subcategory == ["verbs", "mood"]
    assert repository.last_payload.raw_text == "Uno dos tres"
    assert repository.last_payload.doc_id == "doc_01ARZ3NDEKTSV4RRFFQ69G5FAV"
    assert repository.last_payload.publication_date == date(2025, 1, 1)


def test_get_metadata_options_returns_canonical_values() -> None:
    service = DocumentService(InMemoryRepository())

    options = service.get_metadata_options()

    assert options.categories == list(CANONICAL_CATEGORIES)
    assert options.sources == list(CANONICAL_SOURCES)


def test_create_document_returns_created_summary() -> None:
    repository = InMemoryRepository()
    service = DocumentService(repository)

    created = service.create_document(
        CreateDocumentRequest(
            category="Tecnología",
            subcategory=["  verbs  ", "mood"],
            source="blogs",
            url="https://example.com/doc-001",
            publication_year=2025,
            raw_text="  Uno   dos\n\ttres  ",
        )
    )

    assert created.doc_id.startswith("doc_")
    assert created.category == "Tecnología"
    assert created.subcategory == ["verbs", "mood"]
    assert created.source == "blogs"
    assert created.publication_date == date(2025, 1, 1)
    assert created.word_count == 3
    assert repository.last_payload is not None
    assert repository.last_payload.subcategory == ["verbs", "mood"]
    assert repository.last_payload.raw_text == "Uno dos tres"


def test_list_documents_returns_empty_collection() -> None:
    service = DocumentService(InMemoryRepository())

    listed = service.list_documents()

    assert listed == []


def test_list_documents_returns_existing_documents(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "packages.services.document_service.generate_doc_id",
        lambda: "doc_01ARZ3NDEKTSV4RRFFQ69G5FAA",
    )
    repository = InMemoryRepository()
    service = DocumentService(repository)
    service.create_document(
        CreateDocumentRequest(
            category="Ciencia",
            subcategory=["vowels"],
            source="papers",
            url=None,
            raw_text="uno dos",
        )
    )

    listed = service.list_documents()

    assert len(listed) == 1
    assert listed[0].doc_id == "doc_01ARZ3NDEKTSV4RRFFQ69G5FAA"


def test_create_document_raises_persistence_error_when_repository_fails() -> None:
    service = DocumentService(FailingRepository())

    with pytest.raises(PersistenceUnavailableError):
        service.create_document(
            CreateDocumentRequest(
                category="Noticias",
                subcategory=["verbs"],
                source="noticias",
                url=None,
                raw_text="uno",
            )
        )


def test_create_document_raises_validation_error_for_blank_raw_text() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError):
        service.create_document(
            CreateDocumentRequest(
                category="Noticias",
                subcategory=["verbs"],
                source="noticias",
                raw_text="   \n\t",
            )
        )


def test_create_document_raises_validation_error_for_empty_subcategory_items() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError):
        service.create_document(
            CreateDocumentRequest(
                category="Noticias",
                subcategory=["  ", ""],
                source="noticias",
                raw_text="uno dos",
            )
        )


def test_create_document_lowercases_subcategory_before_persistence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "packages.services.document_service.generate_doc_id",
        lambda: "doc_01ARZ3NDEKTSV4RRFFQ69G5FAB",
    )
    repository = InMemoryRepository()
    service = DocumentService(repository)

    created = service.create_document(
        CreateDocumentRequest(
            category="Literatura",
            subcategory=[" Clauses ", "DEPENDENT"],
            source="novelas",
            raw_text="uno dos",
        )
    )

    assert created.subcategory == ["clauses", "dependent"]
    assert repository.last_payload is not None
    assert repository.last_payload.subcategory == ["clauses", "dependent"]


def test_create_document_rejects_noncanonical_category() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError, match="category must be one of"):
        service.create_document(
            CreateDocumentRequest(
                category="Invalid Category",
                subcategory=["verbs"],
                source="noticias",
                raw_text="uno dos",
            )
        )


def test_create_document_rejects_noncanonical_source() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError, match="source must be one of"):
        service.create_document(
            CreateDocumentRequest(
                category="Tecnología",
                subcategory=["verbs"],
                source="manual",
                raw_text="uno dos",
            )
        )


def test_create_document_rejects_non_exact_category_label() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError, match="category must be one of"):
        service.create_document(
            CreateDocumentRequest(
                category="tecnología",
                subcategory=["verbs"],
                source="blogs",
                raw_text="uno dos",
            )
        )


def test_create_document_rejects_non_exact_source_label() -> None:
    service = DocumentService(InMemoryRepository())

    with pytest.raises(DocumentValidationError, match="source must be one of"):
        service.create_document(
            CreateDocumentRequest(
                category="Tecnología",
                subcategory=["verbs"],
                source="Blogs",
                raw_text="uno dos",
            )
        )


def test_create_document_raises_duplicate_error_when_repository_reports_duplicate() -> None:
    service = DocumentService(DuplicateFailingRepository())

    with pytest.raises(DuplicateDocumentError):
        service.create_document(
            CreateDocumentRequest(
                category="Noticias",
                subcategory=["verbs"],
                source="noticias",
                raw_text="uno dos",
            )
        )


def test_list_documents_raises_persistence_error_when_repository_fails() -> None:
    service = DocumentService(FailingRepository())

    with pytest.raises(PersistenceUnavailableError):
        service.list_documents()
