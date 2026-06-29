"use client";

import { useMutation } from "@tanstack/react-query";
import type { EntityInfo } from "@/lib/sparql/sparql-hover";
import { useI18n } from "@/lib/i18n/context";

export function useWikidataLabels() {
  const { locale } = useI18n();
  return useMutation({
    mutationFn: async (ids: string[]): Promise<Record<string, EntityInfo>> => {
      if (ids.length === 0) return {};
      const res = await fetch("/api/wikidata", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids, language: locale }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { labels: Record<string, EntityInfo> };
      return data.labels;
    },
  });
}
