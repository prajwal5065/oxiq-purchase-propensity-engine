import type {
  AnalysisExplanation,
  AnalyzeJobAccepted,
  CompanyListResponse,
  CompanySummary,
  DashboardSummary,
  EvidenceRecord,
  JobStatusResponse,
  PillarScore,
  RecommendationResult,
} from "../types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new ApiError(response.status, body || response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  submitAnalysis: (domain: string, name?: string) =>
    request<AnalyzeJobAccepted>("/analyze", {
      method: "POST",
      body: JSON.stringify({ domain, name: name || undefined }),
    }),

  getJobStatus: (jobId: string) => request<JobStatusResponse>(`/jobs/${jobId}`),

  getCompany: (companyId: string) => request<CompanySummary>(`/company/${companyId}`),

  listCompanies: (params: { limit?: number; offset?: number; industry?: string } = {}) => {
    const search = new URLSearchParams();
    if (params.limit) search.set("limit", String(params.limit));
    if (params.offset) search.set("offset", String(params.offset));
    if (params.industry) search.set("industry", params.industry);
    const qs = search.toString();
    return request<CompanyListResponse>(`/companies${qs ? `?${qs}` : ""}`);
  },

  getScores: (companyId: string) => request<PillarScore[]>(`/scores/${companyId}`),

  getRecommendation: async (companyId: string): Promise<RecommendationResult | null> => {
    try {
      return await request<RecommendationResult>(`/company/${companyId}/recommendation`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },

  getExplanation: async (companyId: string): Promise<AnalysisExplanation | null> => {
    try {
      return await request<AnalysisExplanation>(`/company/${companyId}/explanation`);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) return null;
      throw err;
    }
  },

  getEvidence: (companyId: string) => request<EvidenceRecord[]>(`/company/${companyId}/evidence`),

  getDashboardSummary: () => request<DashboardSummary>("/dashboard/summary"),
};

export { ApiError };
