package app.tileprint.data

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.net.Uri
import android.provider.OpenableColumns
import androidx.annotation.StringRes
import androidx.exifinterface.media.ExifInterface
import app.tileprint.R
import app.tileprint.core.SourceInfo
import com.tom_roush.pdfbox.io.MemoryUsageSetting
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPage
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.common.PDRectangle
import com.tom_roush.pdfbox.pdmodel.encryption.InvalidPasswordException
import com.tom_roush.pdfbox.pdmodel.graphics.image.JPEGFactory
import com.tom_roush.pdfbox.pdmodel.graphics.image.LosslessFactory
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream

/** The opened source, normalised to a PDF file on disk (images are wrapped in a one-page PDF). */
class SourceDoc(
    val file: File,
    val name: String,
    val kind: Kind,
    val sizes: List<Pair<Double, Double>>,
    val pixelW: Int?,
    val pixelH: Int?,
) {
    enum class Kind { PDF, IMAGE }

    val pageCount: Int get() = sizes.size
    fun info(page: Int) = SourceInfo(name, sizes[page].first, sizes[page].second, pageCount, pixelW, pixelH)
}

class SourceException(@StringRes val resId: Int, message: String) : Exception(message)

object SourceLoader {
    private const val DEFAULT_IMAGE_DPI = 96.0

    /** Blocking: call from a background dispatcher. */
    fun load(context: Context, uri: Uri): SourceDoc {
        val dir = File(context.cacheDir, "source").apply { mkdirs() }
        dir.listFiles()?.forEach { it.deleteRecursively() }
        val name = displayName(context, uri)
        val raw = File(dir, "original.bin")
        val input = context.contentResolver.openInputStream(uri)
            ?: throw SourceException(R.string.unsupported_file, "cannot open $uri")
        input.use { src -> FileOutputStream(raw).use { src.copyTo(it) } }

        val head = ByteArray(5)
        FileInputStream(raw).use { it.read(head) }
        val isPdf = String(head, Charsets.ISO_8859_1) == "%PDF-"
        return if (isPdf) loadPdf(raw, name) else loadImage(dir, raw, name)
    }

    private fun displayName(context: Context, uri: Uri): String {
        runCatching {
            context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) c.getString(0)?.let { return it }
            }
        }
        return uri.lastPathSegment?.substringAfterLast('/') ?: "document"
    }

    private fun loadPdf(file: File, name: String): SourceDoc {
        val doc = try {
            PDDocument.load(file, MemoryUsageSetting.setupTempFileOnly())
        } catch (e: InvalidPasswordException) {
            throw SourceException(R.string.password_pdf, "password protected")
        }
        try {
            val sizes = (0 until doc.numberOfPages).map { i ->
                val page = doc.getPage(i)
                val box = page.cropBox
                var w = box.width.toDouble()
                var h = box.height.toDouble()
                if (((page.rotation % 360) + 360) % 360 % 180 != 0) w = h.also { h = w }
                w to h
            }
            if (sizes.isEmpty()) throw SourceException(R.string.unsupported_file, "no pages")
            return SourceDoc(file, name, SourceDoc.Kind.PDF, sizes, null, null)
        } finally {
            doc.close()
        }
    }

    private fun loadImage(dir: File, raw: File, name: String): SourceDoc {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(raw.path, bounds)
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0) throw SourceException(R.string.unsupported_file, "not an image")

        val orientation = runCatching {
            FileInputStream(raw).use { ExifInterface(it).getAttributeInt(ExifInterface.TAG_ORIENTATION, ExifInterface.ORIENTATION_NORMAL) }
        }.getOrDefault(ExifInterface.ORIENTATION_NORMAL)
        val isJpeg = bounds.outMimeType == "image/jpeg"
        val needsTransform = orientation != ExifInterface.ORIENTATION_NORMAL && orientation != ExifInterface.ORIENTATION_UNDEFINED

        var pxW = bounds.outWidth
        var pxH = bounds.outHeight
        var bitmap: Bitmap? = null
        if (!isJpeg || needsTransform) {
            var bmp = BitmapFactory.decodeFile(raw.path) ?: throw SourceException(R.string.unsupported_file, "decode failed")
            if (needsTransform) {
                val m = Matrix()
                when (orientation) {
                    ExifInterface.ORIENTATION_ROTATE_90 -> m.postRotate(90f)
                    ExifInterface.ORIENTATION_ROTATE_180 -> m.postRotate(180f)
                    ExifInterface.ORIENTATION_ROTATE_270 -> m.postRotate(270f)
                    ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> m.postScale(-1f, 1f)
                    ExifInterface.ORIENTATION_FLIP_VERTICAL -> m.postScale(1f, -1f)
                    ExifInterface.ORIENTATION_TRANSPOSE -> { m.postRotate(90f); m.postScale(-1f, 1f) }
                    ExifInterface.ORIENTATION_TRANSVERSE -> { m.postRotate(270f); m.postScale(-1f, 1f) }
                }
                bmp = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
            }
            bitmap = bmp
            pxW = bmp.width
            pxH = bmp.height
        }

        val wPt = pxW * 72.0 / DEFAULT_IMAGE_DPI
        val hPt = pxH * 72.0 / DEFAULT_IMAGE_DPI
        val pdf = File(dir, "image.pdf")
        PDDocument().use { doc ->
            val page = PDPage(PDRectangle(wPt.toFloat(), hPt.toFloat()))
            doc.addPage(page)
            val image = if (bitmap == null) FileInputStream(raw).use { JPEGFactory.createFromStream(doc, it) }
            else LosslessFactory.createFromImage(doc, bitmap)
            PDPageContentStream(doc, page).use { it.drawImage(image, 0f, 0f, wPt.toFloat(), hPt.toFloat()) }
            doc.save(pdf)
        }
        bitmap?.recycle()
        return SourceDoc(pdf, name, SourceDoc.Kind.IMAGE, listOf(wPt to hPt), pxW, pxH)
    }
}
