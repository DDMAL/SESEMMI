"use client";

import type { SparqlResults } from "@/lib/sparql/virtuoso";

interface ResultsTableProps {
  data: SparqlResults | null;
  isError: boolean;
  error: Error | null;
  isPending: boolean;
}

function ResultsShell({
  action,
  children,
}: {
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-1 flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-widest text-slate-600">Results</span>
        {action}
      </div>
      {children}
    </div>
  );
}

function SkeletonRow({ cols }: { cols: number }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div
            className="h-3 animate-pulse rounded"
            style={{ width: `${60 + ((i * 23) % 40)}%`, background: "rgba(99,102,241,0.1)" }}
          />
        </td>
      ))}
    </tr>
  );
}

export function ResultsTable({ data, isError, error, isPending }: ResultsTableProps) {
  if (isPending) {
    return (
      <ResultsShell
        action={
          <div
            className="h-5 w-20 animate-pulse rounded-full"
            style={{ background: "rgba(99,102,241,0.1)" }}
          />
        }
      >
        <div
          className="flex-1 overflow-hidden rounded-xl"
          style={{ border: "1px solid rgba(99,102,241,0.12)" }}
        >
          <table className="w-full text-sm">
            <thead style={{ background: "rgba(99,102,241,0.05)" }}>
              <tr>
                {[40, 55, 35].map((w, i) => (
                  <th key={i} className="px-4 py-3 text-left">
                    <div
                      className="h-3 animate-pulse rounded"
                      style={{ width: `${w}%`, background: "rgba(99,102,241,0.12)" }}
                    />
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 4 }, (_, i) => (
                <SkeletonRow key={i} cols={3} />
              ))}
            </tbody>
          </table>
        </div>
      </ResultsShell>
    );
  }

  if (isError && error) {
    return (
      <ResultsShell>
        <div
          className="flex items-start gap-3 rounded-xl p-4 text-sm"
          style={{ background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)" }}
        >
          <svg
            aria-hidden="true"
            className="mt-0.5 h-4 w-4 shrink-0 text-red-500"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <div>
            <p className="font-medium text-red-700">Query failed</p>
            <p className="mt-0.5 text-red-500">{error.message}</p>
          </div>
        </div>
      </ResultsShell>
    );
  }

  if (!data) {
    return (
      <ResultsShell>
        <div className="flex flex-1 flex-col items-center justify-center gap-3 text-center">
          <svg
            aria-hidden="true"
            className="h-10 w-10 text-indigo-200"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9 9l10.5-3m0 6.553v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 11-.99-3.467l2.31-.66a2.25 2.25 0 001.632-2.163zm0 0V2.25L9 5.25v10.303m0 0v3.75a2.25 2.25 0 01-1.632 2.163l-1.32.377a1.803 1.803 0 01-.99-3.467l2.31-.66A2.25 2.25 0 009 15.553z"
            />
          </svg>
          <p className="text-sm text-slate-400">Run a query to explore music metadata</p>
        </div>
      </ResultsShell>
    );
  }

  const { vars } = data.head;
  const { bindings } = data.results;

  if (bindings.length === 0) {
    return (
      <ResultsShell>
        <div
          className="flex items-center gap-2 rounded-xl px-4 py-3 text-sm text-amber-700"
          style={{ background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)" }}
        >
          <svg
            aria-hidden="true"
            className="h-4 w-4 shrink-0"
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
          Query returned 0 results
        </div>
      </ResultsShell>
    );
  }

  return (
    <ResultsShell
      action={
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-medium text-indigo-600"
          style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)" }}
        >
          {bindings.length} {bindings.length === 1 ? "row" : "rows"}
        </span>
      }
    >
      <div
        className="flex-1 overflow-auto rounded-xl"
        style={{ border: "1px solid rgba(99,102,241,0.12)" }}
      >
        <table className="w-full text-left text-sm">
          <thead
            className="sticky top-0"
            style={{ background: "rgba(238,240,255,0.9)", backdropFilter: "blur(12px)" }}
          >
            <tr>
              {vars.map((v) => (
                <th
                  key={v}
                  className="whitespace-nowrap px-4 py-2.5 font-mono text-xs font-semibold text-indigo-500"
                >
                  ?{v}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {bindings.map((row, i) => (
              <tr
                key={i}
                className="transition-colors"
                style={{ borderTop: "1px solid rgba(99,102,241,0.07)" }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLTableRowElement).style.background =
                    "rgba(99,102,241,0.04)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLTableRowElement).style.background = "";
                }}
              >
                {vars.map((v) => {
                  const val = row[v]?.value ?? "";
                  return (
                    <td
                      key={v}
                      className="max-w-xs truncate px-4 py-2.5 text-slate-600"
                      title={val}
                    >
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </ResultsShell>
  );
}
