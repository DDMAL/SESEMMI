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

export interface ClarifyTurn {
  question: string;
  answer: string;
}

export interface ClarifyQuestion {
  question: string;
  options: string[];
}

export interface ClarifyResult {
  ready: boolean;
  questions: ClarifyQuestion[];
  enriched_query: string;
}

export async function clarifyQuery(
  userQuery: string,
  history: ClarifyTurn[],
): Promise<ClarifyResult> {
  const maxAttempts = 3;
  let lastError: Error | undefined;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const res = await fetch(`${env.LLM_SERVICE_URL}/clarify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userQuery, history }),
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "LLM service error" }));
        throw new Error(error.detail || `LLM service returned ${res.status}`);
      }

      return (await res.json()) as ClarifyResult;
    } catch (err) {
      lastError = err as Error;
      if (attempt < maxAttempts) {
        await new Promise((r) => setTimeout(r, 500 * attempt));
      }
    }
  }

  throw lastError!;
}

export async function translateToSparql(userQuery: string): Promise<TranslateResult> {
  const maxAttempts = 3;
  let lastError: Error | undefined;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
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
    } catch (err) {
      lastError = err as Error;
      if (attempt < maxAttempts) {
        await new Promise((r) => setTimeout(r, 500 * attempt));
      }
    }
  }

  throw lastError!;
}
