// Deliberately serializes the raw dossier objects (company, scores,
// recommendation, explanation, evidence) as returned by the API - not
// ReportData (reportData.ts), which flattens/relabels fields for
// human-readable rendering and drops things like evidence_ids and raw
// enum values. "Preserve the complete structured result" means this export
// should stay lossless.
import type { DossierData } from "./reportData";

export interface JsonExport {
  exported_at: string;
  company: DossierData["company"];
  scores: {
    purchase_score: number;
    purchase_confidence: number;
    pillars: DossierData["pillars"];
  };
  recommendation: DossierData["recommendation"];
  explanation: DossierData["explanation"];
  evidence: DossierData["evidence"];
}

export function buildJsonExport(dossier: DossierData): JsonExport {
  return {
    exported_at: new Date().toISOString(),
    company: dossier.company,
    scores: {
      purchase_score: dossier.purchaseScore,
      purchase_confidence: dossier.purchaseConfidence,
      pillars: dossier.pillars,
    },
    recommendation: dossier.recommendation,
    explanation: dossier.explanation,
    evidence: dossier.evidence,
  };
}

export function reportToJsonString(dossier: DossierData): string {
  return JSON.stringify(buildJsonExport(dossier), null, 2);
}
