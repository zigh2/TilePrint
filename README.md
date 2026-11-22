# TilePrint

Split a large PDF, image or spreadsheet into printable A4 (or any paper) tiles, with a thin frame on every sheet and **arrows + page numbers of the neighbouring sheets above the frame** — like the "poster printing" of family-tree programs. The output is a PDF that **keeps vector artwork vector**.

Windows · macOS · Linux — Arabic and English UI (RTL supported).

## Features

| Area | What it does |
|---|---|
| Inputs | PDF (any page), images (PNG/JPG/TIFF/…), spreadsheets (xlsx/xls/ods/csv via LibreOffice) |
| Final size | ISO A0–A8, B0–B8, US/ARCH presets, or custom width × height in mm / cm / in; keep-proportions lock |
| Placement | Fit / Fill / Stretch; drag the content in the preview |
| Tiling | Printer margin, overlap, automatic portrait/landscape (fewest sheets), **smart cut** (moves sheet edges onto empty space), **skip blank sheets** |
| Sheet furniture | Thin frame, neighbour arrows ◄ ► ▲ ▼ with page numbers (omitted where no neighbour), sequential (1, 2, 3) or row/column (A1, B2) numbering, crop marks, dashed overlap guides + registration crosses, footer (name · page · date · scale), real-size scale ruler (5 cm / 2 in) |
| Output | Tiled PDF, and a single full-size PDF (for plotters / print shops) |
| Printing aids | "Duplex printer" option inserts a blank back after every sheet so tiles never share a sheet |
| Preview | Poster with tile grid and numbers, overlap strips, skipped sheets dimmed; double-click a sheet for an exact preview of the printed page |
| Quality | Image DPI shown, with a warning below 150 DPI at the chosen size |
| Project | Save / open `.tileprint` projects, undo / redo |

## Why the PDF stays vector

The chosen source page is wrapped **once** as a Form XObject (pikepdf). Every tile sheet only references it with its own transform and clip rectangle — nothing is rasterised and the artwork is stored once, so the tiled file is about the size of the source. Text stays selectable. Raster images are embedded at their original resolution. (Tests assert that no image XObjects are created for a vector source and that the tiles reassemble into the full-size render.)

All geometry is computed in PDF points (1/72 in) from the paper size, so sheets register to a fraction of a millimetre when printed at **100 % / "Actual size"** — never "Fit to page".

## Run from source

```bash
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m tileprint [file]
pytest                                            # QT_QPA_PLATFORM=offscreen on a headless box
```

Spreadsheets need [LibreOffice](https://www.libreoffice.org/download) installed (auto-detected; it can't reasonably be bundled).
Workbooks that contain charts or images are converted untouched (not auto-fitted to one page) so nothing is lost.

## Releases — the `incoming/` drop folder

Update the whole project from GitHub without touching git locally:

1. Put a project `.zip` (for example `tileprint-0.2.0.zip`) into `incoming/` and push to `main`.
2. The **Incoming → Build → Release** workflow (`.github/workflows/incoming.yml`) takes the newest zip and
   replaces the whole project with its contents (`incoming/` and `.github/workflows/` are kept).
3. It runs the tests and builds on Windows, macOS and Linux with PyInstaller.
4. Only if everything succeeds it commits the new project state, deletes the zip, and publishes a
   GitHub Release `vX.Y.Z` with `TilePrint-vX.Y.Z-windows-portable.zip`, `TilePrint-vX.Y.Z-macos.dmg`,
   `TilePrint-vX.Y.Z-linux-x86_64.AppImage`, the source zip and `SHA256SUMS.txt`.

The version comes from the `VERSION` file in the zip (fallback: the number in the zip name). If that tag already
exists the last number is bumped (`0.1.9` → `0.1.10`), and the version is written back into `pyproject.toml`
and `src/tileprint/__init__.py`. If a build fails nothing is committed and the zip stays in `incoming/`.
Release notes are taken from the matching `## [X.Y.Z]` section of `CHANGELOG.md` when that file exists.

`.github/workflows/build.yml` still runs the tests/builds on every normal push and pull request (it ignores
pushes that only touch `incoming/`), and publishes a release when you push a `v*` tag by hand.

* **macOS:** the app is not code-signed (needs a paid Apple Developer account). On first launch use right-click → Open.
* **Windows:** SmartScreen may warn for an unsigned executable.

## Layout

```
src/tileprint/
  paper.py      paper sizes and units
  layout.py     pure tiling maths: placement, axis splitting, smart cut, numbering, neighbours
  source.py     PDF / image / xlsx -> PDF, preview raster, ink profiles, blank-tile detection
  overlay.py    per-sheet vector furniture (reportlab)
  exporter.py   tiled and full-size PDF writers (pikepdf)
  project.py    settings, save/load, job building
  app.py        PySide6 GUI
  textutil.py   bundled fonts + Arabic shaping
  i18n.py       English / Arabic strings
```

## Licenses

TilePrint: MIT. Bundled fonts Noto Sans and Noto Sans Arabic: SIL Open Font License 1.1 (`assets/fonts/OFL.txt`; embedding in PDFs is allowed). Dependencies: PySide6 (LGPL), pikepdf (MPL-2.0), pypdfium2 (Apache-2.0/BSD-3), reportlab (BSD), Pillow (HPND), openpyxl (MIT), arabic-reshaper (MIT), python-bidi (LGPL).

## Known limits

* A single PDF page cannot exceed 200 in (5.08 m); for larger posters use the tiled export.
* Very complex vector sources are re-drawn clipped on every sheet; viewers handle this, but a huge map split into hundreds of sheets can be slow to open.
* Smart cut and blank-sheet detection analyse a ≈2000 px raster of the poster, so hairline-thin content can occasionally be missed.
* Encrypted PDFs must be unlocked first.
