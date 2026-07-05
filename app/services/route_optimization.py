from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

LOCAL_TIMEZONE = ZoneInfo("Asia/Kolkata")
EARTH_RADIUS_KM = 6371.0088


@dataclass(frozen=True)
class RoutingJob:
    decision_id: str
    candidate_id: str
    site_id: str
    latitude: float
    longitude: float
    priority_score: float
    priority_label: str
    probable_issue: str
    recommended_action: str
    required_skills: tuple[str, ...]
    duration_min: int
    recoverable_energy_kwh: float
    recoverable_value_inr: float
    escalation_deadline: datetime | None
    earliest_service_time: datetime | None = None
    queue_rank: int | None = None
    confidence_score: float | None = None
    estimated_energy_loss_kwh: float | None = None
    escalation_condition: str | None = None


@dataclass(frozen=True)
class TechnicianResource:
    technician_id: str
    latitude: float
    longitude: float
    shift_start: time
    shift_end: time
    maximum_visits: int
    skills: frozenset[str]
    region: str
    active: bool = True

    @property
    def shift_minutes(self) -> int:
        start = self.shift_start.hour * 60 + self.shift_start.minute
        end = self.shift_end.hour * 60 + self.shift_end.minute
        return max(end - start, 0)


def haversine_km(first: tuple[float, float], second: tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, first)
    lat2, lon2 = map(math.radians, second)
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(value))


class RouteOptimizer:
    def __init__(self, config: dict) -> None:
        self.config = config.get("routing", {})
        self.average_speed_kmph = float(self.config.get("average_speed_kmph", 30))

    def optimize(
        self,
        jobs: list[RoutingJob],
        technicians: list[TechnicianResource],
        planning_date: date,
    ) -> dict:
        active_technicians = [technician for technician in technicians if technician.active]
        feasible, pre_unassigned = self._preflight_jobs(jobs, active_technicians)
        naive_routes, naive_unassigned = self._priority_first_routes(
            feasible, active_technicians
        )
        naive_distance = self._routes_distance(naive_routes, active_technicians)
        try:
            routes, solver_unassigned = self._solve_ortools(feasible, active_technicians)
            status = "optimized"
            failure_reason = None
        except Exception as exc:
            routes = naive_routes
            solver_unassigned = naive_unassigned
            status = "fallback"
            failure_reason = f"OR-Tools unavailable or failed: {type(exc).__name__}"
        all_unassigned = [*pre_unassigned, *solver_unassigned]
        stops, route_summaries = self._scheduled_stops(
            routes, active_technicians, planning_date
        )
        optimized_distance = self._routes_distance(routes, active_technicians)
        return {
            "optimisation_status": status,
            "failure_reason": failure_reason,
            "naive_routes": self._route_site_sequences(naive_routes),
            "routes": route_summaries,
            "stops": stops,
            "unassigned_jobs": all_unassigned,
            "naive_distance_km": round(naive_distance, 3),
            "optimised_distance_km": round(optimized_distance, 3),
            "distance_avoided_km": round(max(naive_distance - optimized_distance, 0.0), 3),
            "total_travel_duration_min": sum(
                route["travel_duration_min"] for route in route_summaries
            ),
            "total_job_duration_min": sum(job.duration_min for route in routes for job in route),
            "total_recoverable_energy_kwh": round(
                sum(job.recoverable_energy_kwh for route in routes for job in route), 3
            ),
            "total_recoverable_value_inr": round(
                sum(job.recoverable_value_inr for route in routes for job in route), 2
            ),
        }

    def _preflight_jobs(
        self,
        jobs: list[RoutingJob],
        technicians: list[TechnicianResource],
    ) -> tuple[list[RoutingJob], list[dict]]:
        feasible = []
        unassigned = []
        active = [technician for technician in technicians if technician.shift_minutes > 0]
        for job in jobs:
            if not self._valid_coordinates(job.latitude, job.longitude):
                unassigned.append(self._unassigned(job, "invalid coordinates"))
            elif job.duration_min <= 0:
                unassigned.append(self._unassigned(job, "missing duration estimate"))
            elif not any(set(job.required_skills).issubset(tech.skills) for tech in active):
                unassigned.append(self._unassigned(job, "no technician with required skill"))
            else:
                feasible.append(job)
        return feasible, unassigned

    def _solve_ortools(
        self,
        jobs: list[RoutingJob],
        technicians: list[TechnicianResource],
    ) -> tuple[list[list[RoutingJob]], list[dict]]:
        if not technicians:
            return [], [self._unassigned(job, "no active technician") for job in jobs]
        hub_count = len(technicians)
        locations = [
            (technician.latitude, technician.longitude) for technician in technicians
        ] + [(job.latitude, job.longitude) for job in jobs]
        distances = self._distance_matrix(locations)
        manager = pywrapcp.RoutingIndexManager(
            len(locations),
            len(technicians),
            list(range(hub_count)),
            list(range(hub_count)),
        )
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index: int, to_index: int) -> int:
            distance = distances[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]
            return int(round(distance * 1000))

        distance_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(distance_index)

        def time_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            travel = self._travel_minutes(distances[from_node][to_node])
            service = jobs[from_node - hub_count].duration_min if from_node >= hub_count else 0
            return travel + service

        time_index = routing.RegisterTransitCallback(time_callback)
        routing.AddDimensionWithVehicleCapacity(
            time_index,
            0,
            [technician.shift_minutes for technician in technicians],
            True,
            "Time",
        )

        def visit_callback(index: int) -> int:
            return int(manager.IndexToNode(index) >= hub_count)

        visit_index = routing.RegisterUnaryTransitCallback(visit_callback)
        routing.AddDimensionWithVehicleCapacity(
            visit_index,
            0,
            [technician.maximum_visits for technician in technicians],
            True,
            "Visits",
        )
        base_penalty = int(self.config.get("drop_penalty_base", 100000))
        multiplier = int(self.config.get("drop_penalty_priority_multiplier", 5000))
        for job_index, job in enumerate(jobs):
            node = hub_count + job_index
            routing_index = manager.NodeToIndex(node)
            allowed = [
                vehicle
                for vehicle, technician in enumerate(technicians)
                if set(job.required_skills).issubset(technician.skills)
            ]
            routing.VehicleVar(routing_index).SetValues(allowed)
            routing.AddDisjunction(
                [routing_index],
                base_penalty + int(round(job.priority_score * multiplier)),
            )
        search = pywrapcp.DefaultRoutingSearchParameters()
        search.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        )
        search.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search.time_limit.seconds = int(self.config.get("solver_time_limit_seconds", 3))
        solution = routing.SolveWithParameters(search)
        if solution is None:
            raise RuntimeError("OR-Tools returned no solution")
        routes: list[list[RoutingJob]] = [[] for _ in technicians]
        assigned: set[str] = set()
        for vehicle in range(len(technicians)):
            index = routing.Start(vehicle)
            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                if node >= hub_count:
                    job = jobs[node - hub_count]
                    routes[vehicle].append(job)
                    assigned.add(job.decision_id)
                index = solution.Value(routing.NextVar(index))
        unassigned = [
            self._unassigned(job, self._solver_drop_reason(job, routes, technicians))
            for job in jobs
            if job.decision_id not in assigned
        ]
        return routes, unassigned

    def _priority_first_routes(
        self,
        jobs: list[RoutingJob],
        technicians: list[TechnicianResource],
    ) -> tuple[list[list[RoutingJob]], list[dict]]:
        routes: list[list[RoutingJob]] = [[] for _ in technicians]
        unassigned = []
        for job in sorted(jobs, key=lambda item: (-item.priority_score, item.site_id)):
            candidates = [
                index
                for index, technician in enumerate(technicians)
                if set(job.required_skills).issubset(technician.skills)
                and len(routes[index]) < technician.maximum_visits
            ]
            placed = False
            for index in candidates:
                trial = [*routes[index], job]
                if (
                    self._route_minutes(trial, technicians[index])
                    <= technicians[index].shift_minutes
                ):
                    routes[index] = trial
                    placed = True
                    break
            if not placed:
                reason = (
                    "maximum visit capacity reached"
                    if not candidates
                    else "shift-time infeasible"
                )
                unassigned.append(self._unassigned(job, reason))
        return routes, unassigned

    def _scheduled_stops(
        self,
        routes: list[list[RoutingJob]],
        technicians: list[TechnicianResource],
        planning_date: date,
    ) -> tuple[list[dict], list[dict]]:
        stops = []
        summaries = []
        for technician, route in zip(technicians, routes, strict=True):
            current = (technician.latitude, technician.longitude)
            clock = datetime.combine(planning_date, technician.shift_start, LOCAL_TIMEZONE)
            route_distance = 0.0
            travel_duration = 0
            route_stops = []
            for sequence, job in enumerate(route, start=1):
                distance = haversine_km(current, (job.latitude, job.longitude))
                travel = self._travel_minutes(distance)
                arrival = clock + timedelta(minutes=travel)
                departure = arrival + timedelta(minutes=job.duration_min)
                stop = {
                    "technician_id": technician.technician_id,
                    "sequence": sequence,
                    "job": asdict(job),
                    "arrival": arrival,
                    "departure": departure,
                    "travel_distance_km": round(distance, 3),
                    "travel_duration_min": travel,
                }
                stops.append(stop)
                route_stops.append(stop)
                route_distance += distance
                travel_duration += travel
                clock = departure
                current = (job.latitude, job.longitude)
            return_distance = haversine_km(current, (technician.latitude, technician.longitude))
            return_minutes = self._travel_minutes(return_distance)
            route_distance += return_distance
            travel_duration += return_minutes
            summaries.append(
                {
                    "technician_id": technician.technician_id,
                    "skills": sorted(technician.skills),
                    "distance_km": round(route_distance, 3),
                    "travel_duration_min": travel_duration,
                    "job_duration_min": sum(job.duration_min for job in route),
                    "return_to_hub": True,
                    "stops": route_stops,
                }
            )
        return stops, summaries

    def _routes_distance(
        self, routes: list[list[RoutingJob]], technicians: list[TechnicianResource]
    ) -> float:
        total = 0.0
        for technician, route in zip(technicians, routes, strict=True):
            current = (technician.latitude, technician.longitude)
            for job in route:
                destination = (job.latitude, job.longitude)
                total += haversine_km(current, destination)
                current = destination
            total += haversine_km(current, (technician.latitude, technician.longitude))
        return total

    def _route_minutes(self, route: list[RoutingJob], technician: TechnicianResource) -> int:
        current = (technician.latitude, technician.longitude)
        minutes = 0
        for job in route:
            destination = (job.latitude, job.longitude)
            minutes += self._travel_minutes(haversine_km(current, destination)) + job.duration_min
            current = destination
        return minutes + self._travel_minutes(
            haversine_km(current, (technician.latitude, technician.longitude))
        )

    def _solver_drop_reason(
        self,
        job: RoutingJob,
        routes: list[list[RoutingJob]],
        technicians: list[TechnicianResource],
    ) -> str:
        compatible = [
            (route, technician)
            for route, technician in zip(routes, technicians, strict=True)
            if set(job.required_skills).issubset(technician.skills)
        ]
        if all(len(route) >= technician.maximum_visits for route, technician in compatible):
            return "maximum visit capacity reached"
        return "shift-time infeasible"

    def _distance_matrix(self, locations: list[tuple[float, float]]) -> list[list[float]]:
        return [
            [haversine_km(origin, destination) for destination in locations]
            for origin in locations
        ]

    def _travel_minutes(self, distance_km: float) -> int:
        if distance_km <= 0:
            return 0
        return max(1, int(math.ceil(distance_km / self.average_speed_kmph * 60)))

    @staticmethod
    def _route_site_sequences(routes: list[list[RoutingJob]]) -> list[list[str]]:
        return [[job.site_id for job in route] for route in routes]

    @staticmethod
    def _valid_coordinates(latitude: float, longitude: float) -> bool:
        return -90 <= latitude <= 90 and -180 <= longitude <= 180

    @staticmethod
    def _unassigned(job: RoutingJob, reason: str) -> dict:
        return {"decision_id": job.decision_id, "site_id": job.site_id, "reason": reason}


def deterministic_route_plan_id(analysis_run_id: str, planning_date: date) -> str:
    digest = hashlib.sha1(f"{analysis_run_id}|{planning_date.isoformat()}".encode()).hexdigest()
    return f"RP-{digest[:24]}"
