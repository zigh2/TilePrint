"""Paper sizes and unit helpers. All internal geometry is in PDF points (1/72 inch)."""
from __future__ import annotations

import locale
import math

PT_PER_INCH = 72.0
PT_PER_MM = PT_PER_INCH / 25.4
PT_PER_CM = PT_PER_MM * 10

UNITS = {"mm": PT_PER_MM, "cm": PT_PER_CM, "in": PT_PER_INCH, "pt": 1.0}


def to_pt(value: float, unit: str) -> float:
    return value * UNITS[unit]


def from_pt(value_pt: float, unit: str) -> float:
    return value_pt / UNITS[unit]


def _iso_a(n: int) -> tuple[float, float]:
    # A0 = 841 x 1189 mm; each step halves the area (ISO 216, rounded to mm).
    w, h = 841.0, 1189.0
    for _ in range(n):
        w, h = h / 2, w
        w, h = math.floor(w), math.floor(h)
    return w, h


def _iso_b(n: int) -> tuple[float, float]:
    w, h = 1000.0, 1414.0  # B0
    for _ in range(n):
        w, h = h / 2, w
        w, h = math.floor(w), math.floor(h)
    return w, h


# name -> (width_mm, height_mm), portrait
_MM_SIZES: dict[str, tuple[float, float]] = {}
for _n in range(0, 9):
    _MM_SIZES[f"A{_n}"] = _iso_a(_n)
for _n in range(0, 9):
    _MM_SIZES[f"B{_n}"] = _iso_b(_n)

# Imperial / US sizes in inches, portrait
_IN_SIZES = {
    "Letter": (8.5, 11.0),
    "Legal": (8.5, 14.0),
    "Tabloid": (11.0, 17.0),
    "ANSI C": (17.0, 22.0),
    "ANSI D": (22.0, 34.0),
    "ANSI E": (34.0, 44.0),
    "ARCH A": (9.0, 12.0),
    "ARCH B": (12.0, 18.0),
    "ARCH C": (18.0, 24.0),
    "ARCH D": (24.0, 36.0),
    "ARCH E": (36.0, 48.0),
    "ARCH E1": (30.0, 42.0),
}

PAPER_SIZES_PT: dict[str, tuple[float, float]] = {}
for _k, (_w, _h) in _MM_SIZES.items():
    PAPER_SIZES_PT[_k] = (_w * PT_PER_MM, _h * PT_PER_MM)
for _k, (_w, _h) in _IN_SIZES.items():
    PAPER_SIZES_PT[_k] = (_w * PT_PER_INCH, _h * PT_PER_INCH)

# Order shown in the UI
PRESET_ORDER = (
    [f"A{i}" for i in range(0, 7)]
    + [f"B{i}" for i in range(0, 7)]
    + list(_IN_SIZES)
)


def paper_size(name: str, landscape: bool = False) -> tuple[float, float]:
    w, h = PAPER_SIZES_PT[name]
    return (h, w) if landscape else (w, h)


def default_paper_name() -> str:
    """A4 everywhere except the US/Canada, where Letter is the norm."""
    try:
        loc = (locale.getlocale()[0] or "") or ""
    except Exception:
        loc = ""
    return "Letter" if loc.endswith(("_US", "_CA")) or loc in ("en_US", "en_CA") else "A4"
