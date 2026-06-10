"use client";

import { useMutation } from "@tanstack/react-query";
import type { ExplainChatMessage } from "@/lib/llm/client";

export function useExplainChat() {
  return useMutation({
    mutationFn: async (args: {
      sparql: string;
      messages: ExplainChatMessage[];
    }): Promise<{ reply: string }> => {
      const res = await fetch("/api/explain/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(args),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error((data as { error?: string }).error ?? `HTTP ${res.status}`);
      }
      return res.json() as Promise<{ reply: string }>;
    },
  });
}
