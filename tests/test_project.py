import pytest

from tileprint import project as PR
from tileprint import source as S
from tileprint.paper import PT_PER_MM


def test_settings_roundtrip(tmp_path):
    s = PR.Settings(poster_preset="A1", numbering="rc", smart_cut=True, offset=[3.0, -4.0])
    p = tmp_path / ("x" + PR.PROJECT_EXT)
    PR.save_project(str(p), s, "doc.pdf")
    s2, src = PR.load_project(str(p))
    assert s2 == s and src == str(tmp_path / "doc.pdf")


def test_unknown_keys_are_ignored():
    assert PR.Settings.from_dict({"poster_preset": "A2", "bogus": 1}).poster_preset == "A2"


def test_build_job_basic(vector_pdf):
    src = S.load_source(vector_pdf)
    job = PR.build_job(src, PR.Settings(poster_preset="A0", paper="A4"))
    assert round(job.poster_w / PT_PER_MM) == 841 and round(job.poster_h / PT_PER_MM) == 1189
    assert job.layout.rows * job.layout.cols >= 20
    assert job.dpi is None and job.scale > 3


def test_poster_orientation_auto_follows_source(tmp_path):
    from reportlab.pdfgen import canvas
    p = tmp_path / "wide.pdf"
    c = canvas.Canvas(str(p), pagesize=(800, 400)); c.rect(10, 10, 100, 100); c.save()
    job = PR.build_job(S.load_source(str(p)), PR.Settings(poster_preset="A1"))
    assert job.poster_w > job.poster_h


def test_smart_cut_and_blank_skip(corner_pdf):
    src = S.load_source(corner_pdf)
    job = PR.build_job(src, PR.Settings(poster_preset="A1", smart_cut=True, skip_blank=True))
    n = job.layout.rows * job.layout.cols
    assert len(job.skip) == n - 1


def test_custom_size_and_stretch(vector_pdf):
    src = S.load_source(vector_pdf)
    s = PR.Settings(poster_preset="Custom", poster_w=1000.0, poster_h=500.0, scale_mode="stretch")
    job = PR.build_job(src, s)
    assert (job.poster_w, job.poster_h) == (1000.0, 500.0)
    assert job.overlay.scale_text == ""          # non-uniform scale: no single scale shown
