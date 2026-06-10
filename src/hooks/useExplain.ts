import { useMutation } from "@tanstack/react-query";

export function useExplain() {
  return useMutation({
    mutationFn: async (sparql: string): Promise<{ explanation: string }> => {
      const res = await fetch("/api/explain", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sparql }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error((data as { error?: string }).error ?? `HTTP ${res.status}`);
      }
      return res.json() as Promise<{ explanation: string }>;
    },
  });
}
