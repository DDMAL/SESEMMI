import { describe, it, expect } from "vitest";
import { validateSparql } from "@/lib/sparql/validate";

describe("validateSparql", () => {
  it("accepts a valid SELECT query", () => {
    const result = validateSparql("SELECT ?s WHERE { ?s ?p ?o }");
    expect(result.valid).toBe(true);
  });

  it("rejects an empty query", () => {
    const result = validateSparql("");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("empty");
  });

  it("rejects a query with no query form keyword", () => {
    const result = validateSparql("{ ?s ?p ?o }");
    expect(result.valid).toBe(false);
  });

  it("detects unbalanced braces", () => {
    const result = validateSparql("SELECT ?s WHERE { ?s ?p ?o");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("Unbalanced");
  });

  it("accepts DESCRIBE without a WHERE clause", () => {
    const result = validateSparql("DESCRIBE <http://example.org/resource>");
    expect(result.valid).toBe(true);
  });

  it("accepts a query with PREFIX declarations", () => {
    const result = validateSparql(
      "PREFIX mo: <http://purl.org/ontology/mo/> SELECT ?s WHERE { ?s ?p ?o }",
    );
    expect(result.valid).toBe(true);
  });

  it("rejects a query missing WHERE", () => {
    const result = validateSparql("SELECT ?s { ?s ?p ?o }");
    expect(result.valid).toBe(false);
  });
});
