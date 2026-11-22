"""Tiny translation table. Languages: 'en', 'ar'."""
from __future__ import annotations

STRINGS: dict[str, dict[str, str]] = {
    # --- printed output ---------------------------------------------------
    "page_of": {"en": "Page {n} of {total}", "ar": "صفحة {n} من {total}"},
    "row_col": {"en": "row {r}, col {c}", "ar": "صف {r}، عمود {c}"},
    "scale": {"en": "Scale ×{s}", "ar": "المقياس ×{s}"},
    "real_length": {"en": "{v} {u}", "ar": "{v} {u}"},
    # --- GUI: filled in by app.py --------------------------------------------
}

_lang = "en"


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in ("en", "ar") else "en"


def language() -> str:
    return _lang


def register(extra: dict[str, dict[str, str]]) -> None:
    STRINGS.update(extra)


def tr(key: str, lang: str | None = None, **kw) -> str:
    entry = STRINGS.get(key)
    if entry is None:
        return key
    text = entry.get(lang or _lang) or entry.get("en", key)
    return text.format(**kw) if kw else text
