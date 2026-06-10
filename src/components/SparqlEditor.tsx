"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useExplain } from "@/hooks/useExplain";
import { useExplainChat } from "@/hooks/useExplainChat";
import type { ExplainChatMessage } from "@/lib/llm/client";
import { EditorView, keymap, placeholder } from "@codemirror/view";
import { EditorState, Compartment } from "@codemirror/state";
import { defaultKeymap, history, historyKeymap } from "@codemirror/commands";
import { linter, type Diagnostic } from "@codemirror/lint";
import { Parser } from "sparqljs";
import { sparqlLanguageSupport, sparqlSyntaxHighlighting } from "@/lib/sparql/codemirror-sparql";
import { Spinner } from "@/components/Spinner";
import { validateSparql, formatSparqlError } from "@/lib/sparql/validate";

interface LastValidated {
  value: string;
  result: { valid: boolean; error?: string };
}

interface SparqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  onExecute: () => void;
  isPending: boolean;
  /** Original NL query that produced this SPARQL (from flow.messages). */
  originalQuery?: string;
  /** Called when the user wants to regenerate SPARQL with chat refinements. */
  onRefine?: (query: string, refinements: string[]) => void;
}

const EDITOR_THEME = EditorView.theme({
  "&": {
    background: "rgba(248,250,255,0.8)",
    border: "1px solid rgba(99,102,241,0.15)",
    borderRadius: "0.75rem",
    fontSize: "0.875rem",
    fontFamily: "var(--font-geist-mono), ui-monospace, SFMono-Regular, monospace",
    minHeight: "22rem",
  },
  "&.cm-focused": {
    outline: "none",
    boxShadow: "0 0 0 2px rgba(99,102,241,0.4)",
  },
  ".cm-scroller": {
    fontFamily: "inherit",
    lineHeight: "1.6",
  },
  ".cm-content": {
    padding: "0.75rem 1rem",
    caretColor: "#4f46e5",
  },
  ".cm-line": {
    padding: "0",
  },
  ".cm-placeholder": {
    color: "#94a3b8",
  },
  ".cm-cursor": {
    borderLeftColor: "#4f46e5",
  },
  ".cm-lintRange-error": {
    backgroundImage: "none",
    borderBottom: "2px solid rgba(239,68,68,0.7)",
  },
  ".cm-tooltip.cm-tooltip-lint": {
    background: "rgba(254,242,242,0.97)",
    border: "1px solid rgba(239,68,68,0.22)",
    borderRadius: "0.5rem",
    color: "#b91c1c",
    fontSize: "0.75rem",
    padding: "0.375rem 0.625rem",
    backdropFilter: "blur(8px)",
  },
});

function sparqlLinterSource(view: EditorView): Diagnostic[] {
  const doc = view.state.doc.toString();
  if (!doc.trim()) return [];
  try {
    new Parser().parse(doc);
    return [];
  } catch (err) {
    const message = formatSparqlError(err);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const offset: number | undefined = (err as any)?.location?.start?.offset;
    let from: number;
    let to: number;
    if (typeof offset === "number") {
      from = offset;
      const lineEnd = doc.indexOf("\n", from);
      to = lineEnd === -1 ? doc.length : lineEnd;
      if (to <= from) to = Math.min(from + 1, doc.length);
    } else {
      const lineMatch = /Parse error on line (\d+)/.exec(err instanceof Error ? err.message : "");
      if (lineMatch) {
        try {
          const line = view.state.doc.line(parseInt(lineMatch[1], 10));
          from = line.from;
          to = line.to;
        } catch {
          from = 0;
          to = doc.length;
        }
      } else {
        from = 0;
        to = doc.length;
      }
    }
    return [{ from, to, severity: "error", message }];
  }
}

type ChatEntry = ExplainChatMessage & { id: number };

export function SparqlEditor({
  value,
  onChange,
  onExecute,
  isPending,
  originalQuery,
  onRefine,
}: SparqlEditorProps) {
  const [lastValidated, setLastValidated] = useState<LastValidated | null>(null);
  const [isErrorExpanded, setIsErrorExpanded] = useState(true);
  const explain = useExplain();
  const explainChat = useExplainChat();

  const [chatMessages, setChatMessages] = useState<ChatEntry[]>([]);
  const [chatInput, setChatInput] = useState("");
  const chatIdRef = useRef(0);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  const isMac = typeof navigator !== "undefined" && /mac/i.test(navigator.userAgent);

  // Debounced validation
  useEffect(() => {
    if (!value.trim()) return;
    const timer = setTimeout(() => {
      const result = validateSparql(value);
      setLastValidated({ value, result });
      if (!result.valid) setIsErrorExpanded(true);
    }, 600);
    return () => clearTimeout(timer);
  }, [value]);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const validation =
    !value.trim() || lastValidated?.value !== value
      ? ("idle" as const)
      : lastValidated.result.valid
        ? ("valid" as const)
        : ("invalid" as const);

  const error = validation === "invalid" ? (lastValidated?.result.error ?? "Invalid SPARQL") : "";
  const isInvalid = validation === "invalid";

  const onChangeRef = useRef(onChange);
  const onExecuteRef = useRef(onExecute);
  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);
  useEffect(() => {
    onExecuteRef.current = onExecute;
  }, [onExecute]);

  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const readOnlyComp = useMemo(() => new Compartment(), []);

  // Mount CodeMirror once
  useEffect(() => {
    if (!containerRef.current) return;
    const view = new EditorView({
      state: EditorState.create({
        doc: value,
        extensions: [
          sparqlLanguageSupport(),
          sparqlSyntaxHighlighting,
          history(),
          keymap.of([
            {
              key: "Ctrl-Enter",
              run: () => {
                if (!isPendingRef.current) onExecuteRef.current();
                return true;
              },
            },
            {
              key: "Mod-Enter",
              run: () => {
                if (!isPendingRef.current) onExecuteRef.current();
                return true;
              },
            },
            ...historyKeymap,
            ...defaultKeymap,
          ]),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              onChangeRef.current(update.state.doc.toString());
            }
          }),
          linter(sparqlLinterSource, { delay: 600 }),
          readOnlyComp.of(EditorState.readOnly.of(false)),
          placeholder(
            "SELECT ?subject ?predicate ?object\nWHERE {\n  ?subject ?predicate ?object\n}\nLIMIT 25",
          ),
          EDITOR_THEME,
          EditorView.lineWrapping,
        ],
      }),
      parent: containerRef.current,
    });
    viewRef.current = view;
    return () => view.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const isPendingRef = useRef(isPending);
  useEffect(() => {
    isPendingRef.current = isPending;
  }, [isPending]);

  // Sync external value in
  useEffect(() => {
    const view = viewRef.current;
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== value) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: value } });
    }
  }, [value]);

  // Toggle readOnly
  useEffect(() => {
    viewRef.current?.dispatch({
      effects: readOnlyComp.reconfigure(EditorState.readOnly.of(isPending)),
    });
  }, [isPending, readOnlyComp]);

  const handleExplain = () => {
    setChatMessages([]);
    explain.mutate(value, {
      onSuccess: (data) => {
        setChatMessages([
          { id: chatIdRef.current++, role: "assistant", content: data.explanation },
        ]);
      },
    });
  };

  const handleChatSend = () => {
    const text = chatInput.trim();
    if (!text || explainChat.isPending) return;
    const userMsg: ChatEntry = { id: chatIdRef.current++, role: "user", content: text };
    const updated = [...chatMessages, userMsg];
    setChatMessages(updated);
    setChatInput("");
    explainChat.mutate(
      { sparql: value, messages: updated.map(({ role, content }) => ({ role, content })) },
      {
        onSuccess: (data) => {
          setChatMessages((prev) => [
            ...prev,
            { id: chatIdRef.current++, role: "assistant", content: data.reply },
          ]);
        },
      },
    );
  };

  const handleRefine = () => {
    const userMessages = chatMessages.filter((m) => m.role === "user").map((m) => m.content);
    onRefine?.(originalQuery ?? "", userMessages);
  };

  return (
    <div className="flex flex-col gap-3">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <label className="text-xs font-semibold uppercase tracking-widest text-slate-600">
          SPARQL Editor
        </label>
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

      {/* Side-by-side: editor (60%) + chat panel (40%) */}
      <div className="flex items-stretch gap-3">
        {/* Editor */}
        <div
          className={`relative min-w-0 flex-[3] transition-opacity ${isPending ? "opacity-50" : ""} ${isInvalid ? "editor-invalid" : ""}`}
        >
          <div ref={containerRef} />

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

          {validation === "invalid" && (
            <div className="absolute bottom-3 left-3 right-3 flex flex-row-reverse items-end gap-1.5">
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

        {/* Explanation / chat panel */}
        <div
          className="flex min-h-[22rem] min-w-0 flex-[2] flex-col rounded-xl p-4 text-sm"
          style={{
            background: "rgba(248,250,255,0.8)",
            border: "1px solid rgba(99,102,241,0.15)",
          }}
        >
          {/* Panel header */}
          <div className="mb-3 flex items-center justify-between">
            <p className="text-[10px] font-semibold uppercase tracking-widest text-indigo-400">
              Explanation
            </p>
            <button
              onClick={handleExplain}
              disabled={explain.isPending || !value.trim()}
              className="cursor-pointer text-xs text-indigo-400 underline transition-colors hover:text-indigo-600 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {explain.isPending
                ? "Explaining…"
                : chatMessages.length > 0
                  ? "Re-explain"
                  : "Explain"}
            </button>
          </div>

          {/* Empty state */}
          {!value.trim() && chatMessages.length === 0 && !explain.isPending && (
            <p className="mt-6 text-center text-xs text-slate-400">
              Write or generate a SPARQL query to see an explanation here.
            </p>
          )}

          {/* Prompt to explain */}
          {value.trim() && chatMessages.length === 0 && !explain.isPending && !explain.isError && (
            <p className="mt-6 text-center text-xs text-slate-400">
              Click{" "}
              <button
                onClick={handleExplain}
                className="cursor-pointer text-indigo-400 underline hover:text-indigo-600"
              >
                Explain
              </button>{" "}
              to understand this query.
            </p>
          )}

          {/* Explain spinner (first load) */}
          {explain.isPending && chatMessages.length === 0 && (
            <div className="mt-6 flex items-center gap-2 text-slate-400">
              <Spinner />
              <span>Explaining…</span>
            </div>
          )}

          {/* Explain error (no messages yet) */}
          {explain.isError && !explain.isPending && chatMessages.length === 0 && (
            <p className="mt-2 text-xs text-red-600">
              {explain.error?.message ?? "Explanation failed"}
            </p>
          )}

          {/* Chat bubble list */}
          {chatMessages.length > 0 && (
            <div className="flex flex-1 flex-col gap-2 overflow-y-auto">
              {chatMessages.map((msg) => (
                <div
                  key={msg.id}
                  className={`rounded-lg px-3 py-2 text-xs leading-relaxed ${
                    msg.role === "assistant"
                      ? "bg-indigo-50/70 text-slate-700"
                      : "ml-6 bg-white/70 text-slate-600"
                  }`}
                >
                  {msg.content}
                </div>
              ))}
              {explainChat.isPending && (
                <div className="flex items-center gap-2 text-xs text-slate-400">
                  <Spinner />
                  <span>Thinking…</span>
                </div>
              )}
              <div ref={chatBottomRef} />
            </div>
          )}

          {/* Chat input + Regenerate — only after first explanation */}
          {chatMessages.length > 0 && (
            <div className="mt-3 flex flex-col gap-2 border-t border-indigo-50/80 pt-2">
              <div className="flex gap-2">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleChatSend();
                    }
                  }}
                  placeholder="Ask about this query…"
                  disabled={explainChat.isPending}
                  className="flex-1 rounded-lg border border-indigo-100 bg-white/60 px-2.5 py-1.5 text-xs outline-none placeholder:text-slate-300 focus:border-indigo-300 focus:ring-1 focus:ring-indigo-200/50 disabled:opacity-50"
                />
                <button
                  onClick={handleChatSend}
                  disabled={explainChat.isPending || !chatInput.trim()}
                  className="cursor-pointer rounded-lg px-2.5 py-1.5 text-xs font-medium text-white transition-all hover:brightness-110 disabled:opacity-40"
                  style={{ background: "linear-gradient(135deg, #6366f1, #4f46e5)" }}
                >
                  Send
                </button>
              </div>
              {onRefine && chatMessages.some((m) => m.role === "user") && (
                <button
                  onClick={handleRefine}
                  disabled={explainChat.isPending}
                  className="cursor-pointer rounded-lg border border-indigo-200 px-3 py-1.5 text-xs font-medium text-indigo-600 transition-all hover:bg-indigo-50 disabled:opacity-40"
                >
                  Regenerate SPARQL with these refinements ↑
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
