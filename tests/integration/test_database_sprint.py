from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from alembic.config import Config
from sqlalchemy import create_engine, text

from alembic import command
from app.core.config import get_settings, require_test_database_url
from app.database.session import _normalise_database_url
from app.repositories import AnalysisRepository, SitesRepository
from app.services.analysis_orchestration import AnalysisOrchestrationService
from app.services.data_loader import DemoDataLoader
from app.services.expected_generation import ExpectedGenerationService

EXPECTED_SOLARGUARD_TABLES = {
    "alembic_version",
    "sites",
    "technicians",
    "analysis_runs",
    "weather_history",
    "weather_forecast",
    "telemetry",
    "service_history",
    "site_diagnostics",
    "expected_generation_results",
    "expected_model_runs",
    "incident_candidates",
    "service_jobs",
    "route_plans",
    "route_stops",
}


def database_url_for_tests() -> str:
    try:
        return require_test_database_url(get_settings())
    except ValueError as exc:
        pytest.skip(str(exc))


def apply_migrations(database_url: str) -> None:
    config = Config("alembic.ini")
    config.cmd_opts = type("Options", (), {"x": [f"database_url={database_url}"]})()
    command.upgrade(config, "head")


def public_tables(connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
    }


def assert_development_database_is_safe(connection) -> None:
    tables = public_tables(connection)
    unexpected = tables - EXPECTED_SOLARGUARD_TABLES
    assert not unexpected, f"Unexpected non-SolarGuard tables present: {sorted(unexpected)}"


@pytest.fixture()
def migrated_engine():
    database_url = database_url_for_tests()
    engine = create_engine(_normalise_database_url(database_url), pool_pre_ping=True)
    with engine.connect() as connection:
        assert_development_database_is_safe(connection)
    apply_migrations(database_url)
    apply_migrations(database_url)
    with engine.begin() as connection:
        assert_development_database_is_safe(connection)
        AnalysisRepository(connection).clear_demo_data()
    yield engine
    engine.dispose()


def test_alembic_migration_application(migrated_engine) -> None:
    with migrated_engine.connect() as connection:
        tables = public_tables(connection)
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()

    assert "sites" in tables
    assert "expected_generation_results" in tables
    assert "incident_candidates" in tables
    assert revision == "20260704_0005"


def test_schema_constraints_indexes_and_foreign_keys(migrated_engine) -> None:
    with migrated_engine.connect() as connection:
        unique_constraints = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT conname
                    FROM pg_constraint
                    WHERE contype = 'u'
                    """
                )
            )
        }
        foreign_keys = int(
            connection.execute(
                text("SELECT count(*) FROM pg_constraint WHERE contype = 'f'")
            ).scalar_one()
        )
        indexes = {
            row[0]
            for row in connection.execute(
                text(
                    """
                    SELECT indexname
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    """
                )
            )
        }

    assert "uq_telemetry_site_time" in unique_constraints
    assert "uq_weather_zone_time" in unique_constraints
    assert "uq_weather_forecast_zone_time" in unique_constraints
    assert foreign_keys >= 10
    assert "ix_telemetry_site_id" in indexes
    assert "ix_expected_generation_results_analysis_run_id" in indexes
    assert "ix_expected_generation_results_anomaly_state" in indexes


def test_repository_read_write_and_transaction_rollback(migrated_engine) -> None:
    with pytest.raises(RuntimeError):
        with migrated_engine.begin() as connection:
            SitesRepository(connection).replace_sites(
                pd.DataFrame(
                    [
                        {
                            "site_id": "MH-999",
                            "site_name": "Rollback Site",
                            "capacity_kw": 5.0,
                            "latitude": 18.5,
                            "longitude": 73.8,
                            "weather_zone": "PUNE_TEST",
                            "commissioning_date": date(2025, 1, 1),
                            "inverter_vendor": "Vendor-A",
                            "inverter_model": "INV-5K",
                            "panel_capacity_w": 550,
                            "panel_count": 9,
                            "tilt_degree": 18,
                            "azimuth_degree": 180,
                            "site_efficiency_factor": 0.9,
                            "tariff_per_kwh": 8.0,
                            "service_region": "Pune Test",
                            "customer_type": "residential",
                            "warranty_end_date": date(2030, 1, 1),
                            "cleaning_cost_inr": 750,
                            "visit_cost_inr": 800,
                        }
                    ]
                )
            )
            raise RuntimeError("force rollback")

    with migrated_engine.connect() as connection:
        assert SitesRepository(connection).count_sites() == 0


def test_load_demo_idempotency_counts_and_ground_truth_isolation(migrated_engine) -> None:
    loader = DemoDataLoader(Path("data/raw"), migrated_engine)

    first = loader.load_demo(reset_existing=True)
    second = loader.load_demo(reset_existing=True)

    assert first["database_counts"] == second["database_counts"]
    assert second["database_counts"]["sites"] == 30
    assert second["database_counts"]["telemetry"] == 86400
    assert second["database_counts"]["weather_history"] == 8640
    assert second["database_counts"]["weather_forecast"] == 864
    assert second["database_counts"]["service_history"] == 48
    assert second["database_counts"]["technicians"] == 2
    assert second["database_counts"]["fault_ground_truth"] == 0
    assert second["database_counts"]["scenario_validation_expected"] == 0

    with migrated_engine.connect() as connection:
        duplicate_telemetry = connection.execute(
            text(
                """
                SELECT count(*)
                FROM (
                    SELECT site_id, timestamp
                    FROM telemetry
                    GROUP BY site_id, timestamp
                    HAVING count(*) > 1
                ) duplicates
                """
            )
        ).scalar_one()
        duplicate_weather = connection.execute(
            text(
                """
                SELECT count(*)
                FROM (
                    SELECT weather_zone, timestamp
                    FROM weather_history
                    GROUP BY weather_zone, timestamp
                    HAVING count(*) > 1
                ) duplicates
                """
            )
        ).scalar_one()
        missing_count = connection.execute(
            text(
                """
                SELECT count(*)
                FROM telemetry
                WHERE data_received = false AND generation_kwh IS NULL
                """
            )
        ).scalar_one()
        fabricated_missing = connection.execute(
            text(
                """
                SELECT count(*)
                FROM telemetry
                WHERE data_received = false
                  AND (
                    generation_kwh IS NOT NULL
                    OR ac_power_kw IS NOT NULL
                    OR dc_voltage IS NOT NULL
                    OR dc_current IS NOT NULL
                    OR ac_voltage IS NOT NULL
                    OR grid_frequency_hz IS NOT NULL
                    OR inverter_temperature_c IS NOT NULL
                  )
                """
            )
        ).scalar_one()
        assert missing_count > 0
        assert duplicate_telemetry == 0
        assert duplicate_weather == 0
        assert fabricated_missing == 0
        tables = public_tables(connection)
        assert "fault_ground_truth" not in tables
        assert "scenario_validation_expected" not in tables


def test_expected_generation_persists_valid_daytime_rows(migrated_engine) -> None:
    DemoDataLoader(Path("data/raw"), migrated_engine).load_demo(reset_existing=True)

    with migrated_engine.begin() as connection:
        service = ExpectedGenerationService(
            connection,
            config=get_settings().config,
            configuration_version=get_settings().configuration_version,
        )
        summary = service.run_baseline("RUN-INTEGRATION-EXPECTED")
        rows = AnalysisRepository(connection).read_expected_generation_frame(
            "RUN-INTEGRATION-EXPECTED"
        )

    assert summary.rows_persisted > 0
    assert summary.eligible_rows > 0
    assert (rows["expected_generation_kwh"] >= 0).all()
    assert rows["eligible"].any()
    assert rows["signed_residual_kwh"].notna().any()
    assert (rows["energy_loss_kwh"] >= 0).all()
    assert rows["model_version"].eq("expected-baseline-v1").all()


def test_full_analysis_run_persists_model_metadata_and_incident_candidates(migrated_engine) -> None:
    DemoDataLoader(Path("data/raw"), migrated_engine).load_demo(reset_existing=True)

    with migrated_engine.begin() as connection:
        service = AnalysisOrchestrationService(
            connection,
            config=get_settings().config,
            configuration_version=get_settings().configuration_version,
            raw_data_dir=Path("data/raw"),
        )
        summary = service.run("RUN-INTEGRATION-FULL")
        expected_rows = AnalysisRepository(connection).read_expected_generation_frame(
            "RUN-INTEGRATION-FULL"
        )
        incidents = AnalysisRepository(connection).read_incident_candidates_frame(
            "RUN-INTEGRATION-FULL"
        )

    assert summary.status == "completed"
    assert summary.total_intervals > 0
    assert summary.eligible_intervals > 0
    assert summary.incident_candidates > 0
    assert summary.raw_grouped_candidates > summary.consolidated_candidates
    assert summary.consolidated_candidates < 100
    assert summary.communication_incidents > 0
    assert expected_rows["signed_residual_kwh"].notna().any()
    assert (expected_rows["energy_loss_kwh"] >= 0).all()
    consolidated = incidents[incidents["candidate_stage"].eq("consolidated")]
    assert "communication failure" in set(consolidated["provisional_category"])
    scenario_categories = {
        site_id: set(group["provisional_category"])
        for site_id, group in consolidated.groupby("site_id")
    }
    assert "sudden severe underperformance" in scenario_categories["MH-107"]
    assert "sudden severe underperformance" in scenario_categories["MH-119"]
    assert "persistent underperformance" in scenario_categories["MH-105"]
    assert "morning time-window candidate" in scenario_categories["MH-109"]
    assert "afternoon time-window candidate" in scenario_categories["MH-124"]
    assert scenario_categories["MH-115"] == {"insufficient evidence"}
    assert scenario_categories["MH-130"] == {"insufficient evidence"}
    for communication_site in ["MH-103", "MH-112", "MH-126"]:
        assert scenario_categories[communication_site] == {"communication failure"}
    assert "fault_type" not in expected_rows.columns

    with migrated_engine.begin() as connection:
        repository = AnalysisRepository(connection)
        repository.replace_incident_candidates("RUN-INTEGRATION-FULL", incidents)
        repository.replace_incident_candidates("RUN-INTEGRATION-FULL", incidents)
        rerun_incidents = repository.read_incident_candidates_frame(
            "RUN-INTEGRATION-FULL"
        )
    assert len(rerun_incidents) == len(incidents)
    assert (
        len(rerun_incidents[rerun_incidents["candidate_stage"].eq("consolidated")])
        == summary.consolidated_candidates
    )
