# SolarGuard Synthetic Dataset

## Purpose

This package contains a deterministic, internally consistent synthetic rooftop-solar fleet designed for the SolarGuard POC.

It demonstrates:
- CSV ingestion and validation
- expected-generation modelling
- weather-normalised performance analysis
- anomaly and probable-cause reasoning
- energy-value prioritisation
- cleaning decisions
- technician routing

## Scenario

- Sites: 30
- Region: Pune and nearby areas
- Historical period: 2026-05-15T00:00:00+05:30 to 2026-06-13T23:45:00+05:30
- Resolution: 15 minutes
- Historical telemetry rows: 86,400
- Weather zones: 3
- Forecast horizon: 72 hours
- Technicians: 2
- Primary incidents: 10
- Ambiguous evaluation cases: 2
- Random seed: 42

## Files

1. `site_master.csv`
2. `telemetry.csv`
3. `weather_history.csv`
4. `weather_forecast.csv`
5. `service_history.csv`
6. `technicians.csv`
7. `fault_ground_truth.csv`
8. `scenario_validation_expected.csv`
9. `dataset_profile.csv`
10. `data_generation_summary.json`

## Important modelling rules

- Missing telemetry is represented by blank measurement fields and `data_received=false`.
- Missing telemetry is never replaced by zero.
- Weather is correlated within each zone.
- Sites in one weather zone share broad conditions but retain site-specific performance variation.
- Healthy output includes clipping, sensor bias, correlated noise, orientation effects, temperature effects, and benign missing intervals.
- Fault patterns are intentionally not perfectly separable.
- `fault_ground_truth.csv` is evaluation-only and must not be used as an inference feature.
- Synthetic data validates workflow feasibility, not field accuracy.

## Training guidance

Train the expected-generation model only on:
- received telemetry
- good or acceptable quality rows
- healthy intervals outside `fault_ground_truth.csv`

Use a time-based split, not random row splitting.

## Suggested first checks

- Row and foreign-key validation: `data_generation_summary.json`
- Fleet metadata: `site_master.csv`
- One sudden outage: `MH-107`
- One no-code outage: `MH-119`
- Cleaning candidate: `MH-105`
- Rain-deferred cleaning case: `MH-121`
- Morning shading-like pattern: `MH-109`
- Afternoon shading-like pattern: `MH-124`
- Unknown/insufficient evidence: `MH-115` and `MH-130`

## Disclosure

All customer, technician, equipment, service, weather, and fault data are simulated.
