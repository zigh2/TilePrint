"""Bundled fonts (Noto Sans / Noto Sans Arabic, SIL OFL) and mixed Arabic/Latin text drawing."""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

try:  # Arabic shaping is optional at import time, but shipped in requirements.
    import arabic_reshaper
    from bidi.algorithm import get_display
except Exception:  # pragma: no cover
    arabic_reshaper = None
    get_display = None


def asset_path(*parts: str) -> Path:
    """Locate bundled data both from source and from a PyInstaller bundle."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    p = base / "tileprint" / "assets" if hasattr(sys, "_MEIPASS") else base / "assets"
    return p.joinpath(*parts)


_FONTS = {
    "lat": "NotoSans-Regular.ttf", "lat-b": "NotoSans-Bold.ttf",
    "ar": "NotoSansArabic-Regular.ttf", "ar-b": "NotoSansArabic-Bold.ttf",
}
_registered = False


def register_fonts() -> None:
    global _registered
    if _registered:
        return
    for key, fn in _FONTS.items():
        pdfmetrics.registerFont(TTFont(f"TP-{key}", str(asset_path("fonts", fn))))
    _registered = True


def _is_arabic(ch: str) -> bool:
    o = ord(ch)
    return (0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0x08A0 <= o <= 0x08FF
            or 0xFB50 <= o <= 0xFDFF or 0xFE70 <= o <= 0xFEFF)


def has_arabic(text: str) -> bool:
    return any(_is_arabic(c) for c in text)


def visual(text: str) -> str:
    """Shape + reorder so that left-to-right drawing shows correct Arabic."""
    if arabic_reshaper and get_display and has_arabic(text):
        return get_display(arabic_reshaper.reshape(text))
    return text


def _runs(shown: str, bold: bool) -> list[tuple[str, str]]:
    suffix = "-b" if bold else ""
    runs: list[tuple[str, str]] = []
    current = None
    for ch in shown:
        if _is_arabic(ch):
            face = "ar"
        elif ch.isalpha():
            face = "lat"
        else:                       # digits, spaces, punctuation: keep the surrounding face
            face = current or ("ar" if has_arabic(shown) and not shown[0].isalpha() else "lat")
        face_name = f"TP-{face}{suffix}"
        if runs and runs[-1][1] == face_name:
            runs[-1] = (runs[-1][0] + ch, face_name)
        else:
            runs.append((ch, face_name))
        current = face
    return runs


def text_width(text: str, size: float, bold: bool = False) -> float:
    register_fonts()
    return sum(pdfmetrics.stringWidth(t, f, size) for t, f in _runs(visual(text), bold))


def draw_text(c, x: float, y: float, text: str, size: float, bold: bool = False,
              align: str = "left") -> float:
    """Draw text on a reportlab canvas; returns the drawn width."""
    register_fonts()
    shown = visual(text)
    runs = _runs(shown, bold)
    width = sum(pdfmetrics.stringWidth(t, f, size) for t, f in runs)
    if align == "center":
        x -= width / 2
    elif align == "right":
        x -= width
    for t, f in runs:
        c.setFont(f, size)
        c.drawString(x, y, t)
        x += pdfmetrics.stringWidth(t, f, size)
    return width


def fit_text(text: str, size: float, max_width: float, bold: bool = False) -> str:
    """Shorten with an ellipsis so the text fits max_width."""
    if text_width(text, size, bold) <= max_width:
        return text
    while len(text) > 1 and text_width(text + "…", size, bold) > max_width:
        text = text[:-1]
    return text + "…"
