"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save } from "lucide-react";
import { api, ApiError } from "@/lib/api-client";
import { clearSession, getUser, setSession } from "@/lib/auth";
import { useRequireAuth } from "@/lib/use-require-auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SettingsPage() {
  const authed = useRequireAuth();
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "ok" | "err"; text: string } | null>(null);

  useEffect(() => {
    if (!authed) return;
    const t = setTimeout(() => {
      const u = getUser();
      if (u) {
        setFullName(u.full_name ?? "");
        setEmail(u.email ?? "");
      }
    }, 0);
    return () => clearTimeout(t);
  }, [authed]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      const updated = await api.updateProfile(
        fullName || undefined,
        newPassword || undefined,
      );
      // Password change revokes the token — session must be refreshed.
      if (newPassword) {
        const login = await api.login(email, newPassword);
        setSession(login.access_token, updated);
      } else {
        setSession(localStorage.getItem("nexus_access_token") ?? "", updated);
      }
      setNewPassword("");
      setMessage({ type: "ok", text: "Profile updated." });
    } catch (err) {
      setMessage({
        type: "err",
        text: err instanceof ApiError ? err.message : "Update failed",
      });
    } finally {
      setSaving(false);
    }
  }

  function signOut() {
    api.logout().catch(() => {});
    clearSession();
    router.push("/login");
  }

  if (!authed) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-brand-400" />
      </div>
    );
  }

  const inputCls =
    "h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary focus:border-brand-500/60 focus:outline-none";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Settings</h1>
        <p className="mt-1 text-sm text-text-secondary">Profile and account preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Profile</CardTitle>
          <CardDescription>Update your display name and password.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={save} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">Email</label>
              <input value={email} disabled className={`${inputCls} opacity-60`} />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">Full name</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} className={inputCls} />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-text-secondary">
                New password <span className="text-text-muted">(leave blank to keep current)</span>
              </label>
              <input
                type="password"
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className={inputCls}
                placeholder="Min. 8 characters"
              />
              <p className="mt-1 text-[11px] text-text-muted">
                Changing your password signs out all existing sessions.
              </p>
            </div>
            {message && (
              <div className={`rounded-lg border px-3 py-2 text-sm ${message.type === "ok" ? "border-success/30 bg-success/10 text-success" : "border-danger/30 bg-danger/10 text-danger"}`}>
                {message.text}
              </div>
            )}
            <button
              type="submit"
              disabled={saving}
              className="flex h-10 items-center gap-2 rounded-lg bg-brand-600 px-5 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
            >
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              Save changes
            </button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Session</CardTitle>
        </CardHeader>
        <CardContent>
          <button
            onClick={signOut}
            className="rounded-lg border border-danger/40 px-4 py-2 text-sm text-danger hover:bg-danger/10"
          >
            Sign out
          </button>
        </CardContent>
      </Card>
    </div>
  );
}
