import { env } from "@/lib/env";
import { logger } from "@/lib/logger";

export interface TranslateResult {
  sparql: string;
  usage: {
    inputTokens: number | undefined;
    outputTokens: number | undefined;
    totalTokens: number | undefined;
  };
  durationMs: number;
}

export async function translateToSparql(userQuery: string): Promise<TranslateResult> {
  const res = await fetch(`${env.LLM_SERVICE_URL}/translate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query: userQuery }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "LLM service error" }));
    throw new Error(error.detail || `LLM service returned ${res.status}`);
  }

  const data = await res.json();

  logger.info({
    event: "llm_translation",
    durationMs: data.durationMs,
    inputTokens: data.usage.inputTokens,
    outputTokens: data.usage.outputTokens,
    totalTokens: data.usage.totalTokens,
  });

  return {
    sparql: data.sparql,
    usage: data.usage,
    durationMs: data.durationMs,
  };
}
