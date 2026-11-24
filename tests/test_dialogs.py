"""Desktop dialogs and drag-and-drop, with a fake window that validates file filters exactly like pywebview."""
import json

import pytest

webview = pytest.importorskip("webview")
from webview.util import parse_file_type  # noqa: E402

from tileprint.api import Api  # noqa: E402
from tileprint.webapp import drop_handler  # noqa: E402


class FakeWindow:
    """What Api needs from a pywebview Window. create_file_dialog rejects invalid filters like the real one."""

    def __init__(self, picks=None):
        self.picks = picks
        self.dialog_calls = []
        self.js = []

    def create_file_dialog(self, dialog_type, directory="", allow_multiple=False, save_filename="", file_types=()):
        for f in file_types:
            parse_file_type(f)                      # raises ValueError('... is not a valid file filter')
        self.dialog_calls.append((dialog_type, tuple(file_types)))
        return self.picks

    def evaluate_js(self, code):
        self.js.append(code)


def test_every_dialog_filter_is_valid_for_pywebview():
    for filt in (*Api._open_types(), *Api._project_types(), "PDF (*.pdf)"):
        parse_file_type(filt)                       # would have raised for the old space-separated filter
    desc, exts = parse_file_type(Api._open_types()[0])
    for ext in (".pdf", ".png", ".jpg", ".xlsx", ".csv"):
        assert f"*{ext}" in exts.split(";")


def test_open_button_opens_the_picked_file(vector_pdf):
    api = Api("en")
    win = FakeWindow(picks=(vector_pdf,))
    api._bind(win)
    r = api.open_dialog()
    assert r["ok"] and r["state"]["has_source"] and win.dialog_calls


def test_open_button_cancel_is_not_an_error():
    api = Api("en")
    api._bind(FakeWindow(picks=None))
    r = api.open_dialog()
    assert r["ok"] and r.get("cancelled")


def test_save_dialogs_use_valid_filters(vector_pdf):
    api = Api("en")
    win = FakeWindow(picks=None)
    api._bind(win)
    api.open_path(vector_pdf)
    assert api.save_project_dialog().get("cancelled")
    assert api.open_project_dialog().get("cancelled")
    assert api.export("tiled").get("cancelled")


def test_dropped_file_is_opened_and_ui_is_told(vector_pdf):
    api = Api("en")
    win = FakeWindow()
    api._bind(win)
    drop_handler(api)({"dataTransfer": {"files": [{"name": "vec.pdf", "pywebviewFullPath": vector_pdf}]}})
    assert api.get_state()["has_source"]
    assert len(win.js) == 1 and win.js[0].startswith("window.TP && window.TP.afterExternalOpen(")
    payload = json.loads(win.js[0][len("window.TP && window.TP.afterExternalOpen("):-1])
    assert payload["ok"] and payload["state"]["source"]["name"] == "vec.pdf"


def test_dropped_unsupported_file_reports_error(tmp_path):
    bad = tmp_path / "notes.txt"
    bad.write_text("hi")
    api = Api("en")
    win = FakeWindow()
    api._bind(win)
    drop_handler(api)({"dataTransfer": {"files": [{"name": "notes.txt", "pywebviewFullPath": str(bad)}]}})
    payload = json.loads(win.js[0][len("window.TP && window.TP.afterExternalOpen("):-1])
    assert payload["ok"] is False and "Unsupported" in payload["error"]


def test_drop_without_a_path_is_ignored():
    api = Api("en")
    win = FakeWindow()
    api._bind(win)
    drop_handler(api)({"dataTransfer": {"files": [{"name": "x.pdf"}]}})
    drop_handler(api)({})
    assert win.js == []
