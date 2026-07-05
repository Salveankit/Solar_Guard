import { z } from "zod";

import { isoTimestampSchema } from "./common";

export const fleetSummarySchema = z.object({
  analysis_run_id: z.string(),
  monitored_sites: z.number(),
  healthy_sites: z.number(),
  attention_sites: z.number(),
  communication_issues: z.number(),
  insufficient_evidence: z.number(),
  remote_actions: z.number(),
  field_visits: z.number(),
  estimated_energy_value_at_risk_inr: z.number(),
  estimated_recoverable_energy_kwh: z.number(),
  estimated_recoverable_value_inr: z.number(),
  top_priority_site_id: z.string().nullable(),
});

export const fleetTimeseriesItemSchema = z.object({
  timestamp: isoTimestampSchema,
  expected_generation_kwh: z.number(),
  actual_generation_kwh: z.number().nullable(),
  energy_loss_kwh: z.number(),
  ghi_wm2: z.number().nullable(),
});

export const fleetTimeseriesSchema = z.object({
  analysis_run_id: z.string(),
  items: z.array(fleetTimeseriesItemSchema),
});

export type FleetSummary = z.infer<typeof fleetSummarySchema>;
export type FleetTimeseries = z.infer<typeof fleetTimeseriesSchema>;
export type FleetTimeseriesItem = z.infer<typeof fleetTimeseriesItemSchema>;
