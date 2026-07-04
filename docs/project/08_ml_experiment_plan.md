# 08 — ML Experiment Plan

## 1. ML objective

Estimate expected 15-minute solar generation under healthy conditions so that residual performance can be analysed. The ML model is not responsible for final fault confirmation or technician routing.

## 2. Modelling strategy

Use two levels:

1. **Deterministic/domain baseline** — capacity, irradiance, interval duration, temperature/orientation efficiency.
2. **XGBoost regression model** — learns site/weather/time corrections.

Implementation may proceed baseline-first to unblock anomaly and decision logic, but XGBoost remains mandatory for the first demo's expected-generation workstream. If the XGBoost artifact is missing or does not improve sufficiently over the baseline, the POC must still remain functional using the baseline and must disclose that fallback state.

## 3. Target

```text
generation_kwh_per_15_min
```

Training target must come only from known healthy, received telemetry.

## 4. Candidate features

### Time

- hour sine/cosine;
- day-of-year sine/cosine;
- weekday/weekend only if justified;
- solar zenith/elevation from pvlib.

### Weather

- GHI;
- DNI/DHI if available;
- ambient temperature;
- cloud cover;
- rainfall indicator;
- wind speed.

### Site

- capacity;
- tilt;
- azimuth;
- site efficiency factor;
- customer/site class;
- weather zone or site ID encoding where controlled.

### Derived

- clear-sky index;
- temperature-adjusted irradiance;
- expected clipping flag;
- lagged healthy performance only if leakage is prevented.

## 5. Exclusions

Do not train on:

- injected fault intervals;
- missing telemetry;
- invalid/suspect readings;
- target-derived future information;
- hidden ground-truth category;
- service resolution labels.

## 6. Data split

Use chronological split:

- first 70% of dates: train;
- next 15%: validation;
- last 15%: test.

Where possible, include a secondary holdout by site to discuss cross-site generalisation, but this is optional for the two-day POC.

Random row splitting is prohibited because adjacent time points can leak weather and generation patterns.

## 7. Baseline model

Conceptual baseline:

```text
expected_energy =
  capacity_kw
  × normalised_irradiance
  × interval_hours
  × orientation_factor
  × temperature_factor
  × site_efficiency
```

Evaluate baseline before XGBoost.

## 8. XGBoost model

Suggested initial parameters:

```python
{
    "n_estimators": 300,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.85,
    "colsample_bytree": 0.85,
    "objective": "reg:squarederror",
    "random_state": 42,
    "n_jobs": -1
}
```

Use early stopping if validation integration is straightforward. Do not spend the POC timeline on large hyperparameter searches.

## 9. Metrics

Report:

- MAE in kWh/interval;
- RMSE in kWh/interval;
- normalised MAE relative to mean daytime generation;
- daily aggregated MAE;
- residual plots for healthy validation data.

The metrics are engineering sanity checks on synthetic data, not field-accuracy claims.

## 10. Model acceptance rule

The XGBoost model is accepted when:

- it beats the deterministic baseline on validation/test MAE by a meaningful margin, suggested >= 10%;
- daytime residuals are not obviously biased by capacity or weather zone;
- predictions are non-negative after clipping;
- prediction does not exceed a configured plausible capacity bound;
- model output is deterministic with seed 42.

If not accepted, use baseline for operational demo calculations and present the XGBoost result as an experiment rather than the active expected-generation path.

## 11. Inference post-processing

- Clip predictions below zero to zero.
- Apply night-time zero based on solar/irradiance gate.
- Cap implausible interval energy at configured site-capacity bound.
- Store model and feature-version metadata.

## 12. Anomaly methodology

Primary POC method: residual and performance-ratio rules.

```text
residual = actual - expected
performance_ratio = actual / expected
```

Use persistence and daylight gates.

Optional exploratory method: Isolation Forest on multivariate residual features. It must not replace the explainable primary method unless it clearly improves scenario validation and remains interpretable.

## 13. Probable-cause methodology

Use a hybrid rule/evidence engine for the POC. Do not train a supervised fault classifier on synthetic labels and present it as real fault intelligence.

Possible features for evidence:

- data completeness;
- abruptness of drop;
- residual persistence;
- recurring hour-window pattern;
- DC/AC availability;
- inverter status/fault code;
- weather consistency;
- multi-day trend.

## 14. Confidence methodology

Confidence is a weighted evidence score, not a calibrated posterior probability. Document components and thresholds in `05_business_rules.md`.

## 15. Experiment outputs

- `models/expected_generation_model.joblib`
- `models/feature_schema.json`
- `models/model_metrics.json`
- `reports/model_evaluation.md`
- `data/processed/expected_vs_actual.parquet` or CSV

## 16. Reproducibility

- random seed 42 across NumPy, scikit-learn, and XGBoost;
- package versions locked in `pyproject.toml`/lock file;
- training script accepts configuration path;
- model artifact stores metadata;
- training data query/filter is logged.

## 17. Common failure modes

| Failure | Prevention |
|---|---|
| Unrealistically perfect score | Hidden generator variables, noise, time split |
| Fault leakage into training | Exclude ground-truth incident windows |
| Night-time false residuals | Daylight eligibility gate |
| Cloudy-day false alarms | Weather-aware expected output |
| Site-size bias | Normalised metrics and capacity features |
| Synthetic accuracy overclaim | Scenario validation and explicit disclaimer |

## 18. Interview Smart Answer

The ML component estimates what a healthy site should have generated under the observed weather and configuration. We compare that baseline with actual output and use persistent residual patterns as evidence. We deliberately keep the final fault and dispatch decisions explainable and rule-driven in the POC because synthetic labels cannot justify a production fault classifier.
