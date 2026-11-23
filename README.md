# TilePrint

Split a large PDF, image or spreadsheet into printable A4 (or any paper) tiles. Every sheet gets a thin frame and **arrows with the page numbers of the neighbouring sheets above the frame**, like the poster printing of family-tree programs. The output is a PDF that **keeps vector artwork vector**.

Windows · macOS · Linux · **Android** (native app in `android/`) — English and Arabic UI (full RTL), light and dark themes.

## What you get

| Area | |
|---|---|
| Inputs | PDF (any page), images (PNG/JPG/TIFF/…), spreadsheets (xlsx/xls/ods/csv via LibreOffice); drag and drop |
| Final size | ISO A0–A8, B0–B8, US/ARCH presets, or custom width × height in mm / cm / in with a keep-proportions lock |
| Placement | Fit / Fill / Stretch; drag the content on the canvas |
| Tiling | Printer margin, overlap, automatic portrait/landscape (fewest sheets), **smart cut** (moves sheet edges onto empty space), **skip blank sheets** |
| Sheet furniture | Thin frame, neighbour arrows ◄ ► ▲ ▼ with page numbers (omitted where there is no neighbour), 1·2·3 or A1·B2 numbering, crop marks, overlap ticks in the margin (nothing inside the frame), footer (name · page · date · scale), real-size ruler (5 cm / 2 in) |
| Preview | Poster with the tile grid and numbers, overlap strips, skipped sheets hatched; wheel zoom with **crisp vector re-rendering**, pan, scale bar; double-click a sheet for the exact printed page |
| Output | Tiled PDF and a single full-size PDF (plotters / print shops); "duplex printer" option adds blank backs |
| Quality | Image DPI shown with a warning below 150 DPI at the chosen size |
| Project | Save / open `.tileprint` projects, undo / redo (Ctrl+Z / Ctrl+Y) |

Shortcuts: Ctrl+O open · Ctrl+S save project · Ctrl+E export · Space+drag pan · `+` `-` `0` zoom / fit.

## How it works

* **UI**: plain HTML/CSS/JS in `src/tileprint/assets` shown by the system web view through [pywebview](https://pywebview.flowrl.com) (WebView2 on Windows, WKWebView on macOS). No bundled browser engine, so the download stays small.
* **Back-end**: `api.py` is one Python object exposed to JavaScript; the same object is served over a token-protected local HTTP API in *browser mode* (`tileprint --browser`). Linux builds use browser mode automatically unless GTK/Qt bindings are installed.
* **Vector output**: the chosen source page is wrapped **once** as a Form XObject (pikepdf). Every sheet only references it with its own transform and clip, so nothing is rasterised, text stays selectable, and the file is about the size of the source. Geometry is in PDF points, so sheets register to a fraction of a millimetre when printed at **100 % / "Actual size"**.

## Run from source

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m tileprint [file]            # desktop window
python -m tileprint --browser         # or: use your browser
pytest
python -m tileprint --selftest        # engine check; add --ui to include the web view
```

Spreadsheets need [LibreOffice](https://www.libreoffice.org/download) installed (auto-detected). Workbooks with charts or images are converted untouched so nothing is lost.
On Linux, for a native window install GTK bindings (`python3-gi`, `gir1.2-webkit2-4.1`) — otherwise it opens in your browser.

## Releases — the `incoming/` drop folder

Update the whole project from GitHub without touching git locally:

1. Put a project `.zip` (for example `tileprint-0.3.0.zip`) into `incoming/` and push to `main`.
2. **Incoming → Build → Release** (`.github/workflows/incoming.yml`) replaces the whole project with the zip contents (`incoming/` and `.github/workflows/` are kept).
3. It runs the tests and builds on Windows, macOS and Linux with PyInstaller, then runs `TilePrint --selftest` on each **built** app.
4. Only if everything succeeded it commits the new state, deletes the zip, and publishes a GitHub Release `vX.Y.Z` with `TilePrint-vX.Y.Z-windows-portable.zip` (and a smaller `.7z`), `…-macos.dmg`, `…-linux-x86_64.AppImage`, the source zip and `SHA256SUMS.txt`.

The version comes from the `VERSION` file in the zip (fallback: the number in its name); if the tag exists the last number is bumped, and the version is written to `pyproject.toml` and `src/tileprint/__init__.py`. If a build fails nothing is committed and the zip stays in `incoming/`. `build.yml` runs tests/builds on normal pushes and PRs.

* **macOS:** not code-signed (needs a paid Apple Developer account): first launch via right-click → Open.
* **Windows:** SmartScreen may warn for an unsigned executable. Needs the WebView2 runtime (included in Windows 11 and current Windows 10).

## Android

`android/` holds a native Kotlin / Jetpack Compose app that does the same job on phones and tablets (PDF and images; no spreadsheets). Its layout engine is checked against the Python one by a parity test. See [android/README.md](android/README.md). Releases attach `TilePrint-vX.Y.Z-android.apk`.

## Layout

```
src/tileprint/
  paper.py       paper sizes and units
  layout.py      tiling maths: placement, axis splitting, smart cut, numbering, neighbours
  source.py      PDF / image / xlsx -> PDF, preview raster, ink profiles, blank-tile detection
  overlay.py     per-sheet vector furniture (reportlab)
  exporter.py    tiled and full-size PDF writers (pikepdf)
  project.py     settings, save/load, job building
  api.py         back-end object exposed to the UI
  webapp.py      entry point (pywebview window or browser mode)
  devserver.py   browser-mode HTTP server (token protected)
  selftest.py    headless check used by CI on the built app
  textutil.py    bundled fonts + Arabic shaping
  assets/        index.html, ui/app.css, ui/app.js, fonts, icons
```

## Licenses

TilePrint: MIT. Fonts Noto Sans and Noto Sans Arabic: SIL OFL 1.1 (`assets/fonts/OFL.txt`; embedding in PDFs is allowed). Dependencies: pywebview (BSD-3), pikepdf (MPL-2.0), pypdfium2 (Apache-2.0/BSD-3), reportlab (BSD), Pillow (HPND), openpyxl (MIT), arabic-reshaper (MIT), python-bidi (LGPL).

## Known limits

* A single PDF page cannot exceed 200 in (5.08 m); for larger posters use the tiled export.
* A huge vector source is re-drawn clipped on every sheet; viewers cope, but hundreds of sheets can be slow to open.
* Smart cut and blank-sheet detection analyse a ≈2000 px raster of the poster, so hairline-thin content can occasionally be missed.
* Encrypted PDFs must be unlocked first.
