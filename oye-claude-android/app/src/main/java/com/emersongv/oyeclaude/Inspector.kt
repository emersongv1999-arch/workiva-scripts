package com.emersongv.oyeclaude

/** Estado del inspector: captura los botones visibles de Claude para que elijas el de voz. */
object Inspector {
    @Volatile
    var active = false

    @Volatile
    var items: List<UiCandidate> = emptyList()

    fun begin() {
        items = emptyList()
        active = true
    }
}
