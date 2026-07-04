from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.engine import Connection

from app.repositories import ServiceDecisionRepository

ISSUE_BY_PATTERN = {
    "communication failure": "communication or data-logger failure",
    "sudden severe underperformance": "probable inverter or grid-side interruption",
    "persistent underperformance": "probable gradual soiling or persistent degradation",
    "morning time-window candidate": "probable recurring shade or obstruction",
    "afternoon time-window candidate": "probable recurring shade or obstruction",
    "recurring time-specific candidate": "probable recurring shade or obstruction",
    "insufficient evidence": "unknown or insufficient evidence",
}

RECOVERABILITY_KEY = {
    "communication failure": "COMMUNICATION",
    "sudden severe underperformance": "SUDDEN_PRODUCTION_OUTAGE",
    "persistent underperformance": "SOILING_OR_GRADUAL_DEGRADATION",
    "morning time-window candidate": "TIME_DEPENDENT_SHADING_OR_OBSTRUCTION",
    "afternoon time-window candidate": "TIME_DEPENDENT_SHADING_OR_OBSTRUCTION",
    "recurring time-specific candidate": "TIME_DEPENDENT_SHADING_OR_OBSTRUCTION",
    "insufficient evidence": "UNKNOWN_OR_INSUFFICIENT_EVIDENCE",
}

SEVERITY_SCORE = {"NONE": 0.0, "LOW": 25.0, "MEDIUM": 50.0, "HIGH": 75.0, "CRITICAL": 100.0}


@dataclass(frozen=True)
class ServiceDecisionSummary:
    analysis_run_id: str
    decisions: int
    actionable: int
    remote_actions: int
    field_visits: int
    monitoring: int


class ServiceDecisionService:
    def __init__(self, connection: Connection, config: dict) -> None:
        self.repository = ServiceDecisionRepository(connection)
        self.config = config
        self.business = config.get("business", {})
        self.reasoning = self.business.get("reasoning", {})
        self.priority_config = self.business.get("priority", {})

    def run(self, analysis_run_id: str) -> ServiceDecisionSummary:
        candidates = self.repository.read_consolidated_candidates(analysis_run_id)
        sites = self.repository.read_sites().set_index("site_id")
        telemetry = self.repository.read_telemetry()
        history = self.repository.read_service_history()
        forecast = self.repository.read_weather_forecast()
        weather_history = self.repository.read_weather_history()
        decisions = []
        for candidate in candidates.itertuples(index=False):
            site = sites.loc[candidate.site_id]
            site_telemetry = self._candidate_telemetry(telemetry, candidate)
            site_history = self._recent_history(history, candidate)
            site_forecast = forecast[forecast["weather_zone"].eq(site.weather_zone)]
            site_weather_history = self._recent_weather(
                weather_history[weather_history["weather_zone"].eq(site.weather_zone)],
                candidate,
            )
            decisions.append(
                self._decision(
                    candidate,
                    site,
                    site_telemetry,
                    site_history,
                    site_forecast,
                    site_weather_history,
                )
            )
        self._assign_queue_ranks(decisions)
        self.repository.replace_decisions(analysis_run_id, decisions)
        return ServiceDecisionSummary(
            analysis_run_id=analysis_run_id,
            decisions=len(decisions),
            actionable=sum(bool(item["actionable"]) for item in decisions),
            remote_actions=sum(
                bool(
                    item["actionable"]
                    and item["remote_action_available"]
                    and not item["visit_required"]
                )
                for item in decisions
            ),
            field_visits=sum(bool(item["visit_required"]) for item in decisions),
            monitoring=sum(not bool(item["actionable"]) for item in decisions),
        )

    def _decision(
        self,
        candidate,
        site: pd.Series,
        telemetry: pd.DataFrame,
        history: pd.DataFrame,
        forecast: pd.DataFrame,
        weather_history: pd.DataFrame | None = None,
    ) -> dict:
        category = candidate.provisional_category
        evidence, contradictions, telemetry_score, weather_score = self._evidence(
            candidate, telemetry, history, forecast, weather_history
        )
        confidence_score, confidence_label, confidence_components = self._confidence(
            candidate,
            telemetry_score,
            weather_score,
            history,
            contradictions,
        )
        impact = self._impact(candidate, site, forecast, confidence_score)
        complaint_severity, sla_status, complaint_score, sla_score = self._service_context(
            history, candidate, site
        )
        cleaning = self._cleaning_decision(
            candidate,
            site,
            forecast,
            history,
            confidence_score,
            impact,
            weather_history,
        )
        actionable, actionability_reason = self._operational_actionability(
            candidate,
            site,
            confidence_score,
        )
        evidence.append(actionability_reason)
        technical_evidence = self._has_independent_technical_evidence(telemetry)
        action = self._recommended_action(
            candidate,
            confidence_score,
            complaint_severity,
            cleaning,
            impact,
            actionable=actionable,
            sla_status=sla_status,
            independent_technical_evidence=technical_evidence,
        )
        priority_score, priority_label, priority_components = self._priority(
            candidate,
            confidence_score,
            impact,
            complaint_score,
            sla_score,
            capacity_kw=float(site.capacity_kw),
        )
        return {
            "decision_id": self._decision_id(
                candidate.analysis_run_id, candidate.incident_candidate_id
            ),
            "analysis_run_id": candidate.analysis_run_id,
            "incident_candidate_id": candidate.incident_candidate_id,
            "site_id": candidate.site_id,
            "probable_issue": self._probable_issue(candidate),
            "confidence_score": confidence_score,
            "confidence_label": confidence_label,
            "supporting_evidence": evidence,
            "contradictory_evidence": contradictions,
            "confidence_components": confidence_components,
            "expected_energy_kwh": float(candidate.expected_energy_kwh),
            "actual_energy_kwh": (
                None
                if category == "communication failure"
                else self._optional_float(candidate.actual_energy_kwh)
            ),
            "estimated_energy_loss_kwh": max(float(candidate.total_energy_loss_kwh), 0.0),
            **impact,
            "tariff_per_kwh": float(site.tariff_per_kwh),
            "visit_cost_inr": float(site.visit_cost_inr),
            "cleaning_cost_inr": float(site.cleaning_cost_inr),
            **cleaning,
            **action,
            "actionable": actionable,
            "complaint_severity": complaint_severity,
            "sla_status": sla_status,
            "priority_score": priority_score,
            "priority_label": priority_label,
            "priority_components": priority_components,
            "queue_rank": None,
        }

    def _evidence(
        self,
        candidate,
        telemetry: pd.DataFrame,
        history: pd.DataFrame,
        forecast: pd.DataFrame,
        weather_history: pd.DataFrame | None = None,
    ) -> tuple[list[str], list[str], float, float]:
        category = candidate.provisional_category
        evidence = [
            f"Detected pattern: {category}",
            f"Evidence duration: {int(candidate.duration_minutes)} minutes",
        ]
        contradictions: list[str] = []
        telemetry_score = 30.0
        if category == "communication failure":
            missing = int((~telemetry["data_received"].astype(bool)).sum())
            missing_measurements = int(telemetry["generation_kwh"].isna().sum())
            evidence.extend(
                [
                    f"{missing} received-false intervals",
                    f"{missing_measurements} intervals lack generation measurements",
                ]
            )
            telemetry_score = min(100.0, missing * 10.0)
        elif category == "sudden severe underperformance":
            evidence.extend(
                [
                    f"Minimum performance ratio {float(candidate.minimum_performance_ratio):.3f}",
                    f"Sustained energy loss {float(candidate.total_energy_loss_kwh):.2f} kWh",
                ]
            )
            fault_rows = telemetry[telemetry["fault_code"].notna()]
            abnormal_status = telemetry[
                telemetry["inverter_status"].isin(["FAULT", "OFFLINE", "STANDBY"])
            ]
            if not fault_rows.empty:
                evidence.append("Explicit inverter alarm code is present")
                telemetry_score += 40
            else:
                evidence.append(
                    "No explicit fault code; outage pattern remains independently visible"
                )
            if not abnormal_status.empty:
                evidence.append("Inverter status corroborates interrupted operation")
                telemetry_score += 30
            if telemetry["ac_voltage"].dropna().lt(180).any():
                evidence.append("AC voltage includes an abnormal low reading")
                telemetry_score += 20
        elif category == "persistent underperformance":
            evidence.extend(
                [
                    f"Multi-interval loss totals {float(candidate.total_energy_loss_kwh):.2f} kWh",
                    f"Average performance ratio {float(candidate.average_performance_ratio):.3f}",
                ]
            )
            telemetry_score = 55.0
        elif "time-window" in category or "time-specific" in category:
            evidence.append("Loss recurs in a consistent Asia/Kolkata daylight window")
            if candidate.secondary_evidence:
                evidence.append("Secondary evidence: " + ", ".join(candidate.secondary_evidence))
            elif not candidate.actionable:
                contradictions.append(
                    "Low-impact pattern lacks independent corroboration; "
                    "model or weather bias is possible"
                )
            telemetry_score = 65.0
        else:
            evidence.append("Available signals do not support a reliable physical cause")
            contradictions.append("Evidence is incomplete or conflicting")
            telemetry_score = 15.0
        if not history.empty:
            evidence.append(f"{len(history)} recent service-history record(s) reviewed")
        rain = float(forecast["rainfall_mm"].sum()) if not forecast.empty else 0.0
        historical_rain = (
            float(weather_history["rainfall_mm"].sum())
            if weather_history is not None and not weather_history.empty
            else 0.0
        )
        weather_score = (
            80.0 if rain < float(self.business.get("significant_rain_mm", 2.0)) else 55.0
        )
        if rain > 0:
            evidence.append(f"Forecast rainfall totals {rain:.2f} mm")
        if historical_rain > 0:
            evidence.append(f"Recent observed rainfall totals {historical_rain:.2f} mm")
        return evidence, contradictions, min(telemetry_score, 100.0), weather_score

    def _confidence(
        self,
        candidate,
        telemetry_score: float,
        weather_score: float,
        history: pd.DataFrame,
        contradictions: list[str],
    ) -> tuple[float, str, dict]:
        weights = self.reasoning.get("confidence_weights", {})
        pattern = {
            "communication failure": 90.0,
            "sudden severe underperformance": 90.0,
            "persistent underperformance": 70.0,
            "morning time-window candidate": 80.0,
            "afternoon time-window candidate": 80.0,
            "recurring time-specific candidate": 80.0,
            "insufficient evidence": 20.0,
        }.get(candidate.provisional_category, 20.0)
        persistence = min(float(candidate.duration_minutes) / 480.0 * 100.0, 100.0)
        completeness = max(0.0, min(float(candidate.data_completeness) * 100.0, 100.0))
        service = self._history_corroboration(history, candidate.provisional_category)
        raw = {
            "pattern_strength": pattern,
            "persistence": persistence,
            "data_completeness": completeness,
            "telemetry_corroboration": telemetry_score,
            "service_history_corroboration": service,
            "weather_stability": weather_score,
        }
        components = {
            key: {
                "raw": round(value, 2),
                "weight": float(weights.get(key, 0)),
                "points": round(value * float(weights.get(key, 0)) / 100.0, 2),
            }
            for key, value in raw.items()
        }
        penalty = float(self.reasoning.get("contradiction_penalty", 15)) * len(contradictions)
        score = sum(item["points"] for item in components.values()) - penalty
        if candidate.provisional_category == "insufficient evidence":
            score = min(score, 39.0)
        score = round(max(0.0, min(score, 100.0)), 2)
        components["contradiction_penalty"] = {
            "raw": len(contradictions),
            "weight": -float(self.reasoning.get("contradiction_penalty", 15)),
            "points": -penalty,
        }
        return score, self._confidence_label(score), components

    def _impact(
        self,
        candidate,
        site: pd.Series,
        forecast: pd.DataFrame,
        confidence_score: float,
    ) -> dict:
        historical_loss = max(float(candidate.total_energy_loss_kwh), 0.0)
        tariff = float(site.tariff_per_kwh)
        evidence = candidate.dominant_evidence or {}
        affected_days = max(int(evidence.get("recurring_days", 1)), 1)
        projection_days = int(self.reasoning.get("recoverable_projection_days", 7))
        forecast_ghi = float(forecast["ghi_wm2"].mean()) if not forecast.empty else 500.0
        production_factor = max(0.25, min(forecast_ghi / 500.0, 1.25))
        projected_loss = historical_loss / affected_days * projection_days * production_factor
        factor_key = RECOVERABILITY_KEY.get(
            candidate.provisional_category, "UNKNOWN_OR_INSUFFICIENT_EVIDENCE"
        )
        recoverability = float(self.business.get("recoverability_factor", {}).get(factor_key, 0))
        ongoing = float(self.reasoning.get("ongoing_incident_factor", 1.0))
        recoverable_energy = max(
            projected_loss * recoverability * confidence_score / 100.0 * ongoing,
            0.0,
        )
        return {
            "estimated_value_at_risk_inr": round(historical_loss * tariff, 2),
            "projected_seven_day_loss_kwh": round(projected_loss, 3),
            "estimated_recoverable_energy_kwh": round(recoverable_energy, 3),
            "estimated_recoverable_value_inr": round(recoverable_energy * tariff, 2),
        }

    def _cleaning_decision(
        self,
        candidate,
        site: pd.Series,
        forecast: pd.DataFrame,
        history: pd.DataFrame,
        confidence_score: float,
        impact: dict,
        weather_history: pd.DataFrame | None = None,
    ) -> dict:
        rain = float(forecast["rainfall_mm"].sum()) if not forecast.empty else 0.0
        significant_rain = float(self.business.get("significant_rain_mm", 2.0))
        applies = candidate.provisional_category == "persistent underperformance" or (
            "persistent underperformance" in (candidate.secondary_evidence or [])
        )
        if not applies:
            if rain >= significant_rain:
                return {
                    "cleaning_decision": "defer_rain",
                    "cleaning_reason": "Cleaning is not primary and forecast rain favors deferral.",
                }
            return {
                "cleaning_decision": "not_applicable",
                "cleaning_reason": "Detected pattern does not independently justify cleaning.",
            }
        recent_cleaning = history[history["complaint_type"].eq("CLEANING")]
        recent_rain = (
            float(weather_history["rainfall_mm"].sum())
            if weather_history is not None and not weather_history.empty
            else 0.0
        )
        if rain >= significant_rain:
            return {
                "cleaning_decision": "defer_rain",
                "cleaning_reason": "Meaningful near-term rain is forecast; defer cleaning.",
            }
        if not recent_cleaning.empty:
            return {
                "cleaning_decision": "inspect",
                "cleaning_reason": "Recent cleaning history contradicts automatic re-cleaning.",
            }
        if recent_rain >= significant_rain:
            return {
                "cleaning_decision": "inspect",
                "cleaning_reason": (
                    "Recent observed rain weakens an automatic probable-soiling conclusion."
                ),
            }
        minimum_confidence = float(self.reasoning.get("cleaning_confidence_threshold", 60))
        required_value = float(site.cleaning_cost_inr) * float(
            self.business.get("cleaning_safety_margin", 1.2)
        )
        if confidence_score >= minimum_confidence and (
            impact["estimated_recoverable_value_inr"] >= required_value
        ):
            return {
                "cleaning_decision": "schedule",
                "cleaning_reason": "Projected recoverable value exceeds cleaning economics gate.",
            }
        return {
            "cleaning_decision": "inspect",
            "cleaning_reason": (
                "Evidence or recoverable value is insufficient for automatic cleaning."
            ),
        }

    def _recommended_action(
        self,
        candidate,
        confidence_score: float,
        complaint_severity: str,
        cleaning: dict,
        impact: dict,
        actionable: bool | None = None,
        sla_status: str = "NO_OPEN_SLA",
        independent_technical_evidence: bool = False,
    ) -> dict:
        category = candidate.provisional_category
        is_actionable = bool(candidate.actionable) if actionable is None else actionable
        if not is_actionable:
            action = "collect additional data" if category == "insufficient evidence" else "monitor"
            return {
                "recommended_action": action,
                "action_reason": "Current evidence does not justify field dispatch.",
                "prerequisite_remote_checks": ["Review telemetry and weather alignment"],
                "escalation_condition": (
                    "Escalate if persistence, impact, or corroboration increases."
                ),
                "remote_action_available": True,
                "visit_required": False,
            }
        if category == "communication failure":
            escalation = int(self.reasoning.get("communication_escalation_minutes", 1440))
            visit = candidate.duration_minutes >= escalation or complaint_severity == "CRITICAL"
            return {
                "recommended_action": (
                    "physical technical inspection" if visit else "remote connectivity check"
                ),
                "action_reason": (
                    "Missing telemetry indicates a probable logger or connectivity issue."
                ),
                "prerequisite_remote_checks": ["Verify network", "Restart data logger remotely"],
                "escalation_condition": (
                    "Dispatch if remote recovery fails or SLA urgency increases."
                ),
                "remote_action_available": True,
                "visit_required": visit,
            }
        if category == "sudden severe underperformance":
            visit = (
                candidate.duration_minutes
                >= int(self.reasoning.get("outage_field_duration_minutes", 240))
                and candidate.total_energy_loss_kwh
                >= float(self.reasoning.get("outage_field_minimum_loss_kwh", 8))
            ) or complaint_severity == "CRITICAL"
            return {
                "recommended_action": "urgent field visit" if visit else "remote diagnostic",
                "action_reason": "Sustained near-zero production under meaningful expectation.",
                "prerequisite_remote_checks": ["Check inverter status", "Verify grid availability"],
                "escalation_condition": (
                    "Dispatch when remote restart is unsuitable or unsuccessful."
                ),
                "remote_action_available": True,
                "visit_required": visit,
            }
        if cleaning["cleaning_decision"] == "defer_rain":
            severe_degradation = (
                candidate.average_performance_ratio is not None
                and candidate.average_performance_ratio
                <= float(self.reasoning.get("severe_degradation_ratio", 0.35))
            )
            urgent_service = complaint_severity == "CRITICAL" and sla_status in {
                "OPEN",
                "OVERDUE",
            }
            if not (independent_technical_evidence or severe_degradation or urgent_service):
                return {
                    "recommended_action": "monitor",
                    "action_reason": (
                        "Cleaning is deferred for forecast rain and no independent "
                        "technical escalation evidence is present."
                    ),
                    "prerequisite_remote_checks": [
                        "Review performance remotely after the forecast rain event"
                    ],
                    "escalation_condition": (
                        "Reassess after rainfall; inspect if loss persists or electrical "
                        "evidence emerges."
                    ),
                    "remote_action_available": True,
                    "visit_required": False,
                }
        if cleaning["cleaning_decision"] == "schedule":
            return {
                "recommended_action": "schedule cleaning",
                "action_reason": cleaning["cleaning_reason"],
                "prerequisite_remote_checks": ["Confirm safe roof access"],
                "escalation_condition": "Inspect technically if performance does not recover.",
                "remote_action_available": False,
                "visit_required": True,
            }
        if "time-window" in category or "time-specific" in category:
            return {
                "recommended_action": "physical technical inspection",
                "action_reason": (
                    "Recurring local-time loss suggests probable shade or obstruction."
                ),
                "prerequisite_remote_checks": ["Review site imagery and orientation"],
                "escalation_condition": "Schedule inspection when pattern persists after review.",
                "remote_action_available": True,
                "visit_required": impact["estimated_recoverable_value_inr"] > 0,
            }
        return {
            "recommended_action": "physical technical inspection",
            "action_reason": cleaning["cleaning_reason"],
            "prerequisite_remote_checks": ["Review recent cleaning and inverter history"],
            "escalation_condition": "Clean only after inspection confirms likely soiling.",
            "remote_action_available": True,
            "visit_required": confidence_score
            >= float(self.reasoning.get("high_confidence_threshold", 70)),
        }

    def _priority(
        self,
        candidate,
        confidence_score: float,
        impact: dict,
        complaint_score: float,
        sla_score: float,
        capacity_kw: float = 1.0,
    ) -> tuple[float, str, dict]:
        weights = self.priority_config.get("weights", {})
        max_value = float(self.priority_config.get("maximum_recoverable_value_inr", 3000))
        max_capacity_impact = float(
            self.priority_config.get("maximum_recoverable_energy_per_capacity_kwh", 5)
        )
        capacity_weight = float(
            self.priority_config.get("capacity_normalized_impact_weight", 0.70)
        )
        persistence_reference = self._persistence_reference(candidate.provisional_category)
        recoverable_per_capacity = (
            impact.get("estimated_recoverable_energy_kwh", 0.0) / max(capacity_kw, 0.1)
        )
        value_impact = min(
            impact["estimated_recoverable_value_inr"] / max_value * 100,
            100,
        )
        capacity_impact = min(recoverable_per_capacity / max_capacity_impact * 100, 100)
        combined_impact = (
            capacity_weight * capacity_impact + (1 - capacity_weight) * value_impact
        )
        raw = {
            "recoverable_impact": impact["estimated_recoverable_value_inr"],
            "persistence": float(candidate.duration_minutes),
            "diagnostic_confidence": confidence_score,
            "complaint_urgency": complaint_score,
            "sla_warranty_risk": sla_score,
            "route_clustering_benefit": float(self.priority_config.get("neutral_route_score", 50)),
        }
        normalized = {
            "recoverable_impact": combined_impact,
            "persistence": min(raw["persistence"] / persistence_reference * 100, 100),
            "diagnostic_confidence": confidence_score,
            "complaint_urgency": complaint_score,
            "sla_warranty_risk": sla_score,
            "route_clustering_benefit": raw["route_clustering_benefit"],
        }
        components = {
            key: {
                "raw": round(raw[key], 2),
                "normalized": round(normalized[key], 2),
                "weight": float(weights.get(key, 0)),
                "points": round(normalized[key] * float(weights.get(key, 0)), 2),
            }
            for key in raw
        }
        components["recoverable_impact"]["capacity_normalized_kwh_per_kw"] = round(
            recoverable_per_capacity, 3
        )
        components["persistence"]["category_reference_minutes"] = persistence_reference
        score = round(sum(item["points"] for item in components.values()), 2)
        return score, self._priority_label(score), components

    def _service_context(
        self, history: pd.DataFrame, candidate, site: pd.Series
    ) -> tuple[str, str, float, float]:
        reference = pd.Timestamp(candidate.end_timestamp)
        warranty_end = pd.Timestamp(site.warranty_end_date)
        warranty_days = (warranty_end.tz_localize("UTC") - reference).days
        warranty_risk = 60.0 if 0 <= warranty_days <= 365 else 25.0
        if history.empty:
            status = "WARRANTY_EXPIRING" if warranty_risk > 25 else "NO_OPEN_SLA"
            return "NONE", status, 0.0, warranty_risk
        unresolved = history[history["resolved_at"].isna()]
        if unresolved.empty:
            repeat = bool(history["repeat_complaint"].astype(bool).any())
            severity = "LOW" if repeat else "NONE"
        else:
            severity = max(
                (str(value) for value in unresolved["complaint_severity"]),
                key=lambda value: SEVERITY_SCORE.get(value, 0),
            )
        overdue = (
            not unresolved.empty
            and pd.to_datetime(unresolved["sla_due_at"], utc=True).lt(reference).any()
        )
        repeat = bool(history["repeat_complaint"].astype(bool).any())
        sla_status = "OVERDUE" if overdue else ("OPEN" if not unresolved.empty else "RESOLVED")
        sla_score = (
            100.0 if overdue else (70.0 if not unresolved.empty else (50.0 if repeat else 25.0))
        )
        return severity, sla_status, SEVERITY_SCORE.get(severity, 0.0), max(
            sla_score, warranty_risk
        )

    def _operational_actionability(
        self,
        candidate,
        site: pd.Series,
        confidence_score: float,
    ) -> tuple[bool, str]:
        category = candidate.provisional_category
        if category == "communication failure":
            return True, "Actionable remote check; communication loss need not have energy impact."
        if category == "insufficient evidence":
            return False, "Diagnostic-only state remains outside the operational queue."
        rules = self.reasoning.get("actionability", {})
        loss = max(float(candidate.total_energy_loss_kwh), 0.0)
        expected = max(float(candidate.expected_energy_kwh), 0.001)
        capacity = max(float(site.capacity_kw), 0.1)
        loss_fraction = loss / expected
        loss_per_capacity = loss / capacity
        minimum_duration = float(rules.get("minimum_duration_minutes", 180))
        minimum_confidence = float(rules.get("minimum_confidence", 60))
        evidence_gate = (
            candidate.duration_minutes >= minimum_duration
            and confidence_score >= minimum_confidence
        )
        absolute_gate = loss >= float(rules.get("minimum_absolute_loss_kwh", 10))
        normalized_gate = (
            loss_fraction >= float(rules.get("minimum_loss_fraction", 0.25))
            and loss_per_capacity
            >= float(rules.get("minimum_loss_per_capacity_kwh", 0.25))
        )
        recurring = "time-window" in category or "time-specific" in category
        if recurring and not absolute_gate and bool(
            rules.get("recurring_requires_secondary_evidence_below_absolute_threshold", True)
        ):
            normalized_gate = normalized_gate and bool(candidate.secondary_evidence)
        actionable = evidence_gate and (absolute_gate or normalized_gate)
        reason = (
            f"Actionability gates: absolute_loss={absolute_gate}, "
            f"loss_fraction={loss_fraction:.3f}, loss_per_capacity={loss_per_capacity:.3f}, "
            f"duration_confidence={evidence_gate}."
        )
        return actionable, reason

    @staticmethod
    def _has_independent_technical_evidence(telemetry: pd.DataFrame) -> bool:
        if telemetry.empty:
            return False
        alarm = telemetry["fault_code"].notna().any()
        status = telemetry["inverter_status"].isin(["FAULT", "OFFLINE"]).any()
        low_voltage = telemetry["ac_voltage"].dropna().lt(180).any()
        return bool(alarm or status or low_voltage)

    def _persistence_reference(self, category: str) -> float:
        references = self.priority_config.get("persistence_reference_minutes", {})
        if category == "communication failure":
            key = "communication"
        elif category == "sudden severe underperformance":
            key = "outage"
        elif category == "persistent underperformance":
            key = "persistent"
        elif "time-window" in category or "time-specific" in category:
            key = "recurring"
        else:
            key = "insufficient"
        default = float(self.priority_config.get("maximum_persistence_minutes", 1440))
        return max(float(references.get(key, default)), 1.0)

    @staticmethod
    def _history_corroboration(history: pd.DataFrame, category: str) -> float:
        if history.empty:
            return 0.0
        expected = {
            "communication failure": {"OFFLINE", "NO_DISPLAY"},
            "sudden severe underperformance": {"OFFLINE", "LOW_GENERATION"},
            "persistent underperformance": {"LOW_GENERATION", "CLEANING"},
            "morning time-window candidate": {"LOW_GENERATION"},
            "afternoon time-window candidate": {"LOW_GENERATION"},
        }.get(category, set())
        matches = history["complaint_type"].isin(expected).sum()
        repeat = history["repeat_complaint"].astype(bool).sum()
        return min(float(matches * 35 + repeat * 20), 100.0)

    def _confidence_label(self, score: float) -> str:
        labels = self.reasoning.get("confidence_labels", {})
        if score >= float(labels.get("very_high", 85)):
            return "Very high"
        if score >= float(labels.get("high", 70)):
            return "High"
        if score >= float(labels.get("medium", 40)):
            return "Medium"
        return "Low"

    @staticmethod
    def _probable_issue(candidate) -> str:
        category = candidate.provisional_category
        recurring = "time-window" in category or "time-specific" in category
        if recurring and not candidate.actionable and not candidate.secondary_evidence:
            return "unknown or insufficient evidence"
        return ISSUE_BY_PATTERN.get(category, "unknown or insufficient evidence")

    def _priority_label(self, score: float) -> str:
        labels = self.priority_config.get("labels", {})
        if score >= float(labels.get("critical", 85)):
            return "Critical"
        if score >= float(labels.get("high", 70)):
            return "High"
        if score >= float(labels.get("medium", 40)):
            return "Medium"
        return "Low"

    def _assign_queue_ranks(self, decisions: list[dict]) -> None:
        actionable = sorted(
            (item for item in decisions if item["actionable"]),
            key=lambda item: (-item["priority_score"], item["site_id"], item["decision_id"]),
        )
        for rank, decision in enumerate(actionable, start=1):
            decision["queue_rank"] = rank

    def _recent_history(self, history: pd.DataFrame, candidate) -> pd.DataFrame:
        site = history[history["site_id"].eq(candidate.site_id)].copy()
        if site.empty:
            return site
        reported = pd.to_datetime(site["reported_at"], utc=True)
        cutoff = pd.Timestamp(candidate.end_timestamp) - pd.Timedelta(
            days=int(self.reasoning.get("recent_service_days", 180))
        )
        return site.loc[reported >= cutoff]

    @staticmethod
    def _recent_weather(weather: pd.DataFrame, candidate) -> pd.DataFrame:
        if weather.empty:
            return weather
        timestamps = pd.to_datetime(weather["timestamp"], utc=True)
        end = pd.Timestamp(candidate.end_timestamp)
        return weather.loc[timestamps.between(end - pd.Timedelta(days=7), end)]

    @staticmethod
    def _candidate_telemetry(telemetry: pd.DataFrame, candidate) -> pd.DataFrame:
        timestamps = pd.to_datetime(telemetry["timestamp"], utc=True)
        return telemetry[
            telemetry["site_id"].eq(candidate.site_id)
            & timestamps.between(candidate.start_timestamp, candidate.end_timestamp)
        ].copy()

    @staticmethod
    def _decision_id(analysis_run_id: str, candidate_id: str) -> str:
        digest = hashlib.sha1(f"{analysis_run_id}|{candidate_id}".encode()).hexdigest()
        return f"SD-{digest[:24]}"

    @staticmethod
    def _optional_float(value) -> float | None:
        return None if pd.isna(value) else float(value)
