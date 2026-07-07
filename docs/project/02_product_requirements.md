# 02 — Product Requirements Document

## 1. Product statement

SolarGuard is a decision-support POC for rooftop-solar operations. It analyses fleet telemetry and produces a ranked, explainable, and route-aware daily O&M plan.

## 2. Personas

### 2.1 EPC Operations Manager

Needs to:

- understand fleet health quickly;
- identify which sites need attention;
- avoid unnecessary dispatches;
- see evidence behind recommendations;
- prioritise work using energy, complaint, and SLA impact;
- approve tomorrow's service plan.

### 2.2 Service Technician

Needs to:

- know which sites are assigned;
- see visit order and site location;
- understand suspected issue and evidence;
- know the recommended first action;
- see required skill and expected job duration.

## 3. Primary user journey

1. Operations manager loads or selects the demo dataset.
2. System validates data completeness and schema.
3. Manager runs fleet analysis.
4. System calculates expected generation and incidents.
5. Fleet summary shows healthy, remote-check, and field-visit counts.
6. Manager opens a site diagnosis and reviews evidence.
7. Manager reviews the ranked service queue.
8. System selects economically and operationally justified field jobs.
9. Route planner assigns jobs to technicians.
10. Manager downloads the daily O&M plan.

## 3.1 Current user-facing interface

The active implemented interface is the React/Vite dashboard in `frontend/`. It is backed by FastAPI and should not recalculate backend business logic.

Implemented routes:

- `/` - Command Centre
- `/fleet` - Fleet Sites
- `/diagnostics` and `/sites/{site_id}` - Site Diagnostics
- `/incidents` - Incidents
- `/service-queue` - Service Queue
- `/technician-plan` - Technician Plan
- `/reports` - Reports

The Streamlit dashboard under `dashboard/` remains retained POC/fallback code and is not the primary interface being polished.

## 4. Functional requirements

### FR-01 — Load demo data

The user can initialise the pre-generated demo dataset.

**Acceptance criteria**

- All required tables are loaded.
- Success response lists row counts by dataset.
- Re-running the action is idempotent or safely resets demo data.
- Validation failures display the exact file and field problem.

### FR-02 — Upload canonical CSV files

The user can upload standard SolarGuard CSVs.

**Acceptance criteria**

- Only approved file types are accepted.
- Required columns are validated.
- Unknown site IDs, invalid timestamps, and impossible values are reported.
- File failure does not crash the application.

### FR-03 — Fleet summary

The system provides fleet-level operational KPIs.

**Required output**

- monitored sites;
- healthy sites;
- communication issues;
- underperforming sites;
- unknown/insufficient-data sites;
- remote-check candidates;
- recommended field visits;
- estimated daily energy value at risk;
- estimated recoverable energy.

### FR-04 — Expected-versus-actual analysis

The system calculates expected generation for eligible 15-minute intervals and daily totals.

**Acceptance criteria**

- No expected-output fault check runs at night.
- Missing telemetry remains missing; it is not imputed as zero for diagnosis.
- Each diagnostic exposes expected, actual, residual, and performance ratio.

### FR-05 — Persistent anomaly detection

The system detects meaningful underperformance only after daylight, magnitude, and persistence gates are met.

**Acceptance criteria**

- One isolated low point does not create a high-priority incident.
- Low output during low irradiance does not automatically create a fault.
- Thresholds are configurable.

### FR-06 — Probable-cause explanation

Every incident contains:

- probable issue category;
- confidence score and label;
- supporting evidence;
- recommended next action;
- data limitation note where relevant.

The system must support:

- communication/data failure;
- sudden production outage;
- gradual persistent underperformance;
- time-specific underperformance;
- unknown/insufficient evidence.

### FR-07 — Energy and value calculation

The system estimates:

- energy loss;
- energy value at risk;
- recoverable energy/value using confidence and recoverability assumptions.

Negative loss values must be clipped to zero.

### FR-08 — Cleaning decision

For gradual-underperformance candidates, the system evaluates whether cleaning is economically justified.

**Acceptance criteria**

- Uses configurable cleaning cost and safety margin.
- Considers forecast rain.
- Returns a clear yes/no/defer outcome and calculation breakdown.

### FR-09 — Service-priority queue

The queue ranks incidents using transparent components.

**Required columns**

- priority label and score;
- site ID;
- probable issue;
- confidence;
- persistence;
- energy value at risk;
- complaint/SLA status;
- recommended action;
- visit required.

### FR-10 — Remote versus field decision

The system distinguishes:

- no action;
- remote check;
- monitor;
- schedule cleaning;
- technician visit;
- collect more data.

Communication failures should default to remote checks unless another confirmed signal supports a visit.

### FR-11 — Route optimisation

Only eligible field jobs are sent to route optimisation.

**Acceptance criteria**

- No job is assigned twice.
- Technician skill and maximum-visit constraints are respected.
- Route starts at service hub.
- Output includes route order, distance, duration, and assigned jobs.
- Naive and optimised distance are both shown.

### FR-12 — Daily O&M plan export

The user can download a CSV report containing:

- technician;
- stop order;
- site;
- issue category;
- evidence summary;
- recommended action;
- priority;
- expected job duration;
- estimated recoverable energy/value.

## 5. Non-functional requirements

### NFR-01 — Performance

Target on standard developer laptop:

- fleet summary: under 3 seconds after analysis is available;
- site diagnostics: under 2 seconds;
- route optimisation: under 5 seconds;
- full analysis for demo fleet: target under 30 seconds.

### NFR-02 — Determinism

- Fixed random seed for data generation and model training.
- Same input and configuration must generate the same service queue.

### NFR-03 — Reliability

- Controlled errors instead of raw tracebacks.
- Empty states for no incidents and no route-worthy jobs.
- Cached or precomputed demo results available as fallback.

### NFR-04 — Explainability

No user-facing score may appear without its major inputs or evidence.

### NFR-05 — Privacy

- No real customer names, phone numbers, addresses, or account IDs.
- Use anonymous site IDs and approximate demo coordinates.

### NFR-06 — Accessibility and usability

- Clear labels and units.
- Do not rely only on colour to convey severity.
- Tables must remain readable at common laptop resolution.
- User-facing copy must avoid backend-engineering leakage such as "backend analysis", raw stack traces, raw JSON, or internal implementation notes.
- Refresh should be page-aware and must not invalidate unrelated heavy data when the current route does not need it.

## 6. POC-level business acceptance scenarios

### Scenario A — Healthy site

Given valid data and expected performance, no incident is created.

### Scenario B — Cloudy conditions

Given low irradiance and proportionately low output, the site is not labelled faulty.

### Scenario C — Communication issue

Given missing heartbeat and rows, the system recommends a remote connectivity check.

### Scenario D — Sudden outage

Given strong irradiance and near-zero output for persistent intervals, the incident is high priority.

### Scenario E — Gradual decline

Given repeated clear-sky degradation, the system evaluates soiling/degradation and cleaning economics.

### Scenario F — Repeated time-window loss

Given loss in the same daily hour window, the system suggests time-dependent shading or obstruction.

### Scenario G — Ambiguous evidence

Given low completeness or overlapping patterns, the system returns unknown/insufficient evidence.

## 7. Out-of-scope product requests

Any request for login, alerts, mobile app, vendor integration, real-time streaming, chatbot, customer billing, or live traffic must be documented as a production roadmap item, not implemented during the POC.
