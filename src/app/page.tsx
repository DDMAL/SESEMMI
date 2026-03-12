"use client";

import { useState } from "react";
import { NLInput } from "@/components/NLInput";
import { SparqlEditor } from "@/components/SparqlEditor";
import { ResultsTable } from "@/components/ResultsTable";
import { useTranslate } from "@/hooks/useTranslate";
import { useExecuteSparql } from "@/hooks/useExecuteSparql";

const glassPanel = {
  background: "rgba(255,255,255,0.65)",
  backdropFilter: "blur(20px)",
  border: "1px solid rgba(255,255,255,0.85)",
  boxShadow: "0 4px 24px rgba(99,102,241,0.08)",
} as const;

export default function Home() {
  const [sparql, setSparql] = useState("");
  const translate = useTranslate();
  const execute = useExecuteSparql();

  const handleTranslate = (query: string) => {
    translate.mutate(query, {
      onSuccess: (data) => setSparql(data.sparql),
    });
  };

  const handleExecute = () => {
    if (sparql.trim()) {
      execute.mutate(sparql);
    }
  };

  const isRunning = execute.isPending || translate.isPending;

  return (
    <div
      className="relative flex min-h-screen flex-col overflow-hidden"
      style={{
        background: "linear-gradient(135deg, #e8eeff 0%, #eef0ff 35%, #eef4ff 65%, #e8edff 100%)",
      }}
    >
      {/* Ambient pastel orbs */}
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 -left-32 h-96 w-96 rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(139,92,246,0.25) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute top-1/3 -right-24 h-80 w-80 rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute bottom-0 left-1/3 h-72 w-72 rounded-full"
        style={{
          background: "radial-gradient(circle, rgba(59,130,246,0.2) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      {/* Header */}
      <header
        className="sticky top-0 z-10 flex items-center justify-between px-6 py-3"
        style={{
          background: "rgba(255,255,255,0.6)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid rgba(99,102,241,0.12)",
        }}
      >
        <div className="flex items-center gap-3">
          <svg
            aria-hidden="true"
            className="h-5 w-5 text-indigo-500"
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
          <span className="text-sm font-semibold tracking-wide text-slate-700">
            Search Engine System for Enhancing Music Metadata Interoperability
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${
              isRunning ? "bg-amber-400 animate-pulse" : "bg-emerald-500"
            }`}
          />
          <span className="text-xs text-slate-400">{isRunning ? "running" : "ready"}</span>
        </div>
      </header>

      {/* Main content */}
      <main className="flex flex-1 flex-col gap-4 p-4 lg:p-6">
        {/* NL Input glass panel */}
        <section className="rounded-2xl p-5" style={glassPanel}>
          <NLInput
            onTranslate={handleTranslate}
            isPending={translate.isPending}
            steps={translate.steps}
          />
          {translate.isError && (
            <p className="mt-2 text-xs text-red-500">{translate.error?.message}</p>
          )}
        </section>

        {/* SPARQL Editor glass panel */}
        <section className="flex flex-col rounded-2xl p-5" style={glassPanel}>
          <SparqlEditor
            value={sparql}
            onChange={setSparql}
            onExecute={handleExecute}
            isPending={execute.isPending}
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
