# 06 — Solution Architecture

## 1. Architecture objective

Create a simple, modular, reproducible POC that clearly separates data ingestion, analytics, decision logic, APIs, and presentation without introducing microservice overhead.

## 2. High-level architecture

```text
Canonical CSVs / Demo Generator
             │
             ▼
     Data Validation Layer
             │
             ▼
   Neon/PostgreSQL Storage
             │
             ▼
 ┌───────────────────────────────┐
 │ Analytics and Decision Core   │
 │ - Solar/time features         │
 │ - Expected generation         │
 │ - Anomaly detection           │
 │ - Probable-cause rules        │
 │ - Loss/value estimation       │
 │ - Priority scoring            │
 │ - Route optimisation          │
 └───────────────────────────────┘
             │
             ▼
         FastAPI Layer
             │ HTTP/JSON
             ▼
      Streamlit Dashboard
             │
             ▼
   Daily O&M Plan CSV Export
```

## 3. Technology decisions

| Layer | Technology | Reason |
|---|---|---|
| Runtime | Python 3.11 | Stable compatibility |
| Package management | uv | Fast environment setup |
| Data | Pandas, NumPy | Appropriate for ~100k rows |
| Domain features | pvlib | Solar position and clear-sky context |
| ML | XGBoost + scikit-learn | Strong tabular baseline and utilities |
| API | FastAPI | Typed APIs and Swagger |
| Validation | Pydantic | Schema enforcement |
| Persistence | Neon/PostgreSQL + SQLAlchemy | Hosted PostgreSQL persistence for the POC demo |
| UI | Streamlit | Fast multipage POC |
| Charts | Plotly | Interactive time-series visuals |
| Map | Folium/OpenStreetMap tiles | No paid API |
| Routing | OR-Tools | Constraint-aware optimisation |
| Tests | Pytest | Unit/integration/scenario testing |
| Quality | Ruff | Fast formatting and linting |
| Packaging | Docker Compose | Reproducible demo |

## 4. Component responsibilities

### 4.1 Data Generator

- Produces deterministic synthetic files.
- Injects documented incidents.
- Creates hidden ground truth.
- Does not perform operational diagnosis.

### 4.2 Data Ingestion Service

- Reads CSVs.
- Applies canonical types.
- Validates schema and keys.
- Loads data into Neon/PostgreSQL.
- Produces row-count and quality summary.

### 4.3 Data Quality Service

- Completeness and freshness checks.
- Duplicate and range validation.
- Distinguishes missing telemetry from zero output.
- Produces quality flags used by diagnosis.

### 4.4 Expected Generation Service

- Builds solar/time/weather features.
- Loads pre-trained model or deterministic baseline.
- Returns interval and daily expected generation.
- Records model version.

### 4.5 Anomaly Detection Service

- Calculates residual and performance ratio.
- Applies daylight and persistence gates.
- Groups abnormal intervals into incidents.

### 4.6 Probable Cause Service

- Applies explainable rules.
- Generates evidence list.
- Computes confidence score.
- Supports unknown/insufficient evidence.

### 4.7 Loss and Priority Services

- Calculate energy loss and value.
- Evaluate cleaning economics.
- Distinguish remote action and visit.
- Produce score and component breakdown.

### 4.8 Route Optimisation Service

- Filters route-eligible jobs.
- Builds local Haversine distance matrix.
- Applies skills, shift, and visit limits.
- Returns assignments and route metrics.

### 4.9 Report Service

- Produces daily O&M CSV.
- Uses stored backend results; no separate recalculation.

### 4.10 FastAPI

- Single API process.
- Orchestrates services.
- Returns typed JSON and controlled errors.

### 4.11 Streamlit

- Four operational pages.
- Calls FastAPI only.
- Does not calculate priority, diagnosis, or route logic.

## 5. Repository structure

```text
solarguard/
├── app/
│   ├── api/
│   │   ├── data.py
│   │   ├── fleet.py
│   │   ├── sites.py
│   │   ├── analysis.py
│   │   ├── service_queue.py
│   │   ├── routes.py
│   │   └── reports.py
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   └── logging.py
│   ├── schemas/
│   ├── database/
│   ├── services/
│   └── main.py
├── dashboard/
│   ├── Home.py
│   ├── api_client.py
│   └── pages/
├── data/
│   ├── raw/
│   ├── generated/
│   └── processed/
├── models/
├── config/
│   └── poc_config.yaml
├── scripts/
│   ├── generate_demo_data.py
│   ├── train_expected_model.py
│   ├── load_demo.py
│   └── start_demo.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── scenarios/
├── docs/
├── pyproject.toml
├── Dockerfile.api
├── Dockerfile.dashboard
├── docker-compose.yml
└── README.md
```

## 6. Persistence model

The POC uses Neon/PostgreSQL as the authoritative application database. SQLAlchemy should keep database access isolated behind repository/session boundaries so analytics, API, and reporting code do not depend on provider-specific Neon behavior.

Database connection settings must be supplied through environment variables, such as `DATABASE_URL`, and must not be committed to the repository. The approved test database strategy is a separate `TEST_DATABASE_URL` pointing to a Neon test branch or test database, not the presentation database. Local development and CI may use that disposable Neon test branch/database, and demo acceptance must verify the configured presentation Neon connection.

Suggested tables:

- sites
- telemetry
- weather_history
- weather_forecast
- service_history
- technicians
- analysis_runs
- site_diagnostics
- service_jobs
- route_plans
- route_stops

Ground truth may remain as a test fixture or isolated evaluation table not exposed by production routes.

CSV upload is deferred for the first POC sprint. The first demo path uses the bundled dataset through `/api/data/load-demo`.

## 7. Analysis run lifecycle

1. Create `analysis_run` with status `RUNNING`.
2. Validate source data.
3. Generate expected output.
4. Detect and group anomalies.
5. Produce site diagnostics.
6. Calculate action and priority.
7. Store results.
8. Mark run `COMPLETED` with summary.
9. On controlled failure, mark `FAILED` and store safe error details.

The POC may execute synchronously because of small volume.

## 8. Configuration management

- YAML for thresholds and business costs.
- `.env` for runtime URLs and secrets, including `DATABASE_URL`.
- Separate environment configuration must identify the Neon test branch/database used for integration tests; tests must not mutate the presentation Neon database.
- No API keys are required for core POC services other than database credentials for Neon/PostgreSQL.
- Include configuration version in analysis output.

## 9. Failure and fallback behavior

| Failure | Behavior |
|---|---|
| Model file missing | Use deterministic physics/rule baseline and show warning |
| Invalid CSV | Reject with file/column-level errors |
| No eligible daylight data | Return insufficient-data diagnosis |
| No route-worthy jobs | Show empty route state, not error |
| Map tiles unavailable | Show textual route and coordinates |
| FastAPI unavailable | Streamlit shows connection guidance, not traceback |
| Database unavailable or misconfigured | API health check fails with safe database-configuration guidance; demo should use a previously exported O&M plan only as a presentation fallback |
| Analysis fails | Retain previous completed run for demo fallback |

## 10. Security and privacy

POC controls:

- synthetic anonymous data only;
- file type and size validation;
- no code execution from uploads;
- database credentials and other secrets outside repository;
- no unrestricted filesystem paths;
- safe error messages.

## 11. Observability

Minimum logs:

- request ID;
- analysis run ID;
- dataset row counts;
- validation summary;
- model/config version;
- service execution duration;
- route result summary;
- controlled failure reason.

## 12. Deployment

Preferred demo startup:

```bash
docker compose up --build
```

The preferred startup requires `DATABASE_URL` to point at the approved Neon/PostgreSQL database. Docker Compose should run the API and dashboard; it should not start an unrelated database unless explicitly configured for local development.

Fallback local startup:

```bash
uv run uvicorn app.main:app --reload --port 8000
uv run streamlit run dashboard/Home.py --server.port 8501
```

The local fallback also requires `DATABASE_URL`. The demo is not required to work fully offline because Neon/PostgreSQL is the approved persistence layer. After dependencies and map assets are available, analytics and routing must not call live weather, traffic, inverter, or mapping APIs.

## 13. Architectural quality gates

- No business calculation in Streamlit.
- No UI access to ground truth.
- No external API required for core route calculation beyond the approved database connection.
- One canonical implementation of every calculation.
- Model has deterministic fallback.
- Every incident is traceable to evidence and configuration.
