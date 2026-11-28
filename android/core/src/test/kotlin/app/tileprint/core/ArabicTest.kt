package app.tileprint.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** The Kotlin shaper + bidi must produce what the desktop app (python-arabic-reshaper + python-bidi) produces. */
class ArabicTest {
    private fun unescape(s: String) = Regex("\\\\u([0-9a-fA-F]{4})").replace(s) { it.groupValues[1].toInt(16).toChar().toString() }

    private val samples: List<Pair<String, String>> by lazy {
        javaClass.getResourceAsStream("/arabic.txt")!!.bufferedReader(Charsets.UTF_8).readLines()
            .filter { it.isNotEmpty() }.map { it.split("|") }.map { unescape(it[0]) to unescape(it.getOrElse(1) { "" }) }
    }

    @Test fun visualMatchesDesktopOnEverySample() {
        assertTrue(samples.size >= 40)
        val bad = samples.filter { (input, expected) -> ArabicText.visual(input) != expected }
        assertTrue("mismatches (${bad.size}): " + bad.joinToString { (i, e) ->
            "'${i.map { "\\u%04x".format(it.code) }.joinToString("")}' expected ${e.map { "%04x".format(it.code) }} got ${ArabicText.visual(i).map { "%04x".format(it.code) }}"
        }.take(1500), bad.isEmpty())
    }

    @Test fun latinOnlyTextIsUntouched() {
        assertEquals("page 5 of 24", ArabicText.visual("page 5 of 24"))
        assertEquals("", ArabicText.visual(""))
    }

    @Test fun lamAlefLigatureAndJoining() {
        assertEquals("\ufefb", ArabicText.reshape("\u0644\u0627"))                  // لا -> isolated lam-alef ligature
        assertEquals("\ufea3\ufee0\ufef2", ArabicText.reshape("\u062d\u0644\u064a"))      // initial + medial + final forms
        assertEquals("\u0645\u0631", ArabicText.reshape("\u0645\u064e\u0631").replace("\ufee3", "\u0645").replace("\ufeae", "\u0631"))  // harakat dropped
    }
}
