from __future__ import annotations

import json
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection

OWNED_TABLES = [
    "route_stops",
    "route_plans",
    "service_jobs",
    "incident_candidates",
    "expected_generation_results",
    "expected_model_runs",
    "site_diagnostics",
    "analysis_runs",
    "service_history",
    "telemetry",
    "weather_forecast",
    "weather_history",
    "technicians",
    "sites",
]


class AnalysisRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def clear_demo_data(self) -> None:
        table_list = ", ".join(OWNED_TABLES)
        self.connection.execute(text(f"TRUNCATE TABLE {table_list} RESTART IDENTITY"))

    def insert_service_history(self, frame: pd.DataFrame) -> None:
        frame.to_sql(
            "service_history",
            self.connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

    def insert_technicians(self, frame: pd.DataFrame) -> None:
        frame.to_sql(
            "technicians",
            self.connection,
            if_exists="append",
            index=False,
            method="multi",
        )

    def count_table(self, table_name: str) -> int:
        if table_name not in OWNED_TABLES:
            raise ValueError(f"Unsupported SolarGuard table: {table_name}")
        return int(self.connection.execute(text(f"SELECT count(*) FROM {table_name}")).scalar_one())

    def create_analysis_run(
        self,
        analysis_run_id: str,
        configuration_version: str,
        model_version: str,
        analysis_date: date | None = None,
    ) -> None:
        self.connection.execute(
            text("DELETE FROM incident_candidates WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        self.connection.execute(
            text(
                "DELETE FROM expected_generation_results "
                "WHERE analysis_run_id = :analysis_run_id"
            ),
            {"analysis_run_id": analysis_run_id},
        )
        self.connection.execute(
            text("DELETE FROM site_diagnostics WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        self.connection.execute(
            text(
                """
                DELETE FROM route_stops
                WHERE route_plan_id IN (
                    SELECT route_plan_id
                    FROM route_plans
                    WHERE analysis_run_id = :analysis_run_id
                )
                """
            ),
            {"analysis_run_id": analysis_run_id},
        )
        self.connection.execute(
            text("DELETE FROM service_jobs WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        self.connection.execute(
            text("DELETE FROM route_plans WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        self.connection.execute(
            text("DELETE FROM analysis_runs WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        self.connection.execute(
            text(
                """
                INSERT INTO analysis_runs (
                    analysis_run_id, status, analysis_date, started_at,
                    configuration_version, model_version
                )
                VALUES (
                    :analysis_run_id, 'RUNNING', :analysis_date, :started_at,
                    :configuration_version, :model_version
                )
                """
            ),
            {
                "analysis_run_id": analysis_run_id,
                "analysis_date": analysis_date,
                "started_at": datetime.now(tz=ZoneInfo("Asia/Kolkata")),
                "configuration_version": configuration_version,
                "model_version": model_version,
            },
        )

    def complete_analysis_run(self, analysis_run_id: str, summary: dict) -> None:
        self.connection.execute(
            text(
                """
                UPDATE analysis_runs
                SET status = 'COMPLETED',
                    completed_at = :completed_at,
                    summary_json = CAST(:summary_json AS JSON),
                    model_version = COALESCE(:model_version, model_version)
                WHERE analysis_run_id = :analysis_run_id
                """
            ),
            {
                "analysis_run_id": analysis_run_id,
                "completed_at": datetime.now(tz=ZoneInfo("Asia/Kolkata")),
                "summary_json": json.dumps(summary),
                "model_version": summary.get("model_version"),
            },
        )

    def fail_analysis_run(self, analysis_run_id: str, message: str) -> None:
        self.connection.execute(
            text(
                """
                UPDATE analysis_runs
                SET status = 'FAILED',
                    completed_at = :completed_at,
                    error_message = :error_message
                WHERE analysis_run_id = :analysis_run_id
                """
            ),
            {
                "analysis_run_id": analysis_run_id,
                "completed_at": datetime.now(tz=ZoneInfo("Asia/Kolkata")),
                "error_message": message[:500],
            },
        )

    def insert_model_run(self, metadata: dict) -> None:
        self.connection.execute(
            text(
                """
                INSERT INTO expected_model_runs (
                    model_run_id, predictor_type, model_version, created_at, active,
                    promotion_decision, rejection_reason, metadata_json
                )
                VALUES (
                    :model_run_id, :predictor_type, :model_version, :created_at, :active,
                    :promotion_decision, :rejection_reason, CAST(:metadata_json AS JSON)
                )
                ON CONFLICT (model_run_id) DO UPDATE
                SET active = EXCLUDED.active,
                    promotion_decision = EXCLUDED.promotion_decision,
                    rejection_reason = EXCLUDED.rejection_reason,
                    metadata_json = EXCLUDED.metadata_json
                """
            ),
            {
                **metadata,
                "created_at": metadata.get("created_at")
                or datetime.now(tz=ZoneInfo("Asia/Kolkata")),
                "metadata_json": json.dumps(metadata.get("metadata_json") or {}),
            },
        )

    def replace_expected_generation(self, analysis_run_id: str, frame: pd.DataFrame) -> None:
        self.connection.execute(
            text(
                "DELETE FROM expected_generation_results "
                "WHERE analysis_run_id = :analysis_run_id"
            ),
            {"analysis_run_id": analysis_run_id},
        )
        frame.to_sql(
            "expected_generation_results",
            self.connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

    def replace_incident_candidates(self, analysis_run_id: str, frame: pd.DataFrame) -> None:
        self.connection.execute(
            text("DELETE FROM incident_candidates WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        if frame.empty:
            return
        insert_sql = text(
            """
            INSERT INTO incident_candidates (
                incident_candidate_id, analysis_run_id, site_id, start_timestamp,
                end_timestamp, interval_count, duration_minutes, expected_energy_kwh,
                actual_energy_kwh, total_energy_loss_kwh, average_performance_ratio,
                minimum_performance_ratio, anomaly_state, dominant_evidence,
                data_completeness, provisional_category, preliminary_recommendation,
                candidate_stage, source_candidate_count, secondary_evidence,
                operational_qualification_status, actionable
            )
            VALUES (
                :incident_candidate_id, :analysis_run_id, :site_id, :start_timestamp,
                :end_timestamp, :interval_count, :duration_minutes, :expected_energy_kwh,
                :actual_energy_kwh, :total_energy_loss_kwh, :average_performance_ratio,
                :minimum_performance_ratio, :anomaly_state, CAST(:dominant_evidence AS JSON),
                :data_completeness, :provisional_category, :preliminary_recommendation,
                :candidate_stage, :source_candidate_count, CAST(:secondary_evidence AS JSON),
                :operational_qualification_status, :actionable
            )
            """
        )
        rows = []
        for row in frame.to_dict(orient="records"):
            row["dominant_evidence"] = json.dumps(row.get("dominant_evidence") or {})
            row["secondary_evidence"] = json.dumps(row.get("secondary_evidence") or [])
            row["candidate_stage"] = row.get("candidate_stage") or "consolidated"
            row["source_candidate_count"] = row.get("source_candidate_count") or 1
            row["operational_qualification_status"] = (
                row.get("operational_qualification_status") or "qualified"
            )
            row["actionable"] = bool(row.get("actionable", True))
            rows.append(row)
        self.connection.execute(insert_sql, rows)

    def read_expected_generation_frame(self, analysis_run_id: str) -> pd.DataFrame:
        return pd.read_sql_query(
            text(
                """
            SELECT analysis_run_id, site_id, timestamp, expected_generation_kwh,
                   actual_generation_kwh, signed_residual_kwh, energy_loss_kwh,
                   performance_ratio, ghi_wm2, solar_elevation_degree, model_run_id,
                   predictor_type, model_version, eligible, anomaly_eligible, anomaly_state,
                   data_quality_status
            FROM expected_generation_results
            WHERE analysis_run_id = :analysis_run_id
            ORDER BY site_id, timestamp
            """
            ),
            self.connection,
            params={"analysis_run_id": analysis_run_id},
        )

    def read_incident_candidates_frame(self, analysis_run_id: str) -> pd.DataFrame:
        return pd.read_sql_query(
            text(
                """
                SELECT *
                FROM incident_candidates
                WHERE analysis_run_id = :analysis_run_id
                ORDER BY site_id, start_timestamp
                """
            ),
            self.connection,
            params={"analysis_run_id": analysis_run_id},
        )
