# SolarGuard Project Context

## 1. Project Identity

SolarGuard is a rooftop-solar performance and field-service decision intelligence POC.

It converts standardized, synthetic rooftop-solar telemetry into an explainable daily operations and maintenance plan for a Pune-region rooftop fleet.

The project demonstrates the team's ability to combine:

* deterministic demo-data generation;
* canonical data validation;
* solar-domain feature engineering;
* expected-generation modelling;
* persistent anomaly detection;
* explainable probable-cause reasoning;
* energy-loss and service-priority calculation;
* FastAPI backend services;
* Neon/PostgreSQL persistence through SQLAlchemy;
* operational dashboard presentation;
* OR-Tools technician route optimisation;
* daily O&M plan export.

SolarGuard is not a production fault-diagnosis platform and must not be presented as one.

---

## 2. Current Implementation Shape

The implemented repository currently contains both the originally specified Streamlit dashboard and a richer React/Vite frontend.

Authoritative project documents still specify **FastAPI + Streamlit** as the approved POC architecture. The current active user-facing interface in this workspace is the **React/Vite frontend** under `frontend/`.

Current major components:

```text
data/raw CSV demo dataset
        |
        v
validation and load-demo service
        |
        v
Neon/PostgreSQL tables
        |
        v
FastAPI backend and service layer
        |
        +--> React/Vite operational dashboard in frontend/
        |
        +--> Streamlit dashboard code retained in dashboard/
```

The backend remains the source of truth. The React frontend displays API results and should not recalculate diagnosis, priority, energy loss, or route optimisation.

---

## 3. Business Problem

A rooftop-solar EPC or service operator cannot manually inspect every inverter dashboard each day.

The operations manager needs to know:

1. Which sites genuinely require attention?
2. Is low generation likely weather-related, data-related, or operational?
3. Which cases should be checked remotely?
4. Which cases justify a technician visit?
5. Which cases carry the highest recoverable energy impact?
6. How should tomorrow's technician visits be assigned and ordered?

SolarGuard converts raw telemetry and weather-context data into these decisions.

---

## 4. Primary Users

### EPC Operations Manager

The operations manager uses SolarGuard to:

* review fleet health;
* identify sites requiring attention;
* inspect probable issue categories;
* review evidence and confidence;
* estimate energy value at risk;
* prioritize service actions;
* approve the technician plan;
* export the daily O&M plan.

### Service Technician

The technician needs:

* assigned site list;
* visit sequence;
* probable issue;
* reason for the visit;
* recommended diagnostic action;
* required skill or equipment;
* estimated job duration;
* route distance and ETA context.

The POC does not include a separate technician mobile app.

---

## 5. Core Product Question

Every major feature must help answer:

> Which solar sites need attention, why do they need attention, and what is the most efficient next action?

Features that do not materially support this question are outside the POC scope.

---

## 6. Demo Data and Truth Boundary

The default POC represents:

* 30 rooftop-solar installations;
* Pune and nearby regions;
* 30 days of historical telemetry;
* 15-minute telemetry readings;
* two technicians;
* one service hub;
* injected operational incidents;
* communication, sudden outage, gradual underperformance, time-specific underperformance, and unknown/insufficient-evidence states.

The dataset is synthetic but operationally realistic and internally linked.

Important truth boundaries:

* There is no live inverter API integration.
* There is no live weather API integration.
* Weather values shown in the UI come from stored demo weather data and current analysis outputs.
* OpenStreetMap tiles are used only for map rendering; route optimisation does not depend on map APIs.
* `fault_ground_truth.csv` is evaluation-only and must not drive user-facing diagnosis.

---

## 7. End-to-End Product Flow

```text
Site metadata
      +
15-minute inverter telemetry
      +
Historical weather data
      +
Weather forecast data
      +
Service history
      +
Technician information
            |
            v
Data ingestion and validation
            |
            v
Data quality assessment
            |
            v
Expected-generation estimation
            |
            v
Actual-versus-expected comparison
            |
            v
Persistent anomaly detection
            |
            v
Explainable probable-cause reasoning
            |
            v
Energy-loss and recoverable-value estimation
            |
            v
Service-priority queue
            |
            v
Remote-check versus field-visit decision
            |
            v
Technician assignment and route optimisation
            |
            v
Daily O&M plan CSV
```

---

## 8. Backend Architecture

Backend language and runtime:

* Python 3.11
* FastAPI
* SQLAlchemy
* Pydantic
* Pandas and NumPy
* pvlib
* XGBoost and scikit-learn
* OR-Tools
* PyYAML configuration

Important backend folders:

* `app/api/` - FastAPI routes
* `app/services/` - application and domain services
* `app/repositories/` - database access
* `app/database/` - SQLAlchemy models and engine/session setup
* `app/schemas/` - canonical Pydantic schemas
* `config/poc_config.yaml` - thresholds and business assumptions
* `scripts/load_demo.py` - demo-data loading entry point

Implemented API areas:

* `GET /health`
* `POST /api/data/load-demo`
* `POST /api/analysis/run`
* `POST /api/analysis/run-expected-generation`
* `GET /api/fleet/summary`
* `GET /api/fleet/timeseries`
* `GET /api/sites`
* `GET /api/sites/{site_id}`
* `GET /api/sites/{site_id}/diagnostics`
* `GET /api/service-queue`
* `POST /api/routes/optimize`
* `GET /api/routes/latest`
* `GET /api/reports/daily-plan`

The SQLAlchemy engine is cached/reused globally through `app/database/session.py` to avoid repeated connection setup latency.

---

## 9. Frontend Architecture

The active frontend is a React/Vite application in `frontend/`.

Current frontend stack:

* React 19
* Vite
* TypeScript
* Ant Design
* TanStack React Query
* Axios
* Zod response validation
* ECharts
* Leaflet and React Leaflet
* Papa Parse
* Vitest and Testing Library

The frontend uses route-level lazy imports to reduce initial load cost.

Implemented React routes:

* `/` - Command Centre
* `/fleet` - Fleet Sites
* `/diagnostics` - Diagnostics default view
* `/sites/:siteId` - Site Diagnostics
* `/incidents` - Incidents
* `/service-queue` - Service Queue
* `/technician-plan` - Technician Plan
* `/reports` - Reports

Refresh behavior is page-aware. The shell no longer invalidates all heavy operational data on every refresh.

---

## 10. UI Screen Model

### Command Centre

Answers:

> What is the current fleet situation and what needs attention first?

Current UI includes:

* hero summary;
* site/weather overview from stored analysis data;
* KPI strip;
* expected versus actual fleet generation chart;
* incident distribution donut;
* today's operations summary;
* service priority queue preview;
* top priority evidence;
* technician route preview with real OpenStreetMap tiles and backend route stop order.

### Fleet Sites

Answers:

> Which sites are healthy, degraded, unknown, or need operational attention?

Current UI includes:

* fleet overview;
* site inventory;
* site filters;
* site cards/table views;
* map-style cluster interaction;
* navigation into diagnostics.

### Site Diagnostics

Answers:

> Why was this site flagged, and what evidence supports the recommendation?

Current UI includes:

* site issue header;
* expected versus actual generation chart;
* diagnostic summary;
* evidence strip;
* site and analysis context;
* event and diagnostic history;
* recommended next actions.

### Incidents

Answers:

> Which incidents need triage, and what action should be taken next?

Current UI includes:

* incident overview;
* incident KPIs;
* incident queue;
* incident distribution;
* selected incident panel;
* recommended next actions;
* service-queue routing confirmation.

Frontend copy should avoid backend-engineering language such as "backend recommendation" or "API-supplied" for non-technical users.

### Service Queue

Answers:

> Which service decisions should be reviewed first?

Current UI includes:

* queue summary;
* ranked service decision queue;
* filters;
* selected decision details;
* priority breakdown;
* action buttons to diagnostics and technician planning.

### Technician Plan

Answers:

> Who should visit which sites, and in what order?

Current UI includes:

* technician plan summary;
* assignment table;
* real Leaflet/OpenStreetMap route map;
* service hub and numbered stops;
* technician-specific route colours;
* selected technician detail;
* plan impact;
* daily O&M plan download.

### Reports

Answers:

> What operational output can be exported from the current plan?

Current UI includes:

* report library;
* selected report detail;
* CSV preview;
* daily O&M plan download.

Only CSV export is currently implemented. PDF, XLSX, scheduling, and email delivery are outside the current POC capability.

---

## 11. Graph and Data Reality

The main charts are backend-driven, not static presentation images.

Examples:

* Command Centre generation chart reads `/api/fleet/timeseries`.
* Diagnostics generation chart reads `/api/sites/{site_id}/diagnostics`.
* Incident and queue distributions read `/api/service-queue`.
* Technician route maps read `/api/routes/latest`.
* Report preview reads `/api/reports/daily-plan`.

These graphs are real for the current synthetic demo dataset. They are not live production telemetry.

The UI must not imply:

* live weather API data;
* live inverter API data;
* confirmed hardware faults;
* guaranteed savings;
* road-following traffic-aware routing.

---

## 12. Intelligence Model

SolarGuard does not use one model for everything.

### Expected Generation

Expected generation estimates how much energy a healthy site should have produced under observed conditions.

Inputs include:

* site capacity;
* panel orientation;
* site efficiency factor;
* irradiance and weather context;
* solar position features;
* historical telemetry.

The project includes:

* deterministic baseline expected-generation logic;
* XGBoost model artifacts in `models/`;
* model metrics in `models/model_metrics.json`.

### Anomaly Detection

Anomaly detection compares actual output with expected output.

Core measures:

```text
Residual = Actual generation - Expected generation
Performance ratio = Actual generation / Expected generation
```

An incident requires sufficient daylight, meaningful expected output, material underperformance, and persistence.

### Probable-Cause Reasoning

Probable-cause classification uses explainable rules and evidence, not an LLM and not hidden synthetic ground truth.

Supported categories:

* communication or data failure;
* sudden production outage;
* gradual persistent underperformance;
* time-specific underperformance;
* unknown or insufficient evidence.

### Priority and Service Decision

Priority combines:

* energy impact;
* recoverable value;
* persistence;
* confidence;
* customer complaint or SLA context;
* route benefit.

The service decision separates:

* remote check;
* monitor;
* collect more data;
* schedule cleaning;
* technician visit.

### Route Optimisation

Only physical-visit jobs enter OR-Tools optimisation.

The route optimiser considers:

* technician skills;
* visit limits;
* shift duration;
* job duration;
* job priority;
* site coordinates;
* service hub location.

Leaflet maps display route order and approximate lines. They do not calculate route order.

---

## 13. Data Truth Rules

### Missing Is Not Zero

Missing telemetry means no reading was received.

Zero generation means a reading was received and measured generation was zero.

These states must remain separate in backend logic and UI copy.

### Weather-Driven Loss Is Not Automatically a Fault

Low output during low irradiance, heavy cloud, or rain should not automatically create an underperformance incident.

### Underperformance Is Not a Confirmed Failure

The system reports probable issue categories. It must not claim confirmed component failure.

### Synthetic Ground Truth Is Evaluation-Only

`fault_ground_truth.csv` validates injected POC scenarios. It must not drive operational diagnosis.

---

## 14. Business Terminology

Use:

* probable issue;
* supporting evidence;
* confidence;
* recommended action;
* energy loss;
* energy value at risk;
* recoverable energy;
* service priority;
* field visit candidate;
* remote-check candidate;
* unknown or insufficient evidence.

Avoid:

* confirmed fault;
* exact component failure;
* guaranteed savings;
* autonomous repair;
* live weather unless a live integration exists;
* AI proved;
* revenue loss as a blanket phrase for all sites.

---

## 15. Persistence and Data Assets

The POC uses Neon/PostgreSQL as the primary persistence layer.

Important database-backed datasets include:

* sites;
* telemetry;
* weather history;
* weather forecast;
* service history;
* technicians;
* analysis runs;
* expected generation results;
* incident candidates;
* service decisions;
* route plans and route stops.

Important local assets include:

* `data/raw/*.csv` - canonical demo inputs;
* `models/expected_generation_model.joblib` - expected-generation model artifact;
* `models/feature_schema.json` - model feature schema;
* `models/model_metrics.json` - model evaluation metrics;
* `config/poc_config.yaml` - thresholds, costs, and business assumptions.

Secrets such as `DATABASE_URL` belong in `.env` and must not be committed.

---

## 16. Testing and Quality

Current test coverage includes:

* backend unit tests with Pytest;
* database/integration sprint tests;
* frontend unit/integration tests with Vitest and Testing Library;
* frontend linting through ESLint;
* frontend production build through TypeScript and Vite.

Common verification commands:

```bash
uv run pytest
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npm test
```

Performance-sensitive frontend behavior already implemented:

* SQLAlchemy engine reuse on the backend;
* route-level lazy imports in the React app;
* page-aware refresh invalidation;
* shell status limited to lightweight global queries.

---

## 17. Non-Goals

The POC does not include:

* authentication;
* role-based access;
* customer mobile application;
* live inverter APIs;
* live weather APIs;
* real-time traffic;
* WhatsApp, SMS, or email delivery;
* payment or billing;
* chatbot;
* Kafka;
* Airflow;
* Redis;
* Celery;
* Kubernetes;
* production monitoring;
* automated model retraining;
* guaranteed diagnosis.

These may be future roadmap items, not current implementation scope.

---

## 18. Engineering Invariants

The following must remain true:

1. FastAPI/backend services remain the source of truth.
2. The frontend does not recalculate diagnosis, priority, energy loss, or routes.
3. Missing telemetry is never silently converted to zero generation.
4. Fault outputs are probable, not confirmed.
5. Unknown or insufficient evidence is a valid output state.
6. Synthetic ground truth is not used as a diagnostic shortcut.
7. Thresholds and business assumptions come from configuration.
8. Reports and UI use the same backend results.
9. Route optimisation receives only physical-visit jobs.
10. Core analytics and routing do not require paid external APIs.
11. Same input and fixed seed should produce deterministic outputs.
12. No dead buttons or placeholder features should appear in the active UI.

---

## 19. Current Startup Model

Typical local backend startup:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Typical React frontend startup:

```bash
cd frontend
npm run dev
```

Legacy/approved Streamlit fallback code remains under `dashboard/`:

```bash
uv run streamlit run dashboard/Home.py --server.port 8501
```

The primary demo path requires `DATABASE_URL` to point to the configured Neon/PostgreSQL database.

---

## 20. Authoritative Detailed Documents

Detailed contracts are stored under `docs/project/`.

Use:

* `01_project_charter.md` for scope and purpose;
* `02_product_requirements.md` for user requirements;
* `03_data_contract.md` for dataset schemas;
* `04_synthetic_data_spec.md` for data generation;
* `05_business_rules.md` for operational decisions;
* `06_solution_architecture.md` for system boundaries;
* `07_api_contract.md` for backend interfaces;
* `08_ml_experiment_plan.md` for modelling;
* `09_ui_screen_spec.md` for dashboard design;
* `10_test_and_acceptance_plan.md` for validation;
* `11_task_ownership_matrix.md` for dependencies;
* `12_demo_script.md` for presentation flow.

If this context file conflicts with the formal project documents, follow the precedence defined in `AGENTS.md` and report the contradiction before implementation.
