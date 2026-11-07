"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Copy, Loader2, RefreshCw, Send, Zap } from "lucide-react";
import { api, ApiError, type ChatResponse, type ModelInfo } from "@/lib/api-client";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PlaygroundPage() {
  const authed = useRequireAuth();
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("auto");
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [result, setResult] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!authed) return;
    api
      .listModels()
      .then(setModels)
      .catch(() => setModels([]));
  }, [authed]);

  const submit = useCallback(async () => {
    if (!prompt.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.chat(prompt.trim(), model);
      setResult(res);
    } catch (err) {
      setResult(null);
      setError(err instanceof ApiError ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, [prompt, model, loading]);

  async function copyResponse() {
    if (!result) return;
    await navigator.clipboard.writeText(result.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  if (!authed) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      </div>
    );
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      {/* Input panel */}
      <div className="space-y-4">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Playground</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Submit a prompt — NEXUS routes it to the right model automatically.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Prompt</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) submit();
              }}
              rows={8}
              placeholder="Ask anything… (Ctrl+Enter to send)"
              className="w-full resize-y rounded-lg border border-border bg-surface px-3 py-2.5 text-sm text-text-primary placeholder:text-text-muted focus:border-brand-500/60 focus:outline-none"
            />

            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">
                Model
              </label>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary focus:border-brand-500/60 focus:outline-none"
              >
                <option value="auto">Auto (intelligent routing)</option>
                {models.map((m) => (
                  <option
                    key={`${m.provider}/${m.model_id}`}
                    value={`${m.provider}/${m.model_id}`}
                    disabled={!m.provider_configured}
                  >
                    {m.display_name}
                    {m.provider_configured ? "" : " (provider not configured)"}
                  </option>
                ))}
              </select>
            </div>

            {error && (
              <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">
                {error}
              </div>
            )}

            <button
              onClick={submit}
              disabled={loading || !prompt.trim()}
              className="flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-brand-600 text-sm font-semibold text-white transition-colors hover:bg-brand-500 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" /> Generating…
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" /> Send prompt
                </>
              )}
            </button>
          </CardContent>
        </Card>
      </div>

      {/* Response panel */}
      <div className="space-y-4">
        <Card className="min-h-[420px]">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-sm">Response</CardTitle>
            {result && (
              <div className="flex gap-2">
                <button
                  onClick={copyResponse}
                  className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs text-text-secondary hover:bg-surface-raised hover:text-text-primary"
                >
                  {copied ? <Check className="h-3.5 w-3.5 text-success" /> : <Copy className="h-3.5 w-3.5" />}
                  {copied ? "Copied" : "Copy"}
                </button>
                <button
                  onClick={submit}
                  disabled={loading}
                  className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs text-text-secondary hover:bg-surface-raised hover:text-text-primary disabled:opacity-50"
                >
                  <RefreshCw className="h-3.5 w-3.5" /> Regenerate
                </button>
              </div>
            )}
          </CardHeader>
          <CardContent>
            {loading && (
              <div className="flex h-48 flex-col items-center justify-center gap-3 text-text-secondary">
                <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
                <span className="text-sm">Waiting for model response…</span>
              </div>
            )}
            {!loading && !result && !error && (
              <div className="flex h-48 flex-col items-center justify-center gap-2 text-center text-text-muted">
                <Zap className="h-8 w-8 opacity-40" />
                <p className="text-sm">Your response will appear here.</p>
              </div>
            )}
            {!loading && result && (
              <div className="space-y-4">
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
                  {result.content}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {result && (
          <Card>
            <CardContent className="grid grid-cols-2 gap-4 pt-5 sm:grid-cols-4">
              <Metric label="Model" value={result.model_display_name ?? result.model} />
              <Metric
                label="Tokens"
                value={`${result.input_tokens ?? "—"} in / ${result.output_tokens ?? "—"} out`}
              />
              <Metric
                label="Est. cost"
                value={
                  result.estimated_cost_usd != null
                    ? `$${result.estimated_cost_usd.toFixed(6)}${result.cost_is_estimate ? "*" : ""}`
                    : "n/a"
                }
              />
              <Metric label="Latency" value={`${result.latency_ms} ms`} />
            </CardContent>
            {(result.cost_is_estimate || result.routing) && (
              <CardContent className="space-y-2 pt-0">
                {result.cost_is_estimate && (
                  <p className="text-[11px] text-text-muted">
                    * Cost is estimated — the provider did not report token usage.
                  </p>
                )}
                {result.routing && (
                  <div className="rounded-lg border border-border bg-surface-raised px-3 py-2">
                    <div className="flex items-center gap-2 text-xs">
                      <Badge variant="brand">auto-routed</Badge>
                      <span className="text-text-secondary">
                        complexity {result.routing.complexity_tier} (
                        {result.routing.complexity_score.toFixed(2)}) · policy{" "}
                        {result.routing.policy_version}
                      </span>
                    </div>
                    <p className="mt-1.5 text-[11px] leading-relaxed text-text-muted">
                      {result.routing.reason}
                    </p>
                  </div>
                )}
              </CardContent>
            )}
          </Card>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[11px] font-medium uppercase tracking-wider text-text-muted">
        {label}
      </div>
      <div className="mt-1 truncate text-sm font-medium text-text-primary" title={value}>
        {value}
      </div>
    </div>
  );
}
