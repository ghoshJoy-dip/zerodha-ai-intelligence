export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface InsightRecord {
  id: number;
  category: string;
  title: string;
  confidence_score: number | string | null;
  is_validated: boolean;
  validation_reason: string | null;
  raw_json: Record<string, unknown>;
}

export interface RecommendationCardData {
  id: number;
  job_id: string | null;
  category: string;
  title: string;
  rationale: string;
  supporting_metrics: { metric_name: string; metric_value: number }[];
  confidence: number;
  freshness_timestamp: string | null;
  disclaimer: string;
  status: string;
  is_validated: boolean;
  validation_reason: string | null;
}

export interface JobResult {
  job_id: string;
  status: string;
  job: {
    id: string;
    status: string;
    portfolio_id: string | null;
    job_type: string | null;
    created_at: string;
    completed_at: string | null;
  };
  insight: InsightRecord | null;
  recommendations: RecommendationCardData[];
  empty_state?: {
    message: string;
    fallback_available: boolean;
    fallback_source: string;
    fallback_action: string;
  } | null;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  tool_name: string | null;
  parameters: Record<string, unknown> | null;
  latency_ms: number | string | null;
  status: string | null;
  error_message: string | null;
  description: string | null;
  created_at: string;
}

export interface AuditResult {
  job_id: string;
  job: JobResult["job"];
  events: AuditEvent[];
  operations: {
    event_count: number;
    failed_event_count: number;
    failure_rate_pct: number;
    average_latency_ms: number | null;
    feedback: { total: number; by_action: Record<string, number> };
  };
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export function startPortfolioAnalysis(userId: string, timeframe: string) {
  return requestJson<{ job_id: string; status: string }>("/api/portfolio-analysis", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, source: "sample", timeframe }),
  });
}

export function getJobResult(jobId: string) {
  return requestJson<JobResult>(`/api/insights/${encodeURIComponent(jobId)}`);
}

export function getJobAudit(jobId: string) {
  return requestJson<AuditResult>(`/api/audit/${encodeURIComponent(jobId)}`);
}

export function refreshMarket(userId: string, timeframe: string) {
  return requestJson<Record<string, unknown>>("/api/market-refresh", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, source: "sample", timeframe }),
  });
}

export function submitFeedback(
  cardId: number,
  action: "thumbs_up" | "thumbs_down" | "accepted" | "dismissed",
  note?: string,
) {
  return requestJson<{ id: number; card_id: number; action: string; note: string | null }>(
    "/api/feedback",
    {
      method: "POST",
      body: JSON.stringify({ card_id: cardId, action, note }),
    },
  );
}

export function getActiveJobId() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("activeJobId");
}

export function saveActiveJob(jobId: string, userId: string, timeframe: string) {
  window.localStorage.setItem("activeJobId", jobId);
  window.localStorage.setItem("activeUserId", userId);
  window.localStorage.setItem("activeTimeframe", timeframe);
  window.dispatchEvent(new Event("active-job-storage"));
}
