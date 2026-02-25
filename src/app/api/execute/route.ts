import { NextRequest, NextResponse } from "next/server";
import { executeSchema } from "@/lib/validations/execute";
import { executeSparql } from "@/lib/sparql/virtuoso";
import { validateSparql } from "@/lib/sparql/validate";
import { apiError } from "@/lib/api-error";
import { rateLimit } from "@/lib/rate-limit";
import { logger } from "@/lib/logger";

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";

  // Rate limit
  const limited = rateLimit(ip);
  if (limited) return limited;

  // Validate input
  let body;
  try {
    body = executeSchema.parse(await req.json());
  } catch (error) {
    logger.warn({ event: "api_validation_error", route: "/api/execute", ip, error });
    return apiError("Invalid request body", 400);
  }

  // Pre-flight SPARQL validation
  const validation = validateSparql(body.sparql);
  if (!validation.valid) {
    return apiError(validation.error ?? "Invalid SPARQL", 400);
  }

  // Execute
  const start = performance.now();
  logger.info({ event: "api_request", route: "/api/execute", ip });

  try {
    const results = await executeSparql(body.sparql);
    const durationMs = Math.round(performance.now() - start);
    logger.info({ event: "api_response", route: "/api/execute", durationMs, status: 200 });
    return NextResponse.json(results);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown error";
    logger.error({ event: "api_error", route: "/api/execute", error: message });
    return apiError(message, 502);
  }
}
