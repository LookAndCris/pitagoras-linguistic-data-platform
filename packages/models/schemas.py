from datetime import date, datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class CreateDocumentRequest(BaseModel):
    doc_id: str
    category: str
    subcategory: list[str]
    source: str
    url: AnyHttpUrl | None = None
    publication_date: date | None = None
    raw_text: str


class DocumentSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    doc_id: str
    category: str
    subcategory: list[str]
    source: str
    url: AnyHttpUrl | None
    publication_date: date | None
    word_count: int
    created_at: datetime


class ListDocumentsResponse(BaseModel):
    items: list[DocumentSummary]


class PdfUploadMetadata(BaseModel):
    doc_id: str
    category: str
    subcategory: list[str]
    source: str
    url: AnyHttpUrl | None = None
    publication_date: date | None = None

    def to_create_document_request(self, raw_text: str) -> CreateDocumentRequest:
        return CreateDocumentRequest(
            doc_id=self.doc_id,
            category=self.category,
            subcategory=self.subcategory,
            source=self.source,
            url=self.url,
            publication_date=self.publication_date,
            raw_text=raw_text,
        )
