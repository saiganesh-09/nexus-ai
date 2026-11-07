"use client";

import { useEffect, useState } from "react";
import { Boxes, Loader2 } from "lucide-react";
import { api, type ModelInfo } from "@/lib/api-client";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ModelsPage() {
  const authed = useRequireAuth();
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!authed) return;
    const t = setTimeout(() => {
      api
        .listModels()
        .then(setModels)
        .catch(() => setModels([]))
        .finally(() => setLoading(false));
    }, 0);
    return () => clearTimeout(t);
  }, [authed]);

  if (!authed || loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Models</h1>
        <p className="mt-1 text-sm text-text-secondary">
          Available providers and models with pricing metadata.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        {models.map((m) => (
          <Card key={`${m.provider}/${m.model_id}`}>
            <CardHeader className="flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm">{m.display_name}</CardTitle>
              <Badge variant={m.provider_configured ? "success" : "warning"}>
                {m.provider_configured ? "configured" : "not configured"}
              </Badge>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-text-secondary">
              <div className="flex justify-between">
                <span>Provider</span>
                <span className="font-mono text-text-primary">{m.provider}</span>
              </div>
              <div className="flex justify-between">
                <span>Model ID</span>
                <span className="font-mono text-text-primary">{m.model_id}</span>
              </div>
              <div className="flex justify-between">
                <span>Context window</span>
                <span className="text-text-primary">{m.context_window.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span>Price (per 1M tokens)</span>
                <span className="text-text-primary">
                  ${m.input_price_per_mtok.toFixed(2)} in / ${m.output_price_per_mtok.toFixed(2)} out
                </span>
              </div>
              <div className="flex flex-wrap gap-1 pt-1">
                {Object.entries(m.capabilities).map(([k, v]) =>
                  v ? <Badge key={k} variant="default">{k}</Badge> : null,
                )}
              </div>
            </CardContent>
          </Card>
        ))}
        {models.length === 0 && (
          <Card className="sm:col-span-2">
            <CardContent className="flex flex-col items-center gap-3 py-12 text-text-muted">
              <Boxes className="h-8 w-8 opacity-40" />
              <p className="text-sm">No models in the catalog yet.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
