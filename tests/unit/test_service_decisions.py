from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd

from app.services.service_decisions import ServiceDecisionService

CONFIG = {
    "business": {
        "cleaning_safety_margin": 1.2,
        "significant_rain_mm": 2.0,
        "recoverability_factor": {
            "COMMUNICATION": 0.4,
            "SUDDEN_PRODUCTION_OUTAGE": 0.75,
            "SOILING_OR_GRADUAL_DEGRADATION": 0.65,
            "TIME_DEPENDENT_SHADING_OR_OBSTRUCTION": 0.5,
            "UNKNOWN_OR_INSUFFICIENT_EVIDENCE": 0.2,
        },
        "reasoning": {
            "confidence_weights": {
                "pattern_strength": 25,
                "persistence": 20,
                "data_completeness": 15,
                "telemetry_corroboration": 20,
                "service_history_corroboration": 10,
                "weather_stability": 10,
            },
            "confidence_labels": {"medium": 40, "high": 70, "very_high": 85},
            "contradiction_penalty": 15,
            "high_confidence_threshold": 70,
            "communication_escalation_minutes": 1440,
            "outage_field_duration_minutes": 240,
            "outage_field_minimum_loss_kwh": 8,
            "severe_degradation_ratio": 0.35,
            "cleaning_confidence_threshold": 60,
            "recoverable_projection_days": 7,
            "ongoing_incident_factor": 1,
            "recent_service_days": 180,
            "actionability": {
                "minimum_absolute_loss_kwh": 10,
                "minimum_loss_fraction": 0.25,
                "minimum_loss_per_capacity_kwh": 0.25,
                "minimum_duration_minutes": 180,
                "minimum_confidence": 60,
                "recurring_requires_secondary_evidence_below_absolute_threshold": True,
            },
        },
        "priority": {
            "weights": {
                "recoverable_impact": 0.30,
                "persistence": 0.20,
                "diagnostic_confidence": 0.15,
                "complaint_urgency": 0.15,
                "sla_warranty_risk": 0.10,
                "route_clustering_benefit": 0.10,
            },
            "maximum_recoverable_value_inr": 3000,
            "maximum_recoverable_energy_per_capacity_kwh": 5,
            "capacity_normalized_impact_weight": 0.70,
            "maximum_persistence_minutes": 1440,
            "persistence_reference_minutes": {
                "communication": 360,
                "outage": 240,
                "persistent": 720,
                "recurring": 1440,
                "insufficient": 1440,
            },
            "neutral_route_score": 50,
            "labels": {"medium": 40, "high": 70, "critical": 85},
        },
    }
}


def _service() -> ServiceDecisionService:
    return ServiceDecisionService(MagicMock(), CONFIG)


def _candidate(category: str, **overrides) -> SimpleNamespace:
    values = {
        "analysis_run_id": "RUN-TEST",
        "incident_candidate_id": "IC-TEST",
        "site_id": "MH-TEST",
        "provisional_category": category,
        "duration_minutes": 300,
        "expected_energy_kwh": 20.0,
        "actual_energy_kwh": 5.0,
        "total_energy_loss_kwh": 15.0,
        "average_performance_ratio": 0.25,
        "minimum_performance_ratio": 0.01,
        "data_completeness": 1.0,
        "dominant_evidence": {"recurring_days": 3},
        "secondary_evidence": [],
        "actionable": True,
        "start_timestamp": pd.Timestamp("2026-06-10T05:00:00Z"),
        "end_timestamp": pd.Timestamp("2026-06-10T10:00:00Z"),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _site(**overrides) -> pd.Series:
    values = {
        "tariff_per_kwh": 8.0,
        "cleaning_cost_inr": 750.0,
        "visit_cost_inr": 800.0,
        "weather_zone": "PUNE_WEST",
        "capacity_kw": 5.0,
        "warranty_end_date": pd.Timestamp("2030-01-01"),
    }
    values.update(overrides)
    return pd.Series(values)


def _telemetry(fault_code: str | None = None, status: str = "RUNNING") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "data_received": [True] * 4,
            "generation_kwh": [0.0] * 4,
            "fault_code": [fault_code] * 4,
            "inverter_status": [status] * 4,
            "ac_voltage": [230.0] * 4,
        }
    )


def _empty_history() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "complaint_type",
            "complaint_severity",
            "repeat_complaint",
            "resolved_at",
            "sla_due_at",
        ]
    )


def _forecast(rainfall: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame({"ghi_wm2": [600.0] * 4, "rainfall_mm": [rainfall] * 4})


def test_sudden_outage_without_fault_code_remains_probable_interruption() -> None:
    decision = _service()._decision(
        _candidate("sudden severe underperformance"),
        _site(),
        _telemetry(),
        _empty_history(),
        _forecast(),
    )

    assert decision["probable_issue"] == "probable inverter or grid-side interruption"
    assert decision["visit_required"] is True
    assert any("No explicit fault code" in item for item in decision["supporting_evidence"])


def test_communication_defaults_to_remote_connectivity_action() -> None:
    telemetry = _telemetry()
    telemetry["data_received"] = False
    telemetry["generation_kwh"] = None
    decision = _service()._decision(
        _candidate("communication failure", total_energy_loss_kwh=0.0, duration_minutes=120),
        _site(),
        telemetry,
        _empty_history(),
        _forecast(),
    )

    assert decision["probable_issue"] == "communication or data-logger failure"
    assert decision["recommended_action"] == "remote connectivity check"
    assert decision["visit_required"] is False


def test_recurring_window_maps_to_probable_shade_not_confirmed_fault() -> None:
    decision = _service()._decision(
        _candidate("morning time-window candidate", average_performance_ratio=0.62),
        _site(),
        _telemetry(),
        _empty_history(),
        _forecast(),
    )

    assert decision["probable_issue"] == "probable recurring shade or obstruction"
    assert "confirmed" not in decision["probable_issue"]


def test_uncorroborated_non_actionable_recurring_pattern_remains_unknown() -> None:
    decision = _service()._decision(
        _candidate(
            "morning time-window candidate",
            actionable=False,
            total_energy_loss_kwh=5.0,
        ),
        _site(),
        _telemetry(),
        _empty_history(),
        _forecast(),
    )

    assert decision["probable_issue"] == "unknown or insufficient evidence"
    assert decision["confidence_score"] < 70
    assert decision["recommended_action"] == "monitor"


def test_ambiguous_non_actionable_state_preserves_uncertainty() -> None:
    decision = _service()._decision(
        _candidate("insufficient evidence", actionable=False, data_completeness=0.5),
        _site(),
        _telemetry(),
        _empty_history(),
        _forecast(),
    )

    assert decision["probable_issue"] == "unknown or insufficient evidence"
    assert decision["confidence_label"] == "Low"
    assert decision["recommended_action"] == "collect additional data"
    assert decision["visit_required"] is False


def test_corroboration_increases_and_missing_data_reduces_confidence() -> None:
    service = _service()
    candidate = _candidate("sudden severe underperformance")
    low, _, _ = service._confidence(candidate, 20, 80, _empty_history(), [])
    high, _, _ = service._confidence(candidate, 100, 80, _empty_history(), [])
    missing, _, _ = service._confidence(
        _candidate("sudden severe underperformance", data_completeness=0.3),
        20,
        80,
        _empty_history(),
        [],
    )

    assert high > low > missing


def test_contradictory_evidence_reduces_confidence() -> None:
    service = _service()
    candidate = _candidate("persistent underperformance")
    clear, _, _ = service._confidence(candidate, 60, 80, _empty_history(), [])
    contradicted, _, _ = service._confidence(
        candidate, 60, 80, _empty_history(), ["Recent cleaning contradicts soiling"]
    )

    assert contradicted < clear


def test_value_at_risk_uses_tariff_and_future_recoverability_is_separate() -> None:
    impact = _service()._impact(
        _candidate("persistent underperformance"), _site(tariff_per_kwh=10), _forecast(), 80
    )

    assert impact["estimated_value_at_risk_inr"] == 150.0
    assert impact["estimated_recoverable_energy_kwh"] >= 0
    assert impact["projected_seven_day_loss_kwh"] != 15.0


def test_forecast_rain_defers_cleaning() -> None:
    result = _service()._cleaning_decision(
        _candidate("persistent underperformance"),
        _site(),
        _forecast(rainfall=1.0),
        _empty_history(),
        80,
        {"estimated_recoverable_value_inr": 2000.0},
    )

    assert result["cleaning_decision"] == "defer_rain"


def test_rain_deferred_cleaning_does_not_create_immediate_visit() -> None:
    action = _service()._recommended_action(
        _candidate("morning time-window candidate", average_performance_ratio=0.62),
        80,
        "HIGH",
        {"cleaning_decision": "defer_rain", "cleaning_reason": "forecast rain"},
        {"estimated_recoverable_value_inr": 30.0},
        actionable=True,
        sla_status="OPEN",
        independent_technical_evidence=False,
    )

    assert action["recommended_action"] == "monitor"
    assert action["visit_required"] is False
    assert "Reassess after rainfall" in action["escalation_condition"]


def test_independent_technical_evidence_can_override_rain_deferral() -> None:
    action = _service()._recommended_action(
        _candidate("morning time-window candidate"),
        80,
        "HIGH",
        {"cleaning_decision": "defer_rain", "cleaning_reason": "forecast rain"},
        {"estimated_recoverable_value_inr": 30.0},
        actionable=True,
        sla_status="OPEN",
        independent_technical_evidence=True,
    )

    assert action["recommended_action"] == "physical technical inspection"
    assert action["visit_required"] is True


def test_recent_observed_rain_prevents_automatic_cleaning() -> None:
    result = _service()._cleaning_decision(
        _candidate("persistent underperformance"),
        _site(),
        _forecast(),
        _empty_history(),
        80,
        {"estimated_recoverable_value_inr": 2000.0},
        pd.DataFrame({"rainfall_mm": [3.0]}),
    )

    assert result["cleaning_decision"] == "inspect"
    assert "Recent observed rain" in result["cleaning_reason"]


def test_non_actionable_diagnostic_never_creates_field_visit() -> None:
    action = _service()._recommended_action(
        _candidate("persistent underperformance", actionable=False),
        90,
        "CRITICAL",
        {"cleaning_decision": "schedule", "cleaning_reason": "economic"},
        {"estimated_recoverable_value_inr": 5000.0},
    )

    assert action["visit_required"] is False


def test_recurring_obstruction_can_be_actionable_below_ten_kwh() -> None:
    candidate = _candidate(
        "afternoon time-window candidate",
        total_energy_loss_kwh=6.424,
        expected_energy_kwh=19.265,
        duration_minutes=225,
        secondary_evidence=["persistent underperformance"],
        actionable=False,
    )

    actionable, reason = _service()._operational_actionability(
        candidate,
        _site(capacity_kw=20),
        69.88,
    )

    assert actionable is True
    assert "loss_fraction=0.333" in reason
    assert "loss_per_capacity=0.321" in reason


def test_low_absolute_and_normalized_impact_remains_non_actionable() -> None:
    candidate = _candidate(
        "morning time-window candidate",
        total_energy_loss_kwh=2.0,
        expected_energy_kwh=20.0,
        duration_minutes=300,
        secondary_evidence=["persistent underperformance"],
    )

    actionable, _reason = _service()._operational_actionability(
        candidate,
        _site(capacity_kw=20),
        80,
    )

    assert actionable is False


def test_priority_weights_total_one_and_impact_increases_score() -> None:
    service = _service()
    weights = CONFIG["business"]["priority"]["weights"]
    assert sum(weights.values()) == 1.0
    candidate = _candidate("persistent underperformance")
    low, _, _ = service._priority(
        candidate, 70, {"estimated_recoverable_value_inr": 100}, 0, 25
    )
    high, _, _ = service._priority(
        candidate, 70, {"estimated_recoverable_value_inr": 2500}, 0, 25
    )

    assert high > low


def test_outage_persistence_is_category_normalized_and_bounded() -> None:
    service = _service()
    outage = _candidate("sudden severe underperformance", duration_minutes=390)
    recurring = _candidate("morning time-window candidate", duration_minutes=1560)
    impact = {
        "estimated_recoverable_value_inr": 200,
        "estimated_recoverable_energy_kwh": 25,
    }

    outage_score, _, outage_components = service._priority(
        outage, 85, impact, 75, 70, capacity_kw=5
    )
    recurring_score, _, recurring_components = service._priority(
        recurring, 85, impact, 75, 70, capacity_kw=5
    )

    assert outage_components["persistence"]["normalized"] == 100
    assert recurring_components["persistence"]["normalized"] == 100
    assert outage_components["persistence"]["category_reference_minutes"] == 240
    assert outage_components["route_clustering_benefit"]["normalized"] == 50
    assert recurring_components["route_clustering_benefit"]["normalized"] == 50
    assert outage_score == recurring_score


def test_sustained_outage_priority_exceeds_deferable_partial_loss() -> None:
    service = _service()
    outage_score, _, _ = service._priority(
        _candidate("sudden severe underperformance", duration_minutes=390),
        88,
        {
            "estimated_recoverable_value_inr": 247,
            "estimated_recoverable_energy_kwh": 30,
        },
        75,
        70,
        capacity_kw=5,
    )
    partial_score, _, _ = service._priority(
        _candidate("morning time-window candidate", duration_minutes=1215),
        80,
        {
            "estimated_recoverable_value_inr": 30,
            "estimated_recoverable_energy_kwh": 3.3,
        },
        75,
        70,
        capacity_kw=7.5,
    )

    assert outage_score > partial_score


def test_complaint_urgency_and_sla_risk_increase_priority() -> None:
    service = _service()
    candidate = _candidate("persistent underperformance")
    baseline, _, _ = service._priority(
        candidate, 60, {"estimated_recoverable_value_inr": 500}, 0, 25
    )
    urgent, _, _ = service._priority(
        candidate, 60, {"estimated_recoverable_value_inr": 500}, 100, 100
    )

    assert urgent > baseline


def test_runtime_reasoning_has_no_ground_truth_input() -> None:
    import inspect

    source = inspect.getsource(ServiceDecisionService)

    assert "fault_ground_truth" not in source
    assert "scenario_validation_expected" not in source


def test_queue_ordering_is_deterministic() -> None:
    decisions = [
        {"actionable": True, "priority_score": 50, "site_id": "MH-102", "decision_id": "B"},
        {"actionable": True, "priority_score": 70, "site_id": "MH-103", "decision_id": "C"},
        {"actionable": True, "priority_score": 50, "site_id": "MH-101", "decision_id": "A"},
        {"actionable": False, "priority_score": 90, "site_id": "MH-104", "decision_id": "D"},
    ]

    _service()._assign_queue_ranks(decisions)

    ranks = {item["decision_id"]: item.get("queue_rank") for item in decisions}
    assert ranks == {"B": 3, "C": 1, "A": 2, "D": None}


def test_run_summary_excludes_monitoring_rows_from_remote_actions() -> None:
    service = _service()
    service.repository = MagicMock()
    service.repository.read_consolidated_candidates.return_value = pd.DataFrame(
        [{"site_id": "MH-101"}, {"site_id": "MH-102"}]
    )
    service.repository.read_sites.return_value = pd.DataFrame(
        [
            {"site_id": "MH-101", "weather_zone": "ZONE"},
            {"site_id": "MH-102", "weather_zone": "ZONE"},
        ]
    )
    service.repository.read_telemetry.return_value = pd.DataFrame(
        columns=["site_id", "timestamp"]
    )
    service.repository.read_service_history.return_value = pd.DataFrame(
        columns=["site_id"]
    )
    service.repository.read_weather_forecast.return_value = pd.DataFrame(
        columns=["weather_zone"]
    )
    service.repository.read_weather_history.return_value = pd.DataFrame(
        columns=["weather_zone"]
    )
    service._candidate_telemetry = MagicMock(return_value=pd.DataFrame())
    service._recent_history = MagicMock(return_value=pd.DataFrame())
    service._decision = MagicMock(
        side_effect=[
            {
                "actionable": True,
                "remote_action_available": True,
                "visit_required": False,
                "priority_score": 50,
                "site_id": "MH-101",
                "decision_id": "A",
            },
            {
                "actionable": False,
                "remote_action_available": True,
                "visit_required": False,
                "priority_score": 10,
                "site_id": "MH-102",
                "decision_id": "B",
            },
        ]
    )

    summary = service.run("RUN-TEST")

    assert summary.remote_actions == 1
    assert summary.monitoring == 1
