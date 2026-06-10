import { NextRequest, NextResponse } from "next/server";
import { explainSchema } from "@/lib/validations/explain";
import { explainSparql } from "@/lib/llm/client";
import { apiError } from "@/lib/api-error";
import { rateLimit } from "@/lib/rate-limit";
import { logger } from "@/lib/logger";

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";

  const limited = rateLimit(ip, 10, 60_000);
  if (limited) return limited;

  let body;
  try {
    body = explainSchema.parse(await req.json());
  } catch {
    return apiError("Invalid request body", 400);
  }

  const start = performance.now();
  logger.info({ event: "api_request", route: "/api/explain", ip });

  try {
    const result = await explainSparql(body.sparql);
    const durationMs = Math.round(performance.now() - start);
    logger.info({ event: "api_response", route: "/api/explain", durationMs, status: 200 });
    return NextResponse.json({ explanation: result.explanation });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Explanation failed";
    logger.error({ event: "api_error", route: "/api/explain", error: message });
    return apiError("Failed to explain query", 500);
  }
}
