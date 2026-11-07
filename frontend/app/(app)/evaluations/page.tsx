"use client";

import { useCallback, useEffect, useState } from "react";
import { ChevronDown, ChevronRight, FlaskConical, Loader2, Play } from "lucide-react";
import {
  api,
  type EvalDatasetInfo,
  type EvalRunDetail,
  type EvalRunSummary,
} from "@/lib/api-client";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function EvaluationsPage() {
  const authed = useRequireAuth();
  const [dataset, setDataset] = useState<EvalDatasetInfo | null>(null);
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [detail, setDetail] = useState<EvalRunDetail | null>(null);
  const [provider, setProvider] = useState("openai-compatible");
  const [model, setModel] = useState("llama3.2:3b");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedTask, setExpandedTask] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [d, r] = await Promise.all([api.evalDataset(), api.listEvalRuns()]);
    setDataset(d);
    setRuns(r.items);
  }, []);

  useEffect(() => {
    if (!authed) return;
    const t = setTimeout(() => {
      refresh().catch(() => setError("Failed to load evaluations"));
    }, 0);
    return () => clearTimeout(t);
  }, [authed, refresh]);

  async function startRun() {
    setRunning(true);
    setError(null);
    try {
      const run = await api.startEvalRun(provider, model);
      await refresh();
      const full = await api.getEvalRun(run.id);
      setDetail(full);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation run failed");
    } finally {
      setRunning(false);
    }
  }

  async function viewRun(id: string) {
    setDetail(await api.getEvalRun(id));
  }

  if (!authed) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      </div>
    );
  }

  const summary = detail?.summary;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Agent Evaluation</h1>
          <p className="mt-1 text-sm text-text-secondary">
            Deterministic tool-use benchmarks — no LLM judge is used for scoring.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select value={provider} onChange={(e) => setProvider(e.target.value)} className="h-9 rounded-lg border border-border bg-surface px-3 text-sm text-text-primary">
            <option value="openai-compatible">openai-compatible</option>
            <option value="anthropic">anthropic</option>
          </select>
          <input
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="h-9 w-44 rounded-lg border border-border bg-surface px-3 font-mono text-xs text-text-primary"
            placeholder="model id"
          />
          <button
            onClick={startRun}
            disabled={running}
            className="flex h-9 items-center gap-2 rounded-lg bg-brand-600 px-4 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {running ? "Running…" : "Run evaluation"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-3 py-2 text-sm text-danger">{error}</div>
      )}

      {/* Dataset info */}
      {dataset && (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm">{dataset.name} v{dataset.version}</CardTitle>
              <CardDescription>
                {dataset.task_count} tasks · {dataset.categories.join(", ")}
              </CardDescription>
            </div>
            <FlaskConical className="h-5 w-5 text-brand-400" />
          </CardHeader>
        </Card>
      )}

      {/* Latest run summary */}
      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <Stat label="Total tests" value={summary.total_tasks} />
          <Stat label="Passed" value={summary.passed_tasks} />
          <Stat label="Failed" value={summary.failed_tasks} />
          <Stat label="Pass rate" value={`${(summary.pass_rate * 100).toFixed(1)}%`} />
          <Stat label="Avg score" value={summary.avg_score.toFixed(2)} />
        </div>
      )}

      {summary?.by_category && (
        <Card>
          <CardHeader><CardTitle className="text-sm">By category</CardTitle></CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            {Object.entries(summary.by_category).map(([cat, s]) => (
              <div key={cat} className="rounded-lg border border-border bg-surface-raised px-3 py-2 text-xs">
                <div className="font-medium text-text-primary">{cat}</div>
                <div className="mt-0.5 text-text-muted">{s.passed}/{s.total} passed</div>
              </div>
            ))}
            <div className="ml-auto text-[11px] text-text-muted">
              {summary.scoring} · {(summary.duration_ms / 1000).toFixed(1)}s · {detail?.agent_config?.model}
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        {/* Run history */}
        <Card>
          <CardHeader><CardTitle className="text-sm">Evaluation history</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            {runs.length === 0 && <p className="text-sm text-text-muted">No runs yet.</p>}
            {runs.map((r) => (
              <button
                key={r.id}
                onClick={() => viewRun(r.id)}
                className={`w-full rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                  detail?.id === r.id ? "border-brand-500/60 bg-brand-500/10" : "border-border hover:bg-surface-raised"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs text-text-primary">{r.agent_config?.model}</span>
                  <Badge variant={r.status === "completed" ? "success" : "warning"}>{r.status}</Badge>
                </div>
                <div className="mt-1 flex items-center justify-between text-xs text-text-muted">
                  <span>{r.summary?.pass_rate != null ? `${(r.summary.pass_rate * 100).toFixed(0)}% pass` : "—"}</span>
                  <span>{r.created_at ? new Date(r.created_at).toLocaleString() : ""}</span>
                </div>
              </button>
            ))}
          </CardContent>
        </Card>

        {/* Task results */}
        <Card>
          <CardHeader><CardTitle className="text-sm">Task results</CardTitle></CardHeader>
          <CardContent className="space-y-1.5">
            {!detail && <p className="text-sm text-text-muted">Select or run an evaluation to see per-task results.</p>}
            {detail?.results.map((r) => {
              const open = expandedTask === r.id;
              return (
                <div key={r.id} className="rounded-lg border border-border">
                  <button
                    onClick={() => setExpandedTask(open ? null : r.id)}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm"
                  >
                    {open ? <ChevronDown className="h-3.5 w-3.5 text-text-muted" /> : <ChevronRight className="h-3.5 w-3.5 text-text-muted" />}
                    <Badge variant={r.passed ? "success" : "danger"}>{r.passed ? "pass" : "fail"}</Badge>
                    <span className="font-mono text-xs text-text-primary">{r.task_id}</span>
                    <span className="ml-auto text-[11px] text-text-muted">
                      {r.details?.category} · {r.latency_ms ?? "—"}ms
                    </span>
                  </button>
                  {open && (
                    <div className="space-y-2 border-t border-border px-3 py-2 text-xs">
                      <div className="text-text-secondary">{r.details?.description}</div>
                      <div>
                        <div className="mb-0.5 font-medium text-text-muted">Prompt</div>
                        <pre className="whitespace-pre-wrap rounded bg-canvas p-2 text-text-primary">{r.details?.prompt}</pre>
                      </div>
                      <div>
                        <div className="mb-0.5 font-medium text-text-muted">Answer</div>
                        <pre className="whitespace-pre-wrap rounded bg-canvas p-2 text-text-primary">{r.details?.answer ?? "(none)"}</pre>
                      </div>
                      {r.details?.provider_error && (
                        <div className="rounded border border-danger/30 bg-danger/10 p-2 text-danger">{r.details.provider_error}</div>
                      )}
                      {r.details?.tools && (
                        <div className="text-text-muted">
                          tools: {(r.details.tools.tools_used ?? []).join(", ") || "none"} · calls: {r.details.tools.tool_calls ?? 0} · errors: {r.details.tools.tool_errors ?? 0}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="text-xs font-medium uppercase tracking-wider text-text-muted">{label}</div>
        <div className="mt-2 text-xl font-semibold text-text-primary">{value}</div>
      </CardContent>
    </Card>
  );
}
