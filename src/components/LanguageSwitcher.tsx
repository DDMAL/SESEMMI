"use client";

import { useEffect, useRef, useState } from "react";
import { useI18n } from "@/lib/i18n/context";
import { LOCALES, type Locale } from "@/lib/i18n";

const ORDER: Locale[] = ["en", "fr", "es", "de", "fa"];

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t("app.language")}
        className="flex cursor-pointer items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-all hover:text-indigo-600"
        style={{
          background: "rgba(99,102,241,0.06)",
          border: "1px solid rgba(99,102,241,0.2)",
        }}
      >
        <svg
          aria-hidden="true"
          className="h-4 w-4 text-indigo-500"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 21a9 9 0 100-18 9 9 0 000 18zm0 0c2.5 0 4.5-4.03 4.5-9S14.5 3 12 3 7.5 7.03 7.5 12s2 9 4.5 9zM3.5 9h17M3.5 15h17"
          />
        </svg>
        <span>{LOCALES[locale].label}</span>
        <span aria-hidden="true" className="text-[8px] text-slate-400">
          ▾
        </span>
      </button>

      {open && (
        <ul
          role="listbox"
          className="absolute end-0 z-20 mt-1.5 min-w-[9rem] overflow-hidden rounded-xl py-1"
          style={{
            background: "rgba(255,255,255,0.97)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(99,102,241,0.18)",
            boxShadow: "0 12px 32px rgba(99,102,241,0.16)",
          }}
        >
          {ORDER.map((code) => (
            <li key={code}>
              <button
                type="button"
                role="option"
                aria-selected={code === locale}
                onClick={() => {
                  setLocale(code);
                  setOpen(false);
                }}
                dir={LOCALES[code].dir}
                className={`flex w-full cursor-pointer items-center justify-between px-3 py-1.5 text-start text-xs transition-colors hover:bg-indigo-50 ${
                  code === locale ? "font-semibold text-indigo-600" : "text-slate-600"
                }`}
              >
                <span>{LOCALES[code].label}</span>
                {code === locale && (
                  <span aria-hidden="true" className="text-indigo-500">
                    ✓
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
