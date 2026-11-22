"""TilePrint desktop GUI (PySide6). Arabic/English with RTL support."""
from __future__ import annotations

import os
import sys
import tempfile
from typing import Optional

import pypdfium2 as pdfium
from PySide6.QtCore import QLocale, QPointF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QFontDatabase, QImage,
                           QKeySequence, QPainter, QPen, QPixmap, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QDockWidget,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QGraphicsItem,
                               QGraphicsPixmapItem, QGraphicsRectItem, QGraphicsScene,
                               QGraphicsSimpleTextItem, QGraphicsView, QGroupBox, QLabel,
                               QLineEdit, QMainWindow, QMessageBox, QProgressDialog,
                               QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from . import exporter as X
from . import i18n
from . import source as S
from .i18n import tr
from .paper import PRESET_ORDER, UNITS, from_pt, to_pt
from .project import (PROJECT_EXT, Job, RasterCache, Settings, build_job, load_project,
                      save_project)
from .textutil import asset_path

i18n.register({
    "app_title": {"en": "TilePrint — poster tiling", "ar": "TilePrint — تقسيم الطباعة"},
    "open": {"en": "Open…", "ar": "فتح…"},
    "open_project": {"en": "Open project…", "ar": "فتح مشروع…"},
    "save_project": {"en": "Save project…", "ar": "حفظ المشروع…"},
    "undo": {"en": "Undo", "ar": "تراجع"}, "redo": {"en": "Redo", "ar": "إعادة"},
    "export_tiled": {"en": "Export tiled PDF…", "ar": "تصدير PDF مجزأ…"},
    "export_full": {"en": "Export full-size PDF…", "ar": "تصدير PDF بالمقاس الكامل…"},
    "language": {"en": "العربية", "ar": "English"},
    "g_source": {"en": "Source", "ar": "المصدر"},
    "g_poster": {"en": "Final size", "ar": "المقاس النهائي"},
    "g_paper": {"en": "Printer paper", "ar": "ورق الطباعة"},
    "g_options": {"en": "Options", "ar": "خيارات"},
    "no_source": {"en": "No file opened", "ar": "لا يوجد ملف"},
    "page": {"en": "Page", "ar": "الصفحة"},
    "paper": {"en": "Paper", "ar": "الورق"},
    "preset": {"en": "Size", "ar": "المقاس"}, "custom": {"en": "Custom", "ar": "مخصص"},
    "orientation": {"en": "Orientation", "ar": "الاتجاه"},
    "auto": {"en": "Automatic", "ar": "تلقائي"},
    "portrait": {"en": "Portrait", "ar": "طولي"}, "landscape": {"en": "Landscape", "ar": "عرضي"},
    "width": {"en": "Width", "ar": "العرض"}, "height": {"en": "Height", "ar": "الارتفاع"},
    "unit": {"en": "Unit", "ar": "الوحدة"},
    "lock_aspect": {"en": "Keep source proportions", "ar": "إبقاء نسبة المصدر"},
    "scale_mode": {"en": "Scaling", "ar": "التحجيم"},
    "fit": {"en": "Fit (whole source)", "ar": "ملاءمة (كل المصدر)"},
    "fill": {"en": "Fill (crop overflow)", "ar": "ملء (قص الزائد)"},
    "stretch": {"en": "Stretch", "ar": "تمديد"},
    "reset_pos": {"en": "Reset position", "ar": "إعادة الموضع"},
    "margin": {"en": "Printer margin", "ar": "هامش الطابعة"},
    "header": {"en": "Arrow band height", "ar": "ارتفاع شريط الأسهم"},
    "overlap": {"en": "Overlap", "ar": "التداخل"},
    "numbering": {"en": "Page numbering", "ar": "ترقيم الصفحات"},
    "seq": {"en": "Sequential (1, 2, 3)", "ar": "تسلسلي (1، 2، 3)"},
    "rc": {"en": "Row/column (A1, B2)", "ar": "صف/عمود (A1, B2)"},
    "crop_marks": {"en": "Crop marks", "ar": "علامات القص"},
    "guides": {"en": "Overlap ticks in the margin", "ar": "علامات التداخل في الهامش فقط"},
    "footer": {"en": "Footer (name, date, scale)", "ar": "تذييل (الاسم والتاريخ والمقياس)"},
    "scale_bar": {"en": "Real-size scale ruler", "ar": "مسطرة المقياس الفعلي"},
    "smart_cut": {"en": "Smart cut (avoid slicing content)", "ar": "قص ذكي (تجنب قطع المحتوى)"},
    "skip_blank": {"en": "Skip blank sheets", "ar": "تخطي الصفحات الفارغة"},
    "blank_backs": {"en": "Duplex printer: add blank backs", "ar": "طابعة وجهين: إضافة ظهر فارغ"},
    "footer_text": {"en": "Footer name", "ar": "اسم التذييل"},
    "sheet_fit": {"en": "Fit each sheet on one page", "ar": "ملاءمة كل ورقة عمل في صفحة"},
    "info_sheets": {"en": "{rows} × {cols} = {n} sheets · {p} to print",
                    "ar": "{rows} × {cols} = {n} ورقة · {p} للطباعة"},
    "info_size": {"en": "Poster {w} × {h} {u} · scale ×{s}", "ar": "الملصق {w} × {h} {u} · المقياس ×{s}"},
    "dpi_ok": {"en": "Image resolution: {d} DPI", "ar": "دقة الصورة: {d} DPI"},
    "dpi_warn": {"en": "Low resolution: only {d} DPI at this size",
                 "ar": "دقة منخفضة: {d} DPI فقط عند هذا المقاس"},
    "open_title": {"en": "Open PDF, image or spreadsheet", "ar": "فتح PDF أو صورة أو جدول"},
    "filter_src": {"en": "Supported files", "ar": "الملفات المدعومة"},
    "filter_pdf": {"en": "PDF files (*.pdf)", "ar": "ملفات PDF (*.pdf)"},
    "export_done": {"en": "Saved: {p}", "ar": "تم الحفظ: {p}"},
    "error": {"en": "Error", "ar": "خطأ"},
    "working": {"en": "Writing PDF…", "ar": "جارٍ كتابة الملف…"},
    "cancel": {"en": "Cancel", "ar": "إلغاء"},
    "page_preview": {"en": "Sheet {n}", "ar": "الورقة {n}"},
    "hint": {"en": "Drag the content to move it · wheel = zoom · double-click a sheet to preview it",
             "ar": "اسحب المحتوى لتحريكه · العجلة للتكبير · انقر مرتين على ورقة لمعاينتها"},
    "note_charts": {"en": "The sheet has charts/images, so it was not auto-fitted to one page.",
                    "ar": "الجدول يحتوي مخططات/صوراً، لذا لم تُضبط الصفحة تلقائياً."},
})

BLUE = QColor(30, 100, 210)


def pil_to_pixmap(img) -> QPixmap:
    img = img.convert("RGBA")
    qimg = QImage(img.tobytes("raw", "RGBA"), img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg.copy())


class ContentItem(QGraphicsPixmapItem):
    def __init__(self, pix: QPixmap, parent, on_release):
        super().__init__(pix, parent)
        self._cb = on_release
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self._cb(self.pos())


class PreviewView(QGraphicsView):
    doubleClickedAt = Signal(QPointF)

    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QBrush(QColor(90, 94, 102)))

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 1 / 1.15
        self.scale(f, f)

    def mouseDoubleClickEvent(self, e):
        self.doubleClickedAt.emit(self.mapToScene(e.position().toPoint()))


class ExportWorker(QThread):
    progress = Signal(int, int)
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, fn, path: str):
        super().__init__()
        self._fn, self._path = fn, path

    def run(self):
        try:
            self._fn(lambda i, n: self.progress.emit(i, n))
            self.done.emit(self._path)
        except Exception as e:  # surfaced to the user
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, lang: str = "en"):
        super().__init__()
        self.settings = Settings(language=lang)
        self.src: Optional[S.Source] = None
        self.job: Optional[Job] = None
        self._pix: Optional[QPixmap] = None
        self._pix_key = None
        self._cache = RasterCache()
        self._loading = False
        self._last_poster = None
        self._history: list[dict] = [self.settings.to_dict()]
        self._pos = 0
        self._worker: Optional[ExportWorker] = None
        self._timer = QTimer(self, singleShot=True, interval=250)
        self._timer.timeout.connect(self._commit)
        self.scene = QGraphicsScene(self)
        self.view = PreviewView(self.scene)
        self.view.doubleClickedAt.connect(self._open_sheet_preview)
        self.setCentralWidget(self.view)
        self._build_panel()
        self._build_actions()
        self.statusBar()
        self.resize(1280, 820)
        self._retranslate()
        self._fill_widgets()
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_actions(self):
        self.act = {}
        spec = [("open", "Ctrl+O", self.open_dialog), ("open_project", None, self.open_project_dialog),
                ("save_project", "Ctrl+S", self.save_project_dialog),
                ("undo", "Ctrl+Z", self.undo), ("redo", "Ctrl+Y", self.redo),
                ("export_tiled", "Ctrl+E", self.export_tiled),
                ("export_full", "Ctrl+Shift+E", self.export_full),
                ("language", None, self.toggle_language)]
        tb = self.addToolBar("main")
        tb.setMovable(False)
        for key, sc, fn in spec:
            a = QAction(self)
            if sc:
                a.setShortcut(QKeySequence(sc))
            a.triggered.connect(fn)
            tb.addAction(a)
            self.act[key] = a
        redo2 = QAction(self)
        redo2.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        redo2.triggered.connect(self.redo)
        self.addAction(redo2)

    def _build_panel(self):
        self.w = {}
        self.lbl = {}
        self.groups = {}
        host = QWidget()
        col = QVBoxLayout(host)

        def group(key):
            g = QGroupBox()
            f = QFormLayout(g)
            f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            self.groups[key] = g
            col.addWidget(g)
            return f

        def row(form, key, widget, label_key=None):
            lab = QLabel()
            self.lbl[label_key or key] = lab
            self.w[key] = widget
            form.addRow(lab, widget)
            return widget

        def spin(minv, maxv, step=1.0):
            s = QDoubleSpinBox()
            s.setRange(minv, maxv)
            s.setSingleStep(step)
            s.setDecimals(2)
            s.setKeyboardTracking(False)
            s.valueChanged.connect(self._on_widget)
            return s

        def combo(items):
            c = QComboBox()
            for data in items:
                c.addItem(data, data)
            c.currentIndexChanged.connect(self._on_widget)
            return c

        def check(key):
            c = QCheckBox()
            c.toggled.connect(self._on_widget)
            self.w[key] = c
            return c

        # source
        f = group("g_source")
        self.src_label = QLabel()
        self.src_label.setWordWrap(True)
        f.addRow(self.src_label)
        pg = QSpinBox()
        pg.setMinimum(1)
        pg.valueChanged.connect(self._on_page)
        row(f, "page", pg)
        row(f, "unit", combo(list(UNITS)[:3]))
        self.w["sheet_fit"] = check("sheet_fit")
        f.addRow(self.w["sheet_fit"])
        # poster
        f = group("g_poster")
        row(f, "preset", combo(list(PRESET_ORDER) + ["Custom"]))
        row(f, "poster_orient", combo(["auto", "portrait", "landscape"]), "orientation")
        row(f, "poster_w", spin(1, 100000), "width")
        row(f, "poster_h", spin(1, 100000), "height")
        self.w["lock_aspect"] = check("lock_aspect")
        f.addRow(self.w["lock_aspect"])
        row(f, "scale_mode", combo(["fit", "fill", "stretch"]))
        reset = QPushButton()
        reset.clicked.connect(self._reset_pos)
        self.w["reset_pos"] = reset
        f.addRow(reset)
        # paper
        f = group("g_paper")
        row(f, "paper", combo(list(PRESET_ORDER)))
        row(f, "paper_orient", combo(["auto", "portrait", "landscape"]), "orientation2")
        row(f, "margin", spin(0, 100))
        row(f, "header", spin(0, 100))
        row(f, "overlap", spin(0, 200))
        row(f, "numbering", combo(["seq", "rc"]))
        # options
        f = group("g_options")
        for k in ("crop_marks", "overlap_guides", "footer", "scale_bar", "smart_cut",
                  "skip_blank", "blank_backs"):
            f.addRow(check(k))
        ft = QLineEdit()
        ft.editingFinished.connect(self._on_widget)
        row(f, "footer_text", ft)
        self.info = QLabel()
        self.info.setWordWrap(True)
        self.dpi_label = QLabel()
        self.dpi_label.setWordWrap(True)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setStyleSheet("color: gray;")
        col.addWidget(self.info)
        col.addWidget(self.dpi_label)
        col.addWidget(self.hint)
        col.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(host)
        self.dock = QDockWidget()
        self.dock.setWidget(scroll)
        self.dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.dock.setMinimumWidth(340)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)

    def _retranslate(self):
        lang = self.settings.language
        i18n.set_language(lang)
        QApplication.instance().setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if lang == "ar" else Qt.LayoutDirection.LeftToRight)
        self.setWindowTitle(tr("app_title"))
        for k, a in self.act.items():
            a.setText(tr(k))
        for k, g in self.groups.items():
            g.setTitle(tr(k))
        for k, lab in self.lbl.items():
            lab.setText(tr({"orientation2": "orientation"}.get(k, k)))
        for k in ("lock_aspect", "crop_marks", "overlap_guides", "footer", "scale_bar",
                  "smart_cut", "skip_blank", "blank_backs", "sheet_fit"):
            self.w[k].setText(tr({"overlap_guides": "guides"}.get(k, k)))
        self.w["reset_pos"].setText(tr("reset_pos"))
        self.hint.setText(tr("hint"))
        for key in ("poster_orient", "paper_orient", "scale_mode", "numbering"):
            c = self.w[key]
            c.blockSignals(True)
            for i in range(c.count()):
                c.setItemText(i, tr(c.itemData(i)))
            c.blockSignals(False)
        c = self.w["preset"]
        c.blockSignals(True)
        c.setItemText(c.count() - 1, tr("custom"))
        c.blockSignals(False)
        self._update_src_label()

    # ------------------------------------------------------- settings <-> UI
    def _unit(self) -> str:
        return self.w["unit"].currentData() or "mm"

    def _fill_widgets(self):
        s = self.settings
        self._loading = True
        try:
            def setc(key, value):
                c = self.w[key]
                i = c.findData(value)
                c.setCurrentIndex(max(i, 0))
            setc("unit", s.unit)
            u = s.unit
            step = {"mm": 1.0, "cm": 0.1, "in": 0.05}[u]
            for key in ("poster_w", "poster_h", "margin", "header", "overlap"):
                sp = self.w[key]
                sp.setSuffix(f" {u}")
                sp.setSingleStep(step)
                sp.setDecimals(2 if u != "mm" else 1)
            setc("preset", s.poster_preset)
            setc("poster_orient", s.poster_orient)
            setc("scale_mode", s.scale_mode)
            setc("paper", s.paper)
            setc("paper_orient", s.paper_orient)
            setc("numbering", s.numbering)
            self.w["poster_w"].setValue(from_pt(s.poster_w, u))
            self.w["poster_h"].setValue(from_pt(s.poster_h, u))
            for key in ("margin", "header", "overlap"):
                self.w[key].setValue(from_pt(getattr(s, key), u))
            for key in ("lock_aspect", "crop_marks", "overlap_guides", "footer", "scale_bar",
                        "smart_cut", "skip_blank", "blank_backs"):
                self.w[key].setChecked(getattr(s, key))
            self.w["sheet_fit"].setChecked(s.sheet_fit_one_page)
            self.w["footer_text"].setText(s.footer_text)
            self.w["page"].setValue(s.page_index + 1)
            self._sync_enabled()
        finally:
            self._loading = False

    def _sync_enabled(self):
        custom = self.w["preset"].currentData() == "Custom"
        for k in ("poster_w", "poster_h", "lock_aspect"):
            self.w[k].setEnabled(custom)
        self.w["poster_orient"].setEnabled(not custom)
        self.w["page"].setEnabled(bool(self.src and self.src.page_count > 1))

    def _read_widgets(self):
        s, w = self.settings, self.w
        s.unit = w["unit"].currentData()
        u = s.unit
        s.poster_preset = w["preset"].currentData()
        s.poster_orient = w["poster_orient"].currentData()
        s.scale_mode = w["scale_mode"].currentData()
        s.paper = w["paper"].currentData()
        s.paper_orient = w["paper_orient"].currentData()
        s.numbering = w["numbering"].currentData()
        if s.poster_preset == "Custom":
            s.poster_w = to_pt(w["poster_w"].value(), u)
            s.poster_h = to_pt(w["poster_h"].value(), u)
        for k in ("margin", "header", "overlap"):
            setattr(s, k, to_pt(w[k].value(), u))
        for k in ("lock_aspect", "crop_marks", "overlap_guides", "footer", "scale_bar",
                  "smart_cut", "skip_blank", "blank_backs"):
            setattr(s, k, w[k].isChecked())
        s.sheet_fit_one_page = w["sheet_fit"].isChecked()
        s.footer_text = w["footer_text"].text().strip()

    def _on_widget(self, *_):
        if self._loading:
            return
        prev_preset, prev_unit = self.settings.poster_preset, self.settings.unit
        sender = self.sender()
        # entering Custom: start from the current poster size
        if sender is self.w["preset"] and self.w["preset"].currentData() == "Custom" \
                and prev_preset != "Custom" and self.job:
            self.settings.poster_w, self.settings.poster_h = self.job.poster_w, self.job.poster_h
        # keep proportions while editing custom width/height
        if self.src and self.w["lock_aspect"].isChecked() and \
                sender in (self.w["poster_w"], self.w["poster_h"]):
            sw, sh = self.src.size_pt
            self._loading = True
            if sender is self.w["poster_w"]:
                self.w["poster_h"].setValue(self.w["poster_w"].value() * sh / sw)
            else:
                self.w["poster_w"].setValue(self.w["poster_h"].value() * sw / sh)
            self._loading = False
        self._read_widgets()
        if self.settings.unit != prev_unit or (sender is self.w["preset"]):
            self._fill_widgets()
        self._sync_enabled()
        self.refresh()
        self._timer.start()

    def _on_page(self, v):
        if self._loading or not self.src:
            return
        self.src.page_index = min(v - 1, self.src.page_count - 1)
        self.settings.page_index = self.src.page_index
        self.settings.offset = [0.0, 0.0]
        self._pix_key = None
        self.refresh(fit=True)
        self._timer.start()

    def _reset_pos(self):
        self.settings.offset = [0.0, 0.0]
        self.refresh()
        self._timer.start()

    def toggle_language(self):
        self.settings.language = "en" if self.settings.language == "ar" else "ar"
        self._retranslate()
        self.refresh()

    # ----------------------------------------------------------------- history
    def _commit(self):
        snap = self.settings.to_dict()
        if snap != self._history[self._pos]:
            del self._history[self._pos + 1:]
            self._history.append(snap)
            self._pos += 1

    def _apply_snapshot(self):
        lang = self.settings.language
        self.settings = Settings.from_dict(self._history[self._pos])
        self.settings.language = lang
        if self.src:
            self.src.page_index = min(self.settings.page_index, self.src.page_count - 1)
        self._fill_widgets()
        self.refresh()

    def undo(self):
        self._timer.stop()
        self._commit()
        if self._pos > 0:
            self._pos -= 1
            self._apply_snapshot()

    def redo(self):
        if self._pos < len(self._history) - 1:
            self._pos += 1
            self._apply_snapshot()

    # --------------------------------------------------------------- open / save
    def open_dialog(self):
        exts = " ".join(f"*{e}" for e in sorted({".pdf"} | S.IMAGE_EXTS | S.SHEET_EXTS))
        path, _ = QFileDialog.getOpenFileName(self, tr("open_title"), "",
                                              f"{tr('filter_src')} ({exts})")
        if path:
            self.open_file(path)

    def open_file(self, path: str, page: int = 0) -> bool:
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.src = S.load_source(path, sheet_fit_one_page=self.settings.sheet_fit_one_page)
        except S.SourceError as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("error"), str(e))
            return False
        finally:
            QApplication.restoreOverrideCursor()
        self.src.page_index = min(page, self.src.page_count - 1)
        self.settings.page_index = self.src.page_index
        self.settings.offset = [0.0, 0.0]
        self._pix_key = None
        self._loading = True
        self.w["page"].setMaximum(self.src.page_count)
        self.w["page"].setValue(self.src.page_index + 1)
        self._loading = False
        self._sync_enabled()
        self._update_src_label()
        if "sheet_has_charts_not_fitted" in self.src.notes:
            self.statusBar().showMessage(tr("note_charts"), 8000)
        self.refresh(fit=True)
        self._commit()
        return True

    def _update_src_label(self):
        if not self.src:
            self.src_label.setText(tr("no_source"))
            return
        w, h = self.src.size_pt
        u = self._unit()
        self.src_label.setText(f"{os.path.basename(self.src.original_path)}\n"
                               f"{from_pt(w, u):.1f} × {from_pt(h, u):.1f} {u} · "
                               f"{self.src.page_count} pp")

    def save_project_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, tr("save_project"), "",
                                              f"TilePrint (*{PROJECT_EXT})")
        if path:
            if not path.endswith(PROJECT_EXT):
                path += PROJECT_EXT
            save_project(path, self.settings, self.src.original_path if self.src else None)

    def open_project_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("open_project"), "", f"TilePrint (*{PROJECT_EXT})")
        if not path:
            return
        try:
            s, src_path = load_project(path)
        except Exception as e:
            QMessageBox.critical(self, tr("error"), str(e))
            return
        lang = self.settings.language
        self.settings = s
        self.settings.language = lang
        self._fill_widgets()
        if src_path and os.path.exists(src_path):
            self.open_file(src_path, s.page_index)
            self.settings = s
            self.settings.language = lang
            self._fill_widgets()
        self.refresh(fit=True)
        self._commit()

    # --------------------------------------------------------------- preview
    def refresh(self, fit: bool = False):
        if not self.src:
            self.scene.clear()
            self.info.setText("")
            self.dpi_label.setText("")
            return
        try:
            self.job = build_job(self.src, self.settings, self._cache)
        except ValueError as e:
            self.statusBar().showMessage(str(e), 6000)
            return
        job = self.job
        key = (self.src.pdf_path, self.src.page_index)
        if key != self._pix_key:
            self._pix = pil_to_pixmap(S.render_page(self.src, 1600))
            self._pix_key = key
        self._rebuild_scene(job)
        poster = (round(job.poster_w), round(job.poster_h))
        if fit or poster != self._last_poster:
            self.view.setSceneRect(-job.poster_w * 0.05, -job.poster_h * 0.05,
                                   job.poster_w * 1.1, job.poster_h * 1.1)
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._last_poster = poster
        lay = job.layout
        u = self._unit()
        n = lay.rows * lay.cols
        text = tr("info_sheets", rows=lay.rows, cols=lay.cols, n=n, p=n - len(job.skip)) + "\n" + \
            tr("info_size", w=f"{from_pt(job.poster_w, u):.1f}", h=f"{from_pt(job.poster_h, u):.1f}",
               u=u, s=f"{job.scale:.2f}")
        self.info.setText(text)
        if job.dpi is not None:
            low = job.dpi < 150
            self.dpi_label.setText(tr("dpi_warn" if low else "dpi_ok", d=f"{job.dpi:.0f}"))
            self.dpi_label.setStyleSheet("color: #c62828; font-weight: bold;" if low else "")
        else:
            self.dpi_label.setText("")

    def _rebuild_scene(self, job: Job):
        sc = self.scene
        sc.clear()
        pl, lay = job.placement, job.layout
        poster = QGraphicsRectItem(0, 0, job.poster_w, job.poster_h)
        poster.setBrush(QBrush(Qt.GlobalColor.white))
        pen = QPen(QColor(40, 40, 40), 0)
        poster.setPen(pen)
        poster.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)
        sc.addItem(poster)
        item = ContentItem(self._pix, poster, self._content_moved)
        item.setTransform(QTransform.fromScale(pl.width / self._pix.width(),
                                               pl.height / self._pix.height()))
        item.setPos(pl.x, pl.y)

        # overlap strips
        shade = QBrush(QColor(255, 150, 0, 55))
        none = QPen(Qt.PenStyle.NoPen)
        for a, b in zip(lay.xs, lay.xs[1:]):
            r = sc.addRect(b, 0, a + lay.frame_w - b, job.poster_h, none, shade)
            r.setZValue(2)
        for a, b in zip(lay.ys, lay.ys[1:]):
            r = sc.addRect(0, b, job.poster_w, a + lay.frame_h - b, none, shade)
            r.setZValue(2)
        # tiles + numbers
        numbers = {p.tile.key: p.label for p in lay.plan(job.skip, self.settings.numbering)}
        tile_pen = QPen(BLUE, 0)
        for t in lay.tiles():
            skipped = t.key in job.skip
            r = sc.addRect(t.x, t.y, t.w, t.h, tile_pen,
                           QBrush(QColor(0, 0, 0, 110)) if skipped else QBrush(Qt.BrushStyle.NoBrush))
            r.setZValue(3)
            label = QGraphicsSimpleTextItem("–" if skipped else numbers[t.key])
            f = QFont("Noto Sans")
            f.setPixelSize(100)
            f.setBold(True)
            label.setFont(f)
            label.setBrush(QBrush(QColor(30, 100, 210, 170)))
            target = min(t.w, t.h) * 0.16
            label.setScale(target / 100)
            label.setPos(t.x + t.w * 0.04, t.y + t.h * 0.02)
            label.setZValue(4)
            sc.addItem(label)

    def _content_moved(self, pos: QPointF):
        if not self.job:
            return
        pl = self.job.placement
        o = self.settings.offset
        self.settings.offset = [o[0] + pos.x() - pl.x, o[1] + pos.y() - pl.y]
        self.refresh()
        self._timer.start()

    def _open_sheet_preview(self, pos: QPointF):
        if not (self.job and self.src):
            return
        job = self.job
        plan = job.layout.plan(job.skip, self.settings.numbering)
        hit = next((p for p in plan if p.tile.x <= pos.x() <= p.tile.x + p.tile.w
                    and p.tile.y <= pos.y() <= p.tile.y + p.tile.h), None)
        if not hit:
            return
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        try:
            X.export_tiled(self.src, tmp.name, job.layout, job.placement, job.overlay,
                           job.skip, only={hit.number})
            doc = pdfium.PdfDocument(tmp.name)
            pix = pil_to_pixmap(doc[0].render(scale=1.6).to_pil())
            doc.close()
        finally:
            os.unlink(tmp.name)
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("page_preview", n=hit.label))
        lay = QVBoxLayout(dlg)
        lab = QLabel()
        lab.setPixmap(pix)
        sa = QScrollArea()
        sa.setWidget(lab)
        lay.addWidget(sa)
        dlg.resize(min(pix.width() + 40, 900), min(pix.height() + 40, 900))
        dlg.exec()

    # ----------------------------------------------------------------- export
    def _run_export(self, default_name: str, fn):
        if not (self.src and self.job):
            return
        base = os.path.splitext(os.path.basename(self.src.original_path))[0]
        path, _ = QFileDialog.getSaveFileName(self, tr("export_tiled"), f"{base}{default_name}",
                                              tr("filter_pdf"))
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        dlg = QProgressDialog(tr("working"), tr("cancel"), 0, 0, self)
        dlg.setCancelButton(None)
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.show()
        self._worker = ExportWorker(fn(path), path)
        self._worker.progress.connect(lambda i, n: (dlg.setMaximum(n), dlg.setValue(i)))

        def ok(p):
            dlg.close()
            self.statusBar().showMessage(tr("export_done", p=p), 10000)

        def bad(msg):
            dlg.close()
            QMessageBox.critical(self, tr("error"), msg)

        self._worker.done.connect(ok)
        self._worker.failed.connect(bad)
        self._worker.start()

    def export_tiled(self):
        job, src = self.job, self.src
        s = self.settings
        if job:
            self._run_export("_tiles.pdf", lambda path: lambda prog: X.export_tiled(
                src, path, job.layout, job.placement, job.overlay, job.skip,
                blank_backs=s.blank_backs, progress=prog))

    def export_full(self):
        job, src = self.job, self.src
        if job:
            self._run_export("_full.pdf", lambda path: lambda prog: X.export_fullsize(
                src, path, job.poster_w, job.poster_h, job.placement))


def selftest() -> int:
    """Headless end-to-end check used by CI on the *frozen* app (and by developers).

    Exercises every bundled piece: reportlab + fonts + Arabic shaping, pypdfium2, Pillow,
    pikepdf (+ lxml), openpyxl import, and a real Qt window (so missing Qt platform
    libraries or pruned plugins are caught). Exit code 0 = OK. Log: $TILEPRINT_SELFTEST_LOG.
    """
    import traceback
    log_path = os.environ.get("TILEPRINT_SELFTEST_LOG")
    lines: list[str] = []

    def say(msg: str) -> None:
        lines.append(msg)
        try:
            print(msg, flush=True)
        except Exception:      # windowed exe has no stdout
            pass

    code = 0
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as rl

        from .overlay import OverlayOptions
        from .paper import PT_PER_MM
        from .project import RasterCache, build_job

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
        n = job.layout.rows * job.layout.cols
        say(f"2 layout built: {job.layout.rows}x{job.layout.cols}, skipped {len(job.skip)}")
        out_t, out_f = os.path.join(tmp, "tiles.pdf"), os.path.join(tmp, "full.pdf")
        pages = X.export_tiled(src, out_t, job.layout, job.placement, job.overlay, job.skip)
        X.export_fullsize(src, out_f, job.poster_w, job.poster_h, job.placement)
        say(f"3 PDFs written ({pages} sheets)")
        doc = pdfium.PdfDocument(out_t)
        assert len(doc) == pages > 0 and n >= pages
        doc[0].render(scale=0.5).to_pil().getbbox()
        doc.close()
        say("4 output re-opened and rendered")
        import openpyxl  # noqa: F401
        from openpyxl.worksheet.properties import PageSetupProperties  # noqa: F401
        say("5 spreadsheet support importable")
        app = QApplication.instance() or QApplication(sys.argv[:1])
        win = MainWindow("en")
        assert win.open_file(pdf)
        win.refresh()
        img = win.grab()
        assert not img.isNull() and img.width() > 100
        say(f"6 Qt window rendered ({QApplication.platformName()})")
        say("SELFTEST OK")
    except Exception:
        say("SELFTEST FAILED\n" + traceback.format_exc())
        code = 1
    if log_path:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    return code


def main(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    app = QApplication(argv)
    for fn in ("NotoSans-Regular.ttf", "NotoSans-Bold.ttf", "NotoSansArabic-Regular.ttf",
               "NotoSansArabic-Bold.ttf"):
        QFontDatabase.addApplicationFont(str(asset_path("fonts", fn)))
    app.setFont(QFont("Noto Sans", 10))
    lang = "ar" if QLocale.system().language() == QLocale.Language.Arabic else "en"
    win = MainWindow(lang)
    win.show()
    if len(argv) > 1 and os.path.exists(argv[1]):
        win.open_file(argv[1])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
