package app.tileprint.engine

import android.content.Context
import android.icu.text.ArabicShaping
import android.icu.text.Bidi
import com.tom_roush.pdfbox.pdmodel.PDDocument
import com.tom_roush.pdfbox.pdmodel.PDPageContentStream
import com.tom_roush.pdfbox.pdmodel.font.PDType0Font

/** Bundled fonts (Noto Sans / Noto Sans Arabic, SIL OFL) embedded as subsets into the output PDF. */
class PdfFonts(val lat: PDType0Font, val latBold: PDType0Font, val ar: PDType0Font, val arBold: PDType0Font) {
    companion object {
        fun load(context: Context, doc: PDDocument): PdfFonts {
            fun font(name: String) = context.assets.open("fonts/$name").use { PDType0Font.load(doc, it) }
            return PdfFonts(font("NotoSans-Regular.ttf"), font("NotoSans-Bold.ttf"),
                font("NotoSansArabic-Regular.ttf"), font("NotoSansArabic-Bold.ttf"))
        }
    }
}

/** Mixed Arabic/Latin text for PDF: shape + reorder (ICU), then draw per-script runs. Port of textutil.py. */
object PdfText {
    private class Run(val text: String, val font: PDType0Font)

    private fun isArabic(ch: Char): Boolean {
        val o = ch.code
        return o in 0x0600..0x06FF || o in 0x0750..0x077F || o in 0x08A0..0x08FF ||
            o in 0xFB50..0xFDFF || o in 0xFE70..0xFEFF
    }

    fun hasArabic(s: String) = s.any { isArabic(it) }

    /** Shape letters into presentation forms and reorder to visual (left-to-right) order. */
    fun visual(text: String): String {
        if (!hasArabic(text)) return text
        return runCatching {
            val shaped = ArabicShaping(ArabicShaping.LETTERS_SHAPE).shape(text)
            Bidi(shaped, Bidi.DIRECTION_DEFAULT_LEFT_TO_RIGHT).writeReordered(Bidi.DO_MIRRORING)
        }.getOrDefault(text)
    }

    private fun runs(shown: String, bold: Boolean, f: PdfFonts): List<Run> {
        val ar = if (bold) f.arBold else f.ar
        val lat = if (bold) f.latBold else f.lat
        val arabicText = hasArabic(shown)
        val out = ArrayList<Run>()
        var current: PDType0Font? = null
        val sb = StringBuilder()
        for (ch in shown) {
            val face = when {
                isArabic(ch) -> ar
                ch.isLetter() -> lat
                else -> current ?: if (arabicText && !shown[0].isLetter()) ar else lat   // digits/space/punctuation keep the neighbour's face
            }
            if (current != null && face !== current && sb.isNotEmpty()) {
                out.add(Run(sb.toString(), current))
                sb.clear()
            }
            current = face
            sb.append(ch)
        }
        if (sb.isNotEmpty() && current != null) out.add(Run(sb.toString(), current))
        return out
    }

    /** Drop characters the font has no glyph for (PDFBox throws instead). */
    private fun safe(font: PDType0Font, s: String): String = try {
        font.getStringWidth(s)
        s
    } catch (e: Exception) {
        s.filter { ch -> runCatching { font.getStringWidth(ch.toString()) }.isSuccess }
    }

    private fun runWidth(r: Run, size: Float) = r.font.getStringWidth(safe(r.font, r.text)) / 1000f * size

    fun width(text: String, size: Float, bold: Boolean, f: PdfFonts): Float =
        runs(visual(text), bold, f).sumOf { runWidth(it, size).toDouble() }.toFloat()

    fun draw(cs: PDPageContentStream, f: PdfFonts, x0: Float, y: Float, text: String, size: Float,
             bold: Boolean = false, align: Align = Align.LEFT): Float {
        val rs = runs(visual(text), bold, f)
        val total = rs.sumOf { runWidth(it, size).toDouble() }.toFloat()
        var x = when (align) {
            Align.LEFT -> x0
            Align.CENTER -> x0 - total / 2
            Align.RIGHT -> x0 - total
        }
        cs.setNonStrokingColor(0f)
        for (r in rs) {
            val t = safe(r.font, r.text)
            if (t.isEmpty()) continue
            cs.beginText()
            cs.setFont(r.font, size)
            cs.newLineAtOffset(x, y)
            cs.showText(t)
            cs.endText()
            x += runWidth(r, size)
        }
        return total
    }

    /** Shorten with an ellipsis so the text fits [maxWidth]. */
    fun fit(text: String, size: Float, maxWidth: Float, f: PdfFonts, bold: Boolean = false): String {
        var t = text
        if (width(t, size, bold, f) <= maxWidth) return t
        while (t.length > 1 && width("$t…", size, bold, f) > maxWidth) t = t.dropLast(1)
        return "$t…"
    }

    enum class Align { LEFT, CENTER, RIGHT }
}
