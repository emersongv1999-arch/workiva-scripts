package com.emersongv.oyeclaude

import android.os.SystemClock

/** Fase del flujo tras detectar la frase: desbloqueo → dentro de Claude → vuelta a escuchar. */
object Flow {
    enum class Phase { IDLE, UNLOCKING, IN_CLAUDE }

    @Volatile
    var phase: Phase = Phase.IDLE
        private set

    @Volatile
    var since: Long = 0L
        private set

    fun set(p: Phase) {
        phase = p
        since = SystemClock.elapsedRealtime()
    }
}
