import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import prune_bundle as pb  # noqa: E402


def _touch(root: Path, rel: str, size: int = 10):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"x" * size)


def test_windows_prune_keeps_core_removes_unused(tmp_path):
    keep = ["_internal/PySide6/Qt6Core.dll", "_internal/PySide6/Qt6Gui.dll",
            "_internal/PySide6/Qt6Widgets.dll", "_internal/PySide6/QtCore.pyd",
            "_internal/PySide6/QtGui.pyd", "_internal/PySide6/QtWidgets.pyd",
            "_internal/PySide6/plugins/platforms/qwindows.dll",
            "_internal/PySide6/plugins/styles/qmodernwindowsstyle.dll",
            "_internal/PySide6/plugins/imageformats/qjpeg.dll",
            "_internal/PySide6/shiboken6.abi3.dll", "_internal/pikepdf/_core.pyd",
            "_internal/PIL/_imaging.pyd", "_internal/tileprint/assets/fonts/NotoSans-Regular.ttf"]
    gone = ["_internal/PySide6/opengl32sw.dll", "_internal/PySide6/Qt6Quick.dll",
            "_internal/PySide6/Qt6Qml.dll", "_internal/PySide6/Qt6Network.dll",
            "_internal/PySide6/Qt6OpenGL.dll", "_internal/PySide6/QtOpenGL.pyd",
            "_internal/PySide6/QtQml.pyd", "_internal/PySide6/pyside6qml.abi3.dll",
            "_internal/PySide6/translations/qtbase_de.qm", "_internal/PySide6/qml/x/y.qml",
            "_internal/PySide6/plugins/sqldrivers/qsqlite.dll",
            "_internal/PySide6/plugins/imageformats/qsvg.dll",
            "_internal/PySide6/plugins/platforms/qdirect2d.dll",
            "_internal/numpy/__init__.py", "_internal/numpy.libs/openblas.dll"]
    for rel in keep + gone:
        _touch(tmp_path, rel)
    pb.prune(tmp_path, "windows")
    for rel in keep:
        assert (tmp_path / rel).exists(), f"wrongly removed {rel}"
    for rel in gone:
        assert not (tmp_path / rel).exists(), f"not removed {rel}"


def test_macos_prune_only_touches_data(tmp_path):
    _touch(tmp_path, "Contents/Frameworks/PySide6/Qt/lib/QtQuick.framework/QtQuick")
    _touch(tmp_path, "Contents/Frameworks/PySide6/Qt/translations/a.qm")
    pb.prune(tmp_path, "macos")
    assert (tmp_path / "Contents/Frameworks/PySide6/Qt/lib/QtQuick.framework/QtQuick").exists()
    assert not (tmp_path / "Contents/Frameworks/PySide6/Qt/translations").exists()


def test_selftest_runs_from_source(tmp_path):
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", TILEPRINT_SELFTEST_LOG=str(tmp_path / "log.txt"))
    env["PYTHONPATH"] = str(ROOT / "src")
    r = subprocess.run([sys.executable, "-m", "tileprint", "--selftest"], env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "SELFTEST OK" in (tmp_path / "log.txt").read_text(encoding="utf-8")
