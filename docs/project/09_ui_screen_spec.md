# 09 — UI and Screen Specification

## 1. Product-design objective

The dashboard must look like an operations tool, not a presentation slide or generic analytics template. Every page should help answer:

> What requires attention, why, and what should the operations team do next?

## 2. Global layout

### Header

- SolarGuard logo/name
- `POC — Simulated Data` badge
- latest analysis timestamp
- dataset/model status

### Navigation

1. Command Centre
2. Site Diagnostics
3. Service Queue
4. Technician Plan

### Global design rules

- Compact but readable spacing.
- Neutral background and clear hierarchy.
- Severity shown using icon + text + colour, never colour alone.
- Units visible beside values.
- No dead navigation items or placeholder controls.
- No editable controls that do nothing.
- No raw JSON on primary screens.

## 3. Screen 1 — Daily Operations Command Centre

### Purpose

Provide the morning fleet decision summary.

### Top KPI row

- Monitored sites
- Healthy
- Require attention
- Remote checks
- Field visits recommended
- Energy value at risk

### Primary action

`Generate Tomorrow's O&M Plan`

Behavior:

- disabled until analysis exists;
- runs/refreshes route optimisation;
- shows success summary and links to Technician Plan.

### Main content

#### A. Fleet attention summary

Stacked or horizontal status visual:

- healthy;
- communication;
- underperformance;
- unknown.

#### B. Top priorities table

Columns:

- rank;
- site;
- probable issue;
- priority;
- value at risk;
- recommended action.

Maximum 5–8 rows on overview.

#### C. Expected vs actual fleet trend

Daily or hourly aggregate, clearly labelled.

#### D. Action split

- monitor;
- remote check;
- field visit;
- cleaning;
- collect more data.

### Empty/loading/error states

- No analysis: show `Load demo data` and `Run analysis` steps.
- Analysis running: progress indicator with current phase.
- No incidents: positive healthy-fleet state, not empty chart.
- API failure: concise retry guidance.

## 4. Screen 2 — Site Diagnostics

### Purpose

Explain one site's performance and recommended action.

### Controls

- site selector/search;
- analysis date/range;
- quick navigation to previous/next priority site.

### Header panel

- site ID/name;
- capacity;
- service region;
- status badge;
- priority badge;
- data completeness.

### Performance chart

Required series:

- expected generation/power;
- actual generation/power;
- irradiance on secondary axis or aligned panel;
- highlighted anomaly windows.

Avoid overcrowding. Default to meaningful 1–3 day window with option for 30-day trend.

### Diagnostic card

Display:

- probable issue;
- confidence label and score;
- evidence bullets;
- limitations;
- recommended first action;
- field visit required: yes/no.

### Impact card

- expected energy;
- actual energy;
- energy loss;
- value at risk;
- estimated recoverable value.

### Priority breakdown

Show six score components and total. A small horizontal breakdown is preferred over a gauge.

### Cleaning panel

Only show for applicable sites:

- 7-day projected loss;
- cleaning cost;
- rain expectation;
- decision and reason.

## 5. Screen 3 — Service Decision Queue

### Purpose

Allow operations manager to review and filter all incidents.

### Summary strip

- total incidents;
- critical/high;
- remote actions;
- field jobs;
- unknown/insufficient data.

### Filters

- priority;
- probable issue;
- action type;
- visit required;
- service region;
- confidence;
- complaint status.

### Table columns

- rank;
- priority label/score;
- site;
- probable issue;
- confidence;
- persistence;
- energy loss;
- value at risk;
- complaint age/SLA;
- recommended action;
- visit required.

### Row interaction

Selecting a row opens the site diagnostic page or an in-page details drawer.

### Rules

- Default sort by priority score descending.
- Unknown incidents remain visible and are not silently dropped.
- Values must match Site Diagnostics and export exactly.

## 6. Screen 4 — Technician Plan

### Purpose

Present the actionable next-day field-service plan.

### Header summary

- plan date;
- technicians used;
- jobs assigned/unassigned;
- optimised distance;
- distance saved;
- expected recoverable energy/value.

### Technician route cards

For each technician:

- name and skills;
- shift;
- total route distance;
- total estimated time;
- ordered stops.

Each stop displays:

- sequence;
- site ID;
- issue;
- priority;
- recommended task;
- estimated job duration;
- required skill/part note.

### Map

- service hub marker;
- numbered route stops;
- separate visual distinction per technician;
- textual route remains usable if tiles fail.

### Unassigned jobs

Show reason:

- no matching skill;
- insufficient shift capacity;
- invalid coordinates;
- lower priority than selected jobs.

### Export

Button: `Download Daily O&M Plan`

## 7. UI-to-API mapping

| UI need | API |
|---|---|
| Load demo | POST `/api/data/load-demo` |
| Run analysis | POST `/api/analysis/run` |
| Command KPIs | GET `/api/fleet/summary` |
| Site list | GET `/api/sites` |
| Site diagnosis | GET `/api/sites/{id}/diagnostics` |
| Queue | GET `/api/service-queue` |
| Cleaning | GET `/api/sites/{id}/cleaning-decision` |
| Route | POST `/api/routes/optimize` and GET latest |
| Download | GET `/api/reports/daily-plan` |

## 8. Copy guidelines

Use:

- `Probable issue`
- `Evidence`
- `Recommended action`
- `Energy value at risk`
- `Estimated recoverable value`
- `Insufficient evidence`

Avoid:

- `AI proved`
- `Confirmed fault`
- `Guaranteed savings`
- `Revenue loss` for all customer types
- unexplained `AI score`

## 9. Responsive priority

Desktop/laptop is primary. Basic tablet compatibility is useful. Mobile optimisation is out of scope.

## 10. UI acceptance checklist

- Four pages only.
- No dead controls.
- No inconsistent values.
- No page recalculates backend logic.
- Charts have labels, units, and meaningful default ranges.
- Tables handle zero and many rows.
- Synthetic-data disclosure is visible but unobtrusive.
- One-click navigation from fleet priority to site evidence to route assignment.
