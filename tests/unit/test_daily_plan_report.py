from __future__ import annotations

import csv
from io import StringIO

from app.services.reports import DailyPlanReportService


def _route_plan() -> dict:
    return {
        "planning_date": "2026-07-05",
        "field_plan": [
            {
                "technician_id": "TECH-01",
                "technician_name": "Asha Patil",
                "stops": [
                    {
                        "sequence": 1,
                        "arrival": "2026-07-05T09:18:00+05:30",
                        "job": {
                            "site_id": "MH-119",
                            "queue_rank": 1,
                            "probable_issue": "probable inverter or grid-side interruption",
                            "confidence_score": 89.0,
                            "priority_label": "High",
                            "recommended_action": "physical technical inspection",
                            "escalation_condition": "dispatch if unresolved",
                            "duration_min": 90,
                            "estimated_energy_loss_kwh": 31.0,
                            "recoverable_energy_kwh": 23.0,
                            "recoverable_value_inr": 184.0,
                        },
                    }
                ],
            }
        ],
        "remote_action_queue": [
            {
                "site_id": "MH-126",
                "queue_rank": 3,
                "probable_issue": "communication or data-logger failure",
                "confidence_score": 78.0,
                "priority_label": "Medium",
                "recommended_action": "remote connectivity check",
                "visit_required": False,
                "estimated_energy_loss_kwh": 0.0,
                "estimated_recoverable_energy_kwh": 0.0,
                "estimated_recoverable_value_inr": 0.0,
            }
        ],
        "monitoring_queue": [
            {
                "site_id": "MH-121",
                "probable_issue": "probable recurring shade or obstruction",
                "priority_label": "Low",
                "recommended_action": "monitor",
                "visit_required": False,
            }
        ],
        "unassigned_jobs": [],
    }


def test_daily_plan_report_contains_field_remote_and_monitoring_rows() -> None:
    body = DailyPlanReportService().build_csv(_route_plan())
    rows = list(csv.DictReader(StringIO(body)))

    assert [row["work_category"] for row in rows] == [
        "field_visit",
        "remote_action",
        "monitoring_or_deferred",
    ]
    assert rows[0]["technician"] == "Asha Patil"
    assert rows[0]["site_id"] == "MH-119"
    assert rows[1]["visit_required"] == "False"


def test_daily_plan_report_enriches_field_rows_from_decisions() -> None:
    plan = _route_plan()
    plan["field_plan"][0]["stops"][0]["job"].pop("confidence_score")
    plan["field_plan"][0]["stops"][0]["job"].pop("estimated_energy_loss_kwh")

    body = DailyPlanReportService().build_csv(
        plan,
        [
            {
                "site_id": "MH-119",
                "confidence_score": 91.0,
                "estimated_energy_loss_kwh": 33.5,
            }
        ],
    )
    rows = list(csv.DictReader(StringIO(body)))

    assert rows[0]["confidence"] == "91.0"
    assert rows[0]["historical_loss_kwh"] == "33.5"


def test_daily_plan_report_does_not_expose_ground_truth() -> None:
    body = DailyPlanReportService().build_csv(_route_plan()).lower()

    assert "fault_ground_truth" not in body
    assert "scenario_validation_expected" not in body
    assert "actual_fault" not in body
