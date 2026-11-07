"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  Boxes,
  FlaskConical,
  GitCompareArrows,
  History,
  LayoutDashboard,
  MessageSquareText,
  Settings,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/playground", label: "Playground", icon: MessageSquareText },
  { href: "/models", label: "Models", icon: Boxes },
  { href: "/comparisons", label: "Comparisons", icon: GitCompareArrows },
  { href: "/requests", label: "Requests", icon: History },
  { href: "/evaluations", label: "Evaluations", icon: FlaskConical },
  { href: "/analytics", label: "Analytics", icon: BarChart3 },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-2.5 border-b border-border px-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600">
          <Zap className="h-4 w-4 text-white" strokeWidth={2.5} />
        </div>
        <div className="leading-tight">
          <div className="text-sm font-bold tracking-wide text-text-primary">
            NEXUS<span className="text-brand-400"> AI</span>
          </div>
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-text-muted">
            LLM Gateway
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-brand-500/10 text-brand-300"
                  : "text-text-secondary hover:bg-surface-raised hover:text-text-primary",
              )}
            >
              <Icon
                className={cn("h-4 w-4", active ? "text-brand-400" : "text-text-muted")}
                strokeWidth={2}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-border px-5 py-4">
        <div className="text-[11px] text-text-muted">
          v0.1.0 · Phase 1
        </div>
      </div>
    </div>
  );
}
