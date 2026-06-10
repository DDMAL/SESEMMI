import { describe, it, expect } from "vitest";
import { validateSparql } from "@/lib/sparql/validate";

describe("validateSparql", () => {
  it("accepts a valid SELECT query", () => {
    expect(validateSparql("SELECT ?s WHERE { ?s ?p ?o }").valid).toBe(true);
  });

  it("accepts a query without WHERE (WHERE is optional in SPARQL 1.1)", () => {
    expect(validateSparql("SELECT ?s { ?s ?p ?o }").valid).toBe(true);
  });

  it("accepts DESCRIBE without a WHERE clause", () => {
    expect(validateSparql("DESCRIBE <http://example.org/resource>").valid).toBe(true);
  });

  it("accepts a query with PREFIX declarations", () => {
    expect(
      validateSparql("PREFIX mo: <http://purl.org/ontology/mo/> SELECT ?s WHERE { ?s ?p ?o }")
        .valid,
    ).toBe(true);
  });

  it("accepts an ASK query", () => {
    expect(validateSparql("ASK { <http://example.org/> ?p ?o }").valid).toBe(true);
  });

  it("rejects an empty query", () => {
    const result = validateSparql("");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("empty");
  });

  it("rejects a query with unbalanced braces", () => {
    const result = validateSparql("SELECT ?s WHERE { ?s ?p ?o");
    expect(result.valid).toBe(false);
    expect(result.error).toBeTruthy();
  });

  it("rejects a query with no query form keyword", () => {
    const result = validateSparql("{ ?s ?p ?o }");
    expect(result.valid).toBe(false);
  });

  it("rejects a FILTER with unclosed parenthesis", () => {
    const result = validateSparql("SELECT ?s WHERE { ?s ?p ?o . FILTER(?s > 0 }");
    expect(result.valid).toBe(false);
  });

  it("rejects a SELECT with no variable list and no wildcard", () => {
    const result = validateSparql("SELECT WHERE { ?s ?p ?o }");
    expect(result.valid).toBe(false);
  });

  it("includes a line number in the error message", () => {
    const result = validateSparql("SELECT ?s WHERE {\n  ?s ?p ?o\n");
    expect(result.valid).toBe(false);
    expect(result.error).toMatch(/Line \d+/);
  });
});
