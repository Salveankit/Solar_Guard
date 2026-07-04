from __future__ import annotations

from datetime import date, time

import pytest

from app.services.route_optimization import (
    RouteOptimizer,
    RoutingJob,
    TechnicianResource,
    deterministic_route_plan_id,
    haversine_km,
)

CONFIG = {
    "routing": {
        "average_speed_kmph": 30,
        "drop_penalty_base": 100000,
        "drop_penalty_priority_multiplier": 5000,
        "solver_time_limit_seconds": 1,
    }
}


def _job(
    site_id: str,
    latitude: float,
    longitude: float,
    skills: tuple[str, ...],
    priority: float = 70,
    duration: int = 60,
) -> RoutingJob:
    return RoutingJob(
        decision_id=f"SD-{site_id}",
        candidate_id=f"IC-{site_id}",
        site_id=site_id,
        latitude=latitude,
        longitude=longitude,
        priority_score=priority,
        priority_label="High",
        probable_issue="probable issue",
        recommended_action="physical technical inspection",
        required_skills=skills,
        duration_min=duration,
        recoverable_energy_kwh=5,
        recoverable_value_inr=40,
        escalation_deadline=None,
    )


def _technician(
    technician_id: str,
    latitude: float,
    longitude: float,
    skills: set[str],
    maximum_visits: int = 4,
    shift_end: time = time(18, 0),
    active: bool = True,
) -> TechnicianResource:
    return TechnicianResource(
        technician_id=technician_id,
        latitude=latitude,
        longitude=longitude,
        shift_start=time(9, 0),
        shift_end=shift_end,
        maximum_visits=maximum_visits,
        skills=frozenset(skills),
        region="Pune",
        active=active,
    )


def test_haversine_distance_is_symmetric_and_zero_for_same_point() -> None:
    first = (18.52043, 73.856744)
    second = (18.565954, 73.925067)

    assert haversine_km(first, first) == 0
    assert haversine_km(first, second) == pytest.approx(
        haversine_km(second, first), rel=1e-12
    )


def test_optimizer_respects_skills_and_assigns_each_job_once() -> None:
    technicians = [
        _technician("TECH-01", 18.52, 73.85, {"electrical", "inverter"}),
        _technician("TECH-02", 18.55, 73.93, {"site_inspection", "cleaning"}),
    ]
    jobs = [
        _job("MH-107", 18.54, 73.88, ("electrical", "inverter"), 80, 90),
        _job("MH-109", 18.60, 73.78, ("site_inspection",), 60, 60),
    ]

    result = RouteOptimizer(CONFIG).optimize(jobs, technicians, date(2026, 7, 5))

    assert result["optimisation_status"] == "optimized"
    assigned = [stop["job"] for stop in result["stops"]]
    assert len(assigned) == len({job["decision_id"] for job in assigned}) == 2
    by_site = {stop["job"]["site_id"]: stop["technician_id"] for stop in result["stops"]}
    assert by_site == {"MH-107": "TECH-01", "MH-109": "TECH-02"}
    assert all(
        route["job_duration_min"] + route["travel_duration_min"] <= 540
        for route in result["routes"]
    )


def test_maximum_visits_and_unassigned_reason_are_respected() -> None:
    technicians = [_technician("TECH-01", 18.52, 73.85, {"electrical"}, maximum_visits=1)]
    jobs = [
        _job("MH-101", 18.53, 73.86, ("electrical",), priority=80),
        _job("MH-102", 18.54, 73.87, ("electrical",), priority=70),
    ]

    result = RouteOptimizer(CONFIG).optimize(jobs, technicians, date(2026, 7, 5))

    assert len(result["stops"]) == 1
    assert result["unassigned_jobs"][0]["reason"] == "maximum visit capacity reached"


def test_no_matching_skill_is_reported() -> None:
    technicians = [_technician("TECH-01", 18.52, 73.85, {"electrical"})]
    job = _job("MH-109", 18.60, 73.78, ("site_inspection",))

    result = RouteOptimizer(CONFIG).optimize([job], technicians, date(2026, 7, 5))

    assert not result["stops"]
    assert result["unassigned_jobs"] == [
        {
            "decision_id": "SD-MH-109",
            "site_id": "MH-109",
            "reason": "no technician with required skill",
        }
    ]


def test_inactive_technician_receives_no_job() -> None:
    technicians = [
        _technician("TECH-01", 18.52, 73.85, {"electrical"}, active=False)
    ]
    job = _job("MH-101", 18.53, 73.86, ("electrical",))

    result = RouteOptimizer(CONFIG).optimize([job], technicians, date(2026, 7, 5))

    assert not result["stops"]
    assert result["unassigned_jobs"][0]["reason"] == "no technician with required skill"


def test_invalid_coordinates_and_missing_duration_have_explicit_reasons() -> None:
    technician = _technician("TECH-01", 18.52, 73.85, {"electrical"})
    jobs = [
        _job("MH-101", 180.0, 73.86, ("electrical",)),
        _job("MH-102", 18.54, 73.87, ("electrical",), duration=0),
    ]

    result = RouteOptimizer(CONFIG).optimize(jobs, [technician], date(2026, 7, 5))

    reasons = {item["site_id"]: item["reason"] for item in result["unassigned_jobs"]}
    assert reasons == {
        "MH-101": "invalid coordinates",
        "MH-102": "missing duration estimate",
    }


def test_shift_time_infeasible_job_is_reported() -> None:
    technicians = [
        _technician("TECH-01", 18.52, 73.85, {"electrical"}, shift_end=time(10, 0))
    ]
    job = _job("MH-101", 18.80, 74.10, ("electrical",), duration=90)

    result = RouteOptimizer(CONFIG).optimize([job], technicians, date(2026, 7, 5))

    assert not result["stops"]
    assert result["unassigned_jobs"][0]["reason"] == "shift-time infeasible"


def test_fallback_preserves_constraints(monkeypatch: pytest.MonkeyPatch) -> None:
    optimizer = RouteOptimizer(CONFIG)
    technician = _technician("TECH-01", 18.52, 73.85, {"electrical"})
    job = _job("MH-101", 18.53, 73.86, ("electrical",))

    def fail_solver(*_args, **_kwargs):
        raise RuntimeError("forced")

    monkeypatch.setattr(optimizer, "_solve_ortools", fail_solver)
    result = optimizer.optimize([job], [technician], date(2026, 7, 5))

    assert result["optimisation_status"] == "fallback"
    assert result["stops"][0]["job"]["site_id"] == "MH-101"
    assert result["failure_reason"] == "OR-Tools unavailable or failed: RuntimeError"


def test_naive_and_optimized_distance_use_same_hub_return_definition() -> None:
    technician = _technician("TECH-01", 18.52, 73.85, {"electrical"})
    jobs = [
        _job("MH-101", 18.53, 73.90, ("electrical",), priority=80),
        _job("MH-102", 18.54, 73.87, ("electrical",), priority=70),
    ]

    result = RouteOptimizer(CONFIG).optimize(jobs, [technician], date(2026, 7, 5))

    assert result["naive_distance_km"] >= result["optimised_distance_km"]
    assert result["distance_avoided_km"] == pytest.approx(
        result["naive_distance_km"] - result["optimised_distance_km"], abs=0.001
    )
    assert [stop["sequence"] for stop in result["stops"]] == [1, 2]


def test_route_plan_id_is_deterministic() -> None:
    first = deterministic_route_plan_id("RUN-TEST", date(2026, 7, 5))
    second = deterministic_route_plan_id("RUN-TEST", date(2026, 7, 5))

    assert first == second
