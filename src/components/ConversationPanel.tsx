"use client";

import { useState } from "react";
import { Spinner } from "@/components/Spinner";
import { StepsPanel } from "@/components/StepsPanel";
import type { ChatMessage, ClarifyFlow } from "@/hooks/useClarifyFlow";

interface ConversationPanelProps {
  flow: ClarifyFlow;
}

function Bubble({
  message,
  showChips,
  onChip,
}: {
  message: ChatMessage;
  showChips: boolean;
  onChip: (text: string) => void;
}) {
  const isUser = message.role === "user";

  if (message.kind === "info") {
    return <p className="px-1 text-center text-[11px] italic text-slate-400">{message.text}</p>;
  }

  return (
    <div className={`flex flex-col gap-1.5 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className="max-w-[85%] rounded-2xl px-3.5 py-2 text-sm"
        style={
          isUser
            ? {
                background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
                color: "white",
                borderBottomRightRadius: 4,
              }
            : {
                background: "rgba(255,255,255,0.85)",
                color: "#334155",
                border: "1px solid rgba(99,102,241,0.15)",
                borderBottomLeftRadius: 4,
              }
        }
      >
        {message.text}
      </div>
      {showChips && message.options && message.options.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.options.map((opt) => (
            <button
              key={opt}
              onClick={() => onChip(opt)}
              className="cursor-pointer rounded-full px-3 py-1 text-xs font-medium text-indigo-600 transition-all hover:brightness-105"
              style={{
                background: "rgba(99,102,241,0.08)",
                border: "1px solid rgba(99,102,241,0.3)",
              }}
            >
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export function ConversationPanel({ flow }: ConversationPanelProps) {
  const [text, setText] = useState("");
  const { messages, phase, isPending, awaitingAnswer, steps } = flow;

  const isTranslating = phase === "translating";
  const hasConversation = messages.length > 0;

  const handleSubmit = () => {
    if (!text.trim() || isTranslating) return;
    flow.submit(text.trim());
    setText("");
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
        <div className="flex items-center gap-2">
          {phase === "clarifying" && (
            <button
              onClick={flow.generateNow}
              disabled={isPending}
              className="cursor-pointer rounded-xl px-3 py-1.5 text-xs font-medium text-indigo-600 transition-all hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-40"
              style={{
                background: "rgba(99,102,241,0.08)",
                border: "1px solid rgba(99,102,241,0.3)",
              }}
            >
              Generate now
            </button>
          )}
          {hasConversation && (phase === "done" || phase === "clarifying") && (
            <button
              onClick={flow.reset}
              className="cursor-pointer rounded-xl px-3 py-1.5 text-xs font-medium text-slate-500 transition-all hover:text-slate-700"
              style={{ border: "1px solid rgba(99,102,241,0.2)" }}
            >
              New
            </button>
          )}
        </div>
      </div>

      {hasConversation && (
        <div className="flex max-h-72 flex-col gap-3 overflow-y-auto pr-1">
          {messages.map((m, i) => (
            <Bubble
              key={m.id}
              message={m}
              showChips={awaitingAnswer && i === messages.length - 1 && m.kind === "question"}
              onChip={flow.answer}
            />
          ))}
        </div>
      )}

      <div className="flex items-center gap-2">
        <div className="relative flex-1">
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
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
            placeholder={
              awaitingAnswer
                ? "Type your answer, or pick an option above…"
                : "Find the birth place of the composer with the most compositions in RISM"
            }
            className="w-full rounded-xl py-2.5 pl-9 pr-3 text-sm text-slate-700 placeholder:text-slate-400 transition-all focus:outline-none focus:ring-2 focus:ring-indigo-400/40 disabled:opacity-50"
            style={{
              background: "rgba(255,255,255,0.7)",
              border: "1px solid rgba(99,102,241,0.2)",
            }}
            disabled={isTranslating}
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={isPending || !text.trim()}
          aria-label={awaitingAnswer ? "Send answer" : "Translate to SPARQL"}
          className="flex cursor-pointer items-center gap-1.5 rounded-xl px-4 py-2.5 text-sm font-medium text-white transition-all hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          style={{ background: "linear-gradient(135deg, #4f46e5, #7c3aed)" }}
        >
          {isPending ? (
            <>
              <Spinner />
              <span>{isTranslating ? "Generating" : "Thinking"}</span>
            </>
          ) : (
            <span>{awaitingAnswer ? "Send" : "Generate"}</span>
          )}
        </button>
      </div>

      <StepsPanel steps={steps} isPending={isPending} />
    </div>
  );
}
