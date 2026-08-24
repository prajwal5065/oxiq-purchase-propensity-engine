import { downloadBlob, slugifyFilename } from "./download";
import { buildDocxBlob } from "./toDocx";
import { reportToJsonString } from "./toJson";
import { reportToMarkdown } from "./toMarkdown";
import { buildPdfBlob } from "./toPdf";
import { buildReportData } from "./reportData";
import type { DossierData } from "./reportData";

export type ExportFormat = "docx" | "pdf" | "json" | "copy";

export async function exportReport(format: ExportFormat, dossier: DossierData): Promise<void> {
  const stem = slugifyFilename(dossier.company.name);

  if (format === "json") {
    const blob = new Blob([reportToJsonString(dossier)], { type: "application/json" });
    downloadBlob(blob, `${stem}-oxiq-report.json`);
    return;
  }

  if (format === "copy") {
    const markdown = reportToMarkdown(buildReportData(dossier));
    await navigator.clipboard.writeText(markdown);
    return;
  }

  const reportData = buildReportData(dossier);

  if (format === "docx") {
    const blob = await buildDocxBlob(reportData);
    downloadBlob(blob, `${stem}-oxiq-report.docx`);
    return;
  }

  if (format === "pdf") {
    const blob = buildPdfBlob(reportData);
    downloadBlob(blob, `${stem}-oxiq-report.pdf`);
    return;
  }
}

export { buildReportData } from "./reportData";
export type { ReportData, DossierData } from "./reportData";
export { reportToMarkdown } from "./toMarkdown";
export { reportToJsonString, buildJsonExport } from "./toJson";
