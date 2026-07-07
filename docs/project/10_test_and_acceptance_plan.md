# 10 — Test and Acceptance Plan

## 1. Test objective

Prove that the POC is deterministic, internally consistent, resilient during presentation, and capable of producing the intended operational decisions from the documented scenarios.

This plan validates workflow behavior; it does not claim production field accuracy.

## 2. Test layers

1. Data-contract tests
2. Unit tests
3. ML/data-science tests
4. Business-rule tests
5. API integration tests
6. Frontend unit/build tests
7. End-to-end tests
8. UI acceptance tests
9. Demo resilience tests
10. Scenario validation against hidden ground truth
11. Database connectivity and configuration tests

Database integration tests must run against `TEST_DATABASE_URL`, which must point to a separate Neon test branch or test database. They must not connect to or mutate the presentation Neon database.

## 3. Data-contract tests

| ID | Test | Expected result |
|---|---|---|
| D-01 | Missing required column | File rejected with field-level error |
| D-02 | Duplicate site/timestamp | Duplicate rows rejected/reported |
| D-03 | Unknown site ID in telemetry | Validation failure |
| D-04 | Unparseable timestamp | Validation failure |
| D-05 | Negative generation | Validation failure |
| D-06 | Missing telemetry represented as null + flag | Accepted as communication evidence |
| D-07 | Zero output with data received | Accepted as real observation |
| D-08 | Invalid coordinates | Route-ineligible and validation error |
| D-09 | Inconsistent weather zone | Validation failure |
| D-10 | Fixed seed rerun | Identical generated files |

## 4. Unit tests

### Calculations

- performance ratio;
- energy loss clipping;
- value at risk;
- recoverable value;
- completeness percentage;
- confidence component total;
- priority score and labels;
- Haversine distance;
- cleaning economics.

### Rules

- daylight eligibility;
- persistence grouping;
- communication precedence;
- sudden outage;
- gradual decline;
- repeated time-window loss;
- unknown outcome;
- route eligibility.

## 5. ML validation tests

- Training excludes injected fault windows.
- Training excludes missing/suspect data.
- Chronological split is respected.
- Predictions are non-negative.
- Night predictions are zero after post-processing.
- Predictions stay within plausible capacity limit.
- XGBoost metrics are compared with baseline.
- Model artifact and feature schema versions match.
- Seeded retraining produces materially identical metrics.

## 6. Mandatory scenario tests

### S-01 — Healthy site

**Given:** healthy received telemetry.  
**Expected:** no incident, status healthy.

### S-02 — Cloudy weather

**Given:** low irradiance and correspondingly low output.  
**Expected:** no production-fault alert.

### S-03 — Communication failure

**Given:** missing telemetry for configured persistence.  
**Expected:** communication issue, remote check, no immediate visit.

### S-04 — Sudden outage

**Given:** strong irradiance and near-zero output for >= 4 intervals.  
**Expected:** sudden-outage category, high confidence/priority, remote-then-visit action.

### S-05 — Gradual degradation

**Given:** multi-day decline under comparable weather.  
**Expected:** soiling/degradation category and cleaning evaluation.

### S-06 — Cleaning economically justified

**Given:** high projected recoverable value and no rain.  
**Expected:** schedule cleaning.

### S-07 — Cleaning deferred

**Given:** near-term rain or value below threshold.  
**Expected:** defer/monitor, no immediate cleaning job.

### S-08 — Time-specific loss

**Given:** repeated same-hour residual loss.  
**Expected:** shading/obstruction category.

### S-09 — Ambiguous evidence

**Given:** insufficient completeness/conflicting evidence.  
**Expected:** unknown/collect more data.

### S-10 — Route capacity

**Given:** more jobs than capacity.  
**Expected:** highest-value feasible jobs assigned; others listed with reason.

### S-11 — Skill constraint

**Given:** cleaning-only and inverter-specific jobs.  
**Expected:** matching technician assignments.

### S-12 — No route-worthy jobs

**Given:** only remote/monitor actions.  
**Expected:** valid empty route state.

## 7. API integration tests

- Load demo -> row counts correct.
- Run analysis -> completed run created.
- Fleet summary -> totals reconcile with diagnostics.
- Site diagnosis -> evidence and score breakdown present.
- Service queue -> sorted descending.
- Route optimise -> no duplicate assignments.
- Report download -> rows match route plan.
- Invalid site -> 404 standard error.
- Invalid upload -> 422/400 standard error.
- No completed analysis -> 409/appropriate response.
- Database health endpoint/config check -> safe success/failure response without exposing credentials.
- Invalid or missing `DATABASE_URL` -> controlled startup or health-check failure.
- Demo load rerun -> idempotent reset/load behavior against PostgreSQL.

## 8. End-to-end acceptance flow

```text
Reset/load demo data
→ validate datasets
→ run analysis
→ inspect fleet summary
→ open high-priority site
→ review service queue
→ optimise routes
→ download daily plan
```

Pass criteria:

- completes without manual database edits;
- uses the configured Neon/PostgreSQL database without committing credentials;
- all numbers reconcile;
- no raw exception;
- same input produces same output.

## 8.1 Current verification commands

Backend:

```bash
uv run pytest
```

Frontend:

```bash
cd frontend
npm run lint
npm run build
npm test
```

Documentation-only changes may be checked with:

```bash
git diff --check
```

## 9. UI acceptance

### Global

- active React routes load;
- POC data disclosure visible;
- no dead links/buttons;
- no clipped critical text at standard laptop size;
- units shown;
- loading/empty/error states work.
- no backend-engineering text, raw JSON, or raw exception appears in user-facing UI.

### Command Centre

- KPI totals reconcile;
- top-priority site opens correctly;
- analysis/route action has visible status.

### Site Diagnostics

- expected, actual, and irradiance align by timestamp;
- anomaly window visible;
- probable cause, evidence, limitation, and action visible;
- score breakdown equals API.

### Service Queue

- filters work;
- sorting is correct;
- selected site navigation works.

### Technician Plan

- routes and map/text agree;
- no duplicate stop;
- total distance matches API;
- download file matches visible plan.

## 10. Ground-truth scenario matrix

Produce a QA report with columns:

- incident ID;
- ground-truth type;
- detected category;
- expected action;
- actual action;
- visit expected;
- visit selected;
- result: pass/partial/fail;
- notes.

Avoid presenting a single synthetic “accuracy” score as the main result. Show scenario coverage and explain partial matches.

## 11. Performance checks

On target laptop:

- load demo under 15 seconds;
- analysis target under 30 seconds;
- fleet/site pages under 3 seconds after analysis;
- route optimisation under 5 seconds;
- CSV download under 2 seconds.

## 12. Demo resilience tests

- Start from clean checkout/environment.
- Verify behavior when map tiles or other non-database internet resources are unavailable.
- Verify demo readiness with the approved Neon/PostgreSQL connection available.
- Verify safe failure messaging when the database is unavailable or credentials are invalid.
- Verify analysis works without map tiles.
- Verify pre-trained model fallback.
- Verify cached completed run remains usable.
- Keep screenshots and exported O&M plan.
- Rehearse full flow twice without resetting hidden state manually.

## 13. Severity and release decision

### Critical

- application does not start;
- configured database cannot be reached for the primary demo path;
- analysis cannot complete;
- queue/route numbers conflict;
- ground truth exposed;
- raw customer-like PII present;
- primary demo scenario fails.

### High

- cloudy-day false fault;
- communication treated as zero outage;
- duplicate route assignment;
- download inconsistent;
- dead primary button.

### Medium

- layout issue;
- secondary filter problem;
- non-critical warning text.

Release rule:

- zero Critical defects;
- zero unresolved High defects affecting demo path;
- Medium defects documented and bypassed if necessary.

## 14. Final acceptance sign-off

| Area | Owner | Required sign-off |
|---|---|---|
| Data consistency | Data/ML Lead | Yes |
| Analytics scenarios | AI/ML Lead | Yes |
| APIs | Backend Lead | Yes |
| UI workflow | Frontend Lead | Yes |
| Route validity | Backend/Operations | Yes |
| Demo readiness | QA + Project Manager | Yes |
