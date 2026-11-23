package app.tileprint.engine

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.graphics.pdf.PdfRenderer
import android.os.ParcelFileDescriptor
import app.tileprint.core.Job
import app.tileprint.core.Placement
import app.tileprint.core.sourceTransform
import app.tileprint.data.SourceDoc
import com.tom_roush.pdfbox.io.MemoryUsageSetting
import com.tom_roush.pdfbox.multipdf.LayerUtility
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle
import com.tom_roush.pdfbox.pdmodel.graphics.form.PDFormXObject
import com.tom_roush.pdfbox.util.Matrix as PdfMatrix
import java.io.File
import java.io.OutputStream
import kotlin.math.max
import kotlin.math.min

/**
 * Writes the tiled PDF and the full-size PDF with PDFBox.
 *
 * The source page is imported ONCE as a Form XObject and every sheet only references it with its own
 * transform + clip. Nothing is rasterised: vector artwork and text stay vector, and the file stays
 * about the size of the source (same technique as the desktop exporter).
 */
object PdfExporter {
    const val MAX_PAGE_PT = 14400.0

    /** (originX, originY, width, height) of the form's BBox after its /Matrix. */
    private fun formGeometry(form: PDFormXObject): DoubleArray {
        val bb = form.bBox
        val m = form.matrix
        val a = m.getValue(0, 0).toDouble(); val b = m.getValue(0, 1).toDouble()
        val c = m.getValue(1, 0).toDouble(); val d = m.getValue(1, 1).toDouble()
        val e = m.getValue(2, 0).toDouble(); val f = m.getValue(2, 1).toDouble()
        val xs = ArrayList<Double>(); val ys = ArrayList<Double>()
        for (x in doubleArrayOf(bb.lowerLeftX.toDouble(), bb.upperRightX.toDouble()))
            for (y in doubleArrayOf(bb.lowerLeftY.toDouble(), bb.upperRightY.toDouble())) {
                xs.add(a * x + c * y + e); ys.add(b * x + d * y + f)
            }
        return doubleArrayOf(xs.min(), ys.min(), xs.max() - xs.min(), ys.max() - ys.min())
    }

    /** The source page imported as an *unrotated* form, plus its geometry and original /Rotate. */
    private class Imported(val form: PDFormXObject, val geom: DoubleArray, val rotation: Int)

    private fun importSource(dest: PDDocument, src: PDDocument, pageIndex: Int): Imported {
        val page = src.getPage(pageIndex)
        val rotation = ((page.rotation % 360) + 360) % 360
        page.rotation = 0            // PDFBox's rotation handling distorts 90/270 pages: we rotate ourselves
        val form = LayerUtility(dest).importPageAsForm(src, pageIndex)
        return Imported(form, formGeometry(form), rotation)
    }

    /** Place the source so poster point (tx, ty) lands at the frame's top-left; clip to frame ∩ poster. */
    private fun drawSource(cs: PDPageContentStream, im: Imported, pl: Placement,
                           posterW: Double, posterH: Double, frame: DoubleArray, tx: Double, ty: Double) {
        val t = sourceTransform(im.rotation, im.geom[0], im.geom[1], im.geom[2], im.geom[3], pl, posterW, posterH, frame, tx, ty)
        cs.saveGraphicsState()
        cs.addRect(t.clipX.toFloat(), t.clipY.toFloat(), t.clipW.toFloat(), t.clipH.toFloat())
        cs.clip()
        cs.transform(PdfMatrix(t.a.toFloat(), t.b.toFloat(), t.c.toFloat(), t.d.toFloat(), t.e.toFloat(), t.f.toFloat()))
        cs.drawForm(im.form)
        cs.restoreGraphicsState()
    }

    /** Returns the number of sheets written. [only] restricts output to those page numbers (sheet preview). */
    fun exportTiled(context: Context, source: SourceDoc, pageIndex: Int, job: Job, opt: OverlayOptions,
                    out: OutputStream, blankBacks: Boolean = false, only: Set<Int>? = null,
                    progress: (Int, Int) -> Unit = { _, _ -> }): Int {
        val plan = job.layout.plan(job.skip, opt.numbering)
        require(plan.isNotEmpty()) { "nothing to print" }
        val src = PDDocument.load(source.file, MemoryUsageSetting.setupTempFileOnly())
        val dest = PDDocument(MemoryUsageSetting.setupTempFileOnly())
        try {
            val im = importSource(dest, src, pageIndex)
            val fonts = PdfFonts.load(context, dest)
            val size = PDRectangle(job.paperW.toFloat(), job.paperH.toFloat())
            var written = 0
            plan.forEachIndexed { i, pp ->
                if (only != null && pp.number !in only) return@forEachIndexed
                val page = PDPage(size)
                dest.addPage(page)
                PDPageContentStream(dest, page, PDPageContentStream.AppendMode.APPEND, true, true).use { cs ->
                    drawSource(cs, im, job.placement, job.posterW, job.posterH, job.layout.frame, pp.tile.x, pp.tile.y)
                    Overlay.draw(cs, fonts, job.layout, pp, opt)
                }
                if (blankBacks) dest.addPage(PDPage(size))
                written++
                progress(i + 1, plan.size)
            }
            dest.documentInformation.title = opt.footerName.ifEmpty { "TilePrint tiles" }
            dest.documentInformation.creator = "TilePrint"
            dest.save(out)
            return written
        } finally {
            runCatching { dest.close() }
            runCatching { src.close() }
        }
    }

    /** One page at the full poster size (plotters / print shops). */
    fun exportFull(source: SourceDoc, pageIndex: Int, job: Job, out: OutputStream) {
        require(max(job.posterW, job.posterH) <= MAX_PAGE_PT) { "poster larger than 200 in" }
        val src = PDDocument.load(source.file, MemoryUsageSetting.setupTempFileOnly())
        val dest = PDDocument(MemoryUsageSetting.setupTempFileOnly())
        try {
            val im = importSource(dest, src, pageIndex)
            val page = PDPage(PDRectangle(job.posterW.toFloat(), job.posterH.toFloat()))
            dest.addPage(page)
            PDPageContentStream(dest, page, PDPageContentStream.AppendMode.APPEND, true, true).use { cs ->
                drawSource(cs, im, job.placement, job.posterW, job.posterH,
                    doubleArrayOf(0.0, 0.0, job.posterW, job.posterH), 0.0, 0.0)
            }
            dest.documentInformation.title = source.name.substringBeforeLast('.')
            dest.documentInformation.creator = "TilePrint"
            dest.save(out)
        } finally {
            runCatching { dest.close() }
            runCatching { src.close() }
        }
    }

    /** The exact printed sheet [number] as a bitmap (written to a temp PDF and rendered). */
    fun sheetPreview(context: Context, source: SourceDoc, pageIndex: Int, job: Job, opt: OverlayOptions, number: Int): Bitmap {
        val tmp = File(context.cacheDir, "sheet_preview.pdf")
        tmp.outputStream().use { exportTiled(context, source, pageIndex, job, opt, it, false, setOf(number)) }
        val pfd = ParcelFileDescriptor.open(tmp, ParcelFileDescriptor.MODE_READ_ONLY)
        try {
            PdfRenderer(pfd).use { r ->
                r.openPage(0).use { p ->
                    val scale = 1.8f
                    val bmp = Bitmap.createBitmap((job.paperW * scale).toInt(), (job.paperH * scale).toInt(), Bitmap.Config.ARGB_8888)
                    bmp.eraseColor(android.graphics.Color.WHITE)
                    p.render(bmp, null, Matrix().apply { setScale(scale, scale) }, PdfRenderer.Page.RENDER_MODE_FOR_DISPLAY)
                    return bmp
                }
            }
        } finally {
            runCatching { pfd.close() }
            tmp.delete()
        }
    }
}
