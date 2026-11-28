package app.tileprint.core

/**
 * Arabic text for PDF output without any platform dependency (Android's ICU lacks ArabicShaping).
 *
 * [reshape] is a line-by-line port of python-arabic-reshaper (default configuration: harakat removed,
 * lam-alef and Allah ligatures) and [bidi] is a compact Unicode Bidirectional Algorithm (rules W1-W7,
 * N1-N2, I1-I2, L1, L2 and mirroring, no explicit embeddings). [visual] = reshape then bidi: the string
 * to draw left-to-right. Parity tests compare it with python-bidi on real samples.
 */
object ArabicText {
    private const val UNSHAPED = 255
    private const val ISOLATED = 0
    private const val INITIAL = 1
    private const val MEDIAL = 2
    private const val FINAL = 3
    private const val NOT_SUPPORTED = -1
    private const val ZWJ = "\u200d"

    fun isArabic(c: Char): Boolean {
        val o = c.code
        return o in 0x0600..0x06FF || o in 0x0750..0x077F || o in 0x08A0..0x08FF || o in 0xFB50..0xFDFF || o in 0xFE70..0xFEFF
    }

    fun hasArabic(s: String) = s.any { isArabic(it) }

    private fun isHarakat(c: Char) =
        c in '\u0610'..'\u061a' || c in '\u064b'..'\u065f' || c == '\u0670' || c in '\u06d6'..'\u06dc' ||
            c in '\u06df'..'\u06e8' || c in '\u06ea'..'\u06ed' || c in '\u08d4'..'\u08ff'

    private val ligatureRegex: Regex by lazy { Regex(ArabicTables.ligatures.joinToString("|") { "(${it.first})" }) }

    // ------------------------------------------------------------------------------------ shaping
    fun reshape(text: String): String {
        if (text.isEmpty()) return ""
        val letters = ArabicTables.letters
        val outL = ArrayList<String>()
        val outF = ArrayList<Int>()
        fun connectsBefore(l: String) = letters[l]?.let { it[FINAL].isNotEmpty() || it[MEDIAL].isNotEmpty() } ?: false
        fun connectsAfter(l: String) = letters[l]?.let { it[INITIAL].isNotEmpty() || it[MEDIAL].isNotEmpty() } ?: false
        fun connectsBoth(l: String) = letters[l]?.let { it[MEDIAL].isNotEmpty() } ?: false
        fun add(l: String, f: Int) { outL.add(l); outF.add(f) }

        for (ch in text) {
            val letter = ch.toString()
            when {
                isHarakat(ch) -> {}                                           // delete_harakat = True
                letter !in letters -> add(letter, NOT_SUPPORTED)
                outL.isEmpty() -> add(letter, ISOLATED)
                else -> {
                    val pl = outL.last()
                    val pf = outF.last()
                    when {
                        pf == NOT_SUPPORTED -> add(letter, ISOLATED)
                        !connectsBefore(letter) -> add(letter, ISOLATED)
                        !connectsAfter(pl) -> add(letter, ISOLATED)
                        pf == FINAL && !connectsBoth(pl) -> add(letter, ISOLATED)
                        pf == ISOLATED -> { outF[outF.size - 1] = INITIAL; add(letter, FINAL) }
                        else -> { outF[outF.size - 1] = MEDIAL; add(letter, FINAL) }
                    }
                }
            }
            if (outL.size > 1 && outL[outL.size - 2] == ZWJ) {                // ZWJ second to last is useless
                outL.removeAt(outL.size - 2); outF.removeAt(outF.size - 2)
            }
        }
        if (outL.isNotEmpty() && outL.last() == ZWJ) { outL.removeAt(outL.size - 1); outF.removeAt(outF.size - 1) }

        // ligatures (lam-alef family, Allah)
        val cleaned = text.filterNot(::isHarakat)
        for (m in ligatureRegex.findAll(cleaned)) {
            val gi = (1 until m.groups.size).first { m.groups[it] != null } - 1
            val forms = ArabicTables.ligatures[gi].second
            val a = m.range.first
            val b = m.range.last + 1
            if (b > outL.size) continue
            val aForm = outF[a]
            val bForm = outF[b - 1]
            val lf = if (aForm == ISOLATED || aForm == INITIAL) {
                if (bForm == ISOLATED || bForm == FINAL) ISOLATED else INITIAL
            } else {
                if (bForm == ISOLATED || bForm == FINAL) FINAL else MEDIAL
            }
            if (forms[lf].isEmpty()) continue
            outL[a] = forms[lf]; outF[a] = NOT_SUPPORTED
            for (k in a + 1 until b) { outL[k] = ""; outF[k] = NOT_SUPPORTED }
        }

        val sb = StringBuilder()
        for (i in outL.indices) {
            val l = outL[i]
            if (l.isEmpty()) continue
            val f = outF[i]
            sb.append(if (f == NOT_SUPPORTED || f == UNSHAPED) l else letters.getValue(l)[f])
        }
        return sb.toString()
    }

    // ------------------------------------------------------------------------------------ bidi
    private enum class C { L, R, AL, EN, ES, ET, AN, CS, NSM, ON, WS }

    private fun classOf(c: Char): C {
        val o = c.code
        return when {
            c in '0'..'9' || c in '\u06f0'..'\u06f9' -> C.EN
            c in '\u0660'..'\u0669' -> C.AN
            c == '+' || c == '-' -> C.ES
            c == '#' || c == '$' || c == '%' || c == '\u00b0' || c in '\u00a2'..'\u00a5' || c == '\u066a' -> C.ET
            c == ',' || c == '.' || c == '/' || c == ':' || c == '\u060c' || c == '\u00a0' -> C.CS
            Character.getType(c) == Character.NON_SPACING_MARK.toInt() -> C.NSM
            isArabic(c) && (c.isLetter() || c == '\u061b' || c == '\u061f') -> C.AL
            o in 0x0590..0x05FF || o in 0x07C0..0x085F || o in 0xFB1D..0xFB4F -> if (c.isLetter()) C.R else C.ON
            c.isLetter() -> C.L
            c.isWhitespace() -> C.WS
            else -> C.ON
        }
    }

    private val mirror = mapOf('(' to ')', ')' to '(', '[' to ']', ']' to '[', '{' to '}', '}' to '{', '<' to '>', '>' to '<',
        '\u00ab' to '\u00bb', '\u00bb' to '\u00ab', '\u2039' to '\u203a', '\u203a' to '\u2039')

    /** Reorder [text] (logical order) into visual order for left-to-right drawing. */
    fun bidi(text: String): String {
        val n = text.length
        if (n == 0) return text
        val orig = Array(n) { classOf(text[it]) }
        // paragraph level from the first strong character
        val firstStrong = orig.firstOrNull { it == C.L || it == C.R || it == C.AL }
        val para = if (firstStrong == C.R || firstStrong == C.AL) 1 else 0
        val sos = if (para == 1) C.R else C.L
        val t = orig.copyOf()

        // W1: NSM takes the previous class
        for (i in 0 until n) if (t[i] == C.NSM) t[i] = if (i == 0) sos else t[i - 1]
        // W2: EN after AL becomes AN
        var lastStrong = sos
        for (i in 0 until n) {
            when (t[i]) { C.L, C.R, C.AL -> lastStrong = t[i]; C.EN -> if (lastStrong == C.AL) t[i] = C.AN; else -> {} }
        }
        // W3: AL -> R
        for (i in 0 until n) if (t[i] == C.AL) t[i] = C.R
        // W4: single separators between numbers
        for (i in 1 until n - 1) {
            if (t[i] == C.ES && t[i - 1] == C.EN && t[i + 1] == C.EN) t[i] = C.EN
            else if (t[i] == C.CS && t[i - 1] == C.EN && t[i + 1] == C.EN) t[i] = C.EN
            else if (t[i] == C.CS && t[i - 1] == C.AN && t[i + 1] == C.AN) t[i] = C.AN
        }
        // W5: ET sequences adjacent to EN become EN
        var i = 0
        while (i < n) {
            if (t[i] == C.ET) {
                var j = i
                while (j < n && t[j] == C.ET) j++
                if ((i > 0 && t[i - 1] == C.EN) || (j < n && t[j] == C.EN)) for (k in i until j) t[k] = C.EN
                i = j
            } else i++
        }
        // W6: leftover separators and terminators become neutral
        for (k in 0 until n) if (t[k] == C.ES || t[k] == C.ET || t[k] == C.CS) t[k] = C.ON
        // W7: EN after strong L becomes L
        lastStrong = sos
        for (k in 0 until n) {
            when (t[k]) { C.L, C.R -> lastStrong = t[k]; C.EN -> if (lastStrong == C.L) t[k] = C.L; else -> {} }
        }
        // N1 / N2: neutral runs take the surrounding direction if both sides agree, else the embedding direction
        fun dirOf(c: C?): C? = when (c) { C.L -> C.L; C.R, C.EN, C.AN -> C.R; else -> null }
        val embed = if (para == 1) C.R else C.L
        i = 0
        while (i < n) {
            if (t[i] == C.ON || t[i] == C.WS) {
                var j = i
                while (j < n && (t[j] == C.ON || t[j] == C.WS)) j++
                val before = if (i == 0) dirOf(sos) else dirOf(t[i - 1])
                val after = if (j == n) dirOf(sos) else dirOf(t[j])
                val d = if (before != null && before == after) before else embed
                for (k in i until j) t[k] = d
                i = j
            } else i++
        }
        // I1 / I2: implicit levels
        val level = IntArray(n) { k ->
            when (t[k]) {
                C.R -> if (para % 2 == 0) para + 1 else para
                C.L -> if (para % 2 == 0) para else para + 1
                C.EN, C.AN -> if (para % 2 == 0) para + 2 else para + 1
                else -> para
            }
        }
        // L1: trailing whitespace goes back to the paragraph level
        var e = n - 1
        while (e >= 0 && orig[e] == C.WS) { level[e] = para; e-- }
        // L2: reverse runs from the highest level down to the lowest odd level
        val idx = IntArray(n) { it }
        val maxLevel = level.max()
        val minOdd = level.filter { it % 2 == 1 }.minOrNull() ?: (maxLevel + 1)
        var lv = maxLevel
        while (lv >= minOdd) {
            var s = 0
            while (s < n) {
                if (level[idx[s]] >= lv) {
                    var f = s
                    while (f < n && level[idx[f]] >= lv) f++
                    idx.reverse(s, f)
                    s = f
                } else s++
            }
            lv--
        }
        val sb = StringBuilder(n)
        for (p in 0 until n) {
            val c = text[idx[p]]
            sb.append(if (level[idx[p]] % 2 == 1) mirror[c] ?: c else c)
        }
        return sb.toString()
    }

    /** Text ready to be drawn left-to-right (the same as python's get_display(reshape(text))). */
    fun visual(text: String): String = if (hasArabic(text)) bidi(reshape(text)) else text
}
