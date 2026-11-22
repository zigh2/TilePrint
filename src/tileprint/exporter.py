"""Write the tiled PDF (and the single full-size PDF) with pikepdf.

The source page is wrapped as a Form XObject *once* and every output sheet merely
references it with its own transform + clip.  Nothing is rasterised, so vector
artwork and text stay vector at any poster size, and the file size stays close
to the source's.
"""
from __future__ import annotations

import os
import tempfile
from typing import Callable, Optional

import pikepdf
from pikepdf import Dictionary, Name, Pdf, Stream

from .layout import Placement, TileLayout
from .overlay import OverlayOptions, build_overlay_pdf
from .source import Source

MAX_PDF_PAGE_PT = 14400.0   # 200 in: the limit most PDF readers/RIPs honour
Progress = Optional[Callable[[int, int], None]]


def _form_geometry(form: Stream) -> tuple[float, float, float, float]:
    """(origin_x, origin_y, width, height) of the form's BBox after its /Matrix."""
    bx0, by0, bx1, by1 = (float(v) for v in form.BBox)
    m = pikepdf.Matrix(*(float(v) for v in form.get("/Matrix", [1, 0, 0, 1, 0, 0])))
    pts = [m.transform((x, y)) for x in (bx0, bx1) for y in (by0, by1)]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _source_form(out: Pdf, src: Source) -> tuple[Stream, tuple[float, float, float, float]]:
    sp = Pdf.open(src.pdf_path)
    form = sp.pages[src.page_index].as_form_xobject()
    geom = _form_geometry(form)
    return out.copy_foreign(form), geom


def _draw_source(out: Pdf, page: pikepdf.Page, form: Stream, geom, pl: Placement,
                 poster_w: float, poster_h: float,
                 frame: tuple[float, float, float, float], tile_xy: tuple[float, float]) -> None:
    """Place the source on `page` so poster point (tile_xy) lands at the frame's top-left."""
    ox, oy, _w, h_src = geom
    x0, y0, x1, y1 = frame
    tx, ty = tile_xy
    # source (a, b) -> page (sx*a + e, sy*b + f)   (derivation in README / tests)
    e = x0 + pl.x - tx - ox * pl.sx
    f = y1 - pl.y + ty - h_src * pl.sy - oy * pl.sy
    # clip = frame ∩ poster rectangle
    cx0 = x0
    cx1 = min(x1, x0 + poster_w - tx)
    cy1 = y1
    cy0 = max(y0, y1 - (poster_h - ty))
    page.obj.Resources = Dictionary(XObject=Dictionary(Src=form))
    ops = (f"q {cx0:.4f} {cy0:.4f} {cx1 - cx0:.4f} {cy1 - cy0:.4f} re W n "
           f"{pl.sx:.8f} 0 0 {pl.sy:.8f} {e:.4f} {f:.4f} cm /Src Do Q\n").encode()
    page.contents_add(Stream(out, ops), prepend=False)


def _finish(out: Pdf, path: str, title: str) -> None:
    with out.open_metadata() as meta:
        meta["dc:title"] = title
        meta["xmp:CreatorTool"] = "TilePrint"
    out.docinfo["/Title"] = title
    out.docinfo["/Creator"] = "TilePrint"
    out.save(path, compress_streams=True,
             object_stream_mode=pikepdf.ObjectStreamMode.generate)


def export_tiled(src: Source, out_path: str, layout: TileLayout, pl: Placement,
                 opt: OverlayOptions, skip: Optional[set] = None,
                 blank_backs: bool = False, progress: Progress = None,
                 only: Optional[set] = None) -> int:
    """Write the tiled PDF; returns the number of tile sheets (excluding blank backs).

    `only` (set of page numbers) restricts output, used for the single-page preview.
    """
    plan = layout.plan(skip, opt.numbering)
    if not plan:
        raise ValueError("nothing to print: every tile is blank or skipped")
    out = Pdf.new()
    form, geom = _source_form(out, src)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.close()
    try:
        build_overlay_pdf(tmp.name, layout, plan, opt)
        ov = Pdf.open(tmp.name)
        for i, pp in enumerate(plan):
            if only is not None and pp.number not in only:
                continue
            page = out.add_blank_page(page_size=(layout.paper_w, layout.paper_h))
            _draw_source(out, page, form, geom, pl, layout.poster_w, layout.poster_h,
                         layout.frame, (pp.tile.x, pp.tile.y))
            page.add_overlay(ov.pages[i])
            if blank_backs:
                out.add_blank_page(page_size=(layout.paper_w, layout.paper_h))
            if progress:
                progress(i + 1, len(plan))
        _finish(out, out_path, opt.footer_name or "TilePrint tiles")
        ov.close()
    finally:
        os.unlink(tmp.name)
    return len(plan)


def export_fullsize(src: Source, out_path: str, poster_w: float, poster_h: float,
                    pl: Placement) -> None:
    """One page at the full poster size (for plotters / print shops). Vector kept."""
    if max(poster_w, poster_h) > MAX_PDF_PAGE_PT:
        raise ValueError(
            "The poster is larger than 200 in (5.08 m); most PDF readers and RIPs cannot open "
            "a single page that big. Use the tiled export, or reduce the size.")
    out = Pdf.new()
    form, geom = _source_form(out, src)
    page = out.add_blank_page(page_size=(poster_w, poster_h))
    # Treat the whole poster as one tile whose frame is the page.
    _draw_source(out, page, form, geom, pl, poster_w, poster_h,
                 (0.0, 0.0, poster_w, poster_h), (0.0, 0.0))
    _finish(out, out_path, os.path.splitext(os.path.basename(src.original_path))[0])
