const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  Header, Footer, PageNumber, TabStopType, convertInchesToTwip
} = require("docx");
const fs = require("fs");

const W = 10080;                 // content width, DXA
const NAVY = "1F3552", INK = "1A1F26", MUTED = "5B6673";
const OK = "2D6A48", WARN = "8A5D10", GAP = "9E2F29";
const BG = "EEF1F5", BGWARN = "FBF3E2", BGGAP = "F8E7E5", BGHEAD = "E3E9F0";
const SERIF = "Georgia", SANS = "Calibri", MONO = "Consolas";

const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const hair = (c) => ({ style: BorderStyle.SINGLE, size: 4, color: c });

/* ---------- text helpers ---------- */
// rich(): "**bold**" segments inside a plain string
function runs(text, opts = {}) {
  const base = { font: opts.font || SANS, size: opts.size || 20, color: opts.color || INK };
  return String(text).split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map(seg => {
    if (seg.startsWith("**") && seg.endsWith("**"))
      return new TextRun({ ...base, text: seg.slice(2, -2), bold: true });
    return new TextRun({ ...base, text: seg, italics: opts.italics || false });
  });
}
const P = (text, o = {}) => new Paragraph({
  children: runs(text, o),
  spacing: { before: o.before ?? 0, after: o.after ?? 140, line: o.line ?? 264 },
  alignment: o.align, indent: o.indent, shading: o.shading, border: o.border,
  keepNext: o.keepNext, keepLines: o.keepLines,
});
const bullet = (text, o = {}) => new Paragraph({
  children: runs(text, o),
  bullet: { level: 0 },
  spacing: { after: o.after ?? 90, line: 264 },
  indent: { left: o.left ?? 360, hanging: 200 },
  shading: o.shading,
});
const spacer = (h = 120) => new Paragraph({ text: "", spacing: { after: h } });

/* ---------- headings ---------- */
const H1 = (t) => new Paragraph({
  children: [new TextRun({ text: t, font: SERIF, size: 30, bold: true, color: NAVY })],
  heading: HeadingLevel.HEADING_1,
  spacing: { before: 400, after: 60 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 6 } },
  keepNext: true,
});
const H2 = (ref, t, statusLabel, statusColor) => new Paragraph({
  children: [
    new TextRun({ text: ref + "  ", font: MONO, size: 19, bold: true, color: NAVY }),
    new TextRun({ text: t, font: SERIF, size: 23, bold: true, color: INK }),
    new TextRun({ text: "   " + statusLabel.toUpperCase(), font: MONO, size: 16, bold: true, color: statusColor }),
  ],
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 320, after: 40 },
  keepNext: true,
});
const NORMS = (t) => new Paragraph({
  children: [new TextRun({ text: t, font: MONO, size: 16, color: MUTED })],
  spacing: { after: 140 }, keepNext: true,
});
const LABEL = (t) => new Paragraph({
  children: [new TextRun({ text: t.toUpperCase(), font: SANS, size: 16, bold: true, color: NAVY, characterSpacing: 20 })],
  spacing: { before: 130, after: 50 }, keepNext: true,
});

/* ---------- proposal block ---------- */
const propBorder = {
  top: NONE,
  left: { style: BorderStyle.SINGLE, size: 18, color: NAVY, space: 10 },
  bottom: NONE, right: NONE,
};
function propHead(sub) {
  return new Paragraph({
    children: [
      new TextRun({ text: "TEXTO PROPUESTO", font: SANS, size: 17, bold: true, color: NAVY, characterSpacing: 20 }),
      new TextRun({ text: "  " + sub, font: SANS, size: 17, italics: true, color: MUTED }),
    ],
    spacing: { before: 200, after: 70 }, shading: { type: ShadingType.CLEAR, fill: BG },
    border: propBorder, keepNext: true,
  });
}
const propP = (t, o = {}) => new Paragraph({
  children: runs(t, { font: SERIF, size: 20, ...o }),
  spacing: { after: o.after ?? 110, line: 268 },
  shading: { type: ShadingType.CLEAR, fill: BG }, border: propBorder,
});
const propBullet = (t) => new Paragraph({
  children: runs(t, { font: SERIF, size: 20 }),
  bullet: { level: 0 }, spacing: { after: 80, line: 268 },
  indent: { left: 620, hanging: 200 },
  shading: { type: ShadingType.CLEAR, fill: BG }, border: propBorder,
});
const propTail = () => new Paragraph({ text: "", spacing: { after: 40 }, shading: { type: ShadingType.CLEAR, fill: BG }, border: propBorder });

const todo = (t) => new Paragraph({
  children: [
    new TextRun({ text: "Pendiente / validar. ", font: SANS, size: 18, bold: true, color: WARN }),
    ...runs(t, { size: 18, color: INK }),
  ],
  spacing: { before: 40, after: 200, line: 260 },
  shading: { type: ShadingType.CLEAR, fill: BGWARN },
  border: {
    top: NONE,
    left: { style: BorderStyle.SINGLE, size: 18, color: WARN, space: 10 },
    bottom: NONE, right: NONE,
  },
});

const alertBox = (title, body) => [
  new Paragraph({
    children: [new TextRun({ text: title.toUpperCase(), font: SANS, size: 18, bold: true, color: GAP, characterSpacing: 20 })],
    spacing: { before: 80, after: 60 },
    shading: { type: ShadingType.CLEAR, fill: BGGAP },
    border: { top: NONE, left: { style: BorderStyle.SINGLE, size: 20, color: GAP, space: 10 }, bottom: NONE, right: NONE },
    keepNext: true,
  }),
  new Paragraph({
    children: runs(body, { size: 20 }),
    spacing: { after: 200, line: 268 },
    shading: { type: ShadingType.CLEAR, fill: BGGAP },
    border: { top: NONE, left: { style: BorderStyle.SINGLE, size: 20, color: GAP, space: 10 }, bottom: NONE, right: NONE },
  }),
];

/* ---------- tables ---------- */
function cell(content, w, o = {}) {
  const kids = Array.isArray(content) ? content : [new Paragraph({
    children: o.bold
      ? [new TextRun({ text: String(content), font: o.font || SANS, size: o.size || 18, color: o.color || INK, bold: true })]
      : runs(content, { size: o.size || 18, font: o.font || SANS, color: o.color || INK }),
    spacing: { before: 40, after: 40, line: 240 }, alignment: o.align,
  })];
  return new TableCell({
    children: kids, width: { size: w, type: WidthType.DXA },
    shading: o.fill ? { type: ShadingType.CLEAR, fill: o.fill } : undefined,
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
    verticalAlign: "top",
  });
}
function headCell(t, w, align) {
  return new TableCell({
    children: [new Paragraph({
      children: [new TextRun({ text: t.toUpperCase(), font: SANS, size: 15, bold: true, color: NAVY, characterSpacing: 16 })],
      spacing: { before: 50, after: 50 }, alignment: align,
    })],
    width: { size: w, type: WidthType.DXA },
    shading: { type: ShadingType.CLEAR, fill: BGHEAD },
    margins: { top: 60, bottom: 60, left: 110, right: 110 },
  });
}
function mkTable(widths, headers, rows) {
  const tblRows = [];
  if (headers) tblRows.push(new TableRow({
    tableHeader: true,
    children: headers.map((h, i) => headCell(typeof h === "string" ? h : h.t, widths[i], (h.align))),
  }));
  rows.forEach((r) => {
    tblRows.push(new TableRow({
      children: r.map((c, i) => {
        const o = (typeof c === "object" && !Array.isArray(c)) ? c : { t: c };
        return cell(o.t, widths[i], o);
      }),
    }));
  });
  return new Table({
    columnWidths: widths, width: { size: W, type: WidthType.DXA }, rows: tblRows,
    borders: {
      top: hair("C8D0DA"), left: hair("C8D0DA"), bottom: hair("C8D0DA"), right: hair("C8D0DA"),
      insideHorizontal: hair("DCE2EA"), insideVertical: hair("DCE2EA"),
    },
  });
}
const NUM = (t) => ({ t, font: MONO, size: 17, align: AlignmentType.RIGHT });
const REF = (t) => ({ t, font: MONO, size: 17, color: NAVY });
const ST = (t, c) => ({ t, size: 17, color: c });

/* =========================================================
   CONTENT
   ========================================================= */
const body = [];

/* --- title --- */
body.push(new Paragraph({
  children: [new TextRun({ text: "REVISIÓN DE CUMPLIMIENTO NORMATIVO", font: SANS, size: 17, bold: true, color: MUTED, characterSpacing: 40 })],
  spacing: { after: 90 },
}));
body.push(new Paragraph({
  children: [new TextRun({ text: "Oficio CMF N° 95881 frente a los EE.FF. consolidados de CGE al 30 de junio de 2026", font: SERIF, size: 38, bold: true, color: NAVY })],
  spacing: { after: 130, line: 400 },
}));
body.push(new Paragraph({
  children: [new TextRun({ text: "Contraste observación por observación entre lo que exige la Comisión para el Mercado Financiero y lo que efectivamente revelan las notas del estado financiero intermedio, con el texto propuesto para cada brecha.", font: SANS, size: 21, color: "39424F" })],
  spacing: { after: 260, line: 300 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: NAVY, space: 10 } },
}));

body.push(mkTable([2700, 7380], null, [
  [{ t: "Oficio", size: 18, color: MUTED, fill: "F5F7F9" }, { t: "OF. ORD. N° 95881, de 05 de junio de 2026 — Comisión para el Mercado Financiero", size: 19 }],
  [{ t: "Folio CMF", size: 18, color: MUTED, fill: "F5F7F9" }, { t: "2026958813453348 · SGD 2026060377813", size: 19, font: MONO }],
  [{ t: "Documento revisado", size: 18, color: MUTED, fill: "F5F7F9" }, { t: "E200 (ESP) — EE.FF. 06-2026 — Compañía General de Electricidad S.A. y subsidiarias", size: 19 }],
  [{ t: "Primera aplicación exigida", size: 18, color: MUTED, fill: "F5F7F9" }, { t: "Información financiera al 30 de junio de 2026 y posteriores", size: 19 }],
  [{ t: "Antecedentes revisados por CMF", size: 18, color: MUTED, fill: "F5F7F9" }, { t: "Estados financieros al 31 de diciembre de 2025 y al 31 de marzo de 2026", size: 19 }],
]));
body.push(spacer(240));

/* --- resumen --- */
body.push(H1("Resumen"));
body.push(P("Se contrastaron las quince exigencias contenidas en el oficio contra las notas del estado financiero intermedio al 30 de junio de 2026. La mayor parte del oficio ya está respondida: las notas 4.2, 5.1.2, 8.1.4 y 26.6.3 fueron reescritas y cubren el fondo de lo solicitado. Lo que resta son brechas de cierre, dos de ellas con exposición relevante.", { before: 120 }));

body.push(mkTable([2520, 2520, 2520, 2520], null, [
  [
    { t: [new Paragraph({ children: [new TextRun({ text: "5", font: SERIF, size: 44, bold: true, color: OK })], spacing: { after: 0 } }), new Paragraph({ children: [new TextRun({ text: "Cumplidas", font: SANS, size: 18, color: MUTED })], spacing: { after: 40 } })] },
    { t: [new Paragraph({ children: [new TextRun({ text: "5", font: SERIF, size: 44, bold: true, color: WARN })], spacing: { after: 0 } }), new Paragraph({ children: [new TextRun({ text: "Cumplidas con reparo", font: SANS, size: 18, color: MUTED })], spacing: { after: 40 } })] },
    { t: [new Paragraph({ children: [new TextRun({ text: "1", font: SERIF, size: 44, bold: true, color: GAP })], spacing: { after: 0 } }), new Paragraph({ children: [new TextRun({ text: "Incumplida", font: SANS, size: 18, color: MUTED })], spacing: { after: 40 } })] },
    { t: [new Paragraph({ children: [new TextRun({ text: "3", font: SERIF, size: 44, bold: true, color: NAVY })], spacing: { after: 0 } }), new Paragraph({ children: [new TextRun({ text: "En el Análisis Razonado", font: SANS, size: 18, color: MUTED })], spacing: { after: 40 } })] },
  ],
]));
body.push(spacer(200));

body.push(...alertBox("Riesgo prioritario antes de enviar",
  "La nota **5.1.2 Riesgo de tasa de interés**, redactada precisamente para responder la observación A.2.a, afirma que la Compañía mantiene derivados contratados para cubrir el riesgo de tasa de interés. La nota **7.1** no revela ningún derivado con ese tipo de cobertura: todos figuran como «Tipo de cambio». Es exactamente la clase de inconsistencia entre notas que la CMF objetó en A.2.b, ahora reintroducida en la respuesta a otra observación."));

/* --- índice de estado --- */
body.push(H1("Estado por observación"));
body.push(NORMS("Referencias según la numeración del propio oficio."));
body.push(mkTable([900, 3300, 900, 1900, 3080],
  ["Ref.", "Materia", "Nota", "Estado", "Brecha"],
  [
    [REF("A.1"), "Técnicas e inputs de valorización de derivados", { t: "4.2", font: MONO, size: 17 }, ST("Cumple", OK), "Falta la frase sobre cambios de técnica"],
    [REF("A.2.a"), "Políticas y procesos — riesgo de tasa de interés", { t: "5.1.2", font: MONO, size: 17 }, ST("Cumple con reparo", WARN), "Contradice la nota 7.1; párrafos sin separar"],
    [REF("A.2.b"), "Consistencia de la cobertura en UF", { t: "5.1.1 / 7.1", font: MONO, size: 17 }, ST("Cumple", OK), "Comparativo reetiquetado sin explicar"],
    [REF("A.3.a-i"), "Desglose de «Deudores varios»", { t: "8.1.2", font: MONO, size: 17 }, ST("Cumple con reparo", WARN), "M$ 24.799.523 corrientes sin desglosar"],
    [REF("A.3.a-ii"), "Desglose de cuentas por pagar", { t: "21", font: MONO, size: 17 }, ST("Cumple con reparo", WARN), "M$ 200.203.131 corrientes sin desglosar"],
    [REF("A.3.b-i"), "Datos, supuestos y método de la matriz ECL", { t: "8.1.4", font: MONO, size: 17 }, ST("Cumple", OK), "—"],
    [REF("A.3.b-ii"), "Agrupación colectiva de deudores", { t: "8.1.4", font: MONO, size: 17 }, ST("Cumple con reparo", WARN), "Nombres de clusters inconsistentes"],
    [REF("A.3.b-iii"), "Tratamiento y salida de clientes repactados", { t: "8.1.4", font: MONO, size: 17 }, ST("No cumple", GAP), "No existe política de salida"],
    [REF("A.3.c"), "Partidas del «(Aumento) disminución»", { t: "8.1.4", font: MONO, size: 17 }, ST("Cumple con reparo", WARN), "Causas sí, montos no"],
    [REF("A.3.d"), "Política de castigos financieros", { t: "8.1.4", font: MONO, size: 17 }, ST("Cumple", OK), "—"],
    [REF("A.4"), "Desglose de «Otras reservas»", { t: "26.6.3", font: MONO, size: 17 }, ST("Cumple", OK), "Signo invertido y encabezado errado"],
    [REF("A.5"), "Provisionados vs. pasivos contingentes", { t: "34", font: MONO, size: 17 }, ST("Cumple con reparo", WARN), "Falta NIC 37.86 (b), (c) y (d)"],
    [REF("B.1.a"), "Fórmulas de indicadores financieros", { t: "—", font: MONO, size: 17 }, ST("Otro documento", NAVY), "Análisis Razonado"],
    [REF("B.1.b"), "Análisis del flujo de efectivo directo", { t: "—", font: MONO, size: 17 }, ST("Otro documento", NAVY), "Análisis Razonado"],
    [REF("B.1.c"), "Áreas de negocios de CGE", { t: "—", font: MONO, size: 17 }, ST("Otro documento", NAVY), "Análisis Razonado"],
  ]));
body.push(spacer(160));

/* ======================= A ======================= */
body.push(H1("A. Estados financieros"));

/* A.1 */
body.push(H2("A.1", "Técnicas de valoración e inputs de los derivados de cobertura", "Cumple", OK));
body.push(NORMS("NIIF 13.93(d)  ·  Nota 4.2"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Revelar en el punto 4.2 una descripción de las técnicas de valoración y los datos de entrada utilizados en la medición del valor razonable de los derivados de cobertura, considerando que en la nota sobre «Otros Activos Financieros» se revela que dichos derivados se clasifican en Nivel II."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("Se incorporaron cuatro párrafos nuevos en la nota 4.2 que cubren la exigencia completa: valorización mark-to-market provista por las contrapartes financieras, modelos de flujos de caja descontados, y la enumeración de los datos de entrada —tipos de cambio spot y forward, curvas de tasas de interés, factores de descuento, montos nocionales, tasas, fechas de pago y vencimientos—. Se agrega el cálculo interno de los ajustes CVA y DVA y la conclusión de que, por ser observables los inputs significativos, los derivados se clasifican en Nivel II de la jerarquía de valor razonable."));
body.push(LABEL("Reparo menor"));
body.push(P("NIIF 13.93(d) también exige informar todo cambio en la técnica de valoración y la razón del cambio. Conviene cerrarlo de forma expresa."));
body.push(propHead("— agregar al final de la nota 4.2"));
body.push(propP("Durante el período terminado al 30 de junio de 2026 no se han producido cambios en las técnicas de valoración ni en los datos de entrada utilizados para determinar el valor razonable de los instrumentos derivados de cobertura respecto de los aplicados al 31 de diciembre de 2025, ni se han efectuado transferencias entre niveles de la jerarquía de valor razonable."));
body.push(propTail());
body.push(spacer(160));

/* A.2.a */
body.push(H2("A.2.a", "Políticas y procesos para la gestión del riesgo de tasa de interés", "Con reparo", WARN));
body.push(NORMS("NIIF 7.33(b)  ·  Nota 5.1.2"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Informar las políticas y procesos para la gestión del riesgo de tasa de interés. La versión objetada únicamente definía el riesgo y cuantificaba la sensibilidad."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("La nota fue reescrita e incorpora el objetivo de gestión —mantener una estructura equilibrada entre obligaciones a tasa fija y variable—, la gestión centralizada a nivel corporativo, el proceso de monitoreo periódico de la composición de la deuda, tasas de referencia, vencimientos, condiciones de mercado e impacto proyectado, y la evaluación de contratación o refinanciamiento y de instrumentos derivados. La exigencia de fondo queda cubierta."));
body.push(LABEL("Dos problemas que corregir antes de enviar"));
body.push(bullet("**Inconsistencia con la nota 7.1.** La nota 5.1.2 cierra afirmando que «Al cierre del período, la Compañía mantiene instrumentos derivados contratados para cubrir el riesgo de tasa de interés», y más arriba menciona «los derivados asociados a financiamientos a tasa variable que convierten su exposición a tasa fija». En la nota 7.1 todos los derivados figuran con «Tipo de cobertura: Tipo de cambio»; no existe ninguna fila de tasa de interés. Es el mismo defecto que la CMF observó en A.2.b."));
body.push(bullet("**Defecto de formato.** Los párrafos nuevos quedaron concatenados sin salto ni espacio tras el punto: «…tasas de interés variables.Las variaciones…», «…de la Compañía.En función…», «…gasto financiero.Al cierre…». Deben separarse en párrafos en Workiva."));
body.push(propHead("— reemplaza el párrafo final de la nota 5.1.2"));
body.push(propP("Al 30 de junio de 2026 la Compañía mantiene contratos de Cross Currency Swap designados como coberturas de tipo de cambio que, adicionalmente, transforman la tasa de interés variable de los financiamientos cubiertos en una tasa fija en pesos chilenos, según se detalla en la nota 7.1. La Compañía no mantiene instrumentos derivados designados exclusivamente como cobertura del riesgo de tasa de interés."));
body.push(propTail());
body.push(todo("Incorporar en la tabla de la nota 7.1 una columna o nota al pie que identifique, para cada Cross Currency Swap, si la operación fija también la tasa de interés del financiamiento subyacente. Si el efecto de conversión a tasa fija no existe, debe eliminarse esa mención en 5.1.2 y recalcularse el 24,89% de deuda a tasa variable, que en la nota se presenta ya neto de dicho efecto."));

/* A.2.b */
body.push(H2("A.2.b", "Consistencia entre la deuda en UF sin cobertura y los derivados por unidad de reajuste", "Cumple", OK));
body.push(NORMS("Nota 5.1.1  ·  Nota 7.1"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("La nota de riesgos informaba que la deuda financiera denominada en UF no estaba cubierta con ningún instrumento de cobertura, mientras la nota sobre otros activos financieros revelaba un activo por derivados de cobertura para la «Unidad de reajuste». Debían efectuarse las modificaciones o complementos para que la información fuese consistente."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("Resuelto. En la nota 7.1 desapareció la fila «Unidad de reajuste»: tanto el saldo al 30-06-2026 como el comparativo al 31-12-2025 por M$ 2.531.040 se presentan ahora como cobertura de «Tipo de cambio». El texto explica que el derivado en UF asociado al bono BCGEI-M N° 916 y el propio bono vencieron el 1 de diciembre de 2025, por lo que no correspondió renovar la cobertura. Ello es coherente con la nota 5.1.1, que informa un 48,20% de deuda financiera en UF sin instrumento de cobertura."));
body.push(LABEL("Reparo menor de trazabilidad"));
body.push(P("La CMF tiene a la vista la versión anterior, donde ese mismo saldo comparativo figuraba etiquetado como «Unidad de reajuste». El cambio de etiqueta del comparativo no está explicado y puede leerse como una reclasificación no revelada."));
body.push(propHead("— nota al pie de la tabla de activos de cobertura, nota 7.1"));
body.push(propP("El saldo comparativo al 31 de diciembre de 2025 se presenta bajo el tipo de cobertura «Tipo de cambio», corrigiendo la clasificación informada en estados financieros anteriores. La modificación afecta únicamente la descripción del tipo de cobertura y no altera los montos, la clasificación entre corriente y no corriente, ni los resultados reconocidos en el período."));
body.push(propTail());
body.push(spacer(160));

/* A.3.a-i */
body.push(H2("A.3.a · i", "Desglose corriente y no corriente de los «Deudores varios»", "Con reparo", WARN));
body.push(NORMS("Nota 8.1.2"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Desglosar los montos corrientes y no corrientes correspondientes a cada uno de los conceptos que originan los «Deudores varios» —aplicación de las Leyes N° 21.185 y N° 21.472, reliquidaciones asociadas al Decreto 5T-2024, entre otros—."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("La nota (*) identifica tres conceptos con sus montos: mecanismos de estabilización de las Leyes N° 21.185, N° 21.472 y N° 21.667; reliquidación del Decreto N° 5T-2024; y proceso tarifario VAD. **La porción no corriente cierra exacta**: M$ 135.688.042 + M$ 297.020.680 + M$ 173.639.706 = M$ 606.348.428, igual al saldo del cuadro."));
body.push(P("La porción corriente no cierra. Solo se desglosan M$ 238.169.651 de un total de M$ 262.969.174, quedando **M$ 24.799.523, equivalentes al 9,4%, sin identificar**. Adicionalmente, para el Decreto N° 5T-2024 y el VAD solo se informa saldo no corriente, sin señalar que la porción corriente es cero."));
body.push(propHead("— sustituir la nota (*) por un cuadro que cierre contra el rubro"));
body.push(propP("(*) Detalle de «Deudores varios» por concepto, al 30 de junio de 2026:", { size: 20 }));
body.push(propTail());
body.push(mkTable([4880, 2600, 2600],
  ["Concepto", { t: "Corrientes M$", align: AlignmentType.RIGHT }, { t: "No corrientes M$", align: AlignmentType.RIGHT }],
  [
    ["Mecanismos de estabilización de tarifas — Leyes N° 21.185, N° 21.472 y N° 21.667", NUM("238.169.651"), NUM("135.688.042")],
    ["Reliquidación tarifaria Decreto N° 5T-2024, incluidos intereses del art. 192° LGSE", NUM("—"), NUM("297.020.680")],
    ["Proceso tarifario VAD noviembre 2024 – noviembre 2030", NUM("—"), NUM("173.639.706")],
    ["Otros conceptos, individualmente no significativos", NUM("24.799.523"), NUM("—")],
    [{ t: "Total Deudores varios", size: 18, fill: "F5F7F9", bold: true }, { t: "262.969.174", font: MONO, size: 17, align: AlignmentType.RIGHT, fill: "F5F7F9", bold: true }, { t: "606.348.428", font: MONO, size: 17, align: AlignmentType.RIGHT, fill: "F5F7F9", bold: true }],
  ]));
body.push(spacer(60));
body.push(todo("Abrir con Contabilidad los M$ 24.799.523 corrientes. Si dentro de ese saldo existe un concepto relevante, debe presentarse en línea propia en lugar de agruparse en «Otros». Replicar el cuadro con la columna comparativa al 31-12-2025 (M$ 246.097.079 corrientes y M$ 643.732.662 no corrientes)."));

/* A.3.a-ii */
body.push(H2("A.3.a · ii", "Mismo desglose en cuentas por pagar comerciales y otras cuentas por pagar", "Con reparo", WARN));
body.push(NORMS("Nota 21"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Aplicar el mismo desglose por concepto, corriente y no corriente, respecto de las cuentas por pagar informadas en la nota sobre «Cuentas por Pagar Comerciales y Otras Cuentas por Pagar»."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("La nota (*) de «Proveedores de energía y otros eléctricos» abre los rezagos de pago derivados del mecanismo de estabilización: Ley N° 21.185 por M$ 235.707.561 corriente y M$ 114.876.787 no corriente, y Leyes N° 21.472 y N° 21.667 por M$ 51.584.021 corriente."));
body.push(P("La cobertura resulta insuficiente frente al saldo del rubro. En la porción corriente se explican M$ 287.291.582 de M$ 487.494.713: quedan **M$ 200.203.131 sin desglosar, el 41,1% del saldo**. En la no corriente quedan M$ 3.528.257 sin identificar. Es la brecha más expuesta del paquete, porque la CMF pidió el desglose precisamente sobre esta partida."));
body.push(propHead("— sustituir la nota (*) de la nota 21"));
body.push(propP("(*) Detalle de «Proveedores de energía y otros eléctricos» por concepto, al 30 de junio de 2026:", { size: 20 }));
body.push(propTail());
body.push(mkTable([4880, 2600, 2600],
  ["Concepto", { t: "Corrientes M$", align: AlignmentType.RIGHT }, { t: "No corrientes M$", align: AlignmentType.RIGHT }],
  [
    ["Rezagos de pago por compras de energía — mecanismo de estabilización Ley N° 21.185", NUM("235.707.561"), NUM("114.876.787")],
    ["Rezagos de pago por compras de energía — Leyes N° 21.472 y N° 21.667", NUM("51.584.021"), NUM("—")],
    ["Facturación corriente por compras de energía y potencia y peajes de transmisión", NUM("[completar]"), NUM("[completar]")],
    ["Otros conceptos, individualmente no significativos", NUM("[completar]"), NUM("[completar]")],
    [{ t: "Total Proveedores de energía y otros eléctricos", size: 18, fill: "F5F7F9", bold: true }, { t: "487.494.713", font: MONO, size: 17, align: AlignmentType.RIGHT, fill: "F5F7F9", bold: true }, { t: "118.405.044", font: MONO, size: 17, align: AlignmentType.RIGHT, fill: "F5F7F9", bold: true }],
  ]));
body.push(spacer(60));
body.push(todo("Las dos líneas marcadas deben sumar M$ 200.203.131 corrientes y M$ 3.528.257 no corrientes; solicitar la apertura a Contabilidad. Añadir la columna comparativa al 31-12-2025 (M$ 496.419.628 corrientes y M$ 219.407.434 no corrientes) y evaluar si «Acreedores varios» por M$ 28.139.024 requiere una apertura equivalente, dado que la observación se refiere al rubro completo y no solo a proveedores de energía."));

/* A.3.b-i */
body.push(H2("A.3.b · i", "Datos de entrada, supuestos, métodos y forma de aplicación de la matriz de pérdida esperada", "Cumple", OK));
body.push(NORMS("NIIF 7.35G  ·  Nota 8.1.4"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Revelar los datos de entrada, supuestos y métodos utilizados para determinar la matriz de cálculo de pérdida esperada y la forma en que ésta se aplica —por cliente, por documento u otro concepto—."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("Cubierto con holgura. La nota incorpora el método ECL = PD × LGD × EAD descontado a la tasa de interés efectiva original conforme al párrafo 5.5.17 de NIIF 9, el enfoque simplificado por vida completa, y responde de forma expresa la pregunta de la CMF: «La matriz se aplica por documento, esto es, cada factura se asigna al tramo de antigüedad que le corresponde a la fecha de cierre y se multiplica por la tasa de pérdida esperada del tramo respectivo del cluster al que pertenece el cliente»."));
body.push(P("Los datos de entrada quedan identificados —facturación y recaudación mensual por cluster obtenidas de los sistemas comerciales, incobrabilidad efectivamente materializada, información histórica de efectividad del corte de suministro y variables macroeconómicas de fuentes externas—, así como los supuestos: ratio histórico de pérdida ponderado por facturación, PD estimada sobre una ventana superior a 24 meses y estructurada en trece tramos de antigüedad desde «En plazo» hasta «Más de 1.080 días», y ajuste prospectivo por correlación estadística superior al 50%, con fuentes citadas (IPoM del Banco Central para IPC y PIB, INE para desempleo, Banco Central para IPDEGA) y tres escenarios ponderados 30% / 40% / 30%."));
body.push(LABEL("Sugerencia, no exigida por el oficio"));
body.push(P("No se revela el efecto cuantitativo del ajuste prospectivo ni una sensibilidad de la PD. Es la pregunta natural de seguimiento en el próximo ciclo de revisión; conviene tener el dato preparado aunque no se incorpore ahora."));
body.push(spacer(160));

/* A.3.b-ii */
body.push(H2("A.3.b · ii", "Agrupación de los deudores comerciales para la medición colectiva", "Con reparo", WARN));
body.push(NORMS("NIIF 7.35F(c)  ·  Nota 8.1.4"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Indicar la manera en que se agruparon los deudores comerciales para efectos de la medición de las pérdidas crediticias esperadas sobre una base colectiva."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("La nota define siete clusters con su criterio de asignación: Municipal-Fiscal, Residenciales, Convenio Especial, PYME, Comercial-Industrial, Mercado Eléctrico y Otros Negocios, y aclara que cada uno cuenta con un modelo ECL independiente, con curvas de default, curvas de recupero y supuestos propios. La exigencia queda cubierta."));
body.push(LABEL("Reparo"));
body.push(P("Los nombres no se mantienen a lo largo de la nota. Al describir el ajuste prospectivo aparecen «Cluster PRC/Vulnerables» y «Cluster Empresa/Industria», que no figuran en la lista de siete definida más arriba, mientras que «Convenio Especial» y «Comercial-Industrial» no reaparecen. Un lector no puede mapear cada cluster con su variable macroeconómica de referencia."));
body.push(propHead("— homologar la nomenclatura en el bloque de ajuste prospectivo"));
body.push(propBullet("Clusters Residenciales, Municipal-Fiscal y Otros Negocios: el ajuste prospectivo se calibra en función del IPC proyectado, variable que exhibe la mayor correlación con la pérdida histórica de estos segmentos (entre 55% y 71%)."));
body.push(propBullet("Cluster Convenio Especial: la variable de referencia es la tasa de desempleo nacional, con una correlación del 86% respecto de la pérdida histórica, lo que refleja la mayor sensibilidad de este segmento al deterioro del mercado laboral."));
body.push(propBullet("Cluster Comercial-Industrial: el ajuste se calibra en función del IPDEGA, con una correlación del 74%, capturando la exposición de estos clientes a variaciones en los costos del sector energético."));
body.push(propBullet("Clusters PYME y Mercado Eléctrico: dado que ninguna variable macroeconómica supera el umbral de correlación estadística del 50%, no se aplica ajuste cuantitativo prospectivo, quedando éste sujeto a la evaluación cualitativa de la Administración."));
body.push(propTail());
body.push(todo("Validar con el equipo de riesgo de crédito que «PRC/Vulnerables» corresponde efectivamente a «Convenio Especial» y «Empresa/Industria» a «Comercial-Industrial». Si se trata de agrupaciones distintas, deben incorporarse a la lista de clusters en lugar de renombrarse."));

/* A.3.b-iii */
body.push(H2("A.3.b · iii", "Tratamiento de los clientes repactados y política para dejar esa clasificación", "No cumple", GAP));
body.push(NORMS("NIIF 7  ·  Nota 8.1.4"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Explicar el tratamiento de los clientes repactados para efectos de la estimación de deterioro, **incluyendo las políticas para que un cliente deje dicha clasificación**."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("La primera mitad está resuelta: se explica que los clientes que suscriben convenios de pago o repactaciones no reciben tratamiento diferenciado en la determinación de las pérdidas crediticias esperadas, salvo aquellos expresamente incluidos en el cluster «Convenio Especial», y se entrega la lógica contable —la repactación no extingue ni transforma sustancialmente el activo financiero original, sino que reprograma sus flujos de cobro, de modo que la cuenta permanece en el mismo cluster con igual PD y LGD—."));
body.push(P("**La segunda mitad no está.** No existe ninguna política de salida. Lo más cercano es la definición del cluster «Convenio Especial», que describe lo contrario: «Al finalizar el convenio se volverá a entregar otro convenio tantas veces como sea necesario hasta extinguir la deuda». Eso es permanencia, no salida. La omisión es visible porque la clasificación sí opera en los estados financieros: las notas 8.2, 8.3 y 8.5 estratifican y provisionan por separado la cartera repactada y la no repactada, sin definir en ningún punto cuándo una cuenta entra y cuándo sale de esa condición."));
body.push(propHead("— agregar tras el párrafo «La lógica de esta decisión…» de la nota 8.1.4"));
body.push(propP("**Ingreso y salida de la condición de cartera repactada.**"));
body.push(propP("Una cuenta por cobrar se clasifica como cartera repactada desde el momento en que el cliente suscribe un convenio de pago sobre deuda vencida y mientras dicho convenio se mantenga vigente. La suscripción del convenio no modifica el cluster de riesgo al que pertenece el cliente ni los parámetros de probabilidad de incumplimiento y pérdida dado el incumplimiento aplicables a su segmento."));
body.push(propP("Un cliente deja la condición de cartera repactada cuando se verifica alguna de las siguientes situaciones:"));
body.push(propBullet("El pago íntegro de las cuotas comprometidas, con lo cual el convenio se extingue y el saldo remanente del cliente, de existir, retorna a la cartera no repactada en el tramo de antigüedad que corresponda a su facturación vigente."));
body.push(propBullet("El incumplimiento del convenio conforme a las condiciones pactadas, caso en el cual el convenio caduca, la deuda se reincorpora a la cartera no repactada conservando la antigüedad original de los documentos que le dieron origen, y queda sujeta a las acciones de cobranza y, en su caso, de suspensión de suministro previstas en la normativa eléctrica."));
body.push(propBullet("El castigo contable del saldo, conforme a la política de castigos descrita más adelante en esta nota."));
body.push(propP("La salida de la condición de repactado no origina por sí sola una reversión de la provisión por deterioro: la cuenta continúa medida bajo el modelo de pérdidas crediticias esperadas del cluster al que pertenece el cliente, según el tramo de antigüedad que le corresponda a la fecha de cierre."));
body.push(propTail());
body.push(todo("Confirmar con Cobranzas el tratamiento efectivo de la antigüedad al caducar un convenio —si la deuda vuelve con la antigüedad original o se reinicia el conteo—, porque de ello depende la PD aplicada y la redacción debe reflejar el comportamiento real del sistema."));

/* A.3.c */
body.push(H2("A.3.c", "Partidas que componen el «(Aumento) disminución del período o ejercicio»", "Con reparo", WARN));
body.push(NORMS("NIIF 7.35H  ·  NIIF 7.35I  ·  NIIF 7 B8D  ·  Nota 8.1.4"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Explicar las partidas que componen dicho concepto, indicando las causas o factores que influyeron en ellas —por ejemplo, cambios en la composición de la cartera, cambios en la morosidad y cambios en las repactaciones—."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("Se agregó un párrafo con cuatro factores: cambios en la composición de la cartera vía facturación por cluster, que altera la base sobre la que se aplica la PD; variaciones de morosidad por traslado de saldos entre tramos; efecto de las repactaciones del período; y los castigos del período. La parte relativa a «causas o factores» queda razonablemente respondida."));
body.push(P("Quedan dos flancos abiertos. Primero, la CMF pidió antes que nada **explicar las partidas que componen dicho concepto**, y el monto de M$ (10.717.277) sigue presentándose como una sola cifra sin apertura. Segundo, el párrafo enumera los castigos como componente del «(Aumento) disminución», pero el mismo cuadro contiene una línea separada, «Baja (reversiones) de deudores comerciales y otras cuentas por cobrar deterioradas del período o ejercicio», por M$ (1.160.102). Si los castigos se imputan en esa línea, el texto contradice el cuadro."));
body.push(propHead("— cuadro de apertura a continuación del movimiento de la provisión"));
body.push(propP("El detalle de las partidas que componen el «(Aumento) disminución del período o ejercicio» es el siguiente:"));
body.push(propTail());
body.push(mkTable([4880, 2600, 2600],
  ["Partida", { t: "30-06-2026 M$", align: AlignmentType.RIGHT }, { t: "31-12-2025 M$", align: AlignmentType.RIGHT }],
  [
    ["Efecto de la variación en el volumen de cartera bruta por cluster", NUM("[completar]"), NUM("[completar]")],
    ["Efecto del cambio en la distribución de la cartera entre tramos de morosidad", NUM("[completar]"), NUM("[completar]")],
    ["Efecto de las repactaciones y convenios del período", NUM("[completar]"), NUM("[completar]")],
    ["Efecto de la actualización de parámetros del modelo (PD, LGD y ajuste prospectivo)", NUM("[completar]"), NUM("[completar]")],
    [{ t: "(Aumento) disminución del período o ejercicio", size: 18, fill: "F5F7F9", bold: true }, { t: "(10.717.277)", font: MONO, size: 17, align: AlignmentType.RIGHT, fill: "F5F7F9", bold: true }, { t: "(52.439.755)", font: MONO, size: 17, align: AlignmentType.RIGHT, fill: "F5F7F9", bold: true }],
  ]));
body.push(spacer(60));
body.push(todo("Corregir además la redacción: eliminar el punto iv) referido a los castigos del párrafo explicativo del «(Aumento) disminución» y trasladarlo a la explicación de la línea «Baja (reversiones)», o bien confirmar en qué línea se imputan efectivamente los castigos y alinear ambos textos. Hoy el cuadro y el párrafo dicen cosas distintas."));

/* A.3.d */
body.push(H2("A.3.d", "Política de castigos para efectos financieros", "Cumple", OK));
body.push(NORMS("NIIF 7.35F(e)  ·  Nota 8.1.4"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Describir la política de castigos para efectos financieros, incluyendo los indicadores de que no hay expectativas razonables de recuperación. La nota anterior solo hacía referencia a los castigos tributarios."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("Se incorporó el apartado «Castigos de deudores incobrables», que resuelve la observación: define el hecho gatillante —agotadas las instancias de cobranza y sin expectativas razonables de recuperación total o parcial—, entrega el indicador para la cartera masiva —antigüedad superior a 36 meses, junto al resultado de las gestiones de cobranza y los antecedentes de recuperabilidad—, aclara que el castigo se imputa contra la provisión previamente constituida, y distingue el caso de cobranza judicial, donde la antigüedad no basta por sí sola y la baja se produce al cerrarse el juicio con el certificado de castigo. El párrafo de castigos tributarios se mantiene, ahora claramente diferenciado del castigo financiero."));
body.push(LABEL("Sugerencia menor"));
body.push(P("Conviene cerrar el punto con el tratamiento de las recuperaciones posteriores al castigo."));
body.push(propHead("— agregar al final del apartado de castigos"));
body.push(propP("Los activos financieros castigados continúan sujetos a gestiones de cobranza cuando existen antecedentes que lo justifican. Las recuperaciones obtenidas con posterioridad al castigo se reconocen en resultados del período en que se perciben, como una disminución del gasto por deterioro."));
body.push(propTail());
body.push(spacer(160));

/* A.4 */
body.push(H2("A.4", "Desglose de los conceptos que componen «Otras reservas»", "Con reparo", WARN));
body.push(NORMS("NIC 1.79(b)  ·  Nota 26.6.3"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Desglosar los conceptos que componen las otras reservas y su respectivo monto, según su naturaleza. La nota anterior solo señalaba que se incluían otras reservas reconocidas de inversiones en subsidiarias, asociadas y negocios de control conjunto."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("El desglose se incorporó y es completo: nueve conceptos identificados con su monto y su fecha —reservas de la ex matriz GNF Chile SpA. hasta su fusión en agosto de 2016, asignación por la división con CGE Gas Natural S.A., canjes de acciones a participaciones no controladoras por las fusiones de 2016, 2017 y 2018, compra de minoritarios de Sociedad de Computación Binaria S.A., reclasificación de reservas históricas de conversión, asignación por la división con CGE Transmisión S.A. y el ajuste por política de revaluación de filiales 2009-2014—. La exigencia de fondo está cubierta."));
body.push(LABEL("Dos errores que corregir"));
body.push(bullet("**Signo invertido.** El cuadro de la nota suma +103.785.672, pero el Estado Consolidado Intermedio de Cambios en el Patrimonio Neto presenta «Otras reservas varias» en (103.785.672), negativo, tanto al 01-01-2025 como al 01-01-2026 y al 30-06-2026. La nota no reconcilia con el estado primario. Publicar un desglose cuyo total tiene signo contrario al del estado financiero es una observación segura."));
body.push(bullet("**Encabezado de columna errado.** La tabla titula las columnas de saldo como «Corrientes», concepto inaplicable a una partida patrimonial. Se trata de un arrastre de otra plantilla."));
body.push(propHead("— corrección de la tabla 26.6.3 y frase de cierre"));
body.push(propBullet("Reemplazar el encabezado «Corrientes» por «30-06-2026 M$ / 31-12-2025 M$», sin clasificación corriente."));
body.push(propBullet("Invertir el signo de los nueve conceptos de modo que el total sea (103.785.672), coincidente con la columna «Otras reservas varias» del Estado de Cambios en el Patrimonio."));
body.push(propBullet("Agregar como cierre del cuadro el párrafo siguiente:"));
body.push(propP("El saldo total de este cuadro corresponde a la columna «Otras reservas varias» presentada en el Estado Consolidado Intermedio de Cambios en el Patrimonio Neto. Estas reservas no han presentado movimientos durante los períodos terminados al 30 de junio de 2026 y al 31 de diciembre de 2025."));
body.push(propTail());
body.push(todo("Confirmar con Consolidación cuál de las dos presentaciones tiene el signo correcto. Si el error está en el estado primario, la corrección va allí y no en la nota; pero ambas presentaciones no pueden convivir."));

/* A.5 */
body.push(H2("A.5", "Diferenciación entre casos provisionados y pasivos contingentes", "Con reparo", WARN));
body.push(NORMS("NIC 37  ·  NIC 37.86  ·  Nota 34"));
body.push(LABEL("Qué exige la CMF"));
body.push(P("Diferenciar aquellos casos que se encuentran provisionados de aquellos que corresponden a pasivos contingentes no contabilizados, conforme a la NIC 37, y revelar para estos últimos la información requerida en el párrafo 86."));
body.push(LABEL("Situación en el EE.FF. 06-2026"));
body.push(P("La separación estructural está hecha. La nota 34.1 agrupa los juicios con provisión constituida —M$ 5.418.841 al 30 de junio de 2026, más M$ 10.407.572 por juicios de carácter laboral—; la nota 34.2 agrupa los pasivos contingentes con la declaración de que «el Grupo no ha constituido provisiones, el estado del proceso no permite estimar como probable que el Grupo resulte obligado en los términos demandados»; y la nota 34.3 las sanciones administrativas con provisión de M$ 23.367.034."));
body.push(P("Falta la segunda parte de la observación. Del párrafo 86 solo se cumple con holgura el literal (a), descripción de la naturaleza. Sobre el literal (b), varias causas registran «Cuantía: Indeterminada» sin acogerse expresamente a la excepción del párrafo 91 ni indicar por qué el efecto financiero no puede estimarse. Del literal (c) solo se cubre la incertidumbre de calendario —«no es posible determinar un calendario razonable de fechas de pago»—, no la relativa al importe. El literal (d), posibilidad de reembolsos, no se menciona en parte alguna, pese a que una compañía de distribución eléctrica con demandas de responsabilidad civil extracontractual razonablemente cuenta con pólizas de seguro."));
body.push(P("Adicionalmente, el título «34.1.- Juicios y otras acciones legales» no señala que corresponda al bloque de los casos provisionados. Si la CMF pidió diferenciar, la diferenciación conviene que se lea desde el índice."));
body.push(propHead("— encabezados y párrafo de cierre de la nota 34.2"));
body.push(propP("**1. Renombrar los apartados:**"));
body.push(propBullet("34.1.- Juicios y otras acciones legales con provisión constituida."));
body.push(propBullet("34.2.- Pasivos contingentes no provisionados."));
body.push(propP("**2. Reemplazar el cierre de la nota 34.2 por:**"));
body.push(propP("En relación con los litigios descritos en este apartado, el Grupo no ha constituido provisiones por cuanto el estado de tramitación de cada proceso no permite calificar como probable que resulte obligado en los términos demandados. En consecuencia, corresponden a pasivos contingentes que no han sido reconocidos en el estado de situación financiera, conforme a lo establecido en la NIC 37."));
body.push(propP("La estimación del efecto financiero de estos pasivos contingentes corresponde, cuando se informa, a la cuantía demandada, la que no representa necesariamente el desembolso que eventualmente deba efectuarse. Respecto de aquellas causas cuya cuantía se indica como indeterminada, el demandante no ha cuantificado su pretensión o ésta queda entregada a la determinación del tribunal, por lo que no resulta practicable efectuar una estimación fiable de su efecto financiero."));
body.push(propP("El importe y la oportunidad de una eventual salida de recursos dependen del resultado de los procesos judiciales en curso, del ejercicio de los recursos procesales disponibles y de los plazos de tramitación de los tribunales, circunstancias que se encuentran fuera del control del Grupo. Por esta razón, no es posible determinar un calendario razonable de fechas de pago ni un rango fiable de importes, si en su caso los hubiere."));
body.push(propP("El Grupo mantiene pólizas de seguro de responsabilidad civil que podrían cubrir parcialmente los desembolsos derivados de determinadas causas de responsabilidad civil extracontractual. Al 30 de junio de 2026 no se han reconocido activos por reembolso, por cuanto su recepción no se considera prácticamente cierta en los términos de la NIC 37."));
body.push(propTail());
body.push(todo("Validar con Legal y con el corredor de seguros el alcance real de la cobertura antes de incorporar el último párrafo. Si no existen pólizas aplicables, debe señalarse expresamente en lugar de omitir el literal (d)."));

/* ======================= B ======================= */
body.push(H1("B. Análisis razonado"));
body.push(NORMS("Norma de Carácter General N° 30, Sección II, N° 2.1, punto A.4, letra e)"));
body.push(H2("B.1.a — B.1.c", "Las tres observaciones de análisis razonado no se resuelven en este archivo", "Fuera de alcance", NAVY));
body.push(LABEL("Verificación efectuada"));
body.push(P("El archivo E200 revisado contiene únicamente los estados financieros consolidados intermedios y sus notas. Se buscaron expresamente y no existen: la sección de indicadores financieros con «Liquidez Corriente», «Razón Ácida» y «Cobertura de Gastos Financieros Netos»; el «Análisis del Estado Consolidado de Flujo de Efectivo Directo»; ni la sección «Áreas de Negocios de CGE». Las tres observaciones deben resolverse en el Análisis Razonado, que se presenta como documento separado y debe revisarse aparte antes del envío."));
body.push(LABEL("Qué debe contener cada una"));
body.push(bullet("**B.1.a — Indicadores financieros.** Incorporar bajo cada indicador la fórmula empleada: Liquidez Corriente como activos corrientes totales sobre pasivos corrientes totales; Razón Ácida como activos corrientes totales menos inventarios y menos activos por impuestos corrientes, sobre pasivos corrientes totales; y Cobertura de Gastos Financieros Netos como resultado antes de impuestos más gastos financieros, sobre gastos financieros netos de ingresos financieros. Para «Deuda Financiera Neta» debe enumerarse los conceptos que la conforman."));
body.push(bullet("**B.1.b — Flujo de efectivo.** Reescribir el análisis de las actividades de la operación explicando por qué variaron los flujos —comportamiento de la recaudación, efecto de los rezagos de pago por los mecanismos de estabilización, calendario de pagos a generadores y efecto de las reliquidaciones tarifarias— en lugar de describir la composición de la variación."));
body.push(bullet("**B.1.c — Áreas de negocios.** Acompañar cada cifra de ventas físicas reguladas y operadas, número de clientes y pérdidas de electricidad con la explicación de las causas o factores principales que incidieron en su evolución: crecimiento vegetativo, comportamiento de la demanda por segmento, incorporación de clientes y planes de reducción de pérdidas."));
body.push(propHead("— definición de «Deuda Financiera Neta» para B.1.a"));
body.push(propP("«Deuda Financiera Neta» se determina como la suma de «Otros pasivos financieros corrientes» y «Otros pasivos financieros no corrientes», menos «Efectivo y equivalentes al efectivo»."));
body.push(propTail());
body.push(todo("Ésta es exactamente la definición que el propio EE.FF. utiliza en la nota 20 para el cálculo de la Razón de Endeudamiento Financiero de las series de bonos BCGEI-I, BCGEI-J y BCGEI-K. Usar la misma en el Análisis Razonado evita que la CMF observe dos definiciones distintas del mismo concepto en documentos del mismo cierre. Si el Análisis Razonado incorpora además las cuentas por pagar a entidades relacionadas, debe señalarse y explicarse la diferencia con la definición de covenants."));

/* ======================= orden de trabajo ======================= */
body.push(H1("Orden de trabajo sugerido"));
body.push(NORMS("De mayor a menor exposición."));
body.push(mkTable([600, 5680, 1200, 2600],
  [{ t: "#", align: AlignmentType.RIGHT }, "Acción", "Ref.", "Depende de"],
  [
    [NUM("1"), "Resolver la contradicción sobre derivados de tasa de interés entre las notas 5.1.2 y 7.1", REF("A.2.a"), "Tesorería"],
    [NUM("2"), "Corregir el signo del cuadro de otras reservas y su encabezado de columna", REF("A.4"), "Consolidación"],
    [NUM("3"), "Redactar la política de entrada y salida de cartera repactada", REF("A.3.b-iii"), "Cobranzas"],
    [NUM("4"), "Cerrar el desglose de proveedores de energía (M$ 200.203.131 corrientes)", REF("A.3.a-ii"), "Contabilidad"],
    [NUM("5"), "Cerrar el desglose de deudores varios (M$ 24.799.523 corrientes)", REF("A.3.a-i"), "Contabilidad"],
    [NUM("6"), "Abrir por partidas el «(Aumento) disminución» y alinear el tratamiento de los castigos", REF("A.3.c"), "Riesgo de crédito"],
    [NUM("7"), "Completar NIC 37.86 (b), (c) y (d) y renombrar los apartados de la nota 34", REF("A.5"), "Legal / Seguros"],
    [NUM("8"), "Homologar los nombres de clusters dentro de la nota 8.1.4", REF("A.3.b-ii"), "Riesgo de crédito"],
    [NUM("9"), "Separar los párrafos concatenados de la nota 5.1.2 en Workiva", REF("A.2.a"), "—"],
    [NUM("10"), "Agregar la frase de «sin cambios en técnicas de valoración» y la nota de reclasificación del comparativo", REF("A.1 · A.2.b"), "—"],
    [NUM("11"), "Revisar el Análisis Razonado contra las tres observaciones de la sección B", REF("B.1"), "Estudios / Regulación"],
  ]));
body.push(spacer(240));

body.push(new Paragraph({
  children: [new TextRun({ text: "Fuentes y alcance", font: SANS, size: 17, bold: true, color: NAVY, characterSpacing: 20 })],
  spacing: { before: 200, after: 60 },
  border: { top: { style: BorderStyle.SINGLE, size: 8, color: "C8D0DA", space: 8 } },
}));
body.push(P("OF. ORD. CMF N° 95881 de 05 de junio de 2026, folio 2026958813453348. E200 (ESP) — EE.FF. 06-2026 — Compañía General de Electricidad S.A. y subsidiarias.", { size: 18, color: MUTED }));
body.push(P("Las cifras citadas se tomaron directamente de las notas del estado financiero revisado. Los textos propuestos son borradores para revisión de la Administración y de los auditores externos; los marcados «[completar]» requieren el dato de origen antes de su incorporación.", { size: 18, color: MUTED }));

/* =========================================================
   DOCUMENT
   ========================================================= */
const doc = new Document({
  creator: "Auditoría CGE",
  title: "Oficio CMF 95881 vs. EE.FF. CGE 06-2026",
  description: "Comparativa de cumplimiento normativo",
  styles: { default: { document: { run: { font: SANS, size: 20, color: INK } } } },
  numbering: { config: [] },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1080, right: 1080, bottom: 1080, left: 1080, header: 620, footer: 620 },
      },
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "Oficio CMF N° 95881  ·  EE.FF. CGE 30-06-2026", font: SANS, size: 16, color: MUTED }),
            new TextRun({ text: "\tRevisión de cumplimiento", font: SANS, size: 16, color: MUTED }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: W }],
          spacing: { after: 60 },
          border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "C8D0DA", space: 4 } },
        })],
      }),
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          children: [
            new TextRun({ text: "Documento de trabajo — uso interno", font: SANS, size: 15, color: MUTED }),
            new TextRun({ text: "\t", font: SANS, size: 15 }),
            new TextRun({ children: ["Página ", PageNumber.CURRENT, " de ", PageNumber.TOTAL_PAGES], font: SANS, size: 15, color: MUTED }),
          ],
          tabStops: [{ type: TabStopType.RIGHT, position: W }],
        })],
      }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync("Comparativa_Oficio_CMF_95881_vs_EEFF_CGE_06-2026.docx", buf);
  console.log("written", buf.length, "bytes");
});
