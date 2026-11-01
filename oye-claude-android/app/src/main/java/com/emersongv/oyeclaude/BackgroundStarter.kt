package com.emersongv.oyeclaude

import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.WindowManager

/**
 * Android (10+) no deja que una app en segundo plano abra pantallas, salvo que
 * tenga una ventana visible. Justo antes de abrir mostramos una ventana invisible
 * de 1 px:
 *  - de accesibilidad (TYPE_ACCESSIBILITY_OVERLAY) si el servicio está activo;
 *    funciona incluso sobre la pantalla de bloqueo,
 *  - o superpuesta (TYPE_APPLICATION_OVERLAY) si se concedió «Mostrar sobre otras apps».
 */
object BackgroundStarter {
    private const val LAUNCH_DELAY_MS = 300L
    private const val OVERLAY_LIFETIME_MS = 6_000L

    private val main = Handler(Looper.getMainLooper())
    private var overlay: Pair<WindowManager, View>? = null
    private val removeRunnable = Runnable { removeOverlay() }

    /** Abre [intent] (debe llevar FLAG_ACTIVITY_NEW_TASK). Devuelve el método usado, para el registro. */
    fun start(ctx: Context, intent: Intent): String {
        val a11y = ClaudeAccessibilityService.instance
        val host: Context
        val how: String
        val shown = when {
            a11y != null && showOverlay(a11y, WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY) -> {
                host = a11y
                how = "ventana de accesibilidad"
                true
            }
            Settings.canDrawOverlays(ctx) &&
                showOverlay(ctx.applicationContext, WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY) -> {
                host = ctx.applicationContext
                how = "ventana superpuesta"
                true
            }
            else -> {
                host = a11y ?: ctx.applicationContext
                how = "directo (puede que Android lo bloquee)"
                false
            }
        }
        val launch = Runnable {
            try {
                host.startActivity(intent)
            } catch (e: Exception) {
                EventLog.add("No se pudo abrir la pantalla: ${e.message}")
            }
        }
        // Damos tiempo a que la ventana auxiliar se dibuje (cuenta como visible).
        if (shown) main.postDelayed(launch, LAUNCH_DELAY_MS) else launch.run()
        main.removeCallbacks(removeRunnable)
        main.postDelayed(removeRunnable, OVERLAY_LIFETIME_MS)
        return how
    }

    /** La pantalla ya se abrió: quitamos la ventana auxiliar. */
    fun done() {
        main.removeCallbacks(removeRunnable)
        main.postDelayed(removeRunnable, 500)
    }

    private fun showOverlay(host: Context, type: Int): Boolean {
        removeOverlay()
        val wm = host.getSystemService(WindowManager::class.java) ?: return false
        val view = View(host).apply { setBackgroundColor(Color.TRANSPARENT) }
        val lp = WindowManager.LayoutParams(
            1, 1, type,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or
                WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE or
                WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        ).apply { gravity = Gravity.TOP or Gravity.START }
        return try {
            wm.addView(view, lp)
            overlay = wm to view
            true
        } catch (e: Exception) {
            EventLog.add("No se pudo crear la ventana auxiliar: ${e.message}")
            false
        }
    }

    private fun removeOverlay() {
        overlay?.let { (wm, view) ->
            try {
                wm.removeViewImmediate(view)
            } catch (_: Exception) {
            }
        }
        overlay = null
    }
}
