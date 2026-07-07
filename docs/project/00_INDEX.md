# SolarGuard POC — Project Initiation & Execution Pack

**Version:** 1.1
**Project type:** Client/leadership capability-demonstration POC  
**Target delivery:** 1–2 working days  
**Region:** Pune and surrounding areas  
**Data mode:** Operationally realistic synthetic data

## Purpose

This pack converts the approved SolarGuard brainstorming and plan of action into implementation-ready specifications. It is the single reference for product scope, data, business rules, APIs, ML design, UI behavior, testing, ownership, and the final demo.

Version 1.1 aligns the documentation with the current repository shape: FastAPI remains the backend source of truth, the active user-facing dashboard is the React/Vite frontend in `frontend/`, and the original Streamlit dashboard remains in `dashboard/` as retained POC/fallback code.

## Document order

1. `01_project_charter.md` — why the project exists and the decision boundaries.
2. `02_product_requirements.md` — personas, workflows, requirements, and acceptance criteria.
3. `03_data_contract.md` — canonical datasets, columns, types, units, and validation.
4. `04_synthetic_data_spec.md` — generation logic, incident injection, and ground truth.
5. `05_business_rules.md` — anomaly, diagnosis, cleaning, dispatch, and priority rules.
6. `06_solution_architecture.md` — system components, data flow, repository, and failure behavior.
7. `07_api_contract.md` — FastAPI endpoints, payloads, and standard errors.
8. `08_ml_experiment_plan.md` — baseline, XGBoost experiment, validation, and evaluation.
9. `09_ui_screen_spec.md` — current dashboard routes and interaction requirements.
10. `10_test_and_acceptance_plan.md` — unit, integration, scenario, and demo gates.
11. `11_task_ownership_matrix.md` — work breakdown, dependencies, owners, and checkpoints.
12. `12_demo_script.md` — fixed client/leadership walkthrough and Q&A handling.

## Source-of-truth rules

- Backend services own calculations; the active React/Vite frontend and retained Streamlit dashboard only display backend outputs.
- `fault_ground_truth.csv` is for evaluation only and must never drive production-facing diagnosis.
- All fault labels shown to users are **probable issue categories**, not confirmed component failures.
- Missing telemetry is not the same as zero generation.
- Synthetic-data limitations must remain visible in the demo.
- Thresholds and costs must be configurable, not hardcoded throughout the codebase.
- Core functionality must not depend on live inverter, weather, traffic, mapping, or LLM APIs.

## Frozen POC profile

| Item | Decision |
|---|---|
| Sites | 30 |
| Historical duration | 30 days |
| Telemetry interval | 15 minutes |
| Approximate telemetry rows | 86,400 |
| Technicians | 2 |
| Injected incidents | 10 plus optional ambiguous cases |
| Fault taxonomy | Communication, sudden outage, gradual underperformance, time-specific underperformance, unknown |
| Default energy value | ₹8/kWh |
| Default field-visit cost | ₹800 |
| Application | FastAPI backend + active React/Vite dashboard; Streamlit retained as fallback/legacy POC UI |
| Storage | Neon/PostgreSQL + CSV artifacts |
| Core ML | Physics-aware features + XGBoost expected-generation model |
| Routing | OR-Tools using local distance matrix |
