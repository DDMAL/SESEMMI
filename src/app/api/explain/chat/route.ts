import { NextRequest, NextResponse } from "next/server";
import { explainChatSchema } from "@/lib/validations/explain";
import { explainChat } from "@/lib/llm/client";
import { apiError } from "@/lib/api-error";
import { rateLimit } from "@/lib/rate-limit";
import { logger } from "@/lib/logger";

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";

  const limited = rateLimit(ip, 10, 60_000);
  if (limited) return limited;

  let body;
  try {
    body = explainChatSchema.parse(await req.json());
  } catch {
    return apiError("Invalid request body", 400);
  }

  const start = performance.now();
  logger.info({ event: "api_request", route: "/api/explain/chat", ip });

  try {
    const result = await explainChat(body.sparql, body.messages);
    const durationMs = Math.round(performance.now() - start);
    logger.info({ event: "api_response", route: "/api/explain/chat", durationMs, status: 200 });
    return NextResponse.json({ reply: result.reply });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Chat failed";
    logger.error({ event: "api_error", route: "/api/explain/chat", error: message });
    return apiError("Failed to get chat reply", 500);
  }
}
