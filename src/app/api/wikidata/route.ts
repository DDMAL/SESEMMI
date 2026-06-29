import { NextRequest, NextResponse } from "next/server";
import { wikidataLabelsSchema } from "@/lib/validations/wikidata";
import { apiError } from "@/lib/api-error";
import { rateLimit } from "@/lib/rate-limit";
import { logger } from "@/lib/logger";

const WIKIDATA_API = "https://www.wikidata.org/w/api.php";

interface EntityInfo {
  label: string;
  description?: string;
}

async function fetchChunk(ids: string[], lang: string): Promise<Record<string, EntityInfo>> {
  const languages = lang === "en" ? "en" : `${lang}|en`;
  const url =
    `${WIKIDATA_API}?action=wbgetentities&ids=${ids.join("|")}` +
    `&props=labels|descriptions&languages=${languages}&languagefallback=1&format=json&origin=*`;
  const res = await fetch(url, {
    headers: { "User-Agent": "SESEMMI/1.0 (music metadata search; contact admin)" },
  });
  if (!res.ok) throw new Error(`Wikidata API ${res.status}`);
  const data = (await res.json()) as {
    entities?: Record<
      string,
      {
        labels?: Record<string, { value: string }>;
        descriptions?: Record<string, { value: string }>;
      }
    >;
  };
  const out: Record<string, EntityInfo> = {};
  for (const [id, ent] of Object.entries(data.entities ?? {})) {
    const label = ent.labels?.[lang]?.value ?? ent.labels?.en?.value;
    if (label) {
      const description = ent.descriptions?.[lang]?.value ?? ent.descriptions?.en?.value;
      out[id] = { label, description };
    }
  }
  return out;
}

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for") ?? "unknown";
  const limited = rateLimit(ip, 20, 60_000);
  if (limited) return limited;

  let body;
  try {
    body = wikidataLabelsSchema.parse(await req.json());
  } catch {
    return apiError("Invalid request body", 400);
  }

  const start = performance.now();
  logger.info({ event: "api_request", route: "/api/wikidata", ip, count: body.ids.length });

  try {
    // Batch in chunks of 50 (wbgetentities limit), resolve all in parallel.
    const chunks: string[][] = [];
    for (let i = 0; i < body.ids.length; i += 50) chunks.push(body.ids.slice(i, i + 50));
    const results = await Promise.all(chunks.map((ids) => fetchChunk(ids, body.language)));
    const labels = Object.assign({}, ...results) as Record<string, EntityInfo>;
    const durationMs = Math.round(performance.now() - start);
    logger.info({ event: "api_response", route: "/api/wikidata", durationMs, status: 200 });
    return NextResponse.json({ labels });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Wikidata lookup failed";
    logger.error({ event: "api_error", route: "/api/wikidata", error: message });
    return apiError("Failed to resolve Wikidata labels", 502);
  }
}
