package com.emersongv.oyeclaude

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat

object Notifications {
    private const val CHANNEL_LISTEN = "escucha"
    private const val CHANNEL_ALERT = "alertas"

    const val ID_LISTENING = 1
    private const val ID_FULLSCREEN = 2
    private const val ID_REACTIVATE = 3

    fun createChannels(ctx: Context) {
        val nm = ctx.getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL_LISTEN, "Escucha en segundo plano", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Aviso permanente mientras se escucha «Oye Claude»"
                setShowBadge(false)
            }
        )
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL_ALERT, "Abrir Claude", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "Se usa para abrir Claude cuando Android bloquea la apertura directa"
                setSound(null, null)
            }
        )
    }

    private fun pendingFlags() = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE

    private fun serviceAction(ctx: Context, action: String, code: Int): PendingIntent =
        PendingIntent.getService(ctx, code, Intent(ctx, WakeWordService::class.java).setAction(action), pendingFlags())

    private fun openMain(ctx: Context, autostart: Boolean = false): PendingIntent {
        val intent = Intent(ctx, MainActivity::class.java)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            .putExtra(MainActivity.EXTRA_AUTOSTART, autostart)
        return PendingIntent.getActivity(ctx, if (autostart) 11 else 10, intent, pendingFlags())
    }

    fun listening(ctx: Context, status: String, paused: Boolean): Notification =
        NotificationCompat.Builder(ctx, CHANNEL_LISTEN)
            .setSmallIcon(R.drawable.ic_stat_mic)
            .setContentTitle("Oye Claude")
            .setContentText(status)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setShowWhen(false)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setContentIntent(openMain(ctx))
            .addAction(
                0,
                if (paused) "Reanudar" else "Pausar",
                serviceAction(ctx, WakeWordService.ACTION_TOGGLE_PAUSE, 20),
            )
            .addAction(0, "Detener", serviceAction(ctx, WakeWordService.ACTION_STOP, 21))
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()

    fun update(ctx: Context, notification: Notification) {
        if (canNotify(ctx)) NotificationManagerCompat.from(ctx).notify(ID_LISTENING, notification)
    }

    /** Respaldo: notificación de pantalla completa que abre la pantalla de desbloqueo. */
    fun showFullScreenLaunch(ctx: Context) {
        if (!canNotify(ctx)) return
        val pi = PendingIntent.getActivity(ctx, 30, UnlockActivity.intent(ctx), pendingFlags())
        val n = NotificationCompat.Builder(ctx, CHANNEL_ALERT)
            .setSmallIcon(R.drawable.ic_stat_mic)
            .setContentTitle("Oye Claude")
            .setContentText("Toca para desbloquear y hablar con Claude")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setAutoCancel(true)
            .setTimeoutAfter(30_000)
            .setContentIntent(pi)
            .setFullScreenIntent(pi, true)
            .build()
        NotificationManagerCompat.from(ctx).notify(ID_FULLSCREEN, n)
    }

    fun cancelFullScreen(ctx: Context) = NotificationManagerCompat.from(ctx).cancel(ID_FULLSCREEN)

    /** Tras reiniciar, Android no deja abrir el micrófono sin que el usuario abra la app. */
    fun showReactivate(ctx: Context) {
        if (!canNotify(ctx)) return
        val n = NotificationCompat.Builder(ctx, CHANNEL_ALERT)
            .setSmallIcon(R.drawable.ic_stat_mic)
            .setContentTitle("Oye Claude está en pausa")
            .setContentText("Toca para volver a escuchar «Oye Claude»")
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true)
            .setContentIntent(openMain(ctx, autostart = true))
            .build()
        NotificationManagerCompat.from(ctx).notify(ID_REACTIVATE, n)
    }

    fun cancelReactivate(ctx: Context) = NotificationManagerCompat.from(ctx).cancel(ID_REACTIVATE)

    fun canNotify(ctx: Context): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
}
