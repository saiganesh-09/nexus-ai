"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, Clock, Coins, Gauge, Loader2, Zap } from "lucide-react";
import { api, type AnalyticsOverview } from "@/lib/api-client";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const PIE_COLORS = ["#6366f1", "#38bdf8", "#818cf8", "#34d399", "#fbbf24", "#f87171", "#a78bfa"];

export default function DashboardPage() {
  const authed = useRequireAuth();
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.analyticsOverview(30));
      setError(null);
    } catch {
      setError("Failed to load analytics");
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

  if (error || !data) {
    return (
      <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
        {error ?? "No data"}
      </div>
    );
  }

  const hasData = data.requests > 0;

  return (
    <div className="mx-auto max-w-7xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Dashboard</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Live metrics from your AI requests — last {data.window_days} days.
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <Kpi icon={<Zap className="h-4 w-4" />} label="Total requests" value={data.requests.toLocaleString()} />
        <Kpi icon={<Activity className="h-4 w-4" />} label="Total tokens" value={data.total_tokens.toLocaleString()} sub={`${data.input_tokens.toLocaleString()} in / ${data.output_tokens.toLocaleString()} out`} />
        <Kpi icon={<Coins className="h-4 w-4" />} label="Est. spend" value={`$${data.estimated_cost_usd.toFixed(4)}`} sub="estimated, not billed" />
        <Kpi icon={<Clock className="h-4 w-4" />} label="Avg latency" value={`${Math.round(data.avg_latency_ms)} ms`} />
        <Kpi icon={<Gauge className="h-4 w-4" />} label="Success rate" value={`${(data.success_rate * 100).toFixed(1)}%`} sub={`cache hits ${(data.cache_hit_rate * 100).toFixed(1)}%`} />
      </div>

      {/* Charts row */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Requests & cost over time</CardTitle>
            <CardDescription>Daily activity, last {data.window_days} days</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            {hasData ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.timeseries} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="reqGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#6366f1" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#1e2a45" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="date" tick={{ fill: "#5d6b8a", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                  <YAxis tick={{ fill: "#5d6b8a", fontSize: 11 }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#111a2e", border: "1px solid #2a3a5f", borderRadius: 8, fontSize: 12 }} />
                  <Area type="monotone" dataKey="requests" stroke="#6366f1" fill="url(#reqGrad)" strokeWidth={2} name="Requests" />
                </AreaChart>
              </ResponsiveContainer>
            ) : <EmptyChart />}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Model usage</CardTitle>
            <CardDescription>Distribution by request count</CardDescription>
          </CardHeader>
          <CardContent className="h-64">
            {hasData && data.model_usage.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={data.model_usage} dataKey="count" nameKey="model" innerRadius={45} outerRadius={75} paddingAngle={3} strokeWidth={0}>
                    {data.model_usage.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#111a2e", border: "1px solid #2a3a5f", borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : <EmptyChart />}
            {hasData && data.model_usage.length > 0 && (
              <div className="mt-2 space-y-1">
                {data.model_usage.slice(0, 4).map((m, i) => (
                  <div key={m.model} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-1.5 text-text-secondary">
                      <span className="h-2 w-2 rounded-full" style={{ background: PIE_COLORS[i % PIE_COLORS.length] }} />
                      {m.model}
                    </span>
                    <span className="text-text-primary">{m.count}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Cost trend */}
      <Card>
        <CardHeader>
          <CardTitle>Cost trend</CardTitle>
          <CardDescription>Estimated USD spend per day</CardDescription>
        </CardHeader>
        <CardContent className="h-52">
          {hasData ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.timeseries} margin={{ top: 4, right: 8, left: -8, bottom: 0 }}>
                <CartesianGrid stroke="#1e2a45" strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: "#5d6b8a", fontSize: 11 }} tickFormatter={(d: string) => d.slice(5)} />
                <YAxis tick={{ fill: "#5d6b8a", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#111a2e", border: "1px solid #2a3a5f", borderRadius: 8, fontSize: 12 }} formatter={(v) => [`$${Number(v).toFixed(4)}`, "Cost"]} />
                <Bar dataKey="cost" fill="#38bdf8" radius={[4, 4, 0, 0]} name="Cost (USD)" />
              </BarChart>
            </ResponsiveContainer>
          ) : <EmptyChart />}
        </CardContent>
      </Card>

      {!hasData && (
        <Card>
          <CardContent className="py-10 text-center">
            <p className="text-sm text-text-secondary">
              No requests yet — head to the{" "}
              <a href="/playground" className="text-brand-400 hover:underline">Playground</a>{" "}
              to send your first prompt.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Kpi({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-text-muted">{label}</span>
          <span className="text-brand-400">{icon}</span>
        </div>
        <div className="mt-2 text-2xl font-semibold text-text-primary">{value}</div>
        {sub && <div className="mt-1 text-[11px] text-text-muted">{sub}</div>}
      </CardContent>
    </Card>
  );
}

function EmptyChart() {
  return (
    <div className="flex h-full items-center justify-center text-xs text-text-muted">
      No data in this window
    </div>
  );
}
