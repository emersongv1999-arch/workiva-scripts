const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, AlignmentType, VerticalAlign,
  HeadingLevel, LevelFormat, Footer, PageNumber, convertInchesToTwip,
  PageOrientation,
} = require("docx");

/* ---------- design tokens ---------- */
const NAVY   = "1F3864";  // titles / headings
const BLUE   = "2E74B5";  // accent
const INK    = "262626";  // body text
const MUTED  = "44546A";  // lead paragraph
const RULE   = "D6DCE4";  // hairlines
const ZEBRA  = "F4F7FB";  // banded rows
const CALLOUT= "EAF0F7";  // note background
const CANVAS = "F7F9FB";  // diagram background

const FONT = "Calibri";
const MONO = "Consolas";

const CONTENT_W = 9360; // 12240 (Letter) - 2 * 1440 margins

const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const hair = (color = RULE) => ({ style: BorderStyle.SINGLE, size: 4, color });

/* ---------- helpers ---------- */

// Body paragraph, justified.
const body = (children, opts = {}) =>
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 140, line: 276 },
    ...opts,
    children: (Array.isArray(children) ? children : [new TextRun(children)]),
  });

const t = (text, opts = {}) => new TextRun({ text, ...opts });

const h1 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_1 });

const h2 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_2 });

const bullet = (text) =>
  new Paragraph({
    text,
    numbering: { reference: "vinetas", level: 0 },
    spacing: { after: 60, line: 276 },
  });

// Data table with dark header band, zebra rows and horizontal hairlines only.
function dataTable(header, rows, widths, centeredCols = []) {
  const cellMargins = { top: 90, bottom: 90, left: 140, right: 140 };

  const headerRow = new TableRow({
    tableHeader: true,
    cantSplit: true,
    children: header.map((text, i) =>
      new TableCell({
        width: { size: widths[i], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, color: "auto", fill: NAVY },
        margins: cellMargins,
        verticalAlign: VerticalAlign.CENTER,
        children: [
          new Paragraph({
            alignment: centeredCols.includes(i) ? AlignmentType.CENTER : AlignmentType.LEFT,
            spacing: { before: 20, after: 20 },
            children: [t(text, { bold: true, color: "FFFFFF", size: 21 })],
          }),
        ],
      })
    ),
  });

  const bodyRows = rows.map((cells, r) =>
    new TableRow({
      cantSplit: true,
      children: cells.map((text, i) =>
        new TableCell({
          width: { size: widths[i], type: WidthType.DXA },
          shading: {
            type: ShadingType.CLEAR,
            color: "auto",
            fill: r % 2 === 0 ? "FFFFFF" : ZEBRA,
          },
          margins: cellMargins,
          verticalAlign: VerticalAlign.CENTER,
          children: [
            new Paragraph({
              alignment: centeredCols.includes(i) ? AlignmentType.CENTER : AlignmentType.LEFT,
              spacing: { before: 20, after: 20, line: 264 },
              children: [
                t(text, {
                  size: 21,
                  bold: i === 0,
                  color: i === 0 ? NAVY : INK,
                }),
              ],
            }),
          ],
        })
      ),
    })
  );

  return new Table({
    columnWidths: widths,
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA },
    borders: {
      top: hair(NAVY),
      bottom: hair(NAVY),
      left: noBorder,
      right: noBorder,
      insideHorizontal: hair(),
      insideVertical: noBorder,
    },
    rows: [headerRow, ...bodyRows],
  });
}

// Framed callout: light fill, thick accent bar on the left.
function callout(paragraphs, { fill = CALLOUT, bar = BLUE } = {}) {
  return new Table({
    columnWidths: [CONTENT_W],
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: {
      top: noBorder, bottom: noBorder, right: noBorder,
      left: { style: BorderStyle.SINGLE, size: 18, color: bar },
      insideHorizontal: noBorder, insideVertical: noBorder,
    },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: CONTENT_W, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, color: "auto", fill },
            margins: { top: 160, bottom: 160, left: 220, right: 220 },
            children: paragraphs,
          }),
        ],
      }),
    ],
  });
}

// Thin spacer paragraph.
const spacer = (after = 120) =>
  new Paragraph({
    spacing: { before: 0, after, line: 120, lineRule: "exact" },
    children: [t("", { size: 10 })],
  });

/* ---------- content ---------- */

const TITLE = "Arquitectura de Workiva";

const flow = [
  [["SAP BPC", "node"]],
  [["   │  Carga de asientos contables del período"]],
  [["   ▼"]],
  [["Workiva Chains", "node"]],
  [["   │  Ejecución automática o manual de cadenas"]],
  [["   ▼"]],
  [["Workiva Wdata", "node"]],
  [["   │  Query's, tablas y conexiones"]],
  [["   ├──► "], ["Individual", "node"]],
  [["   ├──► "], ["Consolidado", "node"]],
  [["   └──► "], ["Combinado", "node"]],
  [["            │  Conexión ◄── Hoja Bases (parámetros)"]],
  [["            ▼"]],
  [["Workiva Wdesk", "node"], ["                ◄── Notas Personas (linking)"]],
  [["   Estados Financieros", "node"], ["       ◄── Activo Fijo (linking)"]],
  [["   Individual / Consolidado / Combinado"]],
  [["            │  Validación y ajustes manuales"]],
  [["            │  Linking"]],
  [["            ├──► "], ["Informes Word (ESP)", "node"], [" ──► "], ["Informes Word (ING)", "node"]],
  [["            ├──► "], ["Presentaciones PPT", "node"]],
  [["            ├──► "], ["Monitor", "node"]],
  [["            └──► "], ["Reportes (Local / Chino)", "node"]],
];

const flowParagraphs = flow.map((segments) =>
  new Paragraph({
    spacing: { before: 0, after: 0, line: 202, lineRule: "exact" },
    children: segments.map(([text, kind]) =>
      t(text, {
        font: MONO,
        size: 17,
        bold: kind === "node",
        color: kind === "node" ? NAVY : "595959",
      })
    ),
  })
);

const children = [
  /* ----- portada / encabezado ----- */
  new Paragraph({
    spacing: { before: 0, after: 60 },
    children: [t(TITLE, { bold: true, size: 52, color: NAVY, font: FONT })],
  }),
  new Paragraph({
    spacing: { after: 240 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 18, color: BLUE, space: 6 } },
    children: [],
  }),
  new Paragraph({
    alignment: AlignmentType.JUSTIFIED,
    spacing: { after: 120, line: 288 },
    children: [
      t(
        "Este documento presenta una descripción detallada de los procesos involucrados en la elaboración de los Estados Financieros en Workiva, considerando las distintas fuentes de información.",
        { size: 23, color: MUTED, font: FONT }
      ),
    ],
  }),

  /* ----- 1 ----- */
  h1("1. Sistemas involucrados"),
  dataTable(
    ["Sistema", "Rol en el proceso"],
    [
      ["SAP BPC", "Fuente principal y primordial, donde se originan la mayoría de los datos para la generación de los Estados Financieros."],
      ["Workiva (Chains)", "Herramienta que une SAP HANA y Workiva, permitiendo la automatización del traspaso de datos entre ambas plataformas."],
      ["Workiva (Wdata)", "Plataforma utilizada para la creación de Query's (consultas), las cuales permiten la automatización del armado y la actualización de las notas de los Estados Financieros."],
      ["Workiva (Wdesk)", "Plataforma final donde se visualizan los cambios y actualizaciones realizadas en los Estados Financieros. Además, en esta plataforma se efectúan los ajustes manuales que no pueden ser automatizados."],
    ],
    [2340, 7020]
  ),
  spacer(200),
  callout([
    new Paragraph({
      alignment: AlignmentType.JUSTIFIED,
      spacing: { after: 0, line: 264 },
      children: [
        t("Nota: ", { bold: true, color: NAVY, size: 21 }),
        t(
          "Wdata y Wdesk, si bien ambas pertenecen a Workiva, cumplen funciones distintas. Wdata almacena y estructura el dato; Wdesk construye y presenta el documento. La frontera entre ambas es la conexión, punto en el cual el proceso admite intervención manual.",
          { size: 21, color: INK }
        ),
      ],
    }),
  ]),

  /* ----- 2 ----- */
  h1("2. Carga SAP BPC"),
  body("Corresponde al proceso de carga de los asientos contables para el período financiero correspondiente. La información generada es la base principal e inicial del proceso de armado de los Estados Financieros."),
  body("Todo el proceso posterior hereda el contenido y la oportunidad de esta carga."),

  h2("2.1 Proceso de consolidación y ejecución de Workiva Chains"),
  body("Posterior a la carga de información en SAP BPC, se ejecuta la cadena de Workiva (Chains), permitiendo la integración y transferencia de datos hacia Workiva para la continuidad del proceso de armado de los Estados Financieros."),
  body("La ejecución de las cadenas puede realizarse de forma automática o manual, según corresponda."),

  h2("2.2 Ejecución de cadenas en Workiva Chains"),
  body("Durante el proceso de armado de los Estados Financieros, se deben ejecutar las siguientes cadenas en Workiva Chains para asegurar la correcta actualización e integración de la información:"),
  dataTable(
    ["N°", "Cadena", "Estado"],
    [
      ["1", "Carga data cubo – Job", "Operativa"],
      ["2", "Carga cuenta agrupador V2", "Operativa"],
      ["3", "Refrescar conexiones consolidados", "Pendiente por aprobar"],
    ],
    [900, 5460, 3000],
    [0, 2]
  ),
  spacer(200),
  body("Mientras la tercera cadena no se encuentre aprobada, el refresco de las conexiones de consolidados debe realizarse de forma manual."),

  h2("2.3 Query's y conexiones en Workiva (Wdata)"),
  body("En Workiva (Wdata) se encuentran almacenadas las Query's, tablas y conexiones utilizadas durante el proceso de armado de los Estados Financieros. Estas Query's son utilizadas en las hojas de cálculo y reportes de Workiva (Wdesk), permitiendo la conexión y actualización automatizada de la información financiera."),
  body("La información se materializa en tres tablas paralelas dentro de Wdata, según el nivel de agregación requerido:"),
  bullet("Individual"),
  bullet("Consolidado"),
  bullet("Combinado"),
  body("Esta estructura de tres niveles se mantiene de forma consistente en las etapas posteriores del proceso.", { spacing: { before: 120, after: 140, line: 276 } }),

  /* ----- 3 ----- */
  h1("3. Generación y actualización de Estados Financieros en Wdesk"),
  body("Posterior a la integración de información en Workiva, se realiza la generación y actualización de los archivos correspondientes para los meses y trimestres asociados a los Estados Financieros en Workiva (Wdesk). Para este proceso se utilizan conexiones, queries y hojas de cálculo previamente configuradas, las cuales permiten automatizar el armado y actualización de la información financiera presentada en los distintos reportes."),
  body("Los archivos generados en esta etapa —Individual, Consolidado y Combinado— constituyen el núcleo del proceso: desde ellos se derivan posteriormente los informes, presentaciones y reportes finales."),

  h2("3.1 Actualización de hojas de cálculo"),
  body("Luego de la generación de los archivos correspondientes en Workiva (Wdesk), se ejecuta la actualización de las conexiones configuradas en las hojas de cálculo de Estados Financieros individuales, consolidados y combinados. Estas conexiones permiten consumir información desde Workiva (Wdata), asegurando la actualización automática de datos financieros dentro de reportes, tablas y notas asociadas."),

  h2("3.2 Actualización \"Hoja Bases\""),
  body("Luego de actualizar las conexiones de las hojas de cálculo, se realiza la actualización de la hoja \"Bases\". En esta hoja se encuentran los parámetros utilizados para la correcta confección de los Estados Financieros, tales como:"),
  bullet("Fechas del período y su comparativo"),
  bullet("Traducciones"),
  bullet("Conversión de monedas"),
  bullet("Otros datos de referencia necesarios para el proceso"),
  body("La hoja Bases constituye el único punto de configuración del período dentro del proceso, por lo que su correcta actualización condiciona el resultado de todas las hojas dependientes.", { spacing: { before: 120, after: 140, line: 276 } }),

  h2("3.3 Insumos externos vinculados"),
  body([
    t("Adicionalmente a la información proveniente de Wdata, los archivos de Estados Financieros incorporan mediante vinculación ("),
    t("linking", { italics: true }),
    t(") dos insumos que se elaboran fuera del proceso automatizado:"),
  ]),
  dataTable(
    ["Insumo", "Origen"],
    [
      ["Notas Personas", "Elaboración manual por el área correspondiente"],
      ["Activo Fijo", "Proceso propio, con cierre local y cierre chino"],
    ],
    [2820, 6540]
  ),
  spacer(200),
  body("Al tratarse de dependencias externas, la oportunidad y calidad de estos archivos condiciona el cierre, con independencia del correcto funcionamiento de las cadenas y conexiones."),

  h2("3.4 Validación y ajustes manuales"),
  body("Posterior a la actualización de las conexiones de Wdata, se realiza la validación de la información financiera reflejada en los Estados Financieros. A su vez, se ingresan manualmente aquellas notas y ajustes que no forman parte del proceso automatizado mediante conexiones y queries."),
  body("Esta etapa constituye el único punto del proceso en que la información puede modificarse sin trazabilidad directa hacia SAP BPC, por lo que requiere registro y control específico."),

  /* ----- 4 ----- */
  h1("4. Distribución hacia entregables"),
  body([
    t("Una vez validados los Estados Financieros, la información se propaga mediante vinculación ("),
    t("linking", { italics: true }),
    t(") hacia los distintos entregables:"),
  ]),
  dataTable(
    ["Destino", "Observación"],
    [
      ["Informes Word (Español)", "Documento narrativo por sociedad"],
      ["Informes Word (Inglés)", "Se generan por traducción desde la versión en español, no directamente desde los datos"],
      ["Presentaciones (PPT)", "Comité ejecutivo e informes detallados, en distintas unidades monetarias e idiomas"],
      ["Monitor", "Archivo de seguimiento del estado del cierre"],
      ["Reportes", "Se emiten en dos versiones: local y chino"],
    ],
    [3060, 6300]
  ),
  spacer(200),
  body("Dado que la versión en inglés deriva de la versión en español, cualquier modificación posterior en esta última requiere rehacer la traducción correspondiente."),

  /* ----- 5 ----- */
  h1("5. Resumen del flujo"),
  new Table({
    columnWidths: [CONTENT_W],
    width: { size: CONTENT_W, type: WidthType.DXA },
    borders: {
      top: hair(), bottom: hair(), left: hair(), right: hair(),
      insideHorizontal: noBorder, insideVertical: noBorder,
    },
    rows: [
      new TableRow({
        cantSplit: true,
        children: [
          new TableCell({
            width: { size: CONTENT_W, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, color: "auto", fill: CANVAS },
            margins: { top: 150, bottom: 150, left: 280, right: 220 },
            children: flowParagraphs,
          }),
        ],
      }),
    ],
  }),

  /* ----- 6 ----- */
  h1("6. Consideraciones del proceso"),
  body([
    t("Concentración de dependencias.", { bold: true, color: NAVY }),
    t(" Los archivos de Estados Financieros en Wdesk constituyen el punto de convergencia de todo el proceso. Los informes Word, presentaciones, Monitor y Reportes dependen de ellos mediante vinculación, por lo que una inconsistencia en esta etapa se propaga simultáneamente a todos los entregables."),
  ]),
  body([
    t("Dos mecanismos de actualización.", { bold: true, color: NAVY }),
    t(" El proceso emplea "),
    t("conexiones", { italics: true }),
    t(" (Wdata hacia Wdesk, y Bases hacia las hojas) para la carga de datos y parámetros, y "),
    t("linking", { italics: true }),
    t(" para la vinculación entre archivos de Wdesk. Ambos propagan cambios de forma automática."),
  ]),
  body([
    t("Secuencialidad de la traducción.", { bold: true, color: NAVY }),
    t(" Los informes en inglés no se generan de forma paralela a los de español, sino derivada. Se recomienda cerrar la versión en español antes de iniciar el proceso de traducción."),
  ]),
];

/* ---------- document ---------- */

const doc = new Document({
  title: TITLE,
  creator: "Emerson Garrido Villarroel",
  description: TITLE,
  styles: {
    default: {
      document: {
        run: { font: FONT, size: 22, color: INK },
        paragraph: { spacing: { line: 276, after: 140 } },
      },
    },
    paragraphStyles: [
      {
        id: "Heading1",
        name: "Heading 1",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: FONT, size: 30, bold: true, color: NAVY },
        paragraph: {
          spacing: { before: 400, after: 180 },
          keepNext: true,
          outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: RULE, space: 4 } },
        },
      },
      {
        id: "PieDePagina",
        name: "Pie de pagina",
        basedOn: "Normal",
        next: "Normal",
        run: { font: FONT, size: 17, color: "808080" },
        paragraph: { spacing: { before: 0, after: 0, line: 240 } },
      },
      {
        id: "Heading2",
        name: "Heading 2",
        basedOn: "Normal",
        next: "Normal",
        quickFormat: true,
        run: { font: FONT, size: 25, bold: true, color: BLUE },
        paragraph: {
          spacing: { before: 280, after: 100 },
          keepNext: true,
          outlineLevel: 1,
        },
      },
    ],
  },
  numbering: {
    config: [
      {
        reference: "vinetas",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "▪",
            alignment: AlignmentType.LEFT,
            style: {
              run: { color: BLUE, font: FONT, size: 22 },
              paragraph: { indent: { left: 460, hanging: 260 } },
            },
          },
        ],
      },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840, orientation: PageOrientation.PORTRAIT },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440, footer: 720 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              style: "PieDePagina",
              spacing: { before: 0, after: 0 },
              border: { top: { style: BorderStyle.SINGLE, size: 4, color: RULE, space: 6 } },
              tabStops: [{ type: "right", position: CONTENT_W }],
              children: [
                t(TITLE, { size: 17, color: "808080" }),
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

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("Arquitectura_de_Workiva_V2.docx", buf);
  console.log("ok");
});
