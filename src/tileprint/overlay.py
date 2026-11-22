"""Vector overlay drawn on every tile sheet (thin frame, neighbour arrows, guides, footer)."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import Optional

from reportlab.pdfgen import canvas

from .i18n import tr
from .layout import PlannedPage, TileLayout
from .paper import PT_PER_CM, PT_PER_INCH, PT_PER_MM
from .textutil import draw_text, fit_text, register_fonts, text_width


@dataclass
class OverlayOptions:
    numbering: str = "seq"            # 'seq' | 'rc'
    crop_marks: bool = True
    overlap_guides: bool = True       # dashed lines + crosses showing where neighbours sit
    footer: bool = True
    scale_bar: bool = True
    imperial_bar: bool = False        # 2 in bar instead of 5 cm
    footer_name: str = ""
    scale_text: str = ""              # e.g. "×2.50"; empty hides it
    language: str = "en"


def _triangle(c, cx: float, cy: float, size: float, direction: str) -> None:
    h = size / 2
    pts = {
        "left":  [(cx + h, cy - h), (cx + h, cy + h), (cx - h, cy)],
        "right": [(cx - h, cy - h), (cx - h, cy + h), (cx + h, cy)],
        "up":    [(cx - h, cy - h), (cx + h, cy - h), (cx, cy + h)],
        "down":  [(cx - h, cy + h), (cx + h, cy + h), (cx, cy - h)],
    }[direction]
    p = c.beginPath()
    p.moveTo(*pts[0])
    p.lineTo(*pts[1])
    p.lineTo(*pts[2])
    p.close()
    c.drawPath(p, stroke=0, fill=1)


def _actual_overlaps(layout: TileLayout, row: int, col: int) -> dict:
    """Real overlap with each neighbour (smart cuts can make it larger than nominal)."""
    fw, fh = layout.frame_w, layout.frame_h
    out = {}
    if col > 0:
        out["left"] = layout.xs[col - 1] + fw - layout.xs[col]
    if col < layout.cols - 1:
        out["right"] = layout.xs[col] + fw - layout.xs[col + 1]
    if row > 0:
        out["up"] = layout.ys[row - 1] + fh - layout.ys[row]
    if row < layout.rows - 1:
        out["down"] = layout.ys[row] + fh - layout.ys[row + 1]
    return out


def draw_page_overlay(c: canvas.Canvas, layout: TileLayout, page: PlannedPage,
                      opt: OverlayOptions) -> None:
    x0, y0, x1, y1 = layout.frame
    pw, ph = layout.paper_w, layout.paper_h
    m, hdr = layout.margin, layout.header
    black = 0

    # ---- thin frame -------------------------------------------------------
    c.setStrokeGray(black)
    c.setFillGray(black)
    c.setLineWidth(0.4)
    c.rect(x0, y0, x1 - x0, y1 - y0, stroke=1, fill=0)

    # ---- crop marks -------------------------------------------------------
    if opt.crop_marks and m >= 3 * PT_PER_MM:
        gap, ln = 1.0 * PT_PER_MM, min(m - 1 * PT_PER_MM, 5 * PT_PER_MM) - 1.0 * PT_PER_MM
        ln = max(ln, 1.5 * PT_PER_MM)
        c.setLineWidth(0.3)
        for x in (x0, x1):
            c.line(x, y0 - gap, x, y0 - gap - ln)                 # below
            if hdr > 0:
                c.line(x, y1 + gap, x, y1 + gap + min(ln, 2.5 * PT_PER_MM))   # above (short)
        for y in (y0, y1):
            c.line(x0 - gap, y, x0 - gap - ln, y)
            c.line(x1 + gap, y, x1 + gap + ln, y)

    # ---- overlap guides + junction crosses ---------------------------------
    if opt.overlap_guides:
        ov = _actual_overlaps(layout, page.tile.row, page.tile.col)
        c.setStrokeGray(0.45)
        c.setLineWidth(0.3)
        c.setDash(3, 2)
        pos = {}
        if "left" in page.neighbors and "left" in ov:
            pos["left"] = x0 + ov["left"]
            c.line(pos["left"], y0, pos["left"], y1)
        if "right" in page.neighbors and "right" in ov:
            pos["right"] = x1 - ov["right"]
            c.line(pos["right"], y0, pos["right"], y1)
        if "up" in page.neighbors and "up" in ov:
            pos["up"] = y1 - ov["up"]
            c.line(x0, pos["up"], x1, pos["up"])
        if "down" in page.neighbors and "down" in ov:
            pos["down"] = y0 + ov["down"]
            c.line(x0, pos["down"], x1, pos["down"])
        c.setDash()
        c.setStrokeGray(black)
        c.setLineWidth(0.4)
        arm = 2.5 * PT_PER_MM
        for hx in ("left", "right"):
            for hy in ("up", "down"):
                if hx in pos and hy in pos:
                    cx_, cy_ = pos[hx], pos[hy]
                    c.line(cx_ - arm, cy_, cx_ + arm, cy_)
                    c.line(cx_, cy_ - arm, cx_, cy_ + arm)

    # ---- header: neighbour arrows + current page ---------------------------
    if hdr > 0:
        fs = max(6.0, min(11.0, hdr * 0.55))
        tri = fs * 0.8
        base = y1 + (hdr - fs * 0.72) / 2 - 0.5          # text baseline in the band
        mid = base + fs * 0.36
        inset = 3 * PT_PER_MM
        cxp = (x0 + x1) / 2

        center_txt = page.label if opt.numbering == "rc" else f"{page.number}"
        small = f"/ {page.total}" if opt.numbering == "seq" else f"{page.number}/{page.total}"
        big_fs = fs * 1.35
        w_big = text_width(center_txt, big_fs, True)
        w_small = text_width(small, fs * 0.8)
        total_w = w_big + 3 + w_small
        draw_text(c, cxp - total_w / 2, base - 0.5, center_txt, big_fs, True)
        draw_text(c, cxp - total_w / 2 + w_big + 3, base, small, fs * 0.8)
        left_edge, right_edge = cxp - total_w / 2, cxp + total_w / 2

        gap = 2.5
        # horizontal neighbours at the outer ends of the frame
        if "left" in page.neighbors:
            _triangle(c, x0 + inset + tri / 2, mid, tri, "left")
            draw_text(c, x0 + inset + tri + gap, base, page.neighbors["left"], fs, True)
        if "right" in page.neighbors:
            t = page.neighbors["right"]
            draw_text(c, x1 - inset - tri - gap, base, t, fs, True, align="right")
            _triangle(c, x1 - inset - tri / 2, mid, tri, "right")
        # vertical neighbours next to the page number
        if "up" in page.neighbors:
            t = page.neighbors["up"]
            wt = text_width(t, fs, True)
            xr = left_edge - 8
            draw_text(c, xr, base, t, fs, True, align="right")
            _triangle(c, xr - wt - gap - tri / 2, mid, tri, "up")
        if "down" in page.neighbors:
            t = page.neighbors["down"]
            xl = right_edge + 8
            _triangle(c, xl + tri / 2, mid, tri, "down")
            draw_text(c, xl + tri + gap, base, t, fs, True)

    # ---- footer -------------------------------------------------------------
    if opt.footer and m >= 5 * PT_PER_MM:
        fs = 6.5
        yb = m / 2 - fs * 0.35
        lang = opt.language
        left_w = (x1 - x0) * 0.38
        name = fit_text(opt.footer_name, fs, left_w) if opt.footer_name else ""
        if name:
            draw_text(c, x0, yb, name, fs)
        mid_txt = tr("page_of", lang, n=page.number, total=page.total) + "  (" + \
            tr("row_col", lang, r=page.tile.row + 1, c=page.tile.col + 1) + ")"
        draw_text(c, (x0 + x1) / 2, yb, mid_txt, fs, align="center")
        right_bits = []
        if opt.scale_text:
            right_bits.append(tr("scale", lang, s=opt.scale_text))
        right_bits.append(_dt.date.today().isoformat())
        right = "  ·  ".join(right_bits)
        draw_text(c, x1, yb, right, fs, align="right")
        # real-size scale bar (prints 1:1 on the sheet = true poster length)
        if opt.scale_bar:
            options = ([(2 * PT_PER_INCH, "2", "in"), (1 * PT_PER_INCH, "1", "in")] if opt.imperial_bar
                       else [(5 * PT_PER_CM, "5", "cm"), (3 * PT_PER_CM, "3", "cm"), (2 * PT_PER_CM, "2", "cm")])
            rw = text_width(right, fs)
            bx1 = x1 - rw - 10
            floor = (x0 + x1) / 2 + text_width(mid_txt, fs) / 2 + 12
            for length, v, u in options:
                label = tr("real_length", lang, v=v, u=u)
                bx0 = bx1 - length
                if bx0 - text_width(label, fs * 0.9) - 3 > floor:
                    c.setLineWidth(0.5)
                    c.line(bx0, yb + 1.0, bx1, yb + 1.0)
                    for x in (bx0, bx1):
                        c.line(x, yb - 1.2, x, yb + 3.2)
                    draw_text(c, bx0 - 3, yb, label, fs * 0.9, align="right")
                    break


def build_overlay_pdf(path: str, layout: TileLayout, pages: list[PlannedPage],
                      opt: OverlayOptions) -> None:
    register_fonts()
    c = canvas.Canvas(path, pagesize=(layout.paper_w, layout.paper_h), pageCompression=1)
    c.setTitle("TilePrint overlay")
    for page in pages:
        draw_page_overlay(c, layout, page, opt)
        c.showPage()
    c.save()
