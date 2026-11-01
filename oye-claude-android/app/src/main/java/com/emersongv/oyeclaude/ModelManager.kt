package com.emersongv.oyeclaude

import android.content.Context
import android.content.res.AssetManager
import java.io.File
import java.io.FileNotFoundException

/** Copia el modelo Vosk empaquetado en el APK (assets/model-es) al almacenamiento interno. */
object ModelManager {
    private const val ASSET_DIR = "model-es"

    private fun modelDir(ctx: Context) = File(ctx.filesDir, ASSET_DIR)
    private fun marker(ctx: Context) = File(modelDir(ctx), ".ok-${BuildConfig.VOSK_MODEL}")

    fun isReady(ctx: Context) = marker(ctx).exists()

    /** Devuelve la carpeta del modelo, copiándola primero si hace falta. Lento la primera vez. */
    @Synchronized
    fun ensure(ctx: Context): File {
        val dir = modelDir(ctx)
        if (marker(ctx).exists()) return dir
        val assets = ctx.assets
        if (assets.list(ASSET_DIR).isNullOrEmpty()) {
            throw FileNotFoundException("El APK no incluye el modelo Vosk (assets/$ASSET_DIR)")
        }
        EventLog.add("Copiando modelo de voz (solo la primera vez)…")
        dir.deleteRecursively()
        copy(assets, ASSET_DIR, dir)
        check(File(dir, "am/final.mdl").exists()) { "Modelo incompleto" }
        marker(ctx).createNewFile()
        EventLog.add("Modelo de voz listo")
        return dir
    }

    private fun copy(assets: AssetManager, path: String, dest: File) {
        val children = assets.list(path)
        if (children.isNullOrEmpty()) {
            dest.parentFile?.mkdirs()
            assets.open(path).use { input ->
                dest.outputStream().use { output -> input.copyTo(output, 64 * 1024) }
            }
        } else {
            dest.mkdirs()
            for (child in children) copy(assets, "$path/$child", File(dest, child))
        }
    }
}
