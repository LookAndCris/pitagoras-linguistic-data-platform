from collections.abc import Sequence
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.models.document import DocumentMetadata
from packages.models.schemas import DocumentSummary, PersistDocumentRequest
from packages.services.document_service import DuplicateDocumentError


def _serialize_subcategory(values: list[str]) -> str:
    return json.dumps(values)


def _deserialize_subcategory(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return [value]
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return parsed
    return [value]


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: PersistDocumentRequest) -> DocumentSummary:
        entity = DocumentMetadata(
            doc_id=payload.doc_id,
            category=payload.category,
            subcategory=_serialize_subcategory(payload.subcategory),
            source=payload.source,
            url=str(payload.url) if payload.url is not None else None,
            publication_date=payload.publication_date,
            raw_text=payload.raw_text,
            word_count=len(payload.raw_text.split(" ")),
        )
        try:
            self._session.add(entity)
            self._session.commit()
            self._session.refresh(entity)
        except IntegrityError as exc:
            self._session.rollback()
            raise DuplicateDocumentError("Document with this doc_id already exists") from exc

        return self._to_summary(entity)

    def list(self) -> Sequence[DocumentSummary]:
        stmt = select(DocumentMetadata).order_by(DocumentMetadata.created_at.asc())
        entities = self._session.execute(stmt).scalars().all()
        return [self._to_summary(entity) for entity in entities]

    def _to_summary(self, entity: DocumentMetadata) -> DocumentSummary:
        return DocumentSummary(
            id=entity.id,
            doc_id=entity.doc_id,
            category=entity.category,
            subcategory=_deserialize_subcategory(entity.subcategory),
            source=entity.source,
            url=entity.url,
            publication_date=entity.publication_date,
            word_count=entity.word_count or 0,
            created_at=entity.created_at,
        )
