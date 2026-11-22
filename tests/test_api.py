"""Back-end used by the web UI: state, undo, previews, export, and the browser-mode HTTP server."""
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from tileprint.api import Api
from tileprint.devserver import make_server

MM = 72 / 25.4


@pytest.fixture()
def api(vector_pdf):
    a = Api("en")
    r = a.open_path(vector_pdf)
    assert r["ok"] and r["state"]["has_source"]
    return a


def test_open_and_state_shape(api):
    st = api.update({"poster_preset": "A2"})
    j = st["job"]
    assert round(j["poster"][0] / MM) in (420, 594) and j["total"] == j["rows"] * j["cols"] == len(j["tiles"])
    assert j["uniform_scale"] and j["scale"] > 1.9
    t = j["tiles"][0]
    assert {"row", "col", "x", "y", "w", "h", "label", "number", "nb", "skipped"} <= set(t)
    assert st["source"]["page_count"] == 1 and st["source"]["kind"] == "pdf"


def test_open_error_is_reported_not_raised(tmp_path):
    a = Api("en")
    bad = tmp_path / "x.txt"
    bad.write_text("hello")
    r = a.open_path(str(bad))
    assert r["ok"] is False and "Unsupported" in r["error"]
    assert a.open_path(str(tmp_path / "missing.pdf"))["ok"] is False


def test_update_validates_input(api):
    st = api.update({"unit": "parsec", "margin": -50, "overlap": 1e9, "bogus": 1, "numbering": "rc",
                     "scale_mode": "stretch", "paper": "NOPE"})
    s = st["settings"]
    assert s["unit"] == "mm" and s["margin"] == 0 and s["overlap"] <= 400 and s["numbering"] == "rc"
    assert s["scale_mode"] == "stretch" and s["paper"] != "NOPE" and "bogus" not in s


def test_custom_size_with_aspect_lock(api):
    st = api.update({"poster_preset": "Custom"})
    assert st["settings"]["poster_preset"] == "Custom"
    st = api.update({"poster_w": 1000 * MM})
    w, h = st["settings"]["poster_w"], st["settings"]["poster_h"]
    assert abs(h / w - 297 / 210) < 1e-6                       # locked to the source proportions
    st = api.update({"lock_aspect": False})
    st = api.update({"poster_w": 500 * MM})
    assert abs(st["settings"]["poster_h"] / st["settings"]["poster_w"] - 297 / 210) > 0.1


def test_layout_error_surfaces_as_message(api):
    st = api.update({"margin": 200.0, "paper": "A6"})          # 200 pt margins on A6: no printable area
    assert st["job"] is None and st["error"]


def test_undo_redo_and_move(api):
    base = api.get_state()["settings"]["numbering"]
    api.update({"numbering": "rc"})
    st = api.move_content(10, 5)
    assert st["settings"]["offset"] == [10.0, 5.0] and st["can_undo"]
    st = api.undo()
    assert st["settings"]["offset"] == [0.0, 0.0] and st["settings"]["numbering"] == "rc"
    st = api.undo()
    assert st["settings"]["numbering"] == base and not st["can_undo"]
    st = api.redo()
    assert st["settings"]["numbering"] == "rc" and st["can_redo"]
    assert api.reset_position()["settings"]["offset"] == [0.0, 0.0]


def test_previews_are_images(api):
    api.update({"poster_preset": "A2"})
    p = api.preview_image(800)
    assert p["ok"] and p["url"].startswith("data:image/jpeg;base64,") and p["w"] <= 800
    r = api.render_region(0, 0, 400, 400, 500)
    assert r["ok"] and r["url"].startswith("data:image/jpeg") and r["w"] > 0
    assert api.render_region(-5000, -5000, 10, 10, 100)["ok"] is False   # outside the content
    s = api.sheet_preview(1)
    assert s["ok"] and s["url"].startswith("data:image/png;base64,")


def test_export_runs_in_background_and_reports(api, tmp_path):
    api.update({"poster_preset": "A2"})
    assert api.export("tiled")["started"]
    for _ in range(100):
        st = api.export_status()
        if st["state"] != "running":
            break
        time.sleep(0.1)
    assert st["state"] == "done" and st["size"] > 1000
    import pikepdf
    with pikepdf.open(st["path"]) as pdf:
        assert len(pdf.pages) == api.get_state()["job"]["printed"]
    assert api.export("full")["started"]
    for _ in range(100):
        if api.export_status()["state"] != "running":
            break
        time.sleep(0.1)
    assert api.export_status()["state"] == "done"


def test_project_roundtrip_through_api(api, tmp_path):
    api.update({"poster_preset": "A1", "numbering": "rc"})
    text = api.project_text()["text"]
    p = tmp_path / "p.tileprint"
    p.write_text(text, encoding="utf-8")
    b = Api("en")
    r = b.open_project_path(str(p))
    assert r["ok"] and r["state"]["settings"]["poster_preset"] == "A1" and r["state"]["has_source"]


def test_underscore_members_are_private():
    public = [n for n in dir(Api) if not n.startswith("_")]
    # pywebview exposes every public attribute: keep them all callable methods
    assert all(callable(getattr(Api, n)) for n in public)


# ------------------------------------------------------------------ browser-mode server
@pytest.fixture()
def server(api):
    srv, url = make_server(api)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    page = urllib.request.urlopen(url).read().decode()
    token = page.split('name="tp-token" content="')[1].split('"')[0]
    yield url, token
    srv.shutdown()


def _post(url, token, path, body):
    req = urllib.request.Request(url.rstrip("/") + path, data=json.dumps(body).encode(), method="POST",
                                 headers={"X-TP-Token": token or "", "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())


def test_server_serves_ui_and_token_gates_api(server):
    url, token = server
    assert urllib.request.urlopen(url + "ui/app.js").status == 200
    assert urllib.request.urlopen(url + "fonts/NotoSans-Regular.ttf").status == 200
    assert _post(url, token, "/api/get_state", [])["has_source"]
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(url, "wrong", "/api/get_state", [])
    assert e.value.code == 403
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(url, token, "/api/_bind", [])                     # private / unknown methods are not callable
    assert e.value.code == 404


def test_server_blocks_path_traversal_and_upload(server, tmp_path):
    url, token = server
    for bad in ("/../api.py", "/%2e%2e/api.py", "/ui/../../api.py"):
        try:
            code = urllib.request.urlopen(url.rstrip("/") + bad).status
        except urllib.error.HTTPError as e:
            code = e.code
        assert code in (403, 404)
    req = urllib.request.Request(url + "upload?name=../../evil.pdf", data=b"%PDF-1.4", method="POST",
                                 headers={"X-TP-Token": token})
    path = json.loads(urllib.request.urlopen(req).read())["path"]
    assert "evil.pdf" in path and ".." not in path.replace("tileprint_", "")
