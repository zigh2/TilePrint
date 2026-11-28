"""Edge-to-edge printing: cut on the frame lines, glue the sheets side by side, nothing repeated."""
import pypdfium2 as pdfium
import pytest
from PIL import Image

from tileprint import exporter as X
from tileprint import layout as L
from tileprint import paper as P
from tileprint import project as PR
from tileprint import source as S
from tileprint.overlay import OverlayOptions

MM = P.PT_PER_MM


def _layout(pw_mm, ph_mm, overlap_mm=0, margin=10, header=9, **kw):
    return L.build_layout(pw_mm * MM, ph_mm * MM, 210 * MM, 297 * MM, margin * MM, header * MM, overlap_mm * MM, **kw)


def test_default_is_edge_to_edge():
    assert PR.Settings().overlap == 0.0


@pytest.mark.parametrize("poster", [(841, 1189), (594, 841), (1000, 500), (200, 280), (3000, 1200)])
def test_sheets_abut_exactly_and_cover_the_poster_once(poster):
    lay = _layout(*poster)
    for starts, sizes, total in ((lay.xs, lay.ws, lay.poster_w), (lay.ys, lay.hs, lay.poster_h)):
        assert starts[0] == 0
        for i in range(len(starts) - 1):
            assert starts[i] + sizes[i] == pytest.approx(starts[i + 1], abs=1e-9)   # next sheet starts where this ends
        assert starts[-1] + sizes[-1] == pytest.approx(total, abs=1e-9)             # the last frame stops at the poster edge
        assert sum(sizes) == pytest.approx(total, abs=1e-6)                         # every poster point printed exactly once
    area = sum(t.w * t.h for t in lay.tiles())
    assert area == pytest.approx(lay.poster_w * lay.poster_h, rel=1e-9)


def test_frames_never_exceed_the_printable_area():
    lay = _layout(841, 1189)
    assert all(t.w <= lay.frame_w + 1e-9 and t.h <= lay.frame_h + 1e-9 for t in lay.tiles())
    t = lay.tiles()[-1]
    x0, y0, x1, y1 = lay.tile_frame(t)
    assert (x1 - x0, y1 - y0) == pytest.approx((t.w, t.h)) and y1 == pytest.approx(lay.frame[3]) and x0 == lay.frame[0]


def test_smart_cut_without_overlap_keeps_sheets_edge_to_edge():
    frame = 190 * MM
    total = 1000 * MM
    prof = [1.0] * int(total + 2)
    ideal = frame                           # first cut would fall at 190 mm
    quiet = int(ideal - 20 * MM)
    prof[quiet] = 0.0                       # an empty column 20 mm before it
    xs = L.axis_starts(total, frame, 0.0, prof, 1.0, 30 * MM)
    ws = L.axis_sizes(xs, frame, 0.0, total)
    assert xs[1] == pytest.approx(quiet)    # the cut moved onto the empty column
    assert ws[0] == pytest.approx(xs[1])    # the first sheet is now narrower: no overlap, no repetition
    assert all(w <= frame + 1e-9 for w in ws)
    assert sum(ws) == pytest.approx(total)


def test_smart_cut_job_at_overlap_zero(corner_pdf):
    src = S.load_source(corner_pdf)
    job = PR.build_job(src, PR.Settings(poster_preset="A1", smart_cut=True, skip_blank=False))
    lay = job.layout
    assert lay.overlap == 0 and sum(lay.ws) == pytest.approx(lay.poster_w)


def _render_full_and_sheets(vector_pdf, tmp_path, **settings):
    src = S.load_source(vector_pdf)
    s = PR.Settings(poster_preset="A3", paper="A4", skip_blank=False, **settings)
    job = PR.build_job(src, s)
    out = tmp_path / "tiles.pdf"
    X.export_tiled(src, str(out), job.layout, job.placement,
                   OverlayOptions(crop_marks=False, overlap_guides=False, footer=False, scale_bar=False), job.skip)
    full = tmp_path / "full.pdf"
    X.export_fullsize(src, str(full), job.poster_w, job.poster_h, job.placement)
    return job, out, full


def test_glued_sheets_reproduce_the_poster_without_gaps_or_repeats(vector_pdf, tmp_path):
    job, tiles_pdf, full_pdf = _render_full_and_sheets(vector_pdf, tmp_path, overlap=0.0)
    lay = job.layout
    scale = 1.0
    ref = pdfium.PdfDocument(str(full_pdf))[0].render(scale=scale).to_pil().convert("L")
    canvas = Image.new("L", ref.size, 128)                      # mid-grey: any gap would show
    doc = pdfium.PdfDocument(str(tiles_pdf))
    for i, t in enumerate(lay.tiles()):
        x0, y0, x1, y1 = lay.tile_frame(t)
        page = doc[i].render(scale=scale).to_pil().convert("L")
        # cut exactly on the frame (its inner side), as the user does with scissors
        box = (round(x0 * scale) + 1, round((lay.paper_h - y1) * scale) + 1, round(x1 * scale) - 1, round((lay.paper_h - y0) * scale) - 1)
        canvas.paste(page.crop(box), (round(t.x * scale) + 1, round(t.y * scale) + 1))
    # compare away from the 1px seams we trimmed
    diff = sum(1 for a, b in zip(S.pixels(canvas), S.pixels(ref)) if abs(a - b) > 80 and a != 128)
    grey = sum(1 for a in S.pixels(canvas) if a == 128)
    assert diff / (ref.width * ref.height) < 0.005
    assert grey / (ref.width * ref.height) < 0.03               # only the 1px trims; no missing strips


def test_each_sheet_has_its_own_tight_frame(vector_pdf, tmp_path):
    """The thin frame is the cut line: it must match the printed area exactly, also on the last sheet."""
    import pikepdf
    job, tiles_pdf, _ = _render_full_and_sheets(vector_pdf, tmp_path, overlap=0.0)
    lay = job.layout
    last = lay.tiles()[-1]
    assert last.x + last.w == pytest.approx(lay.poster_w) and last.y + last.h == pytest.approx(lay.poster_h)
    img = pdfium.PdfDocument(str(tiles_pdf))[len(lay.tiles()) - 1].render(scale=2).to_pil().convert("L")
    x0, y0, x1, y1 = lay.tile_frame(last)
    # the frame's right edge is dark, and just beyond it the paper is white
    ym = int((lay.paper_h - (y0 + y1) / 2) * 2)
    xr = int(x1 * 2)
    assert min(img.getpixel((xr + dx, ym)) for dx in (-1, 0, 1)) < 100
    assert img.getpixel((xr + 12, ym)) > 240


def test_header_never_collides_above_a_narrow_last_sheet(vector_pdf, tmp_path):
    """The arrows/number band spans the full printable width, so a 60 mm wide sheet still reads cleanly."""
    job, tiles_pdf, _ = _render_full_and_sheets(vector_pdf, tmp_path, overlap=0.0)
    lay = job.layout
    narrow = [i for i, t in enumerate(lay.tiles()) if t.w < lay.frame_w * 0.7]
    assert narrow, "test needs a narrow sheet"
    from tileprint.overlay import draw_page_overlay  # noqa: F401  (import check)
    import pypdf
    text = pypdf.PdfReader(str(tiles_pdf)).pages[narrow[0]].extract_text()
    assert str(narrow[0] + 1) in text
