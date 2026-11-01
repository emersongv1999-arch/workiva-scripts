package com.emersongv.oyeclaude

import android.graphics.Rect
import android.view.accessibility.AccessibilityNodeInfo
import java.text.Normalizer
import java.util.Locale

/** Un elemento de la pantalla de Claude que se puede tocar. */
data class UiCandidate(
    val label: String,
    val score: Int,
    /** Centro relativo a la ventana de Claude (0..1). */
    val relX: Float,
    val relY: Float,
)

/**
 * Busca el botón de voz en la ventana de Claude por su descripción de accesibilidad,
 * su texto o su id. Funciona con el teléfono en español o en inglés.
 */
object VoiceButtonFinder {
    private val STRONG = listOf(
        "modo de voz", "modo voz", "voice mode", "conversacion de voz", "voice conversation",
        "chat de voz", "voice chat", "iniciar voz", "start voice", "hablar con claude", "talk to claude",
    )
    private val MEDIUM = setOf("voz", "voice", "hablar", "speak", "talk")
    private val WEAK = setOf("dictar", "dictado", "dictation", "dictate", "microfono", "microphone", "mic")
    private val NEGATIVE = setOf(
        "ajustes", "ajuste", "configuracion", "settings", "setting", "detener", "stop", "cancelar", "cancel",
        "silenciar", "mute", "idioma", "language", "eliminar", "delete", "cerrar", "close",
    )

    private val NEW_CHAT = listOf(
        "nuevo chat", "chat nuevo", "new chat", "nueva conversacion", "new conversation",
        "iniciar un chat", "start new chat", "start a new chat",
    )

    private const val MAX_NODES = 3000

    class Found(val node: AccessibilityNodeInfo, val label: String)

    fun normalize(s: String): String =
        Normalizer.normalize(s, Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(Locale.ROOT)
            .replace('_', ' ')
            .trim()

    fun labelOf(node: AccessibilityNodeInfo): String {
        val parts = mutableListOf<String>()
        node.contentDescription?.toString()?.takeIf { it.isNotBlank() }?.let { parts += it.trim() }
        node.text?.toString()?.takeIf { it.isNotBlank() && it.length <= 60 }?.let { if (it.trim() !in parts) parts += it.trim() }
        node.viewIdResourceName?.substringAfter(":id/")?.takeIf { it.isNotBlank() }?.let { parts += "#$it" }
        return parts.joinToString(" · ")
    }

    fun score(label: String): Int {
        val l = normalize(label)
        if (l.isEmpty()) return 0
        val words = l.split(Regex("[^a-z0-9]+")).filter { it.isNotEmpty() }.toSet()
        var s = when {
            STRONG.any { l.contains(it) } -> 100
            words.any { it in MEDIUM } -> 60
            words.any { it in WEAK } -> 40
            else -> 0
        }
        if (s > 0 && words.any { it in NEGATIVE }) s -= 80
        return s
    }

    private fun visibleNodes(root: AccessibilityNodeInfo): List<AccessibilityNodeInfo> {
        val out = ArrayList<AccessibilityNodeInfo>()
        val stack = ArrayDeque<AccessibilityNodeInfo>()
        stack.addLast(root)
        while (stack.isNotEmpty() && out.size < MAX_NODES) {
            val n = stack.removeLast()
            if (n.isVisibleToUser) out += n
            for (i in n.childCount - 1 downTo 0) n.getChild(i)?.let { stack.addLast(it) }
        }
        return out
    }

    private fun isTappable(node: AccessibilityNodeInfo): Boolean {
        var n: AccessibilityNodeInfo? = node
        var depth = 0
        while (n != null && depth < 4) {
            if (n.isClickable && n.isEnabled) return true
            n = n.parent
            depth++
        }
        return false
    }

    /** Busca el botón guardado por el usuario; si no hay, el mejor candidato automático. */
    fun find(root: AccessibilityNodeInfo, savedLabel: String?): Found? {
        val nodes = visibleNodes(root)
        if (!savedLabel.isNullOrBlank()) {
            val wanted = normalize(savedLabel)
            nodes.firstOrNull { normalize(labelOf(it)) == wanted }?.let { return Found(it, labelOf(it)) }
            // La etiqueta guardada puede incluir el id: probamos también con la primera parte.
            val head = normalize(savedLabel.substringBefore(" · "))
            if (head.isNotEmpty()) {
                nodes.firstOrNull { normalize(labelOf(it)).startsWith(head) }?.let { return Found(it, labelOf(it)) }
            }
            return null
        }
        var best: AccessibilityNodeInfo? = null
        var bestScore = 0
        var bestLabel = ""
        for (n in nodes) {
            val label = labelOf(n)
            val s = score(label)
            if (s > bestScore && isTappable(n)) {
                best = n
                bestScore = s
                bestLabel = label
            }
        }
        return best?.let { Found(it, bestLabel) }
    }

    /** Botón para empezar un chat nuevo (cuando Claude se abrió en otra pantalla). */
    fun findNewChat(root: AccessibilityNodeInfo): Found? {
        for (n in visibleNodes(root)) {
            val label = labelOf(n)
            val l = normalize(label)
            if (l.isNotEmpty() && NEW_CHAT.any { l.contains(it) } && isTappable(n)) return Found(n, label)
        }
        return null
    }

    /** Lista de elementos tocables para que el usuario elija (inspector). */
    fun inspect(root: AccessibilityNodeInfo): List<UiCandidate> {
        val rootRect = Rect().also { root.getBoundsInScreen(it) }
        if (rootRect.width() <= 0 || rootRect.height() <= 0) return emptyList()
        val seen = HashSet<String>()
        val out = ArrayList<UiCandidate>()
        for (n in visibleNodes(root)) {
            val label = labelOf(n)
            if (label.isEmpty() || !isTappable(n) || !seen.add(label)) continue
            val r = Rect().also { n.getBoundsInScreen(it) }
            if (r.isEmpty) continue
            out += UiCandidate(
                label = label,
                score = score(label),
                relX = ((r.exactCenterX() - rootRect.left) / rootRect.width()).coerceIn(0f, 1f),
                relY = ((r.exactCenterY() - rootRect.top) / rootRect.height()).coerceIn(0f, 1f),
            )
        }
        return out.sortedWith(compareByDescending<UiCandidate> { it.score }.thenByDescending { it.relY }).take(80)
    }
}
