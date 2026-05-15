from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.models.document import DocumentMetadata
from packages.models.schemas import CreateDocumentRequest


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, payload: CreateDocumentRequest) -> DocumentMetadata:
        entity = DocumentMetadata(
            doc_id=payload.doc_id,
            category=payload.category,
            subcategory=payload.subcategory,
            source=payload.source,
            url=str(payload.url) if payload.url is not None else None,
            publication_date=payload.publication_date,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def list(self) -> Sequence[DocumentMetadata]:
        stmt = select(DocumentMetadata).order_by(DocumentMetadata.created_at.asc())
        return self._session.execute(stmt).scalars().all()
