package com.emersongv.oyeclaude

import android.os.Handler
import android.os.Looper
import android.util.Log
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.CopyOnWriteArraySet

/** Registro en memoria que se muestra en la pantalla principal (útil para diagnosticar). */
object EventLog {
    private const val TAG = "OyeClaude"
    private const val MAX_LINES = 120

    private val lines = ArrayDeque<String>()
    private val listeners = CopyOnWriteArraySet<() -> Unit>()
    private val main = Handler(Looper.getMainLooper())
    private val time = SimpleDateFormat("HH:mm:ss", Locale.US)

    @Volatile
    var lastHeard: String = ""
        private set

    fun add(message: String) {
        Log.i(TAG, message)
        synchronized(lines) {
            lines.addLast("${time.format(Date())}  $message")
            while (lines.size > MAX_LINES) lines.removeFirst()
        }
        changed()
    }

    fun heard(text: String) {
        lastHeard = text
        changed()
    }

    fun snapshot(): List<String> = synchronized(lines) { lines.toList() }

    fun addListener(l: () -> Unit) {
        listeners += l
    }

    fun removeListener(l: () -> Unit) {
        listeners -= l
    }

    /** Notifica a la UI (estado del servicio, accesibilidad, etc.). */
    fun changed() {
        main.post { listeners.forEach { it() } }
    }
}
