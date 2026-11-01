package com.emersongv.oyeclaude

import android.content.Context
import androidx.core.content.edit

/** Ajustes persistentes de la app. */
class Prefs(context: Context) {
    private val sp = context.applicationContext.getSharedPreferences("oye_claude", Context.MODE_PRIVATE)

    /** El usuario quiere que la escucha esté activa (se usa para reanudar tras reiniciar). */
    var listeningEnabled: Boolean
        get() = sp.getBoolean(K_ENABLED, false)
        set(v) = sp.edit { putBoolean(K_ENABLED, v) }

    var claudePackage: String
        get() = sp.getString(K_PACKAGE, null)?.trim().takeUnless { it.isNullOrEmpty() } ?: DEFAULT_CLAUDE_PACKAGE
        set(v) = sp.edit { putString(K_PACKAGE, v.trim()) }

    /** Palabras de activación ("oye"). */
    var triggerWords: List<String>
        get() = splitWords(sp.getString(K_TRIGGERS, null)).ifEmpty { WakeMatcher.DEFAULT_TRIGGERS }
        set(v) = sp.edit { putString(K_TRIGGERS, v.joinToString(", ")) }

    /** Formas en que el modelo puede escribir "Claude". */
    var nameVariants: List<String>
        get() = splitWords(sp.getString(K_VARIANTS, null)).ifEmpty { WakeMatcher.DEFAULT_VARIANTS }
        set(v) = sp.edit { putString(K_VARIANTS, v.joinToString(", ")) }

    /** Abrir Claude en un chat nuevo (enlace claude.ai/new) en vez de donde lo dejaste. */
    var openNewChat: Boolean
        get() = sp.getBoolean(K_NEW_CHAT, true)
        set(v) = sp.edit { putBoolean(K_NEW_CHAT, v) }

    var beepOnWake: Boolean
        get() = sp.getBoolean(K_BEEP, true)
        set(v) = sp.edit { putBoolean(K_BEEP, v) }

    /** Botón elegido por el usuario con el inspector (texto/descripción/id). Null = automático. */
    var targetLabel: String?
        get() = sp.getString(K_TARGET_LABEL, null)
        set(v) = sp.edit { putString(K_TARGET_LABEL, v) }

    /** Posición relativa (0..1) del botón elegido, como respaldo si la etiqueta cambia. */
    var targetX: Float
        get() = sp.getFloat(K_TARGET_X, -1f)
        set(v) = sp.edit { putFloat(K_TARGET_X, v) }

    var targetY: Float
        get() = sp.getFloat(K_TARGET_Y, -1f)
        set(v) = sp.edit { putFloat(K_TARGET_Y, v) }

    val hasTargetPoint: Boolean
        get() = targetX in 0f..1f && targetY in 0f..1f

    fun clearTarget() = sp.edit {
        remove(K_TARGET_LABEL)
        remove(K_TARGET_X)
        remove(K_TARGET_Y)
    }

    companion object {
        const val DEFAULT_CLAUDE_PACKAGE = "com.anthropic.claude"

        private const val K_ENABLED = "listening_enabled"
        private const val K_PACKAGE = "claude_package"
        private const val K_TRIGGERS = "trigger_words"
        private const val K_VARIANTS = "name_variants"
        private const val K_BEEP = "beep_on_wake"
        private const val K_NEW_CHAT = "open_new_chat"
        private const val K_TARGET_LABEL = "target_label"
        private const val K_TARGET_X = "target_x"
        private const val K_TARGET_Y = "target_y"

        fun splitWords(raw: String?): List<String> = WakeMatcher.normalize(raw?.split(',', ';', '\n') ?: emptyList())
    }
}
