"use client";

import { useEffect, useRef, useState } from "react";
import { ConversationPanel } from "@/components/ConversationPanel";
import { SparqlEditor } from "@/components/SparqlEditor";
import { ResultsTable } from "@/components/ResultsTable";
import { LanguageSwitcher } from "@/components/LanguageSwitcher";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useClarifyFlow } from "@/hooks/useClarifyFlow";
import { useExecuteSparql } from "@/hooks/useExecuteSparql";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";
import { useI18n } from "@/lib/i18n/context";

const glassPanel = {
  background: "var(--surface-glass)",
  backdropFilter: "blur(20px)",
  border: "1px solid var(--border-glass)",
  boxShadow: "var(--shadow-glass)",
} as const;

export default function Home() {
  const { t } = useI18n();
  const [sparql, setSparql] = useState("");
  const flow = useClarifyFlow({ onSparql: setSparql, onStart: () => setSparql("") });
  const execute = useExecuteSparql();
  const conversationRef = useRef<HTMLElement>(null);
  const [highlightNL, setHighlightNL] = useState(false);
  const reducedMotion = usePrefersReducedMotion();

  useEffect(() => {
    if (!highlightNL) return;
    const t = setTimeout(() => setHighlightNL(false), 1500);
    return () => clearTimeout(t);
  }, [highlightNL]);

  const handleExecute = () => {
    if (sparql.trim()) {
      execute.mutate(sparql);
    }
  };

  const isRunning = execute.isPending || flow.isPending;

  return (
    <div
      className="relative flex h-screen min-h-screen flex-col overflow-hidden"
      style={{ background: "var(--bg-gradient)" }}
    >
      {/* Ambient pastel orbs */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full"
        style={{
          background: "radial-gradient(circle, var(--orb-1) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-1/3 -right-24 h-80 w-80 rounded-full"
        style={{
          background: "radial-gradient(circle, var(--orb-2) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 left-1/3 h-72 w-72 rounded-full"
        style={{
          background: "radial-gradient(circle, var(--orb-3) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      {/* Header */}
      <header
        className="sticky top-0 z-10 flex items-center justify-between gap-3 px-4 py-2.5 sm:px-6 sm:py-3"
        style={{
          background: "var(--header-bg)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--header-border)",
        }}
      >
        <div className="flex min-w-0 items-center gap-3">
          <svg
            aria-hidden="true"
            className="h-5 w-5 shrink-0 text-indigo-500"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z"
            />
          </svg>
          <span className="truncate text-sm font-semibold tracking-wide text-slate-700">
            {t("app.title")}
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <ThemeToggle />
          <LanguageSwitcher />
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 rounded-full ${
                isRunning ? "bg-amber-400 animate-pulse" : "bg-emerald-500"
              }`}
            />
            <span className="text-xs text-slate-400">
              {isRunning ? t("app.status.running") : t("app.status.ready")}
            </span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex flex-1 flex-col gap-4 overflow-y-auto p-4 lg:p-6">
        {/* Conversation glass panel */}
        <section ref={conversationRef} className="rounded-2xl p-5" style={glassPanel}>
          <ConversationPanel flow={flow} highlight={highlightNL} />
          {flow.error && <p className="mt-2 text-xs text-red-500">{flow.error.message}</p>}
        </section>

        {/* SPARQL Editor glass panel */}
        <section className="flex flex-col rounded-2xl p-5" style={glassPanel}>
          <SparqlEditor
            value={sparql}
            onChange={setSparql}
            onExecute={handleExecute}
            isPending={execute.isPending}
            originalQuery={flow.messages.find((m) => m.kind === "query")?.text}
            onRefine={(query, refinements) => {
              setSparql("");
              conversationRef.current?.scrollIntoView({
                behavior: reducedMotion ? "auto" : "smooth",
                block: "start",
              });
              setHighlightNL(true);
              flow.restart(query, refinements);
            }}
          />
        </section>

        {/* Bottom — Results table full width */}
        <section className="flex flex-1 flex-col rounded-2xl p-5" style={glassPanel}>
          <ResultsTable
            data={execute.data ?? null}
            isError={execute.isError}
            error={execute.error}
            isPending={execute.isPending}
          />
        </section>
      </main>
    </div>
  );
}
