package com.emersongv.oyeclaude

import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import android.os.SystemClock

/** Enciende la pantalla y abre [UnlockActivity] (que pide desbloquear y abre Claude). */
object WakeLauncher {
    @Volatile
    var lastUnlockActivityStart = 0L

    private val main = Handler(Looper.getMainLooper())

    fun launch(context: Context) {
        val ctx = context.applicationContext
        Flow.set(Flow.Phase.UNLOCKING)
        wakeScreen(ctx)
        val requestedAt = SystemClock.elapsedRealtime()
        val how = BackgroundStarter.start(ctx, UnlockActivity.intent(ctx))
        EventLog.add("Abriendo pantalla de desbloqueo ($how) · Android ${Build.VERSION.RELEASE}")
        main.postDelayed({
            if (lastUnlockActivityStart < requestedAt) {
                EventLog.add(
                    if (ClaudeAccessibilityService.instance == null) {
                        "Android bloqueó la apertura: activa la accesibilidad de Oye Claude. Uso una notificación."
                    } else {
                        "Android bloqueó la apertura. Uso una notificación (tócala)."
                    },
                )
                Notifications.showFullScreenLaunch(ctx)
            }
        }, 2_500)
    }

    @Suppress("DEPRECATION")
    private fun wakeScreen(ctx: Context) {
        val pm = ctx.getSystemService(PowerManager::class.java) ?: return
        if (pm.isInteractive) return
        try {
            pm.newWakeLock(
                PowerManager.SCREEN_BRIGHT_WAKE_LOCK or PowerManager.ACQUIRE_CAUSES_WAKEUP or PowerManager.ON_AFTER_RELEASE,
                "OyeClaude:wake",
            ).acquire(5_000)
        } catch (e: Exception) {
            EventLog.add("No se pudo encender la pantalla: ${e.message}")
        }
    }
}
