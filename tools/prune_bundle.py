#!/usr/bin/env python3
"""Shrink a PyInstaller bundle by deleting Qt parts TilePrint never uses.

TilePrint only needs QtCore / QtGui / QtWidgets. PyInstaller's PySide6 hook still
copies QML, Quick, OpenGL, Pdf, Network, translations, software OpenGL ... (> 100 MB).
Run AFTER pyinstaller, then run `TilePrint --selftest` to prove the app still works.

    python tools/prune_bundle.py dist/TilePrint --platform windows [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path

# --- applies everywhere (data and plugins that need no other library) --------------------
COMMON_DIRS = [
    r"pyside6/(qt/)?(translations|qml|metatypes|resources)",
    r"pyside6/(qt/)?plugins/(sqldrivers|qmltooling|tls|networkinformation|designer|"
    r"vectorimageformats|iconengines)",
    r"pyside6/(qt/)?libexec",
    r"pyside6/(qt/)?bin",
    r"pyside6/translations",
    r"pyside6/typesystems|pyside6/include|pyside6/glue|pyside6/scripts",
]
# image plugins: Qt is only handed raw pixel data, PIL decodes real files
COMMON_FILES = [
    r"pyside6/(qt/)?plugins/imageformats/[^/]*(qpdf|qsvg|qtiff|qwebp|qtga|qicns|qwbmp)[^/]*",
    r".*\.pyi$",
    r".*/qmlls(\.exe)?$|.*/qml(format|lint|tooling)[^/]*$|.*/assistant(\.exe)?$|.*/designer(\.exe)?$",
    r"pyside6/[^/]*\.exe",
    r"pyside6/pyside6qml\.[^/]*",          # QML glue, needs Qt6Qml
    r"pyside6/(qt/)?plugins/platforms/(lib)?(qdirect2d|qwebgl|qvnc|qlinuxfb|qeglfs|qminimalegl|qvkkhrdisplay|qwayland-brcm)[^/]*",
]
# --- python side leftovers (normally already removed with --exclude-module) ----------------
PY_DIRS = [r"numpy", r"numpy\.libs", r"tkinter", r"tcl", r"tk", r"tcl8", r"_tcl_data", r"_tk_data"]
PY_FILES = [r"_tkinter.*", r"libtk.*", r"libtcl.*", r"tcl\d.*\.dll", r"tk\d.*\.dll"]

# --- Windows: keep only the Qt DLLs/modules we use (whitelist) ------------------------------
WIN_KEEP_QT = {"core", "gui", "widgets"}
WIN_DELETE_FILES = [r".*/opengl32sw\.dll", r".*/d3dcompiler_47\.dll", r".*/dxcompiler\.dll", r".*/dxil\.dll"]

# --- Linux: blacklist (system-style libs are interdependent; Qt6OpenGL stays for Wayland/EGL) --
LINUX_QT_LIBS = (r"(lib)?qt6(quick|qml|pdf|designer|network|svg|virtualkeyboard|sql|test|"
                 r"labs|shadertools|3d|concurrent|xml)[^/]*")
LINUX_DIRS = [r"pyside6/(qt/)?plugins/(platformthemes|egldeviceintegrations|generic)"]
LINUX_FILES = [r"lib(gtk|gdk)-3[^/]*", r"libgdk_pixbuf[^/]*", r"libqgtk3[^/]*",
               r"libqt6eglfs[^/]*", r"libqt6opengl[^/]*\.pyi", r"libadwaita[^/]*", r"libqtvirtualkeyboardplugin[^/]*"]

# --- both Linux and Windows: PySide6 python modules we do not import --------------------
KEEP_PYSIDE_MODULES = {"qtcore", "qtgui", "qtwidgets", "qtdbus"}   # qtdbus: Linux platform plugins


def _matches(rel: str, patterns) -> bool:
    return any(re.fullmatch(p, rel) for p in patterns)


def _size(p: Path) -> int:
    if p.is_file() or p.is_symlink():
        try:
            return p.lstat().st_size
        except OSError:
            return 0
    return sum(f.lstat().st_size for f in p.rglob("*") if f.is_file() or f.is_symlink())


def _wanted(rel: str, name: str, is_dir: bool, platform: str) -> bool:
    low = rel.lower()
    base = name.lower()
    if is_dir:
        if any(re.search(rf"(^|/)({d})$", low) for d in COMMON_DIRS):
            return True
        if _matches(base, PY_DIRS) and "/" not in low.replace("_internal/", ""):
            return True
        if platform == "linux" and any(re.search(rf"(^|/)({d})$", low) for d in LINUX_DIRS):
            return True
        if platform == "macos":
            return False       # frameworks are interlinked; only data dirs above are removed
        return False
    if _matches(low, [f".*{p}" for p in COMMON_FILES]):
        return True
    if _matches(base, PY_FILES):
        return True
    if "pyside6/" in low or "/pyside6" in low:
        m = re.fullmatch(r"(qt\w+)\.(pyd|abi3\.so|so)", base)
        if m and platform in ("windows", "linux") and m.group(1) not in KEEP_PYSIDE_MODULES \
                and os.path.dirname(low).endswith("pyside6"):
            return True
    if platform == "windows":
        if _matches(low, WIN_DELETE_FILES):
            return True
        m = re.fullmatch(r"qt6(\w+?)\.dll", base)
        if m and m.group(1) not in WIN_KEEP_QT:
            return True
    if platform == "linux":
        if _matches(base, [LINUX_QT_LIBS + r"\.so[\d.]*"]) or _matches(base, LINUX_FILES):
            return True
    return False


def prune(root: Path, platform: str, dry: bool = False) -> int:
    before = _size(root)
    removed: list[tuple[int, str]] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        here = Path(dirpath)
        for name in list(dirnames):
            rel = (here / name).relative_to(root).as_posix()
            if _wanted(rel, name, True, platform):
                p = here / name
                removed.append((_size(p), rel + "/"))
                dirnames.remove(name)
                if not dry:
                    shutil.rmtree(p, ignore_errors=True)
        for name in filenames:
            rel = (here / name).relative_to(root).as_posix()
            if _wanted(rel, name, False, platform):
                p = here / name
                removed.append((_size(p), rel))
                if not dry:
                    p.unlink(missing_ok=True)
    removed.sort(reverse=True)
    for s, rel in removed[:25]:
        print(f"  -{s / 1e6:7.1f} MB  {rel}")
    if len(removed) > 25:
        print(f"  ... and {len(removed) - 25} more")
    saved = sum(s for s, _ in removed)
    print(f"{'would remove' if dry else 'removed'} {len(removed)} items, "
          f"{saved / 1e6:.1f} MB of {before / 1e6:.1f} MB")
    return saved


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--platform", choices=["windows", "linux", "macos"], required=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    prune(Path(a.root), a.platform, a.dry_run)
