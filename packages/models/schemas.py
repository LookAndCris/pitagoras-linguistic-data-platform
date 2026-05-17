from datetime import date, datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class CreateDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    subcategory: list[str]
    source: str
    url: AnyHttpUrl | None = None
    publication_year: int | None = None
    raw_text: str


class PersistDocumentRequest(BaseModel):
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


class MetadataOptionsResponse(BaseModel):
    categories: list[str]
    sources: list[str]


class PdfUploadMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    subcategory: list[str]
    source: str
    url: AnyHttpUrl | None = None
    publication_year: int | None = None

    def to_create_document_request(self, raw_text: str) -> CreateDocumentRequest:
        return CreateDocumentRequest(
            category=self.category,
            subcategory=self.subcategory,
            source=self.source,
            url=self.url,
            publication_year=self.publication_year,
            raw_text=raw_text,
        )
