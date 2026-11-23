package app.tileprint.core

import kotlin.math.floor

/** Paper sizes and units. All geometry is in PDF points (1/72 inch). Port of paper.py. */
object Paper {
    const val PT_PER_INCH = 72.0
    const val PT_PER_MM = PT_PER_INCH / 25.4
    const val PT_PER_CM = PT_PER_MM * 10

    enum class Unit(val label: String, val pt: Double) {
        MM("mm", PT_PER_MM), CM("cm", PT_PER_CM), IN("in", PT_PER_INCH);

        fun toPt(v: Double) = v * pt
        fun fromPt(v: Double) = v / pt
    }

    private fun iso(n: Int, w0: Double, h0: Double): Pair<Double, Double> {
        var w = w0
        var h = h0
        repeat(n) {
            val nw = h / 2
            val nh = w
            w = floor(nw)
            h = floor(nh)
        }
        return w to h
    }

    private val inSizes: LinkedHashMap<String, Pair<Double, Double>> = linkedMapOf(
        "Letter" to (8.5 to 11.0), "Legal" to (8.5 to 14.0), "Tabloid" to (11.0 to 17.0),
        "ANSI C" to (17.0 to 22.0), "ANSI D" to (22.0 to 34.0), "ANSI E" to (34.0 to 44.0),
        "ARCH A" to (9.0 to 12.0), "ARCH B" to (12.0 to 18.0), "ARCH C" to (18.0 to 24.0),
        "ARCH D" to (24.0 to 36.0), "ARCH E" to (36.0 to 48.0), "ARCH E1" to (30.0 to 42.0),
    )

    /** name -> (width, height) in points, portrait. */
    val sizesPt: Map<String, Pair<Double, Double>> = LinkedHashMap<String, Pair<Double, Double>>().apply {
        for (n in 0..8) iso(n, 841.0, 1189.0).let { put("A$n", it.first * PT_PER_MM to it.second * PT_PER_MM) }
        for (n in 0..8) iso(n, 1000.0, 1414.0).let { put("B$n", it.first * PT_PER_MM to it.second * PT_PER_MM) }
        for ((k, v) in inSizes) put(k, v.first * PT_PER_INCH to v.second * PT_PER_INCH)
    }

    /** Order shown in the UI. */
    val presetOrder: List<String> =
        (0..6).map { "A$it" } + (0..6).map { "B$it" } + inSizes.keys.toList()

    fun size(name: String, landscape: Boolean = false): Pair<Double, Double> {
        val (w, h) = sizesPt.getValue(name)
        return if (landscape) h to w else w to h
    }
}
