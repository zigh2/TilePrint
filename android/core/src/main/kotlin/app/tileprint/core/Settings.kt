package app.tileprint.core

import kotlin.math.max
import kotlin.math.min

/** Everything the user can change. Lengths are points. Port of project.py's Settings. */
data class Settings(
    val unit: Paper.Unit = Paper.Unit.MM,
    val posterPreset: String = "A0",                 // preset name or "Custom"
    val posterOrient: Orient = Orient.AUTO,
    val posterW: Double = 841 * Paper.PT_PER_MM,     // custom size
    val posterH: Double = 1189 * Paper.PT_PER_MM,
    val lockAspect: Boolean = true,
    val scaleMode: ScaleMode = ScaleMode.FIT,
    val offsetX: Double = 0.0,
    val offsetY: Double = 0.0,
    val paper: String = "A4",
    val paperOrient: Orient = Orient.AUTO,
    val margin: Double = 10 * Paper.PT_PER_MM,
    val header: Double = 9 * Paper.PT_PER_MM,
    val overlap: Double = 10 * Paper.PT_PER_MM,
    val numbering: String = "seq",                   // seq | rc
    val cropMarks: Boolean = true,
    val overlapTicks: Boolean = true,
    val footer: Boolean = true,
    val scaleBar: Boolean = true,
    val smartCut: Boolean = false,
    val skipBlank: Boolean = true,
    val blankBacks: Boolean = false,
    val footerText: String = "",
    val pageIndex: Int = 0,
) {
    enum class Orient { AUTO, PORTRAIT, LANDSCAPE }
}

/** What the engine needs to know about the opened source page. */
data class SourceInfo(val name: String, val widthPt: Double, val heightPt: Double,
                      val pageCount: Int, val pixelW: Int? = null, val pixelH: Int? = null)

data class Job(
    val posterW: Double, val posterH: Double, val paperW: Double, val paperH: Double,
    val placement: Placement, val layout: TileLayout, val skip: Set<Pair<Int, Int>>,
    val dpi: Double?, val scale: Double,
) {
    val sheets: Int get() = layout.rows * layout.cols
    val printed: Int get() = sheets - skip.size
}

fun posterDimensions(s: Settings, src: SourceInfo): Pair<Double, Double> {
    if (s.posterPreset == "Custom") return s.posterW to s.posterH
    val (w, h) = Paper.size(s.posterPreset)
    val landscape = s.posterOrient == Settings.Orient.LANDSCAPE ||
        (s.posterOrient == Settings.Orient.AUTO && src.widthPt > src.heightPt)
    return if (landscape) max(w, h) to min(w, h) else min(w, h) to max(w, h)
}

fun paperDimensions(s: Settings, posterW: Double, posterH: Double): Pair<Double, Double> {
    val (w, h) = Paper.size(s.paper)
    return when (s.paperOrient) {
        Settings.Orient.LANDSCAPE -> max(w, h) to min(w, h)
        Settings.Orient.PORTRAIT -> min(w, h) to max(w, h)
        Settings.Orient.AUTO ->
            if (bestOrientation(posterW, posterH, w, h, s.margin, s.header, s.overlap)) max(w, h) to min(w, h)
            else min(w, h) to max(w, h)
    }
}

/**
 * Turns (source, settings) into a ready-to-export job. [raster] is asked for a poster-space
 * greyscale raster only when smart cut or blank-sheet skipping needs one.
 */
fun buildJob(src: SourceInfo, s: Settings, raster: (Placement, Double, Double) -> PosterRaster?): Job {
    val (pw, ph) = posterDimensions(s, src)
    val (paperW, paperH) = paperDimensions(s, pw, ph)
    val pl = placeContent(src.widthPt, src.heightPt, pw, ph, s.scaleMode, s.offsetX, s.offsetY)

    val r = if (s.smartCut || s.skipBlank) raster(pl, pw, ph) else null
    var inkX: DoubleArray? = null
    var inkY: DoubleArray? = null
    if (s.smartCut && r != null) Raster.inkProfiles(r).let { inkX = it.first; inkY = it.second }
    val slack = if (s.smartCut) min(s.overlap * 1.5, 15 * Paper.PT_PER_MM) else 0.0
    val lay = buildLayout(pw, ph, paperW, paperH, s.margin, s.header, s.overlap, inkX, inkY, r?.res ?: 1.0, slack)
    var skip: Set<Pair<Int, Int>> = if (s.skipBlank && r != null) Raster.blankTiles(r, lay) else emptySet()
    if (skip.size >= lay.rows * lay.cols) skip = emptySet()      // never produce an empty document
    val dpi = src.pixelW?.let { effectiveDpi(it.toDouble(), pl.width) }
    return Job(pw, ph, paperW, paperH, pl, lay, skip, dpi, pl.sx)
}
