import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


@pytest.fixture()
def vector_pdf(tmp_path):
    p = tmp_path / "vec.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 36)
    c.drawString(40, h - 80, "VECTOR TEST")
    c.circle(w / 2, h / 2, 80, fill=1)
    c.save()
    return str(p)


@pytest.fixture()
def corner_pdf(tmp_path):
    """Ink only in the top-left corner: most poster tiles are blank."""
    p = tmp_path / "corner.pdf"
    c = canvas.Canvas(str(p), pagesize=A4)
    c.rect(10, A4[1] - 60, 50, 50, fill=1)
    c.save()
    return str(p)
