# Oye Claude (Android)

App Android en Kotlin que escucha **«Oye Claude»** en segundo plano con
[Vosk](https://alphacephei.com/vosk/) y el modelo pequeño en español
(`vosk-model-small-es-0.42`, sin conexión a internet). Cuando oye la frase:

1. suelta el micrófono, emite un pitido y vibra,
2. enciende la pantalla y **pide desbloquear** (PIN, huella o cara),
3. **abre la app de Claude** (`com.anthropic.claude`),
4. **toca el botón de voz** mediante el servicio de accesibilidad,
5. vuelve a escuchar cuando sales de Claude y nadie más usa el micrófono.

## Descargar el APK en el teléfono

Cada push que cambia `oye-claude-android/` compila el APK con GitHub Actions
(`.github/workflows/oye-claude-apk.yml`) y lo publica en dos sitios:

- **Enlace directo (recomendado):**
  `https://github.com/emersongv1999-arch/workiva-scripts/releases/download/oye-claude-latest/OyeClaude.apk`
  Ábrelo en el navegador del teléfono y se descarga el `.apk`.
- **Artefacto de Actions:** pestaña *Actions* → ejecución «Oye Claude APK» →
  *Artifacts* → `OyeClaude-apk` (viene en un `.zip` y hay que iniciar sesión en GitHub).

## Instalar y configurar

1. Abre `OyeClaude.apk` desde Descargas. Si Android lo pide, permite
   «Instalar apps desconocidas» para el navegador o el gestor de archivos.
   Si aparece Play Protect, elige «Instalar de todas formas».
2. Abre **Oye Claude** y, en la tarjeta *Permisos*:
   - **Permitir micrófono** y **Permitir notificaciones**.
   - **Activar accesibilidad** → *Oye Claude: botón de voz* → activar.
     En Android 13 o superior saldrá «Ajuste restringido»: toca
     **Abrir Info de la app** → menú **⋮** (arriba a la derecha) →
     **Permitir ajustes restringidos**, y vuelve a activar la accesibilidad.
   - **Quitar optimización de batería**, para que Android no cierre la escucha.
   - **Mostrar sobre otras apps**: recomendado, ayuda a abrir Claude desde segundo plano
     (en Xiaomi activa también «Mostrar ventanas emergentes en segundo plano» y «Inicio automático»).
3. Activa el interruptor **Escuchar «Oye Claude»**. Aparecerá una notificación
   fija (Android la exige para usar el micrófono en segundo plano).
4. Pulsa **Probar ahora (sin hablar)** para comprobar que Claude se abre y se toca
   el botón de voz. Después prueba diciendo «Oye Claude» con una pausa breve al final.

### Si vibra pero no se abre nada

Android solo deja abrir pantallas desde segundo plano a una app que tenga una
ventana visible. Por eso, justo antes de abrir, Oye Claude muestra una ventana
invisible de 1 px usando la **accesibilidad** (o «Mostrar sobre otras apps»).
Comprueba en la app que la accesibilidad tenga ✅. En *Registro* verás con qué
método intentó abrir y si Android lo bloqueó. En Xiaomi/HyperOS activa además
«Mostrar ventanas emergentes en segundo plano».

### Si toca el botón equivocado o no lo encuentra

La app busca automáticamente un botón cuya descripción contenga «modo de voz»,
«voice mode», «voz», «micrófono», etc. Si no acierta:

1. *Botón de voz de Claude* → **Elegir botón de voz** → **Abrir Claude**.
2. En Claude, ve a la pantalla donde se ve el botón de voz (por ejemplo, un chat nuevo).
3. Vuelve a Oye Claude: aparece la lista de botones detectados (★ = probable botón de voz).
   Elige el correcto. Se guarda su nombre y su posición como respaldo.

## Ajustes avanzados

- **Paquete de la app de Claude**: `com.anthropic.claude` por defecto.
- **Palabra de activación**: `oye` (se pueden poner varias separadas por comas).
- **Cómo puede oír «Claude»**: `claude, cloud, claudio`. El modelo pequeño escribe
  así las pronunciaciones más comunes («clod», «claud»). Mira *Registro → Último texto oído*
  para ver qué entiende cuando lo dices y añade esa palabra si hace falta.

La detección usa una gramática restringida con palabras «señuelo» (claro, clara,
loco…) y solo resultados finales. En pruebas con voces sintéticas en español
detectó 42/42 frases «Oye Claude» con 0 falsos positivos en 132 frases parecidas
(«oye claro», «oye, clara», «oye loco»…). Con voces reales puede variar.

## Limitaciones

- Mientras estás en Claude, Oye Claude no escucha (deja el micrófono libre para Claude).
- Tras reiniciar el teléfono, la escucha se reanuda sola si la accesibilidad está
  activa; si no, aparece una notificación para reactivarla con un toque.
- El reconocimiento continuo gasta algo de batería.
- La interfaz de Claude puede cambiar; si deja de encontrar el botón, vuelve a elegirlo.
- El APK se firma con `app/oyeclaude.keystore` (incluido a propósito para que las
  actualizaciones se instalen encima). Como el repo es público, instala solo el APK
  de este repositorio.

## Compilar en local

Requisitos: JDK 17+ y Android SDK (`sdk.dir` en `local.properties` o `ANDROID_HOME`).

```bash
cd oye-claude-android
./gradlew testReleaseUnitTest assembleRelease
# APK: app/build/outputs/apk/release/app-release.apk
```

La primera compilación descarga el modelo Vosk (~40 MB) en
`app/src/main/assets/model-es/` (ignorado por git).

## Estructura

| Archivo | Qué hace |
|---|---|
| `WakeWordService.kt` | Servicio en primer plano: micrófono → Vosk → detección; pausa y reanuda |
| `WakeMatcher.kt` | Gramática de Vosk y coincidencia «oye» + variante de «claude» |
| `WakeLauncher.kt` | Enciende la pantalla y abre la pantalla de desbloqueo (con notificación de respaldo) |
| `UnlockActivity.kt` | Pantalla invisible sobre la pantalla de bloqueo: pide desbloquear y abre Claude |
| `ClaudeAccessibilityService.kt` | Toca el botón de voz, detecta la app en primer plano y captura botones para el inspector |
| `VoiceButtonFinder.kt` | Puntúa los elementos de la pantalla para encontrar el botón de voz |
| `MainActivity.kt` | Configuración, permisos, prueba e inspector |
| `ModelManager.kt` | Copia el modelo desde el APK al almacenamiento interno |
