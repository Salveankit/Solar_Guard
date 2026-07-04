from __future__ import annotations

from unittest.mock import MagicMock

from app.services.operations_query import OperationsQueryService


def test_diagnostics_and_queue_share_persisted_decision_values() -> None:
    service = OperationsQueryService(MagicMock())
    service.repository = MagicMock()
    decision = {
        "analysis_run_id": "RUN-TEST",
        "incident_candidate_id": "IC-124",
        "site_id": "MH-124",
        "probable_issue": "probable recurring shade or obstruction",
        "priority_score": 21.39,
        "priority_label": "Low",
        "remote_action_available": True,
        "visit_required": False,
        "actionable": True,
        "cleaning_decision": "defer_rain",
    }
    monitoring = {
        **decision,
        "incident_candidate_id": "IC-110",
        "site_id": "MH-110",
        "actionable": False,
        "queue_rank": None,
    }
    service.repository.latest_decision_run_id.return_value = "RUN-TEST"
    service.repository.read_decisions.return_value = [decision, monitoring]
    service.repository.read_site.return_value = {"site_id": "MH-124"}
    service.repository.read_site_candidate.return_value = {"incident_candidate_id": "IC-124"}
    service.repository.read_site_performance.return_value = []

    diagnostic = service.diagnostics("MH-124")
    queue = service.service_queue(actionable_only=True)

    assert diagnostic is not None
    assert queue["count"] == 1
    assert diagnostic["diagnostics"][0]["decision"] == queue["items"][0]
    assert queue["items"][0]["visit_required"] is False
