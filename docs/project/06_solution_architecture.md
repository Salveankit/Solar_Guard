# 06 - Solution Architecture

## 1. Architecture objective

Create a simple, modular, reproducible POC that clearly separates data ingestion, analytics, decision logic, APIs, and presentation without introducing microservice overhead.

The backend remains the source of truth for diagnosis, priority, energy value, and route optimisation. The active frontend presents those backend outputs; it must not independently recalculate business logic.

## 2. Current implementation shape

```text
Canonical CSVs / Demo Generator
             |
             v
     Data Validation Layer
             |
             v
   Neon/PostgreSQL Storage
             |
             v
 +-------------------------------+
 | Analytics and Decision Core   |
 | - Solar/time features         |
 | - Expected generation         |
 | - Anomaly detection           |
 | - Probable-cause rules        |
 | - Loss/value estimation       |
 | - Priority scoring            |
 | - Route optimisation          |
 +-------------------------------+
             |
             v
         FastAPI Layer
             |
             +--> React/Vite operational dashboard in frontend/
             |
             +--> Streamlit dashboard retained in dashboard/
             |
             +--> Daily O&M Plan CSV Export
```

## 3. Technology decisions

| Layer | Technology | Current role |
|---|---|---|
| Runtime | Python 3.11 | Backend application language |
| Package management | uv | Python environment and command runner |
| Data | Pandas, NumPy | Demo-scale tabular processing |
| Domain features | pvlib | Solar/time feature context |
| ML | XGBoost + scikit-learn | Expected-generation model and fallback comparison |
| API | FastAPI | Typed backend API layer |
| Validation | Pydantic | Request/response and data validation |
| Persistence | Neon/PostgreSQL + SQLAlchemy | Authoritative POC database |
| Active UI | React, TypeScript, Vite | Primary polished operational dashboard |
| UI data fetching | TanStack React Query, Axios, Zod | API calls, caching, schema validation |
| UI components | Ant Design plus local CSS | Dashboard components and interaction shell |
| Charts | ECharts in React; Plotly in retained Streamlit | Time-series and distribution visuals |
| Maps | Leaflet/OpenStreetMap tiles in React; Folium available in Streamlit | No paid map API |
| Routing | OR-Tools with local distance matrix | Technician route optimisation |
| Tests | Pytest, Vitest, Testing Library | Backend and frontend verification |
| Quality | Ruff, ESLint, TypeScript | Static quality checks |

## 4. Component responsibilities

### 4.1 Data generator

- Produces deterministic synthetic files.
- Injects documented incidents.
- Creates hidden ground truth.
- Does not perform operational diagnosis.

### 4.2 Data ingestion service

- Reads canonical CSVs from `data/raw/`.
- Applies canonical types.
- Validates schema and keys.
- Loads data into Neon/PostgreSQL.
- Produces row-count and quality summaries.

### 4.3 Data quality service

- Completeness and freshness checks.
- Duplicate and range validation.
- Distinguishes missing telemetry from zero output.
- Produces quality flags used by diagnosis.

### 4.4 Expected generation service

- Builds solar/time/weather features from stored synthetic data.
- Loads the trained model artifact when available.
- Uses deterministic fallback behavior when needed.
- Returns interval and daily expected generation.
- Records model/configuration version.

### 4.5 Anomaly and probable-cause services

- Calculate residuals and performance ratio.
- Apply daylight, magnitude, and persistence gates.
- Group abnormal intervals into incidents.
- Apply explainable probable-cause rules.
- Support unknown/insufficient-evidence outcomes.

### 4.6 Loss, priority, and decision services

- Calculate energy loss and value.
- Evaluate cleaning economics where applicable.
- Distinguish monitor, remote action, field visit, cleaning, and collect-more-data decisions.
- Produce priority score and component breakdown.

### 4.7 Route optimisation service

- Filters route-eligible jobs.
- Builds a local Haversine distance matrix.
- Applies technician skill, shift, and visit limits.
- Returns assignments, route order, and route metrics.
- Does not call live traffic or paid routing APIs.

### 4.8 Report service

- Produces the daily O&M CSV.
- Uses stored backend results; no separate recalculation.

### 4.9 FastAPI

- Single backend API process.
- Orchestrates services.
- Returns JSON/CSV and controlled errors.
- Uses SQLAlchemy engine/session boundaries for persistence.

### 4.10 React/Vite frontend

- Primary user-facing interface.
- Uses route-level lazy imports.
- Uses page-aware data fetching and refresh behavior.
- Displays backend outputs from FastAPI.
- Uses ECharts for charts and Leaflet/OpenStreetMap for route maps.
- Must not show backend-engineering copy such as raw implementation notes, raw JSON, or stack traces.

### 4.11 Streamlit dashboard

- Retained POC/fallback implementation under `dashboard/`.
- Calls FastAPI only.
- Must not calculate priority, diagnosis, energy loss, or route logic.

## 5. Repository structure

```text
solar guard/
|-- app/
|   |-- api/
|   |   |-- analysis.py
|   |   |-- data.py
|   |   |-- health.py
|   |   |-- operations.py
|   |   |-- reports.py
|   |   `-- routes.py
|   |-- core/
|   |-- database/
|   |-- models/
|   |-- repositories/
|   |-- schemas/
|   |-- services/
|   `-- main.py
|-- frontend/
|   |-- src/app/
|   |-- src/components/
|   |-- src/features/
|   |-- src/services/
|   |-- package.json
|   `-- vite.config.ts
|-- dashboard/
|   |-- Home.py
|   |-- api_client.py
|   `-- pages/
|-- data/
|   |-- raw/
|   |-- generated/
|   `-- processed/
|-- models/
|   |-- expected_generation_model.joblib
|   |-- feature_schema.json
|   `-- model_metrics.json
|-- config/
|   `-- poc_config.yaml
|-- scripts/
|-- tests/
|-- docs/project/
|-- pyproject.toml
`-- PROJECT_CONTEXT.md
```

## 6. Persistence model

The POC uses Neon/PostgreSQL as the authoritative application database. SQLAlchemy keeps database access isolated behind repository/session boundaries so analytics, API, and reporting code do not depend on provider-specific Neon behavior.

Database connection settings must be supplied through environment variables, such as `DATABASE_URL`, and must not be committed to the repository. The approved test database strategy is a separate `TEST_DATABASE_URL` pointing to a Neon test branch or test database, not the presentation database.

Core logical tables include:

- sites
- telemetry
- weather_history
- weather_forecast
- service_history
- technicians
- analysis_runs
- expected_generation
- site_diagnostics
- service_decisions/jobs
- route_plans
- route_stops

Ground truth may remain as a test fixture or isolated evaluation table and must not be exposed by production routes.

## 7. Analysis run lifecycle

1. Create an analysis run with running status.
2. Validate source data.
3. Generate expected output.
4. Detect and group anomalies.
5. Produce site diagnostics.
6. Calculate action and priority.
7. Store results.
8. Mark run completed with summary.
9. On controlled failure, store safe error details.

The POC may execute synchronously because of the small synthetic dataset.

## 8. Configuration management

- YAML stores thresholds and business-cost assumptions.
- `.env` stores runtime URLs and secrets, including `DATABASE_URL`.
- Integration tests use `TEST_DATABASE_URL`, not the presentation database.
- No live inverter, weather, traffic, map, or LLM API key is required for core POC services.
- Include configuration version in analysis output.

## 9. Failure and fallback behavior

| Failure | Behavior |
|---|---|
| Model file missing | Use deterministic fallback and show controlled warning |
| Invalid CSV | Reject with file/column-level errors |
| No eligible daylight data | Return insufficient-data diagnosis |
| No route-worthy jobs | Show empty route state, not an error |
| Map tiles unavailable | Show textual route and coordinates |
| FastAPI unavailable | UI shows connection guidance, not traceback |
| Database unavailable or misconfigured | Health check fails with safe database-configuration guidance |
| Analysis fails | Retain previous completed run for demo fallback where available |

## 10. Observability

Minimum logs:

- request ID where available;
- analysis run ID;
- dataset row counts;
- validation summary;
- model/config version;
- service execution duration;
- route result summary;
- controlled failure reason.

## 11. Local startup

Backend:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Active React frontend:

```bash
cd frontend
npm install
npm run dev
```

Retained Streamlit fallback:

```bash
uv run streamlit run dashboard/Home.py --server.port 8501
```

All startup paths require a valid `DATABASE_URL` for the primary demo path. The demo is not required to work fully offline because Neon/PostgreSQL is the approved persistence layer.

## 12. Architectural quality gates

- No business calculation in the React frontend or Streamlit dashboard.
- No UI access to ground truth.
- No external API required for core route calculation beyond the configured database connection.
- No live weather or inverter data should be claimed unless a real integration exists.
- One canonical implementation of every calculation.
- Model has deterministic fallback behavior.
- Every incident is traceable to evidence and configuration.
- Refresh and cache invalidation should be page-aware to avoid unnecessary reload latency.
