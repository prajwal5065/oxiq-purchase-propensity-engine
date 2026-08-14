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

// --- Decision Intelligence -------------------------------------------------

export type FreshnessLabel = "very_fresh" | "recent" | "aging" | "stale" | "unknown";

export type BuyingIntentLevel = "strong" | "moderate" | "weak" | "none" | "insufficient_data";

export interface BuyingIntentSignal {
  evidence_id: string | null;
  label: string;
  excerpt: string;
  source: string;
  strength: "strong" | "moderate" | "weak";
}

export interface BuyingIntentAssessment {
  level: BuyingIntentLevel;
  score: number;
  matched_signals: BuyingIntentSignal[];
  rationale: string;
}

export type ContradictionSeverity = "high" | "medium";

export interface ContradictionEvidenceRef {
  evidence_id: string | null;
  label: string;
  excerpt: string;
  source: string;
}

export interface ContradictionFinding {
  theme: string;
  severity: ContradictionSeverity;
  description: string;
  evidence_a: ContradictionEvidenceRef;
  evidence_b: ContradictionEvidenceRef;
}

export interface ContradictionReport {
  has_contradictions: boolean;
  findings: ContradictionFinding[];
  summary: string;
}

export interface WhyNowTrigger {
  evidence_id: string | null;
  label: string;
  excerpt: string;
  source: string;
  trigger_type: string;
  published_at: string | null;
  freshness_label: FreshnessLabel;
}

export interface WhyNowExplanation {
  has_timing_trigger: boolean;
  data_sufficient: boolean;
  triggers: WhyNowTrigger[];
  narrative: string;
}

export type DecisionPriority = "high_priority" | "medium_priority" | "low_priority" | "insufficient_data";

export const DECISION_PRIORITY_LABELS: Record<DecisionPriority, string> = {
  high_priority: "High Priority",
  medium_priority: "Medium Priority",
  low_priority: "Low Priority",
  insufficient_data: "Insufficient Data",
};

export interface DecisionFactor {
  name: string;
  value: number;
  weight: number;
  description: string;
}

export interface DecisionRecommendation {
  priority: DecisionPriority;
  decision_score: number | null;
  factors: DecisionFactor[];
  rationale: string;
  buying_intent: BuyingIntentAssessment;
  contradictions: ContradictionReport;
  why_now: WhyNowExplanation;
}

export interface ChangeFactor {
  description: string;
  evidence_needed: string[];
}

export interface DecisionChangeAnalysis {
  factors: ChangeFactor[];
  summary: string;
}

export interface EvidenceConfidenceScore {
  evidence_id: string;
  label: string;
  source: string;
  collector: string | null;
  extraction_confidence: number;
  source_reliability: number;
  freshness_weight: number;
  composite_confidence: number;
}

export interface SourceReliability {
  collector: string;
  tier: "high" | "medium" | "low";
  weight: number;
  rationale: string;
  evidence_count: number;
}

export interface DecisionIntelligence {
  recommendation: DecisionRecommendation;
  change_analysis: DecisionChangeAnalysis;
  evidence_confidence: EvidenceConfidenceScore[];
  source_reliability: SourceReliability[];
}

// --- Sales Intelligence ------------------------------------------------------

export interface OpportunityItem {
  description: string;
  evidence_ids: string[];
  confidence: number;
}

export interface SolutionFitItem {
  use_case: string;
  fit_reasoning: string;
  evidence_ids: string[];
  confidence: number;
}

export interface StakeholderRole {
  role_title: string;
  rationale: string;
  evidence_ids: string[];
}

export interface SalesTrigger {
  trigger_type: string;
  label: string;
  excerpt: string;
  source: string;
  evidence_id: string | null;
  freshness_label: string;
  narrative: string;
}

export type SalesRiskType = "contradiction" | "missing_evidence" | "existing_vendor" | "other";

export interface SalesRisk {
  description: string;
  risk_type: SalesRiskType;
  evidence_ids: string[];
}

export interface SalesAction {
  action: string;
  rationale: string;
  evidence_ids: string[];
}

export interface SalesIntelligence {
  opportunity: OpportunityItem | null;
  solution_fit: SolutionFitItem | null;
  likely_buyer_roles: StakeholderRole[];
  sales_trigger: SalesTrigger | null;
  risks: SalesRisk[];
  recommended_next_action: SalesAction | null;
  evidence_ids: string[];
  confidence: number;
  data_sufficient: boolean;
}

export interface AnalysisExplanation {
  company_domain: string;
  headline: string;
  evidence_coverage: EvidenceCoverage;
  confidence_explanation: ConfidenceExplanation;
  pillar_explanations: PillarExplanation[];
  disqualification: DisqualificationExplanation;
  decision_intelligence: DecisionIntelligence;
  sales_intelligence: SalesIntelligence | null;
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
  // Structured Technology fields (null on non-technology evidence, or when
  // extraction couldn't be correlated back to a raw tech signal by URL).
  technology_name: string | null;
  technology_provider: string | null;
  // Structured Jobs fields (null on non-jobs evidence, same caveat).
  job_title: string | null;
  job_department: string | null;
  job_location: string | null;
  job_ats_provider: string | null;
  job_posting_date: string | null;
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
