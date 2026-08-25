const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle, LevelFormat,
} = require("docx");

const AZUL = "1F3864", AZUL2 = "2E5C9A", ROJO = "9C1B1B";

const H1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 140 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 8, color: AZUL2, space: 4 } },
  children: [new TextRun({ text, bold: true, size: 27, color: AZUL, font: "Calibri" })],
});

const P = (runs, o = {}) => new Paragraph({
  spacing: { after: o.after === undefined ? 120 : o.after, line: 276 },
  indent: o.indent,
  children: (typeof runs === "string" ? [{ t: runs }] : runs).map(r => new TextRun({
    text: r.t, bold: r.b, italics: r.i || o.italics, size: r.size || o.size || 21,
    color: r.color || o.color, font: "Calibri",
  })),
});

const NUM = (runs) => new Paragraph({
  numbering: { reference: "pasos", level: 0 }, spacing: { after: 100, line: 276 },
  children: (typeof runs === "string" ? [{ t: runs }] : runs).map(r =>
    new TextRun({ text: r.t, bold: r.b, size: 21, font: "Calibri", color: r.color })),
});

const BUL = (runs) => new Paragraph({
  numbering: { reference: "vinetas", level: 0 }, spacing: { after: 90, line: 276 },
  children: (typeof runs === "string" ? [{ t: runs }] : runs).map(r =>
    new TextRun({ text: r.t, bold: r.b, italics: r.i, size: 21, font: "Calibri", color: r.color })),
});

const doc = new Document({
  creator: "Auditoría CGE",
  title: "Cómo hacer copias en Workiva",
  numbering: { config: [
    { reference: "pasos", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 440, hanging: 290 } } } }] },
    { reference: "vinetas", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 440, hanging: 240 } } } }] },
  ] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1080, bottom: 1080, left: 1080, right: 1080 } } },
    children: [
      new Paragraph({ spacing: { after: 40 },
        children: [new TextRun({ text: "Cómo hacer copias en Workiva", bold: true, size: 40, color: AZUL, font: "Calibri" })] }),
      new Paragraph({ spacing: { after: 240 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 10, color: AZUL2, space: 5 } },
        children: [new TextRun({ text: "Files → clic derecho → Copy", size: 22, color: "555555", font: "Calibri" })] }),

      H1("Los pasos"),
      NUM([{ t: "Clic derecho sobre la carpeta (o el archivo) en Files y elija " }, { t: "Copy", b: true }, { t: "." }]),
      NUM([{ t: "Revise la lista de archivos incluidos y presione " }, { t: "Next", b: true }, { t: ". Los Filings nunca se copian." }]),
      NUM([{ t: "En " }, { t: "Copy includes", b: true }, { t: ", marque o desmarque las casillas según la lista de abajo." }]),
      NUM([{ t: "Revise el desplegable de " }, { t: "Links and Process References", b: true }, { t: ": es la única opción que puede arruinar la copia." }]),
      NUM([{ t: "En " }, { t: "Location Settings", b: true }, { t: ", escriba el " }, { t: "New Folder Name", b: true },
           { t: " del período nuevo y elija el " }, { t: "Location", b: true }, { t: ": la carpeta del año, no la del mes anterior." }]),
      NUM([{ t: "Presione " }, { t: "Copy", b: true }, { t: ". La copia corre en segundo plano y llega un aviso por correo cuando termina." }]),

      H1("Qué marcar en Copy includes"),
      P("Entre paréntesis va el estado con que viene cada casilla por defecto."),
      BUL([{ t: "All comments", b: true }, { t: " (desmarcada): déjela así. Los comentarios del período anterior ya no aplican." }]),
      BUL([{ t: "Outline labels", b: true }, { t: " (marcada): desmárquela, o el período nuevo nace con secciones marcadas como revisadas." }]),
      BUL([{ t: "Attachments", b: true }, { t: " (desmarcada): márquela solo si los adjuntos son parte fija del reporte y no evidencia del período." }]),
      BUL([{ t: "Automations", b: true }, { t: " (marcada): déjela marcada." }]),
      BUL([{ t: "Document Markup", b: true }, { t: " (desmarcada): déjela así. El marcado es evidencia de la revisión del período anterior." }]),
      BUL([{ t: "Links and Process References", b: true }, { t: " (marcada): déjela marcada y revise su desplegable — ver más abajo." }]),
      BUL([{ t: "Maintain managed destination links", b: true }, { t: " e " }, { t: "Include metadata for all source smart links", b: true },
           { t: " (ambas marcadas): déjelas marcadas; conservan los enlaces de destino y los nombres de los smart links." }]),
      BUL([{ t: "Connections", b: true }, { t: " (marcada): déjela marcada, con “Incoming and outgoing connections”." }]),
      BUL([{ t: "Input cell values", b: true }, { t: " (desmarcada): déjela así; los datos del período se cargan de cero." }]),
      BUL([{ t: "Input mode in enabled sections", b: true }, { t: " (desmarcada): márquela si el equipo carga datos con Input Mode." }]),

      H1("El desplegable que hay que mirar sí o sí"),
      P([{ t: "Links and Process References viene siempre en " }, { t: "“Create copies of all source files”", b: true },
         { t: ": duplica también los archivos fuente y enlaza la copia a esos duplicados. Eso es lo correcto cuando las fuentes son del período y avanzan con él." }]),
      P([{ t: "Si las fuentes viven fuera de la carpeta y son únicas y permanentes, hay que cambiarlo a mano a " },
         { t: "“Keep links to original source files”", b: true },
         { t: ": no crea copias de las fuentes y la copia sigue leyendo de las originales." }]),
      P([{ t: "Elegir mal deja el período nuevo mostrando cifras del anterior, o llena el workspace de duplicados que nadie pidió.",
           color: ROJO, b: true }]),

      H1("Después de copiar"),
      BUL("Abra dos o tres archivos y verifique que sus enlaces apunten a donde usted decidió, no al período anterior."),
      BUL("Actualice las fechas dentro de documentos y planillas, y revise Document Health."),
      BUL("Confirme que la carpeta quedó en la ubicación correcta y con el nombre del período nuevo."),
      BUL([{ t: "Mantenga la nomenclatura: prefijos (CHN) / (LC) y código de sociedad (E110, E200, E205…) sin alterar, o los scripts del Auditor dejan de reconocer los archivos." }]),

      P([{ t: "Referencia: Workiva Support Center — “Copy a file or folder” (support.workiva.com/hc/en-us/articles/360035639992)." }],
        { italics: true, color: "777777", size: 18, after: 0 }),
    ],
  }],
});

Packer.toBuffer(doc).then(b => {
  fs.writeFileSync(process.argv[2] || "Guia_Copias_Workiva.docx", b);
  console.log("OK", (b.length / 1024).toFixed(1) + " KB");
});
