"use client";

import { useState, useCallback } from "react";

export type StepStatus = "waiting" | "running" | "done" | "error";

export interface Step {
  step: string;
  label: string;
  status: StepStatus;
  detail: string;
  tokens: string;
}

interface TranslateResult {
  sparql: string;
}

function handleSseEvent(
  eventType: string,
  data: Record<string, unknown>,
  setSteps: React.Dispatch<React.SetStateAction<Step[]>>,
  onSuccess: (result: TranslateResult) => void,
  onError: (err: Error) => void,
) {
  if (eventType === "step_start") {
    setSteps((prev) => [
      ...prev,
      {
        step: data.step as string,
        label: data.label as string,
        status: "running",
        detail: "",
        tokens: "",
      },
    ]);
  } else if (eventType === "step_done") {
    setSteps((prev) =>
      prev.map((s) =>
        s.step === (data.step as string)
          ? { ...s, status: "done", detail: (data.detail as string) ?? "" }
          : s,
      ),
    );
  } else if (eventType === "token") {
    setSteps((prev) =>
      prev.map((s) =>
        s.step === "generate" && s.status === "running" ? { ...s, tokens: s.tokens + (data.text as string) } : s,
      ),
    );
  } else if (eventType === "done") {
    onSuccess({ sparql: (data.sparql as string) ?? "" });
  } else if (eventType === "error") {
    onError(new Error((data.message as string) ?? "Streaming error"));
  }
}

export function useTranslate() {
  const [isPending, setIsPending] = useState(false);
  const [isError, setIsError] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [steps, setSteps] = useState<Step[]>([]);

  const mutate = useCallback(
    async (query: string, callbacks: { onSuccess: (data: TranslateResult) => void }) => {
      setIsPending(true);
      setIsError(false);
      setError(null);
      setSteps([]);

      let errorOccurred = false;

      try {
        const res = await fetch("/api/translate/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query }),
        });

        if (!res.ok || !res.body) {
          const data = await res.json().catch(() => ({ error: "Request failed" }));
          throw new Error(data.error || `HTTP ${res.status}`);
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });

          // SSE messages are separated by double newline
          const parts = buffer.split("\n\n");
          buffer = parts.pop()!;

          for (const part of parts) {
            const eventMatch = part.match(/^event:\s*(\w+)/m);
            const dataMatch = part.match(/^data:\s*(.+)/m);
            if (!eventMatch || !dataMatch) continue;
            const eventType = eventMatch[1];
            let data: Record<string, unknown> = {};
            try {
              data = JSON.parse(dataMatch[1]);
            } catch {
              continue;
            }
            handleSseEvent(eventType, data, setSteps, callbacks.onSuccess, (err) => {
              errorOccurred = true;
              setIsError(true);
              setError(err);
              setSteps((prev) =>
                prev.map((s) => (s.status === "running" ? { ...s, status: "error" } : s)),
              );
            });
          }
        }
      } catch (e) {
        if (!errorOccurred) {
          setIsError(true);
          setError(e as Error);
        }
      } finally {
        setIsPending(false);
      }
    },
    [],
  );

  return { mutate, isPending, isError, error, steps };
}
