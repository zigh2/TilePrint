package app.tileprint.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

private operator fun <T> List<T>.component6() = this[5]
private operator fun <T> List<T>.component7() = this[6]
private operator fun <T> List<T>.component8() = this[7]
private operator fun <T> List<T>.component9() = this[8]

/** Proves the Kotlin engine matches the Python desktop engine (expectations come from parity.txt). */
class ParityTest {
    private val rows: List<List<String>> by lazy {
        javaClass.getResourceAsStream("/parity.txt")!!.bufferedReader().readLines()
            .filter { it.isNotBlank() }.map { it.split("|") }
    }

    private fun kind(k: String) = rows.filter { it[0] == k }
    private fun arr(s: String) = if (s == "-") DoubleArray(0) else s.split(",").map { it.toDouble() }.toDoubleArray()
    private fun near(exp: Double, act: Double, what: String, tol: Double = 1e-6) =
        assertTrue("$what: expected $exp got $act", Math.abs(exp - act) <= tol * maxOf(1.0, Math.abs(exp)))
    private fun nearArr(exp: DoubleArray, act: List<Double>, what: String, tol: Double = 1e-6) {
        assertEquals("$what size", exp.size, act.size)
        exp.indices.forEach { near(exp[it], act[it], "$what[$it]", tol) }
    }
    private fun skipSet(s: String): Set<Pair<Int, Int>> =
        if (s == "-") emptySet() else s.split(",").map { it.split(".").let { p -> p[0].toInt() to p[1].toInt() } }.toSet()

    @Test fun paperSizesAndPresetOrder() {
        for (r in kind("paper")) {
            val (w, h) = Paper.sizesPt.getValue(r[1])
            near(r[2].toDouble(), w, "${r[1]} width"); near(r[3].toDouble(), h, "${r[1]} height")
        }
        assertEquals(kind("order")[0][1], Paper.presetOrder.joinToString(","))
        assertTrue(kind("paper").size >= 29)
    }

    @Test fun layoutsMatch() {
        assertTrue(kind("layout").isNotEmpty())
        for (r in kind("layout")) {
            val v = r.subList(1, 8).map { it.toDouble() }
            val lay = buildLayout(v[0], v[1], v[2], v[3], v[4], v[5], v[6])
            assertEquals("rows", r[8].toInt(), lay.rows); assertEquals("cols", r[9].toInt(), lay.cols)
            nearArr(arr(r[10]), lay.xs, "xs"); nearArr(arr(r[11]), lay.ys, "ys")
        }
    }

    @Test fun orientationChoiceMatches() {
        for (r in kind("orient")) {
            val v = r.subList(1, 8).map { it.toDouble() }
            assertEquals("orient ${r.subList(1, 8)}", r[8] == "1", bestOrientation(v[0], v[1], v[2], v[3], v[4], v[5], v[6]))
        }
    }

    @Test fun plansLabelsAndNeighboursMatch() {
        assertTrue(kind("plan").size > 20)
        for (r in kind("plan")) {
            val v = r.subList(1, 8).map { it.toDouble() }
            val lay = buildLayout(v[0], v[1], v[2], v[3], v[4], v[5], v[6])
            val plan = lay.plan(skipSet(r[9]), r[8])
            assertEquals("count", r[10].toInt(), plan.size)
            val sig = plan.joinToString(";") { p ->
                "${p.number}:${p.label}:" + p.neighbors.toSortedMap().entries.joinToString("/") { "${it.key}=${it.value}" }
            }
            assertEquals("plan ${r.subList(1, 10)}", r[11], sig)
        }
    }

    @Test fun contentPlacementMatches() {
        for (r in kind("place")) {
            val mode = ScaleMode.valueOf(r[5].uppercase())
            val p = placeContent(r[1].toDouble(), r[2].toDouble(), r[3].toDouble(), r[4].toDouble(), mode, r[6].toDouble(), r[7].toDouble())
            listOf(p.sx, p.sy, p.x, p.y, p.width, p.height).forEachIndexed { i, a -> near(r[8 + i].toDouble(), a, "place[$i]") }
        }
    }

    @Test fun smartCutAxisMatches() {
        for (r in kind("axis")) {
            val total = r[1].toDouble(); val slack = r[4].toDouble()
            val prof = DoubleArray(total.toInt() + 2) { ((it * 37) % 11) / 10.0 }
            val starts = axisStarts(total, r[2].toDouble(), r[3].toDouble(), if (slack > 0) prof else null, 1.0, slack)
            nearArr(arr(r[5]), starts, "axis ${r.subList(1, 5)}")
        }
    }

    @Test fun inkProfilesAndBlankTilesMatch() {
        assertTrue(kind("ink").size >= 8)
        for (r in kind("ink")) {
            val w = r[1].toInt(); val h = r[2].toInt()
            val gray = ByteArray(w * h) { 255.toByte() }
            for (rect in r[3].split(";")) {
                val (x0, y0, x1, y1) = rect.split(",").map { it.toInt() }
                for (y in y0 until y1) for (x in x0 until x1) gray[y * w + x] = 0
            }
            val raster = PosterRaster(gray, w, h, r[6].toDouble())
            val (cols, rowsP) = Raster.inkProfiles(raster)
            // PIL's two-pass 8-bit resize may differ from plain rounding by one quantum at exact halves
            val oneQuantum = 1.01 / 255
            nearArr(arr(r[4]), cols.toList(), "cols", oneQuantum); nearArr(arr(r[5]), rowsP.toList(), "rows", oneQuantum)
            val res = raster.res; val mm = Paper.PT_PER_MM
            val lay = buildLayout(w * res, h * res, 210 * mm * 2, 297 * mm * 2, 10 * mm, 9 * mm, 10 * mm)
            assertEquals("blank tiles", skipSet(r[7]), Raster.blankTiles(raster, lay))
        }
    }

    @Test fun jobsMatch() {
        for (r in kind("job")) {
            val s = Settings(posterPreset = r[1], posterOrient = Settings.Orient.valueOf(r[2].uppercase()), paper = r[3],
                paperOrient = Settings.Orient.valueOf(r[4].uppercase()), skipBlank = false, smartCut = false)
            val job = buildJob(SourceInfo("x.pdf", 595.2756, 841.8898, 1, 3000, 2000), s) { _, _, _ -> error("no raster expected") }
            near(r[5].toDouble(), job.posterW, "posterW"); near(r[6].toDouble(), job.posterH, "posterH")
            near(r[7].toDouble(), job.paperW, "paperW"); near(r[8].toDouble(), job.paperH, "paperH")
            assertEquals(r[9].toInt(), job.layout.rows); assertEquals(r[10].toInt(), job.layout.cols)
            near(r[11].toDouble(), job.dpi!!, "dpi")
        }
    }

    @Test fun rotatedSourcesLandWhereQpdfPutsThem() {
        assertTrue(kind("srcxf").size >= 40)
        for (r in kind("srcxf")) {
            val v = r.subList(1, r.size).map { it.toDouble() }
            val (rot, w0, h0, sx, sy, plx, ply, tx, ty) = listOf(v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8])
            val frame = doubleArrayOf(v[9], v[10], v[11], v[12])
            val pl = Placement(sx, sy, plx, ply, w0 * sx, h0 * sy)
            val t = sourceTransform(rot.toInt(), 0.0, 0.0, w0, h0, pl, v[13], v[14], frame, tx, ty)
            val x = v[15]; val y = v[16]
            near(v[17], t.a * x + t.c * y + t.e, "X rot=${rot.toInt()} ($x,$y)")
            near(v[18], t.b * x + t.d * y + t.f, "Y rot=${rot.toInt()} ($x,$y)")
        }
    }

    @Test fun rowLettersAndSmallHelpers() {
        assertEquals(listOf("A", "Z", "AA", "AB", "ZZ", "AAA"), listOf(0, 25, 26, 27, 701, 702).map { rowLetters(it) })
        assertEquals(300.0, effectiveDpi(3000.0, 720.0), 1e-9)
        assertEquals(50.0 to 25.0, sizeFromWidth(200.0, 100.0, 50.0))
    }
}
