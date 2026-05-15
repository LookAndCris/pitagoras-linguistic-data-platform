from collections.abc import Sequence
from typing import Protocol

from packages.models.document import DocumentMetadata
from packages.models.schemas import CreateDocumentRequest, DocumentSummary


class PersistenceUnavailableError(Exception):
    pass


class DocumentRepositoryPort(Protocol):
    def create(self, payload: CreateDocumentRequest) -> DocumentMetadata | DocumentSummary: ...

    def list(self) -> Sequence[DocumentMetadata | DocumentSummary]: ...


class DocumentService:
    def __init__(self, repository: DocumentRepositoryPort) -> None:
        self._repository = repository

    def create_document(self, payload: CreateDocumentRequest) -> DocumentSummary:
        try:
            created = self._repository.create(payload)
            return DocumentSummary.model_validate(created)
        except Exception as exc:  # noqa: BLE001
            raise PersistenceUnavailableError("Document persistence is unavailable") from exc

    def list_documents(self) -> list[DocumentSummary]:
        try:
            items = self._repository.list()
            return [DocumentSummary.model_validate(item) for item in items]
        except Exception as exc:  # noqa: BLE001
            raise PersistenceUnavailableError("Document persistence is unavailable") from exc
