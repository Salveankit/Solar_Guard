from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest
from xgboost import XGBRegressor

from app.services.model_features import (
    FEATURE_COLUMNS,
    FEATURE_SCHEMA_VERSION,
    ExpectedGenerationFeatureBuilder,
)
from app.services.model_training import (
    MODEL_VERSION,
    ChronologicalSplitter,
    ExpectedModelTrainer,
    HealthyTrainingDatasetBuilder,
    ModelArtifactCompatibilityError,
)


def _operational_frame() -> pd.DataFrame:
    timestamps = pd.date_range("2026-06-01T10:00:00+05:30", periods=12, freq="15min")
    return pd.DataFrame(
        [
            {
                "site_id": "MH-101",
                "timestamp": timestamp,
                "generation_kwh": 0.8,
                "data_received": True,
                "source_quality_flag": "GOOD",
                "weather_quality_flag": "GOOD",
                "solar_elevation_degree": 45.0,
                "solar_azimuth_degree": 160.0,
                "ghi_wm2": 700.0,
                "dni_wm2": 500.0,
                "dhi_wm2": 150.0,
                "temperature_c": 32.0,
                "cloud_cover_pct": 20.0,
                "rainfall_mm": 0.0,
                "wind_speed_ms": 2.0,
                "capacity_kw": 5.0,
                "site_efficiency_factor": 0.9,
                "tilt_degree": 18.0,
                "azimuth_degree": 180.0,
                "latitude": 18.5,
                "longitude": 73.8,
            }
            for timestamp in timestamps
        ]
    )


def test_training_builder_excludes_ground_truth_windows(tmp_path: Path) -> None:
    raw_dir = tmp_path
    (raw_dir / "fault_ground_truth.csv").write_text(
        "incident_id,site_id,fault_type,start_timestamp,end_timestamp,severity,"
        "injected_loss_pct,expected_action,expected_visit_required,notes\n"
        "INC-001,MH-101,SUDDEN_OUTAGE,2026-06-01T10:30:00+05:30,"
        "2026-06-01T11:00:00+05:30,HIGH,90,VISIT,true,test\n",
        encoding="utf-8",
    )
    dataset = HealthyTrainingDatasetBuilder(
        {"analysis": {"minimum_irradiance_wm2": 200}},
        raw_dir,
    ).build(_operational_frame())

    excluded = pd.date_range("2026-06-01T10:30:00+05:30", periods=3, freq="15min")
    assert not set(excluded).intersection(set(dataset["timestamp"]))
    assert "fault_type" not in dataset.columns
    assert all(column in dataset.columns for column in FEATURE_COLUMNS)


def test_chronological_split_has_no_timestamp_overlap() -> None:
    frame = _operational_frame()
    frame["target_generation_kwh"] = frame["generation_kwh"]
    for column in FEATURE_COLUMNS:
        frame[column] = ExpectedGenerationFeatureBuilder().add_derived_columns(frame)[column]

    split = ChronologicalSplitter().split(frame)

    train_times = set(split.train["timestamp"])
    validation_times = set(split.validation["timestamp"])
    test_times = set(split.test["timestamp"])
    assert not train_times.intersection(validation_times)
    assert not train_times.intersection(test_times)
    assert not validation_times.intersection(test_times)
    assert split.summary["timestamp_overlap"] is False


def test_time_features_convert_utc_timestamp_to_asia_kolkata() -> None:
    frame = _operational_frame().iloc[:1].copy()
    frame["timestamp"] = pd.to_datetime(["2026-06-01T03:30:00Z"])

    features = ExpectedGenerationFeatureBuilder().add_derived_columns(frame)

    assert features["local_hour"].iloc[0] == 9.0
    assert features["morning_indicator"].iloc[0] == 1.0
    assert features["afternoon_indicator"].iloc[0] == 0.0
    assert np.isclose(features["hour_sin"].iloc[0], np.sin(2 * np.pi * 9 / 24))


def test_local_date_boundary_uses_asia_kolkata() -> None:
    frame = _operational_frame().iloc[:1].copy()
    frame["timestamp"] = pd.to_datetime(["2026-06-01T20:00:00Z"])

    features = ExpectedGenerationFeatureBuilder().add_derived_columns(frame)

    assert str(features["local_date"].iloc[0]) == "2026-06-02"
    assert features["day_of_year_sin"].iloc[0] == pytest.approx(
        np.sin(2 * np.pi * 153 / 365)
    )


def test_naive_timestamp_is_rejected_for_model_features() -> None:
    frame = _operational_frame().iloc[:1].copy()
    frame["timestamp"] = pd.to_datetime(["2026-06-01T09:00:00"])

    with pytest.raises(ValueError, match="timezone-aware"):
        ExpectedGenerationFeatureBuilder().add_derived_columns(frame)


def test_compatible_model_artifact_is_loaded_without_training(tmp_path: Path) -> None:
    model = XGBRegressor(n_estimators=1, max_depth=1)
    features = pd.DataFrame([[0.0] * len(FEATURE_COLUMNS)], columns=FEATURE_COLUMNS)
    model.fit(features, [0.0])
    joblib.dump(model, tmp_path / "expected_generation_model.joblib")
    (tmp_path / "feature_schema.json").write_text(
        json.dumps(
            {
                "feature_schema_version": FEATURE_SCHEMA_VERSION,
                "feature_columns": FEATURE_COLUMNS,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "model_metrics.json").write_text(
        json.dumps(
            {
                "model_version": MODEL_VERSION,
                "feature_timezone": "Asia/Kolkata",
                "promotion_decision": "promoted",
                "baseline_metrics": {"mae": 1.0},
                "xgboost_metrics": {"mae": 0.5},
                "split_summary": {"timestamp_overlap": False},
            }
        ),
        encoding="utf-8",
    )

    result = ExpectedModelTrainer({}, tmp_path, models_dir=tmp_path).load_compatible_artifact()

    assert result.active_predictor_type == "xgboost"
    assert result.model_version == MODEL_VERSION


def test_incompatible_feature_schema_rejects_model_artifact(tmp_path: Path) -> None:
    (tmp_path / "expected_generation_model.joblib").write_bytes(b"not-used")
    (tmp_path / "feature_schema.json").write_text(
        json.dumps({"feature_schema_version": "old", "feature_columns": FEATURE_COLUMNS}),
        encoding="utf-8",
    )
    (tmp_path / "model_metrics.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ModelArtifactCompatibilityError):
        ExpectedModelTrainer({}, tmp_path, models_dir=tmp_path).load_compatible_artifact()
