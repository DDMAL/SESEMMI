"use client";

import { useState } from "react";
import { Spinner } from "@/components/Spinner";
import type { Step, StepStatus } from "@/hooks/useTranslate";

interface NLInputProps {
  onTranslate: (query: string) => void;
  isPending: boolean;
  steps?: Step[];
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "running") return <Spinner className="h-3 w-3 shrink-0 text-indigo-400" />;
  if (status === "done")
    return (
      <svg
        aria-hidden="true"
        className="h-3 w-3 shrink-0 text-emerald-500"
        viewBox="0 0 20 20"
        fill="currentColor"
      >
        <path
          fillRule="evenodd"
          d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z"
          clipRule="evenodd"
        />
      </svg>
    );
  if (status === "error")
    return <span className="h-3 w-3 shrink-0 text-center text-[10px] leading-none text-red-400">✕</span>;
  return <span className="h-3 w-3 shrink-0 rounded-full border border-slate-300" />;
}

export function NLInput({ onTranslate, isPending, steps = [] }: NLInputProps) {
  const [query, setQuery] = useState("");

  const handleSubmit = () => {
    if (query.trim()) {
      onTranslate(query.trim());
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <label
          htmlFor="nl-input"
          className="text-xs font-semibold uppercase tracking-widest text-slate-600"
        >
          Natural Language
        </label>
        <button
          onClick={handleSubmit}
          disabled={isPending || !query.trim()}
          aria-label="Translate to SPARQL"
          className="flex cursor-pointer items-center gap-1.5 rounded-xl px-4 py-1.5 text-sm font-medium text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}
        >
          {isPending ? (
            <>
              <Spinner />
              <span>Translating</span>
            </>
          ) : (
            <>
              <svg
                aria-hidden="true"
                className="h-3.5 w-3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
                />
              </svg>
              <span>Translate</span>
              <span className="ml-0.5 text-xs text-indigo-200">↵</span>
            </>
          )}
        </button>
      </div>

      <div className="relative">
        <svg
          aria-hidden="true"
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 15.803a7.5 7.5 0 0010.607 10.607z"
          />
        </svg>
        <input
          id="nl-input"
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          placeholder='e.g. "Find all jazz albums released in Montreal"'
          className="w-full rounded-xl py-2.5 pl-9 pr-3 text-sm text-slate-700 placeholder:text-slate-400 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-400/40 disabled:opacity-50"
          style={{ background: "rgba(255,255,255,0.7)", border: "1px solid rgba(99,102,241,0.2)" }}
          disabled={isPending}
        />
      </div>

      {steps.length > 0 && (
        <div
          className="overflow-hidden rounded-xl"
          style={{ background: "rgba(79,70,229,0.04)", border: "1px solid rgba(99,102,241,0.15)" }}
        >
          <div
            className="flex items-center px-3 py-1.5"
            style={{ borderBottom: "1px solid rgba(99,102,241,0.1)" }}
          >
            <span className="text-[10px] font-semibold uppercase tracking-widest text-indigo-400">
              {isPending ? "Processing…" : "Done"}
            </span>
          </div>
          <div className="divide-y divide-indigo-50">
            {steps.map((s) => (
              <div key={s.step} className="flex items-start gap-2.5 px-3 py-2">
                <div className="mt-0.5 flex h-3.5 w-3.5 shrink-0 items-center justify-center">
                  <StepIcon status={s.status} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs font-medium text-slate-700">{s.label}</span>
                    {s.detail && (
                      <span className="text-[11px] text-slate-400">{s.detail}</span>
                    )}
                  </div>
                  {s.step === "generate" && s.tokens && (
                    <pre className="mt-1.5 max-h-36 overflow-y-auto font-mono text-[10px] leading-relaxed whitespace-pre-wrap break-all text-slate-500">
                      {s.tokens}
                      {s.status === "running" && (
                        <span className="animate-pulse text-indigo-400">▋</span>
                      )}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
