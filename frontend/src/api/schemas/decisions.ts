import { z } from "zod";

import { priorityLabelSchema } from "./common";

export const serviceDecisionSchema = z.object({
  decision_id: z.string(),
  analysis_run_id: z.string(),
  incident_candidate_id: z.string(),
  site_id: z.string(),
  probable_issue: z.string(),
  confidence_score: z.number(),
  confidence_label: z.string(),
  supporting_evidence: z.array(z.string()),
  contradictory_evidence: z.array(z.string()),
  expected_energy_kwh: z.number(),
  actual_energy_kwh: z.number().nullable(),
  estimated_energy_loss_kwh: z.number(),
  estimated_value_at_risk_inr: z.number(),
  projected_seven_day_loss_kwh: z.number(),
  estimated_recoverable_energy_kwh: z.number(),
  estimated_recoverable_value_inr: z.number(),
  cleaning_decision: z.string(),
  recommended_action: z.string(),
  escalation_condition: z.string(),
  remote_action_available: z.boolean(),
  visit_required: z.boolean(),
  actionable: z.boolean(),
  priority_score: z.number(),
  priority_label: priorityLabelSchema,
  queue_rank: z.number().nullable(),
  created_at: z.string(),
});

export const serviceQueueSchema = z.object({
  analysis_run_id: z.string(),
  count: z.number(),
  items: z.array(serviceDecisionSchema),
});

export type ServiceDecision = z.infer<typeof serviceDecisionSchema>;
export type ServiceQueue = z.infer<typeof serviceQueueSchema>;
