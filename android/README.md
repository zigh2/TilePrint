# TilePrint for Android

Native app (Kotlin + Jetpack Compose) with the same idea as the desktop app: split a large PDF or image into printable A4 (or any paper) sheets with a thin frame and neighbour arrows + page numbers above it. Output PDFs **keep vector artwork vector**.

Android 8.0+ · English and Arabic (full RTL) · light/dark.

## What it does

Open a PDF or image (file picker, "Open with", or "Share to"), choose the final size (A0–A8, B0–B8, US/ARCH or custom in mm/cm/in), paper, margin / arrow band / overlap (0 by default: cut on the frame and glue edge to edge, nothing repeated), numbering (1·2·3 or A1·B2), and options (smart cut, skip blank sheets, crop marks, overlap ticks, footer, real-size ruler, duplex blank backs). Pinch to zoom (vector content is re-rendered crisply), drag to pan, "move content" mode to reposition, double-tap a sheet to see the exact printed page, undo/redo. Export a tiled PDF or a single full-size PDF to any location, then share it.

Not in the Android version (yet): spreadsheets (xlsx; no LibreOffice on Android — export the sheet to PDF first), `.tileprint` project files.

## How it is built

```
android/
  core/   pure Kotlin/JVM: paper sizes, tiling layout, smart cut, numbering, source transform (incl. /Rotate)
          + ParityTest: checks the results against the desktop (Python) engine
  app/    Android: Compose UI, PdfRenderer (preview), PDFBox-Android (vector-preserving export)
```

* **Vector output:** the source page is imported once as a Form XObject (PDFBox `LayerUtility`) and every sheet references it with its own transform and clip, like the desktop exporter. Pages with `/Rotate 90/270` are un-rotated before import and rotated by `core/Geometry.kt` (PDFBox's own handling distorts them); the test suite compares this against qpdf.
* **Preview:** the platform `PdfRenderer` draws the page; when you zoom past the base image's resolution the visible part is re-rendered at screen resolution.
* **Arabic in the PDF footer:** shaped and reordered by `core/ArabicText.kt` (a port of python-arabic-reshaper plus a compact Unicode bidi; Android's ICU has no `ArabicShaping`), then drawn with Noto Sans Arabic / Noto Sans (SIL OFL, bundled) embedded as subsets. `ArabicTest` compares it with the desktop result on 43 samples.
* **Memory:** big sources are processed with PDFBox temp files; poster rasters for smart cut / blank detection are at most ≈2000 px.

## Build

```bash
cd android
gradle :core:test             # engine parity tests (JVM, no Android needed)
gradle :app:assembleRelease   # app/build/outputs/apk/release/app-release.apk
```
Or open `android/` in Android Studio (Ladybug+). Needs JDK 17 and the Android SDK 35.

CI: `.github/workflows/android.yml` (pushes touching `android/`) and a non-blocking job in `incoming.yml` that attaches `TilePrint-vX.Y.Z-android.apk` to the release.

### Signing

Without secrets the APK is signed with the debug key: it installs, but updates only work if every build uses the same key. For a stable key add repository secrets `ANDROID_KEYSTORE_BASE64` (base64 of your `.jks`), `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`. Create a key once with `keytool -genkeypair -v -keystore release.jks -keyalg RSA -keysize 2048 -validity 10000 -alias tileprint`.

### Regenerating the parity data

`python android/gen_parity.py` rewrites `core/src/test/resources/parity.txt` from the Python engine; run it whenever the desktop layout maths changes.

## Status

The `core` module is verified on the JVM (parity with the desktop engine and Arabic shaping, 14 tests; they also pass on CI). The `app` module compiles on CI up to the last fixed error (Arabic shaping); anything after that still shows up only in CI, since the author's environment has no Android SDK.
