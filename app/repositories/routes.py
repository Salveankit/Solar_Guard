from __future__ import annotations

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Connection


class RouteRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def read_field_decisions(self, analysis_run_id: str) -> list[dict]:
        rows = self.connection.execute(
            text(
                """
                SELECT sd.*, s.latitude, s.longitude, s.service_region,
                       (
                           SELECT min(sh.sla_due_at)
                           FROM service_history sh
                           WHERE sh.site_id = sd.site_id AND sh.resolved_at IS NULL
                       ) AS escalation_deadline
                FROM service_decisions sd
                JOIN sites s ON s.site_id = sd.site_id
                WHERE sd.analysis_run_id = :analysis_run_id
                  AND sd.actionable = true
                  AND sd.visit_required = true
                ORDER BY sd.queue_rank, sd.site_id
                """
            ),
            {"analysis_run_id": analysis_run_id},
        ).mappings()
        return [dict(row) for row in rows]

    def read_technicians(self) -> list[dict]:
        rows = self.connection.execute(
            text(
                """
                SELECT technician_id, technician_name, start_latitude, start_longitude,
                       shift_start, shift_end, maximum_visits, skill_set, region, active
                FROM technicians ORDER BY technician_id
                """
            )
        ).mappings()
        return [dict(row) for row in rows]

    def read_plan(self, route_plan_id: str) -> dict | None:
        plan = self.connection.execute(
            text("SELECT * FROM route_plans WHERE route_plan_id = :route_plan_id"),
            {"route_plan_id": route_plan_id},
        ).mappings().first()
        if plan is None:
            return None
        stops = self.connection.execute(
            text(
                """
                SELECT * FROM route_stops
                WHERE route_plan_id = :route_plan_id
                ORDER BY technician_id, stop_order
                """
            ),
            {"route_plan_id": route_plan_id},
        ).mappings()
        result = dict(plan)
        result["stops"] = [dict(row) for row in stops]
        return result

    def latest_plan(self) -> dict | None:
        plan_id = self.connection.execute(
            text("SELECT route_plan_id FROM route_plans ORDER BY created_at DESC LIMIT 1")
        ).scalar_one_or_none()
        return self.read_plan(plan_id) if plan_id else None

    def replace_plan(
        self,
        route_plan_id: str,
        analysis_run_id: str,
        planning_date: date,
        jobs: list[dict],
        result: dict,
    ) -> None:
        self.connection.execute(
            text("DELETE FROM route_stops WHERE route_plan_id = :route_plan_id"),
            {"route_plan_id": route_plan_id},
        )
        self.connection.execute(
            text("DELETE FROM route_plans WHERE route_plan_id = :route_plan_id"),
            {"route_plan_id": route_plan_id},
        )
        self.connection.execute(
            text("DELETE FROM service_jobs WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        self._insert_jobs(analysis_run_id, jobs, result)
        created_at = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
        self.connection.execute(
            text(
                """
                INSERT INTO route_plans (
                    route_plan_id, analysis_run_id, plan_date, created_at, summary_json,
                    optimisation_status, failure_reason, total_eligible_jobs,
                    assigned_jobs, unassigned_jobs, naive_distance_km,
                    optimised_distance_km, distance_avoided_km,
                    total_travel_duration_min, total_job_duration_min,
                    total_recoverable_energy_kwh, total_recoverable_value_inr,
                    naive_routes, unassigned_job_details
                ) VALUES (
                    :route_plan_id, :analysis_run_id, :plan_date, :created_at,
                    CAST(:summary_json AS JSON), :optimisation_status, :failure_reason,
                    :total_eligible_jobs, :assigned_jobs, :unassigned_jobs,
                    :naive_distance_km, :optimised_distance_km, :distance_avoided_km,
                    :total_travel_duration_min, :total_job_duration_min,
                    :total_recoverable_energy_kwh, :total_recoverable_value_inr,
                    CAST(:naive_routes AS JSON), CAST(:unassigned_job_details AS JSON)
                )
                """
            ),
            {
                "route_plan_id": route_plan_id,
                "analysis_run_id": analysis_run_id,
                "plan_date": planning_date,
                "created_at": created_at,
                "summary_json": json.dumps(result, default=self._json_default),
                "optimisation_status": result["optimisation_status"],
                "failure_reason": result["failure_reason"],
                "total_eligible_jobs": len(jobs),
                "assigned_jobs": len(result["stops"]),
                "unassigned_jobs": len(result["unassigned_jobs"]),
                "naive_distance_km": result["naive_distance_km"],
                "optimised_distance_km": result["optimised_distance_km"],
                "distance_avoided_km": result["distance_avoided_km"],
                "total_travel_duration_min": result["total_travel_duration_min"],
                "total_job_duration_min": result["total_job_duration_min"],
                "total_recoverable_energy_kwh": result["total_recoverable_energy_kwh"],
                "total_recoverable_value_inr": result["total_recoverable_value_inr"],
                "naive_routes": json.dumps(result["naive_routes"]),
                "unassigned_job_details": json.dumps(result["unassigned_jobs"]),
            },
        )
        self._insert_stops(route_plan_id, result["stops"])

    def read_work_lists(self, analysis_run_id: str) -> dict:
        rows = self.connection.execute(
            text(
                """
                SELECT decision_id, site_id, probable_issue, recommended_action,
                       actionable, remote_action_available, visit_required,
                       priority_score, priority_label
                FROM service_decisions WHERE analysis_run_id = :analysis_run_id
                ORDER BY queue_rank NULLS LAST, site_id
                """
            ),
            {"analysis_run_id": analysis_run_id},
        ).mappings()
        remote = []
        monitoring = []
        for row in rows:
            item = dict(row)
            if item["actionable"] and not item["visit_required"] and (
                "connectivity" in item["recommended_action"]
                or "diagnostic" in item["recommended_action"]
            ):
                remote.append(item)
            elif not item["visit_required"]:
                monitoring.append(item)
        return {"remote_action_queue": remote, "monitoring_queue": monitoring}

    def _insert_jobs(self, analysis_run_id: str, jobs: list[dict], result: dict) -> None:
        assigned = {stop["job"]["decision_id"] for stop in result["stops"]}
        unassigned = {
            item["decision_id"]: item["reason"] for item in result["unassigned_jobs"]
        }
        statement = text(
            """
            INSERT INTO service_jobs (
                job_id, analysis_run_id, site_id, job_type, required_skill,
                priority_score, estimated_duration_min, earliest_visit, latest_visit,
                selected_for_route, decision_id, candidate_id, latitude, longitude,
                priority_label, probable_issue, recommended_action, required_skills,
                recoverable_energy_kwh, recoverable_value_inr
            ) VALUES (
                :job_id, :analysis_run_id, :site_id, :job_type, :required_skill,
                :priority_score, :estimated_duration_min, :earliest_visit, :latest_visit,
                :selected_for_route, :decision_id, :candidate_id, :latitude, :longitude,
                :priority_label, :probable_issue, :recommended_action,
                CAST(:required_skills AS JSON), :recoverable_energy_kwh,
                :recoverable_value_inr
            )
            """
        )
        rows = []
        for job in jobs:
            rows.append(
                {
                    **job,
                    "job_id": f"JOB-{job['decision_id'][3:]}",
                    "analysis_run_id": analysis_run_id,
                    "job_type": "field_service",
                    "required_skill": ";".join(job["required_skills"]),
                    "required_skills": json.dumps(job["required_skills"]),
                    "estimated_duration_min": job["duration_min"],
                    "earliest_visit": job["earliest_service_time"],
                    "latest_visit": job["escalation_deadline"],
                    "selected_for_route": job["decision_id"] in assigned,
                    "unassigned_reason": unassigned.get(job["decision_id"]),
                }
            )
        if rows:
            self.connection.execute(statement, rows)

    def _insert_stops(self, route_plan_id: str, stops: list[dict]) -> None:
        statement = text(
            """
            INSERT INTO route_stops (
                route_plan_id, technician_id, stop_order, site_id, job_id,
                distance_from_previous_km, estimated_arrival, decision_id,
                estimated_departure, travel_duration_min, job_duration_min,
                probable_issue, recommended_action, priority_score, priority_label,
                required_skills
            ) VALUES (
                :route_plan_id, :technician_id, :stop_order, :site_id, :job_id,
                :distance_from_previous_km, :estimated_arrival, :decision_id,
                :estimated_departure, :travel_duration_min, :job_duration_min,
                :probable_issue, :recommended_action, :priority_score, :priority_label,
                CAST(:required_skills AS JSON)
            )
            """
        )
        rows = []
        for stop in stops:
            job = stop["job"]
            rows.append(
                {
                    "route_plan_id": route_plan_id,
                    "technician_id": stop["technician_id"],
                    "stop_order": stop["sequence"],
                    "site_id": job["site_id"],
                    "job_id": f"JOB-{job['decision_id'][3:]}",
                    "distance_from_previous_km": stop["travel_distance_km"],
                    "estimated_arrival": stop["arrival"],
                    "decision_id": job["decision_id"],
                    "estimated_departure": stop["departure"],
                    "travel_duration_min": stop["travel_duration_min"],
                    "job_duration_min": job["duration_min"],
                    "probable_issue": job["probable_issue"],
                    "recommended_action": job["recommended_action"],
                    "priority_score": job["priority_score"],
                    "priority_label": job["priority_label"],
                    "required_skills": json.dumps(job["required_skills"]),
                }
            )
        if rows:
            self.connection.execute(statement, rows)

    @staticmethod
    def _json_default(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        raise TypeError(f"Unsupported JSON type: {type(value).__name__}")
