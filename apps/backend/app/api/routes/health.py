from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.core.dependencies import get_db_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def readiness(db_session: Session = Depends(get_db_session)) -> dict[str, str]:
    try:
        db_session.execute(text("SELECT 1"))
        if not inspect(db_session.bind).has_table("documents"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Database schema is not ready",
            )
        return {"status": "ok"}
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not ready",
        ) from exc
