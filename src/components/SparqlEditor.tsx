"use client";

import { useState, useEffect } from "react";
import { Spinner } from "@/components/Spinner";
import { validateSparql } from "@/lib/sparql/validate";

interface LastValidated {
  value: string;
  result: { valid: boolean; error?: string };
}

interface SparqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  onExecute: () => void;
  isPending: boolean;
}

export function SparqlEditor({ value, onChange, onExecute, isPending }: SparqlEditorProps) {
  // Holds the last value that was actually validated (set only inside async setTimeout)
  const [lastValidated, setLastValidated] = useState<LastValidated | null>(null);
  const [isErrorExpanded, setIsErrorExpanded] = useState(true);

  // typeof guard keeps SSR and client renders in sync — no effect needed for this
  const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.userAgent);

  // Debounce: only setState inside the async callback — no synchronous setState in effect body
  useEffect(() => {
    if (!value.trim()) return;
    const timer = setTimeout(() => {
      const result = validateSparql(value);
      setLastValidated({ value, result });
      if (!result.valid) setIsErrorExpanded(true);
    }, 600);
    return () => clearTimeout(timer);
  }, [value]);

  // Derived display state — no extra setState needed:
  // • empty editor  → idle
  // • still typing  → idle (lastValidated.value is stale)
  // • settled valid → valid
  // • settled invalid → invalid
  const validation =
    !value.trim() || lastValidated?.value !== value
      ? ("idle" as const)
      : lastValidated.result.valid
        ? ("valid" as const)
        : ("invalid" as const);

  const error = validation === "invalid" ? (lastValidated?.result.error ?? "Invalid SPARQL") : "";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (!isPending && value.trim()) {
        onExecute();
      }
    }
  };

  const isInvalid = validation === "invalid";

  const textareaStyle = {
    background: "rgba(248,250,255,0.8)",
    border: isInvalid ? "1px solid rgba(239,68,68,0.5)" : "1px solid rgba(99,102,241,0.15)",
  };

  const focusRingClass = isInvalid ? "focus:ring-red-400/40" : "focus:ring-indigo-400/40";

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <label
          htmlFor="sparql-editor"
          className="text-xs font-semibold uppercase tracking-widest text-slate-600"
        >
          SPARQL Editor
        </label>

        <div className="flex items-center gap-2">
          <button
            onClick={onExecute}
            disabled={isPending || !value.trim()}
            aria-label="Run query"
            className="flex cursor-pointer items-center gap-1.5 rounded-xl px-4 py-1.5 text-sm font-medium text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
            style={{ background: "linear-gradient(135deg, #059669, #0d9488)" }}
          >
            {isPending ? (
              <>
                <Spinner />
                Running
              </>
            ) : (
              <>
                <svg
                  aria-hidden="true"
                  className="h-3.5 w-3.5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M8 5.14v14l11-7-11-7z" />
                </svg>
                <span>Run Query</span>
                <span className="ml-0.5 text-xs text-indigo-200">{isMac ? "⌘" : "Ctrl"} ↵</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Textarea with overlaid validation indicators */}
      <div className="relative">
        <textarea
          id="sparql-editor"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={14}
          className={`w-full resize-none rounded-xl px-4 py-3 font-mono text-sm text-slate-700 placeholder:text-slate-400 transition-all focus:outline-none focus:ring-2 ${focusRingClass} disabled:opacity-50`}
          style={textareaStyle}
          placeholder={
            "SELECT ?subject ?predicate ?object\nWHERE {\n  ?subject ?predicate ?object\n}\nLIMIT 25"
          }
          spellCheck={false}
          disabled={isPending}
        />

        {/* Valid badge — bottom-right corner inside the textarea */}
        {validation === "valid" && (
          <div
            className="pointer-events-none absolute bottom-3 right-3 transition-opacity duration-200"
            aria-hidden="true"
          >
            <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-white shadow-sm">
              <svg
                className="h-3 w-3"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
          </div>
        )}

        {/* Error tab card — spans full bottom, X badge at right, card fills left */}
        {validation === "invalid" && (
          <div className="absolute bottom-3 left-3 right-3 flex flex-row-reverse items-end gap-1.5">
            {/* X badge — DOM-first = rightmost in flex-row-reverse */}
            <button
              type="button"
              onClick={() => setIsErrorExpanded((v) => !v)}
              aria-expanded={isErrorExpanded}
              aria-label={isErrorExpanded ? "Hide error" : "Show error"}
              className="flex h-5 w-5 shrink-0 cursor-pointer items-center justify-center rounded-full text-white shadow-md ring-2 ring-red-500/20 transition-all hover:ring-red-500/40"
              style={{ background: "linear-gradient(135deg, #f87171, #ef4444)" }}
            >
              <svg
                className="h-3 w-3"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Card — fills remaining width, expands horizontally from the right */}
            <div
              style={{
                width: isErrorExpanded ? "calc(100% - 26px)" : "0",
                flexShrink: 0,
                overflow: "hidden",
                transition: "width 220ms cubic-bezier(0.4, 0, 0.2, 1)",
              }}
            >
              <div
                className="flex w-full items-center gap-2 rounded-xl px-3 py-2.5 text-xs"
                style={{
                  background:
                    "linear-gradient(135deg, rgba(254,226,226,0.97), rgba(254,242,242,0.97))",
                  border: "1px solid rgba(239,68,68,0.22)",
                  backdropFilter: "blur(8px)",
                }}
                role="alert"
                aria-live="polite"
              >
                <svg
                  aria-hidden="true"
                  className="h-3.5 w-3.5 shrink-0 text-red-400"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                  />
                </svg>
                <span className="font-medium text-red-700">{error}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
