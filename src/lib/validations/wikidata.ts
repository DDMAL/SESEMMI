import { z } from "zod";

export const wikidataLabelsSchema = z.object({
  ids: z.array(z.string().regex(/^[QP]\d+$/)).max(200),
  language: z.enum(["en", "fr", "fa", "es", "de"]).default("en"),
});
