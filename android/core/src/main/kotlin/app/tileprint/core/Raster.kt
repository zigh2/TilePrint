package app.tileprint.core

/** Greyscale poster-space raster (white paper, 0..255, one byte per pixel) at [res] points per pixel. */
class PosterRaster(val gray: ByteArray, val w: Int, val h: Int, val res: Double)

/** Smart-cut ink profiles and blank-tile detection. Port of the raster helpers in source.py. */
object Raster {
    const val INK_LEVEL = 240

    private fun ink(b: Byte) = (b.toInt() and 0xFF) < INK_LEVEL

    /** (per-column ink, per-row ink), each 0..1. */
    fun inkProfiles(r: PosterRaster): Pair<DoubleArray, DoubleArray> {
        val cols = IntArray(r.w)
        val rows = IntArray(r.h)
        for (y in 0 until r.h) {
            val base = y * r.w
            for (x in 0 until r.w) if (ink(r.gray[base + x])) {
                cols[x]++
                rows[y]++
            }
        }
        // PIL quantises the box-filtered mean to 8 bits; do the same so both engines pick identical cuts.
        fun q(count: Int, total: Int) = Math.floor(count.toDouble() / total * 255.0 + 0.5) / 255.0
        return DoubleArray(r.w) { q(cols[it], r.h) } to DoubleArray(r.h) { q(rows[it], r.w) }
    }

    /** (row, col) of tiles whose frame area holds no ink at all. */
    fun blankTiles(r: PosterRaster, layout: TileLayout): Set<Pair<Int, Int>> {
        val blank = HashSet<Pair<Int, Int>>()
        for (t in layout.tiles()) {
            val x0 = maxOf(0, (t.x / r.res).toInt())
            val y0 = maxOf(0, (t.y / r.res).toInt())
            val x1 = minOf(r.w, ((t.x + t.w) / r.res).toInt() + 1)
            val y1 = minOf(r.h, ((t.y + t.h) / r.res).toInt() + 1)
            var any = false
            if (x1 > x0 && y1 > y0) {
                loop@ for (y in y0 until y1) {
                    val base = y * r.w
                    for (x in x0 until x1) if (ink(r.gray[base + x])) { any = true; break@loop }
                }
            }
            if (!any) blank.add(t.key)
        }
        return blank
    }

    /** ITU-R 601 luma like PIL's convert("L"): packed ARGB ints -> bytes. */
    fun grayFromArgb(pixels: IntArray): ByteArray = ByteArray(pixels.size) {
        val p = pixels[it]
        val r = (p shr 16) and 0xFF
        val g = (p shr 8) and 0xFF
        val b = p and 0xFF
        ((r * 299 + g * 587 + b * 114) / 1000).toByte()
    }
}
