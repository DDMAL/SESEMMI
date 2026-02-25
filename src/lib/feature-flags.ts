import { env } from "@/lib/env";

export const flags = {
  /** When true, uses RAG retrieval (@/lib/rag/*) instead of hardcoded examples. */
  useRAG: env.FEATURE_RAG_ENABLED,
} as const;
