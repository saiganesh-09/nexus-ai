"use client";

import { Bell, Menu, Search } from "lucide-react";

interface TopbarProps {
  onMenuClick: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  return (
    <header className="flex h-16 items-center gap-3 border-b border-border bg-surface/80 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        onClick={onMenuClick}
        className="rounded-lg p-2 text-text-secondary hover:bg-surface-raised hover:text-text-primary lg:hidden"
        aria-label="Open navigation"
      >
        <Menu className="h-5 w-5" />
      </button>

      <div className="relative hidden flex-1 max-w-md sm:block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
        <input
          type="search"
          placeholder="Search requests, models…"
          className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-text-primary placeholder:text-text-muted focus:border-brand-500/60 focus:outline-none"
        />
      </div>

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          className="relative rounded-lg p-2 text-text-secondary hover:bg-surface-raised hover:text-text-primary"
          aria-label="Notifications"
        >
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-brand-500" />
        </button>
        <div className="ml-1 flex items-center gap-2.5 rounded-lg border border-border bg-surface px-2.5 py-1.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-brand-600/80 text-xs font-semibold text-white">
            U
          </div>
          <div className="hidden leading-tight md:block">
            <div className="text-xs font-medium text-text-primary">User</div>
            <div className="text-[10px] text-text-muted">Free tier</div>
          </div>
        </div>
      </div>
    </header>
  );
}
