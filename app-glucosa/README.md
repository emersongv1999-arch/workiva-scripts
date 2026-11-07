# Diario de Glucosa

App para el teléfono para llevar el auto monitoreo de la glucosa (azúcar en la sangre).

## Qué hace

- **Registrar una medición** en segundos: valor del glucómetro, momento del día (ayunas, antes de comer, 2 h después de comer, antes de dormir, madrugada, otro), fecha y hora. Si quieres, también insulina, carbohidratos, etiquetas (ejercicio, estrés, enfermedad…) y una nota.
- **Resumen**: última medición con su estado (muy baja, baja, en objetivo, alta, muy alta), promedio, HbA1c estimada, % de mediciones en objetivo, número de bajas, variabilidad (CV), distribución por rangos y promedio por momento del día. Períodos de 7, 14, 30 y 90 días.
- **Avisos de seguridad**: si la última medición es baja, recuerda la regla 15-15; si es muy alta, sugiere seguir el plan del equipo de salud.
- **Historial** agrupado por día, con filtro por momento. Al tocar una medición se puede corregir o eliminar (con opción de deshacer).
- **Tendencias**: gráfico de evolución con la banda de objetivo, patrón por hora del día (detecta a qué horas sube o baja) y extremos del período.
- **Ajustes**: mg/dL o mmol/L; objetivos según referencia (diabetes ADA, sin diabetes/prediabetes, gestacional) o personalizados.
- **Para el médico**: exportar planilla CSV (separada por `;`, abre directo en Excel en español), copiar un resumen de 30 días, y respaldo/restauración en JSON.

Los colores de los rangos siguen la convención del informe AGP (rojo oscuro, rojo, verde, amarillo, naranjo). La tipografía es Atkinson Hyperlegible, diseñada para personas con baja visión.

## Instalar en Android (APK)

1. Descarga [`apk/DiarioGlucosa.apk`](apk/DiarioGlucosa.apk) en el teléfono.
2. Ábrelo desde la notificación de descarga o desde *Archivos › Descargas*.
3. Si Android avisa que no permite instalar apps de esa fuente, toca *Configuración*, activa *Permitir de esta fuente* y vuelve atrás.
4. Toca *Instalar*. Si aparece Play Protect diciendo que no reconoce la app, elige *Instalar de todas formas* (es normal en apps que no vienen de Play Store).
5. Busca el ícono **Glucosa** en tu pantalla de inicio.

Requiere Android 7 o superior. Funciona sin internet. Las mediciones quedan guardadas en el teléfono; desde *Ajustes › Descargar respaldo* puedes guardar una copia en Drive o enviártela por correo.

Para actualizar, instala el APK nuevo encima del anterior. Android solo lo acepta si está firmado con la misma clave que la versión instalada; si no, hay que desinstalar (y se pierden los datos), así que antes descarga un respaldo.

## Archivos

| Archivo | Para qué |
|---|---|
| `app.html` | Fuente única de la app (HTML + CSS + JS, sin dependencias). Se publica tal cual como Artifact en claude.ai. |
| `build.py` | Genera `index.html` (PWA) y `android/app/src/main/assets/www/` (APK) a partir de `app.html`. |
| `apk/DiarioGlucosa.apk` | Instalador para Android, listo para descargar. |
| `android/` | Proyecto Android: un WebView a pantalla completa que carga la app desde sus recursos, con un puente para guardar los datos en un archivo interno, exportar archivos y copiar texto. |
| `fonts/` | Fuentes Atkinson Hyperlegible para usar sin conexión (licencia OFL). |
| `index.html` | Versión PWA, generada. No editar a mano. |
| `manifest.webmanifest`, `sw.js`, `icon*` | Manifest, service worker (funciona sin conexión) e íconos de la PWA. |

## Dónde se guardan los datos

- **App Android (APK)**: en el teléfono, en un archivo interno de la app. Se borra si desinstalas la app, así que conviene descargar un respaldo de vez en cuando.
- **Abierta en claude.ai** (como Artifact): en tu cuenta, en un espacio privado que solo tú puedes ver. Se sincroniza entre el teléfono y el computador.
- **Instalada como PWA**: solo en ese teléfono/navegador (`localStorage`). Conviene descargar un respaldo de vez en cuando desde Ajustes.

## Compilar el APK

Requiere JDK 17+ y el SDK de Android (plataforma 35, build-tools 35).

```
python build.py
cd android
ANDROID_HOME=/ruta/al/android-sdk ./gradlew assembleRelease
cp app/build/outputs/apk/release/app-release.apk ../apk/DiarioGlucosa.apk
```

Antes de publicar una versión nueva, sube `versionCode` y `versionName` en `android/app/build.gradle`.

**Firma:** la clave no está en el repo. Para firmar con tu propia clave, crea `android/keystore/` con el archivo `.jks` y un `keystore.properties` (`storeFile`, `storePassword`, `keyAlias`, `keyPassword`); esa carpeta está en `.gitignore`. Sin ella, el APK se firma con la clave de depuración de la máquina que compila. Usa siempre la misma clave para que las actualizaciones se instalen encima sin perder datos.

## Instalar en el teléfono como PWA (iPhone o Android)

1. Publicar la carpeta `app-glucosa/` en un hosting estático con HTTPS (por ejemplo GitHub Pages).
2. Abrir la URL en el teléfono:
   - **Android (Chrome)**: menú ⋮ → *Instalar app* / *Agregar a la pantalla principal*.
   - **iPhone (Safari)**: botón Compartir → *Agregar a inicio*.

## Modificar la app

1. Editar `app.html`.
2. Ejecutar `python build.py` para regenerar la PWA y los recursos del APK.
3. Si cambian archivos de la PWA, subir la versión en `CACHE` dentro de `sw.js` para que los teléfonos descarguen la nueva versión.
4. Para el APK, compilar de nuevo (ver *Compilar el APK*).

> Registro personal. La HbA1c estimada es una aproximación a partir del promedio (fórmula ADAG) y no reemplaza el examen de laboratorio. La app no reemplaza las indicaciones del médico ni del equipo de salud.
