import { useMutation } from "@tanstack/react-query";
import { useI18n } from "@/lib/i18n/context";

export interface ClarifyTurn {
  question: string;
  answer: string;
}

export interface ClarifyQuestion {
  question: string;
  options: string[];
}

export interface ClarifyResult {
  ready: boolean;
  questions: ClarifyQuestion[];
  enriched_query: string;
  /** Display-only, localized copy of enriched_query (falls back to enriched_query). */
  enriched_query_display: string;
}

export function useClarify() {
  const { locale } = useI18n();
  return useMutation({
    mutationFn: async (vars: { query: string; history: ClarifyTurn[] }): Promise<ClarifyResult> => {
      const res = await fetch("/api/clarify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...vars, language: locale }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      return (await res.json()) as ClarifyResult;
    },
  });
}
