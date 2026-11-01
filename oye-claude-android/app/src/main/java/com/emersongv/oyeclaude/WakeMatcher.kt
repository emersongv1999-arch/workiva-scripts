package com.emersongv.oyeclaude

import org.json.JSONArray
import java.util.Locale

/**
 * Gramática restringida para Vosk y detección de la frase "oye claude".
 *
 * El modelo pequeño de español sí conoce "claude", pero según la pronunciación
 * puede escribir "cloud" o "claudio". Para reducir falsos positivos la gramática
 * incluye palabras "señuelo" frecuentes (claro, clara, loco, …): así "oye claro"
 * se reconoce como tal y no como "oye claude". Solo se activa con resultados
 * finales (tras una pausa breve), que en pruebas dieron 0 falsos positivos.
 */
object WakeMatcher {
    val DEFAULT_TRIGGERS = listOf("oye")
    val DEFAULT_VARIANTS = listOf("claude", "cloud", "claudio")

    private val DECOYS = listOf(
        "claro", "clara", "clase", "clave", "cloro", "loco", "lo", "los", "la", "las", "le",
        "cuando", "cuanto", "cuánto", "como", "cómo", "cosa", "cierra", "claudia", "colócalo",
        "llama", "llámame", "calma", "cálmate", "tienes", "dijo", "todo", "ven", "la llave",
        "que", "qué", "y", "tu", "con", "cola", "coca", "ola", "hola", "o", "ya", "acá", "ahí",
        "bien", "clic", "clan", "club", "globo", "flor", "flojo", "golpe", "oro", "pues",
        "mira", "escucha", "oiga",
    )

    fun normalize(words: List<String>): List<String> =
        words.map { it.trim().lowercase(Locale.ROOT) }.filter { it.isNotEmpty() }.distinct()

    fun grammar(triggers: List<String>, variants: List<String>): String {
        val phrases = LinkedHashSet<String>()
        for (t in triggers) for (v in variants) phrases += "$t $v"
        phrases += triggers
        phrases += variants
        phrases += DECOYS
        val arr = JSONArray()
        phrases.forEach { arr.put(it) }
        arr.put("[unk]")
        return arr.toString()
    }

    fun matches(text: String, triggers: List<String>, variants: List<String>): Boolean {
        val tokens = text.lowercase(Locale.ROOT).split(' ', '\t', '\n').filter { it.isNotEmpty() }
        for (i in 0 until tokens.size - 1) {
            if (tokens[i] in triggers && tokens[i + 1] in variants) return true
        }
        return false
    }
}
