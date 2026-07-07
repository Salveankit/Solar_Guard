# 01 — Project Charter

## 1. Project name

**SolarGuard — Rooftop Solar Performance and Service Intelligence**

## 2. Business problem

A rooftop-solar EPC or service operator managing hundreds or thousands of installations cannot manually inspect every inverter dashboard each day. Operators need a repeatable way to identify genuine underperformance, distinguish data problems from production problems, estimate operational impact, decide whether remote action or a field visit is justified, and produce a practical technician plan.

## 3. POC objective

Build a working capability demonstrator that converts standardised rooftop-solar telemetry into an explainable daily operations-and-maintenance plan.

The POC must demonstrate that the team can combine:

- data ingestion and validation;
- domain-aware time-series feature engineering;
- expected-generation modelling;
- anomaly and probable-cause reasoning;
- energy-value and service-priority calculations;
- technician assignment and route optimisation;
- FastAPI backend services;
- a polished operational dashboard in the active React/Vite frontend, with the original Streamlit dashboard retained as fallback POC code;
- deterministic testing and reproducible deployment.

## 4. Intended audience

Primary presentation audience:

- client leadership;
- EPC operations leadership;
- internal delivery leadership;
- technical reviewers evaluating team capability.

Primary POC users:

1. EPC Operations Manager
2. Service Technician

## 5. Scope included

1. Load pre-generated demo CSVs and validate their structure.
2. Analyse 30 simulated Pune-region rooftop sites.
3. Estimate expected 15-minute generation.
4. Compare expected and actual generation.
5. Detect persistent performance deviations.
6. Classify probable operational issue category.
7. Present confidence, evidence, and limitations.
8. Estimate energy loss and recoverable energy value.
9. Rank service incidents.
10. Distinguish remote-check candidates from field-visit candidates.
11. Assign jobs to two technicians and optimise visit order.
12. Download a daily O&M plan.

## 6. Explicit exclusions

The following are not part of this POC:

- live inverter-vendor API integrations;
- production real-time streaming;
- customer mobile application;
- authentication or role-based access;
- notifications, WhatsApp, SMS, or email workflows;
- production-grade multi-tenancy;
- Kafka, Airflow, Redis, or Kubernetes;
- live traffic-aware routing;
- automated model retraining or production monitoring;
- guaranteed fault diagnosis or field-validated accuracy;
- LLM-based numeric reasoning or routing.

## 7. Success definition

The POC succeeds when leadership can observe one complete operational story:

> Raw rooftop telemetry is validated, expected generation is calculated, abnormal sites are identified and explained, economic impact is estimated, only justified field jobs are selected, and technicians receive an optimised next-day plan.

## 8. Business success indicators shown in the demo

These are **estimated POC outputs**, not production claims:

- sites analysed;
- incidents requiring attention;
- remote-check candidates;
- field visits recommended;
- estimated energy value at risk;
- recoverable energy estimate;
- unnecessary visits avoided;
- naive versus optimised route distance;
- estimated kilometres avoided.

## 9. Technical success indicators

- deterministic dataset generation using a fixed seed;
- all seven canonical datasets validate successfully;
- expected-generation model executes for every eligible interval;
- no night-time false alerts;
- cloudy-weather reduction does not automatically become a fault;
- missing telemetry becomes a communication issue, not an outage;
- injected incidents are detected by scenario-level validation;
- service queue and route planner use a single backend source of truth;
- active UI routes load without dead controls, backend-engineering copy leakage, or raw exceptions;
- one-command or documented two-command local startup.

## 10. Constraints

| Constraint | Decision |
|---|---|
| Timeline | 1–2 days |
| Data | Synthetic but operationally realistic |
| Hardware | None required |
| Paid APIs | None required |
| Network dependence | Neon/PostgreSQL connectivity is required for the primary demo path; analytics and routing must not depend on external APIs beyond the configured database |
| Team objective | Demonstrate breadth and engineering discipline, not enterprise accuracy |

## 11. Key assumptions

- Each site has valid capacity and coordinates.
- Weather zones provide irradiance, temperature, cloud cover, rainfall, and wind.
- Energy value uses a configurable ₹/kWh assumption.
- Technician visit and cleaning costs are configurable.
- Fault outputs are probable categories supported by evidence.
- `fault_ground_truth.csv` is hidden from the operational pipeline.
- A Neon/PostgreSQL database is available before the demo, with credentials supplied through environment configuration and not committed to the repository.
- Current charts and weather context are derived from synthetic demo data and backend analysis outputs; they are not live weather or inverter feeds.

## 12. Governance

### Decision authority

- Scope and timeline: Project Manager
- Technical architecture: Solution Architect
- Data and ML rules: AI/ML Lead
- Domain realism: Solar Domain Reviewer
- Release readiness: Project Manager + QA

### Change rule

Any feature not listed in the included scope requires removal of an existing feature of comparable effort. There is no additive scope expansion during the POC build.

## 13. Go/No-Go gate

### GO when

- all canonical schemas are frozen;
- synthetic generator produces deterministic linked datasets;
- probable-cause rules are documented;
- one complete service queue can be produced in Python before UI integration;
- UI wireframe and API contract are approved.

### NO-GO or reduce scope when

- model development blocks the deterministic baseline;
- external map or weather dependency becomes mandatory;
- exact component-failure claims are introduced;
- UI consumes effort before analytics output is stable;
- inconsistent calculations appear across screens.
