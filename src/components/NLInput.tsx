"use client";

import { useState } from "react";
import { Spinner } from "@/components/Spinner";

interface NLInputProps {
  onTranslate: (query: string) => void;
  isPending: boolean;
}

export function NLInput({ onTranslate, isPending }: NLInputProps) {
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
    </div>
  );
}
