import { NextRequest, NextResponse } from "next/server";
import { clarifySchema } from "@/lib/validations/clarify";
import { clarifyQuery } from "@/lib/llm/client";
import { apiError } from "@/lib/api-error";
import { rateLimit } from "@/lib/rate-limit";
import { logger } from "@/lib/logger";

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";

  // Generous limit — a single disambiguation session makes several rounds.
  const limited = rateLimit(ip, 30, 60_000);
  if (limited) return limited;

  let body;
  try {
    body = clarifySchema.parse(await req.json());
  } catch {
    return apiError("Invalid request body", 400);
  }

  const start = performance.now();
  logger.info({ event: "api_request", route: "/api/clarify", ip });

  try {
    const result = await clarifyQuery(body.query, body.history);
    const durationMs = Math.round(performance.now() - start);
    logger.info({ event: "api_response", route: "/api/clarify", durationMs, status: 200 });
    return NextResponse.json(result);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Clarification failed";
    logger.error({ event: "api_error", route: "/api/clarify", error: message });
    return apiError("Failed to clarify query", 500);
  }
}
