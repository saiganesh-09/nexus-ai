import { API_BASE_URL } from "./api";
import { getToken } from "./auth";

export interface ChatResponse {
  id: string;
  provider: string;
  model: string;
  model_display_name: string | null;
  content: string;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number;
  estimated_cost_usd: number | null;
  cost_is_estimate: boolean;
  status: string;
  routing: {
    complexity_score: number;
    complexity_tier: string;
    selected_provider: string;
    selected_model: string;
    reason: string;
    signals: string[];
    policy_version: string;
    timestamp: string;
  } | null;
  error: string | null;
}

export interface RoutingExplanation {
  prompt: string;
  complexity_score: number;
  complexity_tier: string;
  signals: string[];
  selected_provider: string;
  selected_model: string;
  reason: string;
  policy_version: string;
  fallback_candidates: { provider: string; model_id: string }[];
  manual_bypass: boolean;
  decided_at: string;
}

export interface ModelInfo {
  provider: string;
  model_id: string;
  display_name: string;
  input_price_per_mtok: number;
  output_price_per_mtok: number;
  context_window: number;
  capabilities: Record<string, unknown>;
  provider_configured: boolean;
}

export interface AnalyticsOverview {
  requests: number;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
  cache_hit_rate: number;
  timeseries: { date: string; requests: number; cost: number; errors: number }[];
  model_usage: { model: string; count: number }[];
  window_days: number;
}

export interface ModelAnalytics {
  provider: string;
  model: string;
  requests: number;
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
}

export interface RequestListItem {
  id: string;
  request_type: string;
  provider: string;
  model: string;
  status: string;
  prompt: string;
  response_text: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  estimated_cost_usd: number | null;
  cost_is_estimate: boolean;
  cache_hit: boolean;
  error_message: string | null;
  created_at: string;
}

export interface RequestDetail extends RequestListItem {
  conversation_id: string | null;
  routing_decision: {
    complexity_score: number;
    complexity_tier: string;
    selected_provider: string;
    selected_model: string;
    reason: string;
    policy_version: string;
    created_at: string;
  } | null;
}

export interface PaginatedRequests {
  items: RequestListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface RequestListParams {
  page?: number;
  page_size?: number;
  status?: string;
  provider?: string;
  model?: string;
  request_type?: string;
  q?: string;
}

export interface CompareResultItem {
  request_id: string;
  provider: string;
  model: string;
  model_display_name: string | null;
  content: string | null;
  input_tokens: number | null;
  output_tokens: number | null;
  latency_ms: number | null;
  estimated_cost_usd: number | null;
  cost_is_estimate: boolean;
  status: string;
  error: string | null;
}

export interface CompareResponse {
  prompt: string;
  results: CompareResultItem[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers ?? {}),
    },
  });
  if (!res.ok) {
    let code: string | undefined;
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      code = body?.error?.code;
      if (body?.error?.message) message = body.error.message;
    } catch {
      /* non-JSON error body */
    }
    if (res.status === 401) {
      const { clearSession } = await import("./auth");
      clearSession();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.assign("/login");
      }
    }
    throw new ApiError(message, res.status, code);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request<{ id: string; email: string; full_name: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string; expires_in: number }>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
    ),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  me: () =>
    request<{ id: string; email: string; full_name: string; is_active: boolean }>(
      "/auth/me",
    ),
  listModels: () => request<ModelInfo[]>("/models"),
  chat: (prompt: string, model?: string) =>
    request<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ prompt, model: model || "auto" }),
    }),
  explainRouting: (prompt: string) =>
    request<RoutingExplanation>("/routing/explain", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
  analyticsOverview: (days = 30) =>
    request<AnalyticsOverview>(`/analytics/overview?days=${days}`),
  analyticsByModel: (days = 30) =>
    request<ModelAnalytics[]>(`/analytics/models?days=${days}`),
  listRequests: (params: RequestListParams = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", String(params.page));
    if (params.page_size) qs.set("page_size", String(params.page_size));
    if (params.status) qs.set("status", params.status);
    if (params.provider) qs.set("provider", params.provider);
    if (params.model) qs.set("model", params.model);
    if (params.request_type) qs.set("request_type", params.request_type);
    if (params.q) qs.set("q", params.q);
    return request<PaginatedRequests>(`/requests?${qs.toString()}`);
  },
  getRequest: (id: string) => request<RequestDetail>(`/requests/${id}`),
  compare: (prompt: string, models: string[]) =>
    request<CompareResponse>("/compare", {
      method: "POST",
      body: JSON.stringify({ prompt, models }),
    }),
  updateProfile: (full_name?: string, password?: string) =>
    request<{ id: string; email: string; full_name: string }>("/users/me", {
      method: "PATCH",
      body: JSON.stringify({ full_name, password }),
    }),
};
