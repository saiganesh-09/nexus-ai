"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, Loader2, Search, X } from "lucide-react";
import { api, type PaginatedRequests, type RequestDetail } from "@/lib/api-client";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";

const STATUS_VARIANT: Record<string, "success" | "danger" | "warning" | "default"> = {
  success: "success",
  failed: "danger",
  pending: "warning",
};

export default function RequestsPage() {
  const authed = useRequireAuth();
  const [data, setData] = useState<PaginatedRequests | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [provider, setProvider] = useState("");
  const [page, setPage] = useState(1);
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(
        await api.listRequests({
          page,
          page_size: 15,
          q: q || undefined,
          status: status || undefined,
          provider: provider || undefined,
        }),
      );
      setError(null);
    } catch {
      setError("Failed to load requests");
    } finally {
      setLoading(false);
    }
  }, [page, q, status, provider]);

  useEffect(() => {
    if (!authed) return;
    const t = setTimeout(() => {
      const param = new URLSearchParams(window.location.search).get("q");
      if (param) setQ(param);
      void load();
    }, 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed]);

  async function openDetail(id: string) {
    setDetailLoading(true);
    try {
      setDetail(await api.getRequest(id));
    } finally {
      setDetailLoading(false);
    }
  }

  if (!authed) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Request History</h1>
        <p className="mt-1 text-sm text-text-secondary">Every AI request, persisted and auditable.</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); setPage(1); }}
            placeholder="Search prompts and responses…"
            className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:border-brand-500/60 focus:outline-none"
          />
        </div>
        <select value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }} className="h-9 rounded-lg border border-border bg-surface px-3 text-sm text-text-primary focus:border-brand-500/60 focus:outline-none">
          <option value="">All statuses</option>
          <option value="success">Success</option>
          <option value="failed">Failed</option>
          <option value="pending">Pending</option>
        </select>
        <select value={provider} onChange={(e) => { setProvider(e.target.value); setPage(1); }} className="h-9 rounded-lg border border-border bg-surface px-3 text-sm text-text-primary focus:border-brand-500/60 focus:outline-none">
          <option value="">All providers</option>
          <option value="openai-compatible">openai-compatible</option>
          <option value="anthropic">anthropic</option>
        </select>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex h-48 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-brand-400" /></div>
          ) : error ? (
            <div className="p-6 text-sm text-danger">{error}</div>
          ) : !data || data.items.length === 0 ? (
            <div className="p-10 text-center text-sm text-text-muted">No requests match your filters.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-text-muted">
                    <th className="px-4 py-3 font-medium">Status</th>
                    <th className="px-4 py-3 font-medium">Model</th>
                    <th className="px-4 py-3 font-medium">Prompt</th>
                    <th className="px-4 py-3 font-medium">Tokens</th>
                    <th className="px-4 py-3 font-medium">Cost</th>
                    <th className="px-4 py-3 font-medium">Latency</th>
                    <th className="px-4 py-3 font-medium">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => openDetail(r.id)}
                      className="cursor-pointer border-b border-border/60 transition-colors hover:bg-surface-raised"
                    >
                      <td className="px-4 py-3"><Badge variant={STATUS_VARIANT[r.status] ?? "default"}>{r.status}</Badge></td>
                      <td className="px-4 py-3">
                        <div className="text-text-primary">{r.model}</div>
                        <div className="text-[11px] text-text-muted">{r.provider}</div>
                      </td>
                      <td className="max-w-64 truncate px-4 py-3 text-text-secondary">{r.prompt}</td>
                      <td className="px-4 py-3 text-text-secondary">
                        {r.input_tokens ?? "—"}/{r.output_tokens ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-text-secondary">
                        {r.estimated_cost_usd != null ? `$${r.estimated_cost_usd.toFixed(4)}` : "—"}
                      </td>
                      <td className="px-4 py-3 text-text-secondary">{r.latency_ms != null ? `${r.latency_ms}ms` : "—"}</td>
                      <td className="px-4 py-3 text-xs text-text-muted">{new Date(r.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between text-sm text-text-secondary">
          <span>{data.total} requests — page {data.page} of {data.pages}</span>
          <div className="flex gap-2">
            <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 hover:bg-surface-raised disabled:opacity-40">
              <ChevronLeft className="h-4 w-4" /> Prev
            </button>
            <button disabled={page >= data.pages} onClick={() => setPage((p) => p + 1)} className="flex items-center gap-1 rounded-lg border border-border px-3 py-1.5 hover:bg-surface-raised disabled:opacity-40">
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Detail drawer */}
      {(detail || detailLoading) && (
        <div className="fixed inset-0 z-50 flex justify-end bg-black/60" onClick={() => setDetail(null)}>
          <div
            className="h-full w-full max-w-lg overflow-y-auto border-l border-border bg-surface p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-text-primary">Request detail</h2>
              <button onClick={() => setDetail(null)} className="rounded-lg p-1.5 text-text-muted hover:bg-surface-raised hover:text-text-primary" aria-label="Close">
                <X className="h-4 w-4" />
              </button>
            </div>
            {detailLoading || !detail ? (
              <div className="flex h-40 items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-brand-400" /></div>
            ) : (
              <div className="space-y-4 text-sm">
                <Field label="Status"><Badge variant={STATUS_VARIANT[detail.status] ?? "default"}>{detail.status}</Badge></Field>
                <Field label="Model"><span className="font-mono text-xs">{detail.provider}/{detail.model}</span></Field>
                <Field label="Type">{detail.request_type}</Field>
                <Field label="Tokens">{detail.input_tokens ?? "n/a"} in / {detail.output_tokens ?? "n/a"} out{detail.input_tokens == null && <span className="ml-1 text-text-muted">(unavailable)</span>}</Field>
                <Field label="Cost">{detail.estimated_cost_usd != null ? `$${detail.estimated_cost_usd.toFixed(6)}${detail.cost_is_estimate ? " (est.)" : ""}` : "n/a"}</Field>
                <Field label="Latency">{detail.latency_ms != null ? `${detail.latency_ms} ms` : "n/a"}</Field>
                <Field label="Time">{new Date(detail.created_at).toLocaleString()}</Field>
                {detail.cache_hit && <Field label="Cache">hit</Field>}
                {detail.error_message && (
                  <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-xs text-danger">{detail.error_message}</div>
                )}
                {detail.routing_decision && (
                  <div className="rounded-lg border border-border bg-surface-raised px-3 py-2">
                    <div className="text-xs font-medium text-text-secondary">Routing decision</div>
                    <div className="mt-1 text-xs text-text-muted">
                      {detail.routing_decision.complexity_tier} ({detail.routing_decision.complexity_score.toFixed(2)}) → {detail.routing_decision.selected_provider}/{detail.routing_decision.selected_model} · policy {detail.routing_decision.policy_version}
                    </div>
                    <p className="mt-1 text-[11px] leading-relaxed text-text-muted">{detail.routing_decision.reason}</p>
                  </div>
                )}
                <div>
                  <div className="mb-1 text-xs font-medium text-text-secondary">Prompt</div>
                  <pre className="whitespace-pre-wrap rounded-lg border border-border bg-canvas p-3 text-xs text-text-primary">{detail.prompt}</pre>
                </div>
                {detail.response_text && (
                  <div>
                    <div className="mb-1 text-xs font-medium text-text-secondary">Response</div>
                    <pre className="whitespace-pre-wrap rounded-lg border border-border bg-canvas p-3 text-xs text-text-primary">{detail.response_text}</pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="shrink-0 text-xs text-text-muted">{label}</span>
      <span className="text-right text-xs text-text-primary">{children}</span>
    </div>
  );
}
