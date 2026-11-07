"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Bell, LogOut, Menu, Search } from "lucide-react";
import { api } from "@/lib/api-client";
import { clearSession, getUser } from "@/lib/auth";

interface TopbarProps {
  onMenuClick: () => void;
}

export function Topbar({ onMenuClick }: TopbarProps) {
  const router = useRouter();
  const [user, setUser] = useState<{ email?: string; full_name?: string } | null>(null);

  useEffect(() => {
    const t = setTimeout(() => setUser(getUser()), 0);
    return () => clearTimeout(t);
  }, []);

  async function handleLogout() {
    try {
      await api.logout();
    } catch {
      /* token may already be invalid — clear locally regardless */
    }
    clearSession();
    router.push("/login");
    router.refresh();
  }

  const displayName = user?.full_name || user?.email || "User";
  const initial = (user?.full_name?.[0] || user?.email?.[0] || "U").toUpperCase();

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
            {initial}
          </div>
          <div className="hidden leading-tight md:block">
            <div className="max-w-40 truncate text-xs font-medium text-text-primary">
              {displayName}
            </div>
            <div className="text-[10px] text-text-muted">{user?.email ?? ""}</div>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            className="rounded-lg p-1.5 text-text-muted hover:bg-surface-raised hover:text-text-primary"
            aria-label="Sign out"
            title="Sign out"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </header>
  );
}
