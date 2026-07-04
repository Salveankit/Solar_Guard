from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from app.services.expected_generation import ExpectedGenerationService
from app.services.model_features import (
    FEATURE_COLUMNS,
    FEATURE_SCHEMA_VERSION,
    ExpectedGenerationFeatureBuilder,
)

MODEL_VERSION = "expected-xgb-v2"
MODEL_RUN_ID = "MODEL-RUN-EXPECTED-XGB-V2"


class ModelArtifactCompatibilityError(ValueError):
    """Raised when persisted expected-generation artifacts cannot be reused."""


@dataclass(frozen=True)
class DatasetSplit:
    train: pd.DataFrame
    validation: pd.DataFrame
    test: pd.DataFrame
    summary: dict


@dataclass(frozen=True)
class ModelTrainingResult:
    model_run_id: str
    predictor_type: str
    model_version: str
    active_predictor_type: str
    active_model_version: str
    baseline_metrics: dict
    xgboost_metrics: dict
    promotion_decision: str
    rejection_reason: str | None
    split_summary: dict
    feature_columns: list[str]
    artifact_paths: dict[str, str]
    model: XGBRegressor


class HealthyTrainingDatasetBuilder:
    def __init__(self, config: dict, raw_data_dir: Path) -> None:
        self.config = config
        self.raw_data_dir = raw_data_dir
        self.feature_builder = ExpectedGenerationFeatureBuilder()

    def build(self, operational_frame: pd.DataFrame) -> pd.DataFrame:
        if operational_frame.empty:
            return pd.DataFrame()
        frame = operational_frame.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce")
        frame = self._mark_ground_truth_exclusions(frame)
        minimum_irradiance = float(
            self.config.get("analysis", {}).get("minimum_irradiance_wm2", 200)
        )
        eligible = (
            frame["data_received"].astype(bool)
            & frame["generation_kwh"].notna()
            & frame["source_quality_flag"].eq("GOOD")
            & frame["weather_quality_flag"].eq("GOOD")
            & (frame["solar_elevation_degree"] > 0)
            & (frame["ghi_wm2"] >= minimum_irradiance)
            & frame["capacity_kw"].notna()
            & frame["site_efficiency_factor"].notna()
            & ~frame["excluded_from_training"]
        )
        training = frame.loc[eligible].copy()
        training["target_generation_kwh"] = training["generation_kwh"].astype(float)
        feature_frame = self.feature_builder.add_derived_columns(training)
        for column in FEATURE_COLUMNS:
            training[column] = feature_frame[column].fillna(0.0)
        return training.sort_values(["timestamp", "site_id"]).reset_index(drop=True)

    def _mark_ground_truth_exclusions(self, frame: pd.DataFrame) -> pd.DataFrame:
        marked = frame.copy()
        marked["excluded_from_training"] = False
        ground_truth_path = self.raw_data_dir / "fault_ground_truth.csv"
        if not ground_truth_path.exists():
            return marked
        ground_truth = pd.read_csv(ground_truth_path)
        ground_truth["start_timestamp"] = pd.to_datetime(
            ground_truth["start_timestamp"],
            errors="coerce",
        )
        ground_truth["end_timestamp"] = pd.to_datetime(
            ground_truth["end_timestamp"],
            errors="coerce",
        )
        for incident in ground_truth.itertuples(index=False):
            mask = (
                marked["site_id"].eq(incident.site_id)
                & (marked["timestamp"] >= incident.start_timestamp)
                & (marked["timestamp"] <= incident.end_timestamp)
            )
            marked.loc[mask, "excluded_from_training"] = True
        return marked


class ChronologicalSplitter:
    def split(self, frame: pd.DataFrame) -> DatasetSplit:
        if frame.empty:
            empty_summary = {
                "train_rows": 0,
                "validation_rows": 0,
                "test_rows": 0,
                "timestamp_overlap": False,
            }
            return DatasetSplit(frame, frame, frame, empty_summary)
        timestamps = pd.Series(frame["timestamp"].dropna().sort_values().unique())
        train_cut = int(len(timestamps) * 0.70)
        validation_cut = int(len(timestamps) * 0.85)
        train_times = set(timestamps.iloc[:train_cut])
        validation_times = set(timestamps.iloc[train_cut:validation_cut])
        test_times = set(timestamps.iloc[validation_cut:])
        train = frame[frame["timestamp"].isin(train_times)].copy()
        validation = frame[frame["timestamp"].isin(validation_times)].copy()
        test = frame[frame["timestamp"].isin(test_times)].copy()
        summary = {
            "train_rows": len(train),
            "validation_rows": len(validation),
            "test_rows": len(test),
            "train_site_count": int(train["site_id"].nunique()),
            "validation_site_count": int(validation["site_id"].nunique()),
            "test_site_count": int(test["site_id"].nunique()),
            "train_range": _date_range(train),
            "validation_range": _date_range(validation),
            "test_range": _date_range(test),
            "target_distribution": {
                "train_mean": _safe_float(train["target_generation_kwh"].mean()),
                "validation_mean": _safe_float(validation["target_generation_kwh"].mean()),
                "test_mean": _safe_float(test["target_generation_kwh"].mean()),
            },
            "timestamp_overlap": bool(
                train_times.intersection(validation_times)
                or train_times.intersection(test_times)
                or validation_times.intersection(test_times)
            ),
        }
        return DatasetSplit(train, validation, test, summary)


class ExpectedModelTrainer:
    def __init__(self, config: dict, raw_data_dir: Path, models_dir: Path = Path("models")) -> None:
        self.config = config
        self.raw_data_dir = raw_data_dir
        self.models_dir = models_dir
        self.feature_builder = ExpectedGenerationFeatureBuilder()

    def load_compatible_artifact(self) -> ModelTrainingResult:
        model_path = self.models_dir / "expected_generation_model.joblib"
        feature_path = self.models_dir / "feature_schema.json"
        metrics_path = self.models_dir / "model_metrics.json"
        try:
            feature_metadata = json.loads(feature_path.read_text(encoding="utf-8"))
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            raise ModelArtifactCompatibilityError(
                "Model artifact metadata is missing or unreadable"
            ) from exc

        if feature_metadata.get("feature_schema_version") != FEATURE_SCHEMA_VERSION:
            raise ModelArtifactCompatibilityError("Feature schema version is incompatible")
        if feature_metadata.get("feature_columns") != FEATURE_COLUMNS:
            raise ModelArtifactCompatibilityError("Feature columns are incompatible")
        if metrics.get("model_version") != MODEL_VERSION:
            raise ModelArtifactCompatibilityError("Model version metadata is incompatible")
        if metrics.get("feature_timezone") != "Asia/Kolkata":
            raise ModelArtifactCompatibilityError("Model feature timezone is incompatible")
        if metrics.get("promotion_decision") != "promoted":
            raise ModelArtifactCompatibilityError("Persisted model is not promoted")
        try:
            model = joblib.load(model_path)
        except (OSError, ValueError, TypeError, EOFError) as exc:
            raise ModelArtifactCompatibilityError(
                "Persisted model is missing or unreadable"
            ) from exc
        model_features = list(getattr(model, "feature_names_in_", []))
        if model_features and model_features != FEATURE_COLUMNS:
            raise ModelArtifactCompatibilityError("Persisted model feature names are incompatible")
        if not callable(getattr(model, "predict", None)):
            raise ModelArtifactCompatibilityError("Persisted model has no prediction interface")

        paths = {
            "model": str(model_path),
            "feature_schema": str(feature_path),
            "metrics": str(metrics_path),
        }
        return ModelTrainingResult(
            model_run_id=MODEL_RUN_ID,
            predictor_type="xgboost",
            model_version=MODEL_VERSION,
            active_predictor_type="xgboost",
            active_model_version=MODEL_VERSION,
            baseline_metrics=metrics.get("baseline_metrics") or {},
            xgboost_metrics=metrics.get("xgboost_metrics") or {},
            promotion_decision="promoted",
            rejection_reason=None,
            split_summary=metrics.get("split_summary") or {},
            feature_columns=list(FEATURE_COLUMNS),
            artifact_paths=paths,
            model=model,
        )

    def train_and_evaluate(
        self,
        expected_service: ExpectedGenerationService,
        operational_frame: pd.DataFrame,
    ) -> ModelTrainingResult:
        dataset = HealthyTrainingDatasetBuilder(self.config, self.raw_data_dir).build(
            operational_frame
        )
        split = ChronologicalSplitter().split(dataset)
        if split.train.empty or split.validation.empty or split.test.empty:
            raise ValueError("Insufficient healthy daylight data for model training")

        seed = int(self.config.get("metadata", {}).get("random_seed", 42))
        np.random.seed(seed)
        params = {
            **self.config.get("modeling", {}).get("xgboost_parameters", {}),
            "random_state": seed,
        }
        model = XGBRegressor(**params)
        model.fit(
            split.train[FEATURE_COLUMNS],
            split.train["target_generation_kwh"],
            eval_set=[
                (split.validation[FEATURE_COLUMNS], split.validation["target_generation_kwh"])
            ],
            verbose=False,
        )

        baseline_predictions = expected_service.baseline_for_operational_frame(split.test)
        xgb_predictions = pd.Series(
            model.predict(split.test[FEATURE_COLUMNS]),
            index=split.test.index,
        )
        xgb_predictions = self._post_process_predictions(xgb_predictions, split.test)
        baseline_metrics = _metrics(split.test["target_generation_kwh"], baseline_predictions)
        xgboost_metrics = _metrics(split.test["target_generation_kwh"], xgb_predictions)
        promotion = self._promotion_decision(baseline_metrics, xgboost_metrics)
        active_predictor = "xgboost" if promotion[0] == "promoted" else "baseline"
        active_version = MODEL_VERSION if active_predictor == "xgboost" else "expected-baseline-v1"
        artifact_paths = self._persist_artifacts(
            model,
            baseline_metrics,
            xgboost_metrics,
            split,
            promotion,
        )
        return ModelTrainingResult(
            model_run_id=MODEL_RUN_ID,
            predictor_type="xgboost",
            model_version=MODEL_VERSION,
            active_predictor_type=active_predictor,
            active_model_version=active_version,
            baseline_metrics=baseline_metrics,
            xgboost_metrics=xgboost_metrics,
            promotion_decision=promotion[0],
            rejection_reason=promotion[1],
            split_summary=split.summary,
            feature_columns=list(FEATURE_COLUMNS),
            artifact_paths=artifact_paths,
            model=model,
        )

    def _post_process_predictions(self, predictions: pd.Series, frame: pd.DataFrame) -> pd.Series:
        capacity_factor = float(
            self.config.get("modeling", {}).get("maximum_expected_generation_capacity_factor", 1.2)
        )
        capacity_bound = frame["capacity_kw"] * 0.25 * capacity_factor
        daylight = (frame["solar_elevation_degree"] > 0) & (frame["ghi_wm2"] > 0)
        return predictions.clip(lower=0).clip(upper=capacity_bound).where(daylight, 0.0)

    def _promotion_decision(
        self,
        baseline_metrics: dict,
        xgb_metrics: dict,
    ) -> tuple[str, str | None]:
        metric_name = str(
            self.config.get("modeling", {}).get("model_promotion_metric", "normalised_mae")
        )
        margin = float(self.config.get("modeling", {}).get("model_promotion_margin", 0.10))
        baseline_value = baseline_metrics.get(metric_name)
        xgb_value = xgb_metrics.get(metric_name)
        if baseline_value is None or xgb_value is None or baseline_value <= 0:
            return "rejected", "invalid metric values"
        improvement = (baseline_value - xgb_value) / baseline_value
        if improvement >= margin:
            return "promoted", None
        return "rejected", f"{metric_name} improvement {improvement:.3f} below margin {margin:.3f}"

    def _persist_artifacts(
        self,
        model: XGBRegressor,
        baseline_metrics: dict,
        xgboost_metrics: dict,
        split: DatasetSplit,
        promotion: tuple[str, str | None],
    ) -> dict[str, str]:
        self.models_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.models_dir / "expected_generation_model.joblib"
        feature_path = self.models_dir / "feature_schema.json"
        metrics_path = self.models_dir / "model_metrics.json"
        previous_metrics = None
        if metrics_path.exists():
            try:
                previous_metadata = json.loads(metrics_path.read_text(encoding="utf-8"))
                previous_metrics = previous_metadata.get("xgboost_metrics")
            except (OSError, ValueError, TypeError):
                previous_metrics = None
        joblib.dump(model, model_path)
        feature_path.write_text(
            json.dumps(
                {
                    "feature_schema_version": FEATURE_SCHEMA_VERSION,
                    "feature_columns": FEATURE_COLUMNS,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        metrics_path.write_text(
            json.dumps(
                {
                    "model_version": MODEL_VERSION,
                    "feature_timezone": "Asia/Kolkata",
                    "created_at": datetime.now(tz=ZoneInfo("Asia/Kolkata")).isoformat(),
                    "split_summary": split.summary,
                    "baseline_metrics": baseline_metrics,
                    "xgboost_metrics": xgboost_metrics,
                    "previous_xgboost_metrics": previous_metrics,
                    "promotion_decision": promotion[0],
                    "rejection_reason": promotion[1],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return {
            "model": str(model_path),
            "feature_schema": str(feature_path),
            "metrics": str(metrics_path),
        }


def _metrics(actual: pd.Series, predicted: pd.Series) -> dict:
    actual = actual.astype(float)
    predicted = predicted.astype(float)
    mae = float(mean_absolute_error(actual, predicted))
    rmse = float(np.sqrt(mean_squared_error(actual, predicted)))
    denominator = float(actual.mean()) if float(actual.mean()) > 0 else 1.0
    return {
        "mae": mae,
        "rmse": rmse,
        "normalised_mae": mae / denominator,
        "normalised_mae_denominator": "mean daytime actual generation on shared test split",
        "r2": float(r2_score(actual, predicted)) if len(actual) > 1 else None,
    }


def _date_range(frame: pd.DataFrame) -> dict[str, str | None]:
    if frame.empty:
        return {"start": None, "end": None}
    return {
        "start": pd.to_datetime(frame["timestamp"].min()).isoformat(),
        "end": pd.to_datetime(frame["timestamp"].max()).isoformat(),
    }


def _safe_float(value: float) -> float | None:
    if pd.isna(value):
        return None
    return float(value)
