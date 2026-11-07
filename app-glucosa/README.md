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

## Archivos

| Archivo | Para qué |
|---|---|
| `app.html` | Fuente única de la app (HTML + CSS + JS, sin dependencias). Se publica tal cual como Artifact en claude.ai. |
| `build.py` | Genera `index.html` (PWA instalable) a partir de `app.html`. |
| `index.html` | Versión instalable, generada. No editar a mano. |
| `manifest.webmanifest`, `sw.js`, `icon*` | Manifest, service worker (funciona sin conexión) e íconos de la PWA. |

## Dónde se guardan los datos

- **Abierta en claude.ai** (como Artifact): en tu cuenta, en un espacio privado que solo tú puedes ver. Se sincroniza entre el teléfono y el computador.
- **Instalada como PWA**: solo en ese teléfono/navegador (`localStorage`). Conviene descargar un respaldo de vez en cuando desde Ajustes.

## Instalar en el teléfono (PWA)

1. Publicar la carpeta `app-glucosa/` en un hosting estático con HTTPS (por ejemplo GitHub Pages).
2. Abrir la URL en el teléfono:
   - **Android (Chrome)**: menú ⋮ → *Instalar app* / *Agregar a la pantalla principal*.
   - **iPhone (Safari)**: botón Compartir → *Agregar a inicio*.

## Modificar la app

1. Editar `app.html`.
2. Ejecutar `python build.py` para regenerar `index.html`.
3. Si cambian archivos de la PWA, subir la versión en `CACHE` dentro de `sw.js` para que los teléfonos descarguen la nueva versión.

> Registro personal. La HbA1c estimada es una aproximación a partir del promedio (fórmula ADAG) y no reemplaza el examen de laboratorio. La app no reemplaza las indicaciones del médico ni del equipo de salud.
