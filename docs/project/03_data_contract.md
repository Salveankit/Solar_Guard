# 03 — Canonical Data Contract

## 1. General conventions

- File encoding: UTF-8
- Delimiter: comma
- Timestamp format: ISO 8601 with timezone, preferably `YYYY-MM-DDTHH:MM:SS+05:30`
- Operational timezone: `Asia/Kolkata`
- Power: kW
- Energy: kWh
- Irradiance: W/m²
- Temperature: °C
- Distance: km
- Currency: INR
- Missing value: empty/null; never use zero to represent missing telemetry
- Boolean values: `true/false`
- Site keys are case-sensitive and must match `site_master.csv`

## 2. Dataset relationship

```text
site_master.site_id
  ├── telemetry.site_id
  ├── service_history.site_id
  └── fault_ground_truth.site_id

site_master.weather_zone
  ├── weather_history.weather_zone
  └── weather_forecast.weather_zone

technicians.technician_id
  └── service_history.technician_id
```

## 3. `site_master.csv`

| Column | Type | Required | Rule / allowed value | Example |
|---|---|---:|---|---|
| site_id | string | Yes | Unique; pattern `MH-###` | MH-142 |
| site_name | string | Yes | Synthetic, non-personal name | Baner Site 142 |
| capacity_kw | float | Yes | > 0 and <= 100 for POC | 5.0 |
| latitude | float | Yes | -90 to 90 | 18.5590 |
| longitude | float | Yes | -180 to 180 | 73.7868 |
| weather_zone | string | Yes | Must exist in weather data | PUNE_WEST |
| commissioning_date | date | Yes | Before analysis date | 2025-08-12 |
| inverter_vendor | string | Yes | Approved synthetic vendor list | Vendor-A |
| inverter_model | string | Yes | Non-empty | INV-5K |
| panel_capacity_w | integer | No | 250–800 | 550 |
| panel_count | integer | No | > 0 | 9 |
| tilt_degree | float | Yes | 0–60 for POC | 18 |
| azimuth_degree | float | Yes | 0–360 | 180 |
| site_efficiency_factor | float | Yes | 0.70–1.05 | 0.91 |
| tariff_per_kwh | float | Yes | >= 0 | 8.0 |
| service_region | string | Yes | Non-empty | Pune West |
| customer_type | enum | Yes | residential/commercial/society | residential |
| warranty_end_date | date | No | After commissioning | 2030-08-11 |
| cleaning_cost_inr | float | Yes | >= 0 | 750 |
| visit_cost_inr | float | Yes | >= 0 | 800 |

## 4. `telemetry.csv`

| Column | Type | Required | Validation | Example |
|---|---|---:|---|---|
| site_id | string | Yes | Must exist in site master | MH-142 |
| timestamp | datetime | Yes | 15-minute grid; unique per site | 2026-06-18T11:15:00+05:30 |
| generation_kwh | float/null | Yes | >= 0 when received | 0.72 |
| ac_power_kw | float/null | Yes | >= 0; soft check <= 1.2 × capacity | 3.10 |
| dc_voltage | float/null | No | 0–1,500 | 380.2 |
| dc_current | float/null | No | >= 0 | 8.5 |
| ac_voltage | float/null | No | 0–300 for single-phase demo | 229.4 |
| grid_frequency_hz | float/null | No | 40–60 | 49.9 |
| inverter_temperature_c | float/null | No | -20 to 100 | 48.0 |
| inverter_status | enum/null | Yes | RUNNING/OFFLINE/FAULT/STANDBY/UNKNOWN | RUNNING |
| fault_code | string/null | No | Vendor-style synthetic code | GRID_UNDERVOLTAGE |
| data_received | boolean | Yes | False means telemetry unavailable | true |
| source_quality_flag | enum | Yes | GOOD/SUSPECT/MISSING | GOOD |

### Telemetry consistency rules

- `(site_id, timestamp)` must be unique.
- If `data_received=false`, measured fields should be null, not fabricated zero.
- Positive night-time generation is rejected above a small tolerance.
- `generation_kwh` per 15 minutes should not materially exceed `capacity_kw × 0.25`.
- Zero generation with `data_received=true` is a real observation and may indicate outage/standby.

## 5. `weather_history.csv`

| Column | Type | Required | Validation | Example |
|---|---|---:|---|---|
| timestamp | datetime | Yes | 15-minute grid | 2026-06-18T11:15:00+05:30 |
| weather_zone | string | Yes | Composite unique with timestamp | PUNE_WEST |
| ghi_wm2 | float | Yes | 0–1,400 | 710 |
| dni_wm2 | float | No | 0–1,400 | 560 |
| dhi_wm2 | float | No | 0–1,000 | 150 |
| temperature_c | float | Yes | -10 to 60 | 32.1 |
| cloud_cover_pct | float | Yes | 0–100 | 20 |
| rainfall_mm | float | Yes | >= 0 | 0 |
| wind_speed_ms | float | Yes | 0–75 | 3.2 |
| weather_quality_flag | enum | Yes | GOOD/SUSPECT | GOOD |

## 6. `weather_forecast.csv`

Same weather structure as history, plus:

| Column | Type | Required | Rule |
|---|---|---:|---|
| forecast_generated_at | datetime | Yes | Before forecast timestamp |
| forecast_horizon_hours | integer | Yes | 1–168 |

Minimum forecast horizon for POC: 72 hours.

## 7. `service_history.csv`

| Column | Type | Required | Rule / example |
|---|---|---:|---|
| ticket_id | string | Yes | Unique; `TKT-####` |
| site_id | string | Yes | Valid site |
| reported_at | datetime | Yes | Valid timestamp |
| complaint_type | enum | Yes | LOW_GENERATION/OFFLINE/NO_DISPLAY/CLEANING/OTHER |
| complaint_severity | enum | Yes | LOW/MEDIUM/HIGH/CRITICAL |
| actual_fault | string | No | Synthetic technician-confirmed label |
| resolution | string | No | Synthetic resolution text |
| visit_cost_inr | float | No | >= 0 |
| technician_id | string | No | Valid technician |
| resolved_at | datetime | No | >= reported_at |
| remote_resolution | boolean | Yes | true/false |
| repeat_complaint | boolean | Yes | true/false |
| sla_due_at | datetime | Yes | >= reported_at |

## 8. `technicians.csv`

| Column | Type | Required | Rule / example |
|---|---|---:|---|
| technician_id | string | Yes | Unique; `TECH-##` |
| technician_name | string | Yes | Synthetic name |
| start_latitude | float | Yes | Valid latitude |
| start_longitude | float | Yes | Valid longitude |
| shift_start | time | Yes | `09:00` |
| shift_end | time | Yes | `18:00` |
| maximum_visits | integer | Yes | 1–8 |
| skill_set | string-list | Yes | `electrical;inverter;cleaning` |
| region | string | Yes | Service region |
| active | boolean | Yes | true |

## 9. `fault_ground_truth.csv`

**Security rule:** evaluation-only; not exposed through operational API or UI.

| Column | Type | Required | Rule |
|---|---|---:|---|
| incident_id | string | Yes | Unique; `INC-###` |
| site_id | string | Yes | Valid site |
| fault_type | enum | Yes | COMMUNICATION/SUDDEN_OUTAGE/GRADUAL_DEGRADATION/TIME_SPECIFIC/AMBIGUOUS |
| start_timestamp | datetime | Yes | Valid |
| end_timestamp | datetime | Yes | > start |
| severity | enum | Yes | LOW/MEDIUM/HIGH/CRITICAL |
| injected_loss_pct | float | Yes | 0–100 |
| expected_action | enum | Yes | MONITOR/REMOTE_CHECK/CLEANING/VISIT/COLLECT_DATA |
| expected_visit_required | boolean | Yes | true/false |
| notes | string | No | Injection explanation |

## 10. Derived analytical outputs

### `site_diagnostics`

- analysis_date
- site_id
- data_completeness_pct
- expected_energy_kwh
- actual_energy_kwh
- energy_loss_kwh
- performance_ratio
- probable_issue
- confidence_score
- confidence_label
- evidence_json
- recommended_action
- visit_required
- estimated_value_at_risk_inr
- estimated_recoverable_value_inr
- priority_score
- priority_label

### `service_jobs`

- job_id
- site_id
- job_type
- required_skill
- priority_score
- estimated_duration_min
- earliest_visit
- latest_visit
- selected_for_route

## 11. Reject versus warn policy

### Reject row/file

- missing primary key;
- invalid foreign key;
- unparseable required timestamp;
- negative energy/power;
- duplicate telemetry key;
- impossible latitude/longitude.

### Warn but retain

- unusually high power near capacity tolerance;
- suspicious temperature;
- missing optional electrical fields;
- weather value near physical limit;
- incomplete service-history resolution.
