from collections.abc import Sequence
from datetime import date, datetime
from typing import Protocol

from packages.models.document import DocumentMetadata
from packages.models.schemas import CreateDocumentRequest, DocumentSummary


class PersistenceUnavailableError(Exception):
    pass


class DocumentValidationError(Exception):
    pass


class DuplicateDocumentError(Exception):
    pass


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalize_subcategory(values: list[str]) -> list[str]:
    normalized = [_normalize_whitespace(item) for item in values]
    normalized = [item for item in normalized if item]
    if not normalized:
        raise DocumentValidationError("subcategory must contain at least one non-blank value")
    return normalized


def _derive_word_count(raw_text: str) -> int:
    return len(raw_text.split(" ")) if raw_text else 0


def _validate_publication_date(value: date | None) -> None:
    if isinstance(value, datetime):
        raise DocumentValidationError("publication_date must be a valid date")
    if value is not None and not isinstance(value, date):
        raise DocumentValidationError("publication_date must be a valid date")


class DocumentRepositoryPort(Protocol):
    def create(self, payload: CreateDocumentRequest) -> DocumentMetadata | DocumentSummary: ...

    def list(self) -> Sequence[DocumentMetadata | DocumentSummary]: ...


class DocumentService:
    def __init__(self, repository: DocumentRepositoryPort) -> None:
        self._repository = repository

    def create_document(self, payload: CreateDocumentRequest) -> DocumentSummary:
        try:
            normalized_text = _normalize_whitespace(payload.raw_text)
            if not normalized_text:
                raise DocumentValidationError("raw_text cannot be blank")

            normalized_subcategory = _normalize_subcategory(payload.subcategory)
            _validate_publication_date(payload.publication_date)

            normalized_payload = payload.model_copy(
                update={
                    "raw_text": normalized_text,
                    "subcategory": normalized_subcategory,
                }
            )

            created = self._repository.create(normalized_payload)
            created_summary = DocumentSummary.model_validate(created)
            expected_word_count = _derive_word_count(normalized_text)
            return created_summary.model_copy(update={"word_count": expected_word_count})
        except (DocumentValidationError, DuplicateDocumentError):
            raise
        except Exception as exc:  # noqa: BLE001
            raise PersistenceUnavailableError("Document persistence is unavailable") from exc

    def list_documents(self) -> list[DocumentSummary]:
        try:
            items = self._repository.list()
            return [DocumentSummary.model_validate(item) for item in items]
        except Exception as exc:  # noqa: BLE001
            raise PersistenceUnavailableError("Document persistence is unavailable") from exc
