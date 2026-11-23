package app.tileprint.engine

import app.tileprint.core.Paper
import app.tileprint.core.PlannedPage
import app.tileprint.core.TileLayout
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import java.time.LocalDate
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

data class OverlayOptions(
    val numbering: String = "seq",
    val cropMarks: Boolean = true,
    val overlapTicks: Boolean = true,
    val footer: Boolean = true,
    val scaleBar: Boolean = true,
    val imperialBar: Boolean = false,
    val footerName: String = "",
    val scaleText: String = "",
    val language: String = "en",
)

/** Per-sheet vector furniture: frame, neighbour arrows, ticks, footer. Port of overlay.py. */
object Overlay {
    private const val MM = Paper.PT_PER_MM.toFloat()
    private val STRINGS = mapOf(
        "en" to mapOf("page_of" to "Page %d of %d", "row_col" to "row %d, col %d", "scale" to "Scale ×%s"),
        "ar" to mapOf("page_of" to "صفحة %d من %d", "row_col" to "صف %d، عمود %d", "scale" to "المقياس ×%s"),
    )

    private fun PDPageContentStream.line(x1: Float, y1: Float, x2: Float, y2: Float) {
        moveTo(x1, y1); lineTo(x2, y2); stroke()
    }

    private fun PDPageContentStream.triangle(cx: Float, cy: Float, size: Float, dir: String) {
        val h = size / 2
        val p = when (dir) {
            "left" -> floatArrayOf(cx + h, cy - h, cx + h, cy + h, cx - h, cy)
            "right" -> floatArrayOf(cx - h, cy - h, cx - h, cy + h, cx + h, cy)
            "up" -> floatArrayOf(cx - h, cy - h, cx + h, cy - h, cx, cy + h)
            else -> floatArrayOf(cx - h, cy + h, cx + h, cy + h, cx, cy - h)
        }
        setNonStrokingColor(0f)
        moveTo(p[0], p[1]); lineTo(p[2], p[3]); lineTo(p[4], p[5]); closePath(); fill()
    }

    /** Real overlap with each neighbour (smart cuts can make it larger than nominal). */
    private fun overlaps(l: TileLayout, row: Int, col: Int): Map<String, Float> {
        val out = HashMap<String, Float>()
        if (col > 0) out["left"] = (l.xs[col - 1] + l.frameW - l.xs[col]).toFloat()
        if (col < l.cols - 1) out["right"] = (l.xs[col] + l.frameW - l.xs[col + 1]).toFloat()
        if (row > 0) out["up"] = (l.ys[row - 1] + l.frameH - l.ys[row]).toFloat()
        if (row < l.rows - 1) out["down"] = (l.ys[row] + l.frameH - l.ys[row + 1]).toFloat()
        return out
    }

    fun draw(cs: PDPageContentStream, f: PdfFonts, layout: TileLayout, page: PlannedPage, opt: OverlayOptions) {
        val fr = layout.frame
        val x0 = fr[0].toFloat(); val y0 = fr[1].toFloat(); val x1 = fr[2].toFloat(); val y1 = fr[3].toFloat()
        val m = layout.margin.toFloat()
        val hdr = layout.header.toFloat()

        // thin frame
        cs.setStrokingColor(0f); cs.setNonStrokingColor(0f)
        cs.setLineWidth(0.4f)
        cs.addRect(x0, y0, x1 - x0, y1 - y0); cs.stroke()

        // crop marks
        if (opt.cropMarks && m >= 3 * MM) {
            val gap = 1f * MM
            val ln = max(min(m - 1 * MM, 5 * MM) - 1f * MM, 1.5f * MM)
            cs.setLineWidth(0.3f)
            for (x in floatArrayOf(x0, x1)) {
                cs.line(x, y0 - gap, x, y0 - gap - ln)
                if (hdr > 0) cs.line(x, y1 + gap, x, y1 + gap + min(ln, 2.5f * MM))
            }
            for (y in floatArrayOf(y0, y1)) {
                cs.line(x0 - gap, y, x0 - gap - ln, y)
                cs.line(x1 + gap, y, x1 + gap + ln, y)
            }
        }

        // overlap ticks: short marks in the margins only (the content area stays clean)
        if (opt.overlapTicks && m >= 3 * MM) {
            val ov = overlaps(layout, page.tile.row, page.tile.col)
            val gap = 1f * MM
            val ln = max(min(m - 1 * MM, 4 * MM) - 1f * MM, 1.5f * MM)
            cs.setStrokingColor(0.35f); cs.setLineWidth(0.5f)
            val xs = ArrayList<Float>(); val ys = ArrayList<Float>()
            if ("left" in page.neighbors) ov["left"]?.let { xs.add(x0 + it) }
            if ("right" in page.neighbors) ov["right"]?.let { xs.add(x1 - it) }
            if ("up" in page.neighbors) ov["up"]?.let { ys.add(y1 - it) }
            if ("down" in page.neighbors) ov["down"]?.let { ys.add(y0 + it) }
            for (x in xs) cs.line(x, y0 - gap, x, y0 - gap - ln)
            for (y in ys) {
                cs.line(x0 - gap, y, x0 - gap - ln, y)
                cs.line(x1 + gap, y, x1 + gap + ln, y)
            }
            cs.setStrokingColor(0f); cs.setLineWidth(0.4f)
        }

        // header: neighbour arrows + current page
        if (hdr > 0) {
            val fs = max(6f, min(11f, hdr * 0.55f))
            val tri = fs * 0.8f
            val base = y1 + (hdr - fs * 0.72f) / 2 - 0.5f
            val mid = base + fs * 0.36f
            val inset = 3 * MM
            val cxp = (x0 + x1) / 2
            val centerTxt = if (opt.numbering == "rc") page.label else page.number.toString()
            val small = if (opt.numbering == "seq") "/ ${page.total}" else "${page.number}/${page.total}"
            val bigFs = fs * 1.35f
            val wBig = PdfText.width(centerTxt, bigFs, true, f)
            val wSmall = PdfText.width(small, fs * 0.8f, false, f)
            val totalW = wBig + 3 + wSmall
            PdfText.draw(cs, f, cxp - totalW / 2, base - 0.5f, centerTxt, bigFs, true)
            PdfText.draw(cs, f, cxp - totalW / 2 + wBig + 3, base, small, fs * 0.8f)
            val leftEdge = cxp - totalW / 2
            val rightEdge = cxp + totalW / 2
            val gap = 2.5f
            page.neighbors["left"]?.let {
                cs.triangle(x0 + inset + tri / 2, mid, tri, "left")
                PdfText.draw(cs, f, x0 + inset + tri + gap, base, it, fs, true)
            }
            page.neighbors["right"]?.let {
                PdfText.draw(cs, f, x1 - inset - tri - gap, base, it, fs, true, PdfText.Align.RIGHT)
                cs.triangle(x1 - inset - tri / 2, mid, tri, "right")
            }
            page.neighbors["up"]?.let {
                val wt = PdfText.width(it, fs, true, f)
                val xr = leftEdge - 8
                PdfText.draw(cs, f, xr, base, it, fs, true, PdfText.Align.RIGHT)
                cs.triangle(xr - wt - gap - tri / 2, mid, tri, "up")
            }
            page.neighbors["down"]?.let {
                val xl = rightEdge + 8
                cs.triangle(xl + tri / 2, mid, tri, "down")
                PdfText.draw(cs, f, xl + tri + gap, base, it, fs, true)
            }
        }

        // footer
        if (opt.footer && m >= 5 * MM) {
            val fs = 6.5f
            val yb = m / 2 - fs * 0.35f
            val s = STRINGS[opt.language] ?: STRINGS.getValue("en")
            val leftW = (x1 - x0) * 0.38f
            if (opt.footerName.isNotEmpty()) {
                PdfText.draw(cs, f, x0, yb, PdfText.fit(opt.footerName, fs, leftW, f), fs)
            }
            val midTxt = s.getValue("page_of").format(Locale.US, page.number, page.total) + "  (" +
                s.getValue("row_col").format(Locale.US, page.tile.row + 1, page.tile.col + 1) + ")"
            PdfText.draw(cs, f, (x0 + x1) / 2, yb, midTxt, fs, false, PdfText.Align.CENTER)
            val bits = ArrayList<String>()
            if (opt.scaleText.isNotEmpty()) bits.add(s.getValue("scale").format(Locale.US, opt.scaleText))
            bits.add(LocalDate.now().toString())
            val right = bits.joinToString("  ·  ")
            PdfText.draw(cs, f, x1, yb, right, fs, false, PdfText.Align.RIGHT)
            if (opt.scaleBar) {
                val options = if (opt.imperialBar)
                    listOf(Triple(2 * 72f, "2", "in"), Triple(72f, "1", "in"))
                else listOf(Triple(5 * 10 * MM, "5", "cm"), Triple(3 * 10 * MM, "3", "cm"), Triple(2 * 10 * MM, "2", "cm"))
                val rw = PdfText.width(right, fs, false, f)
                val bx1 = x1 - rw - 10
                val floor = (x0 + x1) / 2 + PdfText.width(midTxt, fs, false, f) / 2 + 12
                for ((length, v, u) in options) {
                    val label = "$v $u"
                    val bx0 = bx1 - length
                    if (bx0 - PdfText.width(label, fs * 0.9f, false, f) - 3 > floor) {
                        cs.setLineWidth(0.5f)
                        cs.line(bx0, yb + 1.0f, bx1, yb + 1.0f)
                        for (x in floatArrayOf(bx0, bx1)) cs.line(x, yb - 1.2f, x, yb + 3.2f)
                        PdfText.draw(cs, f, bx0 - 3, yb, label, fs * 0.9f, false, PdfText.Align.RIGHT)
                        break
                    }
                }
            }
        }
    }
}
