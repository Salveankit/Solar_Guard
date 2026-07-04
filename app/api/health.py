from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.database.session import check_database_ready

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    database_status = "not_configured"
    if settings.database_url:
        database_status = "ready" if check_database_ready() else "unavailable"

    return {
        "status": "ok" if database_status in {"ready", "not_configured"} else "degraded",
        "api_version": settings.api_version,
        "database": database_status,
        "model": "not_loaded",
        "configuration_version": settings.configuration_version,
    }

