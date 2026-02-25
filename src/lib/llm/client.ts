import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { generateText } from "ai";
import { env } from "@/lib/env";
import { logger } from "@/lib/logger";
import { buildSystemPrompt } from "@/lib/llm/prompt";
import { FEW_SHOT_EXAMPLES } from "@/lib/llm/examples";
import { flags } from "@/lib/feature-flags";

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
  let examples: typeof FEW_SHOT_EXAMPLES;
  if (flags.useRAG) {
    // Phase 3 modules — don't exist yet. Dynamic import prevents crash when flag=false.
    // @ts-expect-error — @/lib/rag/embed will be created in Phase 3
    const { getEmbedding } = await import("@/lib/rag/embed");
    // @ts-expect-error — @/lib/rag/retrieve will be created in Phase 3
    const { findSimilarExamples } = await import("@/lib/rag/retrieve");
    const embedding = await getEmbedding(userQuery);
    examples = await findSimilarExamples(embedding, 5);
  } else {
    examples = FEW_SHOT_EXAMPLES;
  }

  const start = performance.now();

  const { text, usage } = await generateText({
    model: google(env.LLM_MODEL),
    system: buildSystemPrompt(examples),
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
    ragEnabled: flags.useRAG,
    examplesUsed: examples.length,
  });

  // Strip markdown code fences if the LLM ignores the "raw SPARQL only" instruction
  const cleaned = text
    .replace(/^```sparql?\n?/i, "")
    .replace(/\n?```$/i, "")
    .trim();

  return { sparql: cleaned, usage, durationMs };
}
