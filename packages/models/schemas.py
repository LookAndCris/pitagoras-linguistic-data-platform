from datetime import date, datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class CreateDocumentRequest(BaseModel):
    doc_id: str
    category: str
    subcategory: str | None = None
    source: str
    url: AnyHttpUrl | None = None
    publication_date: date | None = None


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doc_id: str
    category: str
    subcategory: str | None
    source: str
    url: AnyHttpUrl | None
    publication_date: date | None
    created_at: datetime


class ListDocumentsResponse(BaseModel):
    items: list[DocumentSummary]
