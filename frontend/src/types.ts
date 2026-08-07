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
