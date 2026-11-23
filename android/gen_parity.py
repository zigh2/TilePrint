"""Regenerates android/core/src/test/resources/parity.txt from the Python engine.

Run from the repo root:  python android/tools_gen_parity.py
The Kotlin ParityTest then proves the Android engine computes the same layouts as the desktop one.
"""
import random, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from tileprint import layout as L, paper as P, source as S, project as PR
from PIL import Image

MM = P.PT_PER_MM
out = []
def r(x): return repr(float(x))
def csv(v): return ",".join(r(x) for x in v) if len(v) else "-"

for name in sorted(P.PAPER_SIZES_PT):
    w, h = P.PAPER_SIZES_PT[name]; out.append(f"paper|{name}|{r(w)}|{r(h)}")
out.append("order|" + ",".join(P.PRESET_ORDER))

cases = [(841,1189,210,297,10,9,10), (594,841,297,420,8,8,12), (1000,500,210,297,10,9,10),
         (3000,1200,216,279,6,7,0), (420,594,210,297,15,10,5), (200,280,210,297,10,9,10),
         (1189,841,420,297,10,9,15), (5000,2500,297,420,12,9,20), (841,1189,148,210,5,6,8)]
for c in cases:
    pw, ph, aw, ah, m, h, o = [v * MM for v in c]
    lay = L.build_layout(pw, ph, aw, ah, m, h, o)
    out.append(f"layout|{r(pw)}|{r(ph)}|{r(aw)}|{r(ah)}|{r(m)}|{r(h)}|{r(o)}|{lay.rows}|{lay.cols}|{csv(lay.xs)}|{csv(lay.ys)}")
    out.append(f"orient|{r(pw)}|{r(ph)}|{r(aw)}|{r(ah)}|{r(m)}|{r(h)}|{r(o)}|{int(L.best_orientation(pw, ph, aw, ah, m, h, o))}")
    for numbering in ("seq", "rc"):
        for skip in (set(), {(0, 1), (1, 0)}, {(lay.rows - 1, lay.cols - 1)} if lay.rows * lay.cols > 1 else set()):
            plan = lay.plan(skip, numbering)
            sig = ";".join(f"{p.number}:{p.label}:" + "/".join(f"{k}={p.neighbors[k]}" for k in sorted(p.neighbors)) for p in plan)
            sk = ",".join(f"{a}.{b}" for a, b in sorted(skip)) or "-"
            out.append(f"plan|{r(pw)}|{r(ph)}|{r(aw)}|{r(ah)}|{r(m)}|{r(h)}|{r(o)}|{numbering}|{sk}|{len(plan)}|{sig}")

for (sw, sh, pw, ph, mode, ox, oy) in [(595.3, 841.9, 2383.9, 3370.4, "fit", 0, 0), (595.3, 841.9, 2383.9, 3370.4, "fill", 10, -20),
                                       (800, 400, 1000, 1000, "stretch", 5, 5), (300, 600, 1000, 500, "fit", 0, 0), (300, 600, 1000, 500, "fill", 0, 0)]:
    p = L.place_content(sw, sh, pw, ph, mode, (ox, oy))
    out.append(f"place|{r(sw)}|{r(sh)}|{r(pw)}|{r(ph)}|{mode}|{r(ox)}|{r(oy)}|{r(p.sx)}|{r(p.sy)}|{r(p.x)}|{r(p.y)}|{r(p.width)}|{r(p.height)}")

for (total, frame, ov, slack) in [(2383.9, 538.6, 28.3, 0), (2383.9, 538.6, 28.3, 42.5), (3370.4, 759.7, 28.3, 42.5), (1500, 500, 0, 30), (900, 500, 20, 60)]:
    prof = [((i * 37) % 11) / 10.0 for i in range(int(total) + 2)]
    starts = L.axis_starts(total, frame, ov, prof if slack else None, 1.0, slack)
    out.append(f"axis|{r(total)}|{r(frame)}|{r(ov)}|{r(slack)}|{csv(starts)}")

random.seed(7)
for k in range(8):
    w, h = random.choice([(120, 90), (200, 150), (97, 131), (333, 211)])
    rects = []
    for _ in range(random.randrange(1, 5)):
        x, y = random.randrange(0, w - 5), random.randrange(0, h - 5)
        rects.append((x, y, min(w, x + random.randrange(1, 40)), min(h, y + random.randrange(1, 30))))
    img = Image.new("L", (w, h), 255)
    for x0, y0, x1, y1 in rects: img.paste(0, (x0, y0, x1, y1))
    cols, rows = S.ink_profiles(img)
    res = 12.5
    lay = L.build_layout(w * res, h * res, 210 * MM * 2, 297 * MM * 2, 10 * MM, 9 * MM, 10 * MM)
    blank = S.blank_tiles(img, lay, res)
    rs = ";".join(f"{a},{b},{c},{d}" for a, b, c, d in rects)
    out.append(f"ink|{w}|{h}|{rs}|{csv(cols)}|{csv(rows)}|{r(res)}|{','.join(f'{a}.{b}' for a, b in sorted(blank)) or '-'}")

class Src:
    original_path = "x.pdf"; size_pt = (595.2756, 841.8898); pixel_size = (3000, 2000)
for preset, orient, paper, porient in [("A0", "auto", "A4", "auto"), ("A2", "landscape", "A3", "portrait"), ("A1", "portrait", "Letter", "landscape")]:
    s = PR.Settings(poster_preset=preset, poster_orient=orient, paper=paper, paper_orient=porient, skip_blank=False, smart_cut=False)
    job = PR.build_job(Src(), s)
    out.append(f"job|{preset}|{orient}|{paper}|{porient}|{r(job.poster_w)}|{r(job.poster_h)}|{r(job.paper_w)}|{r(job.paper_h)}|{job.layout.rows}|{job.layout.cols}|{r(job.dpi)}")


# --- rotated sources: the Kotlin exporter resets /Rotate and rotates itself; compare with qpdf's own handling
import pikepdf
for rot in (0, 90, 180, 270):
    for (W0, H0) in ((595.2756, 841.8898), (300.0, 500.0)):
        pdf = pikepdf.Pdf.new()
        page = pdf.add_blank_page(page_size=(W0, H0))
        page.obj.Rotate = rot
        form = pdf.make_indirect(page.as_form_xobject())
        from tileprint import exporter as X
        ox, oy, gw, gh = X._form_geometry(form)
        fm = pikepdf.Matrix(*(float(v) for v in form.get("/Matrix", [1, 0, 0, 1, 0, 0])))
        sx, sy, plx, ply = 2.5, 2.5, 120.0, 340.0
        tx, ty = 260.0, 400.0
        fx0, fy0, fx1, fy1 = 28.3, 28.3, 566.9, 800.0
        posterW, posterH = 2000.0, 1800.0
        for (x, y) in ((0, 0), (W0, 0), (0, H0), (W0, H0), (W0 * 0.3, H0 * 0.7)):
            xf, yf = fm.transform((x, y))
            e = fx0 + plx - tx - ox * sx
            f = fy1 - ply + ty - gh * sy - oy * sy
            X_, Y_ = sx * xf + e, sy * yf + f
            out.append(f"srcxf|{rot}|{r(W0)}|{r(H0)}|{r(sx)}|{r(sy)}|{r(plx)}|{r(ply)}|{r(tx)}|{r(ty)}|{r(fx0)}|{r(fy0)}|{r(fx1)}|{r(fy1)}|{r(posterW)}|{r(posterH)}|{r(x)}|{r(y)}|{r(X_)}|{r(Y_)}")

dest = ROOT / "android/core/src/test/resources/parity.txt"
dest.write_text("\n".join(out) + "\n")
print(len(out), "parity lines ->", dest)
