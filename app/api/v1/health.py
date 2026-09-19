"""Liveness and readiness endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.session import get_db
from app.schemas.health import HealthStatus, ReadinessStatus

router = APIRouter(tags=["health"])
log = get_logger(__name__)


@router.get("/health", response_model=HealthStatus)
def health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthStatus:
    """Liveness: the process is up. Never touches dependencies."""
    return HealthStatus(status="ok", environment=settings.goldseats_env, version="0.1.0")


@router.get("/ready", response_model=ReadinessStatus)
def ready(
    response: Response,
    session: Annotated[Session, Depends(get_db)],
) -> ReadinessStatus:
    """Readiness: dependencies this instance needs to serve traffic."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        log.error("readiness_check_failed", dependency="database", error=str(exc))
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessStatus(status="degraded", database=False)

    return ReadinessStatus(status="ok", database=True)
