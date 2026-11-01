package com.emersongv.oyeclaude

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class VoiceButtonFinderTest {
    @Test
    fun prefiereModoDeVoz() {
        val voiceMode = VoiceButtonFinder.score("Iniciar modo de voz")
        val dictation = VoiceButtonFinder.score("Dictar con el micrófono")
        assertTrue(voiceMode > dictation)
        assertTrue(dictation > 0)
    }

    @Test
    fun funcionaEnInglesYConIds() {
        assertEquals(100, VoiceButtonFinder.score("Voice mode"))
        assertEquals(100, VoiceButtonFinder.score("#voice_mode_button"))
        assertTrue(VoiceButtonFinder.score("Voice") > 0)
    }

    @Test
    fun penalizaAjustesYTextoAjeno() {
        assertTrue(VoiceButtonFinder.score("Ajustes de voz") <= 0)
        assertEquals(0, VoiceButtonFinder.score("Enviar mensaje"))
        assertEquals(0, VoiceButtonFinder.score("Vozdeprueba"))
    }

    @Test
    fun normalizaAcentos() {
        assertEquals("microfono", VoiceButtonFinder.normalize("Micrófono"))
    }
}
