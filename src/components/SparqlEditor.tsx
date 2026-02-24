"use client";

import { Spinner } from "@/components/Spinner";

interface SparqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  onExecute: () => void;
  isPending: boolean;
}

export function SparqlEditor({ value, onChange, onExecute, isPending }: SparqlEditorProps) {
  const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.platform);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (!isPending && value.trim()) {
        onExecute();
      }
    }
  };

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

      <textarea
        id="sparql-editor"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        rows={14}
        className="w-full resize-none rounded-xl px-4 py-3 font-mono text-sm text-slate-700 placeholder:text-slate-400 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-400/40 disabled:opacity-50"
        style={{ background: "rgba(248,250,255,0.8)", border: "1px solid rgba(99,102,241,0.15)" }}
        placeholder={
          "SELECT ?subject ?predicate ?object\nWHERE {\n  ?subject ?predicate ?object\n}\nLIMIT 25"
        }
        spellCheck={false}
        disabled={isPending}
      />
    </div>
  );
}
