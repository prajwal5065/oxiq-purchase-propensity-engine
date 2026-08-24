// Draws the PDF directly via jsPDF's vector text/line API (plus
// jspdf-autotable for tables) - there is no HTML rendering step at all in
// this path, so there is nothing for the site's dark CSS/background to
// attach to. Colors below are chosen fresh for a clean, light, printable
// document.
import { jsPDF } from "jspdf";
import autoTable from "jspdf-autotable";
import type { ReportData } from "./reportData";

const PAGE_WIDTH = 210; // A4 mm
const MARGIN = 18;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;
const HEADING_COLOR: [number, number, number] = [26, 26, 46];
const MUTED_COLOR: [number, number, number] = [90, 90, 90];
const BODY_COLOR: [number, number, number] = [34, 34, 34];
const PAGE_HEIGHT = 297;

export function buildPdfBlob(data: ReportData): Blob {
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  let y = MARGIN;

  const ensureSpace = (needed: number) => {
    if (y + needed > PAGE_HEIGHT - MARGIN) {
      doc.addPage();
      y = MARGIN;
    }
  };

  const h1 = (text: string) => {
    ensureSpace(14);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(13);
    doc.setTextColor(...HEADING_COLOR);
    doc.text(text, MARGIN, y);
    y += 8;
    doc.setDrawColor(200, 200, 200);
    doc.line(MARGIN, y - 3, PAGE_WIDTH - MARGIN, y - 3);
  };

  const h2 = (text: string) => {
    ensureSpace(9);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    doc.setTextColor(...HEADING_COLOR);
    doc.text(text, MARGIN, y);
    y += 6;
  };

  const para = (text: string, opts: { italic?: boolean; muted?: boolean } = {}) => {
    doc.setFont("helvetica", opts.italic ? "italic" : "normal");
    doc.setFontSize(9.5);
    doc.setTextColor(...(opts.muted ? MUTED_COLOR : BODY_COLOR));
    const lines = doc.splitTextToSize(text, CONTENT_WIDTH);
    for (const line of lines) {
      ensureSpace(5);
      doc.text(line, MARGIN, y);
      y += 4.6;
    }
    y += 1.5;
  };

  const bullet = (text: string) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(9.5);
    doc.setTextColor(...BODY_COLOR);
    const lines = doc.splitTextToSize(text, CONTENT_WIDTH - 5);
    lines.forEach((line: string, i: number) => {
      ensureSpace(5);
      doc.text(i === 0 ? `\u2022 ${line}` : `  ${line}`, MARGIN, y);
      y += 4.6;
    });
  };

  const table = (head: string[], rows: string[][]) => {
    autoTable(doc, {
      startY: y,
      head: [head],
      body: rows,
      margin: { left: MARGIN, right: MARGIN },
      styles: { fontSize: 8.5, textColor: BODY_COLOR, cellPadding: 2 },
      headStyles: { fillColor: [240, 240, 245], textColor: HEADING_COLOR, fontStyle: "bold" },
      alternateRowStyles: { fillColor: [250, 250, 252] },
    });
    // @ts-expect-error - autoTable attaches this at runtime
    y = doc.lastAutoTable.finalY + 6;
  };

  // Title
  doc.setFont("helvetica", "bold");
  doc.setFontSize(20);
  doc.setTextColor(...HEADING_COLOR);
  doc.text(data.company.name, MARGIN, y);
  y += 8;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9.5);
  doc.setTextColor(...MUTED_COLOR);
  doc.text(
    `OxiQ Purchase Propensity Report - generated ${new Date(data.generatedAt).toLocaleString()}`,
    MARGIN,
    y,
  );
  y += 8;

  h1("Company");
  table(
    ["Field", "Value"],
    [
      ["Domain", data.company.domain],
      ["Industry", data.company.industry ?? "Not specified"],
      ["Last processed", data.company.lastProcessed],
    ],
  );

  h1("Final Decision");
  if (data.decision.headline) para(data.decision.headline, { italic: true });
  table(
    ["Metric", "Value"],
    [
      ["Priority", data.decision.priorityLabel],
      ["Decision", data.decision.finalDecision],
      ["Purchase score", `${data.decision.purchaseScore} / 100`],
      ["Confidence", data.decision.purchaseConfidence],
    ],
  );
  if (data.decision.primaryReason) {
    para(`Primary reason: ${data.decision.primaryReason}`);
    for (const r of data.decision.secondaryReasons) bullet(r);
  }

  if (data.confidence) {
    h1("Confidence");
    para(`${data.confidence.summary} (${data.confidence.overall}, ${data.confidence.level})`);
    if (data.confidence.factors.length) {
      table(
        ["Factor", "Value", "Weight", "Description"],
        data.confidence.factors.map((f) => [f.name, f.value, f.weight, f.description]),
      );
    }
  }

  h1("Pillar Scores");
  for (const p of data.pillars) {
    h2(`${p.name} - ${p.score}/100 (${p.confidence} confidence)`);
    for (const reason of p.reasons) bullet(reason);
    y += 2;
  }

  if (data.decisionIntelligence) {
    const di = data.decisionIntelligence;
    h1("Decision Intelligence");

    h2(`Buying Intent - ${di.buyingIntentLevel}`);
    para(di.buyingIntentRationale);
    for (const s of di.buyingIntentSignals) bullet(`[${s.strength}] "${s.excerpt}" - ${s.source}`);

    h2("Why Now");
    para(di.whyNowNarrative);
    for (const t of di.whyNowTriggers) {
      bullet(`[${t.triggerType}, ${t.freshness}] "${t.excerpt}" - ${t.source}`);
    }

    h2("Contradictions");
    para(di.contradictionsSummary);
    for (const c of di.contradictions) bullet(`${c.theme} (${c.severity} severity): ${c.description}`);

    h2("What Would Change This Decision");
    para(di.changeSummary);
    for (const f of di.changeFactors) bullet(f.description);
  }

  if (data.salesIntelligence) {
    const si = data.salesIntelligence;
    h1("Sales Intelligence");
    if (!si.dataSufficient) {
      para("Insufficient data for a reliable sales assertion.", { italic: true, muted: true });
    } else {
      if (si.opportunity) para(`Opportunity: ${si.opportunity}`);
      if (si.solutionFitUseCase) para(`Solution fit: ${si.solutionFitUseCase} - ${si.solutionFitReasoning}`);
      for (const r of si.buyerRoles) bullet(`${r.title}: ${r.rationale}`);
      if (si.salesTriggerNarrative) para(`Sales trigger: ${si.salesTriggerNarrative}`);
      for (const r of si.risks) bullet(`[${r.type}] ${r.description}`);
      if (si.nextAction) para(`Recommended next action: ${si.nextAction}`);
      if (si.nextActionRationale) para(si.nextActionRationale, { muted: true });
    }
  }

  h1(`Evidence (${data.evidence.length})`);
  if (data.evidence.length) {
    table(
      ["Label", "Excerpt", "Source", "Confidence", "Date"],
      data.evidence.map((e) => [e.label, e.excerpt, e.source, e.confidence, e.date]),
    );
  } else {
    para("No evidence on file.", { muted: true });
  }

  if (data.sources.length) {
    h1("Sources / Collector Status");
    table(
      ["Source", "Status", "Signals"],
      data.sources.map((s) => [s.source, s.status, String(s.signalCount)]),
    );
  }

  return doc.output("blob");
}
