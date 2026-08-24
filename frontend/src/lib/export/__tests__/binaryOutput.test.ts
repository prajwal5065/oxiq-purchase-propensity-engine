import { describe, expect, it } from "vitest";
import { buildReportData } from "../reportData";
import { buildDocxBlob } from "../toDocx";
import { buildPdfBlob } from "../toPdf";
import { sampleDossier } from "./fixtures";

describe("buildDocxBlob", () => {
  it("generates a real, non-empty .docx blob without throwing", async () => {
    const blob = await buildDocxBlob(buildReportData(sampleDossier));
    expect(blob.size).toBeGreaterThan(1000); // a real OOXML zip, not an empty stub
    expect(blob.type).toBe(
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    );
  });

  it("handles missing decision/sales intelligence without throwing", async () => {
    const blob = await buildDocxBlob(buildReportData({ ...sampleDossier, explanation: null }));
    expect(blob.size).toBeGreaterThan(500);
  });

  it("handles empty evidence without throwing", async () => {
    const blob = await buildDocxBlob(buildReportData({ ...sampleDossier, evidence: [] }));
    expect(blob.size).toBeGreaterThan(500);
  });
});

describe("buildPdfBlob", () => {
  it("generates a real, non-empty PDF blob without throwing", () => {
    const blob = buildPdfBlob(buildReportData(sampleDossier));
    expect(blob.size).toBeGreaterThan(1000);
    expect(blob.type).toBe("application/pdf");
  });

  it("handles missing decision/sales intelligence without throwing", () => {
    const blob = buildPdfBlob(buildReportData({ ...sampleDossier, explanation: null }));
    expect(blob.size).toBeGreaterThan(500);
  });

  it("handles a long evidence list (pagination) without throwing", () => {
    const manyEvidence = Array.from({ length: 40 }, (_, i) => ({
      ...sampleDossier.evidence[0],
      id: `e-${i}`,
      excerpt: `Evidence item number ${i} with a reasonably long excerpt to force line wrapping in the PDF renderer.`,
    }));
    const blob = buildPdfBlob(buildReportData({ ...sampleDossier, evidence: manyEvidence }));
    expect(blob.size).toBeGreaterThan(1000);
  });
});
