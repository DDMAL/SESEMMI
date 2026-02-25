import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { generateText } from "ai";
import { env } from "@/lib/env";
import { logger } from "@/lib/logger";
import { buildSystemPrompt } from "@/lib/llm/prompt";
import { FEW_SHOT_EXAMPLES } from "@/lib/llm/examples";

const google = createGoogleGenerativeAI({ apiKey: env.LLM_API_KEY });

export interface TranslateResult {
  sparql: string;
  usage: {
    inputTokens: number | undefined;
    outputTokens: number | undefined;
    totalTokens: number | undefined;
  };
  durationMs: number;
}

export async function translateToSparql(
  userQuery: string,
): Promise<TranslateResult> {
  const start = performance.now();

  const { text, usage } = await generateText({
    model: google(env.LLM_MODEL),
    system: buildSystemPrompt(FEW_SHOT_EXAMPLES),
    prompt: userQuery,
  });

  const durationMs = Math.round(performance.now() - start);

  logger.info({
    event: "llm_translation",
    model: env.LLM_MODEL,
    durationMs,
    inputTokens: usage.inputTokens,
    outputTokens: usage.outputTokens,
    totalTokens: usage.totalTokens,
  });

  // Strip markdown code fences if the LLM ignores the "raw SPARQL only" instruction
  const cleaned = text
    .replace(/^```sparql?\n?/i, "")
    .replace(/\n?```$/i, "")
    .trim();

  return { sparql: cleaned, usage, durationMs };
}
