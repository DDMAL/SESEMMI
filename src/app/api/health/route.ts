import { NextResponse } from "next/server";
import { env } from "@/lib/env";
import { logger } from "@/lib/logger";

export async function GET() {
  const checks: Record<string, string> = { status: "ok" };

  // Check Virtuoso connectivity
  try {
    const res = await fetch(env.VIRTUOSO_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        Accept: "application/sparql-results+json",
      },
      body: new URLSearchParams({ query: "SELECT 1 WHERE { }" }),
      signal: AbortSignal.timeout(5000),
    });
    checks.virtuoso = res.ok ? "connected" : "error";
  } catch {
    checks.virtuoso = "unreachable";
  }

  const allHealthy = checks.virtuoso === "connected";
  const status = allHealthy ? 200 : 503;

  if (!allHealthy) {
    logger.warn({ event: "health_check_degraded", checks });
  }

  return NextResponse.json(checks, { status });
}
