# 09 - UI and Screen Specification

## 1. Product-design objective

The dashboard must look like an operations tool, not a presentation slide or generic analytics template. Every page should help answer:

> What requires attention, why, and what should the operations team do next?

The active implemented UI is the React/Vite application in `frontend/`. The Streamlit dashboard remains retained fallback POC code.

## 2. Global layout

### Header and shell

- SolarGuard logo/name.
- Search where relevant.
- latest refresh/analysis timestamp.
- refresh action.
- date/time context.
- primary navigation.

### Navigation

Implemented React routes:

1. `/` - Command Centre
2. `/fleet` - Fleet Sites
3. `/diagnostics` and `/sites/{site_id}` - Site Diagnostics
4. `/incidents` - Incidents
5. `/service-queue` - Service Queue
6. `/technician-plan` - Technician Plan
7. `/reports` - Reports

### Global design rules

- Compact but readable spacing.
- Cards must not leave large dead space when neighboring content has meaningful data.
- Severity shown using icon + text + colour, never colour alone.
- Units visible beside values.
- No dead navigation items or placeholder controls.
- No editable controls that do nothing.
- No raw JSON, stack traces, or backend-engineering implementation notes on primary screens.
- No claim of live weather, live inverter feeds, live traffic, or guaranteed savings.
- Charts and maps must clearly represent backend outputs from the current synthetic demo dataset.

## 3. Command Centre

### Purpose

Provide the morning fleet decision summary.

### Required content

- Hero command-centre summary.
- Site and weather context based on stored/demo data.
- Fleet KPI strip.
- Important fleet alert/notice when evidence is missing or insufficient.
- Expected vs actual fleet generation trend.
- Incident distribution.
- Today's operations summary.
- Service priority queue preview.
- Top priority evidence.
- Technician route preview.

### Layout guidance

- Expected vs actual generation should receive enough width and height to read trends.
- Incident distribution and today's operations should remain compact summaries.
- Service queue preview should use horizontal room for table readability.
- Top priority evidence should remain concise and aligned with route/queue content.
- Route preview should show a real Leaflet/OpenStreetMap context when tiles are available, with textual fallback.

## 4. Fleet Sites

### Purpose

Help the user scan all sites and open the correct diagnostic context quickly.

### Required content

- Fleet summary metrics.
- Site list/table with status, probable issue, priority, and action context.
- Filtering or search suitable for 30 synthetic sites.
- Navigation into site diagnostics.

### Rules

- Status values must match backend diagnostics.
- Unknown/insufficient-evidence sites must stay visible.
- The page must avoid presenting unavailable live telemetry as if it is current real-world data.

## 5. Site Diagnostics

### Purpose

Explain one site's performance and recommended action.

### Header panel

- site ID/name;
- region;
- status badge;
- coverage/data quality;
- latest analysis timestamp;
- probable issue, confidence, energy loss/value, recommended action.

### Performance chart

Required series:

- expected generation;
- actual generation;
- irradiance on secondary axis or aligned panel;
- highlighted anomaly windows when available.

Avoid overcrowding. Default to a meaningful current diagnostic range and keep legends, axes, and units readable.

### Diagnostic summary

Display:

- probable issue;
- confidence label and score;
- evidence;
- recommended next action;
- field visit required when applicable.

### Supporting sections

- diagnostic evidence;
- site and analysis context;
- event and diagnostic history;
- recommended next actions.

### Layout guidance

- The expected vs actual chart may expand vertically when the lower left column has available space.
- Event history should align visually with recommended next actions where possible.
- Remove redundant service decision snapshots if they repeat existing decision data without adding user value.

## 6. Incidents

### Purpose

Show operational incidents without exposing internal/debug language.

### Required content

- Incident summary.
- Incident list or table.
- Distribution by probable issue/status.
- Link into diagnostics or service queue.

### Rules

- Use "probable issue", "evidence", and "recommended action".
- Do not show backend phrases, internal route state, raw analysis service names, or debug notes.
- Unknown/insufficient-evidence incidents must remain visible.

## 7. Service Queue

### Purpose

Allow the operations manager to review, filter, and act on ranked service decisions.

### Required content

- Hero summary without duplicating the same KPI strip immediately below unless the second strip adds new information.
- Queue KPI strip.
- Service decision queue table.
- Queue distribution.
- Selected decision details.
- Priority breakdown.

### Layout guidance

- The service decision queue is the primary content and should receive the most horizontal space.
- If vertical space is available, increase visible rows instead of paginating at five rows by default.
- Supporting cards such as distribution, selected decision, and priority breakdown should be stacked or moved below when they constrain table readability.
- Small KPI/detail cards can be placed horizontally at the bottom when that improves the table area.

### Table columns

- priority label/score;
- site;
- probable issue;
- confidence;
- persistence;
- energy value at risk;
- complaint status;
- recommended action;
- visit required.

### Rules

- Default sort by priority score descending.
- Unknown incidents remain visible and are not silently dropped.
- Values must match Site Diagnostics and export exactly.
- Pagination should not create unnecessary empty space on common laptop screens.

## 8. Technician Plan

### Purpose

Present the actionable next-day field-service plan.

### Required content

- plan date;
- technicians used;
- jobs assigned/unassigned;
- optimised distance;
- distance saved;
- expected recoverable energy/value;
- technician route cards;
- route map;
- unassigned job reasons;
- daily O&M export.

### Map

- Use Leaflet/OpenStreetMap tiles in the React UI.
- Show service hub marker.
- Show numbered route stops.
- Distinguish technician routes.
- Keep textual route details usable if tiles fail.
- Do not call live traffic or paid map APIs.

## 9. Reports

### Purpose

Provide report preview/download for the daily O&M plan.

### Required content

- latest route/report context;
- CSV download action;
- report rows consistent with visible route plan and service queue.

## 10. UI-to-API mapping

| UI need | API |
|---|---|
| Health | GET `/health` |
| Load demo | POST `/api/data/load-demo` |
| Run analysis | POST `/api/analysis/run` |
| Run expected generation only | POST `/api/analysis/run-expected-generation` |
| Command KPIs | GET `/api/fleet/summary` |
| Fleet trend | GET `/api/fleet/timeseries` |
| Site list | GET `/api/sites` |
| Site details | GET `/api/sites/{site_id}` |
| Site diagnosis | GET `/api/sites/{site_id}/diagnostics` |
| Queue | GET `/api/service-queue` |
| Route optimise | POST `/api/routes/optimize` |
| Latest route | GET `/api/routes/latest` |
| Download CSV | GET `/api/reports/daily-plan` |

## 11. Copy guidelines

Use:

- `Probable issue`
- `Evidence`
- `Recommended action`
- `Energy value at risk`
- `Estimated recoverable value`
- `Insufficient evidence`
- `Latest analysis`
- `Synthetic demo data`

Avoid:

- `AI proved`
- `Confirmed fault`
- `Guaranteed savings`
- `Backend analysis`
- `Backend rows`
- `Frontend recalculation`
- `Revenue loss` for all customer types
- unexplained `AI score`

## 12. Responsive priority

Desktop/laptop is primary. Basic tablet compatibility is useful. Mobile optimisation is outside the current POC scope.

## 13. UI acceptance checklist

- Active React routes load without raw exceptions.
- No dead controls.
- No inconsistent values.
- No page recalculates backend logic.
- No backend-engineering text leakage in the user-facing UI.
- Charts have labels, units, and meaningful default ranges.
- Tables handle zero, five, and many rows without wasting available page space.
- Synthetic-data disclosure is visible but unobtrusive.
- One-click navigation from fleet priority to site evidence to route assignment remains possible.
