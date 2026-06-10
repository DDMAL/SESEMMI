"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useClarify, type ClarifyTurn } from "@/hooks/useClarify";
import { useTranslate } from "@/hooks/useTranslate";

// Max clarification rounds before we force translation. Mirrors the backend
// CLARIFICATION_MAX_ROUNDS safety cap.
const MAX_ROUNDS = 3;

export type Phase = "idle" | "clarifying" | "awaiting_approval" | "translating" | "done";

export interface ChatMessage {
  id: number;
  role: "user" | "assistant";
  kind: "query" | "question" | "answer" | "info" | "approval";
  text: string;
  options?: string[];
  refinements?: string[];
}

export interface ClarifyFlow {
  messages: ChatMessage[];
  phase: Phase;
  isPending: boolean;
  error: Error | null;
  steps: ReturnType<typeof useTranslate>["steps"];
  /** True while the assistant is waiting for the user to answer a question. */
  awaitingAnswer: boolean;
  /** True after the user clicked "Needs adjustment" on an approval card. */
  awaitingFeedback: boolean;
  /** Submit free-text from the input box (routes to start, answer, or reject). */
  submit: (text: string) => void;
  /** Click a suggested-answer chip. */
  answer: (text: string) => void;
  /** Approve the clarified query and begin SPARQL generation. */
  approve: () => void;
  /** Activate the feedback input (user wants to adjust the clarified query). */
  requestFeedback: () => void;
  /** Submit rejection feedback — restarts clarification with the feedback in history. */
  reject: (feedback: string) => void;
  /** Skip remaining questions and show the approval card with the best query so far. */
  generateNow: () => void;
  /** Clear the conversation and start over. */
  reset: () => void;
  /** Clear and immediately start a new query — used by SPARQL refinement from the chat. */
  restart: (query: string, refinements?: string[]) => void;
}

export function useClarifyFlow(opts: { onSparql: (sparql: string) => void }): ClarifyFlow {
  const clarify = useClarify();
  const translate = useTranslate();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [phase, setPhase] = useState<Phase>("idle");
  const [awaitingAnswer, setAwaitingAnswer] = useState(false);
  const [awaitingFeedback, setAwaitingFeedback] = useState(false);

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
      push({ role: "assistant", kind: "info", text: `Generating SPARQL for: "${query}"` });
      translate.mutate(query, {
        onSuccess: (data) => {
          onSparql.current(data.sparql);
          setPhase("done");
        },
      });
    },
    [push, translate],
  );

  const showApprovalCard = useCallback(() => {
    setAwaitingAnswer(false);
    pendingQuestions.current = [];
    push({
      role: "assistant",
      kind: "approval",
      text: fallbackQuery.current || originalQuery.current,
    });
    setPhase("awaiting_approval");
  }, [push]);

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
      showApprovalCard();
      return;
    }

    pendingQuestions.current = result.questions;
    questionIndex.current = 0;
    const q = result.questions[0];
    setAwaitingAnswer(true);
    push({ role: "assistant", kind: "question", text: q.question, options: q.options });
  }, [clarify, push, showApprovalCard]);

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

  const approve = useCallback(() => {
    beginTranslate(fallbackQuery.current);
  }, [beginTranslate]);

  const requestFeedback = useCallback(() => {
    setAwaitingFeedback(true);
  }, []);

  const reject = useCallback(
    (feedback: string) => {
      setAwaitingFeedback(false);
      push({ role: "user", kind: "answer", text: feedback });
      history.current = [
        ...history.current,
        { question: "What would you like to change about the search query?", answer: feedback },
      ];
      round.current = 0; // reset so MAX_ROUNDS doesn't force-translate immediately
      setPhase("clarifying");
      void runClarify();
    },
    [push, runClarify],
  );

  const submit = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      if (phase === "clarifying" && awaitingAnswer) {
        answer(trimmed);
      } else if (phase === "awaiting_approval" && awaitingFeedback) {
        reject(trimmed);
      } else if (phase === "idle" || phase === "done") {
        start(trimmed);
      }
    },
    [answer, awaitingAnswer, awaitingFeedback, phase, reject, start],
  );

  const generateNow = useCallback(() => {
    showApprovalCard();
  }, [showApprovalCard]);

  const reset = useCallback(() => {
    setMessages([]);
    setPhase("idle");
    setAwaitingAnswer(false);
    setAwaitingFeedback(false);
    history.current = [];
    pendingQuestions.current = [];
    round.current = 0;
    questionIndex.current = 0;
  }, []);

  const restart = useCallback(
    (query: string, refinements?: string[]) => {
      const enriched =
        refinements && refinements.length > 0
          ? `${query}\n\nAdditional requirements:\n${refinements.map((r) => `- ${r}`).join("\n")}`
          : query;
      setAwaitingAnswer(false);
      setAwaitingFeedback(false);
      originalQuery.current = enriched;
      fallbackQuery.current = enriched;
      history.current = [];
      round.current = 0;
      pendingQuestions.current = [];
      questionIndex.current = 0;
      setMessages([
        { role: "user", kind: "query", text: query, refinements, id: idCounter.current++ },
      ]);
      setPhase("clarifying");
      void runClarify();
    },
    [runClarify],
  );

  return {
    messages,
    phase,
    isPending: clarify.isPending || translate.isPending,
    error: (clarify.error as Error | null) ?? translate.error,
    steps: translate.steps,
    awaitingAnswer,
    awaitingFeedback,
    submit,
    answer,
    approve,
    requestFeedback,
    reject,
    generateNow,
    reset,
    restart,
  };
}
