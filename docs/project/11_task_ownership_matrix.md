# 11 — Task Ownership and Dependency Matrix

## 1. Delivery model

The plan assumes a compact team. Roles may be combined, but accountability must remain explicit.

### Role codes

- PM — Project Manager
- ARCH — Solution Architect
- ML — AI/ML + Data Engineer
- BE — Backend Engineer
- FE — Frontend/Product Engineer
- QA — QA Engineer
- DOMAIN — Solar-domain reviewer

## 2. Work breakdown

| ID | Task | Owner | Reviewer | Dependency | Output | Exit criteria |
|---|---|---|---|---|---|---|
| GOV-01 | Freeze charter and scope | PM | ARCH | None | Approved charter | Included/excluded scope agreed |
| GOV-02 | Freeze terminology and claims | PM | DOMAIN | GOV-01 | Claim guide | No confirmed-fault/guaranteed-savings wording |
| DATA-01 | Implement canonical schemas | ML | ARCH/BE | GOV-01 | Pydantic/data schema | All columns/types frozen |
| DATA-02 | Generate site master | ML | DOMAIN | DATA-01 | site_master.csv | 30 valid synthetic sites |
| DATA-03 | Generate weather history/forecast | ML | DOMAIN | DATA-02 | weather CSVs | Zones/timestamps valid |
| DATA-04 | Generate healthy telemetry | ML | DOMAIN | DATA-03 | telemetry base | Profiles scale with site/weather |
| DATA-05 | Inject incidents and ground truth | ML | QA | DATA-04 | final telemetry + ground truth | 10 documented incidents |
| DATA-06 | Generate service and technician data | ML | BE | DATA-02 | service/technician CSVs | Valid keys/constraints |
| ML-01 | Build deterministic expected baseline | ML | ARCH | DATA-04 | baseline module | Produces expected output |
| ML-02 | Train XGBoost expected-generation model | ML | QA | ML-01/DATA-05 | model artifact | Time split and metrics saved; fallback baseline remains available |
| ML-03 | Implement anomaly grouping | ML | QA | ML-01 | anomaly module | Persistence/daylight rules pass |
| ML-04 | Implement probable-cause engine | ML | DOMAIN/QA | ML-03 | cause module | Five categories supported |
| ML-05 | Implement impact/priority rules | ML | PM/QA | ML-04 | ranked queue dataframe | Breakdown sums correctly |
| BE-01 | Create DB models and loader | BE | ARCH | DATA-01 | Neon/PostgreSQL schema/loader | All datasets load |
| BE-02 | Implement analysis orchestration | BE | ML | ML-05/BE-01 | analysis service | Stores completed run |
| BE-03 | Implement API endpoints | BE | ARCH/QA | BE-02 | FastAPI app | Swagger and contracts pass |
| OPT-01 | Implement distance matrix | BE | QA | DATA-02 | distance service | Symmetric valid matrix |
| OPT-02 | Implement OR-Tools assignment | BE | ARCH/QA | ML-05/OPT-01/DATA-06 | route plan | Skills/capacity respected |
| FE-01 | Build API client and shell | FE | BE | BE-03 | React/Vite shell and retained Streamlit fallback | API health works |
| FE-02 | Command Centre | FE | PM/QA | FE-01 | Command Centre route | KPIs reconcile |
| FE-03 | Site Diagnostics and Fleet Sites | FE | ML/QA | FE-01 | Diagnostics/fleet routes | Evidence and charts correct |
| FE-04 | Incidents and Service Queue | FE | PM/QA | FE-01 | Incident/queue routes | Filters/sort/navigation work |
| FE-05 | Technician Plan and Reports | FE | BE/QA | OPT-02/FE-01 | Technician/report routes | Route + export work |
| QA-01 | Unit/data tests | QA | Owners | DATA/ML modules | Pytest suite | Critical calculations covered |
| QA-02 | Scenario validation | QA | ML/DOMAIN | ML-05 | scenario report | Mandatory scenarios pass |
| QA-03 | API/E2E tests | QA | BE/FE | BE-03/FE pages | integration report | Full path passes |
| DEMO-01 | Create fixed demo dataset/run | PM | QA | All core | demo package | Stable deterministic output |
| DEMO-02 | Rehearse script and Q&A | PM | All leads | DEMO-01 | rehearsal notes | Two clean runs |
| PACK-01 | Docker/local startup | ARCH/BE | QA | Core complete | compose/start script | Clean startup verified |

## 3. Critical path

```text
GOV-01
→ DATA-01
→ DATA-02/03/04/05
→ ML-01/03/04/05
→ BE-01/02/03
→ FE-02/03/04
→ OPT-01/02
→ FE-05
→ QA-02/03
→ DEMO-01/02
```

## 4. Parallel work opportunities

After data contract freeze:

- ML builds generator and analytics.
- BE builds DB, schemas, and mocked API responses.
- FE builds page shell against documented mock payloads.
- QA writes expected scenario tests.

Integration starts only when API payloads and calculations are stable.

## 5. Two-day execution board

### Day 1 — Foundation and intelligence

#### Morning checkpoint

- charter, schemas, config frozen;
- repository created;
- site/weather generator working.

#### Midday checkpoint

- healthy telemetry and incident injection complete;
- validation and ground-truth summary complete.

#### Evening checkpoint

- expected model/baseline complete;
- anomaly/cause/priority pipeline produces ranked queue in Python;
- mandatory scenario spot-check passes.

**Day 1 hard gate:** Do not prioritise dashboard polish unless ranked queue works.

### Day 2 — Product and demonstration

#### Morning checkpoint

- Neon/PostgreSQL loader and FastAPI endpoints operational;
- command centre and site diagnostics connected.

#### Midday checkpoint

- service queue connected;
- OR-Tools route output valid;
- technician plan page working.

#### Final checkpoint

- tests pass;
- download works;
- deterministic demo run saved;
- complete presentation rehearsed.

## 6. RACI for key decisions

| Decision | PM | ARCH | ML | BE | FE | QA | DOMAIN |
|---|---|---|---|---|---|---|---|
| Scope | A/R | C | C | C | C | C | C |
| Data contract | C | A | R | C | I | C | C |
| Fault definitions | C | C | R | I | I | C | A/R |
| ML acceptance | I | C | A/R | I | I | C | C |
| API contract | I | A | C | R | C | C | I |
| UI workflow | A | C | C | C | R | C | I |
| Release readiness | A | C | C | C | C | R | I |

Legend: R Responsible, A Accountable, C Consulted, I Informed.

## 7. Change-control rules

- New feature requires PM approval and explicit trade-off.
- Threshold change requires ML + QA update to scenario expectations.
- API payload change requires BE + FE + QA acknowledgement.
- Data-schema change requires ARCH approval and regeneration of fixtures.
- Demo dataset is frozen after final QA unless a Critical defect requires change.

## 8. Definition of handoff by role

### ML handoff

- generated datasets;
- data summary;
- model artifact and metrics;
- deterministic analysis function;
- scenario expectations.

### BE handoff

- documented APIs;
- database migration/init;
- error formats;
- route service;
- startup instructions.

### FE handoff

- complete active React routes;
- API-only data flow;
- empty/error/loading states;
- download interaction.

### QA handoff

- automated test results;
- scenario matrix;
- known limitations;
- demo go/no-go status.

## 9. Daily communication

Use brief checkpoints focused on blockers and outputs:

- What completed?
- What is the next dependency?
- What risk can break the demo?
- Is any calculation or contract inconsistent?

Avoid status meetings that reopen approved scope.
