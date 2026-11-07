"use client";

import { useCallback, useEffect, useState } from "react";
import { GitCompareArrows, Loader2 } from "lucide-react";
import { api, type CompareResponse, type ModelInfo } from "@/lib/api-client";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ComparisonsPage() {
  const authed = useRequireAuth();
  const [prompt, setPrompt] = useState("");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!authed) return;
    api.listModels().then(setModels).catch(() => {});
  }, [authed]);

  const toggle = (key: string) =>
    setSelected((s) => (s.includes(key) ? s.filter((k) => k !== key) : s.length < 4 ? [...s, key] : s));

  const run = useCallback(async () => {
    if (!prompt.trim() || selected.length < 2 || loading) return;
    setLoading(true);
    setError(null);
    try {
      setResult(await api.compare(prompt.trim(), selected));
    } catch (e) {
      setResult(null);
      setError(e instanceof Error ? e.message : "Comparison failed");
    } finally {
      setLoading(false);
    }
  }, [prompt, selected, loading]);

  if (!authed) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      </div>
    );
  }

  const configured = models.filter((m) => m.provider_configured);

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Model Comparison</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Send one prompt to up to 4 models and compare responses side by side.
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={4}
            placeholder="Enter a prompt to compare across models…"
            className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-brand-500/60 focus:outline-none"
          />
          <div>
            <div className="mb-2 text-xs font-medium text-text-secondary">
              Select 2–4 models ({selected.length}/4)
            </div>
            <div className="flex flex-wrap gap-2">
              {configured.map((m) => {
                const key = `${m.provider}/${m.model_id}`;
                const active = selected.includes(key);
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => toggle(key)}
                    className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                      active
                        ? "border-brand-500/60 bg-brand-500/15 text-brand-300"
                        : "border-border bg-surface text-text-secondary hover:border-border-strong hover:text-text-primary"
                    }`}
                  >
                    {m.display_name}
                  </button>
                );
              })}
              {configured.length === 0 && (
                <span className="text-xs text-text-muted">No configured providers.</span>
              )}
            </div>
          </div>
          {error && (
            <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>
          )}
          <button
            onClick={run}
            disabled={loading || !prompt.trim() || selected.length < 2}
            className="flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-white transition-colors hover:bg-brand-500 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <GitCompareArrows className="h-4 w-4" />}
            {loading ? "Comparing…" : "Compare"}
          </button>
        </CardContent>
      </Card>

      {result && (
        <div
          className="grid gap-4"
          style={{ gridTemplateColumns: `repeat(${Math.min(result.results.length, 4)}, minmax(0, 1fr))` }}
        >
          {result.results.map((r, i) => (
            <Card key={i} className="flex min-h-72 flex-col">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="truncate text-sm">{r.model_display_name ?? r.model}</CardTitle>
                  <Badge variant={r.status === "success" ? "success" : "danger"}>{r.status}</Badge>
                </div>
                <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-text-muted">
                  <span>{r.provider}</span>
                  <span>{r.input_tokens ?? "—"} in / {r.output_tokens ?? "—"} out</span>
                  <span>{r.latency_ms != null ? `${r.latency_ms}ms` : "—"}</span>
                  <span>
                    {r.estimated_cost_usd != null ? `$${r.estimated_cost_usd.toFixed(6)}` : "n/a"}
                    {r.cost_is_estimate ? "*" : ""}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="flex-1">
                {r.status === "success" && r.content ? (
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">{r.content}</p>
                ) : (
                  <p className="text-sm text-danger">{r.error ?? "No response"}</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
