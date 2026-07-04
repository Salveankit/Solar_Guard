# 05 — Business Rules and Decision Logic

## 1. Design principles

1. Data-quality problems are handled before performance diagnosis.
2. Every user-facing diagnosis is probable, not confirmed.
3. A visit is recommended only after remote-first and economic checks.
4. Scores must be explainable through their component values.
5. Unknown/insufficient evidence is a valid and required outcome.
6. All thresholds live in configuration.

## 2. Core derived measures

### Expected and actual energy

```text
energy_loss_kwh = max(expected_energy_kwh - actual_energy_kwh, 0)
performance_ratio = actual_energy_kwh / expected_energy_kwh
```

If expected energy is below the configured minimum, the interval is not eligible for underperformance diagnosis.

### Energy value at risk

```text
value_at_risk_inr = energy_loss_kwh × tariff_per_kwh
```

### Recoverable value

```text
recoverable_value_inr =
  value_at_risk_inr
  × diagnostic_confidence
  × recoverability_factor
```

Recoverability factors are configurable by issue type.

## 3. Data-quality rules

### DQ-01 — Data completeness

```text
data_completeness = received_intervals / expected_intervals
```

Suggested labels:

- Good: >= 95%
- Partial: 80–94.99%
- Insufficient: < 80%

### DQ-02 — Communication incident

Create a communication incident when either:

- `data_received=false` for configured consecutive intervals; or
- site heartbeat is older than configured stale threshold.

Communication diagnosis takes precedence over production diagnosis for missing periods.

### DQ-03 — Invalid readings

Rows with impossible physical values are excluded from analysis and contribute to data-quality warnings.

## 4. Daylight eligibility

An interval is eligible for performance analysis only when:

- irradiance >= configured minimum; and
- expected power/energy >= configured minimum fraction of site capacity; and
- data quality is sufficient.

Initial configuration:

- minimum irradiance: 200 W/m²;
- minimum expected power: 20% of site capacity.

## 5. Anomaly rules

### A-01 — Underperformance interval

```text
performance_ratio < 0.70
```

### A-02 — Sudden-outage interval

```text
performance_ratio <= 0.05
AND expected output is eligible
```

### A-03 — Persistence

Incident creation requires at least 4 consecutive eligible abnormal intervals unless a strong inverter fault code is present.

### A-04 — Cloud protection

Low actual output is not a fault when expected output is also low due to low irradiance or heavy weather conditions.

## 6. Probable-cause rules

### PC-01 — Communication/data failure

Evidence may include:

- missing intervals;
- stale heartbeat;
- `data_received=false`;
- no usable electrical telemetry.

Default action: `REMOTE_CHECK`.

### PC-02 — Sudden production outage

Candidate when:

- high expected output;
- near-zero actual output;
- abrupt drop;
- persistence met;
- optional grid/inverter fault code.

Confidence increases when DC-side measurements remain available or a matching fault code exists.

Default action: `REMOTE_DIAGNOSTIC`, then `VISIT` if unresolved.

### PC-03 — Gradual persistent underperformance

Candidate when:

- daily clear-sky performance ratio declines across multiple days;
- no abrupt outage;
- no dominant communication problem;
- daytime profile remains broadly similar.

Label: `SOILING_OR_GRADUAL_DEGRADATION`.

Default action: cleaning economics + inspection recommendation.

### PC-04 — Time-specific underperformance

Candidate when:

- abnormal residual repeats in a similar hour window on multiple days;
- other daylight hours are materially healthier;
- weather does not explain the repeated localised loss.

Label: `TIME_DEPENDENT_SHADING_OR_OBSTRUCTION`.

Default action: site inspection/photo review.

### PC-05 — Unknown/insufficient evidence

Use when:

- data completeness is insufficient;
- multiple categories have similar support;
- incident is too short or weak;
- weather and telemetry conflict;
- no rule meets minimum confidence.

Default action: `COLLECT_MORE_DATA` or `REMOTE_INSPECTION`.

## 7. Confidence score

Confidence is not model probability unless explicitly calibrated. It is an evidence score for the POC.

Suggested component structure:

- pattern strength: 0–35;
- persistence: 0–25;
- supporting electrical/status evidence: 0–20;
- weather consistency: 0–10;
- data completeness: 0–10.

Labels:

- Low: < 50
- Medium: 50–74
- High: 75–89
- Very high: >= 90

UI must call it `confidence score`, not `accuracy`.

## 8. Cleaning economics

### Inputs

- 7-day projected recoverable energy;
- tariff/value per kWh;
- diagnostic confidence;
- cleaning cost;
- safety margin;
- forecast rainfall.

### Rule

```text
adjusted_7_day_value =
  projected_7_day_energy_loss
  × tariff
  × confidence
  × recoverability_factor

cleaning_justified =
  adjusted_7_day_value > cleaning_cost × safety_margin
  AND significant_rain_not_expected
```

### Outcomes

- `SCHEDULE_CLEANING`
- `DEFER_DUE_TO_RAIN`
- `MONITOR_NOT_ECONOMIC`
- `INSUFFICIENT_EVIDENCE`

## 9. Field-visit decision

### Recommend visit when

- issue requires physical inspection/repair; and
- remote action is completed, unsuitable, or unlikely to resolve it; and
- priority/impact exceeds configured threshold; and
- data confidence is adequate.

### Do not immediately visit when

- pure communication failure;
- low-confidence ambiguous incident;
- low economic impact without SLA/complaint urgency;
- cleaning cost exceeds projected recoverable value;
- near-term rain makes cleaning unnecessary.

## 10. Priority scoring

Maximum score: 100.

| Component | Max points | Example calculation |
|---|---:|---|
| Recoverable energy impact | 30 | normalised against fleet daily max/cap |
| Persistence | 20 | duration and repeat occurrence |
| Diagnostic confidence | 15 | scaled confidence |
| Complaint urgency | 15 | complaint severity and age |
| SLA/warranty risk | 10 | time to SLA breach/warranty obligation |
| Route-clustering benefit | 10 | proximity to other high-value jobs |

### Priority labels

- Low: 0–39
- Medium: 40–69
- High: 70–84
- Critical: 85–100

### Override rules

Critical fault/alarm or imminent SLA breach may set a minimum priority floor. All overrides must be recorded in the score breakdown.

## 11. Route eligibility

A job is eligible for routing only when:

- `visit_required=true`;
- required skill matches at least one technician;
- visit window overlaps technician shift;
- site coordinates are valid;
- job has not already been resolved remotely.

## 12. Route optimisation objective

Primary objective:

- maximise total serviced priority/recoverable impact;
- minimise distance;
- respect technician capacity and shift.

For the POC, use a weighted cost that penalises unserved high-priority jobs more heavily than additional distance.

## 13. Configuration example

```yaml
analysis:
  minimum_irradiance_wm2: 200
  minimum_expected_capacity_ratio: 0.20
  underperformance_ratio: 0.70
  outage_ratio: 0.05
  persistence_intervals: 4
  minimum_data_completeness: 0.80

business:
  default_energy_value_per_kwh: 8.0
  default_visit_cost_inr: 800
  default_cleaning_cost_inr: 750
  cleaning_safety_margin: 1.20
  significant_rain_mm: 2.0

routing:
  maximum_visits_per_technician: 4
  average_speed_kmph: 30
  default_job_duration_min: 60
```

## 14. Audit fields

Every diagnosis should store:

- analysis timestamp;
- configuration version;
- model version;
- rules triggered;
- evidence values;
- final action and reason;
- any override applied.
