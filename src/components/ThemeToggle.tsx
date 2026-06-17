"use client";

import { useTheme } from "@/lib/theme/context";
import { useI18n } from "@/lib/i18n/context";

export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const { t } = useI18n();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-pressed={isDark}
      aria-label={isDark ? t("app.theme.toLight") : t("app.theme.toDark")}
      title={isDark ? t("app.theme.toLight") : t("app.theme.toDark")}
      className="flex cursor-pointer items-center justify-center rounded-xl p-1.5 text-slate-600 transition-all hover:text-indigo-600"
      style={{
        background: "rgba(99,102,241,0.06)",
        border: "1px solid rgba(99,102,241,0.2)",
      }}
    >
      {isDark ? (
        // sun
        <svg
          aria-hidden="true"
          className="h-4 w-4 text-indigo-400"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          viewBox="0 0 24 24"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41" />
        </svg>
      ) : (
        // moon
        <svg
          aria-hidden="true"
          className="h-4 w-4 text-indigo-500"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          viewBox="0 0 24 24"
        >
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z" />
        </svg>
      )}
    </button>
  );
}
