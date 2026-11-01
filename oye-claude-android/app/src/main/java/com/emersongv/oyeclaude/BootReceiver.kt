package com.emersongv.oyeclaude

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/**
 * Tras reiniciar o actualizar la app. Si la accesibilidad está activa, ella reanuda
 * la escucha; si no, mostramos un aviso para reactivarla con un toque.
 */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED && intent.action != Intent.ACTION_MY_PACKAGE_REPLACED) return
        if (!Prefs(context).listeningEnabled || WakeWordService.running) return
        Notifications.createChannels(context)
        if (!ClaudeAccessibilityService.isEnabled(context)) Notifications.showReactivate(context)
    }
}
