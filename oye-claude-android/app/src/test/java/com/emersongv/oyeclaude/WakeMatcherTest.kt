package com.emersongv.oyeclaude

import org.json.JSONArray
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WakeMatcherTest {
    private val t = WakeMatcher.DEFAULT_TRIGGERS
    private val v = WakeMatcher.DEFAULT_VARIANTS

    @Test
    fun detectaLaFrase() {
        assertTrue(WakeMatcher.matches("oye claude", t, v))
        assertTrue(WakeMatcher.matches("oye cloud", t, v))
        assertTrue(WakeMatcher.matches("hola oye claudio que tal", t, v))
    }

    @Test
    fun ignoraOtrasFrases() {
        assertFalse(WakeMatcher.matches("oye", t, v))
        assertFalse(WakeMatcher.matches("claude", t, v))
        assertFalse(WakeMatcher.matches("oye claro", t, v))
        assertFalse(WakeMatcher.matches("claude oye", t, v))
        assertFalse(WakeMatcher.matches("", t, v))
    }

    @Test
    fun gramaticaIncluyeFrasesSenuelosYUnk() {
        val g = JSONArray(WakeMatcher.grammar(t, v))
        val items = (0 until g.length()).map { g.getString(it) }
        assertTrue("oye claude" in items)
        assertTrue("oye cloud" in items)
        assertTrue("claro" in items)
        assertEquals("[unk]", items.last())
        assertEquals(items.size, items.toSet().size)
    }

    @Test
    fun ajustesSeNormalizan() {
        assertEquals(listOf("oye", "hey"), Prefs.splitWords(" Oye, HEY ,, oye "))
    }
}
