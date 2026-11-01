package com.emersongv.oyeclaude

import android.Manifest
import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Path
import android.graphics.Rect
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.provider.Settings
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo
import android.widget.Toast
import androidx.core.content.ContextCompat

/**
 * Servicio de accesibilidad:
 *  - toca el botón de voz de Claude después de abrirla,
 *  - informa qué app está en primer plano (para volver a escuchar al salir de Claude),
 *  - captura los botones de Claude para el inspector,
 *  - y, al estar vinculado por el sistema, permite abrir pantallas desde segundo plano.
 */
class ClaudeAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAP_TIMEOUT_MS = 15_000L

        @Volatile
        var instance: ClaudeAccessibilityService? = null
            private set

        fun isEnabled(ctx: Context): Boolean {
            val enabled = Settings.Secure.getString(ctx.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES)
                ?: return false
            val me = ComponentName(ctx, ClaudeAccessibilityService::class.java)
            return enabled.split(':').any { ComponentName.unflattenFromString(it) == me }
        }
    }

    private val handler = Handler(Looper.getMainLooper())
    private lateinit var prefs: Prefs

    private var tapPackage: String? = null
    private var tapDeadline = 0L
    private var tapAttempts = 0
    private var attemptScheduled = false
    private var snapshotScheduled = false

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        prefs = Prefs(this)
        EventLog.add("Servicio de accesibilidad conectado")
        EventLog.changed()
        // Tras reiniciar el teléfono: reanudar la escucha si estaba activada.
        val micOk = ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED
        if (prefs.listeningEnabled && !WakeWordService.running && micOk) {
            handler.postDelayed({
                if (!WakeWordService.running) {
                    BackgroundStarter.start(this, StartListeningActivity.intent(this))
                    handler.postDelayed({
                        if (!WakeWordService.running) Notifications.showReactivate(this)
                    }, 5_000)
                }
            }, 2_000)
        }
    }

    override fun onDestroy() {
        instance = null
        handler.removeCallbacksAndMessages(null)
        EventLog.changed()
        super.onDestroy()
    }

    override fun onInterrupt() {}

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        val pkg = event?.packageName?.toString() ?: return
        if (pkg == tapPackage) scheduleAttempt(300)
        if (Inspector.active && pkg == prefs.claudePackage) scheduleSnapshot()
    }

    // ---------------------------------------------------------------- app en primer plano

    /** Paquete de la app que ocupa la pantalla (ignora teclado, barra de notificaciones, etc.). */
    fun currentAppPackage(): String? = try {
        val ws = windows
        val app = ws.firstOrNull { it.type == AccessibilityWindowInfo.TYPE_APPLICATION && it.isFocused }
            ?: ws.firstOrNull { it.type == AccessibilityWindowInfo.TYPE_APPLICATION && it.isActive }
        app?.root?.packageName?.toString() ?: rootInActiveWindow?.packageName?.toString()
    } catch (_: Exception) {
        null
    }

    private fun rootFor(pkg: String): AccessibilityNodeInfo? {
        rootInActiveWindow?.let { if (it.packageName?.toString() == pkg) return it }
        return try {
            windows.firstNotNullOfOrNull { w -> w.root?.takeIf { it.packageName?.toString() == pkg } }
        } catch (_: Exception) {
            null
        }
    }

    // ---------------------------------------------------------------- tocar botón de voz

    fun requestVoiceTap(pkg: String) {
        tapPackage = pkg
        tapDeadline = SystemClock.elapsedRealtime() + TAP_TIMEOUT_MS
        tapAttempts = 0
        attemptScheduled = false
        scheduleAttempt(800)
    }

    private val attemptRunnable = Runnable {
        attemptScheduled = false
        attemptTap()
    }

    private fun scheduleAttempt(delay: Long) {
        if (attemptScheduled) return
        attemptScheduled = true
        handler.postDelayed(attemptRunnable, delay)
    }

    private fun attemptTap() {
        val pkg = tapPackage ?: return
        if (SystemClock.elapsedRealtime() > tapDeadline) {
            tapPackage = null
            EventLog.add("No encontré el botón de voz en Claude. Usa «Elegir botón de voz».")
            Toast.makeText(this, "Oye Claude: no encontré el botón de voz", Toast.LENGTH_LONG).show()
            return
        }
        tapAttempts++
        val root = rootFor(pkg)
        if (root == null) {
            scheduleAttempt(400)
            return
        }
        val found = VoiceButtonFinder.find(root, prefs.targetLabel)
        if (found != null) {
            if (click(found.node)) {
                tapPackage = null
                EventLog.add("Toqué «${found.label}»")
                return
            }
        } else if (prefs.hasTargetPoint && tapAttempts >= 5) {
            // Respaldo: la posición guardada con el inspector.
            val r = Rect().also { root.getBoundsInScreen(it) }
            if (!r.isEmpty) {
                tap(r.left + prefs.targetX * r.width(), r.top + prefs.targetY * r.height())
                tapPackage = null
                EventLog.add("Toqué la posición guardada del botón de voz")
                return
            }
        }
        scheduleAttempt(500)
    }

    private fun click(node: AccessibilityNodeInfo): Boolean {
        var n: AccessibilityNodeInfo? = node
        var depth = 0
        while (n != null && depth < 4) {
            if (n.isClickable && n.isEnabled) {
                if (n.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true
                break
            }
            n = n.parent
            depth++
        }
        val r = Rect().also { node.getBoundsInScreen(it) }
        return !r.isEmpty && tap(r.exactCenterX(), r.exactCenterY())
    }

    private fun tap(x: Float, y: Float): Boolean {
        val path = Path().apply { moveTo(x, y) }
        val gesture = GestureDescription.Builder()
            .addStroke(GestureDescription.StrokeDescription(path, 0, 60))
            .build()
        return dispatchGesture(gesture, null, null)
    }

    // ---------------------------------------------------------------- inspector

    private val snapshotRunnable = Runnable {
        snapshotScheduled = false
        val root = rootFor(prefs.claudePackage) ?: return@Runnable
        val items = VoiceButtonFinder.inspect(root)
        if (items.isNotEmpty()) Inspector.items = items
    }

    private fun scheduleSnapshot() {
        if (snapshotScheduled) return
        snapshotScheduled = true
        handler.postDelayed(snapshotRunnable, 700)
    }
}
