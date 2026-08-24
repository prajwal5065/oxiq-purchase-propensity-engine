// Builds the .docx purely from `docx` library objects (Paragraph, TextRun,
// Table, HeadingLevel...) - never from the rendered page's HTML/DOM. That's
// what structurally guarantees the site's dark theme can never end up in
// the exported Word file: there is no HTML or CSS anywhere in this path
// for a background color to live in. Colors/fonts below are chosen fresh
// for a clean, light, professional document, independent of the app's UI.
import {
  AlignmentType,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  WidthType,
} from "docx";
import type { ReportData } from "./reportData";

const HEADING_COLOR = "1A1A2E";
const MUTED_COLOR = "555555";
const RULE_COLOR = "CCCCCC";

function heading(text: string, level: (typeof HeadingLevel)[keyof typeof HeadingLevel]) {
  return new Paragraph({ text, heading: level, spacing: { before: 320, after: 160 } });
}

function body(text: string, opts: { italic?: boolean; muted?: boolean } = {}) {
  return new Paragraph({
    spacing: { after: 120 },
    children: [
      new TextRun({ text, italics: opts.italic, color: opts.muted ? MUTED_COLOR : undefined }),
    ],
  });
}

function bullet(text: string) {
  return new Paragraph({ text, bullet: { level: 0 }, spacing: { after: 80 } });
}

function simpleTable(headerRow: string[], rows: string[][]): Table {
  const makeRow = (cells: string[], isHeader: boolean) =>
    new TableRow({
      children: cells.map(
        (text) =>
          new TableCell({
            width: { size: 100 / cells.length, type: WidthType.PERCENTAGE },
            children: [
              new Paragraph({
                children: [new TextRun({ text, bold: isHeader })],
              }),
            ],
          }),
      ),
    });

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    rows: [makeRow(headerRow, true), ...rows.map((r) => makeRow(r, false))],
  });
}

export async function buildDocxBlob(data: ReportData): Promise<Blob> {
  const children: (Paragraph | Table)[] = [];

  children.push(
    new Paragraph({
      alignment: AlignmentType.LEFT,
      children: [new TextRun({ text: data.company.name, bold: true, size: 44, color: HEADING_COLOR })],
      spacing: { after: 40 },
    }),
    new Paragraph({
      children: [
        new TextRun({
          text: `OxiQ Purchase Propensity Report — generated ${new Date(data.generatedAt).toLocaleString()}`,
          size: 20,
          color: MUTED_COLOR,
        }),
      ],
      spacing: { after: 60 },
      border: { bottom: { color: RULE_COLOR, space: 8, style: "single", size: 6 } },
    }),
  );

  // Company
  children.push(heading("Company", HeadingLevel.HEADING_2));
  children.push(
    simpleTable(
      ["Field", "Value"],
      [
        ["Domain", data.company.domain],
        ["Industry", data.company.industry ?? "Not specified"],
        ["Last processed", data.company.lastProcessed],
      ],
    ),
  );

  // Final decision
  children.push(heading("Final Decision", HeadingLevel.HEADING_2));
  if (data.decision.headline) children.push(body(data.decision.headline, { italic: true }));
  children.push(
    simpleTable(
      ["Metric", "Value"],
      [
        ["Priority", data.decision.priorityLabel],
        ["Decision", data.decision.finalDecision],
        ["Purchase score", `${data.decision.purchaseScore} / 100`],
        ["Confidence", data.decision.purchaseConfidence],
      ],
    ),
  );
  if (data.decision.primaryReason) {
    children.push(body(""), body(`Primary reason: ${data.decision.primaryReason}`));
    for (const r of data.decision.secondaryReasons) children.push(bullet(r));
  }

  // Confidence
  if (data.confidence) {
    children.push(heading("Confidence", HeadingLevel.HEADING_2));
    children.push(body(`${data.confidence.summary} (${data.confidence.overall}, ${data.confidence.level})`));
    if (data.confidence.factors.length) {
      children.push(
        simpleTable(
          ["Factor", "Value", "Weight", "Description"],
          data.confidence.factors.map((f) => [f.name, f.value, f.weight, f.description]),
        ),
      );
    }
  }

  // Pillars
  children.push(heading("Pillar Scores", HeadingLevel.HEADING_2));
  for (const p of data.pillars) {
    children.push(heading(`${p.name} — ${p.score}/100 (${p.confidence} confidence)`, HeadingLevel.HEADING_3));
    for (const reason of p.reasons) children.push(bullet(reason));
  }

  // Decision Intelligence
  if (data.decisionIntelligence) {
    const di = data.decisionIntelligence;
    children.push(heading("Decision Intelligence", HeadingLevel.HEADING_2));

    children.push(heading(`Buying Intent — ${di.buyingIntentLevel}`, HeadingLevel.HEADING_3));
    children.push(body(di.buyingIntentRationale));
    for (const s of di.buyingIntentSignals) {
      children.push(bullet(`[${s.strength}] "${s.excerpt}" — ${s.source}`));
    }

    children.push(heading("Why Now", HeadingLevel.HEADING_3));
    children.push(body(di.whyNowNarrative));
    for (const t of di.whyNowTriggers) {
      children.push(bullet(`[${t.triggerType}, ${t.freshness}] "${t.excerpt}" — ${t.source}`));
    }

    children.push(heading("Contradictions", HeadingLevel.HEADING_3));
    children.push(body(di.contradictionsSummary));
    for (const c of di.contradictions) {
      children.push(bullet(`${c.theme} (${c.severity} severity): ${c.description}`));
    }

    children.push(heading("What Would Change This Decision", HeadingLevel.HEADING_3));
    children.push(body(di.changeSummary));
    for (const f of di.changeFactors) children.push(bullet(f.description));
  }

  // Sales Intelligence
  if (data.salesIntelligence) {
    const si = data.salesIntelligence;
    children.push(heading("Sales Intelligence", HeadingLevel.HEADING_2));
    if (!si.dataSufficient) {
      children.push(body("Insufficient data for a reliable sales assertion.", { italic: true, muted: true }));
    } else {
      if (si.opportunity) children.push(body(`Opportunity: ${si.opportunity}`));
      if (si.solutionFitUseCase) {
        children.push(body(`Solution fit: ${si.solutionFitUseCase} — ${si.solutionFitReasoning}`));
      }
      for (const r of si.buyerRoles) children.push(bullet(`${r.title}: ${r.rationale}`));
      if (si.salesTriggerNarrative) children.push(body(`Sales trigger: ${si.salesTriggerNarrative}`));
      for (const r of si.risks) children.push(bullet(`[${r.type}] ${r.description}`));
      if (si.nextAction) children.push(body(`Recommended next action: ${si.nextAction}`));
      if (si.nextActionRationale) children.push(body(si.nextActionRationale, { muted: true }));
    }
  }

  // Evidence
  children.push(heading(`Evidence (${data.evidence.length})`, HeadingLevel.HEADING_2));
  if (data.evidence.length) {
    children.push(
      simpleTable(
        ["Label", "Excerpt", "Source", "Confidence", "Date"],
        data.evidence.map((e) => [e.label, e.excerpt, e.source, e.confidence, e.date]),
      ),
    );
  } else {
    children.push(body("No evidence on file.", { muted: true }));
  }

  // Sources
  if (data.sources.length) {
    children.push(heading("Sources / Collector Status", HeadingLevel.HEADING_2));
    children.push(
      simpleTable(
        ["Source", "Status", "Signals"],
        data.sources.map((s) => [s.source, s.status, String(s.signalCount)]),
      ),
    );
  }

  const doc = new Document({
    styles: {
      default: {
        document: { run: { font: "Calibri", size: 22, color: "222222" } },
      },
    },
    sections: [{ children }],
  });

  return Packer.toBlob(doc);
}
