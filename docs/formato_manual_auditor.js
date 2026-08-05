const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, VerticalAlign,
  HeadingLevel, LevelFormat, Footer, PageNumber, PageOrientation,
} = require("docx");

/* ---------- design tokens ---------- */
const NAVY   = "12385F";
const BLUE   = "2E74B5";
const INK    = "262626";
const MUTED  = "595959";
const RULE   = "D6DCE4";
const CARD   = "DCE8F7";
const SOFT   = "F4F7FB";
const GREEN  = "1E7A46";

const FONT = "Calibri";
const MONO = "Consolas";

const W = 9360;                 // Letter 12240 - 2*1440
const MEDIA = "media";

/* Tres anchos fijos para todas las capturas (en pulgadas) */
const GRANDE = 6.4;   // ventana completa de la aplicación
const MEDIA_W = 5.4;  // ventana parcial o cuadro de diálogo
const CHICA  = 3.6;   // ventana emergente pequeña

const noB  = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const hair = (color = RULE, size = 4) => ({ style: BorderStyle.SINGLE, size, color });

const t = (text, o = {}) => new TextRun({ text, ...o });

/* ---------- building blocks ---------- */

const p = (children, o = {}) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 140, line: 276, lineRule: "auto" },
    ...o,
    children: Array.isArray(children) ? children : [t(children)],
  });

const h1 = (text) => new Paragraph({ text, heading: HeadingLevel.HEADING_1 });

const label = (text) =>
  new Paragraph({
    style: "Etiqueta",
    children: [t(text, { bold: true, size: 17, color: BLUE, characterSpacing: 24 })],
  });

const step = (text, inst = 1) =>
  new Paragraph({
    numbering: { reference: "pasos", level: 0, instance: inst },
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 90, line: 276, lineRule: "auto" },
    children: [t(text)],
  });

const check = (text) =>
  new Paragraph({
    numbering: { reference: "checks", level: 0 },
    spacing: { after: 70, line: 268, lineRule: "auto" },
    children: [t(text)],
  });

const arrow = (text) =>
  new Paragraph({
    numbering: { reference: "flechas", level: 0 },
    spacing: { after: 70, line: 268, lineRule: "auto" },
    children: [t(text)],
  });

const field = (text) =>
  new Paragraph({
    numbering: { reference: "campos", level: 0 },
    spacing: { after: 50, line: 264, lineRule: "auto" },
    children: [t(text, { size: 21 })],
  });

const pageStart = () =>
  new Paragraph({
    pageBreakBefore: true,
    spacing: { before: 0, after: 0, line: 20, lineRule: "exact" },
    children: [t("", { size: 2 })],
  });

const gap = (after = 120) =>
  new Paragraph({
    spacing: { before: 0, after, line: 120, lineRule: "exact" },
    children: [t("", { size: 10 })],
  });

// One-cell framed block used for notes, code boxes and the cover banner.
function box(paragraphs, { fill = SOFT, bar = null, pad = 150, border = null } = {}) {
  const b = border
    ? { top: hair(border), bottom: hair(border), left: hair(border), right: hair(border),
        insideHorizontal: noB, insideVertical: noB }
    : { top: noB, bottom: noB, right: noB,
        left: bar ? { style: BorderStyle.SINGLE, size: 18, color: bar } : noB,
        insideHorizontal: noB, insideVertical: noB };
  return new Table({
    columnWidths: [W],
    width: { size: W, type: WidthType.DXA },
    borders: b,
    rows: [
      new TableRow({
        cantSplit: true,
        children: [
          new TableCell({
            width: { size: W, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, color: "auto", fill },
            margins: { top: pad, bottom: pad, left: bar ? 220 : 200, right: 200 },
            children: paragraphs,
          }),
        ],
      }),
    ],
  });
}

// Centred screenshot in its OWN paragraph, never mixed with text.
// keepLines keeps the picture whole: if it does not fit it moves entirely to
// the next page instead of overlapping the text or the footer.
function shot(file, widthIn) {
  const buf = fs.readFileSync(`${MEDIA}/${file}`);
  const pw = buf.readUInt32BE(16), ph = buf.readUInt32BE(20);
  const wPx = Math.round(widthIn * 96);          // docx-js sizes images in px @96dpi
  return new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { before: 140, after: 200, line: 240, lineRule: "auto" },
    keepLines: true,
    children: [
      new ImageRun({
        type: "png",
        data: buf,
        transformation: { width: wPx, height: Math.round(wPx * (ph / pw)) },
      }),
    ],
  });
}

// Module header card: number chip + name + status pill, exactly one text column wide.
function moduleCard(num, name, status) {
  const widths = [780, 6600, 1980];
  return new Table({
    columnWidths: widths,
    width: { size: W, type: WidthType.DXA },
    borders: { top: noB, bottom: noB, left: noB, right: noB, insideHorizontal: noB, insideVertical: noB },
    rows: [
      new TableRow({
        cantSplit: true,
        children: [
          new TableCell({
            width: { size: widths[0], type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, color: "auto", fill: NAVY },
            margins: { top: 110, bottom: 110, left: 0, right: 0 },
            verticalAlign: VerticalAlign.CENTER,
            children: [new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { before: 0, after: 0 },
              children: [t(num, { bold: true, size: 26, color: "FFFFFF" })],
            })],
          }),
          new TableCell({
            width: { size: widths[1], type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, color: "auto", fill: CARD },
            margins: { top: 110, bottom: 110, left: 200, right: 120 },
            verticalAlign: VerticalAlign.CENTER,
            children: [new Paragraph({
              style: "TituloModulo",
              children: [t(name, { bold: true, size: 26, color: NAVY })],
            })],
          }),
          new TableCell({
            width: { size: widths[2], type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, color: "auto", fill: CARD },
            margins: { top: 110, bottom: 110, left: 120, right: 180 },
            verticalAlign: VerticalAlign.CENTER,
            children: [new Paragraph({
              alignment: AlignmentType.RIGHT,
              spacing: { before: 0, after: 0 },
              children: [t(status, { bold: true, size: 17, color: GREEN })],
            })],
          }),
        ],
      }),
    ],
  });
}

/* ---------- content ---------- */

const FOOTER_TEXT = "Auditor CGE — Workiva  ·  Manual interno  ·  v2026";

const cover = new Table({
  columnWidths: [W],
  width: { size: W, type: WidthType.DXA },
  borders: { top: noB, bottom: noB, left: noB, right: noB, insideHorizontal: noB, insideVertical: noB },
  rows: [
    new TableRow({
      cantSplit: true,
      children: [
        new TableCell({
          width: { size: W, type: WidthType.DXA },
          shading: { type: ShadingType.CLEAR, color: "auto", fill: NAVY },
          margins: { top: 420, bottom: 420, left: 400, right: 400 },
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 100 },
              children: [t("AUDITOR CGE — WORKIVA", { bold: true, size: 44, color: "FFFFFF", characterSpacing: 20 })],
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 80 },
              children: [t("Manual de Módulos", { size: 26, color: "D6E4F5" })],
            }),
            new Paragraph({
              alignment: AlignmentType.CENTER,
              spacing: { after: 0 },
              children: [t("v2026 — Uso interno", { size: 18, color: "A8C4E4", characterSpacing: 16 })],
            }),
          ],
        }),
      ],
    }),
  ],
});

const children = [
  cover,
  gap(200),

  h1("¿Qué es el Auditor?"),
  p("El Auditor es una aplicación de escritorio que combina dos tipos de funciones: conexión directa con Workiva (Wdesk) para consultar y escribir datos en el espacio de trabajo, y generación de archivos locales de Excel que se guardan en la carpeta que el usuario elija en su computador. No requiere abrir el navegador ni exportar archivos manualmente."),
  p("La aplicación dispone de los siguientes módulos, cada uno descrito en este manual con su función, los requisitos previos y los pasos de operación."),
  p("No todos los módulos trabajan de la misma forma. El Verificador de Sumas y el Llenado de Comparativos escriben directamente dentro de Workiva. El Extractor de Flujo de Efectivo y la Validación de Comparativos, en cambio, solo generan un archivo de Excel en tu computador y no modifican nada en Workiva."),
  p("El Auditor es de uso personal. Cada persona recibe su propia copia de la aplicación, con sus credenciales de Workiva dentro del programa, de modo que todo lo que se escriba queda registrado en Workiva a su nombre. Por eso el archivo ejecutable no debe compartirse ni prestarse: si otra persona usa tu copia, los cambios quedarán registrados como hechos por ti."),

  h1("Pasos previos de la aplicación"),
  p("El Auditor se distribuye como un único archivo ejecutable (Auditor.exe) que recibirás directamente. Guárdalo en tu computador y ejecútalo con doble clic; no requiere instalación."),
  shot("image1.png", CHICA),
  p([
    t("Si al descargar la aplicación y al intentar ejecutarla les sale un error con la pantalla azul con este mensaje pop-up, deberán abrir un ticket en la mesa de ayuda para que se les habilite el uso de la aplicación. El ticket debe ser generado en la "),
    t("Categoría:", { bold: true }),
    t(" Aplicaciones de escritorio y en la "),
    t("Subcategoría:", { bold: true }),
    t(" Homologación de software. Con ese paso realizado el equipo de soporte les habilitará la aplicación y podrán acceder a todos los módulos de esta, los cuales están detallados más abajo."),
  ]),

  h1("Entrando a la aplicación"),
  p("Al ejecutar el “Auditor” les saldrá esta pantalla. De inicio les aparecerá el módulo de verificación de sumas, de igual manera se pueden observar el resto de módulos tales como llenado de comparativos, flujo de efectivo y validar comparativos. Más abajo se detallan su función y sus requisitos."),
  shot("image2.png", MEDIA_W),

  /* ================= 01 ================= */
  pageStart(),
  moduleCard("01", "Verificador de Sumas", "● Disponible"),
  gap(140),
  label("QUÉ HACE"),
  p("Accede a los documentos Word (docx) de Estados Financieros de Workiva en la misma base de datos del “Auditor” para un período dado y revisa automáticamente que los totales coincidan con la suma de sus componentes."),
  p("Detecta filas y columnas de subtotal en tablas, acumula sus sumandos y señala cualquier diferencia que supere el umbral configurado (por defecto, 1)."),

  label("DÓNDE SE GUARDA EL RESULTADO"),
  p("Al finalizar, los hallazgos se escriben automáticamente en Workiva en el siguiente archivo:"),
  box([
    new Paragraph({
      spacing: { after: 40, line: 240, lineRule: "auto" },
      children: [
        t("Archivo: ", { font: MONO, size: 19, color: MUTED }),
        t("Verificación de Sumas MM.AAAA", { font: MONO, size: 19, bold: true, color: NAVY }),
      ],
    }),
    new Paragraph({
      spacing: { after: 0, line: 240, lineRule: "auto" },
      children: [
        t("Ruta: ", { font: MONO, size: 19, color: MUTED }),
        t("Estados Financieros  /  AAAA  /  [Mes] AAAA", { font: MONO, size: 19, bold: true, color: NAVY }),
      ],
    }),
  ], { bar: BLUE }),
  gap(140),
  p("Ejemplo para junio 2026: Estados Financieros / 2026 / Junio 2026"),
  shot("image3.png", GRANDE),

  label("CAMPOS DE ENTRADA"),
  field("Mes"), field("Año"),

  label("CONDICIONES NECESARIAS"),
  check("Que existan documentos con nombre \"EE.FF MM-AAAA\" en el workspace (espacio de trabajo)."),

  label("PASOS DE USO"),
  step("Escribe el mes (ej: 06) y el año (ej: 2026) en los campos del panel izquierdo.", 1),
  step("Haz clic en \"Buscar documentos\". Aparecerá la lista de Estados Financieros encontrados.", 1),
  shot("image4.png", MEDIA_W),
  step("Marca los documentos a revisar (o usa \"Marcar todos\") y presiona \"Verificar seleccionados\".", 1),
  step("El panel de Actividad muestra el progreso. Los errores aparecen en amarillo; los documentos sin diferencias, en verde.", 1),
  shot("image5.png", GRANDE),
  step("Al finalizar, el resumen queda guardado automáticamente en el archivo Verificación de Sumas MM.AAAA dentro de la carpeta del mes en Workiva, con cinco hojas por cada sociedad revisada: el resumen (E###), Hallazgos, Revisar_manual, Verificadas_OK e Indice_cuadros.", 1),
  shot("image6.png", MEDIA_W),
  step("Al ingresar en la pestaña de Hallazgos saldrá una tabla con las diferencias prioritarias. Cada fila indica la sociedad, el cuadro o nota donde está la diferencia, la fila y la columna afectadas, el valor impreso, el calculado y la diferencia entre ambos, además de la regla con que se sumó el cuadro y la causa probable. El resto de las diferencias queda en Revisar_manual.", 1),
  shot("image7.png", MEDIA_W),

  /* ================= 02 ================= */
  pageStart(),
  moduleCard("02", "Llenar Comparativos", "● Disponible"),
  gap(140),
  label("QUÉ HACE"),
  p("Copia automáticamente los valores del período anterior hacia las columnas comparativas de cada hoja dentro de los archivos Individuales de Workiva. Evita el llenado manual fila por fila."),
  p([
    t("Cada nota de los Estados Financieros muestra dos columnas de cifras. Una es la del período que se está cerrando, que llega sola desde Workiva a través de las conexiones. La otra es la columna comparativa, que muestra el mismo dato pero del período anterior, y esa no llega sola: alguien tiene que abrir el archivo del período pasado, buscar la cifra y copiarla. Como cada archivo Individual tiene decenas de hojas, y cada hoja decenas de filas, hacerlo a mano toma "),
    t("horas", { bold: true }),
    t(" y es fácil equivocarse de fila."),
  ]),
  p("El módulo abre la hoja Bases, una hoja que viene dentro del mismo archivo y que contiene los parámetros del cierre, y lee de ahí dos fechas: la del período actual y la del período con el que hay que comparar. Con la fecha del comparativo busca en Workiva el archivo Individual de esa misma sociedad correspondiente al período anterior. Es el mismo nombre de archivo, cambiando solo el mes y el año."),
  p("Luego entra hoja por hoja. En cada una mira los encabezados y ubica la columna comparativa, que es la que lleva la fecha del período anterior. Las columnas del período actual, y las que se alimentan de consultas o de SAP BPC, las deja fuera, porque esas se actualizan solas."),
  p("Ubicada la columna, empareja las filas. No copia la fila 10 en la fila 10: busca cada partida por su nombre o por su código de cuenta de SAP BPC, y ahí deja el valor que le corresponde. Por eso funciona aunque el cuadro haya cambiado de tamaño entre un período y otro; si en la nota se agregó o se quitó una línea, cada cifra igual queda donde va."),
  p("Solo escribe números y solo en celdas vacías. Si la celda destino tiene una fórmula, como una suma o un subtotal, no la toca. Si tiene texto, tampoco. Y si la fila no tiene nombre ni código, la salta."),

  label("CAMPOS DE ENTRADA"),
  field("Mes"), field("Año"),

  label("CONDICIONES NECESARIAS"),
  check("Que existan archivos con el formato \"E###_IND_MM-AAAA_Base Notas …\" en el workspace (espacio de trabajo)."),
  check("Que la hoja de bases esté actualizada y que sea consistente con el período a llenar."),
  check("Que las celdas en las cuales escribirá NO estén bloqueadas, al igual que los archivos."),

  label("PASOS DE USO"),
  step("Ingresa el mes y año del período a llenar (ej: 09-2026).", 2),
  step("Haz clic en \"Buscar archivos\". La aplicación buscará en Workiva todos los archivos “Excel” individuales del período.", 2),
  step("Selecciona los archivos a procesar. Puedes usar \"Marcar todas\" o elegir solo algunos.", 2),
  shot("image8.png", MEDIA_W),
  step("Al hacer clic en \"Procesar seleccionados\" saldrá una alerta que advertirá que el sistema escribirá directamente en Workiva para evitar errores de procesos; es una medida de prevención.", 2),
  shot("image9.png", MEDIA_W),
  step("Haz clic en \"Procesar seleccionados\". El panel de Actividad mostrará hoja por hoja cuántas columnas se escribieron.", 2),
  step("Luego de que termina de procesar saltará un mensaje pop-up que dirá los archivos que se procesaron, los OK, los errores (ERR) y cuánto tardó en cada uno.", 2),
  shot("image10.png", MEDIA_W),
  step("En la pantalla pop-up en que aparecen los detalles de cuántos OK o ERR (los errores), puedes hacer clic en \"Ver errores\" para ver un detalle más a fondo de esto.", 2),
  step("En los detalles a fondo se puede ver las hojas e incluso qué celdas son las que presentan errores, para poder revisar si es necesario más a fondo.", 2),
  step("Luego de haber corregido los errores uno puede reintentar los fallidos para no tener que correr todo el proceso nuevamente.", 2),
  shot("image11.png", GRANDE),
  step("Luego de hacer clic en \"Aceptar\" se puede ver en la actividad cosas como el detalle de los archivos que tomó como base para rellenar el archivo deseado, de igual manera que las hojas con errores.", 2),
  shot("image12.png", MEDIA_W),

  label("REGLAS AUTOMÁTICAS APLICADAS"),
  arrow("Hojas de balance: solo se procesan cuando el mes es 03 (marzo)."),
  arrow("Hojas con fórmulas en las celdas destino: se omiten sin modificar nada (sumas/subtotales)."),
  arrow("Hojas ya llenadas (con valores numéricos en la columna comparativa): se saltan."),

  /* ================= 03 ================= */
  pageStart(),
  moduleCard("03", "Flujo de Efectivo", "● Disponible"),
  gap(140),
  label("QUÉ HACE"),
  p("Descarga el Estado de Flujo de Efectivo de una o más sociedades directamente desde la aplicación de “Flujo Internacional” y lo guarda como un archivo Excel (.xlsx) en la carpeta que el usuario elija en su computador. Incluye el detalle de los movimientos que componen cada uno de los ítems del flujo. Esto ocurre siempre que el flujo se haya generado en la aplicación; en caso contrario, se extraerá una versión preliminar del flujo."),

  label("CAMPOS DE ENTRADA"),
  field("Mes"), field("Año"), field("Carpeta de salida"),

  label("CONDICIONES NECESARIAS"),
  check("Tener una carpeta local donde se guardará el archivo .xlsx generado."),
  check("Haber generado el flujo en la aplicación “Flujo Internacional”."),

  label("PASOS DE USO"),
  step("Escribe el mes y año del período a descargar (ej: 06-2026).", 3),
  step("Haz clic en \"Examinar…\" para elegir la carpeta donde se guardará el archivo.", 3),
  step("Presiona \"Procesar\". La aplicación descargará el flujo desde la aplicación “Flujo Internacional”.", 3),
  shot("image13.png", MEDIA_W),
  shot("image14.png", GRANDE),
  step("Al finalizar, aparecerá un mensaje de flujo generado diciendo que el archivo .xlsx se generó correctamente y se abrirá automáticamente si le damos que Sí en el pop-up.", 3),
  shot("image15.png", GRANDE),

  /* ================= 04 ================= */
  pageStart(),
  moduleCard("04", "Validar Comparativos", "● Disponible"),
  gap(140),
  label("QUÉ HACE"),
  p("Verifica que las columnas comparativas de los archivos Individuales o Consolidados estén correctamente llenadas para un período dado. Detecta inconsistencias."),
  p("Genera un archivo Excel (.xlsx) con una fila o sección por cada hoja procesada, indicando el detalle de observaciones encontradas en cada una. Se guarda en la carpeta de salida elegida y no escribe nada dentro de Workiva."),

  label("CAMPOS DE ENTRADA"),
  field("Sociedad (ej: E215 o 215)"), field("Año"), field("Trimestre"),
  field("Tipo (Consolidado o Individual)"), field("Carpeta de salida"),

  label("CONDICIONES NECESARIAS"),
  check("Que los comparativos ya hayan sido llenados (ejecutar \"Llenar Comparativos\" primero)."),
  check("Tener una carpeta local donde se guardará el archivo .xlsx con los resultados."),
  check("Conocer el código de la sociedad y el trimestre a revisar."),

  label("PASOS DE USO"),
  step("Ingresa el código de Sociedad (ej: E215 o solo 215).", 4),
  step("Completa el Año, el Trimestre (03 para el primer trimestre, que cierra en marzo; 06 para el segundo, junio; 09 para el tercero, septiembre; 12 para el cuarto, diciembre) y el Tipo desde el parámetro desplegable (viene predeterminado en Consolidado).", 4),
  step("Haz clic en \"Examinar…\" para elegir la carpeta donde se guardará el archivo .xlsx.", 4),
  shot("image16.png", MEDIA_W),
  step("Presiona \"Validar\". El panel de actividad muestra el progreso hoja por hoja.", 4),
  step("Al finalizar, saltará una alerta que dirá si hay hallazgos y permite abrir el Excel generado directamente desde el auditor.", 4),
  shot("image17.png", MEDIA_W),
  step("Al hacer clic en Sí, se abre la carpeta de salida. El Excel generado tiene una fila o sección por cada hoja revisada con el detalle de sus observaciones con los hallazgos, los OK, los no procesados.", 4),
  shot("image18.png", GRANDE),
];

/* ---------- document ---------- */

const doc = new Document({
  title: "Auditor CGE — Workiva · Manual de Módulos",
  creator: "CGE",
  description: "Manual de módulos de la aplicación Auditor CGE — Workiva",
  styles: {
    default: {
      document: {
        run: { font: FONT, size: 22, color: INK },
        paragraph: { spacing: { line: 276, after: 140 } },
      },
    },
    paragraphStyles: [
      {
        id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: NAVY },
        paragraph: {
          spacing: { before: 380, after: 160 }, keepNext: true, keepLines: true, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 4 } },
        },
      },
      {
        id: "TituloModulo", name: "Titulo Modulo", basedOn: "Normal", next: "Normal",
        run: { font: FONT, size: 26, bold: true, color: NAVY },
        paragraph: { spacing: { before: 0, after: 0 }, keepNext: true, outlineLevel: 0 },
      },
      {
        id: "Etiqueta", name: "Etiqueta", basedOn: "Normal", next: "Normal",
        run: { font: FONT, size: 17, bold: true, color: BLUE },
        paragraph: { spacing: { before: 260, after: 80 }, keepNext: true, keepLines: true, outlineLevel: 1 },
      },
      {
        id: "PieDePagina", name: "Pie de pagina", basedOn: "Normal", next: "Normal",
        run: { font: FONT, size: 17, color: "808080" },
        paragraph: { spacing: { before: 0, after: 0, line: 240, lineRule: "auto" } },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "pasos",
        levels: [{
          level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { run: { bold: true, color: BLUE }, paragraph: { indent: { left: 520, hanging: 360 } } },
        }],
      },
      {
        reference: "checks",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "✓", alignment: AlignmentType.LEFT,
          style: { run: { color: GREEN, bold: true, font: FONT }, paragraph: { indent: { left: 520, hanging: 360 } } },
        }],
      },
      {
        reference: "flechas",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "→", alignment: AlignmentType.LEFT,
          style: { run: { color: BLUE, bold: true, font: FONT }, paragraph: { indent: { left: 520, hanging: 360 } } },
        }],
      },
      {
        reference: "campos",
        levels: [{
          level: 0, format: LevelFormat.BULLET, text: "▪", alignment: AlignmentType.LEFT,
          style: { run: { color: BLUE, font: FONT }, paragraph: { indent: { left: 460, hanging: 260 } } },
        }],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840, orientation: PageOrientation.PORTRAIT },
          margin: { top: 1296, right: 1440, bottom: 1296, left: 1440, footer: 680 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              style: "PieDePagina",
              border: { top: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 6 } },
              tabStops: [{ type: "right", position: W }],
              children: [
                t(FOOTER_TEXT, { size: 17, color: "808080" }),
                t("\t", { size: 17 }),
                t("Página ", { size: 17, color: "808080" }),
                new TextRun({ children: [PageNumber.CURRENT], size: 17, color: "808080" }),
                t(" de ", { size: 17, color: "808080" }),
                new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 17, color: "808080" }),
              ],
            }),
          ],
        }),
      },
      children,
    },
  ],
});

Packer.toBuffer(doc).then((b) => {
  fs.writeFileSync("Manual_Auditor_CGE.docx", b);
  console.log("ok");
});
