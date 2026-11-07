import type { LucideIcon } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

interface ModulePlaceholderProps {
  title: string;
  description: string;
  icon: LucideIcon;
  phase: string;
  items?: string[];
}

export function ModulePlaceholder({
  title,
  description,
  icon: Icon,
  phase,
  items = [],
}: ModulePlaceholderProps) {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary">{title}</h1>
        <p className="mt-1 text-sm text-text-secondary">{description}</p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center gap-4 py-14 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-surface-raised">
            <Icon className="h-6 w-6 text-brand-400" />
          </div>
          <div>
            <div className="text-sm font-medium text-text-primary">
              Module in development
            </div>
            <p className="mt-1 max-w-md text-sm text-text-secondary">
              This module is scheduled for <span className="text-brand-300">{phase}</span>.
              {items.length > 0 && (
                <>
                              {" "}Planned capabilities: {items.join(", ")}.
</>
              )}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
