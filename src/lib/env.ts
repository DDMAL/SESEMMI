import { z } from "zod";

const envSchema = z.object({
  VIRTUOSO_ENDPOINT: z.string().url(),
  LLM_API_KEY: z.string().min(1),
  LLM_MODEL: z.string().default("gemini-2.5-flash-lite"),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
  FEATURE_RAG_ENABLED: z.coerce.boolean().default(false),
});

export const env = envSchema.parse(process.env);
