package com.emersongv.oyeclaude

import android.Manifest
import android.annotation.SuppressLint
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.media.ToneGenerator
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.os.VibrationEffect
import android.os.Vibrator
import androidx.core.content.ContextCompat
import org.json.JSONObject
import org.vosk.LibVosk
import org.vosk.LogLevel
import org.vosk.Model
import org.vosk.Recognizer
import java.util.concurrent.Executors

/**
 * Servicio en primer plano (tipo micrófono) que escucha «Oye Claude» con Vosk.
 *
 * Al detectar la frase suelta el micrófono (para que Claude lo pueda usar), abre
 * la pantalla de desbloqueo y vuelve a escuchar cuando sales de Claude.
 */
class WakeWordService : Service() {

    companion object {
        const val ACTION_START = "com.emersongv.oyeclaude.action.START"
        const val ACTION_STOP = "com.emersongv.oyeclaude.action.STOP"
        const val ACTION_TOGGLE_PAUSE = "com.emersongv.oyeclaude.action.TOGGLE_PAUSE"
        const val ACTION_RESUME = "com.emersongv.oyeclaude.action.RESUME"
        const val ACTION_TRIGGER = "com.emersongv.oyeclaude.action.TRIGGER"

        private const val SAMPLE_RATE = 16000
        private const val MAX_IN_CLAUDE_MS = 30 * 60_000L
        private const val MAX_UNLOCK_MS = 60_000L
        private const val NO_A11Y_PAUSE_MS = 60_000L

        @Volatile
        var running = false
            private set

        @Volatile
        var status: String = "Detenido"
            private set

        fun start(ctx: Context) {
            ContextCompat.startForegroundService(ctx, Intent(ctx, WakeWordService::class.java).setAction(ACTION_START))
        }

        fun stop(ctx: Context) {
            ctx.stopService(Intent(ctx, WakeWordService::class.java))
        }

        /** Envía una orden al servicio solo si ya está en marcha. */
        fun send(ctx: Context, action: String): Boolean {
            if (!running) return false
            return try {
                ctx.startService(Intent(ctx, WakeWordService::class.java).setAction(action))
                true
            } catch (e: Exception) {
                EventLog.add("No se pudo enviar $action: ${e.message}")
                false
            }
        }
    }

    private val handler = Handler(Looper.getMainLooper())
    private val loader = Executors.newSingleThreadExecutor()
    private lateinit var prefs: Prefs

    private var foreground = false
    private var destroyed = false
    private var loading = false
    private var model: Model? = null
    private var listener: ListenThread? = null

    private var triggers = WakeMatcher.DEFAULT_TRIGGERS
    private var variants = WakeMatcher.DEFAULT_VARIANTS

    private var manualPause = false
    private var awaitingReturn = false
    private var pausedAt = 0L
    private var lastWake = 0L
    private var leftClaudeChecks = 0
    private var retryDelay = 2_000L

    private val screenOffReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            // Si se apagó la pantalla sin desbloquear, volvemos a escuchar.
            if (awaitingReturn && Flow.phase == Flow.Phase.UNLOCKING) {
                Flow.set(Flow.Phase.IDLE)
                finishWaiting("pantalla apagada sin desbloquear")
            }
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        prefs = Prefs(this)
        Notifications.createChannels(this)
        ContextCompat.registerReceiver(
            this, screenOffReceiver, IntentFilter(Intent.ACTION_SCREEN_OFF), ContextCompat.RECEIVER_NOT_EXPORTED,
        )
        try {
            LibVosk.setLogLevel(LogLevel.WARNINGS)
        } catch (_: Throwable) {
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!goForeground()) {
            stopSelf()
            return START_NOT_STICKY
        }
        when (intent?.action) {
            ACTION_STOP -> {
                prefs.listeningEnabled = false
                EventLog.add("Escucha detenida")
                stopSelf()
                return START_NOT_STICKY
            }
            ACTION_TOGGLE_PAUSE -> {
                manualPause = !manualPause
                if (manualPause) {
                    stopListening()
                    setStatus("En pausa")
                    EventLog.add("Escucha en pausa")
                } else {
                    awaitingReturn = false
                    startListening()
                }
            }
            ACTION_RESUME -> if (awaitingReturn) finishWaiting("reanudado") else if (!manualPause) startListening()
            ACTION_TRIGGER -> onWake("prueba manual")
            else -> {
                prefs.listeningEnabled = true
                Notifications.cancelReactivate(this)
                if (!manualPause && !awaitingReturn) startListening()
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        destroyed = true
        running = false
        handler.removeCallbacksAndMessages(null)
        try {
            unregisterReceiver(screenOffReceiver)
        } catch (_: Exception) {
        }
        stopListening()
        val m = model
        model = null
        loader.execute { m?.close() }
        loader.shutdown()
        setStatus("Detenido")
        super.onDestroy()
    }

    // ---------------------------------------------------------------- primer plano

    private fun goForeground(): Boolean {
        if (foreground) return true
        return try {
            val n = Notifications.listening(this, "Iniciando…", false)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(Notifications.ID_LISTENING, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE)
            } else {
                startForeground(Notifications.ID_LISTENING, n)
            }
            foreground = true
            running = true
            true
        } catch (e: Exception) {
            EventLog.add("Android no permitió iniciar la escucha: ${e.message}")
            Notifications.showReactivate(this)
            false
        }
    }

    private fun setStatus(text: String) {
        status = text
        if (foreground && !destroyed) {
            Notifications.update(this, Notifications.listening(this, text, manualPause))
        }
        EventLog.changed()
    }

    // ---------------------------------------------------------------- micrófono

    private fun hasMicPermission() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private fun startListening() {
        if (destroyed || listener != null || loading || manualPause || awaitingReturn) return
        if (!hasMicPermission()) {
            setStatus("Falta el permiso de micrófono")
            return
        }
        val m = model
        if (m == null) {
            loadModelThenListen()
            return
        }
        try {
            triggers = prefs.triggerWords
            variants = prefs.nameVariants
            val rec = Recognizer(m, SAMPLE_RATE.toFloat(), WakeMatcher.grammar(triggers, variants))
            listener = ListenThread(rec).also { it.start() }
            setStatus("Escuchando «${triggers.first()} ${variants.first()}»")
        } catch (e: Exception) {
            EventLog.add("No se pudo iniciar el reconocedor: ${e.message}")
            scheduleRetry()
        }
    }

    /** Suelta el micrófono (espera hasta ~1 s a que el hilo termine). */
    private fun stopListening() {
        val t = listener ?: return
        listener = null
        t.requestStop()
        try {
            t.join(1_000)
        } catch (_: InterruptedException) {
        }
    }

    private val retryRunnable = Runnable { startListening() }

    private fun scheduleRetry() {
        handler.removeCallbacks(retryRunnable)
        handler.postDelayed(retryRunnable, retryDelay)
        retryDelay = (retryDelay * 2).coerceAtMost(60_000L)
    }

    private fun loadModelThenListen() {
        if (loading || destroyed) return
        loading = true
        setStatus("Preparando el modelo de voz…")
        loader.execute {
            try {
                val dir = ModelManager.ensure(this)
                val m = Model(dir.absolutePath)
                handler.post {
                    loading = false
                    if (destroyed) {
                        m.close()
                    } else {
                        model = m
                        startListening()
                    }
                }
            } catch (e: Throwable) {
                handler.post {
                    loading = false
                    EventLog.add("Error al cargar el modelo: ${e.message}")
                    setStatus("Error con el modelo de voz")
                }
            }
        }
    }

    /** Hilo que lee el micrófono y pasa el audio a Vosk. Es dueño del AudioRecord y del Recognizer. */
    private inner class ListenThread(private val rec: Recognizer) : Thread("oye-claude-mic") {
        @Volatile
        private var stopRequested = false

        fun requestStop() {
            stopRequested = true
        }

        @SuppressLint("MissingPermission") // comprobado en startListening()
        override fun run() {
            var record: AudioRecord? = null
            try {
                val minBuf = AudioRecord.getMinBufferSize(
                    SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT,
                )
                val chunk = maxOf(minBuf / 2, SAMPLE_RATE / 10) // ~100 ms en muestras
                record = AudioRecord(
                    MediaRecorder.AudioSource.VOICE_RECOGNITION, SAMPLE_RATE,
                    AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, maxOf(minBuf, chunk * 4),
                )
                if (record.state != AudioRecord.STATE_INITIALIZED) throw IllegalStateException("micrófono no disponible")
                record.startRecording()
                if (record.recordingState != AudioRecord.RECORDSTATE_RECORDING) throw IllegalStateException("micrófono en uso")
                handler.post { retryDelay = 2_000L }
                val buffer = ShortArray(chunk)
                while (!stopRequested) {
                    val n = record.read(buffer, 0, buffer.size)
                    if (n < 0) throw IllegalStateException("error de lectura $n")
                    if (n == 0 || stopRequested) continue
                    if (rec.acceptWaveForm(buffer, n)) {
                        val result = rec.result
                        handler.post { if (listener === this) handleResult(result) }
                    }
                }
            } catch (e: Throwable) {
                if (!stopRequested) {
                    handler.post {
                        if (listener === this) {
                            listener = null
                            EventLog.add("Problema con el micrófono: ${e.message}")
                            setStatus("Micrófono ocupado; reintentando…")
                            scheduleRetry()
                        }
                    }
                }
            } finally {
                try {
                    record?.stop()
                } catch (_: Exception) {
                }
                record?.release()
                try {
                    rec.close()
                } catch (_: Exception) {
                }
            }
        }
    }

    private fun handleResult(json: String?) {
        if (json.isNullOrBlank()) return
        val text = try {
            JSONObject(json).optString("text")
        } catch (_: Exception) {
            return
        }
        // Solo usamos resultados finales (tras una pausa): son más fiables que los parciales.
        val clean = text.replace("[unk]", " ").trim().replace(Regex("\\s+"), " ")
        if (clean.isEmpty()) return
        EventLog.heard(clean)
        if (WakeMatcher.matches(clean, triggers, variants)) onWake("«$clean»")
    }

    // ---------------------------------------------------------------- activación

    private fun onWake(reason: String) {
        val now = SystemClock.elapsedRealtime()
        if (now - lastWake < 3_000) return
        lastWake = now
        EventLog.add("¡Activado! $reason")
        stopListening()
        handler.removeCallbacks(retryRunnable)
        awaitingReturn = true
        pausedAt = now
        leftClaudeChecks = 0
        setStatus("Abriendo Claude…")
        if (prefs.beepOnWake) feedback()
        WakeLauncher.launch(this)
        handler.removeCallbacks(resumeCheck)
        handler.postDelayed(resumeCheck, 3_000)
    }

    /** Comprueba periódicamente si ya podemos recuperar el micrófono. */
    private val resumeCheck = object : Runnable {
        override fun run() {
            if (!awaitingReturn || destroyed) return
            val elapsed = SystemClock.elapsedRealtime() - pausedAt
            val resume = when (Flow.phase) {
                Flow.Phase.IDLE -> true
                Flow.Phase.UNLOCKING -> elapsed > MAX_UNLOCK_MS
                Flow.Phase.IN_CLAUDE -> {
                    val a11y = ClaudeAccessibilityService.instance
                    if (a11y == null) {
                        elapsed > NO_A11Y_PAUSE_MS
                    } else {
                        val fg = a11y.currentAppPackage()
                        leftClaudeChecks = if (fg != null && fg != prefs.claudePackage) leftClaudeChecks + 1 else 0
                        // Esperamos a que salgas de Claude y que nadie más use el micrófono.
                        (leftClaudeChecks >= 2 && !someoneElseRecording()) || elapsed > MAX_IN_CLAUDE_MS
                    }
                }
            }
            if (resume) {
                Flow.set(Flow.Phase.IDLE)
                finishWaiting("saliste de Claude")
            } else {
                handler.postDelayed(this, 2_000)
            }
        }
    }

    private fun finishWaiting(reason: String) {
        handler.removeCallbacks(resumeCheck)
        awaitingReturn = false
        EventLog.add("Vuelvo a escuchar ($reason)")
        startListening()
    }

    /** Nuestro micrófono está cerrado, así que cualquier grabación activa es de otra app. */
    private fun someoneElseRecording(): Boolean = try {
        getSystemService(AudioManager::class.java)?.activeRecordingConfigurations?.isNotEmpty() == true
    } catch (_: Exception) {
        false
    }

    @Suppress("DEPRECATION")
    private fun feedback() {
        try {
            val tone = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 70)
            tone.startTone(ToneGenerator.TONE_PROP_BEEP2, 180)
            handler.postDelayed({ tone.release() }, 400)
        } catch (_: Exception) {
        }
        try {
            getSystemService(Vibrator::class.java)?.vibrate(VibrationEffect.createOneShot(60, VibrationEffect.DEFAULT_AMPLITUDE))
        } catch (_: Exception) {
        }
    }
}
