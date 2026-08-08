export type JobStatus = "pending" | "running" | "completed" | "failed";

export type ScoreType =
  | "need"
  | "urgency"
  | "capacity"
  | "digital_maturity"
  | "org_readiness"
  | "winnability"
  | "purchase_propensity";

export const PILLAR_TYPES: Exclude<ScoreType, "purchase_propensity">[] = [
  "need",
  "urgency",
  "capacity",
  "digital_maturity",
  "org_readiness",
  "winnability",
];

export const PILLAR_LABELS: Record<string, string> = {
  need: "Need",
  urgency: "Urgency",
  capacity: "Capacity",
  digital_maturity: "Digital Maturity",
  org_readiness: "Org Readiness",
  winnability: "Winnability",
};

export interface PillarScore {
  score_type: ScoreType;
  score: number;
  confidence: number;
  reasons: string[];
}

export interface AnalyzeJobAccepted {
  job_id: string;
  status: JobStatus;
  status_url: string;
}

export interface JobStatusResponse {
  job_id: string;
  status: JobStatus;
  company_domain: string;
  company_id: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface CompanySummary {
  id: string;
  name: string;
  domain: string;
  industry: string | null;
  created_at: string;
  last_processed_at: string | null;
  purchase_score: number | null;
  final_decision: "qualified" | "disqualified" | "insufficient_data" | null;
  disqualification_category: DisqualificationCategory | null;
  confidence: number | null;
  coverage_percentage: number | null;
}

export interface CompanyListResponse {
  items: CompanySummary[];
  total: number;
  limit: number;
  offset: number;
}

export type ContactPriority = "high" | "medium" | "low";

export interface RecommendationResult {
  executive_summary: string;
  fit_reasons: string[];
  top_buying_signals: string[];
  top_risks: string[];
  suggested_approach: string;
  contact_priority: ContactPriority;
  solution_match: string | null;
}

export type CollectorStatusType =
  | "success"
  | "no_results"
  | "not_configured"
  | "blocked"
  | "timeout"
  | "error";

export interface CollectorStatusReport {
  source: string;
  status: CollectorStatusType;
  is_live: boolean;
  signal_count: number;
  errors: string[];
}

export interface EvidenceCoverage {
  sources_discovered: number;
  sources_attempted: number;
  sources_successful: number;
  sources_failed: number;
  sources_zero_results: number;
  sources_not_configured: number;
  evidence_items_extracted: number;
  evidence_items_accepted: number;
  coverage_percentage: number;
  collector_statuses: CollectorStatusReport[];
  sources_not_implemented: string[];
}

export interface ConfidenceFactor {
  name: string;
  value: number;
  weight: number;
  description: string;
}

export interface ConfidenceExplanation {
  overall_confidence: number;
  level: "high" | "medium" | "low";
  factors: ConfidenceFactor[];
  summary: string;
}

export interface ScoreContribution {
  evidence_id: string | null;
  label: string;
  excerpt: string;
  source: string;
  points: number;
  direction: "positive" | "negative";
}

export interface PillarExplanation {
  score_type: ScoreType;
  score: number;
  confidence: number;
  positive_evidence: ScoreContribution[];
  negative_evidence: ScoreContribution[];
  missing_expected_signals: string[];
  source_coverage: Record<string, number>;
}

export type DisqualificationCategory =
  | "not_disqualified"
  | "genuine_negative_evidence"
  | "insufficient_evidence"
  | "collection_failure"
  | "source_unavailable";

export interface DisqualificationExplanation {
  final_decision: "qualified" | "disqualified" | "insufficient_data";
  category: DisqualificationCategory;
  primary_reason: string;
  secondary_reasons: string[];
  disqualifying_rules_triggered: string[];
  supporting_evidence: string[];
  missing_evidence: string[];
  data_quality_limitations: string[];
  confidence: number;
  recommended_next_action: string;
}

export interface AnalysisExplanation {
  company_domain: string;
  headline: string;
  evidence_coverage: EvidenceCoverage;
  confidence_explanation: ConfidenceExplanation;
  pillar_explanations: PillarExplanation[];
  disqualification: DisqualificationExplanation;
  generated_at: string;
}

export interface EvidenceRecord {
  id: string;
  signal_label: string;
  excerpt: string;
  source: string;
  url: string | null;
  confidence: number;
  category: string | null;
  collector: string | null;
  pillar: string | null;
  published_at: string | null;
  created_at: string;
}

export interface DecisionCounts {
  qualified: number;
  disqualified: number;
  insufficient_data: number;
}

export interface DisqualificationCategoryCounts {
  not_disqualified: number;
  genuine_negative_evidence: number;
  insufficient_evidence: number;
  collection_failure: number;
  source_unavailable: number;
}

export interface DashboardSummary {
  total_companies: number;
  analyzed_companies: number;
  by_decision: DecisionCounts;
  by_disqualification_category: DisqualificationCategoryCounts;
  avg_confidence: number;
  avg_coverage: number;
  avg_purchase_score: number;
  high_priority_count: number;
}
