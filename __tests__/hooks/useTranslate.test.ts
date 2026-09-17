import { describe, expect, it, vi } from "vitest";
import { handleSseEvent } from "@/hooks/useTranslate";

describe("translation completion", () => {
  it("preserves limitations from the server for display", () => {
    const onSuccess = vi.fn();
    handleSseEvent(
      "done",
      {
        sparql: "SELECT ?work WHERE {}",
        confidence: "medium",
        assumptions: ["The archive does not distinguish composers from other contributors."],
      },
      vi.fn(),
      onSuccess,
      vi.fn(),
    );
    expect(onSuccess).toHaveBeenCalledWith({
      sparql: "SELECT ?work WHERE {}",
      confidence: "medium",
      assumptions: ["The archive does not distinguish composers from other contributors."],
    });
  });

  it("accepts older responses without inventing an assessment", () => {
    const onSuccess = vi.fn();
    handleSseEvent("done", { sparql: "SELECT ?s WHERE {}" }, vi.fn(), onSuccess, vi.fn());
    expect(onSuccess).toHaveBeenCalledWith({
      sparql: "SELECT ?s WHERE {}",
      confidence: null,
      assumptions: [],
    });
  });
});
