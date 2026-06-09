"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useClarify, type ClarifyTurn } from "@/hooks/useClarify";
import { useTranslate } from "@/hooks/useTranslate";

// Max clarification rounds before we force translation. Mirrors the backend
// CLARIFICATION_MAX_ROUNDS safety cap.
const MAX_ROUNDS = 3;

export type Phase = "idle" | "clarifying" | "translating" | "done";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  kind: "query" | "question" | "answer" | "info";
  text: string;
  options?: string[];
}

export interface ClarifyFlow {
  messages: ChatMessage[];
  phase: Phase;
  isPending: boolean;
  error: Error | null;
  steps: ReturnType<typeof useTranslate>["steps"];
  /** True while the assistant is waiting for the user to answer a question. */
  awaitingAnswer: boolean;
  /** Submit free-text from the input box (routes to start or answer). */
  submit: (text: string) => void;
  /** Click a suggested-answer chip. */
  answer: (text: string) => void;
  /** Skip remaining questions and translate with the best query so far. */
  generateNow: () => void;
  /** Clear the conversation and start over. */
  reset: () => void;
}

export function useClarifyFlow(opts: { onSparql: (sparql: string) => void }): ClarifyFlow {
  const clarify = useClarify();
  const translate = useTranslate();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [awaitingAnswer, setAwaitingAnswer] = useState(false);

  // Durable conversation state kept in refs to avoid stale closures across async calls.
  const originalQuery = useRef("");
  const fallbackQuery = useRef("");
  const history = useRef<ClarifyTurn[]>([]);
  const round = useRef(0);
  const pendingQuestions = useRef<{ question: string; options: string[] }[]>([]);
  const questionIndex = useRef(0);
  const idCounter = useRef(0);
  const onSparql = useRef(opts.onSparql);
  useEffect(() => {
    onSparql.current = opts.onSparql;
  }, [opts.onSparql]);

  const push = useCallback((msg: Omit<ChatMessage, "id">) => {
    setMessages((prev) => [...prev, { ...msg, id: idCounter.current++ }]);
  }, []);

  const beginTranslate = useCallback(
    (query: string) => {
      setAwaitingAnswer(false);
      pendingQuestions.current = [];
      setPhase("translating");
      push({ role: "assistant", kind: "info", text: `Generating SPARQL for: “${query}”` });
      translate.mutate(query, {
        onSuccess: (data) => {
          onSparql.current(data.sparql);
          setPhase("done");
        },
      });
    },
    [push, translate],
  );

  const runClarify = useCallback(async () => {
    const result = await clarify.mutateAsync({
      query: originalQuery.current,
      history: history.current,
    });
    if (result.enriched_query?.trim()) {
      fallbackQuery.current = result.enriched_query;
    }

    const noMore = result.ready || result.questions.length === 0 || round.current >= MAX_ROUNDS;
    if (noMore) {
      beginTranslate(fallbackQuery.current);
      return;
    }

    pendingQuestions.current = result.questions;
    questionIndex.current = 0;
    const q = result.questions[0];
    setAwaitingAnswer(true);
    push({ role: "assistant", kind: "question", text: q.question, options: q.options });
  }, [beginTranslate, clarify, push]);

  const start = useCallback(
    (query: string) => {
      originalQuery.current = query;
      fallbackQuery.current = query;
      history.current = [];
      round.current = 0;
      pendingQuestions.current = [];
      questionIndex.current = 0;
      setMessages([{ role: "user", kind: "query", text: query, id: idCounter.current++ }]);
      setPhase("clarifying");
      void runClarify();
    },
    [runClarify],
  );

  const answer = useCallback(
    (text: string) => {
      const current = pendingQuestions.current[questionIndex.current];
      if (!current) return;
      push({ role: "user", kind: "answer", text });
      history.current = [...history.current, { question: current.question, answer: text }];

      if (questionIndex.current + 1 < pendingQuestions.current.length) {
        // More questions remain in this round — ask the next one.
        questionIndex.current += 1;
        const next = pendingQuestions.current[questionIndex.current];
        push({ role: "assistant", kind: "question", text: next.question, options: next.options });
      } else {
        // Round complete — ask the backend whether it needs more.
        round.current += 1;
        pendingQuestions.current = [];
        setAwaitingAnswer(false);
        void runClarify();
      }
    },
    [push, runClarify],
  );

  const submit = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      if (phase === "clarifying" && awaitingAnswer) {
        answer(trimmed);
      } else if (phase === "idle" || phase === "done") {
        start(trimmed);
      }
    },
    [answer, awaitingAnswer, phase, start],
  );

  const generateNow = useCallback(() => {
    beginTranslate(fallbackQuery.current || originalQuery.current);
  }, [beginTranslate]);

  const reset = useCallback(() => {
    setMessages([]);
    setPhase("idle");
    setAwaitingAnswer(false);
    history.current = [];
    pendingQuestions.current = [];
    round.current = 0;
    questionIndex.current = 0;
  }, []);

  return {
    messages,
    phase,
    isPending: clarify.isPending || translate.isPending,
    error: (clarify.error as Error | null) ?? translate.error,
    steps: translate.steps,
    awaitingAnswer,
    submit,
    answer,
    generateNow,
    reset,
  };
}
