"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { DEFAULT_LOCALE, LOCALES, dictionaries, type Dictionary, type Locale } from "./index";

const STORAGE_KEY = "sesemmi-locale";

interface I18nValue {
  locale: Locale;
  dir: "ltr" | "rtl";
  dict: Dictionary;
  setLocale: (l: Locale) => void;
  /** Dot-path lookup into the active dictionary, with `{name}` interpolation. */
  t: (path: string, vars?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

function resolve(dict: Dictionary, path: string): string {
  const value = path
    .split(".")
    .reduce<unknown>((o, k) => (o as Record<string, unknown> | undefined)?.[k], dict);
  // Fall back to the raw path so a missing key is visible rather than blank.
  return typeof value === "string" ? value : path;
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(DEFAULT_LOCALE);

  // Restore the saved choice on mount. Deliberately done in an effect (not a lazy
  // initializer) so the first client render matches the server's English HTML — avoiding
  // a hydration mismatch — then switches to the saved locale.
  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (saved && saved in LOCALES) setLocaleState(saved as Locale);
  }, []);

  // Keep <html lang>/<dir> in sync so RTL locales mirror the whole layout.
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = LOCALES[locale].dir;
  }, [locale]);

  const setLocale = (l: Locale) => {
    localStorage.setItem(STORAGE_KEY, l);
    setLocaleState(l);
  };

  const dict = dictionaries[locale];
  const t = (path: string, vars?: Record<string, string | number>) => {
    let s = resolve(dict, path);
    if (vars) {
      for (const [k, val] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(val));
    }
    return s;
  };

  return (
    <I18nContext.Provider value={{ locale, dir: LOCALES[locale].dir, dict, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within LanguageProvider");
  return ctx;
}
