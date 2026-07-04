from __future__ import annotations

from dataclasses import asdict
from datetime import date

from sqlalchemy.engine import Connection

from app.repositories.routes import RouteRepository
from app.repositories.service_decisions import ServiceDecisionRepository
from app.services.route_optimization import (
    RouteOptimizer,
    RoutingJob,
    TechnicianResource,
    deterministic_route_plan_id,
)


class RoutePlanningService:
    def __init__(self, connection: Connection, config: dict) -> None:
        self.repository = RouteRepository(connection)
        self.decisions = ServiceDecisionRepository(connection)
        self.config = config
        self.routing_config = config.get("routing", {})

    def optimize(
        self,
        planning_date: date,
        analysis_run_id: str | None = None,
        replace_existing_plan: bool = True,
    ) -> dict:
        run_id = analysis_run_id or self.decisions.latest_decision_run_id()
        if not run_id:
            raise ValueError("No persisted service-decision run is available")
        plan_id = deterministic_route_plan_id(run_id, planning_date)
        existing = self.repository.read_plan(plan_id)
        if existing and not replace_existing_plan:
            return self._persisted_response(existing)
        decision_rows = self.repository.read_field_decisions(run_id)
        technician_rows = self.repository.read_technicians()
        available_skills = self._available_skills(technician_rows)
        jobs = [self._job(row, available_skills) for row in decision_rows]
        technicians = [self._technician(row) for row in technician_rows]
        result = RouteOptimizer(self.config).optimize(jobs, technicians, planning_date)
        job_rows = [asdict(job) for job in jobs]
        self.repository.replace_plan(plan_id, run_id, planning_date, job_rows, result)
        return self._response(plan_id, run_id, planning_date, result)

    def latest(self) -> dict | None:
        plan = self.repository.latest_plan()
        return self._persisted_response(plan) if plan else None

    def _response(
        self,
        plan_id: str,
        analysis_run_id: str,
        planning_date: date,
        result: dict,
    ) -> dict:
        work_lists = self.repository.read_work_lists(analysis_run_id)
        return {
            "route_plan_id": plan_id,
            "analysis_run_id": analysis_run_id,
            "planning_date": planning_date,
            "optimisation_status": result["optimisation_status"],
            "failure_reason": result["failure_reason"],
            "field_plan": result["routes"],
            **work_lists,
            "unassigned_jobs": result["unassigned_jobs"],
            "naive_routes": result["naive_routes"],
            "naive_distance_km": result["naive_distance_km"],
            "optimised_distance_km": result["optimised_distance_km"],
            "distance_avoided_km": result["distance_avoided_km"],
            "total_travel_duration_min": result["total_travel_duration_min"],
            "total_job_duration_min": result["total_job_duration_min"],
            "total_recoverable_energy_kwh": result["total_recoverable_energy_kwh"],
            "total_recoverable_value_inr": result["total_recoverable_value_inr"],
        }

    def _persisted_response(self, plan: dict) -> dict:
        result = dict(plan.get("summary_json") or {})
        return self._response(
            plan["route_plan_id"],
            plan["analysis_run_id"],
            plan["plan_date"],
            result,
        )

    def _job(self, row: dict, available_skills: set[str]) -> RoutingJob:
        required_skills, duration = self._requirements(row)
        absent = set(required_skills) - available_skills
        if absent:
            required_skills = tuple(sorted(set(required_skills) | absent))
        return RoutingJob(
            decision_id=row["decision_id"],
            candidate_id=row["incident_candidate_id"],
            site_id=row["site_id"],
            latitude=self._coordinate(row.get("latitude")),
            longitude=self._coordinate(row.get("longitude")),
            priority_score=float(row["priority_score"]),
            priority_label=row["priority_label"],
            probable_issue=row["probable_issue"],
            recommended_action=row["recommended_action"],
            required_skills=required_skills,
            duration_min=duration,
            recoverable_energy_kwh=float(row["estimated_recoverable_energy_kwh"]),
            recoverable_value_inr=float(row["estimated_recoverable_value_inr"]),
            escalation_deadline=row.get("escalation_deadline"),
            earliest_service_time=None,
        )

    def _requirements(self, row: dict) -> tuple[tuple[str, ...], int]:
        issue = row["probable_issue"]
        durations = self.routing_config.get("job_duration_minutes", {})
        if "inverter or grid" in issue:
            return ("electrical", "inverter"), int(
                durations.get("inverter_grid_interruption", 90)
            )
        if "shade or obstruction" in issue:
            return ("site_inspection",), int(durations.get("recurring_obstruction", 60))
        if "degradation" in issue or "soiling" in issue:
            skills = ["site_inspection"]
            if row["recommended_action"] == "schedule cleaning":
                skills.append("cleaning")
            return tuple(skills), int(durations.get("persistent_degradation", 90))
        return ("electrical",), int(self.routing_config.get("default_job_duration_min", 60))

    @staticmethod
    def _technician(row: dict) -> TechnicianResource:
        skills = frozenset(
            item.strip() for item in str(row["skill_set"]).split(";") if item.strip()
        )
        return TechnicianResource(
            technician_id=row["technician_id"],
            latitude=float(row["start_latitude"]),
            longitude=float(row["start_longitude"]),
            shift_start=row["shift_start"],
            shift_end=row["shift_end"],
            maximum_visits=int(row["maximum_visits"]),
            skills=skills,
            region=row["region"],
            active=bool(row["active"]),
        )

    @staticmethod
    def _available_skills(rows: list[dict]) -> set[str]:
        return {
            skill.strip()
            for row in rows
            for skill in str(row["skill_set"]).split(";")
            if skill.strip()
        }

    @staticmethod
    def _coordinate(value) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return float("nan")
