"""Pure geometry for splitting a large poster into printable tiles.

Coordinate conventions
----------------------
* *Poster space*: origin top-left, x to the right, y DOWN, units = PDF points.
  The poster is the final-size sheet (e.g. A0) that gets cut into tiles.
* *Page space*: PDF native, origin bottom-left, y UP, units = points.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Sequence

EPS = 1e-6


# --------------------------------------------------------------------------- #
# content placement
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Placement:
    """Where the source page lands on the poster (poster space)."""
    sx: float          # horizontal scale: source pt -> poster pt
    sy: float          # vertical scale
    x: float           # left edge of the scaled content
    y: float           # top edge of the scaled content
    width: float       # scaled content width
    height: float      # scaled content height


def place_content(src_w: float, src_h: float, poster_w: float, poster_h: float,
                  mode: str = "fit", offset: tuple[float, float] = (0.0, 0.0)) -> Placement:
    """Scale the source onto the poster.

    mode: 'fit' (whole source visible, aspect kept), 'fill' (poster fully covered,
    aspect kept, overflow cropped) or 'stretch' (aspect ignored).
    offset is an extra translation in poster points (used when dragging in the preview).
    """
    if src_w <= 0 or src_h <= 0:
        raise ValueError("source has zero size")
    if mode == "stretch":
        sx, sy = poster_w / src_w, poster_h / src_h
    elif mode == "fill":
        sx = sy = max(poster_w / src_w, poster_h / src_h)
    elif mode == "fit":
        sx = sy = min(poster_w / src_w, poster_h / src_h)
    else:
        raise ValueError(f"unknown scale mode {mode!r}")
    w, h = src_w * sx, src_h * sy
    return Placement(sx, sy, (poster_w - w) / 2 + offset[0], (poster_h - h) / 2 + offset[1], w, h)


def size_from_width(src_w: float, src_h: float, width: float) -> tuple[float, float]:
    """Poster (width, height) that keeps the source aspect ratio for a given width."""
    return width, width * src_h / src_w


def size_from_height(src_w: float, src_h: float, height: float) -> tuple[float, float]:
    return height * src_w / src_h, height


def effective_dpi(pixels: float, scaled_length_pt: float) -> float:
    """Print resolution of a raster image whose `pixels` span `scaled_length_pt` on the poster."""
    inches = scaled_length_pt / 72.0
    return pixels / inches if inches > 0 else float("inf")


# --------------------------------------------------------------------------- #
# numbering helpers
# --------------------------------------------------------------------------- #
def row_letters(n: int) -> str:
    """0 -> A, 25 -> Z, 26 -> AA ..."""
    s = ""
    n += 1
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


# --------------------------------------------------------------------------- #
# tile layout
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Tile:
    row: int
    col: int
    x: float      # left, poster space
    y: float      # top, poster space
    w: float      # frame width  (same for all tiles)
    h: float      # frame height

    @property
    def key(self) -> tuple[int, int]:
        return (self.row, self.col)


@dataclass(frozen=True)
class PlannedPage:
    tile: Tile
    number: int                  # 1-based among printed pages
    label: str                   # text shown as the page's own name
    neighbors: dict              # 'left'|'right'|'up'|'down' -> label (only printed ones)
    total: int


def _quietest(profile: Sequence[float], res: float, lo: float, hi: float) -> float:
    """Position in [lo, hi] (poster pt) with the least ink; ties go to the largest."""
    i0 = max(0, int(math.ceil(lo / res)))
    i1 = min(len(profile) - 1, int(math.floor(hi / res)))
    if i1 < i0:
        return hi
    best_i, best_v = i1, profile[i1]
    for i in range(i1, i0 - 1, -1):
        if profile[i] < best_v - 1e-12:
            best_i, best_v = i, profile[i]
    return best_i * res


def axis_starts(total: float, frame: float, overlap: float,
                profile: Optional[Sequence[float]] = None, profile_res: float = 1.0,
                slack: float = 0.0) -> list[float]:
    """Start coordinates of the tiles along one axis.

    Each tile spans [start, start + frame]; consecutive tiles share at least `overlap`.
    With an ink `profile` (ink amount per `profile_res` points) and `slack` > 0 the next
    start may move back up to `slack` points (more overlap) to land on empty space, so
    the visible edge of the next sheet doesn't slice through drawing content.
    """
    if frame <= overlap + EPS:
        raise ValueError("frame must be larger than the overlap")
    if total <= frame + EPS:
        return [0.0]
    step = frame - overlap
    starts = [0.0]
    while starts[-1] + frame < total - EPS:
        ideal = starts[-1] + step
        nxt = ideal
        if profile is not None and slack > 0:
            lo = max(ideal - slack, starts[-1] + 1.0)
            nxt = _quietest(profile, profile_res, lo, ideal)
        starts.append(nxt)
    return starts


@dataclass
class TileLayout:
    poster_w: float
    poster_h: float
    paper_w: float
    paper_h: float
    margin: float
    header: float
    overlap: float
    xs: list = field(default_factory=list)
    ys: list = field(default_factory=list)

    # ---- frame (page space, y up) -------------------------------------- #
    @property
    def frame(self) -> tuple[float, float, float, float]:
        """(x0, y0, x1, y1) of the thin frame on the page."""
        return (self.margin, self.margin,
                self.paper_w - self.margin, self.paper_h - self.margin - self.header)

    @property
    def frame_w(self) -> float:
        return self.paper_w - 2 * self.margin

    @property
    def frame_h(self) -> float:
        return self.paper_h - 2 * self.margin - self.header

    @property
    def cols(self) -> int:
        return len(self.xs)

    @property
    def rows(self) -> int:
        return len(self.ys)

    def tiles(self) -> list[Tile]:
        return [Tile(r, c, x, y, self.frame_w, self.frame_h)
                for r, y in enumerate(self.ys) for c, x in enumerate(self.xs)]

    def plan(self, skip: Optional[set] = None, numbering: str = "seq") -> list[PlannedPage]:
        """Printed pages in reading order with their labels and neighbour labels.

        numbering: 'seq' (1, 2, 3 ... among printed pages) or 'rc' (A1, B2 ...).
        Tiles in `skip` (row, col) are not printed and never referenced by arrows.
        """
        skip = skip or set()
        printed = [t for t in self.tiles() if t.key not in skip]
        labels: dict[tuple[int, int], str] = {}
        for i, t in enumerate(printed, 1):
            labels[t.key] = str(i) if numbering == "seq" else f"{row_letters(t.row)}{t.col + 1}"
        out = []
        for i, t in enumerate(printed, 1):
            nb = {}
            for name, (dr, dc) in (("left", (0, -1)), ("right", (0, 1)),
                                   ("up", (-1, 0)), ("down", (1, 0))):
                k = (t.row + dr, t.col + dc)
                if k in labels:
                    nb[name] = labels[k]
            out.append(PlannedPage(t, i, labels[t.key], nb, len(printed)))
        return out


def build_layout(poster_w: float, poster_h: float, paper_w: float, paper_h: float,
                 margin: float, header: float, overlap: float,
                 ink_x: Optional[Sequence[float]] = None,
                 ink_y: Optional[Sequence[float]] = None,
                 ink_res: float = 1.0, smart_slack: float = 0.0) -> TileLayout:
    lay = TileLayout(poster_w, poster_h, paper_w, paper_h, margin, header, overlap)
    if lay.frame_w <= overlap + EPS or lay.frame_h <= overlap + EPS:
        raise ValueError("margins/header/overlap leave no printable area")
    lay.xs = axis_starts(poster_w, lay.frame_w, overlap, ink_x, ink_res, smart_slack)
    lay.ys = axis_starts(poster_h, lay.frame_h, overlap, ink_y, ink_res, smart_slack)
    return lay


def best_orientation(poster_w: float, poster_h: float, paper_w: float, paper_h: float,
                     margin: float, header: float, overlap: float) -> bool:
    """True if landscape needs fewer sheets than portrait (ties -> less waste -> portrait)."""
    def count(pw: float, ph: float) -> tuple[int, float]:
        fw, fh = pw - 2 * margin, ph - 2 * margin - header
        if fw <= overlap + EPS or fh <= overlap + EPS:
            return (10 ** 9, 0.0)
        n = len(axis_starts(poster_w, fw, overlap)) * len(axis_starts(poster_h, fh, overlap))
        return (n, n * fw * fh - poster_w * poster_h)

    p = count(min(paper_w, paper_h), max(paper_w, paper_h))
    l = count(max(paper_w, paper_h), min(paper_w, paper_h))
    return l < p
