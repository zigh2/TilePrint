"""Browser mode: serves the same UI + API on 127.0.0.1 (used on Linux and for development/tests).

Security: the API is only reachable with a random per-run token that is embedded in the page we
serve, so other web pages in the user's browser cannot talk to it.
"""
from __future__ import annotations

import json
import mimetypes
import os
import secrets
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .api import Api
from .textutil import asset_path

PUBLIC_METHODS = {
    "init", "get_state", "open_path", "set_page", "update", "move_content", "reset_position", "undo",
    "redo", "preview_image", "render_region", "sheet_preview", "export", "export_status",
    "open_project_path", "project_text", "startup_file",
}
mimetypes.add_type("font/ttf", ".ttf")
mimetypes.add_type("text/javascript", ".js")


def make_server(api: Api, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    root = asset_path().resolve()
    token = secrets.token_urlsafe(24)
    upload_dir = Path(api._tmp) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):          # keep the console quiet
            pass

        def _send(self, code: int, body: bytes, ctype: str = "application/json", extra=None):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _authorised(self) -> bool:
            return secrets.compare_digest(self.headers.get("X-TP-Token", ""), token)

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(url.query)
            if url.path == "/download":
                if not secrets.compare_digest(q.get("t", [""])[0], token):
                    return self._send(403, b"{}")
                path = api._downloads.get(q.get("id", [""])[0])
                if not path or not os.path.exists(path):
                    return self._send(404, b"{}")
                data = Path(path).read_bytes()
                name = urllib.parse.quote(os.path.basename(path))
                return self._send(200, data, "application/pdf",
                                  {"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})
            rel = "index.html" if url.path in ("/", "") else url.path.lstrip("/")
            target = (root / rel).resolve()
            if root not in target.parents and target != root / "index.html":
                return self._send(403, b"forbidden", "text/plain")
            if not target.is_file():
                return self._send(404, b"not found", "text/plain")
            data = target.read_bytes()
            if rel == "index.html":
                data = data.replace(b"<!--TP_TOKEN-->", f'<meta name="tp-token" content="{token}">'.encode())
            ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
            self._send(200, data, ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))

        def do_POST(self):
            if not self._authorised():
                return self._send(403, b'{"ok":false,"error":"forbidden"}')
            url = urllib.parse.urlparse(self.path)
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            if url.path == "/upload":
                name = os.path.basename(urllib.parse.parse_qs(url.query).get("name", ["upload"])[0]) or "upload"
                dest = upload_dir / f"{secrets.token_hex(4)}_{name}"
                dest.write_bytes(body)
                return self._send(200, json.dumps({"ok": True, "path": str(dest)}).encode())
            if url.path.startswith("/api/"):
                method = url.path[5:]
                if method not in PUBLIC_METHODS:
                    return self._send(404, b'{"ok":false,"error":"unknown method"}')
                try:
                    args = json.loads(body.decode("utf-8") or "[]")
                    result = getattr(api, method)(*args)
                except Exception as e:
                    result = {"ok": False, "error": f"{type(e).__name__}: {e}"}
                return self._send(200, json.dumps(result, ensure_ascii=False).encode("utf-8"))
            self._send(404, b"{}")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


def serve_forever(api: Api, port: int = 0, open_browser: bool = True) -> None:
    server, url = make_server(api, port)
    api._bind(None, "browser")
    print(f"TilePrint is running at {url}\nPress Ctrl+C to quit.", flush=True)
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
