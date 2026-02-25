/**
 * Lightweight SPARQL syntax validator — no external dependencies.
 * Safe to import from both "use client" components and server routes.
 *
 * Catches the most common LLM output mistakes (wrong query form,
 * missing WHERE, unbalanced braces) without a full parser.
 * Virtuoso will catch any remaining syntax errors with its own messages.
 */
export function validateSparql(sparql: string): { valid: boolean; error?: string } {
  const trimmed = sparql.trim();

  if (!trimmed) return { valid: false, error: "Query is empty" };

  if (!/\b(SELECT|CONSTRUCT|ASK|DESCRIBE)\b/i.test(trimmed)) {
    return { valid: false, error: "Query must contain SELECT, CONSTRUCT, ASK, or DESCRIBE" };
  }

  const isDescribe = /^\s*(PREFIX[\s\S]*?)?\s*DESCRIBE\b/i.test(trimmed);
  if (!isDescribe && !/\bWHERE\b/i.test(trimmed)) {
    return { valid: false, error: "Missing WHERE clause" };
  }

  const opens = (trimmed.match(/{/g) ?? []).length;
  const closes = (trimmed.match(/}/g) ?? []).length;
  if (opens !== closes) {
    return {
      valid: false,
      error: `Unbalanced braces (${opens} opening, ${closes} closing)`,
    };
  }

  return { valid: true };
}
