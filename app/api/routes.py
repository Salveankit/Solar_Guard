from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings
from app.database.session import get_engine
from app.services.route_planning import RoutePlanningService

router = APIRouter(prefix="/api/routes", tags=["routes"])


class OptimizeRouteRequest(BaseModel):
    planning_date: date
    analysis_run_id: str | None = None
    replace_existing_plan: bool = True


@router.post("/optimize")
def optimize_routes(request: OptimizeRouteRequest) -> dict:
    settings = get_settings()
    try:
        with get_engine().begin() as connection:
            return RoutePlanningService(connection, settings.config).optimize(
                planning_date=request.planning_date,
                analysis_run_id=request.analysis_run_id,
                replace_existing_plan=request.replace_existing_plan,
            )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/latest")
def latest_route() -> dict:
    settings = get_settings()
    with get_engine().connect() as connection:
        result = RoutePlanningService(connection, settings.config).latest()
    if result is None:
        raise HTTPException(status_code=404, detail="No route plan is available")
    return result
