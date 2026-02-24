import { useMutation } from "@tanstack/react-query";

interface TranslateResult {
  sparql: string;
}

export function useTranslate() {
  return useMutation({
    mutationFn: async (naturalLanguage: string): Promise<TranslateResult> => {
      const res = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: naturalLanguage }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error(data.error || `HTTP ${res.status}`);
      }
      return res.json();
    },
  });
}
