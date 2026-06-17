"use client";

import { useEffect, useState } from "react";
import { Spinner } from "@/components/Spinner";
import { fetchEntity, type EntityDetail as Entity } from "@/lib/wikidata";
import { useFocusTrap } from "@/hooks/useFocusTrap";
import { useI18n } from "@/lib/i18n/context";

interface EntityDetailProps {
  qid: string;
  onClose: () => void;
}

export function EntityDetail({ qid, onClose }: EntityDetailProps) {
  const { t } = useI18n();
  const dialogRef = useFocusTrap<HTMLDivElement>();
  const titleId = `entity-title-${qid}`;
  const [entity, setEntity] = useState<Entity | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let active = true;
    fetchEntity(qid)
      .then((e) => active && setEntity(e))
      .catch(() => active && setError(true));
    return () => {
      active = false;
    };
  }, [qid]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div
        className="fixed inset-0 z-40"
        style={{ background: "rgba(15,23,42,0.45)", backdropFilter: "blur(3px)" }}
        onClick={onClose}
        aria-hidden="true"
      />

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={entity ? titleId : undefined}
        aria-label={entity ? undefined : t("entity.loading")}
        className="modal-enter fixed top-1/2 left-1/2 z-50 flex w-[min(384px,calc(100vw-2rem))] flex-col gap-3 overflow-y-auto rounded-2xl p-5"
        style={{
          background: "var(--surface-solid)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(99,102,241,0.15)",
          boxShadow: "0 24px 64px rgba(15,23,42,0.18), 0 4px 16px rgba(99,102,241,0.1)",
          maxHeight: "70vh",
        }}
      >
        {/* Close button only — no redundant label */}
        <div className="flex justify-end">
          <button
            onClick={onClose}
            aria-label={t("entity.close")}
            className="cursor-pointer rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
          >
            ✕
          </button>
        </div>

        {!entity && !error && (
          <div className="flex items-center justify-center gap-2 py-6 text-sm text-slate-400">
            <Spinner className="h-4 w-4 text-indigo-400" />
            {t("entity.loading")}
          </div>
        )}

        {error && (
          <p className="py-4 text-center text-sm text-red-500">{t("entity.loadError", { qid })}</p>
        )}

        {entity && (
          <>
            <div>
              <h3 id={titleId} className="text-base font-semibold text-slate-800">
                {entity.label}
              </h3>
              {entity.description && (
                <p className="mt-0.5 text-sm text-slate-500">
                  {entity.description.length > 120
                    ? entity.description.slice(0, 120) + "…"
                    : entity.description}
                </p>
              )}
            </div>

            {entity.facts.length > 0 && (
              <dl className="flex flex-col gap-1.5 border-t border-slate-100 pt-3">
                {entity.facts.slice(0, 3).map((f, i) => (
                  <div key={i} className="flex gap-3 text-sm">
                    <dt className="w-20 shrink-0 text-slate-400">{f.prop}</dt>
                    <dd className="min-w-0 flex-1 text-slate-700">{f.value}</dd>
                  </div>
                ))}
              </dl>
            )}

            <a
              href={entity.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 self-start rounded-lg px-3 py-2 text-sm font-medium text-indigo-600 transition-colors hover:bg-indigo-50 hover:text-indigo-700"
              style={{ border: "1px solid rgba(99,102,241,0.2)" }}
            >
              {t("entity.openWikidata")}
              <span aria-hidden="true">↗</span>
            </a>
          </>
        )}
      </div>
    </>
  );
}
