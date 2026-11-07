import { Suspense } from "react";
import { Activity, Clock, Server, Zap } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { fetchHealth, type HealthStatus } from "@/lib/api";

async function getHealth(): Promise<HealthStatus | null> {
  try {
    return await fetchHealth();
  } catch {
    return null;
  }
}

export default function OverviewPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Overview</h1>
        <p className="mt-1 text-sm text-text-secondary">
          System status and platform health.
        </p>
      </div>

      <Suspense fallback={<HealthSkeleton />}>
        <HealthSection />
      </Suspense>
    </div>
  );
}

async function HealthSection() {
  const health = await getHealth();

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatusCard
          icon={<Server className="h-4 w-4" />}
          label="API service"
          value={health ? health.service : "Unreachable"}
          healthy={Boolean(health)}
        />
        <StatusCard
          icon={<Activity className="h-4 w-4" />}
          label="API status"
          value={health ? health.status.toUpperCase() : "DOWN"}
          healthy={Boolean(health)}
        />
        <StatusCard
          icon={<Zap className="h-4 w-4" />}
          label="Version"
          value={health?.version ?? "—"}
          healthy={Boolean(health)}
        />
        <StatusCard
          icon={<Clock className="h-4 w-4" />}
          label="Environment"
          value={health?.environment ?? "—"}
          healthy={Boolean(health)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Backend connectivity</CardTitle>
          <CardDescription>
            Live response from{" "}
            <code className="font-mono text-brand-300">GET /api/v1/health</code>
          </CardDescription>
        </CardHeader>
        <CardContent>
          {health ? (
            <div className="flex items-center justify-between rounded-lg border border-border bg-surface-raised px-4 py-3">
              <div className="flex items-center gap-3">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-60" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-success" />
                </span>
                <span className="text-sm text-text-primary">
                  Connected to backend
                </span>
              </div>
              <Badge variant="success">{health.status}</Badge>
            </div>
          ) : (
            <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              Backend is not reachable at{" "}
              <code className="font-mono">NEXT_PUBLIC_API_URL</code>. Start the
              FastAPI server on port 8000 and reload.
            </div>
          )}
          <p className="mt-4 text-xs text-text-muted">
            Dashboard metrics (requests, tokens, cost, latency) will populate
            from real database records once the data layer ships in Phase 2+.
          </p>
        </CardContent>
      </Card>
    </>
  );
}

function HealthSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardContent className="pt-5">
            <div className="h-3 w-20 animate-pulse rounded bg-surface-overlay" />
            <div className="mt-3 h-6 w-28 animate-pulse rounded bg-surface-overlay" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function StatusCard({
  icon,
  label,
  value,
  healthy,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  healthy: boolean;
}) {
  return (
    <Card>
      <CardContent className="flex items-start justify-between pt-5">
        <div>
          <div className="text-xs font-medium uppercase tracking-wider text-text-muted">
            {label}
          </div>
          <div className="mt-2 truncate text-lg font-semibold text-text-primary">
            {value}
          </div>
        </div>
        <div
          className={`flex h-9 w-9 items-center justify-center rounded-lg border ${
            healthy
              ? "border-success/30 bg-success/10 text-success"
              : "border-border bg-surface-raised text-text-muted"
          }`}
        >
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}
