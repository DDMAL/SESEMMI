import { NextRequest, NextResponse } from "next/server";
import { translateSchema } from "@/lib/validations/translate";
import { translateToSparql } from "@/lib/llm/client";
import { apiError } from "@/lib/api-error";
import { rateLimit } from "@/lib/rate-limit";
import { logger } from "@/lib/logger";

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";

  // Tighter rate limit for LLM calls (costs money)
  const limited = rateLimit(ip, 10, 60_000);
  if (limited) return limited;

  let body;
  try {
    body = translateSchema.parse(await req.json());
  } catch {
    return apiError("Invalid request body", 400);
  }

  const start = performance.now();
  logger.info({ event: "api_request", route: "/api/translate", ip });

  try {
    const result = await translateToSparql(body.query);
    const durationMs = Math.round(performance.now() - start);
    logger.info({ event: "api_response", route: "/api/translate", durationMs, status: 200 });
    return NextResponse.json({ sparql: result.sparql });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Translation failed";
    logger.error({ event: "api_error", route: "/api/translate", error: message });
    return apiError("Failed to translate query", 500);
  }
}
