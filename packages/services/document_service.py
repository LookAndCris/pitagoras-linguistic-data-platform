from collections.abc import Sequence
from datetime import date
import secrets
import time
from typing import Protocol

from packages.models.document import DocumentMetadata
from packages.models.schemas import (
    CreateDocumentRequest,
    DocumentSummary,
    MetadataOptionsResponse,
    PersistDocumentRequest,
)

CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
CANONICAL_CATEGORIES = (
    "Noticias",
    "Tecnología",
    "Negocios",
    "Ciencia",
    "Salud",
    "Deportes",
    "Entretenimiento",
    "Literatura",
    "Redes Sociales",
    "Lifestyle",
    "Política",
    "Académico",
)
CANONICAL_SOURCES = (
    "papers",
    "noticias",
    "blogs",
    "redes sociales",
    "entrevistas",
    "podcasts",
    "documentación",
    "novelas",
)


class PersistenceUnavailableError(Exception):
    pass


class DocumentValidationError(Exception):
    pass


class DuplicateDocumentError(Exception):
    pass


def _encode_crockford(value: int, length: int) -> str:
    encoded: list[str] = []
    remaining = value
    for _ in range(length):
        encoded.append(CROCKFORD_BASE32[remaining & 31])
        remaining >>= 5
    return "".join(reversed(encoded))


def generate_doc_id() -> str:
    timestamp_ms = int(time.time() * 1000)
    randomness = secrets.randbits(80)
    ulid = _encode_crockford(timestamp_ms, 10) + _encode_crockford(randomness, 16)
    return f"doc_{ulid}"


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _normalize_subcategory(values: list[str]) -> list[str]:
    normalized = [_normalize_whitespace(item).lower() for item in values]
    normalized = [item for item in normalized if item]
    if not normalized:
        raise DocumentValidationError("subcategory must contain at least one non-blank value")
    return normalized


def _derive_word_count(raw_text: str) -> int:
    return len(raw_text.split(" ")) if raw_text else 0


def _normalize_publication_date(publication_year: int | None) -> date | None:
    if publication_year is None:
        return None
    try:
        return date(publication_year, 1, 1)
    except ValueError as exc:
        raise DocumentValidationError("publication_year must be a valid year") from exc


def _validate_canonical_value(field_name: str, value: str, allowed_values: tuple[str, ...]) -> str:
    normalized = _normalize_whitespace(value)
    if normalized not in allowed_values:
        allowed = ", ".join(allowed_values)
        raise DocumentValidationError(f"{field_name} must be one of: {allowed}")
    return normalized


class DocumentRepositoryPort(Protocol):
    def create(self, payload: PersistDocumentRequest) -> DocumentMetadata | DocumentSummary: ...

    def list(self) -> Sequence[DocumentMetadata | DocumentSummary]: ...


class DocumentService:
    def __init__(self, repository: DocumentRepositoryPort) -> None:
        self._repository = repository

    def get_metadata_options(self) -> MetadataOptionsResponse:
        return MetadataOptionsResponse(
            categories=list(CANONICAL_CATEGORIES),
            sources=list(CANONICAL_SOURCES),
        )

    def create_document(self, payload: CreateDocumentRequest) -> DocumentSummary:
        try:
            normalized_text = _normalize_whitespace(payload.raw_text)
            if not normalized_text:
                raise DocumentValidationError("raw_text cannot be blank")

            normalized_category = _validate_canonical_value(
                "category",
                payload.category,
                CANONICAL_CATEGORIES,
            )
            normalized_subcategory = _normalize_subcategory(payload.subcategory)
            normalized_source = _validate_canonical_value(
                "source",
                payload.source,
                CANONICAL_SOURCES,
            )
            normalized_publication_date = _normalize_publication_date(payload.publication_year)

            normalized_payload = PersistDocumentRequest(
                doc_id=generate_doc_id(),
                category=normalized_category,
                subcategory=normalized_subcategory,
                source=normalized_source,
                url=payload.url,
                publication_date=normalized_publication_date,
                raw_text=normalized_text,
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
