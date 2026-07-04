# SolarGuard Implementation Status

## Current Phase

Expected-generation v2 and calibrated candidate-quality correction sprint implemented.
The current development database is the approved disposable Neon/PostgreSQL database for
this phase when `ALLOW_DEVELOPMENT_DB_TESTS=true` is explicitly configured.

## Completed

- Repository/specification audit completed.
- Neon/PostgreSQL confirmed as the only approved persistence architecture.
- `docs/project/` confirmed as the authoritative detailed specification path.
- Neon test branch/database confirmed as the database integration-test strategy.
- CSV upload deferred for the first POC; `/api/data/load-demo` is the required initial demo path.
- Expected-generation implementation may proceed baseline-first, but XGBoost remains mandatory for the first demo workstream unless explicitly de-scoped by project leadership.
- Approved repository structure created for backend, schemas, services, database, tests, config, scripts, and data docs.
- Python project configuration added with Python 3.11 requirement.
- Environment example added with Neon/PostgreSQL `DATABASE_URL`.
- `TEST_DATABASE_URL` added for Neon test branch/database integration tests.
- YAML POC configuration added for thresholds, costs, routing defaults, and fixed seed.
- Pydantic canonical data schemas added.
- CSV validation layer added for required files, columns, all-row schema checks, critical value checks, uniqueness, foreign keys, and missing-vs-zero handling.
- Alembic added with one initial PostgreSQL migration.
- Minimal repositories added for sites, telemetry, weather, analysis runs, and expected-generation results.
- Demo dataset loader hardened for controlled-replace ingestion, operational CSV isolation, transaction scope, and post-load database count reporting.
- SQLAlchemy table definitions added for source datasets, future analysis outputs, and expected-generation results.
- Deterministic domain-aware expected-generation baseline added using site capacity, irradiance, temperature, orientation, site efficiency, and pvlib solar-position features.
- XGBoost feature/model interface implemented with deterministic feature schema, Joblib
  model artifact, metrics artifact, chronological split, and explicit promotion rule.
- Signed residual semantics corrected: `signed_residual_kwh = actual - expected`.
- Non-negative interval energy loss added separately as
  `energy_loss_kwh = max(expected - actual, 0)`.
- Alembic migration `20260704_0002_model_anomaly_foundation.py` added result metrics,
  model-run metadata, and incident-candidate persistence.
- Backend analysis orchestration added for model training/evaluation, active predictor
  selection, expected-result persistence, interval anomaly states, persistent incident
  candidates, communication incidents, and time-window candidates.
- FastAPI health, demo-load, baseline expected-generation, and full analysis-run
  endpoints added.
- Unit tests added for configuration safety, data validation, and expected-generation baseline behavior.
- Integration tests added for Alembic migration application, repository behavior, transaction rollback, ingestion idempotency, database counts, ground-truth isolation, and expected-generation persistence. These tests require `TEST_DATABASE_URL` and skip when it is absent.
- Alembic URL handling hardened so migration commands require an explicit `-x database_url=...` value and refuse placeholder URLs.
- Expected-generation time features now explicitly convert aware timestamps to
  `Asia/Kolkata`; naive timestamps are rejected.
- XGBoost `expected-xgb-v2` was trained once with feature schema
  `expected-generation-features-v3` and promoted after deterministic baseline and
  chronological leakage checks.
- Candidate contract migration `20260704_0004_candidate_quality_contract.py` adds
  secondary evidence, operational qualification, and actionable status.
- Insufficient-evidence durations use supporting evidence intervals rather than the full
  analysis span.
- Materially overlapping categories resolve to one precedence-selected primary candidate
  while retaining secondary evidence and non-duplicated energy loss.
- Low-impact and insufficient-evidence diagnostics remain visible but are excluded from
  actionable incident counts.

## Verification

- `uv run pytest tests/unit -q`: 31 passed in 3.03s.
- `uv run ruff check .`: all checks passed.
- Alembic explicit settings-driven verification: current revision `20260704_0004 (head)`.
- Final analysis `RUN-CANDIDATE-QUALITY-FINAL`: 563 raw candidates, 13 consolidated
  outputs, 8 actionable incidents, 5 non-actionable diagnostics, and one duplicate
  overlap resolved.
- Healthy-site actionable candidate count: zero.
- Scenario assertions pass for:
  - `MH-107`: sudden severe underperformance candidate;
  - `MH-119`: sudden severe underperformance candidate;
  - `MH-105`: persistent underperformance candidate;
  - `MH-109`: morning time-window candidate;
  - `MH-124`: afternoon time-window candidate;
  - `MH-115`: insufficient evidence;
  - `MH-130`: insufficient evidence;
  - communication sites `MH-103`, `MH-112`, and `MH-126`: communication failure.

## Not Yet Implemented

- Probable-cause engine.
- Cleaning economics.
- Service priority scoring.
- Ranked service queue.
- Route optimisation.
- Streamlit dashboard.
- Report generation.

## Known Gaps

- The current XGBoost configuration is intentionally small for the POC and avoids tuning.
- Model promotion is based on synthetic-data metrics and is not a production accuracy claim.
- Incident categories from this sprint remain provisional; final probable-cause reasoning,
  recommendations, confidence scoring, priority, routing, Streamlit, and reports belong
  to later approved sprints.
- Full database integration tests are intentionally slower because they train XGBoost and
  run the scenario pipeline against Neon/PostgreSQL.
- MH-111 retains a low-impact, monitor-only morning pattern. Its broad residual pattern
  and peer comparison indicate model/weather bias rather than an actionable site event.
