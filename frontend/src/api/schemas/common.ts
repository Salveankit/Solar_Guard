import { z } from "zod";

export const nullableNumberSchema = z.number().nullable();
export const nullableStringSchema = z.string().nullable();

export const isoTimestampSchema = z.string().min(1);

export const priorityLabelSchema = z.union([
  z.literal("Critical"),
  z.literal("High"),
  z.literal("Medium"),
  z.literal("Low"),
]);
