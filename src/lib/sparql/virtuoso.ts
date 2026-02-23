import { env } from "@/lib/env";
import { logger } from "@/lib/logger";

export interface SparqlResults {
  head: { vars: string[] };
  results: { bindings: Record<string, { type: string; value: string }>[] };
}

export async function executeSparql(sparql: string): Promise<SparqlResults> {
  const start = performance.now();

  const res = await fetch(env.VIRTUOSO_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Accept: "application/sparql-results+json",
    },
    body: new URLSearchParams({ query: sparql }),
  });

  const durationMs = Math.round(performance.now() - start);

  if (!res.ok) {
    const errorText = await res.text();
    logger.error({
      event: "virtuoso_error",
      status: res.status,
      durationMs,
      error: errorText.slice(0, 500),
    });
    throw new Error(`Virtuoso error (${res.status}): ${errorText.slice(0, 200)}`);
  }

  const data = (await res.json()) as SparqlResults;

  logger.info({
    event: "virtuoso_query",
    durationMs,
    status: res.status,
    resultCount: data.results.bindings.length,
  });

  return data;
}
