from __future__ import annotations

import pandas as pd

from app.services.anomaly_detection import AnomalyDetectionService

CONFIG = {
    "analysis": {
        "underperformance_ratio": 0.70,
        "severe_underperformance_ratio": 0.35,
        "near_zero_ratio": 0.05,
        "persistence_intervals": 4,
        "maximum_grouping_gap_intervals": 1,
        "communication_missing_intervals": 4,
        "incident_merge_window_minutes": 180,
        "communication_merge_window_minutes": 360,
        "calibration_warmup_days": 0,
        "minimum_incident_energy_loss_kwh": 2.0,
        "sudden_minimum_energy_loss_kwh": 2.0,
        "sudden_near_zero_ratio": 0.10,
        "persistent_minimum_days": 3,
        "persistent_minimum_energy_loss_kwh": 5.0,
        "persistent_maximum_average_ratio": 0.68,
        "recurring_window_minimum_days": 3,
        "recurring_window_minimum_energy_loss_kwh": 5.0,
        "recurring_window_maximum_outside_loss_ratio": 0.20,
        "actionable_minimum_energy_loss_kwh": 10.0,
        "candidate_overlap_minimum_ratio": 0.50,
        "category_precedence": [
            "communication failure",
            "sudden severe underperformance",
            "morning time-window candidate",
            "afternoon time-window candidate",
            "persistent underperformance",
            "insufficient evidence",
        ],
    }
}


def _intervals(site_id: str, ratios: list[float]) -> pd.DataFrame:
    timestamps = pd.date_range("2026-06-01T10:00:00+05:30", periods=len(ratios), freq="15min")
    return pd.DataFrame(
        {
            "analysis_run_id": "RUN-TEST",
            "site_id": site_id,
            "timestamp": timestamps,
            "expected_generation_kwh": [1.0] * len(ratios),
            "actual_generation_kwh": ratios,
            "signed_residual_kwh": [ratio - 1.0 for ratio in ratios],
            "energy_loss_kwh": [max(1.0 - ratio, 0) for ratio in ratios],
            "performance_ratio": ratios,
            "data_quality_status": ["GOOD"] * len(ratios),
            "anomaly_eligible": [True] * len(ratios),
            "ghi_wm2": [700.0] * len(ratios),
        }
    )


def test_missing_telemetry_becomes_communication_incident_not_performance_incident() -> None:
    service = AnomalyDetectionService(CONFIG)
    telemetry = pd.DataFrame(
        {
            "site_id": ["MH-103"] * 4,
            "timestamp": pd.date_range("2026-06-01T10:00:00+05:30", periods=4, freq="15min"),
            "generation_kwh": [None] * 4,
            "ac_power_kw": [None] * 4,
            "data_received": [False] * 4,
        }
    )
    incidents = service.incident_candidates(
        "RUN-TEST",
        _intervals("MH-101", [1, 1, 1, 1]),
        telemetry,
    )

    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]
    assert consolidated["provisional_category"].tolist() == ["communication failure"]
    assert consolidated["preliminary_recommendation"].tolist() == ["remote connectivity check"]


def test_isolated_dips_are_not_incident_candidates() -> None:
    service = AnomalyDetectionService(CONFIG)
    classified = service.classify_intervals(_intervals("MH-101", [1.0, 0.2, 1.0, 1.0]))
    incidents = service.incident_candidates("RUN-TEST", classified, pd.DataFrame())

    assert incidents.empty


def test_persistent_near_zero_output_becomes_sudden_severe_candidate() -> None:
    service = AnomalyDetectionService(CONFIG)
    classified = service.classify_intervals(_intervals("MH-107", [0.02, 0.02, 0.01, 0.03]))
    incidents = service.incident_candidates("RUN-TEST", classified, pd.DataFrame())

    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]
    assert consolidated["provisional_category"].tolist() == ["sudden severe underperformance"]
    assert consolidated["total_energy_loss_kwh"].iloc[0] > 3.8


def test_fragments_within_merge_window_consolidate() -> None:
    service = AnomalyDetectionService(CONFIG)
    frame = _intervals(
        "MH-107",
        [0.02, 0.02, 0.01, 0.03, 1.0, 1.0, 0.02, 0.02, 0.01, 0.03],
    )
    classified = service.classify_intervals(frame)
    incidents = service.incident_candidates("RUN-TEST", classified, pd.DataFrame())
    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]

    assert len(consolidated) == 1
    assert consolidated["source_candidate_count"].iloc[0] == 2


def test_low_expected_energy_does_not_become_consolidated_candidate() -> None:
    service = AnomalyDetectionService(CONFIG)
    frame = _intervals("MH-101", [0.2, 0.2, 0.2, 0.2])
    frame["expected_generation_kwh"] = 0.1
    frame["energy_loss_kwh"] = 0.08
    frame["ghi_wm2"] = 220
    classified = service.classify_intervals(frame)
    incidents = service.incident_candidates("RUN-TEST", classified, pd.DataFrame())

    assert incidents[incidents["candidate_stage"].eq("consolidated")].empty


def test_local_time_morning_window_uses_asia_kolkata() -> None:
    service = AnomalyDetectionService(CONFIG)
    frames = []
    for day in range(3):
        timestamps = pd.date_range(
            f"2026-06-0{day + 1}T03:30:00Z",
            periods=4,
            freq="15min",
        )
        frame = pd.DataFrame(
            {
                "analysis_run_id": "RUN-TEST",
                "site_id": "MH-109",
                "timestamp": timestamps,
                "expected_generation_kwh": [1.0] * 4,
                "actual_generation_kwh": [0.5] * 4,
                "signed_residual_kwh": [-0.5] * 4,
                "energy_loss_kwh": [0.5] * 4,
                "performance_ratio": [0.5] * 4,
                "data_quality_status": ["GOOD"] * 4,
                "anomaly_eligible": [True] * 4,
                "ghi_wm2": [700.0] * 4,
            }
        )
        frames.append(frame)
    classified = service.classify_intervals(pd.concat(frames, ignore_index=True))
    incidents = service.incident_candidates("RUN-TEST", classified, pd.DataFrame())
    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]

    assert "morning time-window candidate" in set(consolidated["provisional_category"])


def test_overlapping_time_window_and_persistent_candidates_have_one_primary() -> None:
    service = AnomalyDetectionService(CONFIG)
    frames = []
    for day in range(3):
        frame = _intervals("MH-124", [0.5, 0.5, 0.5, 0.5])
        frame["timestamp"] = pd.date_range(
            f"2026-06-0{day + 1}T03:30:00Z",
            periods=4,
            freq="15min",
        )
        frames.append(frame)
    classified = service.classify_intervals(pd.concat(frames, ignore_index=True))

    incidents = service.incident_candidates("RUN-TEST", classified, pd.DataFrame())
    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]

    assert len(consolidated) == 1
    assert consolidated["provisional_category"].iloc[0] == "morning time-window candidate"
    assert consolidated["secondary_evidence"].iloc[0] == ["persistent underperformance"]
    assert consolidated["total_energy_loss_kwh"].iloc[0] == 6.0


def test_insufficient_evidence_uses_evidence_duration_and_is_non_actionable() -> None:
    service = AnomalyDetectionService(CONFIG)
    frame = _intervals("MH-115", [0.5, 0.5, 0.5, 0.5])
    classified = service.classify_intervals(frame)
    missing_times = pd.date_range("2026-06-02T01:00:00Z", periods=10, freq="2h")
    telemetry = pd.DataFrame(
        {
            "site_id": ["MH-115"] * 10,
            "timestamp": missing_times,
            "generation_kwh": [None] * 10,
            "ac_power_kw": [None] * 10,
            "data_received": [False] * 10,
        }
    )

    incidents = service.incident_candidates("RUN-TEST", classified, telemetry)
    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]

    assert len(consolidated) == 1
    assert consolidated["duration_minutes"].iloc[0] == 60
    assert consolidated["operational_qualification_status"].iloc[0] == "diagnostic_only"
    assert not bool(consolidated["actionable"].iloc[0])


def test_low_impact_recurring_candidate_is_generally_non_actionable() -> None:
    service = AnomalyDetectionService(CONFIG)
    frames = []
    for day in range(3):
        frame = _intervals("HEALTHY-SITE", [0.5, 0.5, 0.5, 0.5])
        frame["timestamp"] = pd.date_range(
            f"2026-06-0{day + 1}T03:30:00Z",
            periods=4,
            freq="15min",
        )
        frames.append(frame)
    classified = service.classify_intervals(pd.concat(frames, ignore_index=True))

    incidents = service.incident_candidates("RUN-TEST", classified, pd.DataFrame())
    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]

    assert len(consolidated) == 1
    assert consolidated["total_energy_loss_kwh"].iloc[0] < 10
    assert consolidated["operational_qualification_status"].iloc[0] == "monitor_only"
    assert not bool(consolidated["actionable"].iloc[0])


def test_candidate_generation_is_idempotent_for_same_run_and_input() -> None:
    service = AnomalyDetectionService(CONFIG)
    classified = service.classify_intervals(
        _intervals("MH-107", [0.02, 0.02, 0.01, 0.03])
    )

    first = service.incident_candidates("RUN-IDEMPOTENT", classified, pd.DataFrame())
    second = service.incident_candidates("RUN-IDEMPOTENT", classified, pd.DataFrame())

    assert first.to_dict(orient="records") == second.to_dict(orient="records")
    assert first["incident_candidate_id"].is_unique
