package app.tileprint.core

import kotlin.math.abs
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min

/**
 * Pure tiling geometry. Port of layout.py (kept line-for-line comparable; a parity test checks it).
 *
 * Poster space: origin top-left, y DOWN, points. Page space: PDF native, origin bottom-left, y UP.
 */
const val EPS = 1e-6

enum class ScaleMode { FIT, FILL, STRETCH }

data class Placement(val sx: Double, val sy: Double, val x: Double, val y: Double,
                     val width: Double, val height: Double)

fun placeContent(srcW: Double, srcH: Double, posterW: Double, posterH: Double,
                 mode: ScaleMode = ScaleMode.FIT, offsetX: Double = 0.0, offsetY: Double = 0.0): Placement {
    require(srcW > 0 && srcH > 0) { "source has zero size" }
    val (sx, sy) = when (mode) {
        ScaleMode.STRETCH -> (posterW / srcW) to (posterH / srcH)
        ScaleMode.FILL -> max(posterW / srcW, posterH / srcH).let { it to it }
        ScaleMode.FIT -> min(posterW / srcW, posterH / srcH).let { it to it }
    }
    val w = srcW * sx
    val h = srcH * sy
    return Placement(sx, sy, (posterW - w) / 2 + offsetX, (posterH - h) / 2 + offsetY, w, h)
}

fun sizeFromWidth(srcW: Double, srcH: Double, width: Double) = width to width * srcH / srcW
fun sizeFromHeight(srcW: Double, srcH: Double, height: Double) = height * srcW / srcH to height

fun effectiveDpi(pixels: Double, scaledLengthPt: Double): Double {
    val inches = scaledLengthPt / 72.0
    return if (inches > 0) pixels / inches else Double.POSITIVE_INFINITY
}

/** 0 -> A, 25 -> Z, 26 -> AA ... */
fun rowLetters(n0: Int): String {
    var n = n0 + 1
    val sb = StringBuilder()
    while (n > 0) {
        val r = (n - 1) % 26
        n = (n - 1) / 26
        sb.insert(0, ('A' + r))
    }
    return sb.toString()
}

data class Tile(val row: Int, val col: Int, val x: Double, val y: Double, val w: Double, val h: Double) {
    val key: Pair<Int, Int> get() = row to col
}

data class PlannedPage(val tile: Tile, val number: Int, val label: String,
                       val neighbors: Map<String, String>, val total: Int)

/** Position in [lo, hi] (poster pt) with the least ink; ties go to the largest. */
internal fun quietest(profile: DoubleArray, res: Double, lo: Double, hi: Double): Double {
    val i0 = max(0, ceil(lo / res).toInt())
    val i1 = min(profile.size - 1, floor(hi / res).toInt())
    if (i1 < i0) return hi
    var bestI = i1
    var bestV = profile[i1]
    var i = i1
    while (i >= i0) {
        if (profile[i] < bestV - 1e-12) {
            bestI = i
            bestV = profile[i]
        }
        i--
    }
    return bestI * res
}

fun axisStarts(total: Double, frame: Double, overlap: Double, profile: DoubleArray? = null,
               profileRes: Double = 1.0, slack: Double = 0.0): List<Double> {
    require(frame > overlap + EPS) { "frame must be larger than the overlap" }
    if (total <= frame + EPS) return listOf(0.0)
    val step = frame - overlap
    val starts = arrayListOf(0.0)
    while (starts.last() + frame < total - EPS) {
        val ideal = starts.last() + step
        var nxt = ideal
        if (profile != null && slack > 0) {
            val lo = max(ideal - slack, starts.last() + 1.0)
            nxt = quietest(profile, profileRes, lo, ideal)
        }
        starts.add(nxt)
    }
    return starts
}

class TileLayout(val posterW: Double, val posterH: Double, val paperW: Double, val paperH: Double,
                 val margin: Double, val header: Double, val overlap: Double,
                 val xs: List<Double>, val ys: List<Double>) {
    /** (x0, y0, x1, y1) of the thin frame on the page (page space). */
    val frame: DoubleArray get() = doubleArrayOf(margin, margin, paperW - margin, paperH - margin - header)
    val frameW: Double get() = paperW - 2 * margin
    val frameH: Double get() = paperH - 2 * margin - header
    val cols: Int get() = xs.size
    val rows: Int get() = ys.size

    fun tiles(): List<Tile> = ys.withIndex().flatMap { (r, y) ->
        xs.withIndex().map { (c, x) -> Tile(r, c, x, y, frameW, frameH) }
    }

    /** Printed pages in reading order. numbering: "seq" (1,2,3 ...) or "rc" (A1, B2 ...). */
    fun plan(skip: Set<Pair<Int, Int>> = emptySet(), numbering: String = "seq"): List<PlannedPage> {
        val printed = tiles().filter { it.key !in skip }
        val labels = HashMap<Pair<Int, Int>, String>()
        printed.forEachIndexed { i, t ->
            labels[t.key] = if (numbering == "seq") (i + 1).toString() else "${rowLetters(t.row)}${t.col + 1}"
        }
        return printed.mapIndexed { i, t ->
            val nb = LinkedHashMap<String, String>()
            for ((name, d) in listOf("left" to (0 to -1), "right" to (0 to 1), "up" to (-1 to 0), "down" to (1 to 0))) {
                labels[(t.row + d.first) to (t.col + d.second)]?.let { nb[name] = it }
            }
            PlannedPage(t, i + 1, labels.getValue(t.key), nb, printed.size)
        }
    }
}

fun buildLayout(posterW: Double, posterH: Double, paperW: Double, paperH: Double,
                margin: Double, header: Double, overlap: Double,
                inkX: DoubleArray? = null, inkY: DoubleArray? = null,
                inkRes: Double = 1.0, smartSlack: Double = 0.0): TileLayout {
    val fw = paperW - 2 * margin
    val fh = paperH - 2 * margin - header
    require(fw > overlap + EPS && fh > overlap + EPS) { "margins/header/overlap leave no printable area" }
    return TileLayout(posterW, posterH, paperW, paperH, margin, header, overlap,
        axisStarts(posterW, fw, overlap, inkX, inkRes, smartSlack),
        axisStarts(posterH, fh, overlap, inkY, inkRes, smartSlack))
}

/** True if landscape sheets need fewer pages than portrait (ties -> less waste -> portrait). */
fun bestOrientation(posterW: Double, posterH: Double, paperW: Double, paperH: Double,
                    margin: Double, header: Double, overlap: Double): Boolean {
    fun count(pw: Double, ph: Double): Pair<Long, Double> {
        val fw = pw - 2 * margin
        val fh = ph - 2 * margin - header
        if (fw <= overlap + EPS || fh <= overlap + EPS) return 1_000_000_000L to 0.0
        val n = axisStarts(posterW, fw, overlap).size.toLong() * axisStarts(posterH, fh, overlap).size
        return n to (n * fw * fh - posterW * posterH)
    }
    val p = count(min(paperW, paperH), max(paperW, paperH))
    val l = count(max(paperW, paperH), min(paperW, paperH))
    return l.first < p.first || (l.first == p.first && l.second < p.second)
}

/** Unused helper kept for API symmetry with the desktop engine. */
fun nearlyEqual(a: Double, b: Double) = abs(a - b) < 1e-6
