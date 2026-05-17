from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile as StarletteUploadFile

from packages.core.dependencies import get_db_session
from packages.models.schemas import (
    CreateDocumentRequest,
    DocumentSummary,
    ListDocumentsResponse,
    MetadataOptionsResponse,
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


def _raise_validation_http_error(exc: ValidationError) -> None:
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=exc.errors(),
    ) from exc


def _parse_upload_metadata(form_data: dict[str, object], subcategory: list[str]) -> PdfUploadMetadata:
    try:
        return PdfUploadMetadata(
            category=form_data.get("category"),
            subcategory=subcategory,
            source=form_data.get("source"),
            url=form_data.get("url"),
            publication_year=form_data.get("publication_year"),
        )
    except ValidationError as exc:
        _raise_validation_http_error(exc)


@router.get("/metadata-options", response_model=MetadataOptionsResponse)
def get_metadata_options(db_session: Session = Depends(get_db_session)) -> MetadataOptionsResponse:
    service = _build_service(db_session)
    return service.get_metadata_options()


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
        return service.list_documents()
    except PersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document persistence is unavailable",
        ) from exc


@router.post("/upload-pdf", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
async def upload_pdf_document(
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> DocumentSummary:
    service = _build_service(db_session)
    form = await request.form()

    allowed_keys = {"file", "category", "subcategory", "source", "url", "publication_year"}
    unexpected_keys = sorted(set(form.keys()) - allowed_keys)
    if unexpected_keys:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unexpected multipart fields: {', '.join(unexpected_keys)}",
        )

    upload = form.get("file")
    if not isinstance(upload, StarletteUploadFile):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[{"loc": ["body", "file"], "msg": "Field required", "type": "missing"}],
        )

    metadata = _parse_upload_metadata(dict(form), form.getlist("subcategory"))
    content = await upload.read()

    try:
        raw_text = extract_pdf_text(content, filename=upload.filename, content_type=upload.content_type)
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
        await upload.close()
