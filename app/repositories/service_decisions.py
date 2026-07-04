from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection


class ServiceDecisionRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def read_consolidated_candidates(self, analysis_run_id: str) -> pd.DataFrame:
        return pd.read_sql_query(
            text(
                """
                SELECT * FROM incident_candidates
                WHERE analysis_run_id = :analysis_run_id
                  AND candidate_stage = 'consolidated'
                ORDER BY site_id, start_timestamp
                """
            ),
            self.connection,
            params={"analysis_run_id": analysis_run_id},
        )

    def read_sites(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT site_id, site_name, capacity_kw, latitude, longitude, weather_zone,
                   azimuth_degree, tariff_per_kwh, service_region, customer_type,
                   warranty_end_date, cleaning_cost_inr, visit_cost_inr
            FROM sites ORDER BY site_id
            """,
            self.connection,
        )

    def read_telemetry(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT site_id, timestamp, generation_kwh, ac_power_kw, dc_voltage,
                   dc_current, ac_voltage, inverter_status, fault_code, data_received
            FROM telemetry ORDER BY site_id, timestamp
            """,
            self.connection,
        )

    def read_service_history(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT ticket_id, site_id, reported_at, complaint_type, complaint_severity,
                   resolution, resolved_at, remote_resolution, repeat_complaint, sla_due_at
            FROM service_history ORDER BY site_id, reported_at
            """,
            self.connection,
        )

    def read_weather_forecast(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT weather_zone, timestamp, ghi_wm2, rainfall_mm, cloud_cover_pct
            FROM weather_forecast ORDER BY weather_zone, timestamp
            """,
            self.connection,
        )

    def read_weather_history(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT weather_zone, timestamp, ghi_wm2, rainfall_mm, cloud_cover_pct
            FROM weather_history ORDER BY weather_zone, timestamp
            """,
            self.connection,
        )

    def replace_decisions(self, analysis_run_id: str, decisions: list[dict]) -> None:
        self.connection.execute(
            text("DELETE FROM service_decisions WHERE analysis_run_id = :analysis_run_id"),
            {"analysis_run_id": analysis_run_id},
        )
        if not decisions:
            return
        statement = text(
            """
            INSERT INTO service_decisions (
                decision_id, analysis_run_id, incident_candidate_id, site_id,
                probable_issue, confidence_score, confidence_label,
                supporting_evidence, contradictory_evidence, confidence_components,
                expected_energy_kwh, actual_energy_kwh, estimated_energy_loss_kwh,
                estimated_value_at_risk_inr, projected_seven_day_loss_kwh,
                estimated_recoverable_energy_kwh, estimated_recoverable_value_inr,
                tariff_per_kwh, visit_cost_inr, cleaning_cost_inr,
                cleaning_decision, cleaning_reason, recommended_action, action_reason,
                prerequisite_remote_checks, escalation_condition,
                remote_action_available, visit_required, actionable,
                complaint_severity, sla_status, priority_score, priority_label,
                priority_components, queue_rank, created_at
            ) VALUES (
                :decision_id, :analysis_run_id, :incident_candidate_id, :site_id,
                :probable_issue, :confidence_score, :confidence_label,
                CAST(:supporting_evidence AS JSON), CAST(:contradictory_evidence AS JSON),
                CAST(:confidence_components AS JSON), :expected_energy_kwh,
                :actual_energy_kwh, :estimated_energy_loss_kwh,
                :estimated_value_at_risk_inr, :projected_seven_day_loss_kwh,
                :estimated_recoverable_energy_kwh, :estimated_recoverable_value_inr,
                :tariff_per_kwh, :visit_cost_inr, :cleaning_cost_inr,
                :cleaning_decision, :cleaning_reason, :recommended_action, :action_reason,
                CAST(:prerequisite_remote_checks AS JSON), :escalation_condition,
                :remote_action_available, :visit_required, :actionable,
                :complaint_severity, :sla_status, :priority_score, :priority_label,
                CAST(:priority_components AS JSON), :queue_rank, :created_at
            )
            """
        )
        rows = []
        for decision in decisions:
            row = decision.copy()
            for key in (
                "supporting_evidence",
                "contradictory_evidence",
                "confidence_components",
                "prerequisite_remote_checks",
                "priority_components",
            ):
                row[key] = json.dumps(row.get(key) or ([] if "evidence" in key else {}))
            row["created_at"] = datetime.now(tz=ZoneInfo("Asia/Kolkata"))
            rows.append(row)
        self.connection.execute(statement, rows)

    def latest_decision_run_id(self) -> str | None:
        return self.connection.execute(
            text(
                """
                SELECT analysis_run_id FROM service_decisions
                GROUP BY analysis_run_id
                ORDER BY max(created_at) DESC LIMIT 1
                """
            )
        ).scalar_one_or_none()

    def read_decisions(self, analysis_run_id: str) -> list[dict]:
        rows = self.connection.execute(
            text(
                """
                SELECT * FROM service_decisions
                WHERE analysis_run_id = :analysis_run_id
                ORDER BY queue_rank NULLS LAST, site_id
                """
            ),
            {"analysis_run_id": analysis_run_id},
        ).mappings()
        return [dict(row) for row in rows]

    def read_site(self, site_id: str) -> dict | None:
        row = (
            self.connection.execute(
                text("SELECT * FROM sites WHERE site_id = :site_id"),
                {"site_id": site_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def read_site_candidate(self, analysis_run_id: str, candidate_id: str) -> dict | None:
        row = (
            self.connection.execute(
                text(
                    """
                SELECT * FROM incident_candidates
                WHERE analysis_run_id = :analysis_run_id
                  AND incident_candidate_id = :candidate_id
                """
                ),
                {"analysis_run_id": analysis_run_id, "candidate_id": candidate_id},
            )
            .mappings()
            .first()
        )
        return dict(row) if row else None

    def read_site_performance(self, analysis_run_id: str, site_id: str) -> list[dict]:
        rows = self.connection.execute(
            text(
                """
                SELECT timestamp, expected_generation_kwh, actual_generation_kwh,
                       signed_residual_kwh, energy_loss_kwh, performance_ratio,
                       ghi_wm2, anomaly_state, data_quality_status
                FROM expected_generation_results
                WHERE analysis_run_id = :analysis_run_id AND site_id = :site_id
                ORDER BY timestamp
                """
            ),
            {"analysis_run_id": analysis_run_id, "site_id": site_id},
        ).mappings()
        return [dict(row) for row in rows]
