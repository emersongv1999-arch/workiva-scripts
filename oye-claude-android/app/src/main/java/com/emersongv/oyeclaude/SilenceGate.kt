package com.emersongv.oyeclaude

import kotlin.math.max
import kotlin.math.sqrt

/**
 * Compuerta de silencio para ahorrar batería: el reconocedor Vosk solo recibe
 * audio cuando hay sonido por encima del ruido de fondo.
 *
 * - Guarda ~0,8 s de audio previo para no perder el comienzo de «oye».
 * - Sigue pasando audio ~1,2 s después del último sonido para que Vosk cierre la frase.
 * - El nivel de ruido de fondo se adapta: baja rápido y sube despacio, así un ruido
 *   constante (ventilador, tele) termina quedando por debajo del umbral.
 *
 * Calibrada con las mismas frases sintéticas de las pruebas de detección: mismo
 * acierto que sin compuerta.
 */
class SilenceGate(chunkSize: Int, chunkMs: Int) {
    companion object {
        const val PRE_ROLL_MS = 800
        const val HANGOVER_MS = 1200
        const val FACTOR = 2.0
        const val MIN_RMS = 60.0
    }

    private val preChunks = (PRE_ROLL_MS / chunkMs).coerceAtLeast(1)
    private val hangChunks = (HANGOVER_MS / chunkMs).coerceAtLeast(1)

    private val ring = Array(preChunks) { ShortArray(chunkSize) }
    private val ringLen = IntArray(preChunks)
    private var ringStart = 0
    private var ringCount = 0

    private var floor = -1.0
    private var quiet = 0

    var active = false
        private set

    /** Trozos leídos y trozos pasados al reconocedor (para mostrar el ahorro). */
    var totalChunks = 0L
        private set
    var fedChunks = 0L
        private set

    /**
     * Procesa un trozo de audio. [feed] recibe el audio que debe ir al reconocedor;
     * [close] se llama cuando vuelve el silencio y hay que cerrar la frase.
     */
    fun process(chunk: ShortArray, n: Int, feed: (ShortArray, Int) -> Unit, close: () -> Unit) {
        totalChunks++
        val level = rms(chunk, n)
        floor = when {
            floor < 0 -> level
            level < floor -> 0.7 * floor + 0.3 * level
            else -> 0.995 * floor + 0.005 * level
        }
        val loud = level > max(floor * FACTOR, MIN_RMS)

        if (!active) {
            if (loud) {
                active = true
                quiet = 0
                for (i in 0 until ringCount) {
                    val idx = (ringStart + i) % preChunks
                    feedCounted(ring[idx], ringLen[idx], feed)
                }
                ringCount = 0
                ringStart = 0
                feedCounted(chunk, n, feed)
            } else {
                remember(chunk, n)
            }
        } else {
            feedCounted(chunk, n, feed)
            quiet = if (loud) 0 else quiet + 1
            if (quiet > hangChunks) {
                active = false
                close()
            }
        }
    }

    private fun feedCounted(data: ShortArray, n: Int, feed: (ShortArray, Int) -> Unit) {
        fedChunks++
        feed(data, n)
    }

    private fun remember(chunk: ShortArray, n: Int) {
        val idx: Int
        if (ringCount < preChunks) {
            idx = (ringStart + ringCount) % preChunks
            ringCount++
        } else {
            idx = ringStart
            ringStart = (ringStart + 1) % preChunks
        }
        val len = minOf(n, ring[idx].size)
        System.arraycopy(chunk, 0, ring[idx], 0, len)
        ringLen[idx] = len
    }

    private fun rms(data: ShortArray, n: Int): Double {
        if (n <= 0) return 0.0
        var sum = 0.0
        for (i in 0 until n) {
            val v = data[i].toDouble()
            sum += v * v
        }
        return sqrt(sum / n)
    }
}
