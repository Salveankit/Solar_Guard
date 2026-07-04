# 04 — Synthetic Data Generation Specification

## 1. Objective

Generate a deterministic, internally consistent rooftop-solar fleet that is realistic enough to demonstrate data engineering, expected-generation modelling, anomaly detection, probable-cause reasoning, financial prioritisation, and routing.

The generator must not produce perfectly separable textbook faults or allow the model to simply reverse the exact generation equation.

## 2. Fixed scenario

- 30 sites around Pune
- 30 historical days
- 15-minute interval
- 3 weather zones: Pune West, Pune Central, Pune East
- 2 technicians
- 10 primary incidents
- Optional 1–2 ambiguous low-confidence patterns
- Fixed random seed: `42`

## 3. Site generation

### Site attributes

Sample from controlled distributions:

- capacity: 3, 5, 7.5, 10, 15, and 20 kW;
- customer type: mostly residential, with a few society/commercial sites;
- tilt: 10–25 degrees;
- azimuth: 150–220 degrees;
- site efficiency: 0.82–0.98;
- commissioning age: 1 month to 4 years;
- coordinates: realistic but synthetic points around Pune service regions;
- inverter vendors: `Vendor-A`, `Vendor-B`, `Vendor-C`.

### Site variability

Include:

- persistent site efficiency differences;
- minor sensor calibration offsets;
- inverter clipping near rated power;
- small day-to-day performance variation;
- random but bounded measurement noise.

## 4. Weather generation

For each weather zone and timestamp:

1. Generate daylight/solar-position features using `pvlib` or a stable clear-sky approximation.
2. Apply daily cloud regimes: clear, partly cloudy, overcast, rainy.
3. Add correlated cloud transitions rather than independent random values per row.
4. Calculate GHI reduction based on cloud regime.
5. Generate temperature using diurnal curve plus weather effect.
6. Generate rainfall events that align with high cloud cover.
7. Generate wind with bounded variation.

### Rules

- Night irradiance must be zero or near zero.
- Rainfall should not occur with implausibly clear conditions.
- Sites in the same weather zone share the broad weather pattern.
- Weather should not be identical across zones.

## 5. Healthy generation logic

Use a physics-aware baseline plus hidden variability.

Conceptual relationship:

```text
clear_sky_or_weather_irradiance
× site_capacity
× orientation_factor
× temperature_efficiency
× site_efficiency
× interval_hours
= latent healthy energy
```

Then apply:

- inverter clipping;
- autocorrelated noise;
- sensor bias;
- small unobserved site-loss term;
- occasional benign communication gaps outside primary incidents.

The ML model must not receive every hidden generator parameter. This prevents unrealistically perfect prediction.

## 6. Electrical telemetry approximation

For healthy intervals:

- `ac_power_kw ≈ generation_kwh / 0.25`;
- `dc_power` slightly above AC power due to inverter efficiency;
- choose plausible DC voltage and derive current;
- AC voltage varies around nominal grid voltage;
- inverter temperature increases with ambient temperature and power;
- status is `RUNNING` during producing daylight intervals and `STANDBY` at night.

These values are demo approximations, not equipment-certification data.

## 7. Incident injection catalogue

### 7.1 Communication/data failure — 3 incidents

**Pattern**

- Remove or null consecutive telemetry intervals.
- Set `data_received=false` and `source_quality_flag=MISSING`.
- Do not set actual power to zero as a substitute.

**Durations**

- one short incident: 1–2 hours;
- one long incident: 6–12 hours;
- one multi-day intermittent incident.

**Expected action**

Remote connectivity/data-logger check; no immediate physical visit unless repeated or SLA-critical.

### 7.2 Sudden production outage — 2 incidents

**Pattern**

- Occur during meaningful irradiance.
- Abruptly reduce AC power and generation to 0–5% of healthy output.
- Optionally preserve DC voltage for grid/inverter-side evidence.
- Add vendor-style fault code to one incident; leave the other without explicit code.

**Expected action**

Remote inverter/grid diagnostic followed by field visit if unresolved.

### 7.3 Gradual persistent underperformance — 3 incidents

**Pattern**

- Apply increasing loss over several days, e.g. 5% to 25–40%.
- Maintain broad daytime shape.
- Avoid explicit alarm codes.
- Include one case with near-term rain to produce a deferred-cleaning recommendation.

**Expected action**

Investigate soiling/vegetation/degradation; apply cleaning economics.

### 7.4 Time-specific underperformance — 2 incidents

**Pattern**

- Repeat similar loss in a fixed daily window, e.g. 09:00–11:00 or 15:00–17:00.
- Keep rest of day near normal.
- Use 25–50% reduction in the affected window.

**Expected action**

Inspect for recurring shade or obstruction.

### 7.5 Ambiguous cases — optional

Examples:

- low completeness plus mild underperformance;
- one-day decline with mixed weather;
- conflicting electrical signals.

**Expected action**

Unknown/insufficient evidence; collect more telemetry.

## 8. Service-history generation

Create 30–50 synthetic historical tickets with:

- realistic complaint mix;
- remote and physical resolutions;
- visit costs;
- SLA deadlines;
- repeat-complaint flags;
- technician assignment.

At least some tickets should align with injected incidents, but historical tickets must not directly reveal every current ground-truth event.

## 9. Technician generation

Two technicians:

- Technician 1: inverter/electrical skill;
- Technician 2: cleaning/electrical skill;
- one shared Pune service hub or individual start coordinates;
- 09:00–18:00 shifts;
- maximum 4 visits each;
- job durations between 30 and 120 minutes based on issue type.

## 10. Training and evaluation separation

- Train expected-generation model only on known healthy intervals.
- Exclude injected incident periods.
- Exclude missing telemetry.
- Maintain time-based train/validation/test split.
- Keep `fault_ground_truth.csv` outside UI and inference feature access.

## 11. Output files

The generator must create:

1. `site_master.csv`
2. `telemetry.csv`
3. `weather_history.csv`
4. `weather_forecast.csv`
5. `service_history.csv`
6. `technicians.csv`
7. `fault_ground_truth.csv`

Optional derived validation files:

- `data_generation_summary.json`
- `scenario_validation_expected.csv`

## 12. Generator quality checks

- Exact row count and date coverage documented.
- All foreign keys valid.
- No duplicate telemetry keys.
- Missing-data incidents remain null/missing.
- Healthy night generation is zero.
- Daily generation roughly scales with site capacity and weather.
- Cloudy days reduce expected and actual healthy output together.
- Every ground-truth incident visibly changes the appropriate telemetry pattern.
- Fixed seed reproduces identical files.

## 13. Disclosure

All customer, equipment, service, weather, and technician data in the POC are simulated. Synthetic outputs demonstrate workflow feasibility and team capability, not field-validated model accuracy.
