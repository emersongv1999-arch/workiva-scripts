package com.emersongv.oyeclaude

import android.Manifest
import android.app.NotificationManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.PowerManager
import android.provider.Settings
import android.widget.Toast
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.isVisible
import com.emersongv.oyeclaude.databinding.ActivityMainBinding
import com.google.android.material.button.MaterialButton
import com.google.android.material.dialog.MaterialAlertDialogBuilder

class MainActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_AUTOSTART = "autostart"
    }

    private lateinit var b: ActivityMainBinding
    private val prefs by lazy { Prefs(this) }
    private var updatingUi = false
    private var startAfterMicGrant = false

    private val onChanged: () -> Unit = { refresh() }

    private val micPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted && startAfterMicGrant) startListening()
        startAfterMicGrant = false
        refresh()
    }

    private val notifPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) {
        refresh()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        b = ActivityMainBinding.inflate(layoutInflater)
        setContentView(b.root)
        ViewCompat.setOnApplyWindowInsetsListener(b.root) { v, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars() or WindowInsetsCompat.Type.displayCutout())
            v.setPadding(bars.left, bars.top, bars.right, bars.bottom)
            insets
        }
        Notifications.createChannels(this)

        b.listenSwitch.setOnCheckedChangeListener { _, checked ->
            if (updatingUi) return@setOnCheckedChangeListener
            if (checked) startListening() else stopListening()
        }
        b.testButton.setOnClickListener { testNow() }

        b.btnMic.setOnClickListener { micPermission.launch(Manifest.permission.RECORD_AUDIO) }
        b.btnNotif.setOnClickListener {
            if (Build.VERSION.SDK_INT >= 33) notifPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        b.btnA11y.setOnClickListener { open(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
        b.btnAppInfo.setOnClickListener {
            open(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
        }
        b.btnBattery.setOnClickListener {
            open(Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:$packageName")))
        }
        b.btnOverlay.setOnClickListener {
            open(Intent(Settings.ACTION_MANAGE_OVERLAY_PERMISSION, Uri.parse("package:$packageName")))
        }
        b.btnFullScreen.setOnClickListener {
            if (Build.VERSION.SDK_INT >= 34) {
                open(Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:$packageName")))
            }
        }

        b.btnInspect.setOnClickListener { chooseVoiceButton() }
        b.btnResetTarget.setOnClickListener {
            prefs.clearTarget()
            Toast.makeText(this, "Usando detección automática", Toast.LENGTH_SHORT).show()
            refresh()
        }

        b.inputPackage.setText(prefs.claudePackage)
        b.inputTriggers.setText(prefs.triggerWords.joinToString(", "))
        b.inputVariants.setText(prefs.nameVariants.joinToString(", "))
        b.beepSwitch.isChecked = prefs.beepOnWake
        b.btnSave.setOnClickListener { saveAdvanced() }

        handleAutostart(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleAutostart(intent)
    }

    override fun onResume() {
        super.onResume()
        EventLog.addListener(onChanged)
        refresh()
        if (Inspector.active) {
            Inspector.active = false
            showInspectorResults()
        }
    }

    override fun onPause() {
        EventLog.removeListener(onChanged)
        super.onPause()
    }

    // ---------------------------------------------------------------- acciones

    private fun handleAutostart(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_AUTOSTART, false) == true) {
            intent.removeExtra(EXTRA_AUTOSTART)
            Notifications.cancelReactivate(this)
            startListening()
        }
    }

    private fun hasMic() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private fun startListening() {
        if (!hasMic()) {
            startAfterMicGrant = true
            micPermission.launch(Manifest.permission.RECORD_AUDIO)
            refresh()
            return
        }
        if (Build.VERSION.SDK_INT >= 33 && !Notifications.canNotify(this)) {
            notifPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
        prefs.listeningEnabled = true
        try {
            WakeWordService.start(this)
        } catch (e: Exception) {
            Toast.makeText(this, "No se pudo iniciar: ${e.message}", Toast.LENGTH_LONG).show()
        }
        refresh()
    }

    private fun stopListening() {
        prefs.listeningEnabled = false
        WakeWordService.stop(this)
        EventLog.add("Escucha detenida")
        refresh()
    }

    private fun testNow() {
        if (!WakeWordService.send(this, WakeWordService.ACTION_TRIGGER)) {
            EventLog.add("Prueba manual (sin escucha activa)")
            WakeLauncher.launch(this)
        }
    }

    private fun saveAdvanced() {
        prefs.claudePackage = b.inputPackage.text?.toString().orEmpty()
        prefs.triggerWords = Prefs.splitWords(b.inputTriggers.text?.toString())
        prefs.nameVariants = Prefs.splitWords(b.inputVariants.text?.toString())
        prefs.beepOnWake = b.beepSwitch.isChecked
        b.inputPackage.setText(prefs.claudePackage)
        b.inputTriggers.setText(prefs.triggerWords.joinToString(", "))
        b.inputVariants.setText(prefs.nameVariants.joinToString(", "))
        // Reinicia el reconocedor para aplicar la nueva gramática.
        if (WakeWordService.running) {
            WakeWordService.stop(this)
            b.root.postDelayed({ startListening() }, 500)
        }
        Toast.makeText(this, "Guardado", Toast.LENGTH_SHORT).show()
        refresh()
    }

    private fun open(intent: Intent) {
        try {
            startActivity(intent)
        } catch (_: Exception) {
            try {
                startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:$packageName")))
            } catch (_: Exception) {
                Toast.makeText(this, "No se pudo abrir los ajustes", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ---------------------------------------------------------------- inspector

    private fun chooseVoiceButton() {
        if (ClaudeAccessibilityService.instance == null) {
            Toast.makeText(this, "Primero activa la accesibilidad de Oye Claude", Toast.LENGTH_LONG).show()
            return
        }
        MaterialAlertDialogBuilder(this)
            .setTitle("Elegir botón de voz")
            .setMessage(
                "1. Se abrirá Claude.\n" +
                    "2. Ve a la pantalla donde ves el botón de voz (por ejemplo, un chat nuevo).\n" +
                    "3. Vuelve a Oye Claude y elige el botón de la lista.",
            )
            .setPositiveButton("Abrir Claude") { _, _ ->
                val launch = packageManager.getLaunchIntentForPackage(prefs.claudePackage)
                if (launch == null) {
                    Toast.makeText(this, "No encontré la app de Claude", Toast.LENGTH_LONG).show()
                } else {
                    Inspector.begin()
                    startActivity(launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                }
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    private fun showInspectorResults() {
        val items = Inspector.items
        if (items.isEmpty()) {
            Toast.makeText(this, "No capturé botones de Claude. Inténtalo de nuevo.", Toast.LENGTH_LONG).show()
            return
        }
        val labels = items.map { (if (it.score >= 60) "★ " else "") + it.label }.toTypedArray()
        MaterialAlertDialogBuilder(this)
            .setTitle("¿Cuál es el botón de voz?")
            .setItems(labels) { _, which ->
                val item = items[which]
                prefs.targetLabel = item.label
                prefs.targetX = item.relX
                prefs.targetY = item.relY
                EventLog.add("Botón de voz elegido: «${item.label}»")
                refresh()
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }

    // ---------------------------------------------------------------- estado

    private fun refresh() {
        if (!::b.isInitialized) return
        updatingUi = true
        b.listenSwitch.isChecked = prefs.listeningEnabled
        updatingUi = false
        b.serviceStatus.text = when {
            WakeWordService.running -> WakeWordService.status
            prefs.listeningEnabled -> "No está escuchando. Apaga y enciende el interruptor."
            else -> "Detenido"
        }

        val mic = hasMic()
        val notif = Notifications.canNotify(this)
        val a11yOn = ClaudeAccessibilityService.instance != null
        val battery = getSystemService(PowerManager::class.java)?.isIgnoringBatteryOptimizations(packageName) == true
        val overlay = Settings.canDrawOverlays(this)
        val fullScreen = Build.VERSION.SDK_INT < 34 ||
            getSystemService(NotificationManager::class.java)?.canUseFullScreenIntent() == true
        val claudeInstalled = packageManager.getLaunchIntentForPackage(prefs.claudePackage) != null

        b.checklist.text = buildString {
            appendLine(check(claudeInstalled, "App de Claude instalada"))
            appendLine(check(mic, "Micrófono"))
            appendLine(check(a11yOn, "Accesibilidad (abrir Claude y tocar el botón de voz)"))
            append(check(ModelManager.isReady(this@MainActivity), "Modelo de voz preparado"))
        }

        setPermissionButton(b.btnMic, mic, "Permitir micrófono")
        setPermissionButton(b.btnNotif, notif, "Permitir notificaciones")
        b.btnNotif.isVisible = Build.VERSION.SDK_INT >= 33
        setPermissionButton(b.btnA11y, a11yOn, "Activar accesibilidad")
        b.a11yHint.isVisible = !a11yOn
        b.btnAppInfo.isVisible = !a11yOn
        setPermissionButton(b.btnBattery, battery, "Quitar optimización de batería")
        setPermissionButton(b.btnOverlay, overlay, "Mostrar sobre otras apps (recomendado)")
        setPermissionButton(b.btnFullScreen, fullScreen, "Notificaciones a pantalla completa")
        b.btnFullScreen.isVisible = Build.VERSION.SDK_INT >= 34

        val target = prefs.targetLabel
        b.targetText.text = if (target.isNullOrBlank()) {
            "Automático: busca «modo de voz», «voz», «micrófono»… en Claude."
        } else {
            "Elegido: «$target»"
        }
        b.btnResetTarget.isVisible = !target.isNullOrBlank()

        val heard = EventLog.lastHeard
        b.heardText.text = if (heard.isEmpty()) "Aún no he oído nada." else "Último texto oído: «$heard»"
        b.logText.text = EventLog.snapshot().takeLast(40).reversed().joinToString("\n")
    }

    private fun check(ok: Boolean, text: String) = (if (ok) "✅  " else "⚠️  ") + text

    private fun setPermissionButton(button: MaterialButton, granted: Boolean, text: String) {
        button.text = if (granted) "✓ $text" else text
        button.isEnabled = !granted
    }
}
