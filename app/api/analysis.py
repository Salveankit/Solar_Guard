from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings
from app.database.session import get_engine
from app.services.analysis_orchestration import AnalysisOrchestrationService
from app.services.expected_generation import ExpectedGenerationService

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


class RunAnalysisRequest(BaseModel):
    analysis_date: date | None = None


@router.post("/run-expected-generation")
def run_expected_generation(request: RunAnalysisRequest) -> dict:
    settings = get_settings()
    timestamp = datetime.now(tz=ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d%H%M%S")
    analysis_run_id = f"RUN-{timestamp}"
    with get_engine().begin() as connection:
        service = ExpectedGenerationService(
            connection=connection,
            config=settings.config,
            configuration_version=settings.configuration_version,
        )
        summary = service.run_baseline(
            analysis_run_id=analysis_run_id,
            analysis_date=request.analysis_date,
        )
    return {
        "analysis_run_id": summary.analysis_run_id,
        "status": "completed",
        "expected_generation_rows": summary.rows_persisted,
        "eligible_rows": summary.eligible_rows,
        "model_version": summary.model_version,
        "configuration_version": settings.configuration_version,
    }


@router.post("/run")
def run_analysis(request: RunAnalysisRequest) -> dict:
    settings = get_settings()
    timestamp = datetime.now(tz=ZoneInfo("Asia/Kolkata")).strftime("%Y%m%d%H%M%S")
    analysis_run_id = f"RUN-{timestamp}"
    with get_engine().begin() as connection:
        service = AnalysisOrchestrationService(
            connection=connection,
            config=settings.config,
            configuration_version=settings.configuration_version,
            raw_data_dir=settings.resolved_raw_data_dir,
        )
        summary = service.run(
            analysis_run_id=analysis_run_id,
            analysis_date=request.analysis_date,
        )
    return {
        "analysis_run_id": summary.analysis_run_id,
        "status": summary.status,
        "predictor_used": summary.predictor_used,
        "model_version": summary.model_version,
        "baseline_metrics": summary.baseline_metrics,
        "xgboost_metrics": summary.xgboost_metrics,
        "model_promotion_decision": summary.model_promotion_decision,
        "sites_analysed": summary.sites_analysed,
        "total_intervals": summary.total_intervals,
        "eligible_intervals": summary.eligible_intervals,
        "ineligible_intervals": summary.ineligible_intervals,
        "anomaly_intervals": summary.anomaly_intervals,
        "raw_grouped_candidates": summary.raw_grouped_candidates,
        "consolidated_candidates": summary.consolidated_candidates,
        "actionable_candidates": summary.actionable_candidates,
        "non_actionable_diagnostic_states": summary.non_actionable_diagnostic_states,
        "duplicate_overlaps_resolved": summary.duplicate_overlaps_resolved,
        "incident_candidates": summary.incident_candidates,
        "communication_incidents": summary.communication_incidents,
        "insufficient_evidence_candidates": summary.insufficient_evidence_candidates,
        "service_decisions": summary.service_decisions,
        "remote_actions": summary.remote_actions,
        "field_visits": summary.field_visits,
        "start_timestamp": summary.start_timestamp,
        "completion_timestamp": summary.completion_timestamp,
        "split_summary": summary.split_summary,
    }
