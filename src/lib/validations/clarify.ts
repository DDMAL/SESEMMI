import { z } from "zod";

export const clarifySchema = z.object({
  query: z.string().min(1, "Query is required").max(2000),
  history: z.array(z.object({ question: z.string(), answer: z.string() })).default([]),
  language: z.enum(["en", "fr", "fa", "es", "de"]).default("en"),
});

export type ClarifyInput = z.infer<typeof clarifySchema>;
