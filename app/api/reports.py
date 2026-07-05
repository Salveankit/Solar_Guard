from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.config import get_settings
from app.database.session import get_engine
from app.services.operations_query import OperationsQueryService
from app.services.reports import DailyPlanReportService
from app.services.route_planning import RoutePlanningService

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/daily-plan")
def daily_plan(route_plan_id: str | None = None, format: str = "csv") -> Response:
    if format.lower() != "csv":
        raise HTTPException(status_code=400, detail="Only CSV report format is supported")
    settings = get_settings()
    with get_engine().connect() as connection:
        route_service = RoutePlanningService(connection, settings.config)
        if route_plan_id:
            route_plan = route_service.by_id(route_plan_id)
        else:
            route_plan = route_service.latest()
        decisions = OperationsQueryService(connection).service_queue().get("items", [])
    if route_plan is None:
        raise HTTPException(status_code=404, detail="No route plan is available")
    body = DailyPlanReportService().build_csv(route_plan, decisions)
    filename = f"solarguard_daily_plan_{route_plan['planning_date']}.csv"
    return Response(
        content=body,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
