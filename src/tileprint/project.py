"""Project settings and the pipeline that turns (source, settings) into a ready-to-export job."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from typing import Optional

from . import layout as L
from . import source as S
from .overlay import OverlayOptions
from .paper import PT_PER_MM, default_paper_name, paper_size

PROJECT_EXT = ".tileprint"
RASTER_SAMPLES = 2000          # long side of the poster raster used for smart cuts / blank tiles


@dataclass
class Settings:
    unit: str = "mm"
    poster_preset: str = "A0"                 # preset name or "Custom"
    poster_orient: str = "auto"               # auto | portrait | landscape (presets only)
    poster_w: float = 841 * PT_PER_MM         # custom size, points
    poster_h: float = 1189 * PT_PER_MM
    lock_aspect: bool = True
    scale_mode: str = "fit"                   # fit | fill | stretch
    offset: list = field(default_factory=lambda: [0.0, 0.0])   # drag offset, poster points
    paper: str = field(default_factory=default_paper_name)
    paper_orient: str = "auto"                # auto | portrait | landscape
    margin: float = 10 * PT_PER_MM
    header: float = 9 * PT_PER_MM
    overlap: float = 10 * PT_PER_MM
    numbering: str = "seq"                    # seq | rc
    crop_marks: bool = True
    overlap_guides: bool = True
    footer: bool = True
    scale_bar: bool = True
    smart_cut: bool = False
    skip_blank: bool = True
    blank_backs: bool = False
    footer_text: str = ""
    language: str = "en"
    page_index: int = 0
    sheet_fit_one_page: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Settings":
        names = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in names})


def save_project(path: str, settings: Settings, source_path: Optional[str]) -> None:
    data = {"version": 1, "source": source_path, "settings": settings.to_dict()}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_project(path: str) -> tuple[Settings, Optional[str]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    src = data.get("source")
    if src and not os.path.isabs(src):
        src = os.path.join(os.path.dirname(path), src)
    return Settings.from_dict(data.get("settings", {})), src


# --------------------------------------------------------------------------- #
@dataclass
class Job:
    poster_w: float
    poster_h: float
    paper_w: float
    paper_h: float
    placement: L.Placement
    layout: L.TileLayout
    skip: set
    overlay: OverlayOptions
    dpi: Optional[float]                      # effective resolution for raster sources
    scale: float                               # poster pt per source pt (horizontal)


def poster_dimensions(s: Settings, src: S.Source) -> tuple[float, float]:
    if s.poster_preset == "Custom":
        return s.poster_w, s.poster_h
    w, h = paper_size(s.poster_preset)
    sw, sh = src.size_pt
    if s.poster_orient == "landscape" or (s.poster_orient == "auto" and sw > sh):
        return max(w, h), min(w, h)
    return min(w, h), max(w, h)


def paper_dimensions(s: Settings, poster_w: float, poster_h: float) -> tuple[float, float]:
    w, h = paper_size(s.paper)
    if s.paper_orient == "landscape":
        return max(w, h), min(w, h)
    if s.paper_orient == "portrait":
        return min(w, h), max(w, h)
    land = L.best_orientation(poster_w, poster_h, w, h, s.margin, s.header, s.overlap)
    return (max(w, h), min(w, h)) if land else (min(w, h), max(w, h))


class RasterCache:
    """Poster-space raster is the costly part; reuse it while only tile settings change."""

    def __init__(self) -> None:
        self.key = None
        self.raster = None
        self.res = 1.0

    def get(self, src: S.Source, pl: L.Placement, pw: float, ph: float):
        key = (src.pdf_path, src.page_index, round(pl.x, 2), round(pl.y, 2),
               round(pl.width, 2), round(pl.height, 2), round(pw, 2), round(ph, 2))
        if key != self.key:
            self.res = max(pw, ph) / RASTER_SAMPLES
            self.raster = S.poster_raster(src, pl, pw, ph, self.res)
            self.key = key
        return self.raster, self.res


def build_job(src: S.Source, s: Settings, cache: Optional[RasterCache] = None) -> Job:
    pw, ph = poster_dimensions(s, src)
    paper_w, paper_h = paper_dimensions(s, pw, ph)
    sw, sh = src.size_pt
    pl = L.place_content(sw, sh, pw, ph, s.scale_mode, tuple(s.offset))

    ink_x = ink_y = None
    res = 1.0
    raster = None
    if s.smart_cut or s.skip_blank:
        cache = cache or RasterCache()
        raster, res = cache.get(src, pl, pw, ph)
    if s.smart_cut and raster is not None:
        ink_x, ink_y = S.ink_profiles(raster)
    lay = L.build_layout(pw, ph, paper_w, paper_h, s.margin, s.header, s.overlap,
                         ink_x, ink_y, res, smart_slack=min(s.overlap * 1.5, 15 * PT_PER_MM) if s.smart_cut else 0.0)
    skip = S.blank_tiles(raster, lay, res) if (s.skip_blank and raster is not None) else set()
    if len(skip) >= lay.rows * lay.cols:      # never produce an empty document
        skip = set()

    name = s.footer_text or os.path.basename(src.original_path)
    overlay = OverlayOptions(
        numbering=s.numbering, crop_marks=s.crop_marks, overlap_guides=s.overlap_guides,
        footer=s.footer, scale_bar=s.scale_bar, imperial_bar=(s.unit == "in"),
        footer_name=name, scale_text=f"{pl.sx:.2f}" if abs(pl.sx - pl.sy) < 1e-6 else "",
        language=s.language)
    dpi = L.effective_dpi(src.pixel_size[0], pl.width) if src.pixel_size else None
    return Job(pw, ph, paper_w, paper_h, pl, lay, skip, overlay, dpi, pl.sx)
