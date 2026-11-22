"""Headless end-to-end check of the *frozen* app (CI) and for developers.

`TilePrint --selftest`       engine: PDF split/export, fonts + Arabic shaping, pdfium, Pillow, pikepdf
`TilePrint --selftest --ui`  additionally opens the real web view (hidden) and waits for the UI

Exit code 0 = OK. Optional log file: $TILEPRINT_SELFTEST_LOG.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import traceback
from pathlib import Path


def _engine(say) -> None:
    import pypdfium2 as pdfium
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl

    from . import exporter as X
    from . import source as S
    from .api import Api
    from .project import RasterCache, Settings, build_job

    tmp = tempfile.mkdtemp(prefix="tileprint_selftest_")
    pdf = os.path.join(tmp, "test.pdf")
    c = rl.Canvas(pdf, pagesize=A4)
    c.setFont("Helvetica-Bold", 30)
    c.drawString(40, 760, "TilePrint self-test")
    c.circle(300, 400, 120, fill=1)
    c.save()
    say("1 source PDF created")
    src = S.load_source(pdf)
    s = Settings(poster_preset="A1", smart_cut=True, skip_blank=True, numbering="rc",
                 footer_text="اختبار — selftest", language="ar")
    job = build_job(src, s, RasterCache())
    say(f"2 layout built: {job.layout.rows}x{job.layout.cols}, skipped {len(job.skip)}")
    out_t, out_f = os.path.join(tmp, "tiles.pdf"), os.path.join(tmp, "full.pdf")
    pages = X.export_tiled(src, out_t, job.layout, job.placement, job.overlay, job.skip)
    X.export_fullsize(src, out_f, job.poster_w, job.poster_h, job.placement)
    say(f"3 PDFs written ({pages} sheets)")
    doc = pdfium.PdfDocument(out_t)
    assert len(doc) == pages > 0
    doc[0].render(scale=0.5).to_pil().getbbox()
    doc.close()
    say("4 output re-opened and rendered")
    import openpyxl  # noqa: F401
    from openpyxl.worksheet.properties import PageSetupProperties  # noqa: F401
    say("5 spreadsheet support importable")
    api = Api("en")
    assert api.open_path(pdf)["ok"]
    st = api.update({"poster_preset": "A2"})
    assert st["job"]["total"] > 1
    assert api.preview_image()["url"].startswith("data:image/jpeg")
    assert api.render_region(0, 0, 500, 500, 400)["ok"] in (True, False)
    assert api.sheet_preview(1)["url"].startswith("data:image/png")
    say("6 UI back-end (state, preview, region render, sheet preview) OK")
    index = Path(__file__).parent / "assets" / "index.html"
    from .textutil import asset_path
    assert (asset_path() / "index.html").is_file() and (asset_path() / "ui" / "app.js").is_file(), index
    say("7 UI files bundled")


def _ui(say, timeout: float = 40.0) -> None:
    import webview

    from .api import Api
    from .textutil import asset_path

    api = Api("en")
    result = {"ok": False, "err": None}
    window = webview.create_window("TilePrint self-test", url=str(asset_path() / "index.html"),
                                   js_api=api, hidden=True, width=1200, height=800)
    api._bind(window)

    def probe(w):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                if w.evaluate_js("!!(window.TP && window.TP.ready === true)"):
                    result["ok"] = True
                    break
            except Exception as e:                      # page not ready yet
                result["err"] = str(e)
            time.sleep(0.5)
        try:
            w.destroy()
        except Exception:
            pass

    webview.start(probe, window, http_server=True)
    assert result["ok"], f"web view did not become ready: {result['err']}"
    say("8 web view started and the UI reported ready")


def selftest(ui: bool = False) -> int:
    log_path = os.environ.get("TILEPRINT_SELFTEST_LOG")
    lines: list[str] = []

    def say(msg: str) -> None:
        lines.append(msg)
        try:
            print(msg, flush=True)
        except Exception:               # windowed exe has no stdout
            pass

    code = 0
    try:
        _engine(say)
        if ui:
            _ui(say)
        say("SELFTEST OK")
    except Exception:
        say("SELFTEST FAILED\n" + traceback.format_exc())
        code = 1
    if log_path:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(selftest("--ui" in sys.argv))
