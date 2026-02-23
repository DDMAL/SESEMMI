import { apiError } from "@/lib/api-error";
import { logger } from "@/lib/logger";

const requests = new Map<string, { count: number; resetAt: number }>();

export function rateLimit(ip: string, limit = 20, windowMs = 60_000) {
  const now = Date.now();
  const entry = requests.get(ip);

  if (!entry || now > entry.resetAt) {
    requests.set(ip, { count: 1, resetAt: now + windowMs });
    return null;
  }

  if (entry.count >= limit) {
    logger.warn({ event: "rate_limit_hit", ip, limit });
    return apiError("Too many requests", 429);
  }

  entry.count++;
  return null;
}
