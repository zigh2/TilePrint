import math

import pytest

from tileprint import layout as L
from tileprint import paper as P

MM = P.PT_PER_MM


def test_paper_sizes_iso():
    w, h = P.paper_size("A4")
    assert (round(w / MM), round(h / MM)) == (210, 297)
    w, h = P.paper_size("A0")
    assert (round(w / MM), round(h / MM)) == (841, 1189)
    w, h = P.paper_size("A3", landscape=True)
    assert (round(w / MM), round(h / MM)) == (420, 297)
    assert P.to_pt(1, "in") == 72 and P.from_pt(72, "in") == 1


def test_place_content_modes():
    fit = L.place_content(200, 100, 400, 400, "fit")
    assert (fit.width, fit.height) == (400, 200) and fit.y == 100
    fill = L.place_content(200, 100, 400, 400, "fill")
    assert (fill.width, fill.height) == (800, 400) and fill.x == -200
    st = L.place_content(200, 100, 400, 400, "stretch")
    assert (st.sx, st.sy) == (2, 4)
    assert L.size_from_width(200, 100, 50) == (50, 25)
    assert L.effective_dpi(3000, 72 * 10) == 300


def test_row_letters():
    assert [L.row_letters(i) for i in (0, 25, 26, 27, 701, 702)] == ["A", "Z", "AA", "AB", "ZZ", "AAA"]


def test_axis_exact_cover_and_overlap():
    xs = L.axis_starts(1000, 300, 20)
    assert xs[0] == 0 and xs[-1] + 300 >= 1000
    assert all(abs((b - a) - 280) < 1e-9 for a, b in zip(xs, xs[1:]))
    assert L.axis_starts(250, 300, 20) == [0.0]


def test_layout_counts_and_frame():
    lay = L.build_layout(*P.paper_size("A0"), *P.paper_size("A4"), 10 * MM, 9 * MM, 10 * MM)
    fw, fh = 190 * MM, 268 * MM
    assert lay.frame_w == pytest.approx(fw) and lay.frame_h == pytest.approx(fh)
    assert lay.cols == math.ceil((841 * MM - 10 * MM) / (fw - 10 * MM))
    assert lay.rows == math.ceil((1189 * MM - 10 * MM) / (fh - 10 * MM))
    with pytest.raises(ValueError):
        L.build_layout(1000, 1000, 100, 100, 40, 40, 10)


def test_plan_labels_and_neighbors():
    lay = L.build_layout(500, 500, 200, 200, 10, 10, 10)     # 3x3
    plan = lay.plan()
    assert len(plan) == lay.rows * lay.cols
    mid = next(p for p in plan if (p.tile.row, p.tile.col) == (1, 1))
    assert mid.number == 5 and mid.neighbors == {"left": "4", "right": "6", "up": "2", "down": "8"}
    corner = plan[0]
    assert set(corner.neighbors) == {"right", "down"}
    rc = lay.plan(numbering="rc")
    assert rc[0].label == "A1" and rc[4].label == "B2" and rc[4].neighbors["right"] == "B3"


def test_skipped_tiles_are_renumbered_and_not_referenced():
    lay = L.build_layout(500, 500, 200, 200, 10, 10, 10)
    plan = lay.plan(skip={(0, 1)})
    assert len(plan) == lay.rows * lay.cols - 1
    first = plan[0]
    assert "right" not in first.neighbors and first.neighbors["down"] == "3"


def test_smart_cut_moves_edge_to_quiet_column():
    frame, ov = 300.0, 20.0
    prof = [1.0] * 1000
    prof[265] = 0.0                       # a white gap just before the ideal edge (280)
    xs = L.axis_starts(1000, frame, ov, prof, 1.0, slack=30.0)
    assert xs[1] == 265
    assert xs[1] + frame - xs[2] >= ov    # overlap never shrinks below the minimum


def test_best_orientation():
    # a wide poster prefers landscape sheets
    wide = L.best_orientation(1189 * MM, 300 * MM, 210 * MM, 297 * MM, 10 * MM, 9 * MM, 10 * MM)
    tall = L.best_orientation(300 * MM, 1189 * MM, 210 * MM, 297 * MM, 10 * MM, 9 * MM, 10 * MM)
    assert wide is True and tall is False
