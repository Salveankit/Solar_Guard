# 07 — FastAPI Contract

## 1. General API conventions

- Base path: `/api`
- Content type: `application/json` except CSV upload/download
- Timestamps: ISO 8601 with timezone
- IDs are strings
- Confidence returned from 0.0 to 1.0 plus label
- Monetary values in INR
- Version path is optional for POC; include `api_version` in health response

## 2. Standard error response

```json
{
  "error": {
    "code": "DATA_VALIDATION_FAILED",
    "message": "telemetry.csv contains invalid rows",
    "details": [
      {
        "row": 118,
        "field": "timestamp",
        "reason": "Unparseable ISO-8601 value"
      }
    ],
    "request_id": "req_01J..."
  }
}
```

Common codes:

- `DATA_VALIDATION_FAILED`
- `RESOURCE_NOT_FOUND`
- `ANALYSIS_NOT_READY`
- `MODEL_UNAVAILABLE`
- `ROUTE_INFEASIBLE`
- `INTERNAL_ERROR`

## 3. Health

### `GET /health`

**200 response**

```json
{
  "status": "ok",
  "api_version": "1.0.0",
  "database": "ready",
  "model": "ready",
  "configuration_version": "poc-v1"
}
```

## 4. Data operations

### `POST /api/data/load-demo`

Loads pre-generated demo files.

**Request**

```json
{
  "reset_existing": true
}
```

**200 response**

```json
{
  "status": "loaded",
  "datasets": {
    "sites": 30,
    "telemetry": 86400,
    "weather_history": 8640,
    "weather_forecast": 864,
    "service_history": 40,
    "technicians": 2
  },
  "validation_warnings": []
}
```

### `POST /api/data/upload`

Multipart upload of one or more canonical files.

This endpoint is deferred for the first POC sprint. The first demo path uses `/api/data/load-demo`; when upload is implemented later, uploaded files must be validated with the same canonical data contract as bundled demo files.

**Response**

```json
{
  "status": "validated",
  "accepted_files": ["site_master.csv", "telemetry.csv"],
  "row_counts": {"site_master.csv": 30, "telemetry.csv": 86400},
  "warnings": []
}
```

## 5. Analysis

### `POST /api/analysis/run`

**Request**

```json
{
  "analysis_date": "2026-07-03",
  "force_recompute": false
}
```

**200 response**

```json
{
  "analysis_run_id": "RUN-20260703-001",
  "status": "completed",
  "sites_analysed": 30,
  "incidents_created": 10,
  "duration_ms": 12450,
  "model_version": "expected-xgb-v1",
  "configuration_version": "poc-v1"
}
```

### `GET /api/analysis/runs/latest`

Returns latest completed run metadata.

## 6. Fleet

### `GET /api/fleet/summary`

Optional query: `analysis_run_id`.

**200 response**

```json
{
  "analysis_run_id": "RUN-20260703-001",
  "monitored_sites": 30,
  "healthy_sites": 20,
  "communication_issues": 3,
  "underperforming_sites": 6,
  "unknown_sites": 1,
  "remote_check_candidates": 3,
  "field_visits_recommended": 4,
  "daily_energy_loss_kwh": 38.5,
  "energy_value_at_risk_inr": 308.0,
  "estimated_recoverable_energy_kwh": 25.4,
  "top_priority_site_id": "MH-142"
}
```

## 7. Sites

### `GET /api/sites`

Query parameters:

- `status`
- `service_region`
- `customer_type`
- `limit`
- `offset`

**Response item**

```json
{
  "site_id": "MH-142",
  "site_name": "Baner Site 142",
  "capacity_kw": 5.0,
  "service_region": "Pune West",
  "status": "underperforming",
  "priority_label": "High"
}
```

### `GET /api/sites/{site_id}`

Returns site master and current summary.

### `GET /api/sites/{site_id}/telemetry`

Query parameters: `start`, `end`, `granularity`.

### `GET /api/sites/{site_id}/diagnostics`

**200 response**

```json
{
  "analysis_run_id": "RUN-20260703-001",
  "site_id": "MH-142",
  "analysis_date": "2026-07-03",
  "data_quality": {
    "completeness_pct": 98.9,
    "label": "Good",
    "warnings": []
  },
  "performance": {
    "expected_energy_kwh": 23.4,
    "actual_energy_kwh": 14.2,
    "energy_loss_kwh": 9.2,
    "performance_ratio": 0.607
  },
  "diagnosis": {
    "probable_issue": "SUDDEN_PRODUCTION_OUTAGE",
    "display_label": "Possible inverter or grid-side interruption",
    "confidence": 0.82,
    "confidence_label": "High",
    "evidence": [
      "Expected output remained high during the incident",
      "Actual output stayed near zero for six consecutive intervals",
      "Irradiance remained above 600 W/m²"
    ],
    "limitations": [
      "Component-level failure cannot be confirmed without richer inverter telemetry"
    ]
  },
  "impact": {
    "energy_value_at_risk_inr": 73.6,
    "estimated_recoverable_value_inr": 48.3
  },
  "decision": {
    "recommended_action": "Run remote grid and inverter checks; dispatch if unresolved",
    "visit_required": true,
    "priority_score": 84,
    "priority_label": "High",
    "score_breakdown": {
      "energy_impact": 27,
      "persistence": 18,
      "confidence": 12,
      "complaint_urgency": 15,
      "sla_risk": 8,
      "route_benefit": 4
    }
  }
}
```

## 8. Service queue

### `GET /api/service-queue`

Query parameters:

- `priority`
- `action_type`
- `visit_required`
- `service_region`

**Response**

```json
{
  "analysis_run_id": "RUN-20260703-001",
  "items": [
    {
      "rank": 1,
      "site_id": "MH-142",
      "priority_score": 84,
      "priority_label": "High",
      "probable_issue": "SUDDEN_PRODUCTION_OUTAGE",
      "confidence": 0.82,
      "energy_loss_kwh": 9.2,
      "value_at_risk_inr": 73.6,
      "recommended_action": "REMOTE_THEN_VISIT",
      "visit_required": true,
      "required_skill": "electrical"
    }
  ]
}
```

## 9. Cleaning evaluation

### `GET /api/sites/{site_id}/cleaning-decision`

**Response**

```json
{
  "site_id": "MH-217",
  "decision": "SCHEDULE_CLEANING",
  "projected_7_day_loss_kwh": 180.0,
  "adjusted_recoverable_value_inr": 1008.0,
  "cleaning_cost_inr": 750.0,
  "safety_margin": 1.2,
  "significant_rain_expected": false,
  "explanation": "Projected recoverable value exceeds the cost threshold and no significant rain is expected."
}
```

## 10. Routes

### `POST /api/routes/optimize`

**Request**

```json
{
  "analysis_run_id": "RUN-20260703-001",
  "plan_date": "2026-07-04",
  "technician_ids": ["TECH-01", "TECH-02"],
  "include_priority_labels": ["Critical", "High"],
  "include_medium_if_capacity": true
}
```

**200 response**

```json
{
  "route_plan_id": "ROUTE-20260704-001",
  "plan_date": "2026-07-04",
  "summary": {
    "jobs_assigned": 4,
    "jobs_unassigned": 1,
    "naive_distance_km": 68.0,
    "optimised_distance_km": 47.0,
    "distance_saved_km": 21.0,
    "estimated_recoverable_energy_kwh": 25.4
  },
  "routes": [
    {
      "technician_id": "TECH-01",
      "total_distance_km": 24.0,
      "estimated_duration_min": 330,
      "stops": [
        {
          "sequence": 1,
          "site_id": "MH-142",
          "job_type": "ELECTRICAL_DIAGNOSTIC",
          "priority_label": "High",
          "estimated_job_duration_min": 75
        }
      ]
    }
  ],
  "unassigned_jobs": []
}
```

### `GET /api/routes/latest`

Returns latest route plan.

## 11. Reports

### `GET /api/reports/daily-plan`

Query parameters: `route_plan_id`, `format=csv`.

Response: downloadable UTF-8 CSV.

## 12. HTTP status conventions

- 200: successful read/action
- 201: resource created if used
- 400: malformed request
- 404: site/run/resource not found
- 409: analysis state conflict
- 422: schema validation error
- 500: controlled internal failure

## 13. API acceptance checks

- Swagger opens and documents all endpoints.
- Example payloads match actual schemas.
- Pydantic rejects invalid enums and missing required fields.
- No endpoint exposes fault ground truth.
- Frontend can complete the entire demo through API calls only.
