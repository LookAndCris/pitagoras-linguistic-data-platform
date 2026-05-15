from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from packages.core.dependencies import get_db_session
from packages.models.schemas import CreateDocumentRequest, DocumentSummary, ListDocumentsResponse
from packages.repositories.document_repository import DocumentRepository
from packages.services.document_service import DocumentService, PersistenceUnavailableError

router = APIRouter(prefix="/documents", tags=["documents"])


def _build_service(db_session: Session) -> DocumentService:
    return DocumentService(DocumentRepository(db_session))


@router.post("", response_model=DocumentSummary, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: CreateDocumentRequest,
    db_session: Session = Depends(get_db_session),
) -> DocumentSummary:
    service = _build_service(db_session)
    try:
        return service.create_document(payload)
    except PersistenceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Document persistence is unavailable",
        ) from exc


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
