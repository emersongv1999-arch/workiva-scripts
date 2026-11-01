package com.emersongv.oyeclaude

import android.app.Activity
import android.content.Context
import android.content.Intent

/**
 * Pantalla invisible que arranca el servicio de escucha. Android exige que la app
 * esté visible para empezar a usar el micrófono en segundo plano; el servicio de
 * accesibilidad la abre tras reiniciar el teléfono.
 */
class StartListeningActivity : Activity() {

    companion object {
        fun intent(ctx: Context): Intent = Intent(ctx, StartListeningActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION)
    }

    private var launched = false

    override fun onResume() {
        super.onResume()
        if (launched) return
        launched = true
        try {
            WakeWordService.start(this)
            EventLog.add("Escucha reanudada automáticamente")
        } catch (e: Exception) {
            EventLog.add("No se pudo reanudar la escucha: ${e.message}")
            Notifications.showReactivate(this)
        }
        window.decorView.postDelayed({ finish() }, 300)
    }
}
