import { z } from "zod";

export const translateSchema = z.object({
  query: z.string().min(1, "Query is required").max(2000),
});

export type TranslateInput = z.infer<typeof translateSchema>;
