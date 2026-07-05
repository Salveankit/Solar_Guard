from __future__ import annotations

import csv
from io import StringIO
from typing import Any

REPORT_COLUMNS = [
    "work_category",
    "queue_rank",
    "technician",
    "route_sequence",
    "site_id",
    "probable_issue",
    "confidence",
    "priority",
    "recommended_action",
    "escalation_condition",
    "visit_required",
    "estimated_arrival",
    "job_duration_min",
    "historical_loss_kwh",
    "recoverable_energy_kwh",
    "recoverable_value_inr",
]


class DailyPlanReportService:
    """Builds the user-facing O&M plan from backend-owned route and queue results."""

    def build_csv(
        self,
        route_plan: dict[str, Any],
        decision_items: list[dict[str, Any]] | None = None,
    ) -> str:
        buffer = StringIO()
        writer = csv.DictWriter(buffer, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for row in self._rows(route_plan, decision_items or []):
            writer.writerow(row)
        return buffer.getvalue()

    def _rows(
        self,
        route_plan: dict[str, Any],
        decision_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        decisions_by_site = {item["site_id"]: item for item in decision_items}
        for route in route_plan.get("field_plan", []):
            technician = route.get("technician_name") or route.get("technician_id")
            for stop in route.get("stops", []):
                job = stop.get("job", {})
                decision = decisions_by_site.get(job.get("site_id"), {})
                rows.append(
                    {
                        "work_category": "field_visit",
                        "queue_rank": job.get("queue_rank", decision.get("queue_rank", "")),
                        "technician": technician,
                        "route_sequence": stop.get("sequence", ""),
                        "site_id": job.get("site_id", ""),
                        "probable_issue": job.get("probable_issue", ""),
                        "confidence": job.get(
                            "confidence_score",
                            decision.get("confidence_score", ""),
                        ),
                        "priority": job.get("priority_label", ""),
                        "recommended_action": job.get("recommended_action", ""),
                        "escalation_condition": job.get(
                            "escalation_condition",
                            decision.get("escalation_condition", ""),
                        ),
                        "visit_required": True,
                        "estimated_arrival": self._iso(stop.get("arrival")),
                        "job_duration_min": job.get("duration_min", ""),
                        "historical_loss_kwh": job.get(
                            "estimated_energy_loss_kwh",
                            decision.get("estimated_energy_loss_kwh", ""),
                        ),
                        "recoverable_energy_kwh": job.get("recoverable_energy_kwh", ""),
                        "recoverable_value_inr": job.get("recoverable_value_inr", ""),
                    }
                )
        for item in route_plan.get("remote_action_queue", []):
            rows.append(self._queue_row("remote_action", item))
        for item in route_plan.get("monitoring_queue", []):
            rows.append(self._queue_row("monitoring_or_deferred", item))
        for item in route_plan.get("unassigned_jobs", []):
            rows.append(
                {
                    "work_category": "unassigned_field_job",
                    "site_id": item.get("site_id", ""),
                    "probable_issue": item.get("probable_issue", ""),
                    "priority": item.get("priority_label", ""),
                    "recommended_action": item.get("reason", ""),
                    "visit_required": True,
                }
            )
        return rows

    @staticmethod
    def _queue_row(category: str, item: dict[str, Any]) -> dict[str, Any]:
        return {
            "work_category": category,
            "queue_rank": item.get("queue_rank", ""),
            "site_id": item.get("site_id", ""),
            "probable_issue": item.get("probable_issue", ""),
            "confidence": item.get("confidence_score", ""),
            "priority": item.get("priority_label", ""),
            "recommended_action": item.get("recommended_action", ""),
            "escalation_condition": item.get("escalation_condition", ""),
            "visit_required": bool(item.get("visit_required")),
            "historical_loss_kwh": item.get("estimated_energy_loss_kwh", ""),
            "recoverable_energy_kwh": item.get("estimated_recoverable_energy_kwh", ""),
            "recoverable_value_inr": item.get("estimated_recoverable_value_inr", ""),
        }

    @staticmethod
    def _iso(value: Any) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value or "")
