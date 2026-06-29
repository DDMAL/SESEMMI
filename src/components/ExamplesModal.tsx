"use client";

import { useEffect } from "react";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import { useI18n } from "@/lib/i18n/context";

interface ExamplesModalProps {
  /** Insert the chosen query into the input (no submit). */
  onPick: (query: string) => void;
  onClose: () => void;
}

export function ExamplesModal({ onPick, onClose }: ExamplesModalProps) {
  const { t, dict } = useI18n();
  const dialogRef = useFocusTrap<HTMLDivElement>();
  const titleId = "examples-title";

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ background: "rgba(15,23,42,0.45)", backdropFilter: "blur(4px)" }}
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="modal-enter fixed top-1/2 left-1/2 z-50 flex w-[min(960px,calc(100vw-2rem))] max-h-[80vh] flex-col gap-3 overflow-y-auto rounded-2xl p-5"
        style={{
          background: "var(--surface-solid)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(99,102,241,0.15)",
          boxShadow: "0 24px 64px rgba(15,23,42,0.18), 0 4px 16px rgba(99,102,241,0.1)",
        }}
      >
        <div className="flex items-center justify-between">
          <h3
            id={titleId}
            className="text-xs font-semibold uppercase tracking-widest text-indigo-500"
          >
            {t("conversation.tryExample")}
          </h3>
          <button
            onClick={onClose}
            aria-label={t("entity.close")}
            className="cursor-pointer rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
          {dict.conversation.starters.map((s) => (
            <button
              key={s.label}
              type="button"
              onClick={() => onPick(s.query)}
              className="flex cursor-pointer flex-col gap-1 rounded-xl px-3.5 py-3 text-start transition-all duration-200 hover:-translate-y-1 hover:border-indigo-400 hover:shadow-[0_8px_24px_rgba(99,102,241,0.18)]"
              style={{
                background: "var(--surface-input)",
                border: "1px solid rgba(99,102,241,0.2)",
              }}
            >
              <span className="text-xs font-semibold text-indigo-600">{s.label}</span>
              <span className="text-xs leading-snug text-slate-500">{s.query}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );
}
