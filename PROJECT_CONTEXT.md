# SolarGuard Project Context

## 1. Project identity

SolarGuard is a rooftop-solar performance and field-service decision intelligence POC.

It analyses fleet-level solar telemetry and converts it into an explainable daily operations and maintenance plan.

The application is designed to demonstrate the team's ability to combine:

* data engineering;
* solar-domain modelling;
* time-series machine learning;
* anomaly detection;
* explainable decision logic;
* backend API development;
* operational dashboards;
* technician route optimisation.

SolarGuard is not intended to be presented as a production-ready autonomous fault-diagnosis system.

---

## 2. Business problem

A rooftop-solar EPC or installer may manage hundreds or thousands of geographically distributed installations.

An operations manager cannot manually inspect every inverter dashboard every day.

The manager needs to know:

1. Which sites are genuinely underperforming?
2. Is the underperformance likely caused by weather or an operational issue?
3. Which cases can be checked remotely?
4. Which sites require technician visits?
5. Which cases have the highest recoverable energy impact?
6. How should tomorrow's technician visits be grouped and routed?

SolarGuard converts raw operational data into these decisions.

---

## 3. Primary users

### EPC Operations Manager

The operations manager supervises the solar fleet.

The manager uses SolarGuard to:

* review fleet health;
* identify sites requiring attention;
* understand probable issue categories;
* review evidence behind recommendations;
* estimate energy value at risk;
* prioritise service jobs;
* approve the next-day technician plan.

### Service Technician

The technician receives an ordered daily visit plan.

The technician needs:

* site identifier;
* probable issue;
* reason for the visit;
* recommended diagnostic action;
* required skill or equipment;
* estimated job duration;
* visit sequence.

The POC does not include a separate technician mobile application.

---

## 4. Core product question

Every major feature must help answer:

> Which solar sites need attention tomorrow, why do they need attention, and what is the most efficient action?

Features that do not materially support this question are outside the POC scope.

---

## 5. End-to-end product flow

```text
Site metadata
      +
15-minute inverter telemetry
      +
Historical weather data
      +
Service history
      +
Technician information
            ↓
Data ingestion and validation
            ↓
Data completeness and quality assessment
            ↓
Expected-generation estimation
            ↓
Actual-versus-expected comparison
            ↓
Persistent anomaly detection
            ↓
Explainable probable-cause reasoning
            ↓
Energy-loss and recoverable-value estimation
            ↓
Service-priority ranking
            ↓
Remote-check versus field-visit decision
            ↓
Technician assignment and route optimisation
            ↓
Daily O&M plan
```

---

## 6. Demonstration scenario

The default POC represents:

* 30 rooftop-solar installations;
* Pune and nearby regions;
* 30 days of historical telemetry;
* 15-minute readings;
* two technicians;
* one service hub;
* ten injected operational incidents;
* four primary incident patterns;
* one unknown or insufficient-evidence state.

The dataset is synthetic but must remain operationally realistic and internally consistent.

---

## 7. Core domain entities

### Site

A rooftop-solar installation.

Important attributes include:

* site ID;
* installed capacity;
* geographic coordinates;
* inverter vendor and model;
* panel orientation;
* commissioning date;
* energy-value assumption;
* service region.

### Telemetry reading

A time-stamped operational measurement from a site.

Examples:

* generation;
* AC power;
* DC voltage;
* DC current;
* AC voltage;
* inverter temperature;
* inverter status;
* alarm code.

### Weather observation

Weather information associated with a site or weather zone.

Important values include:

* irradiance;
* temperature;
* cloud cover;
* rainfall;
* wind speed.

### Incident

A detected period of abnormal or unavailable operation.

An incident has:

* site;
* start and end time;
* probable issue category;
* severity;
* persistence;
* confidence;
* supporting evidence;
* recommended action.

### Service job

An operational action created from an incident.

A service job may require:

* remote check;
* cleaning;
* technical inspection;
* physical technician visit;
* additional data collection.

### Technician

A field-service resource with:

* service hub;
* shift timing;
* skill set;
* maximum visits;
* assigned route.

---

## 8. Incident taxonomy

SolarGuard uses the following operational categories.

### Communication or data failure

Telemetry is missing, stale or unavailable.

This must not be treated as zero solar generation.

Typical action:

* check data logger;
* check network connectivity;
* contact customer remotely;
* avoid immediate dispatch unless necessary.

### Sudden production outage

Expected output is meaningful, but actual output suddenly drops close to zero.

Possible causes may include:

* inverter shutdown;
* grid outage;
* AC-side interruption;
* protective trip.

The product reports a probable category, not a confirmed component failure.

### Gradual persistent underperformance

Output decreases gradually and remains below the weather-normalised expectation.

Possible causes may include:

* soiling;
* vegetation;
* system degradation;
* sensor drift.

Cleaning should be recommended only when economically justified.

### Time-specific underperformance

Loss repeats during similar hours across multiple days.

Possible causes may include:

* recurring shade;
* obstruction;
* orientation-related effects.

### Unknown or insufficient evidence

Available data does not support a reliable probable-cause conclusion.

This is a valid and mandatory output state.

---

## 9. Intelligence model

SolarGuard does not use one model for everything.

### Expected-generation estimation

Purpose:

Estimate how much energy a healthy site should have produced under the observed conditions.

Approach:

```text
Solar and weather-aware features
            +
Historical site behaviour
            ↓
Expected-generation model
```

The POC uses:

* solar-position and domain features;
* weather and irradiance;
* site capacity and orientation;
* XGBoost regression;
* a simple physical or formula-based baseline for comparison.

### Anomaly detection

Anomaly detection compares actual output with expected output.

Core measures:

```text
Residual = Actual generation - Expected generation
```

```text
Performance ratio = Actual generation / Expected generation
```

An alert requires:

* sufficient expected generation;
* meaningful underperformance;
* persistence across consecutive intervals.

A single low reading should not automatically create an incident.

### Probable-cause reasoning

The POC uses explainable business and telemetry rules.

It does not train a production fault classifier on synthetic labels.

Every probable cause should include:

* issue category;
* confidence;
* supporting evidence;
* data limitations;
* recommended next action.

### Priority scoring

The priority score combines:

* recoverable energy impact;
* incident persistence;
* diagnostic confidence;
* customer complaint urgency;
* SLA or warranty risk;
* route-clustering benefit.

The score must be explainable. It must not be presented as an unexplained magic number.

### Route optimisation

Only service jobs requiring physical visits enter the route optimiser.

The optimiser considers:

* technician skills;
* visit limits;
* shift duration;
* job duration;
* job priority;
* site coordinates;
* service-hub location.

Route optimisation is performed using OR-Tools.

---

## 10. Business terminology

Use:

* energy loss;
* estimated energy value at risk;
* estimated savings impact;
* recoverable energy value;
* probable issue;
* recommended action;
* service priority.

Avoid:

* guaranteed revenue loss;
* confirmed fault;
* exact component failure;
* autonomous repair;
* production-validated accuracy.

Residential rooftop systems may represent electricity savings rather than direct energy-sale revenue.

---

## 11. Application architecture

```text
Streamlit dashboard
        ↓ HTTP
FastAPI application
        ↓
Application services
        ↓
Neon/PostgreSQL persistence
        ↓
Analytics and optimisation modules
```

Core backend services:

* data ingestion;
* data validation;
* expected generation;
* anomaly detection;
* probable-cause reasoning;
* loss estimation;
* priority scoring;
* route optimisation;
* report generation.

This is a modular monolith.

It is not a microservices architecture.

---

## 12. Source-of-truth rule

FastAPI backend services are the source of truth for:

* diagnostics;
* energy loss;
* probable causes;
* confidence;
* priority scores;
* service recommendations;
* technician routes.

The Streamlit dashboard must not independently recalculate these values.

The dashboard displays backend results.

This prevents conflicting numbers between:

* API responses;
* dashboard pages;
* downloaded reports.

---

## 13. Data truth rules

The following distinctions must always be preserved.

### Missing is not zero

Missing telemetry means the system did not receive a reading.

Zero generation means a reading was received and the measured output was zero.

These represent different operational conditions.

### Weather-driven loss is not automatically a fault

Low output during low irradiance or heavy cloud cover should not automatically create an underperformance incident.

### Underperformance is not confirmed failure

A performance deviation may indicate a probable operational issue, but available telemetry may not identify the exact physical cause.

### Synthetic ground truth is evaluation-only

`fault_ground_truth.csv` is used to validate injected POC scenarios.

It must not be used by the production-facing diagnostic pipeline to directly determine the answer.

---

## 14. POC output

The primary output is a daily O&M plan.

Example:

```text
Site: MH-142
Status: Underperforming
Expected generation: 23.4 kWh
Actual generation: 14.2 kWh
Energy loss: 9.2 kWh

Probable issue:
Sudden inverter or grid-side interruption

Confidence:
82%

Evidence:
- Irradiance remained high
- Output dropped close to zero
- Deviation persisted for six intervals

Recommended action:
Perform remote inverter and grid checks.
Dispatch a technician if the issue remains unresolved.

Priority:
High
```

The fleet-level output should also include:

* remote-check cases;
* physical-visit cases;
* cleaning candidates;
* insufficient-data cases;
* technician assignments;
* route order;
* estimated distance;
* distance saved compared with a naive route.

---

## 15. User interface mental model

### Daily Operations Command Centre

Answers:

> What happened across the fleet, and what requires attention?

### Site Diagnostics

Answers:

> Why was this site flagged, and what evidence supports the recommendation?

### Service Decision Queue

Answers:

> Which actions should be completed first?

### Technician Plan

Answers:

> Who should visit which sites, and in what order?

Every screen should support one of these questions.

---

## 16. POC success criteria

The POC is successful when it demonstrates that the team can:

1. create and validate realistic solar telemetry;
2. estimate expected generation;
3. distinguish weather-related reduction from persistent abnormal performance;
4. separate communication failure from zero production;
5. produce explainable probable-cause outputs;
6. estimate energy and business impact;
7. rank service actions;
8. optimise technician routes;
9. expose results through FastAPI;
10. present the workflow through a usable dashboard.

Production-grade accuracy is not the success criterion.

---

## 17. Non-goals

The POC does not include:

* production authentication;
* role-based access;
* customer mobile application;
* live inverter APIs;
* multiple inverter adapters;
* live weather integration;
* streaming infrastructure;
* Kafka;
* Airflow;
* Redis;
* Celery;
* Kubernetes;
* real-time traffic;
* LLM chatbot;
* autonomous hardware control;
* guaranteed fault diagnosis;
* production model monitoring.

These are possible future phases, not current requirements.

---

## 18. Technology mental model

| Responsibility            | Technology            |
| ------------------------- | --------------------- |
| Language                  | Python 3.11           |
| Backend API               | FastAPI               |
| Validation                | Pydantic              |
| Data processing           | Pandas and NumPy      |
| Solar-domain features     | pvlib                 |
| Expected-generation model | XGBoost               |
| ML utilities              | scikit-learn          |
| Persistence               | Neon/PostgreSQL and SQLAlchemy |
| Dashboard                 | Streamlit             |
| Charts                    | Plotly                |
| Route optimisation        | OR-Tools              |
| Map visualisation         | Folium                |
| Tests                     | Pytest                |
| Code quality              | Ruff                  |
| Packaging                 | Docker Compose        |

Technology changes require an explicit architectural decision. Coding agents should not silently replace this stack.

---

## 19. Engineering invariants

The following must remain true throughout development:

1. Missing telemetry is never silently converted to zero.
2. Fault output is described as probable, not confirmed.
3. Unknown or insufficient evidence is supported.
4. Fault-injected intervals are excluded from healthy-model training.
5. Synthetic ground truth is not used as a diagnostic shortcut.
6. Business thresholds are configuration-driven.
7. Backend services remain the source of truth.
8. Dashboard and downloadable reports use the same backend results.
9. Route optimisation receives only physical-visit jobs.
10. External paid APIs are not required for the core demo.
11. The same input and fixed seed produce deterministic output.
12. Existing working functionality must not be broken by unrelated changes.

---

## 20. Authoritative detailed documents

Detailed contracts are stored under:

`docs/project/`

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

This file provides the project mental model.

The detailed documents provide implementation authority.
