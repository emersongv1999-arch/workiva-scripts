const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, PageBreak, Footer, PageNumber, convertInchesToTwip
} = require("docx");

const AZUL = "1F3864";
const AZUL2 = "2E5C9A";
const GRIS = "F2F5FA";
const GRISB = "D9E1F2";
const ROJO = "9C1B1B";
const W = 10080; // ancho util en DXA (Carta con margenes 0.75")

/* ---------- helpers ---------- */
const P = (text, opts = {}) => new Paragraph({
  spacing: { after: opts.after === undefined ? 120 : opts.after, line: 276 },
  alignment: opts.align,
  indent: opts.indent,
  children: [new TextRun({ text, bold: opts.bold, italics: opts.italics, size: opts.size || 21, color: opts.color, font: "Calibri" })],
});

const Prich = (runs, opts = {}) => new Paragraph({
  spacing: { after: opts.after === undefined ? 120 : opts.after, line: 276 },
  indent: opts.indent,
  children: runs.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, size: r.size || 21, color: r.color, font: r.font || "Calibri" })),
});

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 320, after: 160 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: AZUL2, space: 4 } },
  children: [new TextRun({ text, bold: true, size: 30, color: AZUL, font: "Calibri" })],
});

const H2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 260, after: 120 },
  children: [new TextRun({ text, bold: true, size: 25, color: AZUL2, font: "Calibri" })],
});

const H3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  spacing: { before: 200, after: 100 },
  children: [new TextRun({ text, bold: true, size: 22, color: "333333", font: "Calibri" })],
});

const BUL = (text, level = 0) => new Paragraph({
  numbering: { reference: "vinetas", level },
  spacing: { after: 80, line: 276 },
  children: [new TextRun({ text, size: 21, font: "Calibri" })],
});

const NUM = (text, ref = "pasos") => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 90, line: 276 },
  children: [new TextRun({ text, size: 21, font: "Calibri" })],
});

const NUMrich = (runs, ref = "pasos") => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 90, line: 276 },
  children: runs.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, size: 21, font: "Calibri", color: r.color })),
});

const cell = (content, width, opts = {}) => new TableCell({
  width: { size: width, type: WidthType.DXA },
  shading: opts.shading ? { type: ShadingType.CLEAR, fill: opts.shading, color: "auto" } : undefined,
  margins: { top: 80, bottom: 80, left: 110, right: 110 },
  children: (Array.isArray(content) ? content : [content]).map(t =>
    typeof t === "string"
      ? new Paragraph({ spacing: { after: 0, line: 260 }, children: [new TextRun({ text: t, bold: opts.bold, size: 19, color: opts.color, font: "Calibri" })] })
      : t),
});

const tabla = (widths, header, rows) => new Table({
  columnWidths: widths,
  width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
  borders: {
    top: { style: BorderStyle.SINGLE, size: 4, color: "AAB7CE" },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: "AAB7CE" },
    left: { style: BorderStyle.SINGLE, size: 4, color: "AAB7CE" },
    right: { style: BorderStyle.SINGLE, size: 4, color: "AAB7CE" },
    insideHorizontal: { style: BorderStyle.SINGLE, size: 4, color: "AAB7CE" },
    insideVertical: { style: BorderStyle.SINGLE, size: 4, color: "AAB7CE" },
  },
  rows: [
    new TableRow({
      tableHeader: true,
      children: header.map((h, i) => cell(h, widths[i], { shading: GRISB, bold: true, color: AZUL })),
    }),
    ...rows.map((r, ri) => new TableRow({
      children: r.map((c, i) => cell(c, widths[i], { shading: ri % 2 ? GRIS : undefined })),
    })),
  ],
});

const nota = (titulo, texto, color) => new Table({
  columnWidths: [W],
  width: { size: W, type: WidthType.DXA },
  borders: {
    top: { style: BorderStyle.SINGLE, size: 4, color: color },
    bottom: { style: BorderStyle.SINGLE, size: 4, color: color },
    left: { style: BorderStyle.SINGLE, size: 24, color: color },
    right: { style: BorderStyle.SINGLE, size: 4, color: color },
    insideHorizontal: { style: BorderStyle.NONE },
    insideVertical: { style: BorderStyle.NONE },
  },
  rows: [new TableRow({
    children: [cell([
      new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: titulo, bold: true, size: 20, color: color, font: "Calibri" })] }),
      new Paragraph({ spacing: { after: 0, line: 260 }, children: [new TextRun({ text: texto, size: 20, font: "Calibri" })] }),
    ], W, { shading: "FBFCFE" })],
  })],
});

const SP = (h = 120) => new Paragraph({ spacing: { after: h }, children: [] });

/* ---------- contenido ---------- */
const doc = new Document({
  creator: "Auditoría CGE",
  title: "Guía para hacer copias en Workiva",
  description: "Procedimiento detallado de copia de archivos, carpetas y roll forward en Workiva",
  numbering: {
    config: [
      { reference: "vinetas", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 250 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 900, hanging: 250 } } } },
      ]},
      { reference: "pasos", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 300 } } } },
      ]},
      { reference: "pasosB", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 300 } } } },
      ]},
      { reference: "pasosC", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 300 } } } },
      ]},
      { reference: "pasosD", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 300 } } } },
      ]},
      { reference: "check", levels: [
        { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 300 } } } },
      ]},
    ],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "Guía de copias en Workiva — CGE   |   Página ", size: 17, color: "777777", font: "Calibri" }),
                     new TextRun({ children: [PageNumber.CURRENT], size: 17, color: "777777", font: "Calibri" }),
                     new TextRun({ text: " de ", size: 17, color: "777777", font: "Calibri" }),
                     new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 17, color: "777777", font: "Calibri" })],
        })],
      }),
    },
    children: [
      /* ---- portada ---- */
      SP(600),
      new Paragraph({ spacing: { after: 60 }, alignment: AlignmentType.LEFT,
        children: [new TextRun({ text: "PROCEDIMIENTO DE AUDITORÍA — CGE", bold: true, size: 20, color: AZUL2, font: "Calibri" })] }),
      new Paragraph({ spacing: { after: 120 },
        children: [new TextRun({ text: "Cómo hacer copias en Workiva", bold: true, size: 52, color: AZUL, font: "Calibri" })] }),
      new Paragraph({ spacing: { after: 300 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: AZUL2, space: 6 } },
        children: [new TextRun({ text: "Guía detallada de copia de archivos, carpetas y roll forward de período, con todas las opciones que hay que marcar en cada caso", size: 24, color: "444444", font: "Calibri" })] }),
      SP(200),
      tabla([2600, 7480], ["Campo", "Detalle"], [
        ["Documento", "Guía operativa de copias en Workiva (Home / Archivos)"],
        ["Dirigido a", "Equipo de auditoría y preparación de EE.FF. de CGE que trabaja en Workiva"],
        ["Alcance", "Copia de archivos y carpetas dentro del mismo workspace, roll forward de período y copia entre workspaces"],
        ["Versión", "1.0"],
        ["Fecha", "Agosto 2026"],
      ]),
      SP(240),
      nota("Antes de empezar", "Los nombres de las opciones que aparecen en pantalla pueden variar levemente según el idioma del workspace y la versión de Workiva. En esta guía cada opción se indica primero en español y luego, entre paréntesis, con su nombre original en inglés, que es como aparece en la mayoría de los workspaces de CGE.", AZUL2),

      new Paragraph({ children: [new PageBreak()] }),

      /* ---- indice ---- */
      H1("Contenido"),
      ...[
        "1. Para qué sirve copiar en Workiva",
        "2. Conceptos que hay que tener claros antes de copiar",
        "3. Permisos necesarios",
        "4. Los cuatro tipos de copia y cuándo usar cada uno",
        "5. Procedimiento A — Copiar un archivo individual",
        "6. Las opciones de copia explicadas una por una",
        "7. Procedimiento B — Copiar una carpeta completa (roll forward de período)",
        "8. Procedimiento C — Copiar o mover a otro workspace",
        "9. Matriz de decisión rápida",
        "10. Checklist posterior a la copia",
        "11. Errores frecuentes y cómo resolverlos",
        "12. Consideraciones específicas para los EE.FF. de CGE y el Auditor",
        "13. Glosario",
        "14. Referencias",
      ].map(t => new Paragraph({ spacing: { after: 70 }, indent: { left: 200 }, children: [new TextRun({ text: t, size: 21, font: "Calibri", color: "333333" })] })),

      /* ---- 1 ---- */
      H1("1. Para qué sirve copiar en Workiva"),
      P("Copiar en Workiva no es lo mismo que copiar un archivo en el explorador de Windows. Un archivo de Workiva (Documento, Planilla o Presentación) no es solo contenido: también arrastra comentarios, tareas, permisos, historial de revisiones, etiquetas de esquema, marcado XBRL y —lo más importante para EE.FF.— una red de enlaces (links) hacia y desde otros archivos. Al copiar, usted decide qué parte de todo eso viaja con la copia."),
      P("Los usos típicos en el trabajo de CGE son:"),
      BUL("Roll forward: partir del cierre anterior (por ejemplo 12-2025) para armar el cierre siguiente (06-2026) sin rehacer estructura ni enlaces."),
      BUL("Crear una versión de trabajo o de respaldo antes de un cambio grande, sin tocar el archivo oficial."),
      BUL("Generar una variante del entregable (por ejemplo la versión “Resumido” de un EE.FF.) a partir del archivo completo."),
      BUL("Replicar la estructura de una sociedad hacia otra (por ejemplo usar E205 como base para E211)."),
      BUL("Llevar un archivo a otro workspace de la organización."),
      SP(60),
      nota("La decisión crítica es una sola", "En todo el cuadro de opciones, la que realmente puede arruinar un cierre es la de enlaces (Links and process references). Elegir mal ahí deja los comparativos apuntando al archivo equivocado o congelados en valores viejos. Las demás opciones son cómodas de corregir después; esa no.", ROJO),

      /* ---- 2 ---- */
      H1("2. Conceptos que hay que tener claros antes de copiar"),
      tabla([2600, 7480], ["Concepto", "Qué significa en la práctica"], [
        ["Archivo", "Un Documento (.docx en Workiva), una Planilla (Spreadsheet) o una Presentación. Es la unidad que se copia."],
        ["Carpeta", "Contenedor de archivos en Home. Se puede copiar completa, y es la forma recomendada de hacer roll forward."],
        ["Workspace", "El espacio de trabajo (por ejemplo el de CGE). Los enlaces solo funcionan entre archivos del mismo workspace."],
        ["Archivo fuente (source)", "El archivo que entrega el dato: balances, EERR, insumos con prefijo (CHN) o (LC) en la nomenclatura de CGE."],
        ["Archivo destino (destination)", "El archivo que recibe el dato mediante un enlace: típicamente el EE.FF. sin prefijo."],
        ["Link (enlace)", "Conexión viva entre una celda o sección fuente y su destino. Se actualiza cuando la fuente se publica (Publish)."],
        ["Último valor publicado", "El valor que quedó congelado en el destino tras el último Publish. Es lo que queda si se elimina el enlace."],
        ["Historial de revisiones", "Bitácora de versiones del archivo. La copia siempre parte con historial en blanco."],
        ["Etiquetas de esquema", "Los puntos de colores del Document Outline que marcan estado de avance (Outline labels)."],
        ["Document Health", "Panel que reporta enlaces rotos, fechas desactualizadas y otros problemas. Se revisa siempre después de copiar."],
      ]),

      /* ---- 3 ---- */
      H1("3. Permisos necesarios"),
      P("Si no ve la opción “Copiar” en el menú, casi siempre es un tema de permisos, no un error del sistema."),
      tabla([3000, 7080], ["Para hacer esto", "Necesita"], [
        ["Copiar un archivo dentro del mismo workspace", "Permiso de Propietario (Owner) o Editor sobre el archivo, y al menos permiso de escritura sobre la carpeta destino."],
        ["Copiar una carpeta completa", "Permiso sobre la carpeta y sobre todos los archivos que contiene. Los archivos sobre los que no tiene permiso no se copian."],
        ["Incluir copias de los archivos fuente", "Permiso de lectura sobre cada archivo fuente que se va a copiar; si falta uno, ese enlace no se recrea."],
        ["Copiar o mover a otro workspace", "Ser Workspace Owner, Copy Manager o Content Manager en el workspace de origen, y tener acceso al workspace de destino."],
        ["Conservar los permisos al copiar entre workspaces", "Rol de Workspace Owner, Copy Manager o Content Manager (es quien ve la opción “Copy permissions from the source workspace”)."],
      ]),
      SP(60),
      nota("Ojo con la propiedad del archivo", "Quien ejecuta la copia queda como propietario de los archivos copiados. Si copia un cierre completo, todos los archivos nuevos quedarán a su nombre: avise al equipo y reasigne propietarios si su procedimiento interno lo exige.", AZUL2),

      /* ---- 4 ---- */
      H1("4. Los cuatro tipos de copia y cuándo usar cada uno"),
      tabla([2300, 4200, 3580], ["Tipo", "Qué hace", "Cuándo usarlo"], [
        ["Copia de archivo individual", "Duplica un solo archivo dentro del mismo workspace.", "Respaldo puntual, versión de prueba, variante “Resumido”."],
        ["Copia de carpeta", "Duplica la carpeta y todo su contenido, resolviendo los enlaces internos entre los archivos copiados.", "Roll forward de un cierre completo. Es el método recomendado para EE.FF."],
        ["Roll forward", "No es un botón distinto: es una copia de carpeta con la opción de enlaces bien elegida, seguida de renombrar y actualizar fechas.", "Paso de un período al siguiente (12-2025 → 06-2026)."],
        ["Copia a otro workspace", "Deja el original intacto y crea el duplicado en otro workspace de la organización.", "Migraciones, entrega a otra unidad, ambientes de prueba."],
      ]),
      SP(80),
      nota("Regla de oro de los enlaces", "Copie junto, en una sola operación, todo lo que está enlazado entre sí. Si copia el EE.FF. hoy y mañana copia su balance fuente por separado, la segunda copia no se enlaza sola: el EE.FF. copiado seguirá apuntando al balance del período anterior y habrá que rehacer los enlaces a mano.", ROJO),

      /* ---- 5 ---- */
      H1("5. Procedimiento A — Copiar un archivo individual"),
      P("Aplica cuando necesita duplicar un solo archivo dentro del mismo workspace."),
      NUM("Entre a Workiva y vaya a Home (Archivos). Ubique el archivo en la carpeta donde está guardado.", "pasos"),
      NUMrich([{ t: "Haga clic en el menú de tres puntos a la derecha del archivo —o clic derecho sobre él— y seleccione " }, { t: "Copiar (Copy)", b: true }, { t: ". También puede marcar la casilla del archivo y usar el botón Copiar de la barra superior." }], "pasos"),
      NUMrich([{ t: "En la ventana de copia, revise la lista de archivos seleccionados y confirme con " }, { t: "Siguiente (Next)", b: true }, { t: "." }], "pasos"),
      NUMrich([{ t: "Elija la " }, { t: "carpeta destino", b: true }, { t: ". Por defecto Workiva propone la misma carpeta del original; para un roll forward conviene crear antes una subcarpeta del período." }], "pasos"),
      NUMrich([{ t: "Defina el " }, { t: "nombre de la copia", b: true }, { t: ". Si deja el nombre por defecto quedará como “Copia de …”; respete siempre la nomenclatura de CGE (ver capítulo 12)." }], "pasos"),
      NUMrich([{ t: "Configure las " }, { t: "opciones de copia (Copy settings)", b: true }, { t: ": comentarios, etiquetas de esquema y —sobre todo— enlaces. El detalle está en el capítulo 6." }], "pasos"),
      NUMrich([{ t: "Presione " }, { t: "Copiar (Copy)", b: true }, { t: ". El proceso corre en segundo plano: puede seguir trabajando en Workiva mientras tanto." }], "pasos"),
      NUM("Espere la notificación en pantalla y el correo con el enlace a los archivos copiados. En cierres completos esto puede tardar varios minutos.", "pasos"),
      NUM("Abra la copia y ejecute el checklist del capítulo 10 antes de empezar a trabajar en ella.", "pasos"),

      /* ---- 6 ---- */
      new Paragraph({ children: [new PageBreak()] }),
      H1("6. Las opciones de copia explicadas una por una"),
      P("Este es el corazón del procedimiento: el cuadro “Opciones de copia” (Copy settings) que aparece antes de confirmar. A continuación se explica cada casilla, qué pasa si la marca, qué pasa si no la marca y qué se recomienda para el trabajo de EE.FF. de CGE."),

      H2("6.1 Nombre de la copia"),
      P("Campo de texto libre. Workiva propone “Copia de <nombre>”. Cámbielo en este momento: renombrar después es posible, pero si el archivo ya quedó enlazado o notificado por correo con el nombre equivocado se presta para confusiones."),
      BUL("Mantenga el código de sociedad al inicio (E110, E200, E205, E211, E215, E230, E244, E514, …)."),
      BUL("Mantenga los prefijos (CHN) y (LC) exactamente como estaban en el original."),
      BUL("Actualice solo la parte del período: “EE.FF 12-2025” → “EE.FF 06-2026”."),

      H2("6.2 Carpeta destino"),
      P("Define dónde queda la copia. Recomendación para roll forward: cree primero una subcarpeta con el período (clic derecho sobre la carpeta → Nueva subcarpeta / New Subfolder) y copie hacia ahí. Así evita mezclar dos cierres en la misma carpeta, que es la principal causa de que alguien edite el archivo equivocado."),

      H2("6.3 Comentarios (All comments)"),
      tabla([2000, 8080], ["Estado", "Efecto"], [
        ["Marcada", "Se copian todos los comentarios del archivo, tanto los abiertos como los ya resueltos, con su hilo de respuestas."],
        ["Desmarcada", "La copia parte sin ningún comentario. El original conserva los suyos."],
      ]),
      Prich([{ t: "Recomendación CGE: ", b: true }, { t: "desmarcada para roll forward de período (los comentarios del cierre anterior ya no aplican y ensucian la revisión). Marcada cuando la copia es un respaldo o una versión de trabajo del mismo cierre y quiere conservar la discusión." }]),

      H2("6.4 Etiquetas de esquema (Outline labels)"),
      tabla([2000, 8080], ["Estado", "Efecto"], [
        ["Marcada", "Se copian los puntos de color del Document Outline, incluidos los conjuntos de etiquetas personalizados del workspace."],
        ["Desmarcada", "La copia queda sin etiquetas: todas las secciones parten “en blanco”, sin estado de avance."],
      ]),
      Prich([{ t: "Recomendación CGE: ", b: true }, { t: "desmarcada en roll forward, porque el avance del cierre anterior no representa el avance del nuevo y puede hacer creer que una nota ya está revisada. Marcada si está clonando el archivo para seguir trabajando en el mismo cierre." }]),

      H2("6.5 Enlaces y referencias de proceso (Links and process references)"),
      P("Esta opción decide de dónde tomarán sus datos los archivos copiados. Si copia un proceso, además determina si las acciones del proceso copiado conservan las referencias a archivos y secciones. Tiene tres resultados posibles:"),
      H3("Opción 1 — Crear copias de todos los archivos fuente (Create copies of all source files)"),
      P("Workiva copia también todos los archivos que alimentan a su selección, y reapunta los enlaces de la copia hacia esas nuevas fuentes. Queda un juego de archivos completo e independiente: puede cambiar fechas y cifras sin tocar nada del período original."),
      BUL("Úsela en el roll forward de cierre: es la opción correcta en la gran mayoría de los casos de CGE."),
      BUL("Requiere permiso sobre los archivos fuente; los que no tenga no se copiarán."),
      BUL("Genera más archivos y demora más: es esperable en un cierre completo."),
      H3("Opción 2 — Mantener los enlaces a los archivos fuente originales (Keep links to original source files)"),
      P("No se copian las fuentes. Los archivos nuevos quedan enlazados a las fuentes originales, es decir, siguen leyendo del mismo balance o insumo de siempre."),
      BUL("Úsela cuando la fuente es un archivo único y permanente que no se versiona por período (una maestra de parámetros, un catálogo de cuentas)."),
      BUL("No la use en roll forward: los EE.FF. del período nuevo quedarían leyendo cifras del período anterior, y peor aún, cuando alguien actualice esa fuente cambiarán también los dos períodos."),
      H3("Opción 3 — Casilla desmarcada (sin enlaces)"),
      P("Se ignora cualquier fuente que esté fuera de la selección y esos enlaces se eliminan en la copia. El archivo copiado conserva los números del último valor publicado, pero congelados: no vuelven a actualizarse nunca."),
      BUL("Sirve para una foto histórica, una versión de solo lectura o un archivo que se enviará fuera de Workiva."),
      BUL("No sirve para trabajar: al perder los enlaces también pierde la trazabilidad hacia el balance."),
      SP(60),
      tabla([2900, 3600, 3580], ["Elección", "Resultado en los datos", "Escenario típico CGE"], [
        ["Crear copias de todos los archivos fuente", "Juego nuevo, independiente y enlazado entre sí.", "Roll forward 12-2025 → 06-2026. Opción por defecto recomendada."],
        ["Mantener enlaces a las fuentes originales", "La copia lee del mismo origen que el archivo original.", "Fuente maestra única que no cambia por período."],
        ["Desmarcada (sin enlaces)", "Valores congelados del último Publish, sin actualización.", "Respaldo histórico o entrega puntual fuera de Workiva."],
      ]),

      H2("6.6 Permisos e historial (se aplican solos)"),
      P("Estas dos no son casillas que se marquen, pero conviene conocerlas porque forman parte del resultado:"),
      BUL("Permisos: la copia conserva la configuración de permisos del archivo original dentro del mismo workspace."),
      BUL("Historial de revisiones: siempre se reinicia. La copia no arrastra el historial del original, así que no busque en ella las versiones del cierre anterior."),
      BUL("Tareas y control de cambios (track changes): no viajan a la copia."),

      H2("6.7 Opción exclusiva de copia entre workspaces"),
      Prich([{ t: "Copiar permisos del workspace de origen (Copy permissions from the source workspace): ", b: true }, { t: "solo aparece al copiar hacia otro workspace de la misma organización. Al marcarla, los usuarios que existen en ambos workspaces reciben el mismo nivel de permiso sobre el contenido copiado. Los usuarios que no existen en el workspace de destino no se agregan, y los permisos otorgados a grupos no se copian: esos hay que reconstruirlos a mano." }]),

      /* ---- 7 ---- */
      new Paragraph({ children: [new PageBreak()] }),
      H1("7. Procedimiento B — Copiar una carpeta completa (roll forward de período)"),
      P("Este es el procedimiento que debe usarse para pasar de un cierre al siguiente. Copiar la carpeta completa permite que los archivos conserven los enlaces entre ellos, en lugar de crear versiones nuevas y volver a enlazarlas una por una."),
      H2("Antes de copiar"),
      BUL("Verifique que el cierre anterior esté publicado (Publish) y sin enlaces rotos: lo que esté roto en el origen se copia roto."),
      BUL("Pida que nadie tenga archivos abiertos en edición durante la copia."),
      BUL("Confirme que la carpeta contiene todo lo que debe viajar: EE.FF., insumos (CHN) y (LC), anexos y planillas de apoyo."),
      BUL("Acuerde con el equipo la nomenclatura del período nuevo antes de empezar."),
      H2("Pasos"),
      NUM("En Home, ubique la carpeta del período que servirá de base (por ejemplo la del cierre 12-2025).", "pasosB"),
      NUM("Como buena práctica, cree primero la subcarpeta donde vivirá el período nuevo: clic derecho sobre la carpeta contenedora → Nueva subcarpeta (New Subfolder).", "pasosB"),
      NUMrich([{ t: "Clic derecho sobre la carpeta base → " }, { t: "Copiar (Copy)", b: true }, { t: "." }], "pasosB"),
      NUM("Revise la lista de archivos incluidos. Si falta alguno, lo más probable es que usted no tenga permisos sobre él: resuélvalo antes de continuar.", "pasosB"),
      NUMrich([{ t: "En " }, { t: "Configuración de enlaces (Link Settings)", b: true }, { t: ", seleccione " }, { t: "Crear copias de todos los archivos fuente (Create copies of all source files)", b: true }, { t: ". Esto le permitirá actualizar las fechas y cifras del período nuevo sin alterar el período original." }], "pasosB"),
      NUM("Defina comentarios y etiquetas de esquema según el capítulo 6 (para roll forward, ambas desmarcadas).", "pasosB"),
      NUM("Ponga a la carpeta el nombre del período nuevo y elija su ubicación de destino.", "pasosB"),
      NUMrich([{ t: "Presione " }, { t: "Copiar (Copy)", b: true }, { t: ". La copia de una carpeta puede tardar varios minutos; puede seguir usando Workiva mientras corre. Recibirá una notificación y un correo cuando esté lista." }], "pasosB"),
      NUM("Renombre los archivos copiados desde Home (clic derecho → Renombrar / Rename), cambiando únicamente la parte del período.", "pasosB"),
      NUM("Actualice las fechas dentro de los documentos: títulos, encabezados de columna, textos de notas y cualquier fecha escrita a mano. Si no lo hace, aparecerán errores en Document Health.", "pasosB"),
      NUM("Revise Document Health y la lista de enlaces (Manage source links) para confirmar que cada enlace apunta a la copia nueva y no al período anterior.", "pasosB"),
      SP(60),
      nota("Verificación imprescindible", "Después del roll forward, abra un archivo copiado y revise el origen de dos o tres enlaces al azar. Si apuntan a la carpeta del período anterior, la copia se hizo con la opción de enlaces equivocada: conviene rehacerla antes de que el equipo empiece a trabajar sobre ella.", ROJO),

      /* ---- 8 ---- */
      H1("8. Procedimiento C — Copiar o mover a otro workspace"),
      P("Copiar a otro workspace deja el archivo original intacto y crea un duplicado en el workspace de destino. Mover, en cambio, lo traslada."),
      H2("Pasos"),
      NUM("Vaya a la pestaña de Archivos (Files) y ubique el archivo.", "pasosC"),
      NUMrich([{ t: "Abra el menú desplegable a la derecha del archivo y elija " }, { t: "Mover (Move)", b: true }, { t: ", o marque la casilla del archivo y use el botón Mover de la barra de herramientas." }], "pasosC"),
      NUMrich([{ t: "Seleccione " }, { t: "Copiar a otro workspace (Copy to another Workspace)", b: true }, { t: "." }], "pasosC"),
      NUMrich([{ t: "Revise los archivos seleccionados y presione " }, { t: "Siguiente (Next)", b: true }, { t: "." }], "pasosC"),
      NUM("Elija las opciones de copia y el workspace de destino. Si corresponde y su rol lo permite, marque “Copy permissions from the source workspace” para conservar los permisos de los usuarios que existan en ambos workspaces.", "pasosC"),
      NUM("Confirme y espere la notificación por correo.", "pasosC"),
      H2("Limitaciones que hay que conocer"),
      BUL("Las tareas, el control de cambios (track changes) y el historial se reinician."),
      BUL("Los archivos no pueden estar abiertos durante la operación."),
      BUL("Si el documento tiene XBRL, el workspace de destino debe tener configurados el namespace y el calendario XBRL."),
      BUL("Los archivos enlazados se incluyen en la operación."),
      BUL("Usted queda marcado como propietario del archivo en el workspace de destino."),
      BUL("Los permisos otorgados a grupos no se copian, y los usuarios que no existen en el destino simplemente no se agregan."),

      /* ---- 9 ---- */
      new Paragraph({ children: [new PageBreak()] }),
      H1("9. Matriz de decisión rápida"),
      P("Use esta tabla para no tener que pensar el cuadro de opciones cada vez."),
      tabla([2600, 1900, 1700, 1900, 1980],
        ["Escenario", "Qué copiar", "Enlaces", "Comentarios", "Etiquetas"],
        [
          ["Roll forward de cierre (12-2025 → 06-2026)", "Carpeta completa", "Crear copias de todas las fuentes", "No", "No"],
          ["Versión “Resumido” a partir del EE.FF. completo", "Archivo", "Crear copias de las fuentes (o mantener, si comparten insumo)", "No", "No"],
          ["Respaldo antes de un cambio grande", "Archivo", "Desmarcada (foto congelada)", "Sí", "Sí"],
          ["Versión de prueba para experimentar", "Archivo", "Mantener enlaces originales", "No", "No"],
          ["Usar una sociedad como plantilla de otra", "Carpeta o archivo", "Crear copias de todas las fuentes", "No", "No"],
          ["Entrega histórica o fuera de Workiva", "Archivo", "Desmarcada", "No", "No"],
          ["Traslado a otro workspace", "Archivo o carpeta", "Se incluyen los enlazados", "Según el caso", "Según el caso"],
        ]),

      /* ---- 10 ---- */
      H1("10. Checklist posterior a la copia"),
      P("Revise estos puntos antes de dar por buena la copia y avisar al equipo."),
      NUM("Llegó la notificación y el correo de copia terminada, y el número de archivos copiados coincide con lo esperado.", "check"),
      NUM("Los nombres de archivos y de la carpeta reflejan el período nuevo y respetan la nomenclatura (código de sociedad, prefijos (CHN) / (LC)).", "check"),
      NUM("Las fechas dentro de los documentos están actualizadas: portada, encabezados, columnas comparativas y textos de notas.", "check"),
      NUM("Document Health no reporta enlaces rotos ni fechas inconsistentes.", "check"),
      NUM("Los enlaces apuntan a las fuentes del período nuevo (revisar Manage source links en dos o tres archivos como muestra).", "check"),
      NUM("Los permisos del equipo están correctos en los archivos copiados y los propietarios son los que corresponde.", "check"),
      NUM("Si el archivo tiene XBRL, el marcado y el calendario quedaron consistentes con el período nuevo.", "check"),
      NUM("La carpeta del período anterior quedó intacta y, si corresponde, bloqueada o marcada como cerrada para evitar ediciones accidentales.", "check"),
      NUM("Se avisó al equipo cuál es la carpeta vigente para trabajar.", "check"),

      /* ---- 11 ---- */
      H1("11. Errores frecuentes y cómo resolverlos"),
      tabla([3200, 3300, 3580], ["Síntoma", "Causa habitual", "Solución"], [
        ["No aparece la opción Copiar", "Permisos insuficientes sobre el archivo o la carpeta destino", "Solicitar permiso de Propietario o Editor, o pedir la copia a quien lo tenga"],
        ["Faltan archivos en la copia de una carpeta", "No tenía permiso sobre esos archivos", "Obtener permisos y copiar esos archivos aparte, enlazándolos manualmente"],
        ["Las cifras del período nuevo son las del anterior y no cambian", "Se copió con “Mantener enlaces originales”, o sin enlaces", "Rehacer la copia con “Crear copias de todos los archivos fuente”; si ya se avanzó, reapuntar los enlaces uno a uno"],
        ["Al editar la fuente cambian los dos períodos", "La copia quedó enlazada al mismo origen que el original", "Reapuntar los enlaces de la copia a la fuente del período nuevo"],
        ["Los valores no se actualizan aunque el enlace existe", "Falta publicar la fuente (Publish)", "Publicar el archivo fuente y refrescar el destino"],
        ["Document Health con errores de fecha o hipervínculos", "Fechas y vínculos no actualizados tras el roll forward", "Actualizar fechas en documentos y revisar los hipervínculos internos"],
        ["La copia se demora mucho o parece colgada", "Copia de carpeta con muchas fuentes", "Es normal: puede tardar varios minutos. Espere la notificación y el correo antes de reintentar"],
        ["Se copiaron comentarios y etiquetas viejos", "Casillas marcadas por defecto", "Resolver o eliminar en masa, o rehacer la copia con esas casillas desmarcadas"],
        ["Error de XBRL al copiar a otro workspace", "El destino no tiene namespace ni calendario XBRL", "Configurar XBRL en el workspace de destino antes de copiar"],
      ]),

      /* ---- 12 ---- */
      new Paragraph({ children: [new PageBreak()] }),
      H1("12. Consideraciones específicas para los EE.FF. de CGE y el Auditor"),
      P("Las copias no solo afectan a quien trabaja en Workiva: también afectan a las automatizaciones del Auditor (Verificar Workiva, Llenar Comparativos, Validar Comparativos y Extractor de Flujo de Efectivo), que identifican los archivos por su nombre."),
      H2("12.1 Nomenclatura: no la improvise al copiar"),
      BUL("Los archivos fuente se reconocen por el prefijo (CHN) o (LC) en el nombre. Si la copia pierde o altera ese prefijo, el script deja de reconocer el archivo como fuente."),
      BUL("Los archivos objetivo (target) son los que no llevan ese prefijo. Un “Copia de …” antepuesto al nombre puede hacer que un archivo se clasifique mal."),
      BUL("Mantenga el código de sociedad al inicio del nombre (E110, E200, E205, E211, E215, E230, E244, E514) y cambie solo el período."),
      BUL("Evite dobles espacios y variaciones de tildes o puntuación al renombrar: son diferencias invisibles a la vista que sí afectan la búsqueda por nombre."),
      H2("12.2 Enlaces y comparativos"),
      BUL("Si la copia se hizo sin enlaces, los comparativos quedan con los valores del último Publish: se ven correctos, pero no se actualizan y no tienen trazabilidad al balance."),
      BUL("Copie en una sola operación el EE.FF. y sus fuentes (CHN)/(LC) para que los enlaces se recreen entre las copias."),
      BUL("Después de un roll forward, corra “Verificar Workiva” y “Validar Comparativos” sobre los archivos nuevos antes de que el equipo empiece a completar información: es la forma más rápida de detectar enlaces mal apuntados."),
      H2("12.3 Orden de trabajo recomendado para un cierre"),
      NUM("Cerrar y publicar el período anterior; dejarlo sin enlaces rotos.", "pasosD"),
      NUM("Crear la subcarpeta del período nuevo.", "pasosD"),
      NUM("Copiar la carpeta con “Crear copias de todos los archivos fuente”, sin comentarios ni etiquetas.", "pasosD"),
      NUM("Renombrar carpeta y archivos al período nuevo respetando la nomenclatura.", "pasosD"),
      NUM("Actualizar fechas y revisar Document Health.", "pasosD"),
      NUM("Cargar los insumos del período (balances, EERR) en los archivos fuente copiados y publicarlos.", "pasosD"),
      NUM("Ejecutar Llenar Comparativos y luego Validar Comparativos desde el Auditor.", "pasosD"),
      NUM("Comunicar al equipo que la carpeta nueva es la vigente.", "pasosD"),

      /* ---- 13 ---- */
      H1("13. Glosario"),
      tabla([2600, 7480], ["Término", "Definición"], [
        ["Copy settings", "Cuadro de opciones que aparece antes de confirmar una copia."],
        ["Create copies of all source files", "Opción que copia también los archivos fuente y reapunta los enlaces a esas copias."],
        ["Keep links to original source files", "Opción que deja la copia enlazada a las fuentes originales."],
        ["Outline labels", "Etiquetas de color del esquema del documento que indican estado de avance."],
        ["Publish", "Acción que actualiza los valores enlazados desde la fuente hacia los destinos."],
        ["Roll forward", "Copiar el cierre anterior como base del siguiente, conservando estructura y enlaces."],
        ["Document Health", "Panel de diagnóstico de enlaces, fechas y consistencia del documento."],
        ["Manage source links", "Vista donde se revisan y administran los enlaces de origen de un archivo."],
        ["Workspace", "Espacio de trabajo de Workiva; los enlaces solo operan dentro de uno."],
        ["Copy Manager / Content Manager", "Roles del workspace habilitados para copiar contenido entre workspaces."],
      ]),

      /* ---- 14 ---- */
      H1("14. Referencias"),
      P("Documentación oficial de Workiva consultada para esta guía (Support Center):"),
      BUL("Copy a file or folder — support.workiva.com/hc/en-us/articles/360035639992"),
      BUL("Roll forward a folder — support.workiva.com/hc/en-us/articles/360046881351"),
      BUL("Move or copy a file to another workspace — support.workiva.com/hc/en-us/articles/360035642472"),
      BUL("Move files and folders — support.workiva.com/hc/en-us/articles/360050453751"),
      BUL("Manage source links — support.workiva.com/hc/en-us/articles/360046357671"),
      BUL("Understanding permissions — support.workiva.com/hc/en-us/articles/360049379792"),
      SP(140),
      P("Las pantallas de Workiva se actualizan periódicamente. Si encuentra una opción con un nombre distinto al descrito aquí, verifique el artículo de soporte correspondiente y actualice esta guía.", { italics: true, color: "666666" }),
    ],
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(process.argv[2] || "Guia_Copias_Workiva.docx", b);
  console.log("OK", (b.length / 1024).toFixed(1) + " KB");
});
