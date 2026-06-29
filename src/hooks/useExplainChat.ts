"use client";

import { useMutation } from "@tanstack/react-query";
import type { ExplainChatMessage } from "@/lib/llm/client";
import { useI18n } from "@/lib/i18n/context";

export function useExplainChat() {
  const { locale } = useI18n();
  return useMutation({
    mutationFn: async (args: {
      sparql: string;
      messages: ExplainChatMessage[];
    }): Promise<{ reply: string; intent?: string }> => {
      const res = await fetch("/api/explain/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...args, language: locale }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: "Request failed" }));
        throw new Error((data as { error?: string }).error ?? `HTTP ${res.status}`);
      }
      return res.json() as Promise<{ reply: string }>;
    },
  });
}
