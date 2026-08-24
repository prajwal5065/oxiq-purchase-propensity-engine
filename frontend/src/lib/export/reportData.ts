// Flattens the dossier's existing structured types (CompanySummary,
// PillarScore, RecommendationResult, AnalysisExplanation, EvidenceRecord -
// all from ../../types) into one report-shaped model every export renderer
// (Markdown, DOCX, PDF) consumes identically. This is deliberately the only
// place that reads field names off the raw API types - renderers never
// touch DossierData/AnalysisExplanation directly, so every format stays in
// sync by construction. JSON export bypasses this and serializes the raw
// dossier instead (see toJson.ts) - "preserve the complete structured
// result" means the JSON export should not lose fields this flattening
// intentionally drops (evidence_ids, raw enums, etc).
import { DECISION_PRIORITY_LABELS, PILLAR_LABELS } from "../../types";
import type {
  AnalysisExplanation,
  CompanySummary,
  EvidenceRecord,
  PillarScore,
  RecommendationResult,
} from "../../types";
import { formatDate, formatLabel, formatPercent, formatScore } from "../format";

export interface ReportPillar {
  name: string;
  score: string;
  confidence: string;
  reasons: string[];
}

export interface ReportConfidenceFactor {
  name: string;
  value: string;
  weight: string;
  description: string;
}

export interface ReportBuyingSignal {
  label: string;
  excerpt: string;
  source: string;
  strength: string;
}

export interface ReportWhyNowTrigger {
  label: string;
  excerpt: string;
  source: string;
  triggerType: string;
  freshness: string;
}

export interface ReportContradiction {
  theme: string;
  severity: string;
  description: string;
  evidenceA: string;
  evidenceB: string;
}

export interface ReportChangeFactor {
  description: string;
  evidenceNeeded: string[];
}

export interface ReportBuyerRole {
  title: string;
  rationale: string;
}

export interface ReportRisk {
  description: string;
  type: string;
}

export interface ReportEvidenceItem {
  label: string;
  excerpt: string;
  source: string;
  url: string | null;
  date: string;
  confidence: string;
  category: string;
}

export interface ReportSource {
  source: string;
  status: string;
  signalCount: number;
}

export interface ReportData {
  generatedAt: string;
  company: {
    name: string;
    domain: string;
    industry: string | null;
    lastProcessed: string;
  };
  decision: {
    priorityLabel: string;
    disqualified: boolean;
    finalDecision: string;
    purchaseScore: string;
    purchaseConfidence: string;
    headline: string | null;
    primaryReason: string | null;
    secondaryReasons: string[];
  };
  confidence: {
    overall: string;
    level: string;
    summary: string;
    factors: ReportConfidenceFactor[];
  } | null;
  pillars: ReportPillar[];
  decisionIntelligence: {
    buyingIntentLevel: string;
    buyingIntentRationale: string;
    buyingIntentSignals: ReportBuyingSignal[];
    whyNowNarrative: string;
    whyNowTriggers: ReportWhyNowTrigger[];
    contradictionsSummary: string;
    contradictions: ReportContradiction[];
    changeSummary: string;
    changeFactors: ReportChangeFactor[];
  } | null;
  salesIntelligence: {
    dataSufficient: boolean;
    opportunity: string | null;
    solutionFitUseCase: string | null;
    solutionFitReasoning: string | null;
    buyerRoles: ReportBuyerRole[];
    salesTriggerNarrative: string | null;
    risks: ReportRisk[];
    nextAction: string | null;
    nextActionRationale: string | null;
  } | null;
  evidence: ReportEvidenceItem[];
  sources: ReportSource[];
}

export interface DossierData {
  company: CompanySummary;
  pillars: PillarScore[];
  purchaseScore: number;
  purchaseConfidence: number;
  recommendation: RecommendationResult | null;
  explanation: AnalysisExplanation | null;
  evidence: EvidenceRecord[];
}

export function buildReportData(dossier: DossierData): ReportData {
  const { company, pillars, purchaseScore, purchaseConfidence, explanation, evidence } = dossier;

  const disqualification = explanation?.disqualification ?? null;
  const decisionIntel = explanation?.decision_intelligence ?? null;
  const salesIntel = explanation?.sales_intelligence ?? null;
  const confidenceExplanation = explanation?.confidence_explanation ?? null;

  const disqualified = disqualification
    ? disqualification.final_decision !== "qualified"
    : purchaseScore === 0 && purchaseConfidence === 0;

  const priorityLabel = decisionIntel
    ? DECISION_PRIORITY_LABELS[decisionIntel.recommendation.priority]
    : disqualified
      ? "Low Priority"
      : purchaseScore >= 70
        ? "High Priority"
        : purchaseScore >= 40
          ? "Medium Priority"
          : "Low Priority";

  return {
    generatedAt: new Date().toISOString(),
    company: {
      name: company.name,
      domain: company.domain,
      industry: company.industry,
      lastProcessed: formatDate(company.last_processed_at),
    },
    decision: {
      priorityLabel,
      disqualified,
      finalDecision: disqualification ? formatLabel(disqualification.final_decision) : "Unknown",
      purchaseScore: formatScore(purchaseScore),
      purchaseConfidence: formatPercent(purchaseConfidence),
      headline: explanation?.headline ?? null,
      primaryReason: disqualification?.primary_reason ?? null,
      secondaryReasons: disqualification?.secondary_reasons ?? [],
    },
    confidence: confidenceExplanation
      ? {
          overall: formatPercent(confidenceExplanation.overall_confidence),
          level: formatLabel(confidenceExplanation.level),
          summary: confidenceExplanation.summary,
          factors: confidenceExplanation.factors.map((f) => ({
            name: f.name,
            value: formatPercent(f.value),
            weight: formatPercent(f.weight),
            description: f.description,
          })),
        }
      : null,
    pillars: pillars.map((p) => ({
      name: PILLAR_LABELS[p.score_type] ?? p.score_type,
      score: formatScore(p.score),
      confidence: formatPercent(p.confidence),
      reasons: p.reasons,
    })),
    decisionIntelligence: decisionIntel
      ? {
          buyingIntentLevel: formatLabel(decisionIntel.recommendation.buying_intent.level),
          buyingIntentRationale: decisionIntel.recommendation.buying_intent.rationale,
          buyingIntentSignals: decisionIntel.recommendation.buying_intent.matched_signals.map((s) => ({
            label: s.label,
            excerpt: s.excerpt,
            source: s.source,
            strength: formatLabel(s.strength),
          })),
          whyNowNarrative: decisionIntel.recommendation.why_now.narrative,
          whyNowTriggers: decisionIntel.recommendation.why_now.triggers.map((t) => ({
            label: t.label,
            excerpt: t.excerpt,
            source: t.source,
            triggerType: formatLabel(t.trigger_type),
            freshness: formatLabel(t.freshness_label),
          })),
          contradictionsSummary: decisionIntel.recommendation.contradictions.summary,
          contradictions: decisionIntel.recommendation.contradictions.findings.map((f) => ({
            theme: f.theme,
            severity: formatLabel(f.severity),
            description: f.description,
            evidenceA: `${f.evidence_a.excerpt} (${f.evidence_a.source})`,
            evidenceB: `${f.evidence_b.excerpt} (${f.evidence_b.source})`,
          })),
          changeSummary: decisionIntel.change_analysis.summary,
          changeFactors: decisionIntel.change_analysis.factors.map((f) => ({
            description: f.description,
            evidenceNeeded: f.evidence_needed,
          })),
        }
      : null,
    salesIntelligence: salesIntel
      ? {
          dataSufficient: salesIntel.data_sufficient,
          opportunity: salesIntel.opportunity?.description ?? null,
          solutionFitUseCase: salesIntel.solution_fit?.use_case ?? null,
          solutionFitReasoning: salesIntel.solution_fit?.fit_reasoning ?? null,
          buyerRoles: salesIntel.likely_buyer_roles.map((r) => ({
            title: r.role_title,
            rationale: r.rationale,
          })),
          salesTriggerNarrative: salesIntel.sales_trigger?.narrative ?? null,
          risks: salesIntel.risks.map((r) => ({
            description: r.description,
            type: formatLabel(r.risk_type),
          })),
          nextAction: salesIntel.recommended_next_action?.action ?? null,
          nextActionRationale: salesIntel.recommended_next_action?.rationale ?? null,
        }
      : null,
    evidence: evidence.map((e) => ({
      label: e.signal_label,
      excerpt: e.excerpt,
      source: e.source,
      url: e.url,
      date: e.published_at ? formatDate(e.published_at) : formatDate(e.created_at),
      confidence: formatPercent(e.confidence),
      category: e.category ? formatLabel(e.category) : "Uncategorized",
    })),
    sources: explanation?.evidence_coverage.collector_statuses.map((s) => ({
      source: s.source,
      status: formatLabel(s.status),
      signalCount: s.signal_count,
    })) ?? [],
  };
}
