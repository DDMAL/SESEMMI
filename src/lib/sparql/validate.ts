import { Parser } from "sparqljs";

export function validateSparql(sparql: string): { valid: boolean; error?: string } {
  if (!sparql.trim()) return { valid: false, error: "Query is empty" };

  try {
    new Parser().parse(sparql);
    return { valid: true };
  } catch (err) {
    return { valid: false, error: formatSparqlError(err) };
  }
}

export function formatSparqlError(err: unknown): string {
  const raw = err instanceof Error ? err.message : "Invalid SPARQL";
  // peggy (sparqljs's parser generator) formats errors as:
  //   "Parse error on line N:\n...<context>...\n--^--\nExpected X but Y found."
  const lineMatch = /Parse error on line (\d+)/.exec(raw);
  const lines = raw.split("\n");
  const detail = lines.find((l) => /^Expected|^Unexpected/.test(l.trim())) ?? lines[0];
  return lineMatch ? `Line ${lineMatch[1]}: ${detail.trim()}` : detail.trim();
}
