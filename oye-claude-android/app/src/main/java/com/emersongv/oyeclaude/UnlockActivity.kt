package com.emersongv.oyeclaude

import android.app.Activity
import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.WindowManager
import android.widget.Toast

/**
 * Pantalla invisible que se muestra sobre la pantalla de bloqueo, la enciende,
 * pide desbloquear (PIN / huella / cara) y luego abre Claude.
 */
class UnlockActivity : Activity() {

    companion object {
        /** La app de Claude abre los enlaces de claude.ai (ver claude.ai/.well-known/assetlinks.json). */
        private const val NEW_CHAT_URL = "https://claude.ai/new"

        fun intent(ctx: Context): Intent = Intent(ctx, UnlockActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION)
    }

    private val handler = Handler(Looper.getMainLooper())
    private var started = false
    private var done = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        markStarted()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON,
            )
        }
        // Por si el usuario ignora el desbloqueo.
        handler.postDelayed({ if (!done) fail("Tiempo de desbloqueo agotado") }, 60_000)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        markStarted()
    }

    private fun markStarted() {
        WakeLauncher.lastUnlockActivityStart = SystemClock.elapsedRealtime()
        Notifications.cancelFullScreen(this)
        BackgroundStarter.done()
    }

    override fun onResume() {
        super.onResume()
        if (started) return
        started = true
        window.decorView.post { unlockThenOpen() }
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    private fun unlockThenOpen() {
        val km = getSystemService(KeyguardManager::class.java)
        if (km == null || !km.isKeyguardLocked) {
            openClaude()
            return
        }
        EventLog.add("Pidiendo desbloqueo…")
        km.requestDismissKeyguard(this, object : KeyguardManager.KeyguardDismissCallback() {
            override fun onDismissSucceeded() = openClaude()
            override fun onDismissCancelled() = fail("Desbloqueo cancelado")
            override fun onDismissError() = fail("No se pudo mostrar el desbloqueo")
        })
    }

    private fun openClaude() {
        if (done) return
        done = true
        val prefs = Prefs(this)
        val pkg = prefs.claudePackage
        val launch = claudeIntent(pkg, prefs.openNewChat)
        if (launch == null) {
            Toast.makeText(this, "No encontré la app de Claude ($pkg)", Toast.LENGTH_LONG).show()
            fail("App de Claude no instalada: $pkg")
            return
        }
        Flow.set(Flow.Phase.IN_CLAUDE)
        val a11y = ClaudeAccessibilityService.instance
        if (a11y != null) {
            a11y.requestVoiceTap(pkg, prefs.openNewChat)
        } else {
            EventLog.add("Accesibilidad desactivada: abro Claude pero no puedo tocar el botón de voz")
            Toast.makeText(this, "Activa la accesibilidad de Oye Claude para tocar el botón de voz", Toast.LENGTH_LONG).show()
        }
        EventLog.add("Abriendo Claude")
        startActivity(launch)
        finish()
    }

    /** Chat nuevo vía enlace si la app lo acepta; si no, la app tal como quedó. */
    private fun claudeIntent(pkg: String, newChat: Boolean): Intent? {
        if (newChat) {
            val view = Intent(Intent.ACTION_VIEW, Uri.parse(NEW_CHAT_URL)).setPackage(pkg)
            if (view.resolveActivity(packageManager) != null) {
                EventLog.add("Abriendo un chat nuevo en Claude")
                return view.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            EventLog.add("Claude no acepta el enlace de chat nuevo; abro la app tal como quedó")
        }
        return packageManager.getLaunchIntentForPackage(pkg)
            ?.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
    }

    private fun fail(reason: String) {
        done = true
        EventLog.add(reason)
        Flow.set(Flow.Phase.IDLE)
        WakeWordService.send(this, WakeWordService.ACTION_RESUME)
        finish()
    }
}
