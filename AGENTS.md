# SolarGuard AI Coding Agent Instructions

## Project purpose

SolarGuard is a functional POC that demonstrates the team's capability to convert rooftop-solar telemetry into an explainable daily operations and maintenance plan.

This is not a production-ready solar fault-diagnosis platform.

## Authoritative project documents

All approved project specifications are stored in:

`docs/project/`

Begin with:

1. `docs/project/00_INDEX.md`
2. `docs/project/01_project_charter.md`
3. `docs/project/02_product_requirements.md`
4. `docs/project/06_solution_architecture.md`
5. The task-specific documents relevant to the current implementation phase

Do not invent requirements that are absent from these documents.

## Document precedence

When documents appear to conflict, use this priority:

1. `01_project_charter.md`
2. `02_product_requirements.md`
3. `03_data_contract.md`
4. `05_business_rules.md`
5. `06_solution_architecture.md`
6. `07_api_contract.md`
7. `08_ml_experiment_plan.md`
8. `09_ui_screen_spec.md`
9. `10_test_and_acceptance_plan.md`
10. `11_task_ownership_matrix.md`
11. `12_demo_script.md`

Report material contradictions before implementation. Do not silently choose an interpretation.

## Mandatory architecture rules

* Python 3.11 is the application language.
* FastAPI owns backend and business logic.
* Streamlit displays results and calls FastAPI.
* The dashboard must not duplicate or independently recalculate backend business logic.
* Neon/PostgreSQL is the POC database.
* XGBoost is used only for expected-generation estimation.
* Probable-cause classification uses explainable rules.
* OR-Tools handles technician route optimisation.
* Core functionality must not depend on an LLM.
* Missing telemetry and zero generation are different states.
* Diagnostic outputs must use “probable issue,” not “confirmed fault.”
* The application must support an unknown or insufficient-evidence state.
* All thresholds and business assumptions must come from configuration files.
* A fixed random seed must be used for synthetic data and model reproducibility.

## Scope restrictions

Do not add unless explicitly requested:

* authentication;
* role-based access;
* React;
* Redis;
* Celery;
* Kafka;
* Airflow;
* Kubernetes;
* live inverter APIs;
* live weather APIs;
* WhatsApp integration;
* customer mobile application;
* chatbot;
* payment or billing;
* real-time traffic integration;
* microservices.

Do not replace approved technologies merely because another technology is more familiar.

## Required workflow before coding

For every implementation task:

1. Read the relevant project documents.
2. Summarise the requirements that apply to the task.
3. Identify affected files and dependencies.
4. State any ambiguity or conflict.
5. Produce a short implementation plan.
6. Implement only the approved scope.
7. Run relevant unit and integration tests.
8. Report files changed, tests executed and remaining limitations.

Do not modify unrelated working functionality.

## Implementation order

Follow this dependency sequence:

1. Repository and configuration
2. Canonical data schemas
3. Synthetic data generator
4. Data-quality validation
5. Expected-generation baseline and model
6. Anomaly detection
7. Probable-cause rules
8. Energy-loss and priority calculation
9. Neon/PostgreSQL persistence
10. FastAPI endpoints
11. Route optimisation
12. Streamlit dashboard
13. Report generation
14. End-to-end tests
15. Demo validation

Do not begin dashboard development before the ranked service queue works from a Python script or backend service.

## Quality requirements

* Use type hints.
* Use Pydantic for API validation.
* Use clear service boundaries.
* Avoid large multipurpose functions.
* Add useful error messages.
* Do not expose raw stack traces in the UI.
* Avoid hardcoded paths and thresholds.
* Add tests for calculations and business rules.
* Keep outputs deterministic.
* Preserve consistency between API, UI and downloaded reports.
* Do not create dead buttons or placeholder features.

## Completion reporting format

At the end of each task, report:

### Implemented

What was completed.

### Files changed

Exact relative file paths.

### Tests

Commands executed and results.

### Assumptions

Any approved assumptions used.

### Known limitations

Anything intentionally outside the current POC scope.

### Next dependency

The next task that can safely begin.
