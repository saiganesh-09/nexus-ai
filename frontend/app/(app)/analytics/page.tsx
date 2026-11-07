"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Loader2 } from "lucide-react";
import { api, type AnalyticsOverview, type ModelAnalytics } from "@/lib/api-client";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AnalyticsPage() {
  const authed = useRequireAuth();
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [models, setModels] = useState<ModelAnalytics[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [o, m] = await Promise.all([api.analyticsOverview(30), api.analyticsByModel(30)]);
      setOverview(o);
      setModels(m);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authed) return;
    const t = setTimeout(() => void load(), 0);
    return () => clearTimeout(t);
  }, [authed, load]);

  if (!authed || loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      </div>
    );
  }

  const tooltipStyle = { background: "#111a2e", border: "1px solid #2a3a5f", borderRadius: 8, fontSize: 12 };

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Analytics</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Cost, token, latency and provider metrics — all from recorded requests.
        </p>
      </div>

      {!overview || overview.requests === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-sm text-text-muted">
            No usage data yet. Send prompts in the Playground to populate analytics.
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Requests" value={overview.requests} />
            <Stat label="Tokens" value={overview.total_tokens} />
            <Stat label="Spend (est.)" value={`$${overview.estimated_cost_usd.toFixed(4)}`} />
            <Stat label="Error rate" value={`${((1 - overview.success_rate) * 100).toFixed(1)}%`} />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Daily cost</CardTitle>
                <CardDescription>Estimated USD per day</CardDescription>
              </CardHeader>
              <CardContent className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={overview.timeseries} margin={{ top: 4, right: 8, left: -12, bottom: 0 }}>
                    <CartesianGrid stroke="#1e2a45" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: "#5d6b8a", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                    <YAxis tick={{ fill: "#5d6b8a", fontSize: 11 }} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`$${Number(v).toFixed(4)}`, "Cost"]} />
                    <Bar dataKey="cost" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Daily requests vs errors</CardTitle>
                <CardDescription>Volume and failure count</CardDescription>
              </CardHeader>
              <CardContent className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={overview.timeseries} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <CartesianGrid stroke="#1e2a45" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="date" tick={{ fill: "#5d6b8a", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                    <YAxis tick={{ fill: "#5d6b8a", fontSize: 11 }} allowDecimals={false} />
                    <Tooltip contentStyle={tooltipStyle} />
                    <Bar dataKey="requests" fill="#6366f1" radius={[4, 4, 0, 0]} name="Requests" />
                    <Bar dataKey="errors" fill="#f87171" radius={[4, 4, 0, 0]} name="Errors" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Per-model performance</CardTitle>
              <CardDescription>Requests, tokens, cost, latency and success rate by model</CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-[11px] uppercase tracking-wider text-text-muted">
                    <th className="px-5 py-3 font-medium">Model</th>
                    <th className="px-4 py-3 font-medium">Requests</th>
                    <th className="px-4 py-3 font-medium">Tokens</th>
                    <th className="px-4 py-3 font-medium">Cost</th>
                    <th className="px-4 py-3 font-medium">Avg latency</th>
                    <th className="px-4 py-3 font-medium">Success</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={`${m.provider}/${m.model}`} className="border-b border-border/60">
                      <td className="px-5 py-3">
                        <div className="text-text-primary">{m.model}</div>
                        <div className="text-[11px] text-text-muted">{m.provider}</div>
                      </td>
                      <td className="px-4 py-3 text-text-secondary">{m.requests}</td>
                      <td className="px-4 py-3 text-text-secondary">{(m.input_tokens + m.output_tokens).toLocaleString()}</td>
                      <td className="px-4 py-3 text-text-secondary">${m.estimated_cost_usd.toFixed(4)}</td>
                      <td className="px-4 py-3 text-text-secondary">{Math.round(m.avg_latency_ms)}ms</td>
                      <td className="px-4 py-3"><Badge variant={m.success_rate >= 0.95 ? "success" : m.success_rate >= 0.8 ? "warning" : "danger"}>{(m.success_rate * 100).toFixed(0)}%</Badge></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        </>
      )}
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
