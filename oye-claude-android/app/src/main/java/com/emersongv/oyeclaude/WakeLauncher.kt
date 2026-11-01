package com.emersongv.oyeclaude

import android.content.Context
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
        try {
            // Permitido desde segundo plano porque el servicio de accesibilidad está
            // vinculado por el sistema (o si se concedió «Mostrar sobre otras apps»).
            ctx.startActivity(UnlockActivity.intent(ctx))
        } catch (e: Exception) {
            EventLog.add("No se pudo abrir la pantalla de desbloqueo: ${e.message}")
        }
        main.postDelayed({
            if (lastUnlockActivityStart < requestedAt) {
                EventLog.add("Android bloqueó la apertura directa; uso notificación de pantalla completa")
                Notifications.showFullScreenLaunch(ctx)
            }
        }, 1500)
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
