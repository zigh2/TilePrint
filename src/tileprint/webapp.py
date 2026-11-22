"""Entry point: desktop window (pywebview) or browser mode."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .api import Api
from .textutil import asset_path

HELP = """TilePrint - split posters into printable tiles

  tileprint [FILE]          open the desktop app (optionally with a PDF/image/spreadsheet)
  tileprint --browser       use your web browser instead of a window (always works, e.g. on Linux)
  tileprint --selftest      run the built-in check (add --ui to include the web view)
"""


def _storage_dir() -> str:
    d = Path.home() / ".tileprint" / "webview"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def _has_engine() -> bool:
    """Is there a native web view on this machine? (Linux needs GTK or Qt bindings.)"""
    if sys.platform.startswith("linux"):
        import importlib.util
        return any(importlib.util.find_spec(m) for m in ("gi", "qtpy"))
    return True


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(HELP)
        return 0
    if "--selftest" in argv:
        from .selftest import selftest
        return selftest(ui="--ui" in argv)

    api = Api()
    files = [a for a in argv if not a.startswith("-") and os.path.exists(a)]
    if files:
        api._startup = os.path.abspath(files[0])

    if "--browser" not in argv and _has_engine():
        try:
            import webview
        except ImportError:
            print("pywebview is not installed - using the browser instead.", file=sys.stderr)
        else:
            window = webview.create_window(
                "TilePrint", url=str(asset_path() / "index.html"), js_api=api,
                width=1440, height=920, min_size=(1040, 680), background_color="#0e1116",
                text_select=False)
            api._bind(window, "desktop")
            try:
                webview.start(http_server=True, private_mode=False, storage_path=_storage_dir())
                return 0
            except Exception as e:     # no GTK/Qt web engine on this machine (typically Linux)
                print(f"No web view engine available ({e}); opening your browser instead.", file=sys.stderr)
    from .devserver import serve_forever
    serve_forever(api)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
