from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy.engine import Connection

from app.repositories import AnalysisRepository, TelemetryRepository
from app.services.anomaly_detection import AnomalyDetectionService
from app.services.expected_generation import BASELINE_MODEL_VERSION, ExpectedGenerationService
from app.services.model_features import FEATURE_COLUMNS, ExpectedGenerationFeatureBuilder
from app.services.model_training import (
    MODEL_RUN_ID,
    ExpectedModelTrainer,
    ModelArtifactCompatibilityError,
)
from app.services.service_decisions import ServiceDecisionService


@dataclass(frozen=True)
class AnalysisRunSummary:
    analysis_run_id: str
    status: str
    predictor_used: str
    model_version: str
    baseline_metrics: dict
    xgboost_metrics: dict
    model_promotion_decision: str
    sites_analysed: int
    total_intervals: int
    eligible_intervals: int
    ineligible_intervals: int
    anomaly_intervals: int
    raw_grouped_candidates: int
    consolidated_candidates: int
    actionable_candidates: int
    non_actionable_diagnostic_states: int
    duplicate_overlaps_resolved: int
    incident_candidates: int
    communication_incidents: int
    insufficient_evidence_candidates: int
    service_decisions: int
    remote_actions: int
    field_visits: int
    start_timestamp: str
    completion_timestamp: str
    split_summary: dict


class AnalysisOrchestrationService:
    def __init__(
        self,
        connection: Connection,
        config: dict,
        configuration_version: str,
        raw_data_dir: Path,
    ) -> None:
        self.connection = connection
        self.config = config
        self.configuration_version = configuration_version
        self.raw_data_dir = raw_data_dir
        self.analysis_repository = AnalysisRepository(connection)
        self.telemetry_repository = TelemetryRepository(connection)
        self.expected_service = ExpectedGenerationService(connection, config, configuration_version)
        self.feature_builder = ExpectedGenerationFeatureBuilder()

    def run(self, analysis_run_id: str, analysis_date: date | None = None) -> AnalysisRunSummary:
        started_at = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
        self.analysis_repository.create_analysis_run(
            analysis_run_id=analysis_run_id,
            configuration_version=self.configuration_version,
            model_version=None,
            analysis_date=analysis_date,
        )
        try:
            operational_frame = self.expected_service.merged_operational_frame()
            trainer = ExpectedModelTrainer(
                self.config,
                self.raw_data_dir,
            )
            try:
                training_result = trainer.load_compatible_artifact()
            except ModelArtifactCompatibilityError:
                training_result = trainer.train_and_evaluate(
                    self.expected_service,
                    operational_frame,
                )
            self.analysis_repository.insert_model_run(
                {
                    "model_run_id": training_result.model_run_id,
                    "predictor_type": training_result.predictor_type,
                    "model_version": training_result.model_version,
                    "active": training_result.active_predictor_type == "xgboost",
                    "promotion_decision": training_result.promotion_decision,
                    "rejection_reason": training_result.rejection_reason,
                    "metadata_json": {
                        "random_seed": self.config.get("metadata", {}).get("random_seed", 42),
                        "feature_list": training_result.feature_columns,
                        "split_summary": training_result.split_summary,
                        "parameters": self.config.get("modeling", {}).get(
                            "xgboost_parameters",
                            {},
                        ),
                        "baseline_metrics": training_result.baseline_metrics,
                        "xgboost_metrics": training_result.xgboost_metrics,
                        "artifact_paths": training_result.artifact_paths,
                    },
                }
            )

            expected_frame = self._expected_results(operational_frame, training_result)
            expected_frame["analysis_run_id"] = analysis_run_id
            anomaly_service = AnomalyDetectionService(self.config)
            expected_frame = anomaly_service.classify_intervals(expected_frame)
            self.analysis_repository.replace_expected_generation(analysis_run_id, expected_frame)
            telemetry_frame = self.telemetry_repository.read_telemetry_frame()
            incidents = anomaly_service.incident_candidates(
                analysis_run_id,
                expected_frame,
                telemetry_frame,
            )
            self.analysis_repository.replace_incident_candidates(analysis_run_id, incidents)
            decision_summary = ServiceDecisionService(self.connection, self.config).run(
                analysis_run_id
            )
            completed_at = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
            summary = self._summary(
                analysis_run_id,
                training_result,
                expected_frame,
                incidents,
                started_at,
                completed_at,
                decision_summary,
            )
            self.analysis_repository.complete_analysis_run(analysis_run_id, summary.__dict__)
            return summary
        except Exception as exc:
            self.analysis_repository.fail_analysis_run(analysis_run_id, str(exc))
            raise

    def _expected_results(self, operational_frame: pd.DataFrame, training_result) -> pd.DataFrame:
        if training_result.active_predictor_type == "xgboost":
            feature_frame = self.feature_builder.add_derived_columns(operational_frame)
            predictions = pd.Series(
                training_result.model.predict(feature_frame[FEATURE_COLUMNS]),
                index=feature_frame.index,
            )
            predictions = self._post_process_predictions(predictions, feature_frame)
            return self.expected_service.apply_prediction_columns(
                operational_frame,
                predictions,
                training_result.active_model_version,
                "xgboost",
                MODEL_RUN_ID,
            )
        baseline = self.expected_service.baseline_for_operational_frame(operational_frame)
        return self.expected_service.apply_prediction_columns(
            operational_frame,
            baseline,
            BASELINE_MODEL_VERSION,
            "baseline",
            MODEL_RUN_ID,
        )

    def _post_process_predictions(self, predictions: pd.Series, frame: pd.DataFrame) -> pd.Series:
        capacity_factor = float(
            self.config.get("modeling", {}).get("maximum_expected_generation_capacity_factor", 1.2)
        )
        bound = frame["capacity_kw"] * 0.25 * capacity_factor
        daylight = (frame["solar_elevation_degree"] > 0) & (frame["ghi_wm2"] > 0)
        return predictions.clip(lower=0).clip(upper=bound).where(daylight, 0.0)

    def _summary(
        self,
        analysis_run_id: str,
        training_result,
        expected_frame: pd.DataFrame,
        incidents: pd.DataFrame,
        started_at: datetime,
        completed_at: datetime,
        decision_summary,
    ) -> AnalysisRunSummary:
        anomaly_mask = expected_frame["anomaly_state"].isin(
            ["underperformance", "severe underperformance", "near-zero output"]
        )
        consolidated = (
            incidents[incidents["candidate_stage"].eq("consolidated")]
            if not incidents.empty and "candidate_stage" in incidents.columns
            else incidents
        )
        raw_grouped = (
            incidents[incidents["candidate_stage"].eq("raw_grouped")]
            if not incidents.empty and "candidate_stage" in incidents.columns
            else incidents.iloc[0:0]
        )
        communication_incidents = int(
            consolidated["provisional_category"].eq("communication failure").sum()
            if not consolidated.empty
            else 0
        )
        insufficient_evidence = int(
            consolidated["provisional_category"].eq("insufficient evidence").sum()
            if not consolidated.empty
            else 0
        )
        actionable_candidates = (
            int(consolidated["actionable"].sum()) if not consolidated.empty else 0
        )
        non_actionable_diagnostics = int(
            (~consolidated["actionable"].astype(bool)).sum() if not consolidated.empty else 0
        )
        duplicate_overlaps = int(
            consolidated["secondary_evidence"].map(lambda value: len(value or [])).sum()
            if not consolidated.empty
            else 0
        )
        return AnalysisRunSummary(
            analysis_run_id=analysis_run_id,
            status="completed",
            predictor_used=training_result.active_predictor_type,
            model_version=training_result.active_model_version,
            baseline_metrics=training_result.baseline_metrics,
            xgboost_metrics=training_result.xgboost_metrics,
            model_promotion_decision=training_result.promotion_decision,
            sites_analysed=int(expected_frame["site_id"].nunique()),
            total_intervals=len(expected_frame),
            eligible_intervals=int(expected_frame["anomaly_eligible"].sum()),
            ineligible_intervals=int((~expected_frame["anomaly_eligible"]).sum()),
            anomaly_intervals=int(anomaly_mask.sum()),
            raw_grouped_candidates=len(raw_grouped),
            consolidated_candidates=len(consolidated),
            actionable_candidates=actionable_candidates,
            non_actionable_diagnostic_states=non_actionable_diagnostics,
            duplicate_overlaps_resolved=duplicate_overlaps,
            incident_candidates=actionable_candidates,
            communication_incidents=communication_incidents,
            insufficient_evidence_candidates=insufficient_evidence,
            service_decisions=decision_summary.decisions,
            remote_actions=decision_summary.remote_actions,
            field_visits=decision_summary.field_visits,
            start_timestamp=started_at.isoformat(),
            completion_timestamp=completed_at.isoformat(),
            split_summary=training_result.split_summary,
        )
