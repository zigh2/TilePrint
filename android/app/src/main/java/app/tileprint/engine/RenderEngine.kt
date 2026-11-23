package app.tileprint.engine

import android.graphics.Bitmap
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import app.tileprint.core.Placement
import app.tileprint.core.PosterRaster
import app.tileprint.core.Raster
import app.tileprint.core.SourceInfo
import java.io.File
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/** A crisp re-render of part of the poster (poster-space rectangle in points). */
class Region(val bitmap: Bitmap, val x: Double, val y: Double, val w: Double, val h: Double)

/** Renders pages of one PDF file with the platform renderer (vector-sharp at any zoom). */
class RenderEngine(file: File) : AutoCloseable {
    private val pfd = ParcelFileDescriptor.open(file, ParcelFileDescriptor.MODE_READ_ONLY)
    private val renderer = PdfRenderer(pfd)

    /** PdfRenderer allows one open page at a time. Matrix maps page points (top-left origin) to bitmap pixels. */
    @Synchronized
    fun render(page: Int, bitmap: Bitmap, matrix: Matrix) {
        bitmap.eraseColor(Color.WHITE)
        renderer.openPage(page).use { it.render(bitmap, null, matrix, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY) }
    }

    /** The whole source page, longest side [maxPx] (the base layer of the preview). */
    fun overview(info: SourceInfo, page: Int, maxPx: Int = 1600): Bitmap {
        val scale = maxPx / max(info.widthPt, info.heightPt)
        val bw = max(1, (info.widthPt * scale).roundToInt())
        val bh = max(1, (info.heightPt * scale).roundToInt())
        val bmp = Bitmap.createBitmap(bw, bh, Bitmap.Config.ARGB_8888)
        val m = Matrix().apply { setScale(bw / info.widthPt.toFloat(), bh / info.heightPt.toFloat()) }
        render(page, bmp, m)
        return bmp
    }

    /** Re-render the visible part of the poster at screen resolution. Null if it misses the content. */
    fun region(page: Int, pl: Placement, rx: Double, ry: Double, rw: Double, rh: Double, outPx: Int): Region? {
        val x0 = max(rx, pl.x)
        val y0 = max(ry, pl.y)
        val x1 = min(rx + rw, pl.x + pl.width)
        val y1 = min(ry + rh, pl.y + pl.height)
        if (x1 - x0 < 1e-3 || y1 - y0 < 1e-3) return null
        // poster rect -> source-page rect (distances from the page's top-left, in points)
        val u0 = (x0 - pl.x) / pl.sx
        val u1 = (x1 - pl.x) / pl.sx
        val v0 = (y0 - pl.y) / pl.sy
        val v1 = (y1 - pl.y) / pl.sy
        var scale = min(max(outPx, 8).toDouble(), MAX_SIDE) / (u1 - u0)
        scale = min(scale, MAX_SIDE / (v1 - v0))
        val bw = max(1, ((u1 - u0) * scale).roundToInt())
        val bh = max(1, ((v1 - v0) * scale).roundToInt())
        val bmp = Bitmap.createBitmap(bw, bh, Bitmap.Config.ARGB_8888)
        val m = Matrix().apply {
            postTranslate(-u0.toFloat(), -v0.toFloat())
            postScale((bw / (u1 - u0)).toFloat(), (bh / (v1 - v0)).toFloat())
        }
        render(page, bmp, m)
        return Region(bmp, x0, y0, x1 - x0, y1 - y0)
    }

    /** Poster-space greyscale raster (white paper) for smart cuts and blank-sheet detection. */
    fun posterRaster(page: Int, pl: Placement, posterW: Double, posterH: Double): PosterRaster {
        val res = max(posterW, posterH) / RASTER_SAMPLES
        val w = max(1, (posterW / res).roundToInt())
        val h = max(1, (posterH / res).roundToInt())
        val bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
        val m = Matrix().apply {
            postScale((pl.sx / res).toFloat(), (pl.sy / res).toFloat())
            postTranslate((pl.x / res).toFloat(), (pl.y / res).toFloat())
        }
        render(page, bmp, m)
        val px = IntArray(w * h)
        bmp.getPixels(px, 0, w, 0, 0, w, h)
        bmp.recycle()
        return PosterRaster(Raster.grayFromArgb(px), w, h, res)
    }

    override fun close() {
        runCatching { renderer.close() }
        runCatching { pfd.close() }
    }

    companion object {
        const val RASTER_SAMPLES = 2000.0
        private const val MAX_SIDE = 2800.0
    }
}
