from __future__ import annotations

from unittest.mock import MagicMock

from app.repositories.analysis import AnalysisRepository


def test_complete_analysis_run_persists_model_version() -> None:
    connection = MagicMock()
    repository = AnalysisRepository(connection)

    repository.complete_analysis_run(
        "RUN-TEST",
        {"status": "completed", "model_version": "expected-xgb-v1"},
    )

    parameters = connection.execute.call_args.args[1]
    assert parameters["model_version"] == "expected-xgb-v1"
