package com.emersongv.oyeclaude

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.sin
import kotlin.random.Random

class SilenceGateTest {
    private val chunk = 1600 // 100 ms a 16 kHz
    private val rnd = Random(7)

    private fun noise(rms: Double) = ShortArray(chunk) { (rnd.nextDouble(-1.0, 1.0) * rms * 1.73).toInt().toShort() }
    private fun tone(amp: Double) = ShortArray(chunk) { (amp * sin(it * 0.2)).toInt().toShort() }

    @Test
    fun enSilencioNoPasaNadaAlReconocedor() {
        val gate = SilenceGate(chunk, 100)
        var fed = 0
        repeat(300) { gate.process(noise(20.0), chunk, { _, _ -> fed++ }, {}) }
        assertEquals(0, fed)
        assertFalse(gate.active)
    }

    @Test
    fun alHablarPasaElAudioPrevioYCierraLaFraseTrasElSilencio() {
        val gate = SilenceGate(chunk, 100)
        var fed = 0
        var closes = 0
        repeat(50) { gate.process(noise(20.0), chunk, { _, _ -> fed++ }, { closes++ }) }
        gate.process(tone(3000.0), chunk, { _, _ -> fed++ }, { closes++ })
        assertTrue(gate.active)
        assertEquals(1 + SilenceGate.PRE_ROLL_MS / 100, fed) // audio previo + trozo actual
        repeat(10) { gate.process(tone(3000.0), chunk, { _, _ -> fed++ }, { closes++ }) }
        repeat(30) { gate.process(noise(20.0), chunk, { _, _ -> fed++ }, { closes++ }) }
        assertFalse(gate.active)
        assertEquals(1, closes)
    }

    @Test
    fun unRuidoConstanteTerminaPorDebajoDelUmbral() {
        val gate = SilenceGate(chunk, 100)
        repeat(20) { gate.process(noise(20.0), chunk, { _, _ -> }, {}) }
        repeat(3000) { gate.process(noise(400.0), chunk, { _, _ -> }, {}) } // 5 min de ventilador
        var fedAtEnd = 0
        repeat(100) { gate.process(noise(400.0), chunk, { _, _ -> fedAtEnd++ }, {}) }
        assertTrue("debería descansar con ruido constante, pasó $fedAtEnd/100", fedAtEnd < 20)
    }
}
