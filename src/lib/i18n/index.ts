import { en } from "./locales/en";
import { fr } from "./locales/fr";
import { fa } from "./locales/fa";
import { es } from "./locales/es";
import { de } from "./locales/de";

// English is the canonical shape; every other locale is typed `: Dictionary`, so a missing
// or extra key is a compile error (guarantees all languages stay complete).
export type Dictionary = typeof en;
export type Locale = "en" | "fr" | "fa" | "es" | "de";

export const LOCALES: Record<Locale, { label: string; dir: "ltr" | "rtl" }> = {
  en: { label: "English", dir: "ltr" },
  fr: { label: "Français", dir: "ltr" },
  fa: { label: "فارسی", dir: "rtl" },
  es: { label: "Español", dir: "ltr" },
  de: { label: "Deutsch", dir: "ltr" },
};

export const dictionaries: Record<Locale, Dictionary> = { en, fr, fa, es, de };
export const DEFAULT_LOCALE: Locale = "en";
