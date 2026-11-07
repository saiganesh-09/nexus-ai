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
    reason: string;
    signals: string[];
    policy_version: string;
  } | null;
  error: string | null;
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
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const { clearSession } = await import("./auth");
      clearSession();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
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
};
