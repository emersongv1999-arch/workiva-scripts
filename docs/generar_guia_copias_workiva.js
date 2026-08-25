const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  LevelFormat, PageBreak, Footer, PageNumber
} = require("docx");

const AZUL = "1F3864";
const AZUL2 = "2E5C9A";
const GRIS = "F2F5FA";
const GRISB = "D9E1F2";
const ROJO = "9C1B1B";
const VERDE = "1E6B3A";
const W = 10080; // ancho util en DXA (Carta, margenes 0.75")

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

const BULrich = (runs, level = 0) => new Paragraph({
  numbering: { reference: "vinetas", level },
  spacing: { after: 80, line: 276 },
  children: runs.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, size: 21, font: r.font || "Calibri", color: r.color })),
});

const NUM = (text, ref) => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 90, line: 276 },
  children: [new TextRun({ text, size: 21, font: "Calibri" })],
});

const NUMrich = (runs, ref) => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 90, line: 276 },
  children: runs.map(r => new TextRun({ text: r.t, bold: r.b, italics: r.i, size: 21, font: r.font || "Calibri", color: r.color })),
});

const cell = (content, width, opts = {}) => new TableCell({
  width: { size: width, type: WidthType.DXA },
  shading: opts.shading ? { type: ShadingType.CLEAR, fill: opts.shading, color: "auto" } : undefined,
  margins: { top: 80, bottom: 80, left: 110, right: 110 },
  children: (Array.isArray(content) ? content : [content]).map(t =>
    typeof t === "string"
      ? new Paragraph({ spacing: { after: 0, line: 260 }, children: [new TextRun({ text: t, bold: opts.bold, size: 19, color: opts.color, font: opts.font || "Calibri" })] })
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

/* recuadro que imita la pantalla de Workiva, en monoespaciado */
const pantalla = (titulo, lineas) => new Table({
  columnWidths: [W],
  width: { size: W, type: WidthType.DXA },
  borders: {
    top: { style: BorderStyle.SINGLE, size: 6, color: "9AA6B8" },
    bottom: { style: BorderStyle.SINGLE, size: 6, color: "9AA6B8" },
    left: { style: BorderStyle.SINGLE, size: 6, color: "9AA6B8" },
    right: { style: BorderStyle.SINGLE, size: 6, color: "9AA6B8" },
    insideHorizontal: { style: BorderStyle.NONE },
    insideVertical: { style: BorderStyle.NONE },
  },
  rows: [new TableRow({
    children: [cell([
      new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: titulo, bold: true, size: 19, color: AZUL, font: "Consolas" })] }),
      ...lineas.map(l => new Paragraph({
        spacing: { after: 20, line: 240 },
        children: [new TextRun({ text: l.t, bold: l.b, size: 18, color: l.color || "222222", font: "Consolas" })],
      })),
    ], W, { shading: "F7F9FC" })],
  })],
});

const SP = (h = 120) => new Paragraph({ spacing: { after: h }, children: [] });

const numCfg = (ref) => ({
  reference: ref,
  levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 460, hanging: 300 } } } }],
});

/* ---------- documento ---------- */
const doc = new Document({
  creator: "Auditoría CGE",
  title: "Cómo hacer copias en Workiva — paso a paso",
  description: "Procedimiento detallado de copia de carpetas y archivos en Workiva, opción por opción",
  numbering: {
    config: [
      { reference: "vinetas", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 460, hanging: 250 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "–", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 900, hanging: 250 } } } },
      ]},
      numCfg("pasos"), numCfg("prep"), numCfg("check"), numCfg("orden"), numCfg("archivo"),
    ],
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [
            new TextRun({ text: "Cómo hacer copias en Workiva — CGE   |   Página ", size: 17, color: "777777", font: "Calibri" }),
            new TextRun({ children: [PageNumber.CURRENT], size: 17, color: "777777", font: "Calibri" }),
            new TextRun({ text: " de ", size: 17, color: "777777", font: "Calibri" }),
            new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 17, color: "777777", font: "Calibri" }),
          ],
        })],
      }),
    },
    children: [
      /* ================= PORTADA ================= */
      SP(500),
      new Paragraph({ spacing: { after: 60 },
        children: [new TextRun({ text: "PROCEDIMIENTO OPERATIVO — AUDITORÍA CGE", bold: true, size: 20, color: AZUL2, font: "Calibri" })] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "Cómo hacer copias en Workiva", bold: true, size: 52, color: AZUL, font: "Calibri" })] }),
      new Paragraph({ spacing: { after: 260 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: AZUL2, space: 6 } },
        children: [new TextRun({ text: "Paso a paso de la ventana Copy, opción por opción, con la configuración recomendada para copiar la carpeta del mes", size: 24, color: "444444", font: "Calibri" })] }),
      SP(160),
      tabla([2600, 7480], ["Campo", "Detalle"], [
        ["Aplica a", "Copia de carpetas y archivos dentro del mismo workspace de Workiva (menú Files → Copy)"],
        ["Ejemplo usado", "Copiar la carpeta 2026 › 08 Agosto 2026 (con Activo fijo y Reportes) para generar el mes siguiente"],
        ["Dirigido a", "Equipo de auditoría y preparación de reportes de CGE"],
        ["Versión", "2.0 — reescrita sobre la pantalla real de Workiva"],
        ["Fecha", "Agosto 2026"],
      ]),
      SP(220),
      nota("La única decisión que realmente pesa",
        "En la ventana Copy hay una lista larga de casillas, pero la que puede arruinar el trabajo es una sola: el desplegable de Links and Process References. Viene por defecto en \"Create copies of all source files\" (duplica también los archivos fuente). Si lo que usted quiere es que la copia siga leyendo de los archivos originales, tiene que cambiarlo a mano a \"Keep links to original source files\". Todo lo demás se corrige después; esto no.",
        ROJO),

      new Paragraph({ children: [new PageBreak()] }),

      /* ================= CONTENIDO ================= */
      H1("Contenido"),
      ...[
        "1. La copia en una mirada (resumen de los 6 pasos)",
        "2. Paso 1 — Preparar antes de copiar",
        "3. Paso 2 — Abrir el menú y elegir Copy",
        "4. Paso 3 — Revisar los archivos seleccionados",
        "5. Paso 4 — Copy includes: casilla por casilla",
        "6. Paso 5 — Links and Process References (la opción crítica)",
        "7. Paso 6 — Connections",
        "8. Paso 7 — Location Settings: nombre y ubicación",
        "9. Paso 8 — Presionar Copy y qué pasa después",
        "10. Configuración recomendada (hoja de referencia rápida)",
        "11. Checklist posterior a la copia",
        "12. Errores frecuentes y cómo resolverlos",
        "13. Diferencias al copiar un archivo suelto en vez de una carpeta",
        "14. Nomenclatura CGE y su efecto en los scripts del Auditor",
        "15. Glosario y referencias",
      ].map(t => new Paragraph({ spacing: { after: 70 }, indent: { left: 200 },
        children: [new TextRun({ text: t, size: 21, font: "Calibri", color: "333333" })] })),

      /* ================= 1 ================= */
      H1("1. La copia en una mirada (resumen de los 6 pasos)"),
      P("Si ya conoce el procedimiento, esta tabla es todo lo que necesita. El detalle de cada paso viene después."),
      tabla([900, 3000, 6180], ["Paso", "Dónde", "Qué hacer"], [
        ["1", "Files (árbol de carpetas)", "Ubicar la carpeta a copiar. Opcional: revisar Linked Files Report para saber con qué está enlazada."],
        ["2", "Menú contextual", "Clic derecho sobre la carpeta → Copy."],
        ["3", "Ventana Copy", "Revisar los archivos incluidos. Ojo: los Filings no se copian. → Next."],
        ["4", "Copy includes", "Marcar o desmarcar: All comments, Outline labels, Attachments, Automations, Document Markup, Links and Process References, Connections, Input cell values, Input mode in enabled sections."],
        ["5", "Desplegables", "Definir Links (Create copies / Keep links) y Connections (incoming / outgoing)."],
        ["6", "Location Settings", "Escribir New Folder Name (obligatorio) y elegir Location. Presionar Copy y esperar el aviso por correo."],
      ]),

      /* ================= 2 ================= */
      H1("2. Paso 1 — Preparar antes de copiar"),
      P("Dos minutos de preparación evitan tener que rehacer la copia completa."),
      NUM("Confirme que nadie esté editando los archivos que va a copiar. Lo que esté a medio guardar o con enlaces rotos se copia tal cual.", "prep"),
      NUMrich([{ t: "Publique (Publish) los archivos fuente si corresponde: la copia arrastra el " }, { t: "último valor publicado", b: true }, { t: ", no lo que está sin publicar." }], "prep"),
      NUMrich([{ t: "Si no tiene claro qué archivos están enlazados con la carpeta, use la opción " }, { t: "Linked Files Report", b: true }, { t: " del mismo menú contextual: le muestra el mapa de enlaces antes de decidir qué opción marcar en el paso 5." }], "prep"),
      NUMrich([{ t: "Decida el nombre de la carpeta nueva respetando la convención que ya usa el workspace: " }, { t: "\"09 Septiembre 2026\"", b: true }, { t: " (número de mes con dos dígitos, nombre del mes y año), igual que \"08 Agosto 2026\"." }], "prep"),
      SP(60),
      nota("Sobre la carpeta destino",
        "En la estructura actual (2024 / 2025 / 2026 con subcarpetas 01, 02, 03 … 08 Agosto 2026) la copia del mes va dentro de la carpeta del año. Eso se define en el campo Location del último paso, así que no necesita crear la carpeta antes: basta con elegir 2026 como Location y escribir el nombre del mes nuevo.",
        AZUL2),

      /* ================= 3 ================= */
      H1("3. Paso 2 — Abrir el menú y elegir Copy"),
      P("Haga clic derecho sobre la carpeta (o sobre el archivo) en el árbol de Files. Se abre el menú contextual, encabezado por su nivel de acceso — por ejemplo OWNER ACCESS."),
      pantalla("Menú contextual de una carpeta (OWNER ACCESS)", [
        { t: "Open                  Abrir la carpeta" },
        { t: "Star                  Marcarla como favorita" },
        { t: "Copy URL              Copiar el vínculo directo (no copia la carpeta)" },
        { t: "Rename                Renombrar" },
        { t: "Move                  Mover a otra ubicación (NO deja copia)" },
        { t: "Copy                  <<< ESTA es la opción de copia", b: true, color: ROJO },
        { t: "Export Workiva File   Exportar fuera de Workiva" },
        { t: "Linked Files Report   Reporte de archivos enlazados (útil ANTES de copiar)" },
        { t: "Permissions >         Administrar permisos" },
        { t: "Create PDF            Generar PDF" },
        { t: "Create XHTML file     Generar XHTML" },
        { t: "New Subfolder         Crear subcarpeta" },
        { t: "Create >              Crear archivo nuevo" },
        { t: "Move to trash         Enviar a la papelera" },
      ]),
      SP(100),
      P("Dos confusiones habituales en este menú:"),
      BULrich([{ t: "Copy URL", b: true }, { t: " no copia nada: solo copia al portapapeles el vínculo para pegarlo en un correo o chat." }]),
      BULrich([{ t: "Move", b: true }, { t: " traslada la carpeta y la saca de su ubicación actual. No genera duplicado. Si lo que quiere es conservar el original, use Copy." }]),

      /* ================= 4 ================= */
      H1("4. Paso 3 — Revisar los archivos seleccionados"),
      P("La ventana Copy parte mostrando qué se va a copiar, con el mensaje: “Review the files you selected. Filings will not be copied.”"),
      BULrich([{ t: "Revise que estén todos los archivos esperados. ", b: true }, { t: "Si falta alguno, casi siempre es porque usted no tiene permisos sobre él: consígalos antes de seguir, porque un archivo que no se copia deja un enlace apuntando al original." }]),
      BULrich([{ t: "Los Filings no se copian. ", b: true }, { t: "Las presentaciones regulatorias asociadas quedan fuera de la copia por diseño; si necesita una, se genera de nuevo desde la copia." }]),
      P("Confirme con Next para pasar a las opciones de copia. (El botón Back de la parte inferior le permite volver a esta lista sin perder lo que ya marcó.)"),

      /* ================= 5 ================= */
      new Paragraph({ children: [new PageBreak()] }),
      H1("5. Paso 4 — Copy includes: casilla por casilla"),
      P("Bajo el título “Copy includes: Select items you'd like copied with your files” aparece la lista de casillas. Este es su orden real en pantalla, con el estado que trae Workiva por defecto:"),
      pantalla("Copy includes — estado por defecto", [
        { t: "[ ]  All comments" },
        { t: "[X]  Outline labels" },
        { t: "[ ]  Attachments                    (?)" },
        { t: "[X]  Automations                    (?)" },
        { t: "[ ]  Document Markup                (?)" },
        { t: "[X]  Links and Process References", b: true },
        { t: "       [ Create copies of all source files  v ]", b: true, color: ROJO },
        { t: "       Smart links" },
        { t: "         [X] Maintain managed destination links      (?)" },
        { t: "         [X] Include metadata for all source smart links  (?)" },
        { t: "[X]  Connections                    (?)" },
        { t: "       [ Incoming and outgoing connections  v ]" },
        { t: "[ ]  Input cell values" },
        { t: "[ ]  Input mode in enabled sections" },
      ]),
      SP(120),

      H2("5.1 All comments — comentarios"),
      tabla([2400, 7680], ["Aspecto", "Detalle"], [
        ["Por defecto", "Desmarcada"],
        ["Si la marca", "Se copian todos los comentarios del archivo, tanto los abiertos como los ya resueltos, con sus respuestas."],
        ["Si la deja desmarcada", "La copia parte limpia, sin comentarios. El original conserva los suyos."],
        ["Recomendación", "Dejarla desmarcada al copiar el mes siguiente: los comentarios del mes anterior ya están resueltos y solo ensucian la revisión. Márquela solo si la copia es un respaldo del mismo período y quiere conservar la discusión."],
      ]),

      H2("5.2 Outline labels — etiquetas de esquema"),
      tabla([2400, 7680], ["Aspecto", "Detalle"], [
        ["Por defecto", "Marcada"],
        ["Qué son", "Los puntos de color del Document Outline que indican el estado de avance de cada sección, incluidos los conjuntos de etiquetas personalizados del workspace."],
        ["Si la marca", "La copia hereda el estado de avance del período anterior."],
        ["Recomendación", "Desmárquela en la copia mensual. Si la deja marcada, el mes nuevo aparece con secciones ya marcadas como revisadas y alguien puede darlas por buenas sin haberlas mirado."],
      ]),

      H2("5.3 Attachments — archivos adjuntos"),
      tabla([2400, 7680], ["Aspecto", "Detalle"], [
        ["Por defecto", "Desmarcada"],
        ["Qué son", "Los respaldos adjuntos a secciones o celdas (soporte, evidencias, planillas de apoyo)."],
        ["Si la marca", "Los adjuntos viajan a la copia, pero su marcado (markup) sobre los adjuntos no se traslada."],
        ["Recomendación", "Márquela si los adjuntos son parte de la estructura permanente del reporte (formatos, instructivos). Déjela desmarcada si los adjuntos son la evidencia del mes, que va a reemplazarse igual."],
      ]),

      H2("5.4 Automations — automatizaciones"),
      tabla([2400, 7680], ["Aspecto", "Detalle"], [
        ["Por defecto", "Marcada"],
        ["Qué son", "Las automatizaciones configuradas sobre los archivos (acciones que corren solas, actualizaciones programadas, flujos)."],
        ["Si la marca", "La copia queda con las mismas automatizaciones que el original."],
        ["Recomendación", "Déjela marcada: es lo que permite que el mes nuevo funcione igual que el anterior sin reconfigurar. Revise después que las automatizaciones copiadas apunten a los archivos correctos del período nuevo."],
      ]),

      H2("5.5 Document Markup — marcado del documento"),
      tabla([2400, 7680], ["Aspecto", "Detalle"], [
        ["Por defecto", "Desmarcada"],
        ["Qué es", "Las marcas de revisión sobre el documento: tick marks, resaltados y anotaciones de auditoría."],
        ["Si la marca", "El marcado del período anterior se copia al nuevo."],
        ["Recomendación", "Dejarla desmarcada en la copia mensual: el marcado es evidencia de la revisión de ese mes y arrastrarlo puede dar por revisado algo que no se revisó. Márquela solo si su procedimiento pide conservar los tick marks como plantilla."],
      ]),

      H2("5.6 Input cell values — valores de celdas de entrada"),
      tabla([2400, 7680], ["Aspecto", "Detalle"], [
        ["Por defecto", "Desmarcada"],
        ["Qué son", "Los valores cargados manualmente en las celdas de entrada (input) de las planillas."],
        ["Si la marca", "Esos valores aparecen en la copia de la planilla."],
        ["Recomendación", "Desmarcada para el mes nuevo (los datos se cargan de cero). Márquela si necesita una copia idéntica para comparar o para respaldo."],
      ]),

      H2("5.7 Input mode in enabled sections — modo de entrada"),
      tabla([2400, 7680], ["Aspecto", "Detalle"], [
        ["Por defecto", "Desmarcada"],
        ["Qué es", "La configuración de Input Mode en las hojas donde está habilitado."],
        ["Si la marca", "Las hojas que tenían Input Mode habilitado en el original lo mantienen habilitado en la copia."],
        ["Recomendación", "Márquela si su equipo carga datos con Input Mode todos los meses: así no hay que volver a habilitarlo hoja por hoja."],
      ]),

      /* ================= 6 ================= */
      new Paragraph({ children: [new PageBreak()] }),
      H1("6. Paso 5 — Links and Process References (la opción crítica)"),
      P("Esta casilla viene marcada por defecto y controla de dónde tomarán sus datos los archivos copiados. Si copia un proceso, además determina si las acciones del proceso copiado conservan las referencias a archivos y secciones."),
      P("Al marcarla se habilita un desplegable con dos opciones. El valor por defecto es el primero:"),

      H2("6.1 Create copies of all source files (valor por defecto)"),
      P("Workiva copia también todos los archivos fuente que alimentan a su selección y reapunta los enlaces de la copia hacia esas nuevas fuentes. Queda un juego completo e independiente."),
      BUL("Ventaja: puede cambiar fechas y cifras del período nuevo sin tocar nada del período anterior."),
      BUL("Costo: se generan más archivos y la copia demora más."),
      BUL("Requisito: permiso sobre cada archivo fuente. El que no tenga, no se copia."),
      Prich([{ t: "Úsela cuando: ", b: true }, { t: "está haciendo un roll forward completo, es decir, cuando las fuentes también son del período y deben duplicarse (bases mensuales, insumos que se rehacen cada mes)." }]),

      H2("6.2 Keep links to original source files"),
      P("Al elegir esta opción, Workiva muestra el aviso: “Won't create new copies of any linked source files”. Es decir, no se duplica ninguna fuente: los archivos nuevos quedan enlazados a las fuentes originales y siguen leyendo de ellas."),
      BUL("Ventaja: no llena el workspace de duplicados y la copia queda leyendo la fuente única y oficial."),
      BUL("Riesgo: si esa fuente cambia, cambian también los datos de la copia — y si la fuente es la del mes anterior, el mes nuevo nace mostrando cifras viejas."),
      Prich([{ t: "Úsela cuando: ", b: true }, { t: "las fuentes viven fuera de la carpeta que está copiando y son permanentes (una maestra de parámetros, un catálogo de cuentas, una base corporativa única), o cuando quiere replicar solo la estructura de reportes sin duplicar los datos de origen." }]),
      SP(80),
      nota("La confusión más común",
        "El desplegable siempre parte en \"Create copies of all source files\". Mucha gente lo pasa por alto y termina con una copia entera de las fuentes que no necesitaba, o al revés: quería duplicar todo y no revisó que alguien lo hubiera dejado en \"Keep links\". Deténgase en este desplegable en cada copia: es un segundo y es la diferencia entre un mes limpio y un mes que hay que rehacer.",
        ROJO),
      SP(80),
      tabla([2900, 3600, 3580], ["Opción", "Qué pasa con las fuentes", "Cuándo elegirla"], [
        ["Create copies of all source files (por defecto)", "Se duplican y la copia se enlaza a los duplicados nuevos.", "Roll forward de mes o de cierre: todo el juego avanza de período."],
        ["Keep links to original source files", "No se duplica ninguna fuente; la copia lee de las originales.", "Fuentes únicas y permanentes que están fuera de la carpeta copiada."],
      ]),

      H2("6.3 Smart links: las dos casillas que aparecen debajo"),
      P("Cuando el desplegable está en “Create copies of all source files”, Workiva muestra la sección Smart links con dos casillas, ambas marcadas por defecto:"),
      H3("Maintain managed destination links"),
      P("Conserva en la copia los enlaces de destino administrados, es decir, la copia mantiene su condición de destino de los datos en lugar de quedar como texto suelto. Déjela marcada salvo que quiera romper deliberadamente esa cadena."),
      H3("Include metadata for all source smart links"),
      P("Conserva los nombres y descripciones de los smart links de origen copiados. Sin esto, los enlaces siguen funcionando pero pierden las etiquetas con que el equipo los identifica, y rastrear de dónde viene un número se vuelve mucho más lento. Déjela marcada."),

      /* ================= 7 ================= */
      H1("7. Paso 6 — Connections"),
      P("La casilla Connections viene marcada por defecto y trae su propio desplegable. Cubre las conexiones entre consultas y tablas de Wdata, reportes y hojas de cálculo."),
      tabla([3200, 6880], ["Opción del desplegable", "Qué incluye"], [
        ["Incoming and outgoing connections (por defecto)", "Ambos sentidos: lo que entra desde reportes, consultas Wdata y hojas, y lo que sale hacia tablas Wdata y hojas. Las conexiones salientes hacia hojas que no estén incluidas en la copia se ignoran."],
        ["Only incoming connections", "Solo lo que entra: conexiones desde reportes, consultas Wdata y hojas."],
        ["Only outgoing connections", "Solo lo que sale: conexiones hacia tablas Wdata y hojas."],
      ]),
      P("Recomendación: dejar la casilla marcada con “Incoming and outgoing connections”, que es lo que replica el comportamiento completo del período anterior."),
      SP(60),
      nota("Detalle fino al copiar carpetas con placeholders",
        "Si copia una carpeta que contiene archivos con placeholders, las conexiones solo se actualizan cuando la planilla del placeholder también está dentro de la carpeta copiada. Si esa planilla quedó fuera, las conexiones del placeholder no se modifican y siguen apuntando al origen original.",
        AZUL2),

      /* ================= 8 ================= */
      H1("8. Paso 7 — Location Settings: nombre y ubicación"),
      P("Al final de la ventana, bajo Location Settings, hay dos campos:"),
      tabla([2800, 7280], ["Campo", "Qué poner"], [
        ["New Folder Name (obligatorio, marcado con asterisco rojo)", "El nombre de la carpeta nueva. Workiva propone el nombre de la carpeta original (por ejemplo “08 Agosto 2026”): cámbielo aquí mismo por el del período nuevo, “09 Septiembre 2026”. Si copia un archivo, este campo se llama New File Name."],
        ["Location", "La carpeta donde quedará la copia. Para la copia mensual, seleccione la carpeta del año (por ejemplo 2026), no la carpeta del mes; si elige el mes, la copia queda anidada dentro del mes anterior."],
      ]),
      SP(60),
      nota("Renombre aquí, no después",
        "Cambiar el nombre en este campo cuesta cinco segundos. Si deja el nombre por defecto y renombra después, durante ese rato hay dos carpetas iguales en el árbol y es exactamente el momento en que alguien abre la equivocada y trabaja sobre el mes anterior.",
        AZUL2),

      /* ================= 9 ================= */
      H1("9. Paso 8 — Presionar Copy y qué pasa después"),
      NUM("Presione el botón verde Copy. (Cancel descarta todo; Back vuelve a la lista de archivos sin perder lo configurado.)", "pasos"),
      NUM("La copia corre en segundo plano: puede seguir usando Workiva mientras tanto. En carpetas grandes puede tardar varios minutos.", "pasos"),
      NUM("Recibirá una notificación en la plataforma y un correo con el enlace a los archivos copiados.", "pasos"),
      NUM("Abra la carpeta nueva y ejecute el checklist del capítulo 11 antes de avisar al equipo que ya puede trabajar en ella.", "pasos"),
      SP(60),
      P("Recuerde que, en toda copia, hay cosas que nunca viajan aunque no exista casilla para ellas: el historial de revisiones se reinicia, las tareas y el control de cambios no se copian, y los Filings quedan fuera. Los permisos, en cambio, sí se conservan dentro del mismo workspace.", { italics: true }),

      /* ================= 10 ================= */
      new Paragraph({ children: [new PageBreak()] }),
      H1("10. Configuración recomendada (hoja de referencia rápida)"),
      P("Imprima esta página y téngala al lado. Columna “Mes nuevo”: copiar la carpeta del mes para trabajar el período siguiente. Columna “Respaldo”: copia de seguridad del mismo período, antes de un cambio grande."),
      tabla([3100, 1700, 1700, 3580], ["Opción en pantalla", "Por defecto", "Mes nuevo", "Respaldo"], [
        ["All comments", "Desmarcada", "Desmarcada", "Marcada"],
        ["Outline labels", "Marcada", "Desmarcada", "Marcada"],
        ["Attachments", "Desmarcada", "Según el caso", "Marcada"],
        ["Automations", "Marcada", "Marcada", "Marcada"],
        ["Document Markup", "Desmarcada", "Desmarcada", "Marcada"],
        ["Links and Process References", "Marcada", "Marcada", "Marcada"],
        ["→ desplegable", "Create copies of all source files", "Create copies (o Keep links si las fuentes son externas y permanentes)", "Keep links to original source files"],
        ["→ Maintain managed destination links", "Marcada", "Marcada", "Marcada"],
        ["→ Include metadata for all source smart links", "Marcada", "Marcada", "Marcada"],
        ["Connections", "Marcada", "Marcada", "Marcada"],
        ["→ desplegable", "Incoming and outgoing", "Incoming and outgoing", "Incoming and outgoing"],
        ["Input cell values", "Desmarcada", "Desmarcada", "Marcada"],
        ["Input mode in enabled sections", "Desmarcada", "Marcada", "Marcada"],
        ["New Folder Name", "Nombre del original", "Nombre del período nuevo", "Nombre + “RESPALDO” y fecha"],
        ["Location", "Carpeta actual", "Carpeta del año", "Carpeta de respaldos"],
      ]),

      /* ================= 11 ================= */
      H1("11. Checklist posterior a la copia"),
      NUM("Llegó la notificación y el correo, y la carpeta nueva contiene la misma cantidad de archivos que la original.", "check"),
      NUM("El nombre de la carpeta y su ubicación son los correctos (no quedó anidada dentro del mes anterior).", "check"),
      NUM("Abrir dos o tres archivos y revisar el origen de sus enlaces: deben apuntar a donde usted decidió en el paso 5, no al período anterior por descuido.", "check"),
      NUM("Las fechas dentro de los documentos y planillas están actualizadas al período nuevo (títulos, encabezados, columnas comparativas).", "check"),
      NUM("Document Health no reporta enlaces rotos ni fechas inconsistentes.", "check"),
      NUM("Las automatizaciones copiadas apuntan a los archivos del período nuevo.", "check"),
      NUM("Los permisos del equipo quedaron correctos sobre la carpeta nueva.", "check"),
      NUM("Si se copiaron comentarios, etiquetas o markup por error, resolverlos ahora o rehacer la copia — no dejarlos “para después”.", "check"),
      NUM("Avisar al equipo cuál es la carpeta vigente del mes.", "check"),

      /* ================= 12 ================= */
      H1("12. Errores frecuentes y cómo resolverlos"),
      tabla([3200, 3300, 3580], ["Síntoma", "Causa habitual", "Solución"], [
        ["No aparece Copy en el menú", "Permisos insuficientes sobre la carpeta o el destino", "Pedir permiso de Owner o Editor, o pedirle la copia a quien lo tenga"],
        ["Faltan archivos en la copia", "Sin permiso sobre esos archivos, o eran Filings (que no se copian)", "Conseguir permisos y copiar aparte; los Filings se generan de nuevo desde la copia"],
        ["Las cifras del mes nuevo no cambian nunca", "Se dejó “Keep links to original source files” cuando las fuentes sí debían duplicarse", "Rehacer la copia con “Create copies of all source files” o reapuntar los enlaces uno por uno"],
        ["Al editar la copia se alteró el mes anterior", "La copia quedó enlazada a las mismas fuentes originales", "Reapuntar los enlaces de la copia a las fuentes del período nuevo"],
        ["Se duplicaron archivos fuente que no correspondía", "Se dejó el desplegable en su valor por defecto sin revisarlo", "Eliminar los duplicados sobrantes y reapuntar los enlaces a la fuente única"],
        ["La copia trae comentarios y marcas viejas", "All comments / Document Markup marcados", "Resolver en masa o rehacer la copia con esas casillas desmarcadas"],
        ["Las conexiones de un placeholder siguen apuntando al original", "La planilla del placeholder quedó fuera de la carpeta copiada", "Incluir esa planilla en la copia, o reconfigurar la conexión a mano"],
        ["La copia demora mucho", "Carpeta grande con muchas fuentes duplicándose", "Es normal: espere la notificación y el correo antes de reintentar; reintentar genera copias duplicadas"],
        ["Los valores de entrada aparecen vacíos", "Input cell values desmarcada (comportamiento por defecto)", "Si los necesitaba, rehacer la copia con esa casilla marcada"],
      ]),

      /* ================= 13 ================= */
      H1("13. Diferencias al copiar un archivo suelto en vez de una carpeta"),
      P("El procedimiento es el mismo; cambian tres detalles:"),
      NUMrich([{ t: "El campo de nombre se llama " }, { t: "New File Name", b: true }, { t: " en lugar de New Folder Name." }], "archivo"),
      NUMrich([{ t: "Las opciones propias de planillas —" }, { t: "Input cell values", b: true }, { t: " e " }, { t: "Input mode in enabled sections", b: true }, { t: "— solo tienen efecto si el archivo es una planilla." }], "archivo"),
      NUMrich([{ t: "El manejo de enlaces se vuelve más delicado: al copiar un solo archivo, todas sus fuentes están " }, { t: "fuera", b: true }, { t: " de la selección. Con “Create copies of all source files” se duplicarán esas fuentes aunque usted solo quería un archivo; con “Keep links” la copia quedará leyendo de las fuentes originales. Por eso, cuando varios archivos están enlazados entre sí, conviene copiar la carpeta completa en una sola operación." }], "archivo"),

      /* ================= 14 ================= */
      H1("14. Nomenclatura CGE y su efecto en los scripts del Auditor"),
      P("Las copias no solo afectan a quien trabaja en Workiva: también afectan a las automatizaciones del Auditor (Verificar Workiva, Llenar Comparativos, Validar Comparativos y Extractor de Flujo de Efectivo), que identifican los archivos por su nombre."),
      BUL("Los archivos fuente se reconocen por el prefijo (CHN) o (LC) en el nombre. Si la copia altera o pierde ese prefijo, el script deja de reconocerlos como fuente."),
      BUL("Los archivos objetivo (target) son los que no llevan ese prefijo: un nombre con “Copy of …” antepuesto puede hacer que un archivo se clasifique mal."),
      BUL("Mantenga el código de sociedad al inicio del nombre (E110, E200, E205, E211, E215, E230, E244, E514) y cambie solo la parte del período."),
      BUL("Evite dobles espacios y cambios de tildes o puntuación al renombrar: son diferencias invisibles a la vista que sí afectan la búsqueda por nombre."),
      BUL("Si la copia se hizo con “Keep links to original source files” y las fuentes eran del período anterior, los comparativos se llenarán con cifras viejas aunque todo parezca correcto."),
      SP(60),
      H2("Orden de trabajo recomendado para el período"),
      NUM("Cerrar y publicar el período anterior, sin enlaces rotos.", "orden"),
      NUM("Copiar la carpeta del mes con las opciones de la hoja de referencia rápida (capítulo 10).", "orden"),
      NUM("Renombrar carpeta y archivos al período nuevo respetando la nomenclatura.", "orden"),
      NUM("Actualizar fechas y revisar Document Health.", "orden"),
      NUM("Cargar los insumos del período en los archivos fuente y publicarlos.", "orden"),
      NUM("Ejecutar Llenar Comparativos y luego Validar Comparativos desde el Auditor.", "orden"),
      NUM("Comunicar al equipo que la carpeta nueva es la vigente.", "orden"),

      /* ================= 15 ================= */
      H1("15. Glosario y referencias"),
      tabla([2900, 7180], ["Término", "Definición"], [
        ["Copy includes", "Bloque de casillas que define qué se copia junto con los archivos."],
        ["Create copies of all source files", "Opción que duplica también los archivos fuente y reapunta los enlaces a esas copias. Es el valor por defecto."],
        ["Keep links to original source files", "Opción que no duplica ninguna fuente: la copia sigue leyendo de las originales."],
        ["Smart links", "Enlaces inteligentes con nombre y descripción propios, que facilitan rastrear el origen de un dato."],
        ["Managed destination links", "Enlaces de destino administrados: mantienen la copia como destino formal de un dato de origen."],
        ["Connections", "Conexiones entre consultas y tablas de Wdata, reportes y hojas."],
        ["Input Mode", "Modo de carga de datos habilitado en hojas específicas de una planilla."],
        ["Document Markup", "Marcas de revisión sobre el documento (tick marks, resaltados, anotaciones)."],
        ["Filing", "Presentación regulatoria generada desde Workiva. Nunca se incluye en una copia."],
        ["Linked Files Report", "Reporte del menú contextual que muestra con qué archivos está enlazado el que va a copiar."],
        ["Document Health", "Panel de diagnóstico de enlaces, fechas y consistencia del documento."],
        ["Publish", "Acción que actualiza los valores enlazados desde la fuente hacia sus destinos."],
      ]),
      SP(120),
      P("Documentación oficial consultada (Workiva Support Center):"),
      BUL("Copy a file or folder — support.workiva.com/hc/en-us/articles/360035639992"),
      BUL("Roll forward a folder — support.workiva.com/hc/en-us/articles/360046881351"),
      BUL("Manage source links — support.workiva.com/hc/en-us/articles/360046357671"),
      BUL("Intro to smart links — support.workiva.com/hc/en-us/articles/17197053356052"),
      BUL("Use Input Mode — support.workiva.com/hc/en-us/articles/4413294005780"),
      BUL("Attachments in Documents — support.workiva.com/hc/en-us/articles/360041247532"),
      BUL("Move or copy a file to another workspace — support.workiva.com/hc/en-us/articles/360035642472"),
      SP(140),
      P("Las pantallas de Workiva cambian con las versiones. Si aparece una opción nueva o con otro nombre, verifique el artículo de soporte correspondiente y actualice esta guía.", { italics: true, color: "666666" }),
    ],
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(process.argv[2] || "Guia_Copias_Workiva.docx", b);
  console.log("OK", (b.length / 1024).toFixed(1) + " KB");
});
