import { z } from "zod";

import { priorityLabelSchema } from "./common";

export const routeWorkItemSchema = z.object({
  decision_id: z.string(),
  site_id: z.string(),
  probable_issue: z.string(),
  recommended_action: z.string(),
  actionable: z.boolean(),
  remote_action_available: z.boolean(),
  visit_required: z.boolean(),
  priority_score: z.number(),
  priority_label: priorityLabelSchema,
});

export const routeJobSchema = z.object({
  decision_id: z.string(),
  candidate_id: z.string(),
  site_id: z.string(),
  latitude: z.number(),
  longitude: z.number(),
  priority_score: z.number(),
  priority_label: priorityLabelSchema,
  probable_issue: z.string(),
  recommended_action: z.string(),
  required_skills: z.array(z.string()),
  duration_min: z.number(),
  recoverable_energy_kwh: z.number(),
  recoverable_value_inr: z.number(),
  escalation_deadline: z.string().nullable(),
  earliest_service_time: z.string().nullable(),
});

export const routeStopSchema = z.object({
  technician_id: z.string(),
  sequence: z.number(),
  job: routeJobSchema,
  arrival: z.string(),
  departure: z.string(),
  travel_distance_km: z.number(),
  travel_duration_min: z.number(),
});

export const technicianRouteSchema = z.object({
  technician_id: z.string(),
  technician_name: z.string().optional(),
  shift_start: z.string().optional(),
  shift_end: z.string().optional(),
  region: z.string().optional(),
  skills: z.array(z.string()),
  distance_km: z.number(),
  travel_duration_min: z.number(),
  job_duration_min: z.number(),
  return_to_hub: z.boolean(),
  stops: z.array(routeStopSchema),
});

export const latestRoutePlanSchema = z.object({
  route_plan_id: z.string(),
  analysis_run_id: z.string(),
  planning_date: z.string(),
  optimisation_status: z.string(),
  failure_reason: z.string().nullable(),
  field_plan: z.array(technicianRouteSchema),
  remote_action_queue: z.array(routeWorkItemSchema),
  monitoring_queue: z.array(routeWorkItemSchema),
  unassigned_jobs: z.array(z.unknown()),
  naive_routes: z.array(z.array(z.string())),
  total_eligible_jobs: z.number(),
  assigned_jobs: z.number(),
  unassigned_jobs_count: z.number(),
  naive_distance_km: z.number(),
  optimised_distance_km: z.number(),
  distance_avoided_km: z.number(),
  total_travel_duration_min: z.number(),
  total_job_duration_min: z.number(),
  total_recoverable_energy_kwh: z.number(),
  total_recoverable_value_inr: z.number(),
});

export type LatestRoutePlan = z.infer<typeof latestRoutePlanSchema>;
export type RouteWorkItem = z.infer<typeof routeWorkItemSchema>;
export type RouteJob = z.infer<typeof routeJobSchema>;
export type RouteStop = z.infer<typeof routeStopSchema>;
export type TechnicianRoute = z.infer<typeof technicianRouteSchema>;
