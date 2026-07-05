from __future__ import annotations

from datetime import date, timedelta
from typing import Any

DISCLOSURE_TEXT = (
    "SolarGuard POC uses synthetic but operationally realistic rooftop-solar data. "
    "Results demonstrate workflow and engineering capability, not production-validated "
    "fault accuracy."
)


def tomorrow_iso(today: date | None = None) -> str:
    base = today or date.today()
    return (base + timedelta(days=1)).isoformat()


def split_service_queue(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    field = [
        item
        for item in items
        if bool(item.get("actionable")) and bool(item.get("visit_required"))
    ]
    remote = [
        item
        for item in items
        if bool(item.get("actionable"))
        and not bool(item.get("visit_required"))
        and bool(item.get("remote_action_available"))
    ]
    monitoring = [
        item
        for item in items
        if not bool(item.get("visit_required")) and item not in remote
    ]
    return {"field": field, "remote": remote, "monitoring": monitoring}


def route_stop_site_ids(route_plan: dict[str, Any]) -> list[str]:
    site_ids = []
    for route in route_plan.get("field_plan", []):
        for stop in route.get("stops", []):
            job = stop.get("job", {})
            site_ids.append(str(job.get("site_id") or stop.get("site_id") or ""))
    return [site_id for site_id in site_ids if site_id]


def zero_distance_message(route_plan: dict[str, Any]) -> str | None:
    avoided = float(route_plan.get("distance_avoided_km") or 0)
    if round(avoided, 3) != 0:
        return None
    return (
        "The optimiser produced a feasible skill-aware route. In this four-job scenario, "
        "reversing either technician's two-stop closed route does not change total "
        "Haversine distance."
    )


def format_inr(value: Any) -> str:
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def format_kwh(value: Any) -> str:
    try:
        return f"{float(value):,.2f} kWh"
    except (TypeError, ValueError):
        return "0.00 kWh"


def format_bool(value: Any) -> str:
    return "Yes" if bool(value) else "No"
