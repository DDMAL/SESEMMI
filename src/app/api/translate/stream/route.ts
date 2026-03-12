import { NextRequest } from "next/server";
import { translateSchema } from "@/lib/validations/translate";
import { apiError } from "@/lib/api-error";
import { rateLimit } from "@/lib/rate-limit";
import { logger } from "@/lib/logger";
import { env } from "@/lib/env";

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";

  const limited = rateLimit(ip, 10, 60_000);
  if (limited) return limited;

  let body;
  try {
    body = translateSchema.parse(await req.json());
  } catch {
    return apiError("Invalid request body", 400);
  }

  logger.info({ event: "api_request", route: "/api/translate/stream", ip });

  const upstream = await fetch(`${env.LLM_SERVICE_URL}/translate/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query: body.query }),
  }).catch((err) => {
    logger.error({ event: "api_error", route: "/api/translate/stream", error: String(err) });
    return null;
  });

  if (!upstream?.ok || !upstream.body) {
    return apiError("LLM service streaming failed", 502);
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
