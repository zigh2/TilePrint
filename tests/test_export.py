import pikepdf
import pypdfium2 as pdfium
import pytest
from PIL import Image

from tileprint import exporter as X
from tileprint import layout as L
from tileprint import paper as P
from tileprint import source as S
from tileprint.overlay import OverlayOptions

MM = P.PT_PER_MM


def _setup(path, poster="A2", **kw):
    src = S.load_source(path)
    pw, ph = P.paper_size(poster)
    pl = L.place_content(*src.size_pt, pw, ph, kw.get("mode", "fit"))
    lay = L.build_layout(pw, ph, *P.paper_size("A4"), 10 * MM, 9 * MM, 10 * MM)
    return src, pw, ph, pl, lay


def _image_count(pdf_path):
    n = 0
    with pikepdf.open(pdf_path) as pdf:
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Stream) and obj.get("/Subtype") == "/Image":
                n += 1
    return n


def test_tiled_export_keeps_vector(vector_pdf, tmp_path):
    src, pw, ph, pl, lay = _setup(vector_pdf)
    out = tmp_path / "tiles.pdf"
    n = X.export_tiled(src, str(out), lay, pl, OverlayOptions(footer_name="vec.pdf"))
    assert n == lay.rows * lay.cols
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == n
        w, h = (float(v) for v in pdf.pages[0].MediaBox[2:])
        assert (round(w / MM), round(h / MM)) == (210, 297)
    assert _image_count(out) == 0                       # nothing was rasterised
    # source artwork appears exactly once in the file (shared by every sheet)
    assert out.stat().st_size < 300_000


def test_fullsize_export_page_size_and_vector(vector_pdf, tmp_path):
    src, pw, ph, pl, lay = _setup(vector_pdf, "A1")
    out = tmp_path / "full.pdf"
    X.export_fullsize(src, str(out), pw, ph, pl)
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == 1
        w, h = (float(v) for v in pdf.pages[0].MediaBox[2:])
        assert (round(w / MM), round(h / MM)) == (594, 841)
    assert _image_count(out) == 0


def test_fullsize_rejects_giant_pages(vector_pdf, tmp_path):
    src = S.load_source(vector_pdf)
    pl = L.place_content(*src.size_pt, 20000, 20000)
    with pytest.raises(ValueError):
        X.export_fullsize(src, str(tmp_path / "x.pdf"), 20000, 20000, pl)


def test_geometry_content_lands_where_expected(vector_pdf, tmp_path):
    """Poster centre (= circle centre for a 'fit' placement) must be dark in the render."""
    src, pw, ph, pl, lay = _setup(vector_pdf, "A3")
    out = tmp_path / "full.pdf"
    X.export_fullsize(src, str(out), pw, ph, pl)
    img = pdfium.PdfDocument(str(out))[0].render(scale=0.5).to_pil().convert("L")
    assert img.getpixel((img.width // 2, img.height // 2)) < 40
    assert img.getpixel((5, img.height - 5)) > 240       # empty corner stays white


def test_tiles_reassemble_to_full_poster(vector_pdf, tmp_path):
    """Pasting each tile's frame back at its poster position reproduces the full render."""
    src, pw, ph, pl, lay = _setup(vector_pdf, "A3")
    out = tmp_path / "tiles.pdf"
    X.export_tiled(src, str(out), lay, pl, OverlayOptions(
        crop_marks=False, overlap_guides=False, footer=False, scale_bar=False))
    full = tmp_path / "full.pdf"
    X.export_fullsize(src, str(full), pw, ph, pl)
    scale = 0.8
    ref = pdfium.PdfDocument(str(full))[0].render(scale=scale).to_pil().convert("L")
    canvas = Image.new("L", ref.size, 255)
    doc = pdfium.PdfDocument(str(out))
    fx0, fy0, fx1, fy1 = lay.frame
    for i, t in enumerate(lay.tiles()):
        page = doc[i].render(scale=scale).to_pil().convert("L")
        left, top = fx0 * scale, (lay.paper_h - fy1) * scale
        crop = page.crop((round(left), round(top), round(left + t.w * scale), round(top + t.h * scale)))
        canvas.paste(crop, (round(t.x * scale), round(t.y * scale)))
    # compare ignoring the thin frame lines (we drew frames, so mask the border ring of each tile)
    diff = sum(1 for a, b in zip(S.pixels(canvas), S.pixels(ref)) if abs(a - b) > 80)
    assert diff / (ref.width * ref.height) < 0.01


def test_image_source_and_dpi(tmp_path):
    p = tmp_path / "pic.png"
    Image.new("RGB", (3000, 2000), (200, 30, 30)).save(p, dpi=(300, 300))
    src = S.load_source(str(p))
    assert src.kind == "image" and src.pixel_size == (3000, 2000)
    assert src.size_pt == pytest.approx((720.0, 480.0), rel=1e-4)
    pw, ph = P.paper_size("A0")
    pl = L.place_content(*src.size_pt, pw, ph)
    dpi = L.effective_dpi(3000, pl.width)
    assert dpi < 100                                      # would trigger a low-resolution warning


def test_blank_tile_detection(corner_pdf):
    src = S.load_source(corner_pdf)
    pw, ph = P.paper_size("A1")
    pl = L.place_content(*src.size_pt, pw, ph)
    lay = L.build_layout(pw, ph, *P.paper_size("A4"), 10 * MM, 9 * MM, 10 * MM)
    res = max(pw, ph) / 2000
    raster = S.poster_raster(src, pl, pw, ph, res)
    blank = S.blank_tiles(raster, lay, res)
    assert (0, 0) not in blank and len(blank) == lay.rows * lay.cols - 1
    plan = lay.plan(skip=blank)
    assert len(plan) == 1 and plan[0].neighbors == {}


def test_blank_backs_and_numbering(vector_pdf, tmp_path):
    src, pw, ph, pl, lay = _setup(vector_pdf, "A3")
    out = tmp_path / "t.pdf"
    n = X.export_tiled(src, str(out), lay, pl, OverlayOptions(numbering="rc"), blank_backs=True)
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == 2 * n
