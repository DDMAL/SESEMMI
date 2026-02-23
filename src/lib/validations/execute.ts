import { z } from "zod";

export const executeSchema = z.object({
  sparql: z.string().min(1, "SPARQL query is required").max(10000),
  endpoint: z.string().url().optional(),
});

export type ExecuteInput = z.infer<typeof executeSchema>;
