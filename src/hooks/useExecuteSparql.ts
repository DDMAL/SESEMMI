import { useMutation } from "@tanstack/react-query";
import type { SparqlResults } from "@/lib/sparql/virtuoso";

export function useExecuteSparql() {
  return useMutation({
    mutationFn: async (sparql: string): Promise<SparqlResults> => {
      const res = await fetch("/api/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sparql }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      return res.json();
    },
  });
}
