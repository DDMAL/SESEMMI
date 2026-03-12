import { z } from "zod";

const envSchema = z.object({
  VIRTUOSO_ENDPOINT: z.string().url(),
  LLM_SERVICE_URL: z.string().url().default("http://llm:8000"),
  LLM_API_KEY: z.string().min(1),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
  NODE_ENV: z.enum(["development", "production", "test"]).default("development"),
});

export const env = envSchema.parse(process.env);
