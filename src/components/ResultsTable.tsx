"use client";

import { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import type { SparqlResults } from "@/lib/sparql/virtuoso";
import { EntityDetail } from "@/components/EntityDetail";
import { extractQid, fetchLabels } from "@/lib/wikidata";

interface ResultsTableProps {
  data: SparqlResults | null;
  isError: boolean;
  error: Error | null;
  isPending: boolean;
}

type Binding = { type: string; value: string } | undefined;

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
        <span className="text-xs font-semibold tracking-widest text-slate-600 uppercase">
          Results
        </span>
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

function formatVar(v: string): string {
  return v
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function shortenUri(uri: string): string {
  const frag = uri.split("#").pop();
  if (frag && frag !== uri) return frag;
  const seg = uri.replace(/\/+$/, "").split("/").pop();
  return seg || uri;
}

function Cell({
  binding,
  labels,
  onSelectQid,
}: {
  binding: Binding;
  labels: Record<string, string>;
  onSelectQid: (qid: string) => void;
}) {
  const value = binding?.value ?? "";
  if (!value) return <span className="text-slate-300">—</span>;

  if (binding?.type === "uri") {
    const qid = extractQid(value);
    if (qid) {
      return (
        <button
          onClick={() => onSelectQid(qid)}
          title={value}
          className="inline-flex max-w-full cursor-pointer items-center gap-0.5 truncate text-left font-medium text-indigo-600 transition-colors hover:text-indigo-700 hover:underline"
        >
          <span className="truncate">{labels[qid] ?? qid}</span>
          <span aria-hidden="true" className="shrink-0 text-indigo-300">
            ↗
          </span>
        </button>
      );
    }
    return (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        title={value}
        className="inline-flex max-w-full items-center gap-0.5 truncate text-indigo-500 transition-colors hover:text-indigo-600 hover:underline"
      >
        <span className="truncate">{shortenUri(value)}</span>
        <span aria-hidden="true" className="shrink-0 text-indigo-300">
          ↗
        </span>
      </a>
    );
  }

  return (
    <span className="text-slate-600" title={value}>
      {value}
    </span>
  );
}

export function ResultsTable({ data, isError, error, isPending }: ResultsTableProps) {
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [selectedQid, setSelectedQid] = useState<string | null>(null);
  const [prevData, setPrevData] = useState(data);

  // Reset the open detail tab when a new result set arrives (render-time pattern).
  if (data !== prevData) {
    setPrevData(data);
    setSelectedQid(null);
  }

  // Collect every Wikidata QID across all cells of the current result set.
  const qids = useMemo(() => {
    if (!data) return [] as string[];
    const set = new Set<string>();
    for (const row of data.results.bindings) {
      for (const v of Object.values(row)) {
        if (v?.type === "uri") {
          const q = extractQid(v.value);
          if (q) set.add(q);
        }
      }
    }
    return [...set];
  }, [data]);

  // Prefetch their labels once per result set (labels are keyed by QID, so
  // entries left from a prior query are harmless and simply ignored).
  useEffect(() => {
    if (qids.length === 0) return;
    let active = true;
    fetchLabels(qids)
      .then((m) => active && setLabels(m))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [qids]);

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
        className="relative flex-1 overflow-hidden rounded-xl"
        style={{ border: "1px solid rgba(99,102,241,0.12)" }}
      >
        <div className="h-full overflow-auto">
          <table className="w-full text-left text-sm">
            <thead
              className="sticky top-0 z-[1]"
              style={{ background: "rgba(238,240,255,0.9)", backdropFilter: "blur(12px)" }}
            >
              <tr>
                {vars.map((v) => (
                  <th
                    key={v}
                    className="px-4 py-2.5 text-xs font-semibold whitespace-nowrap text-indigo-500"
                  >
                    {formatVar(v)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bindings.map((row, i) => {
                const base = i % 2 === 1 ? "rgba(99,102,241,0.025)" : "transparent";
                return (
                  <tr
                    key={i}
                    style={{ borderTop: "1px solid rgba(99,102,241,0.07)", background: base }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "rgba(99,102,241,0.06)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = base;
                    }}
                  >
                    {vars.map((v) => (
                      <td key={v} className="max-w-xs truncate px-4 py-2.5">
                        <Cell binding={row[v]} labels={labels} onSelectQid={setSelectedQid} />
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {selectedQid &&
          createPortal(
            <EntityDetail
              key={selectedQid}
              qid={selectedQid}
              onClose={() => setSelectedQid(null)}
            />,
            document.body,
          )}
      </div>
    </ResultsShell>
  );
}
