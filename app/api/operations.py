from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.database.session import get_engine
from app.services.operations_query import OperationsQueryService

router = APIRouter(prefix="/api", tags=["operations"])


@router.get("/fleet/summary")
def fleet_summary() -> dict:
    with get_engine().connect() as connection:
        return OperationsQueryService(connection).fleet_summary()


@router.get("/sites")
def list_sites() -> list[dict]:
    with get_engine().connect() as connection:
        return OperationsQueryService(connection).sites()


@router.get("/sites/{site_id}")
def get_site(site_id: str) -> dict:
    with get_engine().connect() as connection:
        result = OperationsQueryService(connection).site(site_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return result


@router.get("/sites/{site_id}/diagnostics")
def get_site_diagnostics(site_id: str) -> dict:
    with get_engine().connect() as connection:
        result = OperationsQueryService(connection).diagnostics(site_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Site not found")
    return result


@router.get("/service-queue")
def service_queue(
    priority: str | None = None,
    probable_issue: str | None = None,
    remote_action: bool | None = None,
    cleaning_candidate: bool | None = None,
    field_visit: bool | None = None,
    insufficient_evidence: bool | None = None,
    actionable_only: bool = Query(default=False),
) -> dict:
    with get_engine().connect() as connection:
        result = OperationsQueryService(connection).service_queue(
            priority=priority,
            probable_issue=probable_issue,
            remote_action=remote_action,
            cleaning_candidate=cleaning_candidate,
            field_visit=field_visit,
            insufficient_evidence=insufficient_evidence,
            actionable_only=actionable_only,
        )
    return result
