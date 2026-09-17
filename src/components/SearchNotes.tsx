"use client";

import type { TranslateResult } from "@/hooks/useTranslate";
import { useI18n } from "@/lib/i18n/context";

export function SearchNotes({
  assessment,
  sparql,
}: {
  assessment: TranslateResult | null;
  sparql: string;
}) {
  const { t } = useI18n();
  if (!assessment || assessment.sparql !== sparql) return null;

  const notes = assessment.assumptions.filter((note) => !note.startsWith("Assumed QID "));
  if (notes.length === 0) return null;

  return (
    <aside className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-slate-700 dark:border-amber-800 dark:bg-amber-950">
      <h2 className="font-semibold">{t("results.searchNotes")}</h2>
      <ul className="mt-1 list-disc space-y-1 ps-5">
        {notes.map((note, index) => (
          <li key={`${index}-${note}`}>{note}</li>
        ))}
      </ul>
    </aside>
  );
}
