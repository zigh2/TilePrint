"""The application back-end. One `Api` instance backs the UI.

It is exposed to JavaScript by pywebview (`window.pywebview.api.<method>`) and, in browser
mode, over a small token-protected local HTTP server. Every public method takes and returns
JSON-serialisable values, so both transports behave identically. Everything not meant for
JavaScript starts with an underscore (pywebview exposes all public attributes).
"""
from __future__ import annotations

import base64
import io
import json
import os
import platform
import subprocess
import tempfile
import threading
from dataclasses import fields
from typing import Any, Optional

import pypdfium2 as pdfium

from . import __version__
from . import exporter as X
from . import paper as P
from . import source as S
from .project import (PROJECT_EXT, Job, RasterCache, Settings, build_job, load_project,
                      save_project)

_ENUMS = {
    "unit": {"mm", "cm", "in"},
    "poster_orient": {"auto", "portrait", "landscape"},
    "paper_orient": {"auto", "portrait", "landscape"},
    "scale_mode": {"fit", "fill", "stretch"},
    "numbering": {"seq", "rc"},
    "language": {"en", "ar"},
}
_BOOLS = {"lock_aspect", "crop_marks", "overlap_guides", "footer", "scale_bar", "smart_cut",
          "skip_blank", "blank_backs", "sheet_fit_one_page"}
_LENGTHS = {"poster_w": (10.0, 14400.0 * 40), "poster_h": (10.0, 14400.0 * 40),
            "margin": (0.0, 200.0), "header": (0.0, 200.0), "overlap": (0.0, 400.0)}


def _data_url(img, fmt: str = "JPEG", quality: int = 86) -> str:
    buf = io.BytesIO()
    if fmt == "JPEG":
        img.convert("RGB").save(buf, "JPEG", quality=quality, optimize=True)
        mime = "image/jpeg"
    else:
        img.save(buf, "PNG")
        mime = "image/png"
    return f"data:{mime};base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _default_language() -> str:
    import locale
    try:
        loc = (locale.getlocale()[0] or "").lower()
    except Exception:
        loc = ""
    return "ar" if loc.startswith("ar") else "en"


class Api:
    def __init__(self, language: Optional[str] = None) -> None:
        self._lock = threading.RLock()
        self._s = Settings(language=language or _default_language())
        self._src: Optional[S.Source] = None
        self._job: Optional[Job] = None
        self._error: Optional[str] = None
        self._cache = RasterCache()
        self._hist: list[dict] = [self._s.to_dict()]
        self._pos = 0
        self._previews: dict = {}
        self._regions: dict = {}
        self._window = None
        self._mode = "desktop"
        self._export = {"state": "idle", "done": 0, "total": 0, "path": None, "error": None, "kind": None}
        self._downloads: dict[str, str] = {}
        self._tmp = tempfile.mkdtemp(prefix="tileprint_")
        self._startup: Optional[str] = None

    # ------------------------------------------------------------------ plumbing
    @staticmethod
    def _open_types() -> tuple:
        """Open-dialog filters. pywebview's format: 'Description (*.ext;*.ext2)' with SEMICOLONS."""
        exts = ";".join(f"*{e}" for e in sorted({".pdf"} | S.IMAGE_EXTS | S.SHEET_EXTS))
        return (f"Supported files ({exts})", "All files (*.*)")

    @staticmethod
    def _project_types() -> tuple:
        return (f"TilePrint project (*{PROJECT_EXT})",)

    def _drop_open(self, path: str) -> None:
        """A file was dropped on the window (called from pywebview's DOM-event thread, which is the only
        place the real path is available). Opens it and tells the UI."""
        result = (self.open_project_path(path) if path.lower().endswith(PROJECT_EXT) else self.open_path(path))
        if self._window is not None:
            self._window.evaluate_js("window.TP && window.TP.afterExternalOpen(" + json.dumps(result, ensure_ascii=False) + ")")

    def _bind(self, window, mode: str = "desktop") -> None:
        self._window, self._mode = window, mode

    def _rebuild(self) -> None:
        self._error = None
        if not self._src:
            self._job = None
            return
        try:
            self._job = build_job(self._src, self._s, self._cache)
        except Exception as e:                      # layout errors are user-visible, not fatal
            self._job = None
            self._error = str(e)

    def _commit(self) -> None:
        snap = self._s.to_dict()
        if snap != self._hist[self._pos]:
            del self._hist[self._pos + 1:]
            self._hist.append(snap)
            self._pos += 1
            self._regions.clear()

    def _state(self, **extra) -> dict:
        s, src, job = self._s, self._src, self._job
        st: dict[str, Any] = {
            "ok": True, "version": __version__, "mode": self._mode,
            "settings": s.to_dict(), "error": self._error,
            "can_undo": self._pos > 0, "can_redo": self._pos < len(self._hist) - 1,
            "has_source": src is not None, "job": None, "source": None,
        }
        if src:
            st["source"] = {
                "name": os.path.basename(src.original_path), "path": src.original_path,
                "kind": src.kind, "page_count": src.page_count, "page_index": src.page_index,
                "size_pt": list(src.size_pt), "pixel_size": list(src.pixel_size) if src.pixel_size else None,
                "notes": list(src.notes),
            }
        if job:
            lay = job.layout
            plan = lay.plan(job.skip, s.numbering)
            by_key = {p.tile.key: p for p in plan}
            numbers = {p.label: p.number for p in plan}
            tiles = []
            for t in lay.tiles():
                p = by_key.get(t.key)
                tiles.append({
                    "row": t.row, "col": t.col, "x": t.x, "y": t.y, "w": t.w, "h": t.h,
                    "skipped": p is None,
                    "label": p.label if p else None, "number": p.number if p else None,
                    "nb": {k: numbers[v] for k, v in p.neighbors.items()} if p else {},
                })
            pl = job.placement
            st["job"] = {
                "poster": [job.poster_w, job.poster_h], "paper": [job.paper_w, job.paper_h],
                "placement": {"x": pl.x, "y": pl.y, "w": pl.width, "h": pl.height, "sx": pl.sx, "sy": pl.sy},
                "rows": lay.rows, "cols": lay.cols, "printed": len(plan), "total": lay.rows * lay.cols,
                "frame": [lay.frame_w, lay.frame_h], "xs": lay.xs, "ys": lay.ys,
                "overlap": lay.overlap, "tiles": tiles, "dpi": job.dpi, "scale": job.scale,
                "uniform_scale": abs(pl.sx - pl.sy) < 1e-6,
                "too_big_for_single_page": max(job.poster_w, job.poster_h) > X.MAX_PDF_PAGE_PT,
            }
        st.update(extra)
        return st

    # ------------------------------------------------------------------ session
    def startup_file(self) -> dict:
        """File given on the command line (consumed once by the UI after it loads)."""
        path, self._startup = self._startup, None
        return {"path": path}

    def init(self) -> dict:
        """Static data for building the UI (paper presets in mm) plus the current state."""
        groups = {"iso_a": [], "iso_b": [], "us": []}
        for name in P.PRESET_ORDER:
            w, h = P.PAPER_SIZES_PT[name]
            item = {"name": name, "w_mm": round(w / P.PT_PER_MM, 1), "h_mm": round(h / P.PT_PER_MM, 1)}
            groups["iso_a" if name.startswith("A") and name[1:].isdigit() else
                   "iso_b" if name.startswith("B") and name[1:].isdigit() else "us"].append(item)
        return {"presets": groups, "soffice": S.find_soffice() is not None,
                "platform": platform.system(), "state": self.get_state()}

    def get_state(self) -> dict:
        with self._lock:
            return self._state()

    # ------------------------------------------------------------------ source
    def open_dialog(self) -> dict:
        if not self._window:
            return {"ok": False, "error": "no window"}
        import webview
        res = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=False, file_types=self._open_types())
        if not res:
            return {"ok": True, "cancelled": True, "state": self.get_state()}
        return self.open_path(res[0])

    def open_path(self, path: str) -> dict:
        with self._lock:
            try:
                src = S.load_source(path, work_dir=os.path.join(self._tmp, f"src{len(self._previews)}"),
                                    sheet_fit_one_page=self._s.sheet_fit_one_page)
            except S.SourceError as e:
                return {"ok": False, "error": str(e)}
            except Exception as e:
                return {"ok": False, "error": f"Cannot open this file: {e}"}
            self._src = src
            self._s.page_index = 0
            self._s.offset = [0.0, 0.0]
            self._previews.clear()
            self._regions.clear()
            self._rebuild()
            self._commit()
            return {"ok": True, "state": self._state()}

    def set_page(self, index: int) -> dict:
        with self._lock:
            if self._src:
                self._src.page_index = max(0, min(int(index), self._src.page_count - 1))
                self._s.page_index = self._src.page_index
                self._s.offset = [0.0, 0.0]
                self._rebuild()
                self._commit()
            return self._state()

    # ------------------------------------------------------------------ settings
    def update(self, patch: dict) -> dict:
        with self._lock:
            s = self._s
            names = {f.name for f in fields(Settings)}
            clean: dict[str, Any] = {}
            for k, v in (patch or {}).items():
                if k not in names or k in ("offset", "page_index", "footer_text"):
                    if k == "footer_text":
                        clean[k] = str(v)[:200]
                    continue
                if k in _ENUMS:
                    if v in _ENUMS[k]:
                        clean[k] = v
                elif k in _BOOLS:
                    clean[k] = bool(v)
                elif k in _LENGTHS:
                    lo, hi = _LENGTHS[k]
                    clean[k] = min(max(float(v), lo), hi)
                elif k == "poster_preset":
                    if v == "Custom" or v in P.PAPER_SIZES_PT:
                        clean[k] = v
                elif k == "paper":
                    if v in P.PAPER_SIZES_PT:
                        clean[k] = v
            # entering "Custom": start from the current poster size
            if clean.get("poster_preset") == "Custom" and s.poster_preset != "Custom" and self._job:
                s.poster_w, s.poster_h = self._job.poster_w, self._job.poster_h
            lock = clean.get("lock_aspect", s.lock_aspect)
            if self._src and lock and ("poster_w" in clean) != ("poster_h" in clean):
                sw, sh = self._src.size_pt
                if "poster_w" in clean:
                    clean["poster_h"] = clean["poster_w"] * sh / sw
                else:
                    clean["poster_w"] = clean["poster_h"] * sw / sh
            need_reload = ("sheet_fit_one_page" in clean and clean["sheet_fit_one_page"] != s.sheet_fit_one_page
                           and self._src is not None and self._src.kind == "sheet")
            for k, v in clean.items():
                setattr(s, k, v)
            if need_reload:
                self._reload_source()
            self._rebuild()
            self._commit()
            return self._state()

    def _reload_source(self) -> None:
        old = self._src
        try:
            new = S.load_source(old.original_path, work_dir=os.path.join(self._tmp, f"re{len(self._previews)}"),
                                sheet_fit_one_page=self._s.sheet_fit_one_page)
            new.page_index = min(old.page_index, new.page_count - 1)
            self._src = new
            self._previews.clear()
            self._regions.clear()
        except Exception as e:
            self._error = str(e)

    def move_content(self, dx: float, dy: float) -> dict:
        with self._lock:
            self._s.offset = [self._s.offset[0] + float(dx), self._s.offset[1] + float(dy)]
            self._rebuild()
            self._commit()
            return self._state()

    def reset_position(self) -> dict:
        with self._lock:
            self._s.offset = [0.0, 0.0]
            self._rebuild()
            self._commit()
            return self._state()

    def undo(self) -> dict:
        return self._step(-1)

    def redo(self) -> dict:
        return self._step(1)

    def _step(self, d: int) -> dict:
        with self._lock:
            if 0 <= self._pos + d < len(self._hist):
                self._pos += d
                lang = self._s.language
                prev_fit = self._s.sheet_fit_one_page
                self._s = Settings.from_dict(self._hist[self._pos])
                self._s.language = lang
                if self._src:
                    if self._src.kind == "sheet" and self._s.sheet_fit_one_page != prev_fit:
                        self._reload_source()
                    self._src.page_index = min(self._s.page_index, self._src.page_count - 1)
                self._regions.clear()
                self._rebuild()
            return self._state()

    # ------------------------------------------------------------------ images
    def preview_image(self, max_px: int = 1600) -> dict:
        """Whole source page as a JPEG data URL (the base layer of the preview)."""
        with self._lock:
            if not self._src:
                return {"ok": False}
            key = (self._src.pdf_path, self._src.page_index, int(max_px))
            if key not in self._previews:
                img = S.render_page(self._src, int(max_px))
                self._previews[key] = {"ok": True, "url": _data_url(img), "w": img.width, "h": img.height}
            return self._previews[key]

    def render_region(self, rx: float, ry: float, rw: float, rh: float, out_px: int) -> dict:
        """Crisp re-render of a poster-space rectangle (zoomed preview of vector artwork)."""
        with self._lock:
            if not (self._src and self._job):
                return {"ok": False}
            pl = self._job.placement
            # intersect with the content rectangle
            x0, y0 = max(rx, pl.x), max(ry, pl.y)
            x1, y1 = min(rx + rw, pl.x + pl.width), min(ry + rh, pl.y + pl.height)
            if x1 - x0 < 1e-3 or y1 - y0 < 1e-3:
                return {"ok": False}
            key = (self._src.pdf_path, self._src.page_index, round(x0, 1), round(y0, 1),
                   round(x1, 1), round(y1, 1), int(out_px), round(pl.x, 1), round(pl.y, 1), round(pl.width, 1))
            if key in self._regions:
                return self._regions[key]
            sw, sh = self._src.size_pt
            # poster rect -> source-page rect (distances from the page's top-left)
            u0, u1 = (x0 - pl.x) / pl.sx, (x1 - pl.x) / pl.sx
            v0, v1 = (y0 - pl.y) / pl.sy, (y1 - pl.y) / pl.sy
            scale = min(max(out_px, 8), 3000) / max(u1 - u0, 1e-6)
            scale = min(scale, 3000 / max(v1 - v0, 1e-6))
            doc = pdfium.PdfDocument(self._src.pdf_path)
            try:
                page = doc[self._src.page_index]
                img = page.render(scale=scale, crop=(u0, sh - v1, sw - u1, v0)).to_pil()
            finally:
                doc.close()
            res = {"ok": True, "url": _data_url(img, quality=88), "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}
            if len(self._regions) > 24:
                self._regions.pop(next(iter(self._regions)))
            self._regions[key] = res
            return res

    def sheet_preview(self, number: int) -> dict:
        """Exact picture of one printed sheet (frame, arrows, footer ...)."""
        with self._lock:
            if not (self._src and self._job):
                return {"ok": False}
            job, src = self._job, self._src
        path = os.path.join(self._tmp, f"sheet_{number}.pdf")
        try:
            X.export_tiled(src, path, job.layout, job.placement, job.overlay, job.skip, only={int(number)})
            doc = pdfium.PdfDocument(path)
            try:
                img = doc[0].render(scale=1.8).to_pil()
            finally:
                doc.close()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        return {"ok": True, "url": _data_url(img, "PNG"), "w": img.width, "h": img.height}

    # ------------------------------------------------------------------ export
    def _save_dialog(self, name: str, ext: str, label: str) -> Optional[str]:
        import webview
        res = self._window.create_file_dialog(webview.FileDialog.SAVE, save_filename=name,
                                              file_types=(f"{label} (*{ext})",))
        if not res:
            return None
        path = res if isinstance(res, str) else res[0]
        return path if path.lower().endswith(ext) else path + ext

    def export(self, kind: str) -> dict:
        """kind: 'tiled' | 'full'. Desktop: asks where to save. Browser: prepares a download."""
        with self._lock:
            if not (self._src and self._job):
                return {"ok": False, "error": "Nothing to export"}
            if self._export["state"] == "running":
                return {"ok": False, "error": "An export is already running"}
            base = os.path.splitext(os.path.basename(self._src.original_path))[0]
            name = f"{base}_{'tiles' if kind == 'tiled' else 'full'}.pdf"
        if self._mode == "desktop" and self._window:
            path = self._save_dialog(name, ".pdf", "PDF")
            if not path:
                return {"ok": True, "cancelled": True}
        else:
            path = os.path.join(self._tmp, name)
        with self._lock:
            job, src, s = self._job, self._src, self._s
            self._export = {"state": "running", "done": 0, "total": job.layout.rows * job.layout.cols,
                            "path": path, "error": None, "kind": kind}
        threading.Thread(target=self._run_export, args=(kind, path, job, src, s.blank_backs), daemon=True).start()
        return {"ok": True, "started": True}

    def _run_export(self, kind: str, path: str, job: Job, src: S.Source, blank_backs: bool) -> None:
        def progress(i: int, n: int) -> None:
            self._export.update(done=i, total=n)
        try:
            if kind == "tiled":
                X.export_tiled(src, path, job.layout, job.placement, job.overlay, job.skip,
                               blank_backs=blank_backs, progress=progress)
            else:
                X.export_fullsize(src, path, job.poster_w, job.poster_h, job.placement)
            size = os.path.getsize(path)
            token = os.path.basename(path)
            self._downloads[token] = path
            self._export.update(state="done", size=size, token=token,
                                done=self._export.get("total", 0))
        except Exception as e:
            self._export.update(state="error", error=str(e))

    def export_status(self) -> dict:
        return dict(self._export)

    def reveal(self, path: str) -> dict:
        """Show a file in the system file manager (desktop only)."""
        try:
            if not os.path.exists(path):
                return {"ok": False}
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
            elif system == "Darwin":
                subprocess.Popen(["open", "-R", path])
            else:
                subprocess.Popen(["xdg-open", os.path.dirname(path)])
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------------ projects
    def save_project_dialog(self) -> dict:
        if not (self._window and self._src):
            return {"ok": False, "error": "Open a file first"}
        base = os.path.splitext(os.path.basename(self._src.original_path))[0]
        path = self._save_dialog(base + PROJECT_EXT, PROJECT_EXT, "TilePrint project")
        if not path:
            return {"ok": True, "cancelled": True}
        save_project(path, self._s, self._src.original_path)
        return {"ok": True, "path": path}

    def open_project_dialog(self) -> dict:
        if not self._window:
            return {"ok": False, "error": "no window"}
        import webview
        res = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=False,
                                              file_types=self._project_types())
        if not res:
            return {"ok": True, "cancelled": True, "state": self.get_state()}
        return self.open_project_path(res[0])

    def open_project_path(self, path: str) -> dict:
        with self._lock:
            try:
                s, src_path = load_project(path)
            except Exception as e:
                return {"ok": False, "error": f"Cannot read project: {e}"}
            lang = self._s.language
            if src_path and os.path.exists(src_path):
                r = self.open_path(src_path)
                if not r.get("ok"):
                    return r
            self._s = s
            self._s.language = lang
            if self._src:
                self._src.page_index = min(s.page_index, self._src.page_count - 1)
            self._regions.clear()
            self._rebuild()
            self._commit()
            return {"ok": True, "state": self._state(),
                    "missing_source": bool(src_path) and not os.path.exists(src_path)}

    def project_text(self) -> dict:
        """Project JSON as text (browser mode downloads it)."""
        if not self._src:
            return {"ok": False}
        return {"ok": True, "text": json.dumps({"version": 1, "source": self._src.original_path,
                                                 "settings": self._s.to_dict()}, ensure_ascii=False, indent=2)}
