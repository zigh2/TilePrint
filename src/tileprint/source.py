"""Turn PDF / image / spreadsheet inputs into one normalised vector-first PDF source."""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pypdfium2 as pdfium
from PIL import Image, ImageOps

from .layout import Placement, TileLayout

Image.MAX_IMAGE_PIXELS = None  # large posters are legitimate

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
SHEET_EXTS = {".xlsx", ".xlsm", ".xls", ".ods", ".csv"}
DEFAULT_IMAGE_DPI = 96.0


class SourceError(Exception):
    pass


@dataclass
class Source:
    original_path: str
    pdf_path: str                       # normalised PDF the exporter reads
    kind: str                           # 'pdf' | 'image' | 'sheet'
    page_count: int
    page_index: int = 0
    sizes_pt: list = field(default_factory=list)      # per page (w, h)
    pixel_size: Optional[tuple] = None  # only for raster images
    notes: list = field(default_factory=list)

    @property
    def size_pt(self) -> tuple[float, float]:
        return self.sizes_pt[self.page_index]

    @property
    def is_raster(self) -> bool:
        return self.kind == "image"


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_source(path: str, work_dir: Optional[str] = None, sheet_fit_one_page: bool = True) -> Source:
    p = Path(path)
    if not p.is_file():
        raise SourceError(f"File not found: {path}")
    ext = p.suffix.lower()
    work = Path(work_dir or tempfile.mkdtemp(prefix="tileprint_"))
    work.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    pixel_size = None

    if ext == ".pdf":
        pdf_path, kind = str(p), "pdf"
    elif ext in IMAGE_EXTS:
        pdf_path, pixel_size = _image_to_pdf(p, work)
        kind = "image"
    elif ext in SHEET_EXTS:
        pdf_path = _sheet_to_pdf(p, work, sheet_fit_one_page, notes)
        kind = "sheet"
    else:
        raise SourceError(f"Unsupported file type: {ext}")

    try:
        doc = pdfium.PdfDocument(pdf_path)
    except Exception as e:  # password-protected / corrupt
        raise SourceError(f"Cannot open PDF: {e}") from e
    try:
        sizes = [tuple(doc[i].get_size()) for i in range(len(doc))]
    finally:
        doc.close()
    if not sizes:
        raise SourceError("The document has no pages")
    return Source(str(p), pdf_path, kind, len(sizes), 0, sizes, pixel_size, notes)


def _image_to_pdf(p: Path, work: Path) -> tuple[str, tuple[int, int]]:
    from reportlab.pdfgen import canvas

    with Image.open(p) as im:
        dpi = im.info.get("dpi", (None, None))[0]
        orientation = im.getexif().get(0x0112, 1)
        if orientation not in (None, 1):          # honour EXIF rotation
            im = ImageOps.exif_transpose(im)
            src_for_pdf = work / (p.stem + "_oriented.png")
            im.save(src_for_pdf)
        else:
            src_for_pdf = p
        w_px, h_px = im.size
        has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
        if im.mode in ("P", "CMYK", "I;16", "I", "F") and src_for_pdf == p:
            src_for_pdf = work / (p.stem + "_rgb.png")   # formats reportlab handles poorly
            im.convert("RGBA" if has_alpha else "RGB").save(src_for_pdf)
    if not dpi or dpi < 30:
        dpi = DEFAULT_IMAGE_DPI
    w_pt, h_pt = w_px * 72.0 / dpi, h_px * 72.0 / dpi
    out = work / (p.stem + ".pdf")
    c = canvas.Canvas(str(out), pagesize=(w_pt, h_pt), pageCompression=1)
    c.drawImage(str(src_for_pdf), 0, 0, w_pt, h_pt, mask="auto" if has_alpha else None)
    c.showPage()
    c.save()
    return str(out), (w_px, h_px)


def find_soffice() -> Optional[str]:
    for name in ("soffice", "libreoffice"):
        hit = shutil.which(name)
        if hit:
            return hit
    for cand in (
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        "/usr/bin/soffice", "/usr/local/bin/soffice", "/opt/libreoffice/program/soffice",
    ):
        if os.path.exists(cand):
            return cand
    return None


def _xlsx_has_drawings(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return any(n.startswith(("xl/charts/", "xl/media/", "xl/drawings/")) for n in z.namelist())
    except zipfile.BadZipFile:
        return False


def _sheet_to_pdf(p: Path, work: Path, fit_one_page: bool, notes: list) -> str:
    soffice = find_soffice()
    if not soffice:
        raise SourceError(
            "LibreOffice is required to open spreadsheets (https://www.libreoffice.org/download). "
            "Install it, or export the sheet to PDF yourself and open that.")
    src = p
    if fit_one_page and p.suffix.lower() in (".xlsx", ".xlsm"):
        if _xlsx_has_drawings(p):
            notes.append("sheet_has_charts_not_fitted")   # openpyxl would drop charts/images
        else:
            try:
                import openpyxl
                from openpyxl.worksheet.properties import PageSetupProperties
                wb = openpyxl.load_workbook(p)
                for ws in wb.worksheets:
                    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
                    ws.page_setup.fitToWidth = 1
                    ws.page_setup.fitToHeight = 1
                    if ws.max_column > ws.max_row:
                        ws.page_setup.orientation = "landscape"
                src = work / (p.stem + "_fit.xlsx")
                wb.save(src)
            except Exception as e:  # fall back to the untouched file
                notes.append(f"sheet_fit_failed:{e}")
                src = p
    profile = work / "lo_profile"
    cmd = [soffice, f"-env:UserInstallation={profile.as_uri()}", "--headless",
           "--convert-to", "pdf", "--outdir", str(work), str(src)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=240)
    except subprocess.TimeoutExpired as e:
        raise SourceError("LibreOffice timed out converting the spreadsheet") from e
    except subprocess.CalledProcessError as e:
        raise SourceError(f"LibreOffice failed: {e.stderr.decode(errors='replace')[:300]}") from e
    out = work / (Path(src).stem + ".pdf")
    if not out.exists():
        raise SourceError("LibreOffice produced no PDF")
    return str(out)


# --------------------------------------------------------------------------- #
# rasters: preview, ink profiles, blank-tile detection
# --------------------------------------------------------------------------- #
def render_page(src: Source, max_side_px: int = 1600) -> Image.Image:
    """Raster of the selected source page for on-screen preview (RGB)."""
    w, h = src.size_pt
    scale = max_side_px / max(w, h)
    doc = pdfium.PdfDocument(src.pdf_path)
    try:
        bmp = doc[src.page_index].render(scale=scale)
        img = bmp.to_pil().convert("RGB")
    finally:
        doc.close()
    return img


def poster_raster(src: Source, pl: Placement, poster_w: float, poster_h: float,
                  res: float) -> Image.Image:
    """Greyscale poster-space raster (white paper) at `res` points per pixel."""
    cw, ch = max(1, round(pl.width / res)), max(1, round(pl.height / res))
    pw, ph = max(1, round(poster_w / res)), max(1, round(poster_h / res))
    page = render_page(src, max_side_px=min(4000, max(cw, ch)))
    page = page.convert("L").resize((cw, ch), Image.BILINEAR)
    canvas = Image.new("L", (pw, ph), 255)
    canvas.paste(page, (round(pl.x / res), round(pl.y / res)))
    return canvas


def pixels(img: Image.Image) -> list:
    """Flat pixel list (works before and after Pillow deprecated getdata)."""
    getter = getattr(img, "get_flattened_data", None) or img.getdata
    return list(getter())


INK_LEVEL = 240   # grey values below this count as ink


def ink_profiles(raster: Image.Image) -> tuple[list[float], list[float]]:
    """(per-column ink, per-row ink), each 0..1."""
    ink = raster.point(lambda v: 255 if v < INK_LEVEL else 0)
    cols = ink.resize((ink.width, 1), Image.BOX)
    rows = ink.resize((1, ink.height), Image.BOX)
    return [v / 255.0 for v in pixels(cols)], [v / 255.0 for v in pixels(rows)]


def blank_tiles(raster: Image.Image, layout: TileLayout, res: float) -> set:
    """(row, col) of tiles whose frame area holds no ink at all."""
    ink = raster.point(lambda v: 255 if v < INK_LEVEL else 0)
    blank = set()
    for t in layout.tiles():
        box = (max(0, int(t.x / res)), max(0, int(t.y / res)),
               min(ink.width, int((t.x + t.w) / res) + 1), min(ink.height, int((t.y + t.h) / res) + 1))
        if box[2] <= box[0] or box[3] <= box[1] or ink.crop(box).getbbox() is None:
            blank.add(t.key)
    return blank
