import { z } from "zod";

import {
  isoTimestampSchema,
  nullableNumberSchema,
  nullableStringSchema,
  priorityLabelSchema,
} from "./common";
import { serviceDecisionSchema } from "./decisions";

export const siteSummarySchema = z.object({
  site_id: z.string(),
  site_name: z.string(),
  capacity_kw: z.number(),
  latitude: z.number(),
  longitude: z.number(),
  weather_zone: z.string(),
  azimuth_degree: z.number(),
  tariff_per_kwh: z.number(),
  service_region: z.string(),
  customer_type: z.string(),
  warranty_end_date: z.string(),
  cleaning_cost_inr: z.number(),
  visit_cost_inr: z.number(),
  analysis_run_id: z.string(),
  status: z.string(),
  probable_issue: nullableStringSchema,
  priority_label: priorityLabelSchema.nullable(),
  priority_score: nullableNumberSchema,
  actionable: z.boolean(),
});

export const siteListSchema = z.array(siteSummarySchema);

export const siteMasterSchema = z.object({
  site_id: z.string(),
  site_name: z.string(),
  capacity_kw: z.number(),
  latitude: z.number(),
  longitude: z.number(),
  weather_zone: z.string(),
  azimuth_degree: z.number(),
  tariff_per_kwh: z.number(),
  service_region: z.string(),
  customer_type: z.string(),
  warranty_end_date: z.string(),
  cleaning_cost_inr: z.number(),
  visit_cost_inr: z.number(),
});

export const sitePerformancePointSchema = z.object({
  timestamp: isoTimestampSchema,
  expected_generation_kwh: z.number(),
  actual_generation_kwh: z.number().nullable(),
  signed_residual_kwh: z.number().nullable(),
  energy_loss_kwh: z.number(),
  performance_ratio: z.number().nullable(),
  ghi_wm2: z.number().nullable(),
  anomaly_state: z.string().nullable(),
  data_quality_status: z.string().nullable(),
});

export const diagnosticCandidateSchema = z
  .object({
    incident_candidate_id: z.string().optional(),
    start_timestamp: z.string().optional().nullable(),
    end_timestamp: z.string().optional().nullable(),
    duration_intervals: z.number().optional().nullable(),
    persistence_intervals: z.number().optional().nullable(),
    anomaly_type: z.string().optional().nullable(),
    severity: z.string().optional().nullable(),
  })
  .passthrough()
  .nullable();

export const siteDiagnosticItemSchema = z.object({
  decision: serviceDecisionSchema,
  candidate: diagnosticCandidateSchema,
});

export const siteDiagnosticsSchema = z.object({
  analysis_run_id: z.string(),
  site: siteMasterSchema,
  diagnostics: z.array(siteDiagnosticItemSchema),
  performance: z.array(sitePerformancePointSchema),
});

export type SiteSummary = z.infer<typeof siteSummarySchema>;
export type SiteMaster = z.infer<typeof siteMasterSchema>;
export type SitePerformancePoint = z.infer<typeof sitePerformancePointSchema>;
export type SiteDiagnosticItem = z.infer<typeof siteDiagnosticItemSchema>;
export type SiteDiagnostics = z.infer<typeof siteDiagnosticsSchema>;
