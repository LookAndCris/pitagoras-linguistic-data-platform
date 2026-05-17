from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from packages.core.dependencies import get_db_session
from packages.models.schemas import (
    CreateDocumentRequest,
    DocumentSummary,
    ListDocumentsResponse,
    PdfUploadMetadata,
)
from packages.repositories.document_repository import DocumentRepository
from packages.services.document_service import (
    DocumentService,
    DocumentValidationError,
    DuplicateDocumentError,
    PersistenceUnavailableError,
)
from packages.services.pdf_ingestion import (
    CorruptPdfError,
    EmptyPdfTextError,
    UnsupportedPdfError,
    extract_pdf_text,
)

router = APIRouter(prefix="/documents", tags=["documents"])


def _build_service(db_session: Session) -> DocumentService:
    return DocumentService(DocumentRepository(db_session))


def _parse_upload_metadata(
    doc_id: str = Form(...),
    category: str = Form(...),
    subcategory: list[str] = Form(...),
    source: str = Form(...),
    url: str | None = Form(default=None),
    publication_date: str | None = Form(default=None),
) -> PdfUploadMetadata:
    try:
        return PdfUploadMetadata(
            doc_id=doc_id,
            category=category,
            subcategory=subcategory,
            source=source,
            url=url,
            publication_date=publication_date,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        ) from exc


def _raise_service_http_errors(exc: Exception) -> None:
    if isinstance(exc, DocumentValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    if isinstance(exc, DuplicateDocumentError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    if isinstance(exc, PersistenceUnavailableError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document persistence is unavailable",
        ) from exc


@router.post("", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: CreateDocumentRequest,
    db_session: Session = Depends(get_db_session),
) -> DocumentSummary:
    service = _build_service(db_session)
    try:
        return service.create_document(payload)
    except (DocumentValidationError, DuplicateDocumentError, PersistenceUnavailableError) as exc:
        _raise_service_http_errors(exc)
        raise


@router.get("", response_model=ListDocumentsResponse)
def list_documents(db_session: Session = Depends(get_db_session)) -> ListDocumentsResponse:
    service = _build_service(db_session)
    try:
        return ListDocumentsResponse(items=service.list_documents())
    except PersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document persistence is unavailable",
        ) from exc


@router.post("/upload-pdf", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_pdf_document(
    file: UploadFile = File(...),
    metadata: PdfUploadMetadata = Depends(_parse_upload_metadata),
    db_session: Session = Depends(get_db_session),
) -> DocumentSummary:
    service = _build_service(db_session)
    content = await file.read()

    try:
        raw_text = extract_pdf_text(content, filename=file.filename, content_type=file.content_type)
        payload = metadata.to_create_document_request(raw_text=raw_text)
        return service.create_document(payload)
    except UnsupportedPdfError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except (CorruptPdfError, EmptyPdfTextError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except (DocumentValidationError, DuplicateDocumentError, PersistenceUnavailableError) as exc:
        _raise_service_http_errors(exc)
        raise
    finally:
        await file.close()
