"""Locale-code → language-name mapping for localizing user-facing LLM output.

The frontend sends the website's selected locale code (en|fr|fa|es|de). We map it to an
English language name and inject a "respond in X" directive into the relevant prompts.
English is the default and adds no directive, so the existing behavior is unchanged.
"""

LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "fa": "Persian",
    "es": "Spanish",
    "de": "German",
}


def language_name(code: str | None) -> str:
    """Return the English name of a locale code, defaulting to English for unknown codes."""
    return LANGUAGE_NAMES.get((code or "en").lower(), "English")


def is_english(code: str | None) -> bool:
    return (code or "en").lower() == "en"
